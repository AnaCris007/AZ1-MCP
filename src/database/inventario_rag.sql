-- Inventário somente leitura da coleção vetorial legada.
--
-- Este arquivo pressupõe que vecs.documentos_metro existe. O executor
-- scripts/inventariar_indice_rag.py verifica essa pré-condição e abre uma
-- transação READ ONLY antes de executar a consulta.
--
-- Identificadores de projeto e arquivo nunca são devolvidos em claro. Os hashes
-- servem somente para distinguir grupos dentro do mesmo relatório; não devem ser
-- tratados como anonimização criptográfica dos valores de origem.

WITH base AS (
    SELECT
        id,
        vec,
        metadata,
        NULLIF(btrim(metadata->>'projeto_id'), '')      AS projeto_id,
        NULLIF(btrim(metadata->>'tipo_documento'), '') AS tipo_documento,
        NULLIF(btrim(metadata->>'arquivo_origem'), '') AS arquivo_origem,
        NULLIF(btrim(metadata->>'secao'), '')           AS secao,
        NULLIF(btrim(metadata->>'texto'), '')           AS texto,
        NULLIF(btrim(metadata->>'dataset'), '')         AS dataset
    FROM vecs.documentos_metro
),
duplicatas AS (
    SELECT md5(texto) AS texto_hash, count(*) AS quantidade
    FROM base
    WHERE texto IS NOT NULL
    GROUP BY md5(texto)
    HAVING count(*) > 1
),
resultado AS (
    SELECT
        10 AS ordem,
        'resumo'::text AS secao_relatorio,
        jsonb_build_object(
            'total_chunks', count(*),
            'documentos_distintos', count(DISTINCT (projeto_id, arquivo_origem)),
            'candidatos_sintetico_legado', count(*) FILTER (WHERE dataset IS NULL),
            'vetores_nulos', count(*) FILTER (WHERE vec IS NULL)
        ) AS item
    FROM base

    UNION ALL

    SELECT
        20,
        'dimensao_vetorial',
        jsonb_build_object(
            'coluna', a.attname,
            'tipo', pg_catalog.format_type(a.atttypid, a.atttypmod),
            'obrigatoria', a.attnotnull
        )
    FROM pg_catalog.pg_attribute a
    WHERE a.attrelid = 'vecs.documentos_metro'::regclass
      AND a.attname = 'vec'
      AND a.attnum > 0
      AND NOT a.attisdropped

    UNION ALL

    SELECT
        30,
        'metadados_ausentes',
        jsonb_build_object(
            'projeto_id', count(*) FILTER (WHERE projeto_id IS NULL),
            'tipo_documento', count(*) FILTER (WHERE tipo_documento IS NULL),
            'arquivo_origem', count(*) FILTER (WHERE arquivo_origem IS NULL),
            'secao', count(*) FILTER (WHERE secao IS NULL),
            'texto', count(*) FILTER (WHERE texto IS NULL),
            'dataset', count(*) FILTER (WHERE dataset IS NULL)
        )
    FROM base

    UNION ALL

    SELECT
        40,
        'sinais_em_arquivo_origem',
        -- Os dois padroes que contem barra invertida usam prefixo E de
        -- proposito; o de caminho unix nao precisa, porque nao tem nenhuma.
        --
        -- Com standard_conforming_strings ligado (padrao desde o 9.1), a
        -- barra NAO e escape num literal comum: '\\.' entrega ao regex
        -- \\ (barra literal) seguido de . (qualquer caractere), e o
        -- padrao passa a exigir uma barra invertida antes do TLD. Nenhum
        -- e-mail real casa, e o contador so pode devolver zero.
        jsonb_build_object(
            'caminhos_absolutos_unix',
                count(*) FILTER (WHERE arquivo_origem ~ '^/'),
            'caminhos_absolutos_windows',
                count(*) FILTER (WHERE arquivo_origem ~ E'^[A-Za-z]:[\\\\/]'),
            'possiveis_emails',
                count(*) FILTER (
                    WHERE arquivo_origem ~* E'[A-Z0-9._%+-]+@[A-Z0-9.-]+\\.[A-Z]{2,}'
                )
        )
    FROM base

    UNION ALL

    SELECT
        50,
        'duplicatas_de_conteudo',
        jsonb_build_object(
            'grupos_duplicados', count(*),
            'chunks_excedentes', COALESCE(sum(quantidade - 1), 0)
        )
    FROM duplicatas

    UNION ALL

    SELECT
        60,
        'por_tipo_documental',
        jsonb_build_object(
            'tipo_documento', COALESCE(tipo_documento, '<ausente>'),
            'chunks', count(*),
            'documentos', count(DISTINCT (projeto_id, arquivo_origem))
        )
    FROM base
    GROUP BY tipo_documento

    UNION ALL

    SELECT
        70,
        'por_projeto',
        jsonb_build_object(
            'projeto_hash', md5(COALESCE(projeto_id, '<ausente>')),
            'chunks', count(*),
            'documentos', count(DISTINCT arquivo_origem),
            'identificador_ausente', projeto_id IS NULL
        )
    FROM base
    GROUP BY projeto_id

    UNION ALL

    SELECT
        80,
        'por_arquivo',
        jsonb_build_object(
            'arquivo_hash', md5(
                COALESCE(projeto_id, '<ausente>') || E'\x1f' ||
                COALESCE(arquivo_origem, '<ausente>')
            ),
            'chunks', count(*),
            'tipos_documentais', count(DISTINCT tipo_documento),
            'identificador_ausente', arquivo_origem IS NULL
        )
    FROM base
    GROUP BY projeto_id, arquivo_origem

    UNION ALL

    SELECT
        90,
        'indices',
        jsonb_build_object(
            'nome', indexname,
            'metodo_hnsw', indexdef ILIKE '% USING hnsw %',
            'distancia_cosseno', indexdef ILIKE '%vector_cosine_ops%',
            'chave_primaria', indexname LIKE '%_pkey'
        )
    FROM pg_catalog.pg_indexes
    WHERE schemaname = 'vecs'
      AND tablename = 'documentos_metro'
)
SELECT secao_relatorio, item
FROM resultado
ORDER BY ordem, item::text;
