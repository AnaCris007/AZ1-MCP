# Reprodução da campanha funcional

Rodar na raiz do repositório, com Docker Desktop iniciado. Não utilizar `.env`
nem o banco Supabase compartilhado. Os nomes `az1-functional-*` identificam
recursos dedicados; se já existirem, confira se pertencem a esta campanha antes
de reutilizar. As credenciais abaixo são exclusivamente locais e sintéticas.
O banco de regressão recebe testes destrutivos, por isso nunca substitua sua
URL por `DATABASE_URL` ou `SUPABASE_DB_URL`.

```bash
mkdir -p docs/evidencias/testes-funcionais
docker build --target dev -f docker/api/Dockerfile -t az1/funcionais:local .
docker network create az1-functional-test
docker run -d --name az1-functional-postgres --network az1-functional-test \
  -e POSTGRES_PASSWORD=functional-test-only -e POSTGRES_DB=az1_test postgres:16-alpine
docker run -d --name az1-functional-minio --network az1-functional-test \
  -e MINIO_ROOT_USER=functional-test -e MINIO_ROOT_PASSWORD=functional-test-only \
  quay.io/minio/minio:RELEASE.2025-09-07T16-13-09Z server /data
docker cp src/database az1-functional-postgres:/tmp/az1-database
docker exec az1-functional-postgres psql -U postgres -d az1_test -v ON_ERROR_STOP=1 -f /tmp/az1-database/01_create_database.sql
docker exec az1-functional-postgres psql -U postgres -d az1_test -v ON_ERROR_STOP=1 -f /tmp/az1-database/02_initial_data.sql
docker exec az1-functional-postgres psql -U postgres -d az1_test -v ON_ERROR_STOP=1 -f /tmp/az1-database/03_rls_policies.sql
```

Esperar PostgreSQL/MinIO ficarem disponíveis antes de executar. A imagem
`minio/minio` configurada no Compose não pôde ser baixada nesta campanha;
registrou-se o erro e usou-se a mesma release no registro Quay. Não se alterou
a composição de implantação durante esta tarefa.

```bash
docker run --rm --network az1-functional-test --entrypoint python \
  -e PYTHON_DOTENV_DISABLED=1 \
  -e TEST_DATABASE_URL=postgresql://postgres:functional-test-only@az1-functional-postgres:5432/az1_test \
  -v "$PWD/src:/app/src:ro" -v "$PWD/tests:/app/tests:ro" \
  -v "$PWD/docs:/app/docs:ro" -v "$PWD/infra:/app/infra:ro" \
  -v "$PWD/requirements.txt:/app/requirements.txt:ro" \
  az1/funcionais:local -m unittest discover -s tests -v \
  > docs/evidencias/testes-funcionais/backend.log 2>&1
docker run --rm --network az1-functional-test --entrypoint python \
  -e PYTHON_DOTENV_DISABLED=1 \
  -e TEST_COMMIT=preencher-com-o-hash-do-commit-candidato \
  -v "$PWD/src:/app/src:ro" -v "$PWD/scripts:/app/scripts:ro" \
  -v "$PWD/docs:/app/docs" az1/funcionais:local \
  scripts/executar_testes_funcionais.py \
  > docs/evidencias/testes-funcionais/funcionais.log 2>&1
python3 scripts/consolidar_testes_funcionais.py
```

`executar_testes_funcionais.py` retorna 0 quando as variantes passam, 1 para
reprovações e 2 para erro do instrumento. Reprovação não deve interromper a
consolidação. JSON registra todas as variantes realizadas; CSV/Markdown
agregam por ID. Alterações de scripts após uma execução exigem rodada nova.
A aprovação controlada não comprova provedores reais, login SSO, microfone ou
integração vetorial. A regressão não substitui os casos funcionais.

```bash
cd src/frontend
npm ci
npm test -- --reporter=default --reporter=json --outputFile=../../../docs/evidencias/testes-funcionais/frontend.json > ../../../docs/evidencias/testes-funcionais/frontend.log 2>&1
npm run build > ../../../docs/evidencias/testes-funcionais/frontend-build.log 2>&1
npm run lint > ../../../docs/evidencias/testes-funcionais/frontend-lint.log 2>&1
```

As execuções desta rodada utilizaram as dependências frontend já instaladas;
`npm ci` acima prepara uma máquina limpa. Encerrar somente os serviços dedicados
com `docker stop az1-functional-minio az1-functional-postgres`. Preservar logs,
JSON, manifestos e registros de defeitos antes de uma nova rodada.

## Ensaio de navegador com backend indisponível

Iniciar o frontend na porta 5175 com Supabase fictício; não iniciar a API na
porta 8010. Abrir `http://127.0.0.1:5175/tests/functional.html` no Chrome,
digitar `Qual o status do SYN-01?` e acionar Enviar mensagem. O harness monta
`AgentPage`/`AuthProvider` reais sem a tela Gate; não é teste de SSO nem deve ser
utilizado como rota de produção. A build Vite normal não inclui esse HTML.

```bash
VITE_SUPABASE_URL=http://127.0.0.1:59999 VITE_SUPABASE_ANON_KEY=functional-local-only npm run dev -- --host 127.0.0.1 --port 5175
```

Observar mensagem de erro, ausência de resposta fictícia e ECONNREFUSED no log
Vite. Capturar somente a área da aplicação, sem contas/abas privadas. A rodada
registrada foi controlada via CUA no Chrome nativo. Depois de produzir
`frontend.json`, retornar à raiz e executar novamente a consolidação.
