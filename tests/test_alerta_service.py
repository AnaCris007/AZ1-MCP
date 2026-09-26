from __future__ import annotations

import unittest

from pln.caminhos import DATASET_PADRAO
from pln.classificador import carregar_dataset
from pln.intencao import LIMIAR_PADRAO, IntencaoDetectada
from services.alerta_service import _ARQUIVO_CONFIG, ConfiguracaoAlertas, DispatcherAlerta


def _detectada(prevista: str, confianca: float) -> IntencaoDetectada:
    return IntencaoDetectada(prevista=prevista, confianca=confianca)


class TestConfiguracaoAlertas(unittest.TestCase):
    def test_intencoes_de_risco_existem_no_catalogo_do_classificador(self) -> None:
        """Reproduz o defeito relatado: `alertas.yaml` citava intenções que o
        classificador nunca produz, e o alerta nunca disparava."""
        _, rotulos = carregar_dataset(DATASET_PADRAO)
        catalogo = set(rotulos)

        configuracao = ConfiguracaoAlertas.carregar()

        for intencao in configuracao.intencoes_de_risco:
            self.assertIn(intencao, catalogo)

    def test_yaml_nao_declara_limiar_proprio(self) -> None:
        """O limiar é um só, e mora em `pln.intencao`.

        Havia um `0.70` aqui e outro fixo em `agente_service`, nenhum dos dois
        igual ao que `pln.metricas` media. Duas cópias de um número calibrado
        divergem em silêncio: quem ajusta uma não sabe da outra.
        """
        bruto = _ARQUIVO_CONFIG.read_text(encoding="utf-8")

        self.assertNotIn(
            "limiar", bruto,
            "alertas.yaml voltou a declarar limiar. A decisão de confiar na "
            "classificação é de pln.intencao.LIMIAR_PADRAO, aplicada antes de o "
            "despacho ser consultado.",
        )


class TestDeveDisparar(unittest.TestCase):
    def setUp(self) -> None:
        configuracao = ConfiguracaoAlertas(intencoes_de_risco=["gerar_alertas_pendencias"])
        self._dispatcher = DispatcherAlerta(engine=None, configuracao=configuracao)

    def test_dispara_com_intencao_de_risco_e_confianca_suficiente(self) -> None:
        self.assertTrue(
            self._dispatcher._deve_disparar(
                _detectada("gerar_alertas_pendencias", LIMIAR_PADRAO)
            )
        )

    def test_nao_dispara_intencao_fora_da_lista_de_risco(self) -> None:
        self.assertFalse(
            self._dispatcher._deve_disparar(_detectada("consultar_projeto_sintetico", 0.99))
        )

    def test_nao_dispara_quando_a_deteccao_foi_rejeitada(self) -> None:
        """Rejeitada é `fora_do_catalogo`, que nunca está na lista de risco.

        O despacho não reaplica limiar nenhum: a regra já veio de
        `pln.intencao`. Este teste existe para que isso continue verdadeiro se
        alguém mexer na lista.
        """
        self.assertFalse(
            self._dispatcher._deve_disparar(
                _detectada("gerar_alertas_pendencias", LIMIAR_PADRAO - 0.01)
            )
        )


if __name__ == "__main__":
    unittest.main()
