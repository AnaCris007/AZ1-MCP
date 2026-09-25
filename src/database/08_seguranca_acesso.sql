-- Correções de controle de acesso, aplicáveis a bases já inicializadas.
-- Execute como dono dos schemas, depois de 01_create_database.sql.
-- Idempotente: pode rodar quantas vezes for preciso.
--
-- Contexto: a auditoria da branch fix/auditoria-desenvolvimento-solucao
-- encontrou uma via que contorna as políticas de RLS de `auditoria.conversa` e
-- `auditoria.mensagem`. O 01 já nasce corrigido; este script leva a correção às
-- bases criadas antes dele.
\set ON_ERROR_STOP on
BEGIN;

-- ---------------------------------------------------------------------------
-- 1. `auditoria.vw_turno` deixa de ser bypass de RLS
-- ---------------------------------------------------------------------------
-- Sem `security_invoker`, uma view executa com os privilégios do DONO e a RLS
-- das tabelas de base é avaliada contra ele. Como `03_rls_policies.sql` faz
-- `GRANT SELECT ON ALL TABLES IN SCHEMA auditoria TO az1_app` — e `ALL TABLES`
-- alcança views —, um `SELECT * FROM auditoria.vw_turno` devolvia prompt,
-- resposta, intenção e avaliação de TODOS os usuários.
--
-- Ou seja: as políticas `conversa_propria_leitura` e
-- `mensagem_da_propria_conversa_leitura` estavam corretas e eram contornáveis
-- por um caminho que nada no repositório apontava.
--
-- A correção é uma cláusula, e vale mesmo enquanto a RLS está inerte por
-- `AZ1_DB_ROLE` vazia: ela é o que faz a proteção valer no dia em que o papel
-- for assumido.
ALTER VIEW auditoria.vw_turno SET (security_invoker = true);

-- `portfolio.vw_projeto_situacao` fica de fora DESTE script de propósito. Ela
-- também roda como dono, mas as políticas de `portfolio` já liberam leitura a
-- qualquer autenticado, então o efeito prático é nenhum — e ela será recriada
-- na remoção da tabela `portfolio.portfolio`, que é onde a cláusula entra sem
-- custo. Não é esquecimento.

COMMIT;

-- ---------------------------------------------------------------------------
-- Verificação
-- ---------------------------------------------------------------------------
-- `security_invoker` deve aparecer como on. Vazio significa que o ALTER não
-- pegou — provavelmente a view não existe nesta base.
SELECT c.relname AS view,
       COALESCE(
           (SELECT o FROM unnest(c.reloptions) AS o WHERE o LIKE 'security_invoker=%'),
           'NAO DEFINIDO'
       ) AS opcao
  FROM pg_class c
  JOIN pg_namespace n ON n.oid = c.relnamespace
 WHERE n.nspname = 'auditoria' AND c.relname = 'vw_turno';
