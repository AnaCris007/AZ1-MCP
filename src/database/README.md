# Banco de dados relacional do AZ1

Esta pasta contém o modelo físico da solução, e é a fonte de verdade dele. A
[Seção 3.6 do `docs/Projeto.md`](../../docs/Projeto.md#36-modelagem-conceitual-e-lógica-dos-dados)
apresenta os modelos conceitual, lógico e físico com a justificativa de cada
decisão; o que o modelo atual mudou em relação à modelagem da Sprint 2 está em
[Evolução em relação à modelagem da Sprint 2](#evolução-em-relação-à-modelagem-da-sprint-2).

## Os dois bancos da solução

A solução guarda dados em dois lugares, e a distinção importa para não procurar
informação no lado errado:

| | Onde | O quê | Quem escreve |
|---|---|---|---|
| **Vetorial** | `vecs.documentos_metro` | Conteúdo dos documentos, em chunks com embedding de 3072 dimensões | `src/rag/indexador.py` |
| **Relacional** | schemas `portfolio` e `auditoria` | Identidade, domínio do portfólio, conversas, auditoria, avaliações | scripts desta pasta e a camada de serviços |

**Os dois vivem no mesmo banco PostgreSQL** — o projeto Supabase apontado por
`SUPABASE_DB_URL`. Isso é deliberado: é o que permite ligar uma resposta do
agente ao chunk que a fundamentou (`auditoria.mensagem_fonte`) sem consulta
cruzada entre servidores, condição dos RNF04, RNF11 e RNF12. A decisão fecha o
item 1 da Seção 3.7.9 do `docs/Projeto.md`, que estava em aberto.

## Executar

Os scripts são numerados e devem rodar em ordem. `SUPABASE_DB_URL` é a
connection string direta do PostgreSQL, a mesma que o pipeline de RAG usa.

```bash
cd src/database
set -a && source ../../.env && set +a

psql "$SUPABASE_DB_URL" -X -v ON_ERROR_STOP=1 -f 01_create_database.sql
psql "$SUPABASE_DB_URL" -X -v ON_ERROR_STOP=1 -f 02_initial_data.sql
psql "$SUPABASE_DB_URL" -X -v ON_ERROR_STOP=1 -f 03_rls_policies.sql
psql "$SUPABASE_DB_URL" -X -f 04_verificacao.sql   # sem ON_ERROR_STOP: ver abaixo
```

| Script | O que faz |
|---|---|
| `01_create_database.sql` | Schemas, tabelas, restrições, índices, gatilho, visões e a proteção da trilha de auditoria |
| `02_initial_data.sql` | Carga da base sintética. Reexecutável: limpa antes de inserir |
| `03_rls_policies.sql` | Papel da aplicação, ponte com o SSO e Row Level Security |
| `04_verificacao.sql` | Exercita o caminho de escrita e prova que o banco recusa dado incoerente. Termina em `ROLLBACK` |

Fora desta pasta, `scripts/verificar_modelo_documentado.py` confere se a Seção 3.6.6 do `docs/Projeto.md`, o `01_create_database.sql` e o banco em execução descrevem o mesmo modelo.

O `04_verificacao.sql` roda **sem** `-v ON_ERROR_STOP=1` de propósito: a segunda
metade provoca erros para verificar que as restrições reagem. Cada bloco deve
imprimir `RECUSADO (ok)`; um `ACEITOU` significa que uma restrição se perdeu.

## Estrutura

### Schema `portfolio` — dados operacionais

```
portfolio ──< projeto ──< artefato ──< campo_artefato
                 │  │
                 │  └──< pendencia
                 │
     usuario ────┴──< usuario_projeto
                      projeto_relacionado (projeto ↔ projeto)
```

`usuario` traz a coluna `auth_user_id`, hoje nula. É por ali que a frente de
autenticação vai amarrar cada pessoa à sua conta de SSO — ver
[Ganchos para a autenticação](#ganchos-para-a-autenticação).

### Schema `auditoria` — trilha de uso

```
conversa ──< mensagem ──< mensagem_fonte ──> artefato (opcional)
    │            │
    │            └──< avaliacao
    └──< evento_plataforma

pendencia ──< notificacao ──> usuario
```

O ponto central é `mensagem`: **uma linha por turno**, não por par
pergunta-resposta. O prompt e a resposta são linhas irmãs na mesma conversa,
distinguidas por `papel` (`usuario` ou `agente`) e ordenadas por `ordem`. Ler
a conversa inteira é `ORDER BY ordem`; ler os pares já reunidos é a visão
`auditoria.vw_turno`.

As colunas específicas de cada papel são anuladas por restrição: uma resposta do
agente não pode carregar intenção classificada, e um prompt do usuário não pode
carregar tempo de processamento. O banco recusa as duas coisas.

### Como a fonte de uma resposta é registrada

`auditoria.mensagem_fonte` liga a resposta aos chunks que a fundamentaram, e faz
isso de um jeito que merece explicação:

- `chunk_id` aponta para `vecs.documentos_metro(id)` **sem chave estrangeira**.
  O id do chunk é o md5 do próprio conteúdo (`rag/indexador.py::_chunk_id`), de
  modo que reindexar um documento gera ids novos. Uma FK forçaria a escolher
  entre travar a reindexação e apagar a trilha — as duas inaceitáveis diante da
  imutabilidade exigida pelo RNF09.
- Os metadados (`arquivo_origem`, `secao`, `projeto_codigo`, `trecho`) são
  **copiados no momento da resposta**, não lidos por junção. A fonte citada
  precisa continuar legível mesmo depois de o documento sair do índice.
- `artefato_id` é **opcional**. A Seção 3.6.7 registra que documentos normativos
  não pertencem a projeto algum e portanto não têm artefato; deixá-lo nulo
  resolve essa limitação sem abrir mão do vínculo relacional quando ele existe.

## A base sintética carregada

Os valores do `02_initial_data.sql` não foram inventados: saem dos documentos
que já estão indexados no banco vetorial.

| Tabela | Linhas | Origem |
|---|---:|---|
| `portfolio` | 4 | Subportfólios da planilha `Portfolio_Sintetico_2026.xlsx` |
| `usuario` | 10 | Duas personas da Seção 1.5 e um líder por projeto (nomes fictícios) |
| `projeto` | 8 | Planilha de portfólio: fase, situação, datas, previsto e realizado |
| `projeto_relacionado` | 6 | Dependências declaradas na mesma planilha |
| `artefato` | 37 | Documentos de projeto indexados |
| `pendencia` | 18 | Planilhas `04_Riscos_e_Problemas` de cada projeto |
| `usuario_projeto` | 24 | Diretor e PMO no portfólio inteiro; cada líder no próprio projeto |

Manter os dois lados idênticos não é preciosismo: se o banco disser que o SYN-01
está com -18 p.p. e o documento indexado disser outra coisa, o agente responde
uma coisa ou outra conforme o caminho que tomar. É exatamente a divergência que
o RNF12 mede.

O `02_initial_data.sql` termina com uma consulta de cobertura que compara, projeto
a projeto, os artefatos cadastrados com os documentos distintos indexados no RAG.
As duas contagens devem bater; divergência significa que alguém indexou um
documento sem cadastrá-lo, ou o contrário.

Três documentos ficam fora de `artefato` porque não pertencem a projeto algum e
`artefato.projeto_id` é `NOT NULL`: a planilha de portfólio e os dois materiais
normativos de `VETORIZE/`. Eles continuam citáveis como fonte, com
`mensagem_fonte.artefato_id` nulo.

## Controle de acesso

A API do backend conecta pela connection string direta e opera como dono dos
schemas, portanto **não é filtrada por RLS**. As políticas do
`03_rls_policies.sql` protegem a superfície que o Supabase publica por HTTP:
sem elas, uma tabela exposta no PostgREST é legível por quem tiver a chave
anônima, que é pública por definição.

A regra de acesso, definida pelo RNF02, é **autenticação sim, autorização por
cargo não**. Diretor, PMO e líder enxergam o mesmo portfólio. O que não é
compartilhado é a conversa: cada pessoa alcança apenas as próprias.

`auditoria.evento_plataforma` e `auditoria.notificacao` ficam com RLS ativa e
**nenhuma política** — o que nega tudo para quem é submetido a RLS. É o que o
RNF09 pede ao exigir que esses registros sejam consultáveis apenas por acesso
administrativo. A ausência de política ali é deliberada: acrescentar uma é
afrouxar o RNF09, e precisa ser dito no Merge Request.

### Imutabilidade da trilha

`01_create_database.sql` revoga `UPDATE` e `DELETE` das tabelas de auditoria.
Há exatamente duas exceções, concedidas em nível de coluna ao papel `az1_app`,
porque nenhuma das duas reescreve o que foi registrado:

- `conversa (titulo, atualizada_em, arquivada_em)` — renomear e arquivar;
- `avaliacao (polaridade, nota, motivo, comentario)` — reavaliar uma resposta.

Não existe exclusão de conversa. O "apagar" da interface preenche
`arquivada_em`: a retenção mínima de 90 dias do RNF09 vale também para o que o
usuário quis esconder.

`auditoria.evento_plataforma.detalhe` é um `jsonb` livre e é o campo com maior
risco de vazar segredo. **Não grave senha, token ou chave ali** — o RNF09
proíbe explicitamente.

## Ganchos para a autenticação

A autenticação (RNF02) foi implementada em `feat/autenticacao-login` (Supabase
Auth com Microsoft Entra ID como provedor de identidade; detalhes em
`docs/Projeto.md`, Seção 3.10). O banco já estava preparado para recebê-la, e a
preparação era pequena de propósito:

1. `portfolio.usuario.auth_user_id UUID UNIQUE`. Guarda o id da conta
   no provedor de SSO.
2. `portfolio.usuario_atual()` traduz a identidade do JWT para
   `portfolio.usuario.id`. **Todas as políticas de RLS passam por essa função**,
   então nenhuma delas precisou ser reescrita.
3. Nenhuma senha, token ou segredo é armazenado. O provedor de SSO detém a
   credencial; o banco guarda só a correspondência.

`auth_user_id` já é preenchida no login: `src/services/usuario_service.py`
(`ResolveOrCreateUsuario`) procura o usuário por `auth_user_id` e, se não achar,
por e-mail; se nenhum dos dois encontrar nada — o caso de qualquer conta real,
já que os 10 usuários sintéticos de `02_initial_data.sql` usam e-mails
`@metro.example` —, cria um registro novo com `perfil` padrão `lider_projeto`.
A chamada acontece em `src/az1_api/dependencies.py`, a cada requisição
autenticada, e é best-effort: se o banco estiver fora do ar, a autenticação
continua funcionando, só sem ligar `auth_user_id` naquela requisição.

O que ainda não foi feito é promover a coluna a chave estrangeira:

```sql
ALTER TABLE portfolio.usuario
  ADD CONSTRAINT usuario_auth_user_fk
  FOREIGN KEY (auth_user_id) REFERENCES auth.users (id) ON DELETE SET NULL;
```

Isso já seria seguro — os usuários sintéticos remanescentes continuam com
`auth_user_id` nulo, e uma FK não rejeita nulo —, mas é uma migração de esquema,
categoria de mudança diferente de código de aplicação escrevendo dados, e por
isso ficou como decisão separada da equipe em vez de ser aplicada junto.

## Evolução em relação à modelagem da Sprint 2

O modelo implementado se afasta da modelagem apresentada na Sprint 2 em seis
pontos. Todos foram decididos deliberadamente, e a Seção 3.6 do
`docs/Projeto.md` **já foi atualizada** para refletir cada um deles, junto com o
diagrama `assets/logico.svg`. O modelo conceitual (Seções 3.6.1 a 3.6.3 e
`assets/conceitual.svg`) permanece como estava: ele descreve conceitos de
negócio, e as estruturas acrescentadas aqui — avaliação, evento de plataforma e
o desdobramento de Interação — pertencem à camada de implementação.

A tabela abaixo continua registrada porque explica **por que** cada diferença
existe. A coerência entre o documento, o script e o banco em execução é
verificável a qualquer momento:

```bash
python scripts/verificar_modelo_documentado.py
```

O script compara tabela a tabela e coluna a coluna, e sai com código 1 se
divergirem.

| # | Modelagem da Sprint 2 | Modelo atual | Por quê |
|---|---|---|---|
| 1 | Tabela `interacao`, plana | `conversa` + `mensagem` | A Seção 3.6 não agrupava solicitações em conversa nem ordenava turnos. O frontend já gera `conversation_id` e o descartava |
| 2 | `interacao.resultado` como único registro da resposta | `mensagem.conteudo` guarda o texto | **A Seção 3.6 não armazenava a resposta em lugar nenhum** — `resultado` é um enum de quatro valores. Sem o texto, o RNF12 não é verificável |
| 3 | `interacao_artefato` (FK para artefato) | `mensagem_fonte` (chunk + snapshot + artefato opcional) | As fontes reais são chunks do RAG, e a FK obrigatória excluía os documentos normativos |
| 4 | `interacao.feedback_usuario TEXT` | Tabela `avaliacao` | Um TEXT solto não tem nota, data nem autor: não dá para medir satisfação nem correlacioná-la a intenção, fonte ou tempo |
| 5 | Sem registro de eventos de plataforma | `evento_plataforma` | `mensagem` responde "o que o agente respondeu"; login e navegação são outra pergunta |
| 6 | `pendencia.situacao IN ('aberta','em_tratamento','resolvida')` | Acrescido `'materializada'` | A base sintética usa esse estado para o risco que se concretizou; colapsá-lo faria a resposta vinda do banco divergir do documento |

Acréscimos menores, pela mesma lógica de não perder dado que já existe na base:
`projeto.fase`, `projeto.percentual_previsto` e `projeto.desvio_pp` (coluna
gerada); `projeto_relacionado`; e em `pendencia`, as colunas `codigo`, `titulo`,
`criticidade`, `responsavel` e `acao_resposta`.

## Pendências conhecidas

- **Normalizar `arquivo_origem` no indexador.** `vecs.documentos_metro` guarda o
  caminho absoluto da máquina de quem rodou a indexação
  (`/Users/<pessoa>/Downloads/...`). Aqui, `artefato.referencia` já usa caminho
  relativo, e a junção entre os dois é feita por `LIKE '%' || referencia`.
  Corrigir do lado do `src/rag/indexador.py` elimina a gambiarra e evita exibir
  a pasta pessoal de alguém como fonte ao usuário (RF03).
- **Persistir de fato.** As tabelas existem, mas `src/services/chat_service.py`
  ainda não grava nada: a conversa continua vivendo só no estado do React. É a
  task T26.
- `campo_artefato` está vazia. Depende de extrair os campos de dentro dos
  documentos, que é o insumo do RF04.
