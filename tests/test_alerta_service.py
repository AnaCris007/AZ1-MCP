from __future__ import annotations

import unittest

from pln.caminhos import DATASET_PADRAO
from pln.classificador import carregar_dataset
from services.alerta_service import ConfiguracaoAlertas, DispatcherAlerta


class TestConfiguracaoAlertas(unittest.TestCase):
    def test_intencoes_de_risco_existem_no_catalogo_do_classificador(self) -> None:
        """Reproduz o defeito relatado: `alertas.yaml` citava intenções que o
        classificador nunca produz, e o alerta nunca disparava."""
        _, rotulos = carregar_dataset(DATASET_PADRAO)
        catalogo = set(rotulos)

        configuracao = ConfiguracaoAlertas.carregar()

        for intencao in configuracao.intencoes_de_risco:
            self.assertIn(intencao, catalogo)


class TestDeveDisparar(unittest.TestCase):
    def setUp(self) -> None:
        configuracao = ConfiguracaoAlertas(
            intencoes_de_risco=["gerar_alertas_pendencias"], limiar_confianca=0.70
        )
        self._dispatcher = DispatcherAlerta(engine=None, configuracao=configuracao)

    def test_dispara_com_intencao_de_risco_e_confianca_suficiente(self) -> None:
        self.assertTrue(self._dispatcher._deve_disparar("gerar_alertas_pendencias", 0.70))

    def test_nao_dispara_intencao_fora_da_lista_de_risco(self) -> None:
        self.assertFalse(self._dispatcher._deve_disparar("consultar_projeto_sintetico", 0.99))

    def test_nao_dispara_com_confianca_abaixo_do_limiar(self) -> None:
        self.assertFalse(self._dispatcher._deve_disparar("gerar_alertas_pendencias", 0.69))


if __name__ == "__main__":
    unittest.main()
