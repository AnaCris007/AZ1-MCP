# Testes do leitor do portfólio.
#
# Dois deles não verificam comportamento, verificam ACOPLAMENTO com coisas que
# vivem fora do Python e mudam sem avisar:
#
#   - a view `portfolio.vw_projeto_situacao`, que o repositório lê em vez de
#     refazer as junções à mão;
#   - o CHECK de `portfolio.pendencia.situacao`, duplicado como constante.
#
# Os dois falhariam em produção, em silêncio, e nenhum dublê os pegaria.

from __future__ import annotations

import re
import unittest
from pathlib import Path

from services.portfolio_repository import (
    SITUACAO_ABERTA,
    SITUACAO_RESOLVIDA,
    SITUACOES_VALIDAS,
    PortfolioRepository,
    SituacaoInvalida,
)

RAIZ = Path(__file__).resolve().parent.parent
DDL = (RAIZ / "src" / "database" / "01_create_database.sql").read_text(encoding="utf-8")
SEED = (RAIZ / "src" / "database" / "02_initial_data.sql").read_text(encoding="utf-8")


class _CursorFalso:
    def __init__(self, execucoes, respostas):
        self._execucoes = execucoes
        self._respostas = respostas

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def execute(self, sql, parametros=()):
        self._execucoes.append((" ".join(sql.split()), parametros))

    def fetchone(self):
        return self._respostas.pop(0) if self._respostas else None

    def fetchall(self):
        return self._respostas.pop(0) if self._respostas else []


class _ConexaoFalsa:
    def __init__(self, pool):
        self._pool = pool

    def cursor(self):
        return _CursorFalso(self._pool.execucoes, self._pool.respostas)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class _PoolFalso:
    def __init__(self, respostas=None):
        self.execucoes: list[tuple[str, tuple]] = []
        self.respostas = respostas or []

    def connection(self):
        return _ConexaoFalsa(self)


class TesteLeituraUsaAView(unittest.TestCase):
    def test_projetos_leem_a_view_e_nao_uma_juncao_propria(self):
        # A view já resolve as contagens de pendências e artefatos e os dois
        # JOINs. Refazer isso aqui duplicaria lógica que o DDL mantém — e que
        # divergiria dela na primeira mudança de modelo.
        pool = _PoolFalso(respostas=[[]])
        PortfolioRepository(pool).situacao_dos_projetos()

        sql = pool.execucoes[0][0]
        self.assertIn("FROM portfolio.vw_projeto_situacao", sql)

    def test_projetos_saem_do_mais_atrasado_para_o_menos(self):
        # É a ordem em que um PMO lê, e a mesma que serve de resumo ao chat.
        pool = _PoolFalso(respostas=[[]])
        PortfolioRepository(pool).situacao_dos_projetos()
        self.assertIn("ORDER BY desvio_pp ASC", pool.execucoes[0][0])

    def test_a_view_existe_no_ddl(self):
        self.assertIn("vw_projeto_situacao", DDL)


class TesteEscritaEhMinima(unittest.TestCase):
    def test_o_update_toca_apenas_situacao(self):
        # Título e descrição vieram de planilhas que estão vetorizadas em
        # `vecs.documentos_metro`. Editá-los faria a linha relacional e o trecho
        # citado pelo chat discordarem — a incoerência que o RNF12 mede.
        pool = _PoolFalso(respostas=[(7,), None])
        PortfolioRepository(pool).alterar_situacao(pendencia_id=7, situacao=SITUACAO_RESOLVIDA)

        update = next(sql for sql, _ in pool.execucoes if sql.startswith("UPDATE"))
        self.assertIn("SET situacao = %s", update)
        for proibida in ("titulo", "descricao", "projeto_id", "criticidade"):
            self.assertNotIn(f"{proibida} =", update)

    def test_pendencia_inexistente_devolve_none(self):
        pool = _PoolFalso(respostas=[None])
        self.assertIsNone(
            PortfolioRepository(pool).alterar_situacao(pendencia_id=999, situacao=SITUACAO_ABERTA)
        )

    def test_situacao_fora_do_dominio_nao_chega_ao_banco(self):
        pool = _PoolFalso()
        with self.assertRaises(SituacaoInvalida):
            PortfolioRepository(pool).alterar_situacao(pendencia_id=1, situacao="inventada")
        self.assertEqual(pool.execucoes, [])


class TesteDominioBateComODdl(unittest.TestCase):
    def test_situacoes_validas_espelham_o_check(self):
        achado = re.search(
            r"situacao\s+TEXT\s+NOT\s+NULL[^,]*?CHECK\s*\(\s*situacao\s+IN\s*\((.*?)\)\s*\)",
            DDL,
            re.DOTALL,
        )
        self.assertIsNotNone(achado, "CHECK de pendencia.situacao não encontrado no DDL")
        do_ddl = set(re.findall(r"'([a-z_]+)'", achado.group(1)))
        self.assertEqual(
            SITUACOES_VALIDAS, do_ddl,
            "o domínio de situacao divergiu entre o banco e o repositório.",
        )

    def test_as_duas_constantes_usadas_pertencem_ao_dominio(self):
        self.assertIn(SITUACAO_RESOLVIDA, SITUACOES_VALIDAS)
        self.assertIn(SITUACAO_ABERTA, SITUACOES_VALIDAS)


class TesteMapaDePrioridadeCobreASeed(unittest.TestCase):
    def test_toda_criticidade_semeada_tem_prioridade(self):
        # `criticidade` é TEXT sem CHECK: o domínio real é o que a seed carrega.
        # Um valor sem entrada no mapa cairia no padrão e viraria "media" em
        # silêncio — este teste torna a omissão visível.
        from routes.portfolio import _PRIORIDADE_POR_CRITICIDADE

        bloco = SEED[SEED.index("INSERT INTO portfolio.pendencia") :]
        bloco = bloco[: bloco.index(";")]
        da_seed = set(re.findall(r"'(Crítico|Alto|Moderado|Baixo)'", bloco))

        self.assertTrue(da_seed, "nenhuma criticidade encontrada na seed")
        self.assertEqual(
            da_seed - set(_PRIORIDADE_POR_CRITICIDADE), set(),
            "criticidade presente na seed e ausente do mapa de prioridade.",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
