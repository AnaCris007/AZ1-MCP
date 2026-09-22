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
from datetime import date
from pathlib import Path

from services.portfolio_repository import (
    _SQL_PROJETOS,
    SITUACAO_ABERTA,
    SITUACAO_RESOLVIDA,
    SITUACOES_VALIDAS,
    PortfolioRepository,
    SituacaoInvalida,
)

RAIZ = Path(__file__).resolve().parent.parent
DDL = (RAIZ / "src" / "database" / "01_create_database.sql").read_text(encoding="utf-8")
SEED = (RAIZ / "src" / "database" / "02_initial_data.sql").read_text(encoding="utf-8")


def _sem_comentarios(sql: str) -> str:
    """O SQL sem as linhas de `--`, para asserções sobre estrutura."""
    return "\n".join(re.sub(r"--.*$", "", linha) for linha in sql.split("\n"))


def _colunas_no_topo(corpo: str) -> list[str]:
    """Nomes de saída de uma lista de colunas SQL, na ordem.

    Divide por vírgula respeitando parênteses — as subconsultas de contagem da
    view têm vírgula nenhuma, mas têm `FROM` e parênteses, e um split ingênuo
    as quebraria ao meio.
    """
    partes, atual, profundidade = [], [], 0
    for caractere in corpo:
        if caractere == "(":
            profundidade += 1
        elif caractere == ")":
            profundidade -= 1
        if caractere == "," and profundidade == 0:
            partes.append("".join(atual))
            atual = []
        else:
            atual.append(caractere)
    partes.append("".join(atual))

    nomes = []
    for parte in partes:
        expressao = " ".join(parte.split())
        if not expressao:
            continue
        # `x AS apelido` vale pelo apelido; `pr.codigo` vale pelo que vem depois
        # do ponto; `pr.id` idem.
        apelido = re.search(r"\bAS\s+([A-Za-z_][A-Za-z0-9_]*)\s*$", expressao, re.IGNORECASE)
        nomes.append(apelido.group(1) if apelido else expressao.rsplit(".", 1)[-1])
    return nomes


def _colunas_da_view() -> list[str]:
    inicio = DDL.index("CREATE VIEW portfolio.vw_projeto_situacao")
    # O FROM da view, nao o das subconsultas de contagem: so o de cima
    # comeca em coluna 1.
    fim = DDL.index("\nFROM portfolio.projeto pr", inicio)
    corpo = DDL[DDL.index("SELECT", inicio) + len("SELECT") : fim]
    return _colunas_no_topo(corpo)


def _colunas_do_select() -> list[str]:
    corpo = _SQL_PROJETOS[
        _SQL_PROJETOS.index("SELECT") + len("SELECT") : _SQL_PROJETOS.index("FROM portfolio.vw_projeto_situacao")
    ]
    return _colunas_no_topo(corpo)


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

    def test_a_ordem_do_select_acompanha_a_da_view(self):
        """O acoplamento que não avisa quando quebra.

        `_para_projeto` lê a linha POR POSIÇÃO. Se a view ganhar, perder ou
        reordenar uma coluna e o `SELECT` do repositório não acompanhar, cada
        campo passa a ler o vizinho — e entre colunas do mesmo tipo isso não
        levanta exceção nenhuma. Foi exatamente o risco da remoção de
        `portfolio.portfolio`, que tirou uma coluna do meio da lista.

        Comparar as duas ordens aqui é o que transforma um erro silencioso em
        suíte vermelha.
        """
        self.assertEqual(_colunas_da_view(), _colunas_do_select())

    def test_o_mapeamento_posicional_poe_cada_valor_no_seu_campo(self):
        """Valores distinguíveis, na ordem da view, conferidos um a um.

        Em especial `lider` e `lider_email`: são vizinhos, são os dois texto, e
        trocá-los passaria por qualquer asserção de tipo.
        """
        linha = (
            7, "SYN-09", "Nome do Projeto", "Execução", "Atrasado",
            date(2026, 1, 2), date(2026, 12, 31),
            80, 65, -15,
            "Nome do Líder", "lider@metro.example",
            3, 11,
        )
        self.assertEqual(len(linha), len(_colunas_da_view()))

        pool = _PoolFalso(respostas=[[linha]])
        projeto = PortfolioRepository(pool).situacao_dos_projetos()[0]

        self.assertEqual(projeto.id, 7)
        self.assertEqual(projeto.codigo, "SYN-09")
        self.assertEqual(projeto.nome, "Nome do Projeto")
        self.assertEqual(projeto.fase, "Execução")
        self.assertEqual(projeto.status, "Atrasado")
        self.assertEqual(projeto.data_inicio, date(2026, 1, 2))
        self.assertEqual(projeto.data_termino_prevista, date(2026, 12, 31))
        self.assertEqual(projeto.percentual_previsto, 80.0)
        self.assertEqual(projeto.percentual_avanco, 65.0)
        self.assertEqual(projeto.desvio_pp, -15.0)
        self.assertEqual(projeto.lider, "Nome do Líder")
        self.assertEqual(projeto.lider_email, "lider@metro.example")
        self.assertEqual(projeto.pendencias_abertas, 3)
        self.assertEqual(projeto.artefatos, 11)

    def test_a_tabela_portfolio_nao_existe_mais(self):
        """Removida em 08_remove_portfolio.sql: nada pode voltar a referenciá-la.

        Compara o SQL sem os comentários, porque o DDL explica em texto por que
        a tabela saiu — e uma asserção que tropeça na própria justificativa
        obrigaria a escolher entre o teste e a documentação.
        """
        self.assertNotIn("portfolio.portfolio", _sem_comentarios(DDL))
        self.assertNotIn("portfolio_id", _sem_comentarios(DDL))
        self.assertNotIn("portfolio.portfolio", _sem_comentarios(SEED))


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
