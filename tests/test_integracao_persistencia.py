"""Persistência em banco de dados — TI-24 a TI-29, TI-53, TI-54 e TI-65.

PostgreSQL real, com o DDL de `src/database` aplicado. O que está sob teste aqui
não é código Python: são as RESTRIÇÕES do esquema. `mensagem_papel_coerente`,
`mensagem_audio_coerente`, `avaliacao_alvo_unico` e `avaliacao_tem_juizo` não
têm equivalente em nenhum `if` da aplicação — se o banco não as impuser, nada
mais impõe. Um dublê em memória provaria apenas que o dublê funciona.

Preparação:

    docker compose up -d postgres
    export TEST_DATABASE_URL=postgresql://az1:az1@127.0.0.1:5432/az1_teste
    psql "$TEST_DATABASE_URL" -f src/database/01_create_database.sql
    psql "$TEST_DATABASE_URL" -f src/database/02_initial_data.sql
    psql "$TEST_DATABASE_URL" -f src/database/03_rls_policies.sql
    psql "$TEST_DATABASE_URL" -f src/database/07_evento_local.sql
    python -m unittest tests.test_integracao_persistencia -v

Sem `TEST_DATABASE_URL`, a suíte inteira é PULADA — e pular é registro de
execução parcial, não aprovação (Seção 6.4.5).

A suíte é DESTRUTIVA e recusa rodar contra `DATABASE_URL` ou `SUPABASE_DB_URL`,
mesmo que apontem para o mesmo lugar. A razão está documentada em
`tests/test_integracao_webhook_postgres.py`: rodar sem a variável dedicada já
apagou, uma vez neste projeto, a evidência que sustentava uma seção do relatório.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import unittest
import uuid
from urllib.parse import urlsplit, urlunsplit

import psycopg
from psycopg_pool import ConnectionPool

from services.conversa_repository import (
    ConversaRepository,
    FonteDaResposta,
    PersistenciaDesligada,
    TurnoDoChat,
)
from tests.apoio_integracao import RAIZ

DSN = os.environ.get("TEST_DATABASE_URL")

# Os três schemas e as dezessete tabelas que a Seção 3.6.6 declara.
SCHEMAS_ESPERADOS = {"portfolio", "auditoria", "integracao"}
TOTAL_DE_TABELAS_ESPERADO = 17


def _motivo_para_pular() -> str | None:
    if not DSN:
        return (
            "TEST_DATABASE_URL não definido. Aponte para um banco de teste dedicado — "
            "nunca para DATABASE_URL."
        )
    if DSN in (os.environ.get("DATABASE_URL"), os.environ.get("SUPABASE_DB_URL")):
        return (
            "TEST_DATABASE_URL é igual ao banco da aplicação. Esta suíte é destrutiva; "
            "use uma base separada."
        )
    try:
        with psycopg.connect(DSN, connect_timeout=3) as conexao:
            conexao.execute("SELECT 1 FROM auditoria.mensagem LIMIT 0")
            conexao.execute("SELECT 1 FROM portfolio.usuario LIMIT 0")
    except psycopg.OperationalError:
        return "Postgres de teste indisponível; verifique o serviço e TEST_DATABASE_URL."
    except psycopg.Error as erro:
        return f"Esquema ausente — rode o DDL de src/database: {erro}".strip()
    return None


def _dsn_para(base: str) -> str:
    """O mesmo DSN de teste, apontando para outra base.

    Reescreve só o caminho: usuário, senha, host e porta continuam os de
    `TEST_DATABASE_URL`, que é o único banco que esta suíte tem autorização
    para tocar.
    """
    partes = urlsplit(DSN)
    return urlunsplit(partes._replace(path=f"/{base}"))


MOTIVO = _motivo_para_pular()


class ArmazenamentoEmMemoria:
    """Implementa o `Armazenamento` de `conversa_repository` sem tocar no MinIO.

    O arquivamento do texto no bucket é fronteira de armazenamento, e ela tem
    casos próprios em TI-01 a TI-05. O que esta suíte verifica é a LINHA no
    banco; manter o MinIO em pé aqui faria os casos de restrição falharem por
    um contêiner ausente que não tem nada a ver com o que eles medem.
    """

    def __init__(self) -> None:
        self.objetos: dict[str, bytes] = {}

    def store(self, *, key: str, content, content_type: str, metadata: dict) -> None:
        content.seek(0)
        self.objetos[key] = content.read()


@unittest.skipIf(MOTIVO is not None, MOTIVO or "")
class _BaseDePersistencia(unittest.TestCase):
    """Preparação comum: pool, usuário de teste e limpeza entre casos."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.pool = ConnectionPool(DSN, min_size=1, max_size=4, open=True)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.pool.close()

    def setUp(self) -> None:
        self.armazenamento = ArmazenamentoEmMemoria()
        self.repositorio = ConversaRepository(
            pool=self.pool, armazenamento=self.armazenamento
        )
        self._limpar()
        self.usuario_id = self._usuario("integracao@example.com", "Usuário de Integração")

    def _limpar(self) -> None:
        with self.pool.connection() as conexao:
            conexao.execute("TRUNCATE auditoria.avaliacao RESTART IDENTITY CASCADE")
            conexao.execute("TRUNCATE auditoria.mensagem_fonte RESTART IDENTITY CASCADE")
            conexao.execute("TRUNCATE auditoria.mensagem RESTART IDENTITY CASCADE")
            conexao.execute("TRUNCATE auditoria.conversa RESTART IDENTITY CASCADE")
            conexao.execute("DELETE FROM portfolio.usuario WHERE email LIKE '%@example.com'")

    def _usuario(self, email: str, nome: str) -> int:
        with self.pool.connection() as conexao, conexao.cursor() as cursor:
            cursor.execute(
                "INSERT INTO portfolio.usuario (nome, email) VALUES (%s, %s) RETURNING id",
                (nome, email),
            )
            return cursor.fetchone()[0]

    def _turno(self, **trocas) -> TurnoDoChat:
        base = {
            "conversa_id": str(uuid.uuid4()),
            "usuario_id": self.usuario_id,
            "prompt": "Como está o avanço da linha 6?",
            "resposta": "O avanço físico registrado é de 62%.",
            "resultado": "sucesso",
            "modelo": "gemini-3.5-flash-lite",
            "tempo_processamento_ms": 840,
            "intencao": "consultar_projeto_sintetico",
            "confianca_intencao": 0.91,
        }
        base.update(trocas)
        return TurnoDoChat(**base)

    def _mensagens(self, conversa_id: str) -> list[tuple]:
        with self.pool.connection() as conexao, conexao.cursor() as cursor:
            cursor.execute(
                "SELECT ordem, papel, formato, conteudo, intencao, confianca_intencao, "
                "       resultado, modelo, tempo_processamento_ms, audio_referencia "
                "FROM auditoria.mensagem WHERE conversa_id = %s ORDER BY ordem",
                (conversa_id,),
            )
            return cursor.fetchall()

    def _inserir_mensagem_crua(self, conexao, conversa_id: str, **colunas) -> None:
        """Insere uma linha contornando o repositório, para exercitar os CHECKs.

        O repositório monta as colunas corretamente por construção; para provar
        que a RESTRIÇÃO existe é preciso tentar a combinação proibida na mão.
        """
        base = {
            "conversa_id": conversa_id,
            "ordem": 1,
            "papel": "usuario",
            "formato": "texto",
            "conteudo": "texto qualquer",
        }
        base.update(colunas)
        campos = ", ".join(base)
        marcadores = ", ".join(["%s"] * len(base))
        conexao.execute(
            f"INSERT INTO auditoria.mensagem ({campos}) VALUES ({marcadores})",
            tuple(base.values()),
        )

    def _como_aplicacao(self, conexao) -> None:
        """Assume `az1_app` explicitamente, como a aplicação faz.

        `SET ROLE` é o ponto: conectar como dono do banco e afirmar que a
        trilha está protegida provaria o contrário do que se quer. A Seção
        6.4.4 é explícita — "não usar superusuário para afirmar que RLS protege
        aplicação".
        """
        conexao.execute("SET ROLE az1_app")

    def _exigir_papel_da_aplicacao(self) -> None:
        with self.pool.connection() as conexao, conexao.cursor() as cursor:
            cursor.execute("SELECT 1 FROM pg_roles WHERE rolname = 'az1_app'")
            if cursor.fetchone() is None:
                self.skipTest("papel az1_app ausente; rode src/database/03_rls_policies.sql")

    def _garantir_conversa(self, conexao, conversa_id: str) -> None:
        conexao.execute(
            "INSERT INTO auditoria.conversa (id, usuario_id, titulo) VALUES (%s, %s, %s) "
            "ON CONFLICT (id) DO NOTHING",
            (conversa_id, self.usuario_id, "conversa de ensaio"),
        )


class TestPersistenciaIntegracao(_BaseDePersistencia):
    """TI-24 a TI-27, TI-53 e TI-54."""

    # -- TI-24 ---------------------------------------------------------------

    def test_turno_por_texto_e_gravado_com_atributos_minimos(self) -> None:
        """Um turno vira duas linhas irmãs, com ordens consecutivas."""
        turno = self._turno()

        gravado = self.repositorio.registrar_turno(turno)

        linhas = self._mensagens(turno.conversa_id)
        self.assertEqual(len(linhas), 2)

        usuario, agente = linhas
        self.assertEqual(usuario[1], "usuario")
        self.assertEqual(agente[1], "agente")
        self.assertEqual(agente[0] - usuario[0], 1, "as ordens precisam ser consecutivas")
        self.assertEqual((usuario[0], agente[0]), (gravado.ordem_prompt, gravado.ordem_resposta))

        # O texto de ambas é preservado, e é o que a auditoria lê.
        self.assertEqual(usuario[3], turno.prompt)
        self.assertEqual(agente[3], turno.resposta)

        # Cada papel carrega só as suas colunas — a outra metade fica nula.
        self.assertEqual(usuario[4], turno.intencao)
        self.assertIsNone(usuario[6], "resultado pertence ao agente")
        self.assertIsNone(agente[4], "intenção pertence ao usuário")
        self.assertEqual(agente[6], "sucesso")
        self.assertEqual(agente[7], turno.modelo)

    def test_segundo_turno_continua_a_numeracao_da_conversa(self) -> None:
        """Ordens seguem crescendo na mesma conversa. Complementa TI-24.

        Sem este caso, um repositório que recomeçasse do 1 a cada turno passaria
        em TI-24 e violaria `UNIQUE (conversa_id, ordem)` só em produção.
        """
        conversa = str(uuid.uuid4())

        primeiro = self.repositorio.registrar_turno(self._turno(conversa_id=conversa))
        segundo = self.repositorio.registrar_turno(self._turno(conversa_id=conversa))

        self.assertEqual((primeiro.ordem_prompt, primeiro.ordem_resposta), (1, 2))
        self.assertEqual((segundo.ordem_prompt, segundo.ordem_resposta), (3, 4))
        self.assertEqual(len(self._mensagens(conversa)), 4)

    # -- TI-25 ---------------------------------------------------------------

    def test_turno_por_voz_vincula_o_audio_de_origem(self) -> None:
        """Formato `audio` aceita `audio_referencia`; formato `texto` não.

        É a restrição `mensagem_audio_coerente`. Ela é o que impede a trilha de
        afirmar que existe um objeto no MinIO para um turno que foi digitado.
        """
        conversa = str(uuid.uuid4())
        audio_id = "aud_0123456789abcdef"

        with self.pool.connection() as conexao:
            self._garantir_conversa(conexao, conversa)
            self._inserir_mensagem_crua(
                conexao,
                conversa,
                ordem=1,
                formato="audio",
                audio_referencia=audio_id,
                audio_duracao_s=3.5,
            )

        linhas = self._mensagens(conversa)
        self.assertEqual(linhas[0][2], "audio")
        self.assertEqual(linhas[0][9], audio_id)

        # E a combinação incoerente é recusada pelo banco.
        with self.pool.connection() as conexao, self.assertRaises(psycopg.errors.CheckViolation) as capturado:
            self._inserir_mensagem_crua(
                conexao,
                conversa,
                ordem=2,
                formato="texto",
                audio_referencia=audio_id,
            )
        self.assertIn("mensagem_audio_coerente", str(capturado.exception))

    # -- TI-26 ---------------------------------------------------------------

    def test_consulta_de_projeto_retorna_dados_e_fontes_registradas(self) -> None:
        """Uma linha em `mensagem_fonte` por trecho citado, com os metadados copiados.

        Os metadados são CÓPIA, e não junção com a coleção vetorial: reindexar
        troca o `chunk_id` (é o md5 do conteúdo), e uma trilha que dependesse da
        junção ficaria ilegível depois da primeira reindexação — que é
        exatamente o que o RNF12 não pode permitir.
        """
        fontes = (
            FonteDaResposta(
                chunk_id="chunk-aaa",
                arquivo_origem="01_TAP.docx",
                posicao=1,
                score=0.82,
                projeto_codigo="PRJ-L6",
                tipo_documento="TAP",
                secao="3.1",
                trecho="O avanço previsto para o período é de 60%.",
            ),
            FonteDaResposta(
                chunk_id="chunk-bbb",
                arquivo_origem="04_Riscos.xlsx",
                posicao=3,
                score=0.71,
                projeto_codigo="PRJ-L6",
                tipo_documento="Riscos",
                secao="2",
                trecho="Risco de atraso na desapropriação.",
            ),
        )
        turno = self._turno(fontes=fontes)

        gravado = self.repositorio.registrar_turno(turno)

        with self.pool.connection() as conexao, conexao.cursor() as cursor:
            cursor.execute(
                "SELECT mensagem_id, posicao, chunk_id, score, projeto_codigo, "
                "       tipo_documento, arquivo_origem, secao, trecho "
                "FROM auditoria.mensagem_fonte ORDER BY posicao",
                (),
            )
            linhas = cursor.fetchall()

        self.assertEqual(len(linhas), 2, "uma linha por trecho citado")
        for linha, fonte in zip(linhas, fontes, strict=True):
            self.assertEqual(linha[0], gravado.mensagem_agente_id, "a fonte pende da resposta")
            self.assertEqual(linha[1], fonte.posicao)
            self.assertEqual(linha[2], fonte.chunk_id)
            self.assertAlmostEqual(float(linha[3]), fonte.score, places=4)
            self.assertEqual(linha[4], fonte.projeto_codigo)
            self.assertEqual(linha[6], fonte.arquivo_origem)
            self.assertEqual(linha[8], fonte.trecho)

        # A posição é a citada no texto, não um contador: o segundo trecho foi
        # citado como [3], e é 3 que fica gravado.
        self.assertEqual([linha[1] for linha in linhas], [1, 3])

    # -- TI-27 ---------------------------------------------------------------

    def test_banco_indisponivel_nao_perde_o_turno(self) -> None:
        """CARACTERIZAÇÃO: hoje o turno É perdido, e só sobra o registro no log.

        A ficha do caso pede que o turno seja "reencaminhado, não descartado".
        Não é o que acontece. `routes/chat.py::registrar_turno_em_segundo_plano`
        captura qualquer exceção e apenas registra — não há fila, reenvio nem
        marca de pendência. A resposta ao usuário sai normalmente, e a trilha
        daquele turno não existe.

        A escolha tem razão documentada (gravar é efeito colateral de `/chat`, e
        derrubar a conversa por causa do banco seria pior), mas o RNF04 pede
        durabilidade, e durabilidade sem reenvio não se sustenta. O caso fixa o
        comportamento atual e a lacuna fica registrada na Seção 6.4.4.
        """
        from routes.chat import registrar_turno_em_segundo_plano

        desligado = PersistenciaDesligada("banco fora do ar no ensaio")
        turno = self._turno()

        # Não levanta: a falha é engolida de propósito.
        registrar_turno_em_segundo_plano(desligado, turno)

        self.assertEqual(
            self._mensagens(turno.conversa_id),
            [],
            "nada foi gravado — e nada foi enfileirado para reenvio",
        )

    # -- TI-53 ---------------------------------------------------------------

    def test_papel_da_mensagem_delimita_as_colunas(self) -> None:
        """`mensagem_papel_coerente` recusa as duas combinações cruzadas."""
        conversa = str(uuid.uuid4())

        combinacoes = {
            "resposta do agente com intenção classificada": {
                "ordem": 1,
                "papel": "agente",
                "resultado": "sucesso",
                "intencao": "orientar_tap",
                "confianca_intencao": 0.8,
            },
            "solicitação do usuário com tempo de processamento": {
                "ordem": 2,
                "papel": "usuario",
                "tempo_processamento_ms": 120,
            },
        }

        for descricao, colunas in combinacoes.items():
            with self.subTest(combinacao=descricao):
                with self.pool.connection() as conexao:
                    self._garantir_conversa(conexao, conversa)
                    with self.assertRaises(psycopg.errors.CheckViolation) as capturado:
                        self._inserir_mensagem_crua(conexao, conversa, **colunas)
                self.assertIn("mensagem_papel_coerente", str(capturado.exception))

    # -- TI-54 ---------------------------------------------------------------

    def test_avaliacao_exige_alvo_e_juizo_unicos(self) -> None:
        """Alvo único, juízo obrigatório, e reavaliar atualiza em vez de empilhar."""
        turno = self._turno()
        gravado = self.repositorio.registrar_turno(turno)

        with self.pool.connection() as conexao:
            # Dois alvos ao mesmo tempo: recusado.
            with self.assertRaises(psycopg.errors.CheckViolation) as alvo:
                conexao.execute(
                    "INSERT INTO auditoria.avaliacao "
                    "(usuario_id, conversa_id, mensagem_id, polaridade) VALUES (%s, %s, %s, %s)",
                    (self.usuario_id, turno.conversa_id, gravado.mensagem_agente_id, "positiva"),
                )
            self.assertIn("avaliacao_alvo_unico", str(alvo.exception))

        with self.pool.connection() as conexao:
            # Só comentário, sem polaridade nem nota: recusado.
            with self.assertRaises(psycopg.errors.CheckViolation) as juizo:
                conexao.execute(
                    "INSERT INTO auditoria.avaliacao "
                    "(usuario_id, mensagem_id, comentario) VALUES (%s, %s, %s)",
                    (self.usuario_id, gravado.mensagem_agente_id, "achei estranho"),
                )
            self.assertIn("avaliacao_tem_juizo", str(juizo.exception))

        # E reavaliar o mesmo alvo atualiza a linha existente.
        with self.pool.connection() as conexao:
            conexao.execute(
                "INSERT INTO auditoria.avaliacao (usuario_id, mensagem_id, polaridade) "
                "VALUES (%s, %s, %s)",
                (self.usuario_id, gravado.mensagem_agente_id, "positiva"),
            )
            conexao.execute(
                "INSERT INTO auditoria.avaliacao (usuario_id, mensagem_id, polaridade) "
                "VALUES (%s, %s, %s) "
                "ON CONFLICT (usuario_id, mensagem_id) WHERE mensagem_id IS NOT NULL "
                "DO UPDATE SET polaridade = EXCLUDED.polaridade",
                (self.usuario_id, gravado.mensagem_agente_id, "negativa"),
            )

        with self.pool.connection() as conexao, conexao.cursor() as cursor:
            cursor.execute(
                "SELECT polaridade FROM auditoria.avaliacao WHERE mensagem_id = %s",
                (gravado.mensagem_agente_id,),
            )
            linhas = cursor.fetchall()

        self.assertEqual(len(linhas), 1, "reavaliar empilhou uma linha nova")
        self.assertEqual(linhas[0][0], "negativa")


    # -- TI-28 ---------------------------------------------------------------

    def test_papel_de_aplicacao_nao_altera_auditoria(self) -> None:
        """A aplicação insere e lê a trilha, e não a reescreve nem a apaga.

        É o RNF09: a trilha é append-only do ponto de vista de quem a produz.
        Os GRANTs de `03_rls_policies.sql` dão `SELECT, INSERT` em `auditoria` e
        `UPDATE` apenas em colunas nomeadas de `conversa` e `avaliacao`.
        """
        self._exigir_papel_da_aplicacao()
        turno = self._turno()
        gravado = self.repositorio.registrar_turno(turno)

        for descricao, comando, parametros in (
            (
                "UPDATE em mensagem",
                "UPDATE auditoria.mensagem SET conteudo = %s WHERE id = %s",
                ("texto adulterado", gravado.mensagem_agente_id),
            ),
            (
                "DELETE em mensagem",
                "DELETE FROM auditoria.mensagem WHERE id = %s",
                (gravado.mensagem_agente_id,),
            ),
        ):
            with self.subTest(operacao=descricao), self.pool.connection() as conexao:
                self._como_aplicacao(conexao)
                with self.assertRaises(psycopg.errors.InsufficientPrivilege):
                    conexao.execute(comando, parametros)

        # O conteúdo continua o que era.
        linhas = self._mensagens(turno.conversa_id)
        self.assertEqual(linhas[1][3], turno.resposta)


    # -- TI-29 ---------------------------------------------------------------

    def test_schema_e_criado_em_base_vazia(self) -> None:
        """Os scripts-base e a migração 07 aplicados a uma base recém-criada.

        Este é o caso como o planejamento o descreve, e não uma leitura do banco
        já migrado: cria uma base do zero, aplica `01`, `02`, `03` e `07` na
        ordem, reaplica `07` para provar idempotência e confere o que ficou de
        pé. A base é destruída ao final.

        A execução é por `psql`, e não por `psycopg`, porque o DDL usa
        metacomandos do cliente — `\\set ON_ERROR_STOP`, `\\echo` e `\\if` — que
        só o `psql` interpreta. Rodar os arquivos por driver exigiria removê-los
        do script, o que faria o teste exercitar um DDL diferente do que a
        equipe aplica de verdade.

        Pula, com motivo explícito, quando `psql` não está no PATH ou quando o
        executor não tem privilégio de `CREATEDB` — e pular não é aprovar.
        """
        psql = shutil.which("psql")
        if psql is None:
            self.skipTest(
                "psql ausente no PATH. O DDL usa metacomandos do cliente "
                "(\\set, \\echo, \\if) e precisa dele; instale postgresql-client."
            )

        base = f"az1_ti29_{uuid.uuid4().hex[:10]}"
        try:
            self._criar_base(base)
        except psycopg.errors.InsufficientPrivilege:
            self.skipTest("o usuário de TEST_DATABASE_URL não tem privilégio de CREATEDB")

        try:
            destino = _dsn_para(base)
            for arquivo in (
                "01_create_database.sql",
                "02_initial_data.sql",
                "03_rls_policies.sql",
                "07_evento_local.sql",
                "07_evento_local.sql",
            ):
                with self.subTest(script=arquivo):
                    resultado = subprocess.run(
                        [psql, destino, "-v", "ON_ERROR_STOP=1", "-f", f"src/database/{arquivo}"],
                        capture_output=True,
                        text=True,
                        cwd=RAIZ,
                        timeout=180,
                    )
                    self.assertEqual(
                        resultado.returncode,
                        0,
                        f"{arquivo} falhou em base vazia:\n{resultado.stdout[-2000:]}\n{resultado.stderr[-2000:]}",
                    )

            with psycopg.connect(destino) as conexao, conexao.cursor() as cursor:
                cursor.execute(
                    "SELECT schema_name FROM information_schema.schemata WHERE schema_name = ANY(%s)",
                    (list(SCHEMAS_ESPERADOS),),
                )
                schemas = {linha[0] for linha in cursor.fetchall()}
                cursor.execute(
                    "SELECT count(*) FROM information_schema.tables "
                    "WHERE table_schema = ANY(%s) AND table_type = 'BASE TABLE'",
                    (list(SCHEMAS_ESPERADOS),),
                )
                tabelas = cursor.fetchone()[0]
                cursor.execute("SELECT count(*) FROM portfolio.projeto")
                projetos = cursor.fetchone()[0]

            self.assertEqual(schemas, SCHEMAS_ESPERADOS)
            self.assertEqual(tabelas, TOTAL_DE_TABELAS_ESPERADO)
            self.assertGreater(projetos, 0, "a carga inicial de 02_initial_data.sql não populou")
        finally:
            self._destruir_base(base)

    @staticmethod
    def _criar_base(nome: str) -> None:
        with psycopg.connect(DSN, autocommit=True) as conexao:
            conexao.execute(f'CREATE DATABASE "{nome}"')

    @staticmethod
    def _destruir_base(nome: str) -> None:
        with psycopg.connect(DSN, autocommit=True) as conexao:
            conexao.execute(f'DROP DATABASE IF EXISTS "{nome}" WITH (FORCE)')


class TestPermissoesDaAuditoria(_BaseDePersistencia):
    """TI-65 e os complementos de TI-28 — casos sem nome fixado no catálogo."""

    def setUp(self) -> None:
        super().setUp()
        self._exigir_papel_da_aplicacao()

    def test_feedback_autorizado_continua_permitido(self) -> None:
        """O contraste que dá sentido ao caso acima.

        Se o papel não pudesse escrever nada, TI-28 passaria por um motivo
        errado. A avaliação é o caminho legítimo de escrita: `polaridade`,
        `nota`, `motivo` e `comentario` têm GRANT de coluna.
        """
        turno = self._turno()
        gravado = self.repositorio.registrar_turno(turno)

        with self.pool.connection() as conexao:
            self._como_aplicacao(conexao)
            conexao.execute(
                "INSERT INTO auditoria.avaliacao (usuario_id, mensagem_id, polaridade) "
                "VALUES (%s, %s, %s)",
                (self.usuario_id, gravado.mensagem_agente_id, "positiva"),
            )
            conexao.execute(
                "UPDATE auditoria.avaliacao SET polaridade = %s WHERE mensagem_id = %s",
                ("negativa", gravado.mensagem_agente_id),
            )

        with self.pool.connection() as conexao, conexao.cursor() as cursor:
            cursor.execute(
                "SELECT polaridade FROM auditoria.avaliacao WHERE mensagem_id = %s",
                (gravado.mensagem_agente_id,),
            )
            self.assertEqual(cursor.fetchone()[0], "negativa")

    # -- TI-65 ---------------------------------------------------------------

    def test_historico_de_um_usuario_nao_vaza_para_o_outro(self) -> None:
        """Duas identidades, cada uma enxergando a própria conversa.

        A leitura da trilha pela API filtra por usuário em `routes/conversas.py`.
        Este caso verifica o filtro na CAMADA DE DADOS, que é onde ele precisa
        valer mesmo que alguém consulte por outro caminho.
        """
        outro = self._usuario("outro@example.com", "Outro Usuário")

        minha = self._turno()
        self.repositorio.registrar_turno(minha)
        dele = self._turno(usuario_id=outro, prompt="Pergunta do outro usuário.")
        self.repositorio.registrar_turno(dele)

        minhas = self.repositorio.listar_conversas(self.usuario_id)
        dele_listadas = self.repositorio.listar_conversas(outro)

        identificadores_meus = {str(c.id) for c in minhas}
        identificadores_dele = {str(c.id) for c in dele_listadas}

        self.assertIn(minha.conversa_id, identificadores_meus)
        self.assertNotIn(
            dele.conversa_id, identificadores_meus, "conversa alheia apareceu no histórico próprio"
        )
        self.assertIn(dele.conversa_id, identificadores_dele)
        self.assertNotIn(minha.conversa_id, identificadores_dele)

    def test_mensagens_de_conversa_alheia_nao_sao_devolvidas(self) -> None:
        """O mesmo isolamento, um nível abaixo: as mensagens da conversa."""
        outro = self._usuario("outro@example.com", "Outro Usuário")
        dele = self._turno(usuario_id=outro, prompt="Pergunta do outro usuário.")
        self.repositorio.registrar_turno(dele)

        vazio = self.repositorio.mensagens_da_conversa(dele.conversa_id, self.usuario_id)

        self.assertEqual(tuple(vazio), (), "mensagens de conversa alheia foram devolvidas")


@unittest.skipIf(MOTIVO is not None, MOTIVO or "")
class TestPersistenciaEsquema(unittest.TestCase):
    """Complemento de TI-29: confere a base de teste já migrada."""

    def test_schemas_e_tabelas_do_ddl_estao_presentes(self) -> None:
        """O mesmo resultado, conferido na base de teste já migrada.

        Complementa o caso acima e roda mesmo sem `psql` ou sem `CREATEDB`: se a
        criação do zero não puder ser exercitada, ao menos a base contra a qual
        as demais suítes rodam é conferida contra a Seção 3.6.6.
        """
        with psycopg.connect(DSN) as conexao, conexao.cursor() as cursor:
            cursor.execute(
                "SELECT schema_name FROM information_schema.schemata "
                "WHERE schema_name = ANY(%s)",
                (list(SCHEMAS_ESPERADOS),),
            )
            encontrados = {linha[0] for linha in cursor.fetchall()}

            cursor.execute(
                "SELECT count(*) FROM information_schema.tables "
                "WHERE table_schema = ANY(%s) AND table_type = 'BASE TABLE'",
                (list(SCHEMAS_ESPERADOS),),
            )
            total = cursor.fetchone()[0]

        self.assertEqual(encontrados, SCHEMAS_ESPERADOS)
        self.assertEqual(
            total,
            TOTAL_DE_TABELAS_ESPERADO,
            f"a Seção 3.6.6 declara {TOTAL_DE_TABELAS_ESPERADO} tabelas; o banco tem {total}",
        )

    def test_carga_inicial_esta_populada(self) -> None:
        """`02_initial_data.sql` deixou o portfólio com conteúdo."""
        with psycopg.connect(DSN) as conexao, conexao.cursor() as cursor:
            cursor.execute("SELECT count(*) FROM portfolio.projeto")
            projetos = cursor.fetchone()[0]

        self.assertGreater(projetos, 0, "a carga inicial não foi aplicada")

    def test_evento_local_tem_colunas_do_contrato(self) -> None:
        with psycopg.connect(DSN) as conexao, conexao.cursor() as cursor:
            cursor.execute(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_schema = 'portfolio' AND table_name = 'evento_local' "
                "ORDER BY ordinal_position"
            )
            colunas = [linha[0] for linha in cursor.fetchall()]

        self.assertEqual(
            colunas,
            ["id", "usuario_id", "titulo", "data", "hora", "descricao", "criado_em"],
        )


class TestModeloDocumentado(unittest.TestCase):
    """TI-29, segunda metade: documento e DDL não divergem.

    Roda sem banco — `--sem-banco` compara a Seção 3.6.6 com os arquivos de
    `src/database` — e por isso fica fora do `skipIf` das demais.
    """

    def test_verificador_nao_aponta_divergencia(self) -> None:
        resultado = subprocess.run(
            [sys.executable, "scripts/verificar_modelo_documentado.py", "--sem-banco"],
            capture_output=True,
            text=True,
            cwd=RAIZ,
            timeout=120,
        )

        self.assertEqual(
            resultado.returncode,
            0,
            f"divergência entre a Seção 3.6.6 e o DDL:\n{resultado.stdout}\n{resultado.stderr}",
        )


if __name__ == "__main__":
    unittest.main()
