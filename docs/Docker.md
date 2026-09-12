# Docker e Conteinerização do AZ1

Este documento descreve como a solução é empacotada em contêineres, por que cada
decisão foi tomada e como operar a pilha em desenvolvimento, em integração
contínua e em produção. Ele complementa a [Seção 3.7 do Projeto.md](./Projeto.md#37-processo-de-deploy-em-nuvem),
que trata do provedor de nuvem e da topologia de implantação: aqui está o *como*
as imagens são construídas e executadas; lá, o *onde* elas rodam.

---

## 1. Visão geral

A pilha é composta por quatro contêineres, sendo dois deles construídos a partir
do código do repositório.

| Contêiner | Origem | Papel | Porta interna |
|---|---|---|---|
| `frontend` | `docker/frontend/Dockerfile` | Serve o bundle React e encaminha `/api` para a API. Única porta de entrada. | 8080 (prod) / 5173 (dev) |
| `api` | `docker/api/Dockerfile` | FastAPI, pipeline de PLN, integração com Deepgram e Gemini. | 8000 |
| `minio` | `minio/minio` (oficial) | Armazenamento de áudio compatível com S3. | 9000 / 9001 |
| `minio-init` | `minio/mc` (oficial) | Cria o bucket e aplica a regra de expiração. Roda uma vez e sai. |: |

E dois contêineres sob demanda, controlados por `profiles`:

| Contêiner | Perfil | Papel |
|---|---|---|
| `trainer` | `ml` | Retreina o classificador e roda as varreduras de experimento. |
| `tests` | `ci` | Executa a suíte de testes dentro da imagem. |

### Topologia

```text
                     ┌──────────────────────────────────────────────┐
  navegador ────────▶│  frontend (nginx, UID 101)      :8080        │
     :8080/:80       │  ├── /            → bundle React (estático)  │
                     │  ├── /assets/     → cache imutável de 1 ano  │
                     │  ├── /healthz     → sonda do contêiner       │
                     │  └── /api/        → proxy reverso ───────┐   │
                     └─────────────────────────────────────────│───┘
                            rede: frontend + backend           │
                                                               ▼
                     ┌──────────────────────────────────────────────┐
                     │  api (uvicorn, UID 10001, raiz read-only)    │
                     │  ├── /health                     :8000       │
                     │  └── /api/v1/{audio,transcribe,analyze,chat} │
                     └───────┬──────────────────────────────┬───────┘
                             │ rede: backend                │ internet
                             ▼                              ▼
                     ┌────────────────┐          ┌─────────────────────┐
                     │ minio  :9000   │          │ Deepgram  ·  Gemini │
                     │ bucket az1-audio│         └─────────────────────┘
                     └────────────────┘
```

Duas redes, e não uma: `frontend` recebe tráfego do host, `backend` conecta os
serviços internos. O contêiner do nginx é o único que participa das duas: e,
portanto, o único caminho de fora para dentro. A segmentação é estrutural: um
serviço novo colocado na rede `frontend` simplesmente não enxerga o MinIO, sem
depender de ninguém lembrar de bloquear.

---

## 2. Pré-requisitos

- Docker Engine 23+ ou Docker Desktop (o BuildKit precisa estar ativo, o que é o
  padrão desde a 23);
- Docker Compose v2.24+ (para `!override` e `env_file.required`);
- opcionalmente GNU Make, para os atalhos do `Makefile`.

Verifique com:

```bash
docker version
docker compose version
docker buildx version
```

---

## 3. Desenvolvimento

```bash
cp .env.example .env      # preencha DEEPGRAM_API_KEY, GEMINI_API_KEY e a autenticação (ver Seção 6)
docker compose up -d --build
```

O compose carrega `docker-compose.yml` **e** `docker-compose.override.yml`
automaticamente. Sobem então:

| Endereço | O quê |
|---|---|
| http://localhost:5173 | interface, com hot reload do Vite |
| http://localhost:8010/docs | Swagger da API |
| http://localhost:9001 | console do MinIO (as chaves `AUDIO_STORAGE_*` do seu `.env`) |

O código do host entra por bind mount: editar um `.py` reinicia o uvicorn,
editar um `.jsx` atualiza o navegador. Não é preciso reconstruir a imagem para
nenhuma das duas coisas: só quando as *dependências* mudam.

A interface exige login com Microsoft (RNF02). Sem `SUPABASE_URL` e
`SUPABASE_ANON_KEY` configurados, a API responde 500 em toda rota protegida -
não 401: porque é uma falha de configuração, não de credencial do usuário. Para
desenvolver sem configurar Entra ID/Supabase, defina `AZ1_AUTH_MODE=disabled`
no `.env` (ver Seção 6); só funciona em desenvolvimento, a produção recusa
subir com esse valor (Seção 4).

```bash
docker compose logs -f api     # acompanha os logs da API
docker compose exec api bash   # abre um shell no contêiner
docker compose down            # derruba, preservando os dados do MinIO
docker compose down -v         # derruba e APAGA os áudios armazenados
```

> **Windows e macOS:** o bind mount não propaga eventos de inotify, e sem
> polling o hot reload nunca dispara. Por isso `WATCHFILES_FORCE_POLLING=1` e
> `VITE_USE_POLLING=1` já vêm ligados no override. Em Linux nativo, defina os
> dois como vazio no `.env` para economizar CPU.

---

## 4. Produção

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

Como a linha é longa e repeti-la a cada comando é como se esquece o `-f`, vale
fixar na máquina de deploy:

```bash
export COMPOSE_FILE=docker-compose.yml:docker-compose.prod.yml
docker compose up -d          # já sobe em modo produção
```

Definir `COMPOSE_FILE` também **desliga** o carregamento automático do override
de desenvolvimento: que é o erro mais fácil de cometer num servidor, e o mais
difícil de perceber depois.

O que muda em relação ao desenvolvimento:

- interface publicada na porta **80** do host; API e MinIO **não** são
  publicados, e só existem dentro da rede interna;
- uvicorn com 2 workers, `--proxy-headers` e sem cabeçalho `Server`;
- limites de CPU e memória por serviço;
- `restart: always`;
- `AUDIO_STORAGE_ACCESS_KEY` e `AUDIO_STORAGE_SECRET_KEY` passam a ser
  **obrigatórias**: sem elas a subida falha, em vez de silenciosamente usar
  `minioadmin/minioadmin`;
- `AZ1_AUTH_MODE=disabled` (válvula de desenvolvimento do RNF02: ver Seção 6)
  passa a **derrubar a subida**, em vez de deixar as rotas protegidas abertas
  sem token em produção.

```bash
# .env do servidor
AUDIO_STORAGE_ACCESS_KEY=az1                # 3+ caracteres
AUDIO_STORAGE_SECRET_KEY=<senha forte>      # 8+ caracteres
DEEPGRAM_API_KEY=<chave>
GEMINI_API_KEY=<chave>
SUPABASE_URL=https://<project-ref>.supabase.co
SUPABASE_ANON_KEY=<chave anônima do projeto>
```

Essas duas chaves são a credencial única do armazenamento: a API assina as
requisições S3 com elas **e** o contêiner do MinIO sobe com elas como usuário
root. Não existe um segundo par de variáveis para o servidor. Um par só, num
lugar só: porque credencial duplicada em dois nomes é credencial que um dia vai
divergir, e a divergência aparece como um 403 na primeira gravação de áudio, sem
dizer qual dos dois lados está errado.

---

## 5. Perfis: treino e testes

Nenhum dos dois sobe com `docker compose up`; ambos são invocados
explicitamente e removidos ao terminar.

```bash
# retreina o classificador e grava em ./resultados no host
docker compose --profile ml run --rm trainer

# varredura de pré-processamento e vetorização
docker compose --profile ml run --rm trainer python -m pln.experimento

# varredura de hiperparâmetros
docker compose --profile ml run --rm trainer python -m pln.ajuste_fino

# suíte completa (145 testes)
docker compose --profile ci run --rm tests
```

O valor de treinar em contêiner é a correspondência de ambiente: o modelo que
vai a produção é gerado com as mesmas versões de `scikit-learn`, `nltk` e
`numpy` que a API usa para carregá-lo. Resultado de PLN muda com versão de
biblioteca, e essa é uma divergência cara de descobrir tarde.

> Em **Linux**, exporte `DOCKER_UID=$(id -u)` e `DOCKER_GID=$(id -g)` antes de
> rodar o `trainer`, senão os arquivos gravados em `resultados/` sairão
> pertencendo ao root. Em Windows e macOS o padrão está correto.

---

## 6. Variáveis de ambiente

Todas são lidas do `.env` da raiz (veja `.env.example`). As específicas de
Docker:

| Variável | Padrão | Efeito |
|---|---|---|
| `AZ1_WEB_PORT` | 5173 (dev) / 80 (prod) | Porta publicada da interface. |
| `AZ1_API_PORT` | 8010 | Porta da API publicada em desenvolvimento. |
| `MINIO_API_PORT` / `MINIO_CONSOLE_PORT` | 9000 / 9001 | Portas do MinIO em desenvolvimento. |
| `AUDIO_STORAGE_ACCESS_KEY` / `AUDIO_STORAGE_SECRET_KEY` | `minioadmin` | Credencial única do armazenamento: a API assina as requisições S3 com ela e o MinIO sobe com ela. Obrigatórias em produção. Mínimo de 3 e 8 caracteres. |
| `AZ1_AUTH_MODE` | `enabled` | Com `disabled`, todas as rotas protegidas do RNF02 ficam abertas sem token: só para desenvolvimento. Em produção a subida é recusada se estiver `disabled` (ver Seção 4). |
| `SUPABASE_URL` / `SUPABASE_ANON_KEY` |: | Projeto Supabase usado pelo Supabase Auth (RNF02). A mesma URL é repassada ao build do frontend como `VITE_SUPABASE_URL`/`VITE_SUPABASE_ANON_KEY`: não precisa duplicar a variável no `.env`. |
| `UVICORN_WORKERS` | 2 | Workers do uvicorn em produção. |
| `AZ1_VERSION` | `dev` | Tag das imagens e label OCI de versão. |
| `DOCKER_UID` / `DOCKER_GID` | 0 | Dono dos arquivos gerados pelo `trainer` (só Linux). |
| `WATCHFILES_FORCE_POLLING` / `VITE_USE_POLLING` | 1 | Hot reload sobre bind mount em Windows/macOS. |

`AUDIO_STORAGE_ENDPOINT_URL` é definido pelo próprio compose como
`http://minio:9000` e **sobrepõe** o valor do `.env`. Isso é intencional: o
`.env` está escrito para rodar a API direto no host (`localhost:9000`), e dentro
da rede do compose esse endereço apontaria para o próprio contêiner da API.

### Segredos como arquivo

Chave de API em variável de ambiente aparece em `docker inspect`, no
`/proc/<pid>/environ` de qualquer processo do contêiner e em qualquer log que
imprima o ambiente. Para evitar isso, o entrypoint da API aceita a convenção
`*_FILE`:

```yaml
services:
  api:
    environment:
      GEMINI_API_KEY_FILE: /run/secrets/gemini_api_key
      DEEPGRAM_API_KEY_FILE: /run/secrets/deepgram_api_key
    secrets: [gemini_api_key, deepgram_api_key]

secrets:
  gemini_api_key:
    file: ./secrets/gemini_api_key.txt
  deepgram_api_key:
    file: ./secrets/deepgram_api_key.txt
```

O entrypoint lê o arquivo e exporta a variável antes de iniciar o uvicorn. O
código da aplicação continua lendo apenas `os.environ` e não precisa saber de
nada disso: a mesma imagem funciona com as duas formas.

---

## 7. Build avançado

O compose constrói uma imagem por vez. Para builds paralelas, cache
compartilhado e multiarquitetura, use o `docker-bake.hcl`:

```bash
docker buildx bake                 # api + frontend, em paralelo
docker buildx bake --print         # mostra o plano, sem construir
docker buildx bake trainer         # só a imagem de treino
docker buildx bake release         # linux/amd64 + linux/arm64
docker buildx bake --push release  # constrói e publica no registry
```

Multiarquitetura importa aqui de forma concreta: quem desenvolve em Mac M-series
constrói `arm64`, e a instância EC2 do deploy é `amd64`. Sem `--platform`, a
imagem construída no notebook simplesmente não executa no servidor, e a
descoberta acontece no meio do deploy. Para construir para outra arquitetura é
preciso um builder com emulação:

```bash
docker buildx create --name az1 --driver docker-container --use
```

Em CI, troque o cache local pelo cache de registro (o arquivo tem o trecho
comentado). `mode=max` é o que importa num build multi-estágio como este: sem
ele, o cache guarda apenas a imagem final e o estágio de dependências: o caro -
é refeito em todo pipeline.

---

## 8. Deploy

O fluxo previsto na Seção 3.7 do `Projeto.md` é ECR + EC2. Com esta estrutura:

```bash
# 1. autenticar no registry
aws ecr get-login-password --region us-east-1 \
  | docker login --username AWS --password-stdin <conta>.dkr.ecr.us-east-1.amazonaws.com

# 2. construir e publicar as duas imagens, com metadados de versão
REGISTRY=<conta>.dkr.ecr.us-east-1.amazonaws.com/ \
TAG=0.2.0 VERSION=0.2.0 VCS_REF=$(git rev-parse --short HEAD) \
BUILD_DATE=$(date -u +%Y-%m-%dT%H:%M:%SZ) \
docker buildx bake --push

# 3. na instância: puxar e subir
export COMPOSE_FILE=docker-compose.yml:docker-compose.prod.yml
docker compose pull && docker compose up -d
```

Alternativa sem SSH manual, útil quando a instância já está registrada como
contexto do Docker:

```bash
docker context create az1-prod --docker "host=ssh://ubuntu@<ip-da-instancia>"
docker --context az1-prod compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

Como as imagens carregam labels OCI, é possível descobrir de qual commit saiu um
contêiner em produção sem depender da memória de ninguém:

```bash
docker inspect --format '{{index .Config.Labels "org.opencontainers.image.revision"}}' az1/api:0.2.0
```

---

## 9. Banco de dados e permissões dos webhooks

O Compose inclui PostgreSQL 16 Alpine. Uma base local nova recebe `01_create_database.sql` e `06_webhook_permissions.sql`. A API aguarda o health check do banco e seleciona `DATABASE_URL`, depois `SUPABASE_DB_URL` e, sem as duas, `postgresql://az1:az1@postgres:5432/az1` para o receptor local. Ferramentas no host usam `localhost` pela porta publicada no override.

O receptor abre pool próprio e assume obrigatoriamente `az1_webhook`; o pool das consultas de usuário continua separado. Esse papel só pode inserir/ler eventos, atualizar sua conclusão e marcar a origem para varredura. Não recebe DELETE, alteração do corpo ou leitura dos segredos de integração.

Volumes existentes não reaplicam scripts de inicialização. Antes de iniciar o receptor atualizado, confira `SHOW server_version` e aplique as permissões sem apagar dados. A migração 06 exige PostgreSQL 16 ou superior:

```bash
docker compose exec -T postgres psql -U az1 -d az1 -v ON_ERROR_STOP=1 -v webhook_login=az1 < src/database/06_webhook_permissions.sql
```

Em outro ambiente, `webhook_login` deve ser o nome do usuário no DSN do receptor, mesmo que a migração seja executada por outro administrador. Se omitido, o script usa o usuário conectado. O receptor falha ao abrir o pool quando não consegue assumir `az1_webhook`; `/health` sozinho não verifica essas permissões.

A base relacional completa pode receber `02_initial_data.sql` e `03_rls_policies.sql`, que inclui a migração 06. O RAG usa `SUPABASE_DB_URL` com extensão vetorial; a imagem PostgreSQL local não instala pgvector. Testes destrutivos usam base dedicada indicada por `TEST_DATABASE_URL`.

---

## 10. Diagnóstico

| Sintoma | Causa provável | O que fazer |
|---|---|---|
| `docker compose up` falha com "required variable AUDIO_STORAGE_ACCESS_KEY" | Você está subindo o arquivo de produção sem as credenciais. | Defina `AUDIO_STORAGE_ACCESS_KEY` e `AUDIO_STORAGE_SECRET_KEY` no `.env`. É a proteção funcionando. |
| MinIO reinicia em laço e a API nunca sobe | Segredo com menos de 8 caracteres (ou chave com menos de 3). | `docker compose logs minio` mostra a recusa. Aumente `AUDIO_STORAGE_SECRET_KEY`. |
| Upload de áudio devolve 500 com `SignatureDoesNotMatch` | API e MinIO estão com valores diferentes: você editou o `.env` e usou `docker compose restart`, que reinicia o processo sem reler o arquivo. | `docker compose up -d`: ele detecta a mudança de configuração e recria os contêineres com os valores novos. |
| Interface responde, mas `/api/...` dá 502 | A API não subiu ou está unhealthy. | `docker compose ps` e `docker compose logs api`. |
| `analyze` devolve 500 | Modelo ausente em `resultados/`. | `docker compose --profile ml run --rm trainer`. O log do entrypoint avisa disso na subida. |
| Hot reload não dispara | inotify não atravessa o bind mount no Windows/macOS. | Confirme `WATCHFILES_FORCE_POLLING=1` e `VITE_USE_POLLING=1`. |
| nginx sobe mas a porta recusa conexão | `envsubst` não conseguiu gravar a conf. | O tmpfs de `/etc/nginx/conf.d` precisa de `uid=101,gid=101`. Já está no compose; se você editou, é aqui. |
| Porta já em uso | Outro serviço no host. | `AZ1_WEB_PORT=8090 docker compose up -d`. |
| Build lenta a cada alteração de código | Cache invalidado cedo demais. | Confira se você não acrescentou um `COPY . .` antes da instalação de dependências. |

Comandos úteis:

```bash
docker compose ps                          # estado e saúde de cada serviço
docker inspect --format '{{json .State.Health}}' az1-api-1 | jq
docker compose exec api python -c "import sklearn, spacy; print(sklearn.__version__)"
docker stats                               # consumo em tempo real
docker compose config                      # composição final, já interpolada
```

---

## 11. Tamanho das imagens

| Imagem | Tamanho |
|---|---|
| `az1/frontend` | ~75 MB |
| `az1/api` | ~1,2 GB |

O frontend é pequeno porque o Node fica só no estágio de build: a imagem final é
nginx Alpine mais a pasta `dist`.

A API é grande, e o peso está nas bibliotecas científicas, não na base:

```text
spacy   129 MB    scipy  109 MB    av.libs  72 MB    sklearn  49 MB
numpy    43 MB    blis    34 MB    av       32 MB    botocore 30 MB
```

O maior item é o spaCy (com `blis` e `thinc`, cerca de 180 MB), e ele **não é
usado pelo modelo que está em produção**: a configuração vencedora usa
tokenização por regex e stemming RSLP, ambos do NLTK. O spaCy só entra em cena
na lematização e na tokenização linguística, que são caminhos exercitados pelo
`experimento.py`.

A imagem carrega o spaCy assim mesmo porque ele está declarado como dependência
de núcleo no `pyproject.toml`, e a imagem deve refletir o contrato do pacote -
não uma versão podada que quebraria no dia em que alguém retreinasse o modelo
com lematização. Se o tamanho vier a incomodar (custo de ECR, tempo de pull no
deploy), o caminho correto é mover o spaCy para um extra opcional no
`pyproject.toml`, e não recortá-lo do Dockerfile:

```toml
[project.optional-dependencies]
pln-avancado = ["spacy>=3.7"]
```

Aí o estágio `trainer` instala `.[pln-avancado]` e o `runtime` não: uma
economia de ~180 MB com a dependência explícita, em vez de implícita.

---

## 12. Técnicas aplicadas

Resumo do que está em uso e onde procurar cada coisa.

| Técnica | Onde | Por quê |
|---|---|---|
| Build multi-estágio | ambos os Dockerfiles | Compilador, cache do pip e Node não chegam à imagem final. |
| Cache mounts do BuildKit | `docker/api/Dockerfile`, `docker/frontend/Dockerfile` | Rebuild reaproveita wheels e pacotes npm entre builds. |
| Camada de dependências separada do código | ambos | Editar um `.py` não refaz 700 MB de wheels. |
| Usuário sem privilégios | `api` (UID 10001), `frontend` (UID 101) | Nenhum processo roda como root. |
| Raiz somente-leitura + tmpfs | `docker-compose.yml` | A aplicação não escreve em disco; se tentar, falha visivelmente. |
| `cap_drop: ALL` e `no-new-privileges` | bloco `x-hardening` | Superfície mínima de kernel. |
| Healthcheck em toda a pilha | Dockerfiles + compose | `depends_on: service_healthy` ordena a subida de verdade. |
| `init: true` | bloco `x-hardening` | Sinais e zumbis tratados; `docker stop` não vira SIGKILL. |
| Tags de imagem fixas | `minio`, `mc`, `nginx`, `node`, `python` | A mesma composição sobe a mesma coisa em qualquer máquina. |
| Labels OCI | ambos os Dockerfiles | `docker inspect` responde de qual commit saiu a imagem. |
| `.dockerignore` por negação | raiz | `.env` e `*.pem` não entram no contexto nem por acidente. |
| Perfis | `trainer`, `tests` | Serviços auxiliares existem sem subir no dia a dia. |
| Redes segmentadas | `frontend`, `backend` | MinIO inalcançável de fora, por construção. |
| Volume nomeado | `az1_minio_data` | Dados sobrevivem a `down`; performance melhor que bind mount. |
| Limites de recurso | `docker-compose.prod.yml` | Um pico na API não derruba a instância inteira. |
| Rotação de logs | bloco `x-logging` | Log de contêiner esquecido não enche o disco. |
| Segredos por arquivo | `docker/api/entrypoint.sh` | Chave de API fora de `docker inspect`. |
| `exec` no entrypoint | `docker/api/entrypoint.sh` | O uvicorn recebe o SIGTERM e encerra as requisições em voo. |
| `buildx bake` multiarquitetura | `docker-bake.hcl` | A imagem do notebook ARM roda na instância x86. |
| Modelo treinado na build | estágio `trainer` | O artefato vem do dataset versionado, não do disco de alguém. |
