-- =============================================================================
-- AZ1 — Verificação do banco (T25: validar leitura e escrita)
--
-- Percorre uma conversa completa — dois turnos, um por texto e um por voz —
-- gravando prompt, resposta, fontes, avaliação e evento de plataforma; depois
-- tenta gravar oito registros inválidos e confirma que o banco os recusa.
--
-- Roda inteiro dentro de uma transação que termina em ROLLBACK: verifica sem
-- deixar resíduo. Pode ser executado quantas vezes for preciso, inclusive
-- contra um banco já em uso.
--
--   psql "$SUPABASE_DB_URL" -X -f 04_verificacao.sql
--
-- Não use -v ON_ERROR_STOP=1 aqui: a segunda metade PROVOCA erros de propósito.
-- =============================================================================

BEGIN;

\echo ''
\echo '=========================================================================='
\echo ' PARTE 1 — Caminho feliz: uma conversa de dois turnos'
\echo '=========================================================================='

-- Turno 1 por texto, turno 2 por voz. As fontes usam chunks REAIS do índice
-- vetorial, para exercer a ligação entre a resposta e o que a fundamentou.
CREATE TEMP TABLE _ctx AS
SELECT (SELECT id FROM portfolio.usuario WHERE perfil = 'diretor' LIMIT 1) AS usuario_id,
       gen_random_uuid()                                                   AS conversa_id;

INSERT INTO auditoria.conversa (id, usuario_id, titulo)
SELECT conversa_id, usuario_id, 'Situação dos projetos atrasados' FROM _ctx;

INSERT INTO auditoria.evento_plataforma (usuario_id, tipo, conversa_id, origem, detalhe)
SELECT usuario_id, 'conversa_criada', conversa_id, 'web', '{"tela": "chat"}'::jsonb FROM _ctx;

-- Turno 1 — prompt digitado.
INSERT INTO auditoria.mensagem
    (conversa_id, ordem, papel, formato, conteudo, intencao, confianca_intencao)
SELECT conversa_id, 1, 'usuario', 'texto',
       'Quais projetos estão mais atrasados no portfólio?',
       'consultar_projeto_sintetico', 0.9120
  FROM _ctx;

-- Turno 1 — resposta do agente.
INSERT INTO auditoria.mensagem
    (conversa_id, ordem, papel, formato, conteudo, resultado, modelo, tempo_processamento_ms)
SELECT conversa_id, 2, 'agente', 'texto',
       'Os dois maiores desvios são o SYN-01, com -18 p.p., e o SYN-07, com -14 p.p.',
       'sucesso', 'gemini-3.5-flash-lite', 2140
  FROM _ctx;

SELECT to_regclass('vecs.documentos_metro') IS NOT NULL AS tem_indice_rag \gset
\if :tem_indice_rag
-- Fontes da resposta: chunks reais do índice, com o artefato correspondente
-- resolvido pelo caminho do arquivo quando ele existe no banco.
INSERT INTO auditoria.mensagem_fonte
    (mensagem_id, posicao, chunk_id, score, artefato_id,
     projeto_codigo, tipo_documento, arquivo_origem, secao, trecho)
SELECT m.id,
       row_number() OVER (ORDER BY v.id),
       v.id,
       0.874321,
       a.id,
       v.metadata->>'projeto_id',
       v.metadata->>'tipo_documento',
       v.metadata->>'arquivo_origem',
       v.metadata->>'secao',
       left(v.metadata->>'texto', 400)
  FROM auditoria.mensagem m
  JOIN _ctx c ON c.conversa_id = m.conversa_id AND m.ordem = 2
  JOIN LATERAL (
        SELECT * FROM vecs.documentos_metro
         WHERE metadata->>'tipo_documento' = 'portfolio' LIMIT 2
       ) v ON TRUE
  LEFT JOIN portfolio.artefato a
         ON v.metadata->>'arquivo_origem' LIKE '%' || a.referencia;

\else
\echo 'Etapa de fontes RAG não executada: índice vetorial não existe nesta base.'
\endif

-- Turno 2 — prompt por voz, com transcrição e referência ao objeto no MinIO.
INSERT INTO auditoria.mensagem
    (conversa_id, ordem, papel, formato, conteudo, audio_referencia,
     audio_duracao_s, transcricao_confianca, intencao, confianca_intencao)
SELECT conversa_id, 3, 'usuario', 'audio',
       'E quais são os riscos abertos do SYN-07?',
       'aud_9f2c1b7e4a5d40c8b1e6f3a2d7c40915', 4.31, 0.9640,
       'orientar_riscos_problemas', 0.8830
  FROM _ctx;

INSERT INTO auditoria.mensagem
    (conversa_id, ordem, papel, formato, conteudo, resultado, modelo, tempo_processamento_ms)
SELECT conversa_id, 4, 'agente', 'texto',
       'O SYN-07 tem dois itens em aberto, ambos sob a Gerência de Manutenção.',
       'sucesso', 'gemini-3.5-flash-lite', 1890
  FROM _ctx;

-- Avaliação da segunda resposta.
INSERT INTO auditoria.avaliacao (usuario_id, mensagem_id, polaridade, nota, motivo)
SELECT c.usuario_id, m.id, 'positiva', 5, 'resposta_util'
  FROM auditoria.mensagem m JOIN _ctx c ON c.conversa_id = m.conversa_id
 WHERE m.ordem = 4;

\echo ''
\echo '-- A conversa, turno a turno (view auditoria.vw_turno) --'
SELECT ordem_prompt, formato_prompt, left(prompt, 46) AS prompt, intencao,
       left(resposta, 46) AS resposta, resultado, tempo_processamento_ms AS ms,
       qtd_fontes, avaliacao_nota
  FROM auditoria.vw_turno
 WHERE conversa_id = (SELECT conversa_id FROM _ctx)
 ORDER BY ordem_prompt;

\echo ''
\echo '-- Fontes citadas pela primeira resposta (RF03, RNF12) --'
SELECT f.posicao, f.projeto_codigo, f.tipo_documento, f.secao,
       f.artefato_id IS NOT NULL AS tem_artefato, left(f.chunk_id, 12) AS chunk
  FROM auditoria.mensagem_fonte f
  JOIN auditoria.mensagem m ON m.id = f.mensagem_id
 WHERE m.conversa_id = (SELECT conversa_id FROM _ctx)
 ORDER BY f.posicao;

\echo ''
\echo '-- O gatilho atualizou conversa.atualizada_em? (deve ser t) --'
SELECT c.atualizada_em >= max(m.criada_em) AS atualizada_em_coerente
  FROM auditoria.conversa c
  JOIN auditoria.mensagem m ON m.conversa_id = c.id
 WHERE c.id = (SELECT conversa_id FROM _ctx)
 GROUP BY c.atualizada_em;


\echo ''
\echo '=========================================================================='
\echo ' PARTE 2 — O banco recusa dado incoerente'
\echo ' Cada bloco DEVE imprimir "RECUSADO (ok)". "ACEITOU" indica falha.'
\echo '=========================================================================='

-- Um teste por bloco: cada DO captura a exceção e reporta, de modo que a falha
-- de um não impeça a execução dos demais.
DO $$ BEGIN
    INSERT INTO auditoria.mensagem (conversa_id, ordem, papel, formato, conteudo, resultado)
    SELECT conversa_id, 90, 'usuario', 'texto', 'prompt com desfecho', 'sucesso' FROM _ctx;
    RAISE WARNING 'ACEITOU — prompt do usuário com resultado preenchido';
EXCEPTION WHEN check_violation THEN
    RAISE NOTICE 'RECUSADO (ok) — prompt do usuário não pode ter resultado';
END $$;

DO $$ BEGIN
    INSERT INTO auditoria.mensagem (conversa_id, ordem, papel, formato, conteudo, intencao, resultado)
    SELECT conversa_id, 91, 'agente', 'texto', 'resposta classificando intenção',
           'orientar_tap', 'sucesso' FROM _ctx;
    RAISE WARNING 'ACEITOU — resposta do agente com intenção classificada';
EXCEPTION WHEN check_violation THEN
    RAISE NOTICE 'RECUSADO (ok) — resposta do agente não classifica intenção';
END $$;

DO $$ BEGIN
    INSERT INTO auditoria.mensagem (conversa_id, ordem, papel, formato, conteudo, audio_referencia)
    SELECT conversa_id, 92, 'usuario', 'texto', 'texto com áudio', 'aud_xyz' FROM _ctx;
    RAISE WARNING 'ACEITOU — mensagem de texto com referência de áudio';
EXCEPTION WHEN check_violation THEN
    RAISE NOTICE 'RECUSADO (ok) — só mensagem de áudio referencia áudio';
END $$;

DO $$ BEGIN
    INSERT INTO auditoria.mensagem (conversa_id, ordem, papel, formato, conteudo, intencao, confianca_intencao)
    SELECT conversa_id, 93, 'usuario', 'texto', 'intenção fora do catálogo',
           'consultar_o_tempo', 0.5 FROM _ctx;
    RAISE WARNING 'ACEITOU — intenção fora do catálogo da Seção 3.1';
EXCEPTION WHEN check_violation THEN
    RAISE NOTICE 'RECUSADO (ok) — intenção fora do catálogo da Seção 3.1';
END $$;

DO $$ BEGIN
    INSERT INTO auditoria.mensagem (conversa_id, ordem, papel, formato, conteudo, intencao)
    SELECT conversa_id, 1, 'usuario', 'texto', 'ordem repetida', 'orientar_tap' FROM _ctx;
    RAISE WARNING 'ACEITOU — duas mensagens na mesma ordem da conversa';
EXCEPTION WHEN unique_violation THEN
    RAISE NOTICE 'RECUSADO (ok) — a ordem é única dentro da conversa';
END $$;

DO $$ BEGIN
    INSERT INTO auditoria.avaliacao (usuario_id, conversa_id, mensagem_id, nota)
    SELECT c.usuario_id, c.conversa_id, m.id, 4
      FROM _ctx c JOIN auditoria.mensagem m ON m.conversa_id = c.conversa_id AND m.ordem = 2;
    RAISE WARNING 'ACEITOU — avaliação apontando para conversa E mensagem';
EXCEPTION WHEN check_violation THEN
    RAISE NOTICE 'RECUSADO (ok) — a avaliação recai sobre um alvo só';
END $$;

DO $$ BEGIN
    INSERT INTO auditoria.avaliacao (usuario_id, mensagem_id, comentario)
    SELECT c.usuario_id, m.id, 'só um comentário'
      FROM _ctx c JOIN auditoria.mensagem m ON m.conversa_id = c.conversa_id AND m.ordem = 2;
    RAISE WARNING 'ACEITOU — avaliação sem nota nem polaridade';
EXCEPTION WHEN check_violation THEN
    RAISE NOTICE 'RECUSADO (ok) — avaliação exige nota ou polaridade';
END $$;

DO $$ BEGIN
    UPDATE portfolio.projeto SET percentual_avanco = 140 WHERE codigo = 'SYN-01';
    RAISE WARNING 'ACEITOU — avanço físico acima de 100%%';
EXCEPTION WHEN check_violation THEN
    RAISE NOTICE 'RECUSADO (ok) — avanço físico fora de 0..100';
END $$;

\echo ''
\echo '-- Colunas geradas continuam coerentes com a origem --'
SELECT codigo, percentual_previsto, percentual_avanco, desvio_pp,
       desvio_pp = percentual_avanco - percentual_previsto AS desvio_coerente
  FROM portfolio.projeto WHERE codigo IN ('SYN-01', 'SYN-05') ORDER BY codigo;

ROLLBACK;

\echo ''
\echo '== ROLLBACK executado: nenhum resíduo gravado =='
