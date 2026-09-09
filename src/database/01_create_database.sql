-- =============================================================================
-- AZ1 — criação do banco
-- =============================================================================
-- Implementa o modelo físico da Seção 3.6.6 do docs/Projeto.md, acrescido das
-- estruturas de integração por webhook da Seção 5.1. Este arquivo é a fonte
-- executável do modelo; a Seção 3.6.6 é a sua descrição em prosa. Se os dois
-- divergirem, é este que roda.
--
-- Uso:  psql -v ON_ERROR_STOP=1 -f 01_create_database.sql
-- =============================================================================

CREATE SCHEMA portfolio;
CREATE SCHEMA auditoria;

CREATE TABLE portfolio.portfolio (
    id            INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    nome          TEXT    NOT NULL,
    ano_exercicio INTEGER NOT NULL,
    UNIQUE (nome, ano_exercicio)
);

CREATE TABLE portfolio.usuario (
    id     INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    nome   TEXT NOT NULL,
    email  TEXT NOT NULL UNIQUE,
    perfil TEXT NOT NULL CHECK (perfil IN ('diretor', 'pmo', 'lider_projeto'))
);

CREATE TABLE portfolio.projeto (
    id                    INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    codigo                TEXT NOT NULL UNIQUE,
    nome                  TEXT NOT NULL,
    status                TEXT NOT NULL,
    data_inicio           DATE,
    data_termino_prevista DATE,
    percentual_avanco     NUMERIC(5,2) NOT NULL DEFAULT 0
                          CHECK (percentual_avanco BETWEEN 0 AND 100),
    portfolio_id          INTEGER NOT NULL REFERENCES portfolio.portfolio (id),
    lider_id              INTEGER NOT NULL REFERENCES portfolio.usuario (id)
);

CREATE TABLE portfolio.artefato (
    id         INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    projeto_id INTEGER NOT NULL REFERENCES portfolio.projeto (id) ON DELETE CASCADE,
    tipo       TEXT NOT NULL,
    referencia TEXT NOT NULL,
    data       TIMESTAMPTZ NOT NULL,
    versao     TEXT
);

CREATE TABLE portfolio.campo_artefato (
    id          INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    artefato_id INTEGER NOT NULL REFERENCES portfolio.artefato (id) ON DELETE CASCADE,
    nome        TEXT NOT NULL,
    valor       TEXT,
    obrigatorio BOOLEAN NOT NULL DEFAULT FALSE,
    preenchido  BOOLEAN GENERATED ALWAYS AS
                (valor IS NOT NULL AND btrim(valor) <> '') STORED,
    UNIQUE (artefato_id, nome)
);

CREATE TABLE portfolio.pendencia (
    id         INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    projeto_id INTEGER NOT NULL REFERENCES portfolio.projeto (id) ON DELETE CASCADE,
    tipo       TEXT NOT NULL,
    descricao  TEXT NOT NULL,
    prazo      DATE,
    situacao   TEXT NOT NULL DEFAULT 'aberta'
               CHECK (situacao IN ('aberta', 'em_tratamento', 'resolvida'))
);

CREATE TABLE portfolio.usuario_projeto (
    usuario_id INTEGER NOT NULL REFERENCES portfolio.usuario (id) ON DELETE CASCADE,
    projeto_id INTEGER NOT NULL REFERENCES portfolio.projeto (id) ON DELETE CASCADE,
    PRIMARY KEY (usuario_id, projeto_id)
);

CREATE TABLE auditoria.interacao (
    id                     INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    usuario_id             INTEGER NOT NULL REFERENCES portfolio.usuario (id),
    data_hora              TIMESTAMPTZ NOT NULL DEFAULT now(),
    canal                  TEXT NOT NULL CHECK (canal IN ('texto', 'voz')),
    texto_solicitacao      TEXT NOT NULL,
    audio_referencia       TEXT CHECK (audio_referencia IS NULL OR canal = 'voz'),
    intencao               TEXT CHECK (intencao IN (
                               'consultar_documentos_normativos',
                               'consultar_projeto_sintetico',
                               'orientar_mapa_beneficios',
                               'orientar_tap',
                               'orientar_entregas_cronograma',
                               'orientar_avanco_mensal',
                               'orientar_riscos_problemas',
                               'analisar_completude_coerencia',
                               'gerar_alertas_pendencias',
                               'fora_do_catalogo')),
    resultado              TEXT NOT NULL CHECK (resultado IN
                               ('sucesso', 'esclarecimento', 'recusada', 'falha')),
    categoria_erro         TEXT,
    tempo_processamento_ms INTEGER CHECK (tempo_processamento_ms >= 0),
    feedback_usuario       TEXT
);

CREATE TABLE auditoria.interacao_artefato (
    interacao_id INTEGER NOT NULL REFERENCES auditoria.interacao (id),
    artefato_id  INTEGER NOT NULL REFERENCES portfolio.artefato (id),
    PRIMARY KEY (interacao_id, artefato_id)
);

CREATE TABLE auditoria.notificacao (
    id           INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    pendencia_id INTEGER NOT NULL REFERENCES portfolio.pendencia (id) ON DELETE CASCADE,
    usuario_id   INTEGER NOT NULL REFERENCES portfolio.usuario (id),
    data_envio   TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (pendencia_id, usuario_id)
);

-- Imutabilidade dos registros de auditoria (RNF04)
REVOKE UPDATE, DELETE ON auditoria.interacao, auditoria.interacao_artefato,
                        auditoria.notificacao FROM PUBLIC;

-- Exceção pontual: a avaliação do usuário chega depois da resposta, portanto
-- o papel da aplicação recebe permissão de atualização restrita a essa coluna:
-- GRANT UPDATE (feedback_usuario) ON auditoria.interacao TO <papel_da_aplicacao>;

-- Índices dos acessos frequentes dos cenários da seção 2.2.2
CREATE INDEX idx_artefato_projeto        ON portfolio.artefato (projeto_id);
CREATE INDEX idx_campo_artefato_artefato ON portfolio.campo_artefato (artefato_id);
CREATE INDEX idx_pendencia_verificacao   ON portfolio.pendencia (situacao, prazo);
CREATE INDEX idx_interacao_usuario_data  ON auditoria.interacao (usuario_id, data_hora);

-- =============================================================================
-- Integração por webhook (Seção 5.1)
-- =============================================================================

CREATE SCHEMA integracao;

-- Uma linha por origem observada. É o que permite trocar a conta, o site ou a
-- biblioteca sem tocar no código: `recurso` guarda o caminho assinado no
-- provedor, e é a única diferença entre observar o OneDrive de desenvolvimento
-- ('/me/drive/root') e a biblioteca de documentos do SharePoint do parceiro
-- ('/drives/{drive-id}/root') — os dois são `driveItem`, então o mesmo tradutor
-- serve aos dois.
--
-- `subscription_id` guarda o identificador que o provedor devolve ao criar a
-- origem: a assinatura, no Microsoft Graph, e o canal, no Google Drive. É contra
-- esta coluna que o verificador de autenticidade confronta cada entrega, e é por
-- isso que desativar a linha invalida na hora tudo que tenha sido capturado antes.
CREATE TABLE integracao.conexao (
    id              INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    provedor        TEXT NOT NULL CHECK (provedor IN ('microsoft_graph', 'google_drive', 'power_automate')),
    conta           TEXT NOT NULL,
    recurso         TEXT NOT NULL,
    client_state    TEXT NOT NULL,
    subscription_id TEXT UNIQUE,
    -- Exigido pelo `channels.stop` do Google, que encerra o canal pelo par
    -- (id, resourceId). Nulo no Microsoft Graph, que apaga a assinatura só
    -- pelo identificador dela.
    recurso_id      TEXT,
    expira_em       TIMESTAMPTZ,
    delta_token     TEXT,
    refresh_token   TEXT,
    ativa           BOOLEAN     NOT NULL DEFAULT TRUE,
    -- Marcado pelo processador quando chega uma notificação que exige varredura.
    -- A notificação diz que algo mudou, não o que mudou: descobrir exige uma
    -- chamada `delta` (Graph) ou `changes.list` (Drive), que não cabe na janela
    -- de resposta ao provedor. Esta coluna é o ponto de encaixe do consumidor da
    -- Sprint 5, que varre e limpa a marca.
    delta_pendente  BOOLEAN     NOT NULL DEFAULT FALSE,
    criada_em       TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (provedor, conta, recurso)
);

-- Registro imutável de cada entrega recebida. A unicidade composta é o critério
-- de idempotência exigido pelo caso TI-37: a mesma notificação reentregue pelo
-- provedor encontra a linha já gravada e não repete o efeito.
--
-- `concluido_em` nulo significa entrega registrada mas ainda não processada —
-- o estado em que fica um evento que devolveu 5xx. É por isso que a reentrega
-- consegue retomá-lo em vez de ser descartada como duplicata.
-- As colunas do envelope são anuláveis porque a tabela também guarda a entrega
-- que chegou autenticada mas não pôde ser interpretada (situacao 'recusado',
-- caso TI-39): ela não tem envelope, só o corpo bruto e o motivo. Manter tudo
-- numa tabela só preserva uma ordem única do que o provedor enviou, que é o que
-- a auditoria precisa responder. O UNIQUE convive com isso porque o PostgreSQL
-- não considera dois NULL como iguais.
CREATE TABLE auditoria.evento_webhook (
    id              INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    conexao_id      INTEGER REFERENCES integracao.conexao (id),
    provedor        TEXT        NOT NULL,
    subscription_id TEXT,
    notificacao_id  TEXT,
    tipo            TEXT,
    versao_envelope TEXT,
    correlacao      TEXT,
    conteudo        JSONB,
    corpo_bruto     TEXT,
    motivo          TEXT,
    recebido_em     TIMESTAMPTZ NOT NULL DEFAULT now(),
    concluido_em    TIMESTAMPTZ,
    situacao        TEXT CHECK (situacao IN ('processado', 'ignorado', 'recusado')),
    UNIQUE (provedor, subscription_id, notificacao_id),
    -- Ou é um evento com envelope, ou é uma recusa com motivo. Nunca os dois,
    -- nunca nenhum dos dois.
    CONSTRAINT ck_evento_ou_recusa CHECK (
        (situacao = 'recusado' AND motivo IS NOT NULL AND notificacao_id IS NULL)
        OR (situacao <> 'recusado' AND notificacao_id IS NOT NULL)
        OR (situacao IS NULL AND notificacao_id IS NOT NULL)
    )
);

-- Imutabilidade da trilha de webhook (RNF04), no mesmo regime das demais
-- tabelas de auditoria.
REVOKE UPDATE, DELETE ON auditoria.evento_webhook FROM PUBLIC;

-- Exceção pontual, análoga à de `interacao.feedback_usuario`: a conclusão do
-- processamento só é conhecida depois da gravação, portanto o papel da
-- aplicação recebe permissão de atualização restrita a essas duas colunas:
-- GRANT UPDATE (concluido_em, situacao) ON auditoria.evento_webhook TO <papel_da_aplicacao>;

-- O upsert do artefato disparado pelo webhook precisa de um critério de
-- conflito. `referencia` é o localizador do documento no repositório de origem
-- (o item da lista do SharePoint), e é único dentro de um projeto.
ALTER TABLE portfolio.artefato ADD CONSTRAINT uq_artefato_referencia
    UNIQUE (projeto_id, referencia);

-- Índice parcial para a varredura de pendentes: só as entregas não concluídas
-- interessam, e elas são a minoria.
CREATE INDEX idx_evento_webhook_pendente ON auditoria.evento_webhook (recebido_em)
    WHERE concluido_em IS NULL;
