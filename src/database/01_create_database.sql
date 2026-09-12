-- =============================================================================
-- AZ1 — Banco relacional da solução
--
-- Implementa a modelagem da Seção 3.6 do docs/Projeto.md, com as extensões
-- descritas no README.md desta pasta. Alvo: PostgreSQL 15+ (Supabase).
--
-- Divisão de responsabilidade entre os dois bancos da solução:
--   - o conteúdo dos documentos é vetorizado e vive em vecs.documentos_metro,
--     no MESMO banco (extensão pgvector), gravado pelo pipeline de src/rag;
--   - este script cria a parte relacional: identidade, domínio do portfólio,
--     conversas, trilha de auditoria, avaliações e eventos de plataforma;
--   - a integração por webhook (Microsoft Graph e Google Drive, Seção 5.1) tem
--     schema e tabela de auditoria próprios, acrescentados ao final deste
--     arquivo (Seção 7).
--
-- Manter os dois no mesmo banco é o que permite ligar uma resposta do agente
-- ao chunk que a fundamentou (auditoria.mensagem_fonte) sem consulta cruzada
-- entre servidores — condição dos RNF04, RNF11 e RNF12.
--
-- Execução em ambiente limpo:
--   psql "$SUPABASE_DB_URL" -v ON_ERROR_STOP=1 -f 01_create_database.sql
-- =============================================================================

\set ON_ERROR_STOP on

BEGIN;

-- Dados operacionais consultados pelo agente.
CREATE SCHEMA IF NOT EXISTS portfolio;
-- Trilha de interações, fontes, avaliações e eventos (decisão 7 da Seção 3.6.7).
CREATE SCHEMA IF NOT EXISTS auditoria;

COMMENT ON SCHEMA portfolio IS
    'Dados operacionais do portfólio de projetos do PMO. Leitura e escrita pela aplicação.';
COMMENT ON SCHEMA auditoria IS
    'Trilha de auditoria (RNF04, RNF09). Somente inserção e leitura; atualização restrita por coluna.';

-- gen_random_uuid(), usado pelas chaves de conversa.
CREATE EXTENSION IF NOT EXISTS pgcrypto;


-- =============================================================================
-- 1. DOMÍNIO DO PORTFÓLIO
-- =============================================================================

-- Agrupamento organizacional de projetos. Na base sintética corresponde ao
-- subportfólio declarado na planilha de portfólio ("Expansão da Rede",
-- "Gestão e Finanças", ...), que é o nível pelo qual o PMO agrupa de fato.
CREATE TABLE portfolio.portfolio (
    id            INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    nome          TEXT    NOT NULL,
    ano_exercicio INTEGER NOT NULL,
    UNIQUE (nome, ano_exercicio)
);

-- Profissional autorizado a usar o agente.
--
-- auth_user_id existe para a frente de autenticação (RNF02, SSO Microsoft ou
-- Google) e é NULO enquanto ela não for implementada. A referência a
-- auth.users fica declarada como comentário, e não como FK, porque criar a FK
-- agora impediria semear usuários antes de existirem contas de SSO. Quando a
-- autenticação entrar, basta preencher a coluna e promovê-la a FK:
--
--   ALTER TABLE portfolio.usuario
--     ADD CONSTRAINT usuario_auth_user_fk
--     FOREIGN KEY (auth_user_id) REFERENCES auth.users (id) ON DELETE SET NULL;
--
-- Nenhuma senha, token ou segredo é armazenado aqui: o RNF09 proíbe, e o
-- provedor de SSO é quem detém a credencial.
CREATE TABLE portfolio.usuario (
    id           INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    auth_user_id UUID UNIQUE,
    nome         TEXT NOT NULL,
    email        TEXT NOT NULL UNIQUE,
    perfil       TEXT NOT NULL
                 CHECK (perfil IN ('diretor', 'pmo', 'lider_projeto')),
    ativo        BOOLEAN     NOT NULL DEFAULT TRUE,
    criado_em    TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON COLUMN portfolio.usuario.auth_user_id IS
    'Identidade no provedor de SSO (auth.users.id). Nulo até a frente de autenticação do RNF02.';
COMMENT ON COLUMN portfolio.usuario.perfil IS
    'Perfil profissional das personas. Não concede permissões distintas (decisão 1 da Seção 3.6.7).';

CREATE TABLE portfolio.projeto (
    id                    INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    codigo                TEXT NOT NULL UNIQUE,
    nome                  TEXT NOT NULL,
    fase                  TEXT NOT NULL,
    status                TEXT NOT NULL,
    data_inicio           DATE,
    data_termino_prevista DATE,
    percentual_previsto   NUMERIC(5,2) NOT NULL DEFAULT 0
                          CHECK (percentual_previsto BETWEEN 0 AND 100),
    percentual_avanco     NUMERIC(5,2) NOT NULL DEFAULT 0
                          CHECK (percentual_avanco BETWEEN 0 AND 100),
    -- Desvio em pontos percentuais. Coluna gerada pela mesma razão da decisão 2
    -- da Seção 3.6.7: derivada de duas colunas da própria linha, não pode
    -- divergir delas, e é o número que a persona do Diretor pede diretamente.
    desvio_pp             NUMERIC(6,2) GENERATED ALWAYS AS
                          (percentual_avanco - percentual_previsto) STORED,
    portfolio_id          INTEGER NOT NULL REFERENCES portfolio.portfolio (id),
    lider_id              INTEGER NOT NULL REFERENCES portfolio.usuario (id)
);

COMMENT ON COLUMN portfolio.projeto.fase IS
    'Fase do ciclo de vida: Iniciação, Execução, Encerramento.';
COMMENT ON COLUMN portfolio.projeto.status IS
    'Situação corrente apurada pelo PMO: Dentro do previsto, Atrasado, Em risco, Crítico, Concluído, ...';

-- Dependências declaradas entre projetos na planilha de portfólio. Sustenta as
-- consultas de impacto cruzado ("o que depende do SYN-08?"), que o modelo
-- puramente hierárquico portfólio → projeto não consegue responder.
CREATE TABLE portfolio.projeto_relacionado (
    projeto_id      INTEGER NOT NULL REFERENCES portfolio.projeto (id) ON DELETE CASCADE,
    relacionado_id  INTEGER NOT NULL REFERENCES portfolio.projeto (id) ON DELETE CASCADE,
    relacao         TEXT    NOT NULL,
    PRIMARY KEY (projeto_id, relacionado_id),
    CHECK (projeto_id <> relacionado_id)
);

-- Documento que integra a documentação do projeto e pode ser citado como fonte.
--
-- `referencia` guarda o caminho RELATIVO à raiz do repositório de documentos,
-- e não o caminho absoluto que o indexador gravou em vecs.documentos_metro.
-- O caminho absoluto aponta para a pasta pessoal de quem rodou a indexação e
-- não é exibível ao usuário como fonte (RF03).
CREATE TABLE portfolio.artefato (
    id         INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    projeto_id INTEGER NOT NULL REFERENCES portfolio.projeto (id) ON DELETE CASCADE,
    tipo       TEXT NOT NULL,
    referencia TEXT NOT NULL,
    titulo     TEXT,
    data       TIMESTAMPTZ NOT NULL,
    versao     TEXT,
    UNIQUE (projeto_id, referencia)
);

COMMENT ON COLUMN portfolio.artefato.tipo IS
    'Alinhado a vecs.documentos_metro.metadata->>''tipo_documento'': termo_abertura, cronograma, mapa_beneficios, riscos_problemas, mudancas, relatorio_encerramento, portfolio.';
COMMENT ON COLUMN portfolio.artefato.referencia IS
    'Caminho relativo à raiz do repositório de documentos. É o localizador exibido como fonte (RF03).';

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

-- Item em aberto originado por um projeto: risco ou problema registrado na
-- planilha 04_Riscos_e_Problemas de cada projeto.
--
-- O domínio de `situacao` inclui 'materializada' além dos três estados da
-- Seção 3.6.5. A base sintética usa esse estado para o risco que se concretizou,
-- e colapsá-lo em 'em_tratamento' faria a resposta do agente vinda do banco
-- divergir do documento vetorizado — exatamente a incoerência que o RNF12 mede.
CREATE TABLE portfolio.pendencia (
    id            INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    projeto_id    INTEGER NOT NULL REFERENCES portfolio.projeto (id) ON DELETE CASCADE,
    codigo        TEXT,
    tipo          TEXT NOT NULL,
    titulo        TEXT NOT NULL,
    descricao     TEXT NOT NULL,
    criticidade   TEXT,
    responsavel   TEXT,
    acao_resposta TEXT,
    prazo         DATE,
    situacao      TEXT NOT NULL DEFAULT 'aberta'
                  CHECK (situacao IN ('aberta', 'em_tratamento', 'materializada', 'resolvida')),
    UNIQUE (projeto_id, codigo)
);

CREATE TABLE portfolio.usuario_projeto (
    usuario_id INTEGER NOT NULL REFERENCES portfolio.usuario (id) ON DELETE CASCADE,
    projeto_id INTEGER NOT NULL REFERENCES portfolio.projeto (id) ON DELETE CASCADE,
    PRIMARY KEY (usuario_id, projeto_id)
);


-- =============================================================================
-- 2. CONVERSAS E TRILHA DE AUDITORIA
-- =============================================================================

-- Uma conversa agrupa a sequência prompt 1 → resposta 1 → prompt 2 → ...
--
-- A chave é UUID e não uma identity porque o identificador nasce no cliente:
-- src/frontend/src/pages/AgentPage.jsx gera crypto.randomUUID() e o envia em
-- ChatRequest.conversation_id antes de a primeira mensagem existir no banco.
-- O DEFAULT cobre quem criar a conversa pelo servidor.
--
-- Não há DELETE: arquivar preenche `arquivada_em`. O RNF09 exige retenção
-- mínima de 90 dias e proteção contra exclusão, então o "apagar conversa" da
-- interface é ocultação, não remoção.
CREATE TABLE auditoria.conversa (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    usuario_id    INTEGER NOT NULL REFERENCES portfolio.usuario (id),
    titulo        TEXT,
    criada_em     TIMESTAMPTZ NOT NULL DEFAULT now(),
    atualizada_em TIMESTAMPTZ NOT NULL DEFAULT now(),
    arquivada_em  TIMESTAMPTZ
);

COMMENT ON COLUMN auditoria.conversa.titulo IS
    'Rótulo exibido na barra lateral, derivado da primeira mensagem. Atualizável pela aplicação.';
COMMENT ON COLUMN auditoria.conversa.arquivada_em IS
    'Exclusão lógica. A linha permanece para atender à retenção do RNF09.';

-- Uma linha por turno da conversa: o prompt do usuário e a resposta do agente
-- são linhas irmãs, distinguidas por `papel` e ordenadas por `ordem`.
--
-- Modelar assim, e não como uma linha por par pergunta-resposta, é o que
-- permite guardar o TEXTO da resposta (que a Seção 3.6.5 não previa, tendo
-- apenas o enum `resultado`) e atribuir fontes à resposta — sem elas o RNF12,
-- que confronta afirmações da resposta com as fontes citadas, não é verificável.
--
-- As colunas específicas de cada papel são anuladas pelas restrições abaixo,
-- de modo que o banco não admita uma resposta do agente com intenção
-- classificada, nem um prompt do usuário com tempo de processamento.
CREATE TABLE auditoria.mensagem (
    id                     BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    conversa_id            UUID    NOT NULL REFERENCES auditoria.conversa (id),
    ordem                  INTEGER NOT NULL CHECK (ordem > 0),
    papel                  TEXT    NOT NULL CHECK (papel IN ('usuario', 'agente')),

    -- Formato pelo qual a mensagem entrou ou saiu. 'texto' e 'audio' são os
    -- dois canais implementados (RF01); a Seção 3.2.6 prevê Text to Speech,
    -- que produz respostas do agente em 'audio'. Estender o domínio (anexo,
    -- imagem) é uma alteração desta restrição e do adaptador correspondente.
    formato                TEXT    NOT NULL CHECK (formato IN ('texto', 'audio')),

    -- Sempre o texto: o prompt digitado, a transcrição do áudio enviado, ou a
    -- resposta gerada. É o que a auditoria lê, independentemente do formato.
    conteudo               TEXT    NOT NULL,

    -- Identificador do objeto no armazenamento S3/MinIO ("aud_<hex>", chave
    -- "incoming/<audio_id>"), preenchido apenas quando formato = 'audio'.
    audio_referencia       TEXT,
    audio_duracao_s        NUMERIC(8,2) CHECK (audio_duracao_s >= 0),
    transcricao_confianca  NUMERIC(5,4) CHECK (transcricao_confianca BETWEEN 0 AND 1),

    -- Somente para papel = 'usuario': saída do pipeline de PLN (Seção 3.3).
    -- O domínio replica o catálogo de intenções da Seção 3.1 (decisão 4 da
    -- Seção 3.6.7) e deve ser mantido sincronizado com pln/classificador.py.
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
    confianca_intencao     NUMERIC(5,4) CHECK (confianca_intencao BETWEEN 0 AND 1),

    -- Somente para papel = 'agente'.
    resultado              TEXT CHECK (resultado IN
                               ('sucesso', 'esclarecimento', 'recusada', 'falha')),
    categoria_erro         TEXT,
    modelo                 TEXT,
    tempo_processamento_ms INTEGER CHECK (tempo_processamento_ms >= 0),

    criada_em              TIMESTAMPTZ NOT NULL DEFAULT now(),

    UNIQUE (conversa_id, ordem),

    -- Áudio só se referencia quando o formato é áudio.
    CONSTRAINT mensagem_audio_coerente CHECK (
        (formato = 'audio') OR
        (audio_referencia IS NULL AND audio_duracao_s IS NULL
         AND transcricao_confianca IS NULL)
    ),
    -- Intenção e confiança pertencem ao prompt; resultado, modelo e tempo
    -- pertencem à resposta. Cada papel anula as colunas do outro.
    CONSTRAINT mensagem_papel_coerente CHECK (
        CASE papel
            WHEN 'usuario' THEN
                resultado IS NULL AND categoria_erro IS NULL
                AND modelo IS NULL AND tempo_processamento_ms IS NULL
            WHEN 'agente' THEN
                intencao IS NULL AND confianca_intencao IS NULL
                AND resultado IS NOT NULL
        END
    )
);

COMMENT ON TABLE auditoria.mensagem IS
    'Turnos da conversa. Substitui a tabela interacao da Seção 3.6.5, acrescentando o texto da resposta.';

-- Fontes que fundamentaram uma resposta do agente (RF03, RNF04, RNF11, RNF12).
--
-- Duas decisões justificam o formato:
--
-- 1. `chunk_id` referencia vecs.documentos_metro(id) SEM chave estrangeira. O
--    id do chunk é o md5 do próprio conteúdo (rag/indexador.py::_chunk_id), de
--    modo que reindexar um documento produz ids novos. Uma FK obrigaria a
--    escolher entre travar a reindexação e apagar a trilha — as duas
--    inaceitáveis diante da imutabilidade do RNF09.
--
-- 2. Os metadados são copiados no momento da resposta, e não lidos por junção.
--    A fonte citada precisa continuar legível na auditoria mesmo depois de o
--    documento ser reindexado, movido ou removido do índice.
--
-- `artefato_id` é opcional de propósito. A Seção 3.6.7 registra que os
-- documentos normativos (INT-01) não pertencem a projeto algum e, portanto,
-- não têm artefato correspondente; deixá-lo nulo resolve essa limitação sem
-- abandonar o vínculo relacional quando ele existe.
CREATE TABLE auditoria.mensagem_fonte (
    id             BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    mensagem_id    BIGINT  NOT NULL REFERENCES auditoria.mensagem (id) ON DELETE CASCADE,
    posicao        INTEGER NOT NULL CHECK (posicao > 0),
    chunk_id       TEXT    NOT NULL,
    score          NUMERIC(7,6),
    artefato_id    INTEGER REFERENCES portfolio.artefato (id),
    projeto_codigo TEXT,
    tipo_documento TEXT,
    arquivo_origem TEXT NOT NULL,
    secao          TEXT,
    trecho         TEXT,
    UNIQUE (mensagem_id, chunk_id),
    UNIQUE (mensagem_id, posicao)
);

COMMENT ON COLUMN auditoria.mensagem_fonte.posicao IS
    'Ordem de relevância devolvida pelo retriever (1 = mais próximo).';
COMMENT ON COLUMN auditoria.mensagem_fonte.trecho IS
    'Cópia do texto do chunk no momento da resposta, base da verificação do RNF12.';

-- Avaliação do usuário sobre uma resposta ou sobre a conversa inteira.
--
-- Substitui a coluna feedback_usuario da Seção 3.6.5, que era um TEXT solto:
-- sem nota, sem data e sem autor não era possível medir satisfação nem
-- correlacionar avaliação negativa a intenção, fonte ou tempo de resposta.
CREATE TABLE auditoria.avaliacao (
    id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    usuario_id  INTEGER NOT NULL REFERENCES portfolio.usuario (id),
    conversa_id UUID   REFERENCES auditoria.conversa (id),
    mensagem_id BIGINT REFERENCES auditoria.mensagem (id),
    polaridade  TEXT CHECK (polaridade IN ('positiva', 'negativa')),
    nota        SMALLINT CHECK (nota BETWEEN 1 AND 5),
    motivo      TEXT CHECK (motivo IN (
                    'resposta_incorreta',
                    'fonte_irrelevante',
                    'resposta_incompleta',
                    'nao_entendeu_pergunta',
                    'demorou_demais',
                    'resposta_util',
                    'outro')),
    comentario  TEXT,
    criada_em   TIMESTAMPTZ NOT NULL DEFAULT now(),

    -- A avaliação recai sobre exatamente um alvo: uma mensagem OU a conversa.
    CONSTRAINT avaliacao_alvo_unico
        CHECK (num_nonnulls(conversa_id, mensagem_id) = 1),
    -- Um polegar ou uma nota; um comentário sozinho não é avaliação.
    CONSTRAINT avaliacao_tem_juizo
        CHECK (polaridade IS NOT NULL OR nota IS NOT NULL)
);

-- Uma avaliação por usuário por alvo; reavaliar é atualizar (ver os GRANTs
-- de coluna no fim deste arquivo), não empilhar linhas.
CREATE UNIQUE INDEX uq_avaliacao_mensagem
    ON auditoria.avaliacao (usuario_id, mensagem_id) WHERE mensagem_id IS NOT NULL;
CREATE UNIQUE INDEX uq_avaliacao_conversa
    ON auditoria.avaliacao (usuario_id, conversa_id) WHERE conversa_id IS NOT NULL;

-- Eventos de uso da plataforma que não são solicitações ao agente.
--
-- Separados de `mensagem` porque têm outro ciclo de vida e outra pergunta de
-- negócio: `mensagem` responde "o que o agente respondeu e com base em quê",
-- `evento_plataforma` responde "quem esteve na plataforma e o que fez".
--
-- `usuario_id` admite nulo para registrar tentativa de acesso sem identidade
-- resolvida. `detalhe` NÃO pode conter senha, token ou qualquer segredo — o
-- RNF09 proíbe explicitamente, e este é o campo com maior risco de vazá-los.
CREATE TABLE auditoria.evento_plataforma (
    id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    usuario_id  INTEGER REFERENCES portfolio.usuario (id),
    tipo        TEXT NOT NULL CHECK (tipo IN (
                    'login',
                    'login_falho',
                    'logout',
                    'conversa_criada',
                    'conversa_renomeada',
                    'conversa_arquivada',
                    'conversa_exportada',
                    'audio_enviado',
                    'audio_recusado',
                    'erro_aplicacao')),
    conversa_id UUID REFERENCES auditoria.conversa (id),
    origem      TEXT CHECK (origem IN ('web', 'api', 'agendador')),
    detalhe     JSONB NOT NULL DEFAULT '{}'::jsonb,
    ocorrido_em TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON COLUMN auditoria.evento_plataforma.detalhe IS
    'Contexto livre do evento. Proibido armazenar senhas, tokens ou segredos (RNF09).';

-- Registro dos envios da notificação proativa (RF05, RNF09). A unicidade
-- composta dá ao Agendador um critério idempotente: verificar de novo não
-- reenvia o mesmo alerta ao mesmo usuário.
CREATE TABLE auditoria.notificacao (
    id           INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    pendencia_id INTEGER NOT NULL REFERENCES portfolio.pendencia (id) ON DELETE CASCADE,
    usuario_id   INTEGER NOT NULL REFERENCES portfolio.usuario (id),
    canal        TEXT NOT NULL DEFAULT 'email'
                 CHECK (canal IN ('email', 'interface')),
    data_envio   TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (pendencia_id, usuario_id)
);


-- =============================================================================
-- 3. ÍNDICES DOS ACESSOS FREQUENTES
-- =============================================================================

CREATE INDEX idx_projeto_portfolio       ON portfolio.projeto (portfolio_id);
CREATE INDEX idx_projeto_lider           ON portfolio.projeto (lider_id);
CREATE INDEX idx_artefato_projeto        ON portfolio.artefato (projeto_id);
CREATE INDEX idx_campo_artefato_artefato ON portfolio.campo_artefato (artefato_id);
-- Consulta do Agendador do cenário 3: pendências abertas por prazo.
CREATE INDEX idx_pendencia_verificacao   ON portfolio.pendencia (situacao, prazo);
CREATE INDEX idx_pendencia_projeto       ON portfolio.pendencia (projeto_id);

-- Barra lateral: conversas não arquivadas do usuário, mais recentes primeiro.
CREATE INDEX idx_conversa_usuario_recente
    ON auditoria.conversa (usuario_id, atualizada_em DESC)
    WHERE arquivada_em IS NULL;
-- Carga de uma conversa na ordem em que foi vivida.
CREATE INDEX idx_mensagem_conversa_ordem ON auditoria.mensagem (conversa_id, ordem);
-- Relatórios de auditoria por período e por intenção (RNF01, RNF03, RNF09).
CREATE INDEX idx_mensagem_criada_em      ON auditoria.mensagem (criada_em);
CREATE INDEX idx_mensagem_intencao       ON auditoria.mensagem (intencao)
    WHERE intencao IS NOT NULL;
-- "Quais respostas citaram este chunk / este artefato?" (RNF12).
CREATE INDEX idx_mensagem_fonte_mensagem ON auditoria.mensagem_fonte (mensagem_id);
CREATE INDEX idx_mensagem_fonte_chunk    ON auditoria.mensagem_fonte (chunk_id);
CREATE INDEX idx_mensagem_fonte_artefato ON auditoria.mensagem_fonte (artefato_id)
    WHERE artefato_id IS NOT NULL;
CREATE INDEX idx_evento_usuario_data     ON auditoria.evento_plataforma (usuario_id, ocorrido_em);
CREATE INDEX idx_evento_tipo_data        ON auditoria.evento_plataforma (tipo, ocorrido_em);


-- =============================================================================
-- 4. GATILHOS
-- =============================================================================

-- Mantém conversa.atualizada_em coerente com a última mensagem, para que a
-- ordenação da barra lateral não dependa de a aplicação lembrar de atualizar.
CREATE OR REPLACE FUNCTION auditoria.tocar_conversa()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = auditoria, pg_temp
AS $$
BEGIN
    UPDATE auditoria.conversa
       SET atualizada_em = NEW.criada_em
     WHERE id = NEW.conversa_id;
    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_mensagem_toca_conversa
    AFTER INSERT ON auditoria.mensagem
    FOR EACH ROW EXECUTE FUNCTION auditoria.tocar_conversa();


-- =============================================================================
-- 5. VISÕES DE LEITURA
-- =============================================================================

-- Conversa com a resposta e as fontes já reunidas, no formato que a auditoria
-- e a tela de histórico consomem. Evita que cada consumidor reescreva a
-- junção de quatro tabelas — e que cada um a escreva de um jeito diferente.
CREATE VIEW auditoria.vw_turno AS
SELECT
    c.id                        AS conversa_id,
    c.usuario_id,
    u.nome                      AS usuario_nome,
    c.titulo                    AS conversa_titulo,
    p.ordem                     AS ordem_prompt,
    p.formato                   AS formato_prompt,
    p.conteudo                  AS prompt,
    p.intencao,
    p.confianca_intencao,
    p.audio_referencia,
    r.id                        AS resposta_id,
    r.formato                   AS formato_resposta,
    r.conteudo                  AS resposta,
    r.resultado,
    r.categoria_erro,
    r.modelo,
    r.tempo_processamento_ms,
    p.criada_em                 AS perguntado_em,
    r.criada_em                 AS respondido_em,
    (SELECT count(*) FROM auditoria.mensagem_fonte f WHERE f.mensagem_id = r.id)
                                AS qtd_fontes,
    a.polaridade                AS avaliacao_polaridade,
    a.nota                      AS avaliacao_nota,
    a.motivo                    AS avaliacao_motivo
FROM auditoria.mensagem p
JOIN auditoria.conversa c   ON c.id = p.conversa_id
JOIN portfolio.usuario  u   ON u.id = c.usuario_id
LEFT JOIN auditoria.mensagem r
       ON r.conversa_id = p.conversa_id
      AND r.ordem = p.ordem + 1
      AND r.papel = 'agente'
LEFT JOIN auditoria.avaliacao a ON a.mensagem_id = r.id
WHERE p.papel = 'usuario';

COMMENT ON VIEW auditoria.vw_turno IS
    'Um par prompt/resposta por linha, com intenção, desfecho, contagem de fontes e avaliação (RNF04).';

-- Situação consolidada de cada projeto, com o que o Diretor pergunta primeiro.
CREATE VIEW portfolio.vw_projeto_situacao AS
SELECT
    pr.id,
    pr.codigo,
    pr.nome,
    pf.nome  AS portfolio,
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
JOIN portfolio.portfolio pf ON pf.id = pr.portfolio_id
JOIN portfolio.usuario   li ON li.id = pr.lider_id;


-- =============================================================================
-- 6. PROTEÇÃO DA TRILHA DE AUDITORIA (RNF09)
-- =============================================================================

-- Os registros de auditoria admitem inserção e leitura, não alteração nem
-- exclusão. As três exceções abaixo são atualizações que a interface precisa e
-- que não reescrevem o que foi registrado, concedidas em nível de coluna.
REVOKE UPDATE, DELETE ON auditoria.mensagem,
                         auditoria.mensagem_fonte,
                         auditoria.evento_plataforma,
                         auditoria.notificacao
    FROM PUBLIC;

REVOKE DELETE ON auditoria.conversa, auditoria.avaliacao FROM PUBLIC;

-- As duas atualizações permitidas — renomear/arquivar uma conversa e reavaliar
-- uma resposta — são concedidas em nível de coluna a um papel nomeado, não a
-- PUBLIC. O papel e os GRANTs ficam em 03_rls_policies.sql, junto das demais
-- decisões de acesso.


-- =============================================================================
-- 7. INTEGRAÇÃO POR WEBHOOK (Seção 5.1)
-- =============================================================================

-- Assinaturas e canais de notificação externos que alimentam o receptor de
-- webhook, e a trilha imutável das entregas recebidas por eles.
CREATE SCHEMA IF NOT EXISTS integracao;

COMMENT ON SCHEMA integracao IS
    'Origens externas observadas por webhook (Microsoft Graph, Google Drive). Somente a aplicação lê e escreve.';

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

-- Registro de recebimentos. O UNIQUE atende ao TI-37 somente quando o provedor
-- oferece identidade estável de evento ou versão. Avisos mínimos OneDrive
-- recebem UUID por recebimento, portanto não são deduplicados por esta chave.
-- Neles, repetir delta_pendente = TRUE preserva o estado, mas registra e
-- processa cada recebimento; não há garantia de execução única.
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

COMMENT ON TABLE auditoria.evento_webhook IS
    'Trilha de recebimentos de webhook. UNIQUE deduplica somente identidade estável de evento ou versão (TI-37). Avisos mínimos OneDrive geram uma linha por recebimento; repetir delta_pendente = TRUE preserva o estado.';

-- Imutabilidade da trilha de webhook (RNF09), no mesmo regime da Seção 6.
REVOKE UPDATE, DELETE ON auditoria.evento_webhook FROM PUBLIC;

-- Exceção pontual, análoga às da Seção 6: a conclusão do processamento só é
-- conhecida depois da gravação, portanto o papel da aplicação recebe permissão
-- de atualização restrita a estas duas colunas:
-- O GRANT executável e as políticas estão em 06_webhook_permissions.sql,
-- também chamado por 03_rls_policies.sql. O receptor assume az1_webhook.

-- Índice parcial para a varredura de pendentes: só as entregas não concluídas
-- interessam, e elas são a minoria.
CREATE INDEX idx_evento_webhook_pendente ON auditoria.evento_webhook (recebido_em)
    WHERE concluido_em IS NULL;

COMMIT;

-- =============================================================================
-- Próximos passos, nesta ordem:
--   02_initial_data.sql  — carga da base sintética
--   03_rls_policies.sql  — Row Level Security e papéis de acesso
-- =============================================================================
