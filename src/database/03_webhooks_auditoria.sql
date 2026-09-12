-- Schema auditoria já existe com auditoria.conversa e auditoria.mensagem.
-- O usuário de sistema (id=0) foi inserido em portfolio.usuario manualmente.
-- Este script cria apenas o schema alerta (novo).

CREATE SCHEMA IF NOT EXISTS alerta;

CREATE TABLE IF NOT EXISTS alerta.assinante (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    projeto_id  TEXT NOT NULL,
    url         TEXT NOT NULL CHECK (url LIKE 'https://%'),
    secret_hash TEXT NOT NULL,
    ativa       BOOLEAN NOT NULL DEFAULT TRUE,
    criado_em   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS alerta.historico (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    assinante_id  UUID REFERENCES alerta.assinante(id) ON DELETE SET NULL,
    audio_id      TEXT NOT NULL,
    payload       JSONB NOT NULL,
    situacao      TEXT NOT NULL DEFAULT 'pendente',
    status_code   INT,
    enviado_em    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_historico_assinante ON alerta.historico(assinante_id);
CREATE INDEX IF NOT EXISTS idx_historico_audio ON alerta.historico(audio_id);
