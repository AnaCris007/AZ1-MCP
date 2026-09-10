<p align='center'>
  <a href='https://www.inteli.edu.br/'>
    <img src='assets/inteli.png' alt='Inteli - Instituto de Tecnologia e Liderança' width='300'>
  </a>
</p>

# AZ1 

### **Grupo:** 1

## Integrantes

- [Ana Cristina Jardim](https://www.linkedin.com/in/ana-cristina-jardim/)
- [Felipe Simão](https://www.linkedin.com/in/felipefmsimao/)
- [Karol Barbosa Rocha](https://www.linkedin.com/in/karolbarbosarocha/)
- [Matheus Ferreira da Silva](https://www.linkedin.com/in/matheusferreirads-/)
- [Paulo Henrique Bueno Fernandes](https://www.linkedin.com/in/paulo-henrique0601/)
- [Rui Facó](https://www.linkedin.com/in/ruifac%C3%B3/)
- [Tobias Viana](https://www.linkedin.com/in/tobias-viana/)

## Orientadora

- [Vanessa Nunes](https://www.linkedin.com/in/vanunes/)


### Instrutores
- <a href="https://www.linkedin.com/in/reginaldo-arakaki-9574222b/">Computação - Reginaldo Arakaki</a>
- <a href="https://www.linkedin.com/in/bryan-kano/">Computação - Bryan Kano</a>
- <a href="https://www.linkedin.com/in/fernando-pizzo-208b526a/">Matemática e Física - Fernando Pizzo</a>
- <a href="https://www.linkedin.com/in/lisane-valdo/">Negócios - Lisane Valdo</a>
- <a href="https://www.linkedin.com/in/bruno-grandchamp-rodilha/?locale=pt">Design - Bruno Rodilha</a> 
- <a href="https://www.linkedin.com/in/filipe-gon%C3%A7alves-08a55015b/">Liderança - Filipe Gonçalves</a>

##  Descrição

O **AZ1** é um agente inteligente de apoio à gestão do portfólio de projetos do PMO Corporativo do Metrô de São Paulo. Por meio de uma interface conversacional, o produto interpreta solicitações em linguagem natural para facilitar a consulta, a interpretação, a comparação e o acompanhamento de informações sobre documentos, prazos, marcos, riscos, pendências e avanço dos empreendimentos.

Além de responder a consultas, o AZ1 apoia o acompanhamento preventivo do portfólio com alertas e sugestões de preenchimento, reduzindo o esforço manual das equipes e contribuindo para análises e decisões mais ágeis. O MVP utiliza dados sintéticos e preserva os processos, as permissões e a rastreabilidade existentes, sem substituir os sistemas corporativos nem o julgamento dos profissionais responsáveis.

##  LINKS

- [Índice da documentação](docs/Index.md)
- [Documentação principal do projeto](docs/Projeto.md)

##  Estrutura de pastas

```text
.
├── assets/
│   ├── design/
│   └── negócios/
├── docker/
│   ├── api/         # Dockerfile e entrypoint da API
│   └── frontend/    # Dockerfile e configuração do nginx
├── docs/
│   ├── Docker.md
│   ├── GestaoConfiguracao.md
│   ├── GestaoProjeto.md
│   ├── Index.md
│   └── Projeto.md
├── infra/
│   └── minio/       # regra de ciclo de vida do bucket de áudio
├── resultados/      # comparativos e modelo treinado, saída gerada
├── src/
│   ├── database/    # scripts SQL
│   ├── frontend/    # interface em React + Vite
│   ├── pln/         # pipeline de linguagem natural
│   ├── routes/      # endpoints da API (FastAPI)
│   ├── schemas/     # contratos de entrada da API
│   ├── services/    # casos de uso e adaptadores externos
│   └── az1_api/     # composição e ponto de entrada da API
├── tests/
├── .dockerignore
├── .env.example
├── .gitignore
├── docker-bake.hcl            # build paralela e multiarquitetura
├── docker-compose.yml         # composição base
├── docker-compose.override.yml # desenvolvimento (carregado automaticamente)
├── docker-compose.prod.yml    # produção
├── Makefile
├── pyproject.toml
├── README.md
├── requirements.txt
└── ruff.toml
```

##  Como executar

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e .
python -m nltk.downloader stopwords rslp
python -m spacy download pt_core_news_sm
python -m spacy download pt_core_news_md
```

```bash
python -m pln.experimento          # varre pré-processamento e vetorização
python -m pln.ajuste_fino          # varre os hiperparâmetros do modelo
python -m pln.classificador        # treina, avalia e salva o modelo
python -m unittest discover tests  # 106 testes
```

- `assets/`: imagens e diagramas utilizados na documentação.
- `docs/`: documentação principal do projeto e de sua gestão.
- `src/pln/`: o pipeline de linguagem natural, [documentação técnica](docs/Projeto.md#33-algoritmo-de-nlp-e-implementação).
- `src/schemas/`: contratos de entrada da API.
- `src/database/`: scripts SQL para criação e carga inicial do banco de dados.
- `src/routes/`: endpoints da API (FastAPI).
- `src/schemas/`: modelos Pydantic de request/response da API.
- `src/services/`: casos de uso e integração com armazenamento S3-compatível.
- `src/az1_api/main.py`: ponto de entrada da aplicação FastAPI.
- `resultados/`: saída gerada. Nada ali é editado à mão. Os comparativos vêm de
  `python -m pln.experimento` e `python -m pln.ajuste_fino`, e o modelo treinado de
  `python -m pln.classificador`.

##  Rodando com Docker

A pilha inteira — interface, API, armazenamento de áudio e criação do bucket — sobe com um comando. É o caminho recomendado: não exige Python, Node nem MinIO instalados na máquina, e é o mesmo empacotamento que vai para a nuvem.

```bash
cp .env.example .env      # preencha DEEPGRAM_API_KEY e GEMINI_API_KEY
docker compose up -d --build
```

| Endereço | O quê |
|---|---|
| http://localhost:5173 | interface, com recarga automática |
| http://localhost:8010/docs | documentação interativa da API (Swagger) |
| http://localhost:9001 | console do MinIO (as chaves `AUDIO_STORAGE_*` do seu `.env`) |

O código do repositório é montado dentro dos contêineres: editar um arquivo recarrega a API ou a interface, sem reconstruir imagem.

```bash
docker compose --profile ci run --rm tests      # os 145 testes, dentro da imagem
docker compose --profile ml run --rm trainer    # retreina o classificador
docker compose logs -f api                      # acompanha os logs
docker compose down                             # derruba, preservando os áudios
```

Para subir em modo produção — interface na porta 80, API e MinIO fechados na rede interna, limites de recurso e credenciais obrigatórias:

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

A [documentação de Docker](docs/Docker.md) detalha a topologia, as variáveis de ambiente, o uso de segredos, a build multiarquitetura e o processo de deploy.

##  Rodando a API sem Docker

O endpoint de recebimento de áudio armazena os arquivos em um bucket S3-compatível. Para desenvolvimento local, suba apenas o MinIO (já com o bucket `az1-audio` criado automaticamente):

```bash
docker compose up -d minio minio-init
```

Depois, com o projeto instalado por `pip install -e .`, rode a API normalmente:

```bash
uvicorn az1_api.main:app --reload
```

A documentação interativa (Swagger) fica disponível em `http://127.0.0.1:8000/docs`. O console do MinIO fica em `http://127.0.0.1:9001`, com o usuário e a senha definidos em `AUDIO_STORAGE_ACCESS_KEY` e `AUDIO_STORAGE_SECRET_KEY` no `.env` — as mesmas chaves com que a API assina as requisições S3.

Os arquivos são armazenados com a chave `incoming/{audio_id}` e expiram automaticamente após sete dias. O componente de Speech-to-Text recebe o `audio_id` do orquestrador e recupera o objeto diretamente do bucket `az1-audio`; esta API não oferece endpoint de download nem inicia a transcrição.

Antes de expor o endpoint fora de uma rede controlada, será necessário definir autenticação, rate limiting e um limite de corpo no gateway ou proxy. Nesta etapa do MVP, a API é interna e não exige autenticação.

##  Configuração para desenvolvimento

Para configurar o desenvolvimento da aplicação, [instale o git](https://git-scm.com/downloads) e clone esse repositório em seu computador através do comando:

```
git clone https://git.inteli.edu.br/graduacao/2026-2a/t17/g01
```

##  Histórico de lançamentos

* 0.1.0 - 14/08/2026
    * Artefato - Entendimento do negócio
    * Artefato - Especificação de requisitos funcionais e não funcionais
    * Artefato - Gestão de projeto e configuração
* 0.2.0 - DD/MM/2026
    * Artefato
    * Artefato
* 0.3.0 - DD/MM/2026
    * Artefato
    * Artefato
* 0.4.0 - DD/MM/2026
    * Artefato
    * Artefato
* 0.5.0 - DD/MM/2026
    * Artefato
    * Artefato

## 📋 Licença/License

O [AZ1](https://git.inteli.edu.br/graduacao/2026-2a/t17/g01) foi desenvolvido pelo [Inteli](https://www.inteli.edu.br/) e por [Ana Cristina Jardim](https://www.linkedin.com/in/ana-cristina-jardim/), [Felipe Simão](https://www.linkedin.com/in/felipefmsimao/), [Karol Barbosa Rocha](https://www.linkedin.com/in/karolbarbosarocha/), [Matheus Ferreira da Silva](https://www.linkedin.com/in/matheusferreirads-/), [Paulo Henrique Bueno Fernandes](https://www.linkedin.com/in/paulo-henrique0601/), [Rui Facó](https://www.linkedin.com/in/ruifac%C3%B3/) e [Tobias Viana](https://www.linkedin.com/in/tobias-viana/).

Este projeto está licenciado sob a [Licença Creative Commons Atribuição 4.0 Internacional](https://creativecommons.org/licenses/by/4.0/).
