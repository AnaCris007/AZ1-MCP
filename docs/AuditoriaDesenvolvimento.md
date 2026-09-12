# Auditoria do desenvolvimento da solução

Data do registro: 11/09/2026. Base inspecionada: `develop`, commit `e083074`. Branch de trabalho: `fix/auditoria-desenvolvimento-solucao`.

A revisão local atende aos testes executados da Sprint 3, com ressalvas documentais e operacionais explícitas. Isso não representa aceite coletivo, nota atribuída pelo professor ou prontidão da base Supabase para os receptores. A estratégia da Seção 3.8 de `Projeto.md`, a gestão da Sprint 3 e o histórico local sustentam esse enquadramento. Webhooks, banco e integração de tarefas foram desenvolvidos antecipadamente. Mensageria e consolidação da interface pertencem à Sprint 5; implantação em nuvem começa na Sprint 4.

## Escopo e evidência

Foram conferidos os contratos das rotas, adaptadores de áudio e voz, classificador de intenções, RAG, persistência, frontend, webhooks, scripts SQL, Compose, Dockerfiles, pipeline e documentação. As verificações automáticas percorreram todo `src` e `tests`. A inspeção documental inclui referências locais, marcadores de preenchimento, pontuação e reconciliação do modelo físico. O foco de regressão inclui os cinco achados de código, a perda de conteúdo na primeira revisão documental, as frases quebradas, a delimitação do TI-37 e a preparação dos bancos.

Os resultados locais abaixo não equivalem a homologação com o parceiro, execução real de Microsoft Entra ID/Graph, transcrição no Deepgram ou publicação em nuvem. O ambiente PostgreSQL da suíte foi criado sem rede externa, com armazenamento temporário e dados sintéticos, separado das bases existentes. Depois da validação descartável, a migração 06 foi aplicada ao desenvolvimento com comparação de conteúdo antes e depois. O Supabase recebeu somente consultas de versão e papéis.

## Matriz de consistência e correções

| Conceito | Estado encontrado | Implementação e documentação reconciliadas | Evidência |
|---|---|---|---|
| Aviso OneDrive | Exigia `changeType` e identificação de item | Aceita o aviso mínimo, verifica ambas as grafias de expiração e usa UUID por recebimento quando não há identidade de evento/versão | `TestAvisosOneDrive` e teste real após limpar a marca de varredura |
| Identidade de evento | Item isolado usado como chave | ID do evento ou item com etag; sem ambos, efeito repetível e auditoria por recebimento | Testes de versões e notificações sucessivas |
| Banco do Compose | Seleção implícita e manual operacional desatualizado | API seleciona base explicitamente, com fallback `postgres:5432`, e aguarda health check | Configuração base e produção validadas |
| Banco das CLIs | Fallback local diferente do receptor | `DATABASE_URL`, depois `SUPABASE_DB_URL`; fallback local somente para operação no host | `TestConfiguracaoWebhook` |
| Empréstimo de conexão | Erro antes da reivindicação deixava conexão retida | Rollback/fechamento e devolução em `finally`; transferência explícita para a reivindicação | Seis falhas consecutivas, falhas de SELECT, rollback e commit |
| Configuração de pool | `SET ROLE` deixava transação aberta | Commit ao concluir o callback de configuração | Pool real com `az1_webhook` |
| Privilégios de webhook | REVOKE de PUBLIC não limitava o proprietário | Pool separado com papel obrigatório, grants por coluna e RLS | INSERT/conclusão permitidos; DELETE, TRUNCATE, mudança de corpo e leitura de segredo recusados |
| Abertura de canal | UPSERT sobrescrevia canal ativo | Condição atômica impede substituir origem ativa; compensação restrita à nova reserva | Testes de CLI e PostgreSQL |
| Carga relacional | Consultava índice vetorial inexistente | Carga e verificações relacionais executam antes do RAG; comparação vetorial ocorre quando há índice | Logs SQL |
| Smoke HTTP isolado | `curl /health` e POST do aviso mínimo OneDrive | `200` e `202`, respectivamente, com assinatura sintética e PostgreSQL real | [Log](evidencias/auditoria-desenvolvimento/smoke-http.txt) |
| Modelo físico | Texto omitia tabela de eventos e colunas novas | Definições SQL sincronizadas; verificador inclui `integracao` | Comparação entre documento, DDL e banco |
| Fontes do chat | Texto dizia resposta apenas com `reply` | Documenta `fontes`, seleção de citações, exibição de trechos e recusa sem fundamento | Testes de chat e Gemini existentes |
| Tarefas e agenda | Texto dizia rotas inexistentes; erros só no console | Documenta rotas reais; telas distinguem carregamento, vazio e erro; tarefa muda imediatamente, reverte em falha e bloqueia somente sua própria gravação | Seis testes de tarefas/agenda, incluindo concorrência entre tarefas |
| Deploy | Exemplo proposto competia com Dockerfiles existentes | Manual usa arquivos executáveis, separa local de nuvem e recupera UML, nós, caminhos, fluxos, mapeamento e cinco passos EC2 | Build local, figura renderizada e conteúdo recuperado da base develop |
| Banco existente | Papel obrigatório ainda ausente | Migração local aplicada; Supabase 17.6 compatível, mas sem az1_webhook | [Verificação dos bancos](evidencias/auditoria-desenvolvimento/bancos-revisao.txt) |
| TI-37 | Matriz prometia execução única para qualquer aviso | Garantia restrita a identificadores estáveis; aviso mínimo OneDrive gera outra linha e outra execução | Matriz, manual Graph, comentários SQL e COMMENT ON TABLE corrigidos |
| Gestão | Fotografia parcial anterior aos últimos merges | Acréscimo de reconciliação técnica com os commits locais, preservando cortes históricos e datas comprovadas | `GestaoProjeto.md`, Seção 5.2 |

## Rastreabilidade do código integrado

| Requisito | Componente / arquivo | Contrato | Persistência | Teste | Sprint |
|---|---|---|---|---|---|
| RF01 | `services/audio_service.py`, `routes/audio.py` | `POST /api/v1/audio` | Objeto `incoming/{id}` em S3/MinIO | `test_audio_service.py`, `test_audio_api.py`, `test_storage_service.py` | 3 |
| RF01, RNF06 | `services/transcription_service.py` | `POST /api/v1/audio/{audio_id}/transcribe` | Recupera objeto armazenado | `test_transcription_service.py`, `test_transcription_api.py` | 3 |
| RNF03 | `pln/classificador.py`, `services/analysis_service.py` | `POST /api/v1/audio/{audio_id}/analyze` | Artefato do classificador | Testes de PLN, análise e reprodutibilidade | 3 |
| RF01, RF02, RF03, RNF12 | `services/gemini_service.py`, `routes/chat.py` | `POST /api/v1/chat` | RAG e `auditoria.mensagem_fonte` | `test_gemini_service.py`, `test_chat_api.py` | 3, com avanço de 4 |
| RF01 | `routes/speech.py` | `POST /api/v1/text-to-speech` | WAV devolvido ao cliente | `test_speech_api.py`, `test_gemini_speech_service.py` | 3 |
| RNF02 | `services/auth_service.py` | Bearer validado nas rotas protegidas | Ponte `portfolio.usuario` | `test_auth_api.py`, `test_auth_service.py` | 3, antecipação |
| RF02, RF05 | `routes/portfolio.py`, `services/portfolio_repository.py` | `GET /api/v1/projetos`, `GET/PATCH /api/v1/tasks` | `portfolio` | `test_portfolio_api.py`, `test_portfolio_repository.py` | 4, antecipação |
| RF02 | `routes/portfolio.py`, `CalendarView.jsx` | `GET /api/v1/calendar/events` | Projetos e prazos de pendências | Testes de portfólio e `CalendarView.test.jsx` | 4, antecipação |
| RF01, RF03 | `AgentPage.jsx`, `ChatMessage.jsx`, `lib/api.js` | Texto, gravação, transcrição, fontes e reprodução | Estado React e APIs | `AgentPage.test.jsx`, `api.test.js`, `useMicVolume.test.js` | 3; consolidação em 5 |
| RNF04, RNF09 | `services/conversa_repository.py` | Gravação lateral do chat | Conversa, mensagem e fonte | `test_conversa_repository.py` | 4, antecipação |
| TI-35 a TI-40 e dois casos locais de lote | `graph_push_service.py`, `drive_push_service.py` | `POST /api/v1/webhooks/microsoft`, `/google` | Evento e origem | Contrato comum, HTTP, PostgreSQL e novas regressões | 4, antecipação |
| RNF09 | `06_webhook_permissions.sql` | Papel `az1_webhook` | RLS e grants por coluna | `TestPermissoesWebhook` | 4, antecipação |
| Integração futura | `ProcessadorVarreduraPendente` | Marca `delta_pendente` após notificação | `integracao.conexao` | Testes do processador | Fundação de 5 |

A evidência comum das linhas testadas é a [execução Python](evidencias/auditoria-desenvolvimento/backend.txt) ou a [execução frontend](evidencias/auditoria-desenvolvimento/frontend.txt). Os testes de serviços externos usam dublês, exceto a persistência PostgreSQL explicitamente indicada.

## Validações executadas

| Verificação | Comando principal | Resultado | Evidência |
|---|---|---|---|
| Backend | `python -m unittest discover -v tests` | 489 testes aprovados, zero falhas e zero ignorados, com `TEST_DATABASE_URL` dedicado | [Log](evidencias/auditoria-desenvolvimento/backend.txt) |
| Compilação e lint Python | `python -m compileall -q src tests`; `ruff check --no-cache src tests` | Aprovados na imagem Python do projeto | [Log](evidencias/auditoria-desenvolvimento/backend.txt) |
| Frontend | `npm test` | 18 testes aprovados em cinco arquivos | [Log](evidencias/auditoria-desenvolvimento/frontend.txt) |
| Build frontend | `npm run build` | Aprovado; Vite avisou sobre bundle acima de 500 kB | [Log](evidencias/auditoria-desenvolvimento/frontend.txt) |
| Lint frontend | `npm run lint` | Zero erros e zero avisos em `src` | [Log](evidencias/auditoria-desenvolvimento/frontend.txt) |
| Build API | `docker build --target dev -f docker/api/Dockerfile -t az1/auditoria-api:local .` | Imagem local construída e API importada | [Build](evidencias/auditoria-desenvolvimento/build-api.txt), [importação](evidencias/auditoria-desenvolvimento/importacao-api.txt) |
| DDL e carga | `psql -v ON_ERROR_STOP=1 -f ...` | Criação, carga sintética e políticas executadas | [Log](evidencias/auditoria-desenvolvimento/criacao-carga-permissoes.txt) |
| Migração | Reaplicação de `06_webhook_permissions.sql` com `webhook_login` distinto do administrador | Aprovada; associação com INHERIT FALSE e SET TRUE confirmada | [Log](evidencias/auditoria-desenvolvimento/migracao-reaplicada.txt) |
| Desenvolvimento | Migração 06 e verificação pelo pool real | Papel restrito e RLS ativos; registros preservados; escritas de verificação revertidas | [Log sanitizado](evidencias/auditoria-desenvolvimento/bancos-revisao.txt) |
| Integridade relacional | `04_verificacao.sql` | Restrições exercitadas e rollback final; etapa vetorial condicionada à existência do índice | [Log](evidencias/auditoria-desenvolvimento/verificacao-relacional.txt) |
| Smoke HTTP isolado | `curl /health` e POST do aviso mínimo OneDrive | `200` e `202`, respectivamente, com assinatura sintética e PostgreSQL real | [Log](evidencias/auditoria-desenvolvimento/smoke-http.txt) |
| Modelo físico | `python scripts/verificar_modelo_documentado.py` | 16 tabelas e 132 colunas coincidentes entre documento, DDL e banco | [Log](evidencias/auditoria-desenvolvimento/modelo-documentado.txt) |
| Compose | `config --no-env-resolution` para base e produção | Configuração válida; API com destino interno e dependência saudável | Conferência estrutural da configuração |

As execuções usaram imagens locais com as dependências declaradas. O ambiente virtual do host tinha versões divergentes e ausência de `jwt`; a instalação frontend do host não tinha Vitest. Esses ambientes não foram usados para afirmar aprovação. Nenhum segredo local foi necessário para os testes isolados. Os resultados publicados são contagens de testes, sem inferir percentual de cobertura.

## Checklist por sprint

| Critério | Sprint exigida | Estado verificado nesta auditoria |
|---|---|---|
| API de áudio, formatos, validação de conteúdo, tamanho e duração | 3 | Implementados; WAV, MP3, M4A e WebM, 10 MiB, cinco minutos; cenários positivos e negativos aprovados |
| Erros, armazenamento e referência segura de áudio | 3 | Implementados e testados; armazenamento S3/MinIO e identificador gerado pela aplicação |
| Início do NLP, algoritmo, métricas e exemplos | 3 | Classificador Naive Bayes e pipeline modular presentes; suíte e pins conferidos |
| Speech to Text e síntese de fala | 3 | Adaptadores implementados; contratos verificados com dublês dos provedores |
| Frontend básico, integração e feedback | 3 | Fluxo de texto e áudio com revisão de transcrição, resposta, fontes e reprodução; erros de tarefas/agenda corrigidos |
| Documentação e rastreabilidade da entrega | 3 | Contratos, modelo físico, diagramas de composição e manual reconciliados |
| Dois webhooks, rotas, payloads e validação | 4 | Antecipados; Graph e Drive com contrato HTTP testado |
| Processamento, persistência e repetição de webhook | 4 | Antecipados; marca de varredura e auditoria com PostgreSQL real |
| Início do banco, tabelas, índices, modelos e scripts | 4 | Antecipados; DDL, carga, políticas e verificações locais executados |
| Início do deploy, ambientes, scripts e manual | 4 | Empacotamento local executado; nuvem é a estratégia da próxima sprint |
| Mensageria, produtor, consumidor, repetição e integração com webhook | 5 | Planejados; envelope e marca de varredura constituem a fundação implementada |
| Frontend completo, responsividade e acessibilidade | 5 | Consolidação planejada; testes de componentes verificam parte do comportamento atual |
| Integração completa e falhas de comunicação | 5 | Consolidação planejada; integração local de contratos já exercitada |
| Testes e cobertura | Transversal | Contagens executadas publicadas; nenhuma porcentagem atribuída sem medição |
| Segurança | Transversal | Privilégios de webhook testados; configurações administrativas continuam distintas da sessão restrita |
| Coerência e reprodutibilidade | Transversal | Docker, scripts SQL e modelo físico confrontados com o código |
| Ortografia, travessões e marcadores de preenchimento | Transversal | Trechos afetados pela substituição de pontuação revistos em contexto, inclusive decisões 8 a 11 e 14, apresentações de tabelas e descrições de figuras |

## Revisão documental e inventário

A primeira revisão reduziu a Seção 3.7 e removeu conteúdo técnico útil; o resumo anterior não descrevia essa perda. Esta revisão recupera o UML original, a descrição dos nós, os caminhos C1 a C12 (com C13 para webhooks), três fluxos ponta a ponta, o mapeamento lógico para físico e os cinco passos de EC2 com as capturas históricas. Mantém o enquadramento atual: Dockerfiles e execução local existem; implantação pública, ECR e CloudWatch não foram comprovados. O SVG é uma referência histórica, com suas diferenças para a implementação descritas nas tabelas. A [captura da inspeção no navegador](evidencias/auditoria-desenvolvimento/diagrama-uml-revisado.png) confirma a figura inteira, inclusive o nó externo de LLM.

A pontuação foi revista nos trechos afetados: apartes em parênteses, decisões com título separado da explicação, duas frases indevidamente unidas, descrições das tabelas e texto alternativo da figura de componentes. A verificação automática de links e marcadores é complementar; ela não certifica legibilidade nem substitui revisão por pares. O diff não altera arquivos `README.md`.

O [inventário de arquivos](evidencias/auditoria-desenvolvimento/arquivos-alterados.txt) lista os arquivos alterados ou acrescentados nesta branch. A [verificação documental](evidencias/auditoria-desenvolvimento/documentacao.txt) registra referências locais, âncoras, blocos e sinais de pontuação procurados. Links externos autenticados não foram certificados por essa conferência.

## Ressalvas antes do MR e da operação

- **Base compartilhada:** o Supabase configurado usa PostgreSQL 17.6 e o usuário `postgres`, mas ainda não tem `az1_webhook`. Antes de apontar o receptor atualizado para essa base, o administrador precisa aplicar `06_webhook_permissions.sql` com `webhook_login=postgres`. A conferência de versão não substitui essa migração. Nenhuma permissão ou dado do Supabase foi alterado nesta revisão.
- **TI-37:** avisos mínimos OneDrive não atendem à execução única do contrato original. Geram duas linhas e duas execuções se recebidos duas vezes; marcar `delta_pendente = TRUE` duas vezes preserva o estado. A matriz registra expressamente esse limite. Os nomes TI-41/TI-42 usados pelos testes locais de lote de webhook não comprovam os testes de mensageria de mesmos IDs no catálogo.
- **Aceite coletivo:** ainda falta a evidência humana apontada pelo professor. Não foi produzida nem inferida a partir de testes, commits ou alteração do contrato.
- **Indicadores:** a consulta de milestones e MRs pela API GitLab retornou HTTP 401 na auditoria inicial. Os indicadores conservam o corte histórico e precisam ser atualizados depois do encerramento dos MRs, com evidência desse estado.
- **Riscos:** datas comprovadas de versionamento continuam distintas das datas reais de mudança. Datas sem registro não foram inventadas.
- **Interface:** a situação de tarefa tem atualização otimista com reversão; o modal continua oferecendo campos além dos persistidos pelo contrato atual da API. A consolidação desse fluxo permanece uma limitação da interface.

## Reprodução dos resultados isolados

A suíte PostgreSQL é destrutiva e deve receber uma base exclusiva de teste, criada com os scripts do repositório. A execução registrada usou um contêiner PostgreSQL 16 Alpine com armazenamento temporário e uma imagem da API com o código montado para leitura. `PYTHON_DOTENV_DISABLED=1` impediu carregar configurações locais nos testes. `TEST_DATABASE_URL` selecionou somente a base descartável; essa variável não foi confundida com a base da aplicação.

A migração de permissões exige PostgreSQL 16 ou superior e deve anteceder a atualização do receptor em ambientes existentes: o código assume `az1_webhook` e falha quando esse papel não está disponível. `03_rls_policies.sql` inclui a migração 06 em instalações novas. As CLIs administrativas não compartilham a sessão restrita dos webhooks.

A revisão de MRs e os indicadores de gestão conservam o corte histórico. Os commits `024a5bf`, `b23f276` e o merge `e083074` comprovam evolução técnica local; não substituem aceite humano ou o histórico completo de atividades no GitLab.
