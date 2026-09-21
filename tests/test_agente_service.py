from __future__ import annotations

import unittest
from datetime import date

from services.agente_service import (
    LIMIAR_CONFIANCA_ACAO,
    AgenteDesligado,
    ExecutarIntencao,
    ResultadoAcao,
)
from services.portfolio_repository import Pendencia, SituacaoProjeto


def _pendencia(projeto_codigo: str, titulo: str = "Pendência") -> Pendencia:
    return Pendencia(
        id=1,
        projeto_codigo=projeto_codigo,
        projeto_nome="Projeto",
        codigo=None,
        tipo="risco",
        titulo=titulo,
        descricao=None,
        criticidade=None,
        responsavel=None,
        prazo=date(2026, 12, 1),
        situacao="aberta",
    )


def _projeto(codigo: str) -> SituacaoProjeto:
    return SituacaoProjeto(
        id=1,
        codigo=codigo,
        nome="Projeto",
        portfolio="Portfolio",
        fase="Execução",
        status="Em risco",
        data_inicio=None,
        data_termino_prevista=None,
        percentual_previsto=50.0,
        percentual_avanco=40.0,
        desvio_pp=-10.0,
        lider="Alguém",
        lider_email="alguem@example.com",
        pendencias_abertas=1,
        artefatos=1,
    )


class _PortfolioFalso:
    def __init__(self, pendencias=(), projetos=()) -> None:
        self._pendencias = pendencias
        self._projetos = projetos

    def pendencias(self):
        return self._pendencias

    def situacao_dos_projetos(self):
        return self._projetos


class TestExecutarIntencao(unittest.TestCase):
    def test_baixa_confianca_nao_executa_acao(self) -> None:
        agente = ExecutarIntencao(portfolio=_PortfolioFalso())

        resposta = agente.executar(
            intencao="gerar_alertas_pendencias",
            confianca=LIMIAR_CONFIANCA_ACAO - 0.01,
            texto="tem algo pendente?",
        )

        self.assertEqual(resposta.resultado, ResultadoAcao.SEM_ACAO)

    def test_intencao_sem_acao_implementada_fica_sem_acao(self) -> None:
        agente = ExecutarIntencao(portfolio=_PortfolioFalso())

        resposta = agente.executar(
            intencao="orientar_tap", confianca=0.95, texto="me ajuda com o TAP"
        )

        self.assertEqual(resposta.resultado, ResultadoAcao.SEM_ACAO)

    def test_fora_do_catalogo_com_confianca_suficiente_e_recusada(self) -> None:
        agente = ExecutarIntencao(portfolio=_PortfolioFalso())

        resposta = agente.executar(
            intencao="fora_do_catalogo", confianca=0.9, texto="qual a previsão do tempo?"
        )

        self.assertEqual(resposta.resultado, ResultadoAcao.RECUSADA_FORA_DO_CATALOGO)

    def test_gerar_alertas_pendencias_lista_todas_sem_codigo_de_projeto(self) -> None:
        pendencias = (_pendencia("SYN-01"), _pendencia("SYN-02"))
        agente = ExecutarIntencao(portfolio=_PortfolioFalso(pendencias=pendencias))

        resposta = agente.executar(
            intencao="gerar_alertas_pendencias",
            confianca=0.9,
            texto="o que precisa da minha atenção hoje?",
        )

        self.assertEqual(resposta.resultado, ResultadoAcao.PENDENCIAS)
        self.assertEqual(resposta.pendencias, pendencias)

    def test_gerar_alertas_pendencias_filtra_pelo_codigo_extraido(self) -> None:
        alvo = _pendencia("SYN-01")
        outro = _pendencia("SYN-02")
        agente = ExecutarIntencao(portfolio=_PortfolioFalso(pendencias=(alvo, outro)))

        resposta = agente.executar(
            intencao="gerar_alertas_pendencias",
            confianca=0.9,
            texto="tem pendência no SYN-01?",
        )

        self.assertEqual(resposta.pendencias, (alvo,))

    def test_consultar_projeto_sintetico_filtra_pelo_codigo_extraido(self) -> None:
        alvo = _projeto("SYN-01")
        outro = _projeto("SYN-02")
        agente = ExecutarIntencao(portfolio=_PortfolioFalso(projetos=(alvo, outro)))

        resposta = agente.executar(
            intencao="consultar_projeto_sintetico",
            confianca=0.9,
            texto="qual a situação do SYN-01?",
        )

        self.assertEqual(resposta.resultado, ResultadoAcao.PROJETO)
        self.assertEqual(resposta.projetos, (alvo,))


class TestAgenteDesligado(unittest.TestCase):
    def test_recusa_fora_do_catalogo_mesmo_sem_banco(self) -> None:
        agente = AgenteDesligado("SUPABASE_DB_URL não configurada")

        resposta = agente.executar(
            intencao="fora_do_catalogo", confianca=0.9, texto="qual a previsão do tempo?"
        )

        self.assertEqual(resposta.resultado, ResultadoAcao.RECUSADA_FORA_DO_CATALOGO)

    def test_acao_de_portfolio_fica_sem_acao_sem_banco(self) -> None:
        agente = AgenteDesligado("SUPABASE_DB_URL não configurada")

        resposta = agente.executar(
            intencao="gerar_alertas_pendencias", confianca=0.9, texto="o que está pendente?"
        )

        self.assertEqual(resposta.resultado, ResultadoAcao.SEM_ACAO)


if __name__ == "__main__":
    unittest.main()
