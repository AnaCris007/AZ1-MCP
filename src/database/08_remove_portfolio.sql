-- Remoção da tabela portfolio.portfolio, aplicável a bases já inicializadas.
-- Execute como dono dos schemas, depois de 01_create_database.sql.
-- Idempotente: pode rodar quantas vezes for preciso.
--
-- Por que ela sai: agrupava projetos por subportfólio da planilha, mas o
-- agrupamento nunca chegou a ser consultado. Nenhum código Python lia a tabela
-- nem `projeto.portfolio_id`; o único consumidor era o JOIN de
-- `vw_projeto_situacao`, cujo resultado atravessava o repositório, o contrato
-- `ProjetoResponse` e a rota `/api/v1/projetos` até o frontend, que não exibe
-- nem consome nenhum dos dois. Agrupamento que ninguém lê é peso, não modelo.
--
-- ATENÇÃO ao recriar a view: a ordem das colunas é contrato. `_para_projeto`
-- em src/services/portfolio_repository.py lê a linha POR POSIÇÃO, e trocas
-- entre colunas do mesmo tipo (lider/lider_email) não levantam erro nenhum.
-- `tests/test_portfolio_repository.py` compara a ordem daqui com a do SELECT.
\set ON_ERROR_STOP on
BEGIN;

-- ---------------------------------------------------------------------------
-- 1. A view sai primeiro: ela depende da coluna e da tabela
-- ---------------------------------------------------------------------------
-- `DROP` e não `CREATE OR REPLACE`: o PostgreSQL recusa substituir uma view
-- quando a lista de colunas encolhe.
DROP VIEW IF EXISTS portfolio.vw_projeto_situacao;

-- ---------------------------------------------------------------------------
-- 2. A coluna, levando junto a FK e o índice
-- ---------------------------------------------------------------------------
-- `DROP COLUMN` remove em cascata a restrição de chave estrangeira e o
-- `idx_projeto_portfolio`, que era um índice sobre ela. Não é preciso dropá-los
-- à mão, e tentar seria erro em reexecução.
ALTER TABLE portfolio.projeto DROP COLUMN IF EXISTS portfolio_id;

-- ---------------------------------------------------------------------------
-- 3. A tabela
-- ---------------------------------------------------------------------------
-- Sem CASCADE de propósito: neste ponto nada mais deveria depender dela. Se o
-- DROP falhar por dependência, é sinal de que existe um objeto que esta
-- migração não conhece — e descobrir qual é melhor do que derrubá-lo em
-- silêncio. A RLS e a policy `portfolio_leitura_autenticada` caem com a tabela.
DROP TABLE IF EXISTS portfolio.portfolio;

-- ---------------------------------------------------------------------------
-- 4. A view volta, sem o JOIN e com security_invoker
-- ---------------------------------------------------------------------------
-- `security_invoker` pela mesma razão de `auditoria.vw_turno` no
-- 07_seguranca_acesso.sql: sem ele a view roda com os privilégios do DONO e a
-- RLS das tabelas de base é avaliada contra ele, o que faz de toda view um
-- contorno das policies. Aqui o efeito prático hoje é nenhum — as policies de
-- `portfolio` liberam leitura a qualquer autenticado —, mas deixar o padrão
-- inseguro num lugar e seguro no outro é como a inconsistência volta.
CREATE VIEW portfolio.vw_projeto_situacao WITH (security_invoker = true) AS
SELECT
    pr.id,
    pr.codigo,
    pr.nome,
    pr.fase,
    pr.status,
    pr.data_inicio,
    pr.data_termino_prevista,
    pr.percentual_previsto,
    pr.percentual_avanco,
    pr.desvio_pp,
    li.nome  AS lider,
    li.email AS lider_email,
    (SELECT count(*) FROM portfolio.pendencia pe
      WHERE pe.projeto_id = pr.id AND pe.situacao <> 'resolvida') AS pendencias_abertas,
    (SELECT count(*) FROM portfolio.artefato ar
      WHERE ar.projeto_id = pr.id)                                AS artefatos
FROM portfolio.projeto pr
JOIN portfolio.usuario   li ON li.id = pr.lider_id;

COMMENT ON VIEW portfolio.vw_projeto_situacao IS
    'Situação consolidada de cada projeto, com pendências abertas e artefatos já contados.';

-- A view é recriada, então perdeu os grants. Devolve-os ao papel da aplicação
-- e a `authenticated`, como estavam em 03_rls_policies.sql.
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'az1_app') THEN
        GRANT SELECT ON portfolio.vw_projeto_situacao TO az1_app;
    END IF;
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
        GRANT SELECT ON portfolio.vw_projeto_situacao TO authenticated;
    END IF;
END
$$;

COMMIT;

-- ---------------------------------------------------------------------------
-- Verificação
-- ---------------------------------------------------------------------------
\echo ''
\echo '== A tabela e a coluna devem ter sumido (zero linhas) =='
SELECT 'tabela portfolio.portfolio' AS objeto, count(*) AS existe
  FROM information_schema.tables
 WHERE table_schema = 'portfolio' AND table_name = 'portfolio'
UNION ALL
SELECT 'coluna projeto.portfolio_id', count(*)
  FROM information_schema.columns
 WHERE table_schema = 'portfolio' AND table_name = 'projeto'
   AND column_name = 'portfolio_id';

\echo ''
\echo '== A view deve ter 14 colunas, nesta ordem, e security_invoker=on =='
SELECT ordinal_position, column_name
  FROM information_schema.columns
 WHERE table_schema = 'portfolio' AND table_name = 'vw_projeto_situacao'
 ORDER BY ordinal_position;

SELECT COALESCE(
           (SELECT o FROM unnest(c.reloptions) AS o WHERE o LIKE 'security_invoker=%'),
           'NAO DEFINIDO'
       ) AS opcao
  FROM pg_class c
  JOIN pg_namespace n ON n.oid = c.relnamespace
 WHERE n.nspname = 'portfolio' AND c.relname = 'vw_projeto_situacao';
