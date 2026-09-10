-- =============================================================================
-- AZ1 — Papéis de acesso e Row Level Security
--
-- Por que este arquivo existe:
--
-- A API do backend conecta ao banco pela connection string direta e opera como
-- dono dos schemas, portanto NÃO é filtrada por RLS. As políticas abaixo não
-- protegem a aplicação de si mesma — protegem a superfície que o Supabase
-- publica por HTTP. Qualquer schema exposto no PostgREST fica acessível com a
-- chave anônima, que é pública por definição, e sem RLS uma tabela exposta é
-- legível por qualquer pessoa que tenha a URL do projeto.
--
-- A regra de acesso desta solução, definida pelo RNF02, é: autenticação sim,
-- autorização por cargo não. Diretor, PMO e líder enxergam o mesmo portfólio.
-- O que NÃO é compartilhado é a conversa: cada pessoa lê apenas as próprias,
-- e a leitura administrativa da trilha de auditoria exigida pelo RNF09 passa
-- pelo service_role, nunca pela sessão do usuário.
--
--   psql "$SUPABASE_DB_URL" -v ON_ERROR_STOP=1 -f 03_rls_policies.sql
-- =============================================================================

\set ON_ERROR_STOP on

BEGIN;

-- -----------------------------------------------------------------------------
-- 1. Papel da aplicação
-- -----------------------------------------------------------------------------

-- Papel sem login: existe para receber os GRANTs de coluna e ser herdado pelo
-- usuário que o backend usar. NOLOGIN porque não é uma credencial, é um molde
-- de permissão.
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'az1_app') THEN
        CREATE ROLE az1_app NOLOGIN;
    END IF;
END
$$;

GRANT USAGE ON SCHEMA portfolio, auditoria TO az1_app;

GRANT SELECT ON ALL TABLES IN SCHEMA portfolio TO az1_app;
GRANT INSERT, UPDATE, DELETE ON portfolio.projeto, portfolio.artefato,
      portfolio.campo_artefato, portfolio.pendencia, portfolio.usuario_projeto
      TO az1_app;

-- Na auditoria o padrão é inserir e ler; nunca alterar nem apagar (RNF09).
GRANT SELECT, INSERT ON ALL TABLES IN SCHEMA auditoria TO az1_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA auditoria TO az1_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA portfolio TO az1_app;

-- As duas exceções previstas no 01_create_database.sql, em nível de coluna:
-- renomear/arquivar uma conversa e reavaliar uma resposta não reescrevem
-- nenhuma mensagem registrada.
GRANT UPDATE (titulo, atualizada_em, arquivada_em) ON auditoria.conversa    TO az1_app;
GRANT UPDATE (polaridade, nota, motivo, comentario) ON auditoria.avaliacao  TO az1_app;

-- Papéis do Supabase (podem não existir num PostgreSQL avulso).
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
        GRANT USAGE ON SCHEMA portfolio, auditoria TO authenticated;
        GRANT SELECT ON ALL TABLES IN SCHEMA portfolio TO authenticated;
        GRANT SELECT, INSERT ON auditoria.conversa, auditoria.mensagem,
              auditoria.mensagem_fonte, auditoria.avaliacao TO authenticated;
        GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA auditoria TO authenticated;
        GRANT UPDATE (titulo, atualizada_em, arquivada_em)
              ON auditoria.conversa TO authenticated;
        GRANT UPDATE (polaridade, nota, motivo, comentario)
              ON auditoria.avaliacao TO authenticated;
    END IF;
    -- anon é a chave pública do projeto: não enxerga nada destes schemas.
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
        REVOKE ALL ON ALL TABLES IN SCHEMA portfolio, auditoria FROM anon;
        REVOKE USAGE ON SCHEMA portfolio, auditoria FROM anon;
    END IF;
END
$$;


-- -----------------------------------------------------------------------------
-- 2. Ponte entre o SSO e a tabela de usuários
-- -----------------------------------------------------------------------------

-- Traduz a identidade do provedor de SSO (auth.uid()) para portfolio.usuario.id.
--
-- Esta função é a única peça que a frente de autenticação (RNF02) precisa fazer
-- funcionar: basta que o login preencha portfolio.usuario.auth_user_id com o id
-- da conta no provedor. Todas as políticas abaixo passam por aqui, então nenhuma
-- delas precisará ser reescrita quando a autenticação entrar.
--
-- Enquanto auth_user_id estiver nulo para todo mundo, a função devolve NULL e as
-- políticas negam tudo — comportamento correto: sem identidade, sem acesso. A
-- aplicação continua funcionando porque conecta como dono do schema, que não é
-- submetido a RLS.
--
-- SECURITY DEFINER para poder ler portfolio.usuario mesmo com RLS ativa nela, e
-- search_path fixo para que a função não possa ser sequestrada por um schema
-- plantado no caminho de busca do chamador.
CREATE OR REPLACE FUNCTION portfolio.usuario_atual()
RETURNS INTEGER
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = portfolio, pg_temp
AS $$
    SELECT u.id
      FROM portfolio.usuario u
     WHERE u.auth_user_id = nullif(
               current_setting('request.jwt.claims', true)::jsonb ->> 'sub', ''
           )::uuid
       AND u.ativo;
$$;

COMMENT ON FUNCTION portfolio.usuario_atual() IS
    'portfolio.usuario.id do usuário autenticado, ou NULL. Ponte para a frente de autenticação do RNF02.';

REVOKE EXECUTE ON FUNCTION portfolio.usuario_atual() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION portfolio.usuario_atual() TO az1_app;
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
        GRANT EXECUTE ON FUNCTION portfolio.usuario_atual() TO authenticated;
    END IF;
END
$$;


-- -----------------------------------------------------------------------------
-- 3. Ativação do RLS
-- -----------------------------------------------------------------------------

-- Sem FORCE: o dono do schema (a API do backend) permanece fora do filtro. É
-- ele quem aplica as regras de negócio e quem precisa gravar a auditoria de
-- todos os usuários.
ALTER TABLE portfolio.portfolio           ENABLE ROW LEVEL SECURITY;
ALTER TABLE portfolio.usuario             ENABLE ROW LEVEL SECURITY;
ALTER TABLE portfolio.projeto             ENABLE ROW LEVEL SECURITY;
ALTER TABLE portfolio.projeto_relacionado ENABLE ROW LEVEL SECURITY;
ALTER TABLE portfolio.artefato            ENABLE ROW LEVEL SECURITY;
ALTER TABLE portfolio.campo_artefato      ENABLE ROW LEVEL SECURITY;
ALTER TABLE portfolio.pendencia           ENABLE ROW LEVEL SECURITY;
ALTER TABLE portfolio.usuario_projeto     ENABLE ROW LEVEL SECURITY;

ALTER TABLE auditoria.conversa            ENABLE ROW LEVEL SECURITY;
ALTER TABLE auditoria.mensagem            ENABLE ROW LEVEL SECURITY;
ALTER TABLE auditoria.mensagem_fonte      ENABLE ROW LEVEL SECURITY;
ALTER TABLE auditoria.avaliacao           ENABLE ROW LEVEL SECURITY;
ALTER TABLE auditoria.evento_plataforma   ENABLE ROW LEVEL SECURITY;
ALTER TABLE auditoria.notificacao         ENABLE ROW LEVEL SECURITY;


-- -----------------------------------------------------------------------------
-- 4. Políticas do domínio: qualquer pessoa autenticada lê o portfólio inteiro
-- -----------------------------------------------------------------------------

-- O RNF02 exige autenticação e diz explicitamente que o perfil não concede
-- permissões distintas. A condição é, portanto, "existe um usuário ativo por
-- trás desta sessão" — e não "este usuário acompanha este projeto".
CREATE POLICY portfolio_leitura_autenticada ON portfolio.portfolio
    FOR SELECT USING (portfolio.usuario_atual() IS NOT NULL);
CREATE POLICY projeto_leitura_autenticada ON portfolio.projeto
    FOR SELECT USING (portfolio.usuario_atual() IS NOT NULL);
CREATE POLICY projeto_relacionado_leitura_autenticada ON portfolio.projeto_relacionado
    FOR SELECT USING (portfolio.usuario_atual() IS NOT NULL);
CREATE POLICY artefato_leitura_autenticada ON portfolio.artefato
    FOR SELECT USING (portfolio.usuario_atual() IS NOT NULL);
CREATE POLICY campo_artefato_leitura_autenticada ON portfolio.campo_artefato
    FOR SELECT USING (portfolio.usuario_atual() IS NOT NULL);
CREATE POLICY pendencia_leitura_autenticada ON portfolio.pendencia
    FOR SELECT USING (portfolio.usuario_atual() IS NOT NULL);
CREATE POLICY usuario_projeto_leitura_autenticada ON portfolio.usuario_projeto
    FOR SELECT USING (portfolio.usuario_atual() IS NOT NULL);

-- Exceção: o cadastro de usuários. Cada pessoa vê o próprio registro completo;
-- os demais são expostos pela aplicação apenas onde o domínio exige (o nome do
-- líder de um projeto), e não por leitura direta da tabela.
CREATE POLICY usuario_le_o_proprio_registro ON portfolio.usuario
    FOR SELECT USING (id = portfolio.usuario_atual());


-- -----------------------------------------------------------------------------
-- 5. Políticas da conversa: cada pessoa só alcança as próprias
-- -----------------------------------------------------------------------------

CREATE POLICY conversa_propria_leitura ON auditoria.conversa
    FOR SELECT USING (usuario_id = portfolio.usuario_atual());

CREATE POLICY conversa_propria_criacao ON auditoria.conversa
    FOR INSERT WITH CHECK (usuario_id = portfolio.usuario_atual());

-- Só as colunas do GRANT acima são atualizáveis; a política limita as linhas.
CREATE POLICY conversa_propria_atualizacao ON auditoria.conversa
    FOR UPDATE USING (usuario_id = portfolio.usuario_atual())
           WITH CHECK (usuario_id = portfolio.usuario_atual());

CREATE POLICY mensagem_da_propria_conversa_leitura ON auditoria.mensagem
    FOR SELECT USING (EXISTS (
        SELECT 1 FROM auditoria.conversa c
         WHERE c.id = mensagem.conversa_id
           AND c.usuario_id = portfolio.usuario_atual()));

CREATE POLICY mensagem_da_propria_conversa_criacao ON auditoria.mensagem
    FOR INSERT WITH CHECK (EXISTS (
        SELECT 1 FROM auditoria.conversa c
         WHERE c.id = mensagem.conversa_id
           AND c.usuario_id = portfolio.usuario_atual()));

-- A fonte acompanha a resposta: quem enxerga a mensagem enxerga o que a
-- fundamentou. É o que torna o RF03 verificável pelo próprio usuário.
CREATE POLICY mensagem_fonte_segue_a_mensagem ON auditoria.mensagem_fonte
    FOR SELECT USING (EXISTS (
        SELECT 1 FROM auditoria.mensagem m
          JOIN auditoria.conversa c ON c.id = m.conversa_id
         WHERE m.id = mensagem_fonte.mensagem_id
           AND c.usuario_id = portfolio.usuario_atual()));

CREATE POLICY avaliacao_propria_leitura ON auditoria.avaliacao
    FOR SELECT USING (usuario_id = portfolio.usuario_atual());
CREATE POLICY avaliacao_propria_criacao ON auditoria.avaliacao
    FOR INSERT WITH CHECK (usuario_id = portfolio.usuario_atual());
CREATE POLICY avaliacao_propria_atualizacao ON auditoria.avaliacao
    FOR UPDATE USING (usuario_id = portfolio.usuario_atual())
           WITH CHECK (usuario_id = portfolio.usuario_atual());


-- -----------------------------------------------------------------------------
-- 6. Tabelas sem política: acesso administrativo apenas
-- -----------------------------------------------------------------------------

-- auditoria.evento_plataforma e auditoria.notificacao ficam com RLS ativa e
-- NENHUMA política. Em PostgreSQL isso nega tudo para quem é submetido a RLS,
-- que é exatamente o que o RNF09 pede: os registros são "consultáveis apenas
-- por acesso administrativo". O administrador consulta pelo dono do schema ou
-- pelo service_role; a sessão do usuário não os alcança em hipótese alguma.
--
-- A ausência de política aqui é deliberada. Se alguém acrescentar uma no
-- futuro, estará afrouxando o RNF09 e precisa dizer isso no MR.

COMMIT;


-- =============================================================================
-- Verificação
-- =============================================================================
\echo ''
\echo '== RLS por tabela (todas devem estar ativas) =='
SELECT n.nspname AS schema, c.relname AS tabela, c.relrowsecurity AS rls,
       count(p.policyname) AS politicas
  FROM pg_class c
  JOIN pg_namespace n ON n.oid = c.relnamespace
  LEFT JOIN pg_policies p ON p.schemaname = n.nspname AND p.tablename = c.relname
 WHERE n.nspname IN ('portfolio', 'auditoria') AND c.relkind = 'r'
 GROUP BY 1, 2, 3
 ORDER BY 1, 2;

\echo ''
\echo '== Sem identidade, portfolio.usuario_atual() devolve NULL =='
SELECT portfolio.usuario_atual() AS usuario_atual;
