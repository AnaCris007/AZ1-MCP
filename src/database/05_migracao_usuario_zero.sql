-- =============================================================================
-- AZ1 — Aposentadoria do usuário de sistema id = 0
--
-- POR QUE ESTE SCRIPT EXISTE
--
-- `portfolio.usuario.id` é GENERATED ALWAYS AS IDENTITY (01_create_database.sql).
-- O id 0 nunca poderia ter saído dele: foi inserido à mão, num único banco,
-- para destravar a gravação de auditoria antes de a autenticação existir.
--
-- O efeito é uma divergência que só aparece em tempo de execução, e calada: a
-- base de desenvolvimento tem a linha, qualquer base reconstruída pelo DDL não
-- tem, e a gravação falha por violação de chave estrangeira dentro de um
-- `except Exception` que a registra em log e segue. Ninguém percebe até ir
-- procurar a conversa que deveria estar lá.
--
-- Com a autenticação em vigor, `AuthenticatedUser.domain_user_id` passa a
-- fornecer a identidade real, e o id 0 perde a única razão que tinha.
--
-- O QUE ESTE SCRIPT NÃO FAZ
--
-- Não toca em `auditoria.mensagem`. O que muda é o PONTEIRO DE DONO das
-- conversas antigas — `conversa.usuario_id` —, e ele nunca foi um valor
-- verdadeiro: era um marcador de "não sabemos quem perguntou". Corrigi-lo não é
-- reescrever a trilha que o RNF09 protege; é deixar de afirmar uma falsidade
-- sobre ela.
--
-- Reexecutável: sem linha 0, não faz nada.
--
--   psql "$SUPABASE_DB_URL" -X -v ON_ERROR_STOP=1 -f 05_migracao_usuario_zero.sql
-- =============================================================================

\set ON_ERROR_STOP on

BEGIN;

DO $$
DECLARE
    id_legado INTEGER;
    movidas   INTEGER;
BEGIN
    IF NOT EXISTS (SELECT 1 FROM portfolio.usuario WHERE id = 0) THEN
        RAISE NOTICE 'Sem usuário 0: nada a migrar.';
        RETURN;
    END IF;

    -- O destino nasce pela IDENTITY, como qualquer outro. `ativo = false`
    -- porque não é pessoa e não deve aparecer em listagem nem receber atribuição;
    -- `portfolio.usuario_atual()` já filtra por `ativo`, então ele também não
    -- serve de identidade para a RLS.
    SELECT id INTO id_legado
      FROM portfolio.usuario
     WHERE email = 'auditoria-legado@az1.local';

    IF id_legado IS NULL THEN
        INSERT INTO portfolio.usuario (nome, email, perfil, ativo)
        VALUES ('Trilha anterior à autenticação', 'auditoria-legado@az1.local', 'pmo', false)
        RETURNING id INTO id_legado;
        RAISE NOTICE 'Usuário de legado criado com id %.', id_legado;
    END IF;

    UPDATE auditoria.conversa SET usuario_id = id_legado WHERE usuario_id = 0;
    GET DIAGNOSTICS movidas = ROW_COUNT;
    RAISE NOTICE '% conversa(s) repontadas para o id %.', movidas, id_legado;

    -- Só depois de nenhuma conversa apontar para ela.
    DELETE FROM portfolio.usuario WHERE id = 0;
    RAISE NOTICE 'Usuário 0 removido.';
END
$$;

COMMIT;
