-- Eventos próprios do usuário na Agenda, nunca escritos no Outlook.
-- Em ambientes completos, execute como administrador após
-- 03_rls_policies.sql. O PostgreSQL local do Compose não instala esse baseline
-- de RLS: nesse caso os blocos de privilégios/policies são ignorados com NOTICE
-- e a API, que conecta como dona do schema, continua funcional.
-- PostgreSQL 16 ou superior.
\set ON_ERROR_STOP on
BEGIN;

-- DATE + TIME opcional, e não TIMESTAMPTZ: são compromissos de hora local,
-- sem sincronização externa. Forçar fuso horário num campo opcional
-- fabricaria dado, o mesmo princípio já aplicado ao `time` vazio de marco e
-- prazo em routes/portfolio.py.
CREATE TABLE IF NOT EXISTS portfolio.evento_local (
    id         INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    usuario_id INTEGER     NOT NULL REFERENCES portfolio.usuario (id) ON DELETE CASCADE,
    titulo     TEXT        NOT NULL,
    data       DATE        NOT NULL,
    hora       TIME,
    descricao  TEXT,
    criado_em  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_evento_local_usuario_data ON portfolio.evento_local (usuario_id, data);

ALTER TABLE portfolio.evento_local ENABLE ROW LEVEL SECURITY;

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'az1_app') THEN
        EXECUTE 'GRANT SELECT, INSERT, DELETE ON portfolio.evento_local TO az1_app';
        EXECUTE 'GRANT USAGE, SELECT ON SEQUENCE portfolio.evento_local_id_seq TO az1_app';
    ELSE
        RAISE NOTICE 'papel az1_app ausente; privilégios de evento_local não aplicados';
    END IF;

    IF to_regprocedure('portfolio.usuario_atual()') IS NOT NULL THEN
        EXECUTE 'DROP POLICY IF EXISTS evento_local_propria_leitura ON portfolio.evento_local';
        EXECUTE 'DROP POLICY IF EXISTS evento_local_propria_criacao ON portfolio.evento_local';
        EXECUTE 'DROP POLICY IF EXISTS evento_local_propria_exclusao ON portfolio.evento_local';
        EXECUTE 'CREATE POLICY evento_local_propria_leitura ON portfolio.evento_local
                     FOR SELECT USING (usuario_id = portfolio.usuario_atual())';
        EXECUTE 'CREATE POLICY evento_local_propria_criacao ON portfolio.evento_local
                     FOR INSERT WITH CHECK (usuario_id = portfolio.usuario_atual())';
        EXECUTE 'CREATE POLICY evento_local_propria_exclusao ON portfolio.evento_local
                     FOR DELETE USING (usuario_id = portfolio.usuario_atual())';
    ELSE
        RAISE NOTICE 'função portfolio.usuario_atual ausente; policies de evento_local não aplicadas';
    END IF;
END
$$;

-- A aplicação conecta hoje como dono do schema (AZ1_DB_ROLE opcional, ver
-- database_service.py): estas políticas não são aplicadas ainda. O filtro por
-- usuario_id em EventoLocalRepository não é opcional por causa disso, mesma
-- ressalva já documentada em PortfolioRepository.alterar_situacao.
COMMENT ON TABLE portfolio.evento_local IS
    'Compromissos próprios do usuário na Agenda. Nunca sincronizados com Outlook/Microsoft Graph.';
COMMIT;
