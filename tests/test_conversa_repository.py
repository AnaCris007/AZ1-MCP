# Testes da persistência de conversas.
#
# Três coisas aqui são mais do que verificação de comportamento; são contratos
# que, se quebrarem, quebram em silêncio:
#
#   1. O FORMATO DA CHAVE do objeto no S3. Nenhuma coluna o guarda — ele é
#      recalculado a partir de `(conversa_id, ordem)`. Mudá-lo torna
#      inalcançável tudo o que já foi arquivado, e nada acusa.
#   2. OS DOMÍNIOS duplicados em Python. O banco tem os CHECK; o módulo repete
#      os valores para dar erro legível antes da transação. Duas listas se
#      afastam sozinhas — o teste lê o DDL e compara.
#   3. O PREFIXO. `incoming/` expira em 7 dias por regra de ciclo de vida, e o
#      RNF09 exige 90. Arquivar conversa ali seria perda de trilha programada.

from __future__ import annotations

import json
import re
import unittest
from pathlib import Path
from unittest import mock

from services.conversa_repository import (
    FORMATOS_VALIDOS,
    INTENCOES_VALIDAS,
    PREFIXO_CONVERSAS,
    RESULTADOS_VALIDOS,
    ConversaDeOutroUsuario,
    ConversaNaoGravada,
    ConversaRepository,
    FonteDaResposta,
    TurnoDoChat,
    chave_do_turno,
    fontes_da_busca,
    titulo_a_partir_do_prompt,
)

RAIZ = Path(__file__).resolve().parent.parent
DDL = (RAIZ / "src" / "database" / "01_create_database.sql").read_text(encoding="utf-8")

# Mínimo que o RNF09 exige para a trilha de auditoria.
RETENCAO_MINIMA_DIAS = 90


def _turno(**ajustes) -> TurnoDoChat:
    base = {
        "conversa_id": "3f1c0c4e-0000-4000-8000-000000000001",
        "usuario_id": 2,
        "prompt": "Qual o avanço do projeto SYN-004?",
        "resposta": "O avanço registrado em setembro é de 42%.",
        "resultado": "sucesso",
        "intencao": "orientar_avanco_mensal",
        "confianca_intencao": 0.81,
        "modelo": "gemini-3.5-flash-lite",
        "tempo_processamento_ms": 1234,
    }
    base.update(ajustes)
    return TurnoDoChat(**base)


class _CursorFalso:
    def __init__(self, execucoes, respostas):
        self._execucoes = execucoes
        self._respostas = respostas

    def __enter__(self):
        return self

    def __exit__(self, tipo, valor, tb):
        return False

    def execute(self, sql, parametros=()):
        self._execucoes.append((" ".join(sql.split()), parametros))

    def fetchone(self):
        return self._respostas.pop(0)


class _ConexaoFalsa:
    # Conexão e cursor são objetos SEPARADOS de propósito. Colapsá-los num só
    # faria o `__exit__` do bloco do cursor marcar o commit, e o teste que
    # verifica que uma falha no S3 reverte a transação passaria sempre — porque
    # o cursor fecha antes de o S3 ser tocado.
    def __init__(self, pool):
        self._pool = pool

    def cursor(self):
        return _CursorFalso(self._pool.execucoes, self._pool.respostas)

    def __enter__(self):
        return self

    def __exit__(self, tipo, valor, tb):
        # Commit só na saída limpa, como o psycopg faz.
        if tipo is None:
            self._pool.commitou = True
        return False


class _PoolFalso:
    """Pool mínimo que registra o que foi executado.

    Um `MagicMock` cru serviria, mas a ordem das execuções importa aqui (a
    ordem do turno é lida antes dos INSERTs) e ler isso de `call_args_list`
    tornaria cada teste ilegível.
    """

    def __init__(self, ultima_ordem: int = 0, ids=(10, 11), dono: int | None = 2):
        self.execucoes: list[tuple[str, tuple]] = []
        self.commitou = False
        # A primeira resposta é a de `_SQL_TRAVAR_CONVERSA`, que devolve o
        # `usuario_id` da conversa travada. O padrão 2 é o mesmo dono de
        # `_turno()`, de modo que a conferência passe; `dono=None` simula a
        # conversa que ainda não existe, e outro inteiro simula a alheia.
        self.respostas = [
            None if dono is None else (dono,),
            (ultima_ordem,),
            (ids[0],),
            (ids[1],),
        ]

    def connection(self):
        return _ConexaoFalsa(self)

    def inserts_em(self, tabela: str) -> list[tuple]:
        return [p for sql, p in self.execucoes if f"INSERT INTO {tabela}" in sql]


class _ArmazenamentoFalso:
    def __init__(self, erro: Exception | None = None):
        self.gravados: list[dict] = []
        self._erro = erro

    def store(self, *, key, content, content_type, metadata):
        if self._erro is not None:
            raise self._erro
        self.gravados.append(
            {
                "key": key,
                "texto": content.read().decode("utf-8"),
                "content_type": content_type,
                "metadata": metadata,
            }
        )


class TesteChaveDoObjeto(unittest.TestCase):
    def test_formato_da_chave_e_contrato(self):
        # Se este teste mudar, TODOS os objetos já arquivados ficam órfãos:
        # a chave não está guardada em lugar nenhum, ela é recalculada.
        self.assertEqual(
            chave_do_turno("abc-123", 7, "usuario"),
            "conversas/abc-123/000007-usuario.txt",
        )

    def test_ordem_com_zeros_a_esquerda_mantem_a_listagem_ordenada(self):
        # S3 ordena chave como texto: sem preenchimento, "10" viria antes de "9".
        chaves = sorted(chave_do_turno("c", n, "usuario") for n in (2, 9, 10, 100))
        ordens = [int(re.search(r"/(\d+)-", c).group(1)) for c in chaves]
        self.assertEqual(ordens, sorted(ordens))

    def test_prefixo_nao_e_o_do_audio(self):
        # `incoming/` expira em 7 dias; o RNF09 exige no mínimo 90.
        self.assertNotEqual(PREFIXO_CONVERSAS, "incoming/")
        self.assertTrue(chave_do_turno("c", 1, "usuario").startswith("conversas/"))


class TesteRegraDeCicloDeVida(unittest.TestCase):
    # O arquivo é JSON e não aceita comentário, então a intenção dele só é
    # verificável aqui.
    def setUp(self):
        self.regras = json.loads(
            (RAIZ / "infra" / "minio" / "lifecycle.json").read_text(encoding="utf-8")
        )["Rules"]

    def _regra_do_prefixo(self, prefixo):
        for regra in self.regras:
            if regra["Filter"]["Prefix"] == prefixo:
                return regra
        return None

    def test_existe_regra_para_o_prefixo_das_conversas(self):
        self.assertIsNotNone(
            self._regra_do_prefixo(PREFIXO_CONVERSAS),
            f"sem regra para {PREFIXO_CONVERSAS}, os objetos herdam o comportamento "
            f"padrão do bucket e a retenção do RNF09 deixa de ser garantida.",
        )

    def test_retencao_das_conversas_cobre_o_minimo_do_rnf09(self):
        regra = self._regra_do_prefixo(PREFIXO_CONVERSAS)
        self.assertGreater(
            regra["Expiration"]["Days"], RETENCAO_MINIMA_DIAS,
            f"o RNF09 exige retenção mínima de {RETENCAO_MINIMA_DIAS} dias para a trilha.",
        )

    def test_a_regra_do_audio_continua_curta(self):
        # A separação entre os dois prefixos é o ponto: se alguém unificar as
        # regras, ou o áudio passa a viver demais, ou a trilha some cedo demais.
        self.assertEqual(self._regra_do_prefixo("incoming/")["Expiration"]["Days"], 7)


class TesteDominiosBatemComODdl(unittest.TestCase):
    # O módulo repete os CHECK do banco para dar erro legível antes de abrir
    # transação. Repetição diverge; este teste é o que impede.
    def _valores_do_check(self, coluna: str) -> set[str]:
        padrao = re.compile(
            rf"{coluna}\s+TEXT\s+(?:NOT\s+NULL\s+)?CHECK\s*\(\s*{coluna}\s+IN\s*\((.*?)\)\s*\)",
            re.DOTALL,
        )
        achado = padrao.search(DDL)
        self.assertIsNotNone(achado, f"CHECK de {coluna} não encontrado no DDL")
        return set(re.findall(r"'([a-z_]+)'", achado.group(1)))

    def test_intencoes(self):
        self.assertEqual(
            INTENCOES_VALIDAS, self._valores_do_check("intencao"),
            "o catálogo de intenções do banco e o do repositório divergiram. "
            "Os dois também precisam bater com pln/classificador.py.",
        )

    def test_resultados(self):
        self.assertEqual(RESULTADOS_VALIDOS, self._valores_do_check("resultado"))

    def test_formatos(self):
        self.assertEqual(FORMATOS_VALIDOS, self._valores_do_check("formato"))


class TesteValidacao(unittest.TestCase):
    def setUp(self):
        self.pool = _PoolFalso()
        self.repo = ConversaRepository(self.pool, _ArmazenamentoFalso())

    def _recusa(self, **ajustes):
        with self.assertRaises(ConversaNaoGravada):
            self.repo.registrar_turno(_turno(**ajustes))
        # A recusa precisa acontecer ANTES de qualquer escrita.
        self.assertEqual(self.pool.execucoes, [])

    def test_prompt_vazio(self):
        self._recusa(prompt="   ")

    def test_resposta_vazia(self):
        self._recusa(resposta="")

    def test_resultado_fora_do_dominio(self):
        self._recusa(resultado="ok")

    def test_intencao_fora_do_catalogo(self):
        self._recusa(intencao="consultar_qualquer_coisa")

    def test_formato_fora_do_dominio(self):
        self._recusa(formato="video")

    def test_confianca_fora_da_faixa(self):
        self._recusa(confianca_intencao=1.5)

    def test_tempo_negativo(self):
        self._recusa(tempo_processamento_ms=-1)

    def test_fontes_com_posicao_repetida(self):
        fontes = (
            FonteDaResposta(chunk_id="a", arquivo_origem="x.docx", posicao=1),
            FonteDaResposta(chunk_id="b", arquivo_origem="x.docx", posicao=1),
        )
        self._recusa(fontes=fontes)

    def test_mesmo_chunk_citado_duas_vezes(self):
        fontes = (
            FonteDaResposta(chunk_id="a", arquivo_origem="x.docx", posicao=1),
            FonteDaResposta(chunk_id="a", arquivo_origem="x.docx", posicao=2),
        )
        self._recusa(fontes=fontes)

    def test_fonte_sem_chunk_id(self):
        # Passaria no NOT NULL como string vazia e só apareceria como problema
        # quando alguém tentasse voltar da resposta para o trecho.
        self._recusa(fontes=(FonteDaResposta(chunk_id="", arquivo_origem="x.docx", posicao=1),))

    def test_fonte_sem_arquivo_origem(self):
        self._recusa(fontes=(FonteDaResposta(chunk_id="a", arquivo_origem="", posicao=1),))

    def test_intencao_ausente_e_aceita(self):
        # O canal de texto ainda não roda o classificador; a coluna é anulável.
        self.repo.registrar_turno(_turno(intencao=None, confianca_intencao=None))
        self.assertTrue(self.pool.commitou)


class TesteGravacaoDoTurno(unittest.TestCase):
    def setUp(self):
        self.pool = _PoolFalso(ultima_ordem=4, ids=(77, 78))
        self.armazenamento = _ArmazenamentoFalso()
        self.repo = ConversaRepository(self.pool, self.armazenamento)

    def test_grava_duas_mensagens_continuando_a_ordem(self):
        gravado = self.repo.registrar_turno(_turno())
        self.assertEqual((gravado.ordem_prompt, gravado.ordem_resposta), (5, 6))
        self.assertEqual(len(self.pool.inserts_em("auditoria.mensagem ")), 2)

    def test_intencao_vai_na_linha_do_usuario_e_nao_na_do_agente(self):
        # O CHECK `mensagem_papel_coerente` recusa intenção na resposta. Trocar
        # os dois lados é o erro fácil de cometer aqui.
        self.repo.registrar_turno(_turno())
        usuario, agente = self.pool.inserts_em("auditoria.mensagem ")

        # (conversa, ordem, papel, formato, conteudo, intencao, confianca,
        #  resultado, modelo, tempo)
        self.assertEqual(usuario[2], "usuario")
        self.assertEqual(usuario[5], "orientar_avanco_mensal")
        self.assertEqual(usuario[7:], (None, None, None))

        self.assertEqual(agente[2], "agente")
        self.assertEqual(agente[5:7], (None, None))
        self.assertEqual(agente[7], "sucesso")
        self.assertEqual(agente[9], 1234)

    def test_o_conteudo_de_cada_linha_e_o_texto_do_papel(self):
        self.repo.registrar_turno(_turno())
        usuario, agente = self.pool.inserts_em("auditoria.mensagem ")
        self.assertEqual(usuario[4], "Qual o avanço do projeto SYN-004?")
        self.assertEqual(agente[4], "O avanço registrado em setembro é de 42%.")

    def test_a_conversa_e_criada_sem_duplicar(self):
        self.repo.registrar_turno(_turno())
        sql_conversa = [s for s, _ in self.pool.execucoes if "auditoria.conversa" in s]
        self.assertIn("ON CONFLICT (id) DO NOTHING", sql_conversa[0])

    def test_trava_a_conversa_antes_de_ler_a_ordem(self):
        # Sem o FOR UPDATE, dois turnos simultâneos leem o mesmo max(ordem) e o
        # segundo morre no UNIQUE (conversa_id, ordem).
        self.repo.registrar_turno(_turno())
        sqls = [s for s, _ in self.pool.execucoes]
        trava = next(i for i, s in enumerate(sqls) if "FOR UPDATE" in s)
        ordem = next(i for i, s in enumerate(sqls) if "max(ordem)" in s)
        self.assertLess(trava, ordem)

    def test_turno_em_conversa_alheia_e_recusado(self):
        """Segunda barreira, com a linha já travada.

        A rota tem um porteiro que recusa antes de gerar a resposta, mas entre
        aquela leitura e esta gravação existe janela. Aqui não existe: o dono é
        conferido sobre a linha que o `FOR UPDATE` acabou de travar.
        """
        self.pool = _PoolFalso(dono=99)
        self.repo = ConversaRepository(self.pool, _ArmazenamentoFalso())

        with self.assertRaises(ConversaDeOutroUsuario):
            self.repo.registrar_turno(_turno())

        # Nada foi commitado: nem as mensagens, nem o INSERT da conversa.
        self.assertFalse(self.pool.commitou)
        sqls = [s for s, _ in self.pool.execucoes]
        self.assertFalse(any("INSERT INTO auditoria.mensagem" in s for s in sqls))

    def test_conversa_nova_nao_tem_dono_a_contrariar(self):
        """`dono=None` é a primeira mensagem: o UUID ainda não existe no banco."""
        self.pool = _PoolFalso(dono=None)
        self.repo = ConversaRepository(self.pool, _ArmazenamentoFalso())

        self.repo.registrar_turno(_turno())

        self.assertTrue(self.pool.commitou)

    def test_fontes_sao_ligadas_a_resposta_e_nao_ao_prompt(self):
        # As fontes fundamentam o que o agente respondeu. Ligá-las ao prompt
        # inverteria o sentido da trilha do RNF12.
        fontes = (
            FonteDaResposta(chunk_id="c1", arquivo_origem="02_cronograma.xlsx", posicao=1),
            FonteDaResposta(chunk_id="c2", arquivo_origem="03_riscos.docx", posicao=2),
        )
        self.repo.registrar_turno(_turno(fontes=fontes))

        inseridas = self.pool.inserts_em("auditoria.mensagem_fonte")
        self.assertEqual(len(inseridas), 2)
        self.assertTrue(all(p[0] == 78 for p in inseridas), "id da mensagem do agente")
        self.assertEqual([p[2] for p in inseridas], ["c1", "c2"])

    def test_sem_fontes_nao_insere_nada_em_mensagem_fonte(self):
        self.repo.registrar_turno(_turno())
        self.assertEqual(self.pool.inserts_em("auditoria.mensagem_fonte"), [])


class TesteArquivamentoNoS3(unittest.TestCase):
    def setUp(self):
        self.pool = _PoolFalso(ultima_ordem=0, ids=(1, 2))
        self.armazenamento = _ArmazenamentoFalso()
        self.repo = ConversaRepository(self.pool, self.armazenamento)

    def test_arquiva_os_dois_lados_do_turno(self):
        gravado = self.repo.registrar_turno(_turno())
        chaves = [g["key"] for g in self.armazenamento.gravados]
        self.assertEqual(chaves, [gravado.chave_prompt, gravado.chave_resposta])
        self.assertEqual(
            chaves,
            [
                "conversas/3f1c0c4e-0000-4000-8000-000000000001/000001-usuario.txt",
                "conversas/3f1c0c4e-0000-4000-8000-000000000001/000002-agente.txt",
            ],
        )

    def test_o_texto_arquivado_e_o_mesmo_da_linha(self):
        self.repo.registrar_turno(_turno())
        self.assertEqual(
            self.armazenamento.gravados[0]["texto"], "Qual o avanço do projeto SYN-004?"
        )

    def test_metadado_do_objeto_nao_carrega_acento(self):
        # Metadado de objeto viaja em cabeçalho HTTP; acento ali quebra a
        # assinatura em parte das implementações de S3. O texto vai no corpo.
        self.repo.registrar_turno(_turno())
        for gravado in self.armazenamento.gravados:
            for chave, valor in gravado["metadata"].items():
                self.assertTrue(f"{chave}{valor}".isascii(), f"{chave}={valor}")

    def test_falha_no_s3_impede_o_commit(self):
        # A ordem das escritas existe para isto: se o objeto não for gravado,
        # não pode sobrar linha no banco apontando para ele.
        repo = ConversaRepository(self.pool, _ArmazenamentoFalso(erro=OSError("bucket fora")))
        with self.assertRaises(OSError):
            repo.registrar_turno(_turno())
        self.assertFalse(self.pool.commitou)

    def test_turno_bem_sucedido_commita(self):
        self.repo.registrar_turno(_turno())
        self.assertTrue(self.pool.commitou)


class TesteConversaoDasFontesDaBusca(unittest.TestCase):
    def test_posicao_comeca_em_um_e_segue_a_relevancia(self):
        # `mensagem_fonte.posicao` documenta "1 = mais próximo"; começar em zero
        # violaria o CHECK (posicao > 0) e inverteria a leitura da trilha.
        resultados = [
            mock.Mock(
                chunk_id=f"c{i}",
                arquivo_origem="a.docx",
                score=0.9 - i / 10,
                projeto_id="SYN-004",
                tipo_documento="cronograma",
                secao="Marcos",
                texto=f"trecho {i}",
            )
            for i in range(3)
        ]
        fontes = fontes_da_busca(resultados)
        self.assertEqual([f.posicao for f in fontes], [1, 2, 3])
        self.assertEqual([f.chunk_id for f in fontes], ["c0", "c1", "c2"])

    def test_copia_o_trecho_em_vez_de_deixar_para_juncao(self):
        # Reindexar troca o chunk_id (md5 do conteúdo). Uma junção feita depois
        # não encontraria a fonte justamente na auditoria.
        resultado = mock.Mock(
            chunk_id="c1",
            arquivo_origem="a.docx",
            score=0.9,
            projeto_id="SYN-004",
            tipo_documento="cronograma",
            secao="Marcos",
            texto="O marco foi replanejado.",
        )
        self.assertEqual(fontes_da_busca([resultado])[0].trecho, "O marco foi replanejado.")

    def test_lista_vazia(self):
        self.assertEqual(fontes_da_busca([]), ())


class TesteTitulo(unittest.TestCase):
    def test_usa_o_prompt_quando_curto(self):
        self.assertEqual(titulo_a_partir_do_prompt("Avanço do SYN-004"), "Avanço do SYN-004")

    def test_normaliza_espaco(self):
        self.assertEqual(titulo_a_partir_do_prompt("  a\n\n b  "), "a b")

    def test_trunca_prompt_longo(self):
        titulo = titulo_a_partir_do_prompt("palavra " * 40)
        self.assertLessEqual(len(titulo), 80)
        self.assertTrue(titulo.endswith("…"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
