-- Eventos próprios do usuário na Agenda, nunca escritos no Outlook.
-- Execute como administrador após 03_rls_policies.sql.
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

-- Aditivo, de propósito: uma migração nova não deveria exigir editar
-- 03_rls_policies.sql, então os grants desta tabela ficam autocontidos aqui.
GRANT SELECT, INSERT, UPDATE, DELETE ON portfolio.evento_local TO az1_app;
GRANT USAGE, SELECT ON SEQUENCE portfolio.evento_local_id_seq TO az1_app;

ALTER TABLE portfolio.evento_local ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS evento_local_propria_leitura ON portfolio.evento_local;
DROP POLICY IF EXISTS evento_local_propria_criacao ON portfolio.evento_local;
DROP POLICY IF EXISTS evento_local_propria_exclusao ON portfolio.evento_local;

CREATE POLICY evento_local_propria_leitura ON portfolio.evento_local
    FOR SELECT USING (usuario_id = portfolio.usuario_atual());

CREATE POLICY evento_local_propria_criacao ON portfolio.evento_local
    FOR INSERT WITH CHECK (usuario_id = portfolio.usuario_atual());

-- Primeira política FOR DELETE do projeto: toda tabela existente até aqui usa
-- exclusão lógica (situacao/ativa), não DELETE físico. Não há política de
-- UPDATE: não existe rota de edição neste escopo, e uma política sem rota que
-- a use é manutenção morta.
CREATE POLICY evento_local_propria_exclusao ON portfolio.evento_local
    FOR DELETE USING (usuario_id = portfolio.usuario_atual());

-- A aplicação conecta hoje como dono do schema (AZ1_DB_ROLE opcional, ver
-- database_service.py): estas políticas não são aplicadas ainda. O filtro por
-- usuario_id em EventoLocalRepository não é opcional por causa disso, mesma
-- ressalva já documentada em PortfolioRepository.alterar_situacao.
COMMENT ON TABLE portfolio.evento_local IS
    'Compromissos próprios do usuário na Agenda. Nunca sincronizados com Outlook/Microsoft Graph — ver services/evento_local_repository.py.';
COMMIT;
