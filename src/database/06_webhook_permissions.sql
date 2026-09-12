-- Privilégios dos receptores, aplicáveis também a bases já inicializadas.
-- Execute como administrador após 01_create_database.sql.
-- PostgreSQL 16 ou superior. webhook_login deve ser o usuário do DSN receptor;
-- se omitido, assume o usuário conectado (instalação local padrão).
\set ON_ERROR_STOP on
\if :{?webhook_login}
\else
SELECT current_user AS webhook_login \gset
\endif
BEGIN;
DO $$
BEGIN
    IF current_setting('server_version_num')::integer < 160000 THEN
        RAISE EXCEPTION '06_webhook_permissions.sql exige PostgreSQL 16 ou superior';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'az1_webhook') THEN
        CREATE ROLE az1_webhook NOLOGIN NOSUPERUSER NOBYPASSRLS;
    END IF;
END
$$;
GRANT az1_webhook TO :"webhook_login" WITH INHERIT FALSE, SET TRUE;

REVOKE ALL ON auditoria.evento_webhook, integracao.conexao FROM PUBLIC, az1_webhook;
GRANT USAGE ON SCHEMA auditoria, integracao TO az1_webhook;
GRANT SELECT, INSERT ON auditoria.evento_webhook TO az1_webhook;
GRANT USAGE ON SEQUENCE auditoria.evento_webhook_id_seq TO az1_webhook;
GRANT UPDATE (concluido_em, situacao) ON auditoria.evento_webhook TO az1_webhook;
GRANT SELECT (id, provedor, subscription_id, ativa, expira_em)
    ON integracao.conexao TO az1_webhook;
GRANT UPDATE (delta_pendente) ON integracao.conexao TO az1_webhook;

ALTER TABLE auditoria.evento_webhook ENABLE ROW LEVEL SECURITY;
ALTER TABLE integracao.conexao ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS webhook_leitura ON auditoria.evento_webhook;
DROP POLICY IF EXISTS webhook_registro ON auditoria.evento_webhook;
DROP POLICY IF EXISTS webhook_conclusao ON auditoria.evento_webhook;
DROP POLICY IF EXISTS webhook_origem_leitura ON integracao.conexao;
DROP POLICY IF EXISTS webhook_origem_varredura ON integracao.conexao;
CREATE POLICY webhook_leitura ON auditoria.evento_webhook
    FOR SELECT TO az1_webhook USING (true);
CREATE POLICY webhook_registro ON auditoria.evento_webhook
    FOR INSERT TO az1_webhook WITH CHECK (true);
CREATE POLICY webhook_conclusao ON auditoria.evento_webhook
    FOR UPDATE TO az1_webhook USING (true) WITH CHECK (true);
CREATE POLICY webhook_origem_leitura ON integracao.conexao
    FOR SELECT TO az1_webhook USING (true);
CREATE POLICY webhook_origem_varredura ON integracao.conexao
    FOR UPDATE TO az1_webhook USING (ativa) WITH CHECK (ativa);

-- Papéis de sessões de usuários não recebem acesso à integração ou sua trilha.
DO $$
DECLARE papel text;
BEGIN
    FOREACH papel IN ARRAY ARRAY['az1_app', 'anon', 'authenticated'] LOOP
        IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = papel) THEN
            EXECUTE format('REVOKE ALL ON auditoria.evento_webhook, integracao.conexao FROM %I', papel);
            EXECUTE format('REVOKE ALL ON SCHEMA integracao FROM %I', papel);
        END IF;
    END LOOP;
END
$$;
COMMENT ON TABLE auditoria.evento_webhook IS
    'Trilha de recebimentos de webhook. UNIQUE deduplica somente identidade estável de evento ou versão (TI-37). Avisos mínimos OneDrive geram uma linha por recebimento; repetir delta_pendente = TRUE preserva o estado.';
COMMIT;
