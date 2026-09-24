from __future__ import annotations

import unittest

from pln.entidades import extrair_entidades


class TestExtrairEntidades(unittest.TestCase):
    def test_reconhece_codigo_de_projeto(self) -> None:
        entidades = extrair_entidades("Qual a situação do projeto SYN-01?")
        self.assertEqual(entidades.projeto_codigo, "SYN-01")

    def test_normaliza_para_maiusculas(self) -> None:
        entidades = extrair_entidades("me mostra as pendências do syn-07")
        self.assertEqual(entidades.projeto_codigo, "SYN-07")

    def test_ausencia_de_codigo_devolve_none(self) -> None:
        entidades = extrair_entidades("O que precisa da minha atenção hoje?")
        self.assertIsNone(entidades.projeto_codigo)

    def test_nao_confunde_outras_siglas_com_codigo_de_projeto(self) -> None:
        entidades = extrair_entidades("Quem precisa assinar o Termo de Abertura (TAP-01)?")
        self.assertIsNone(entidades.projeto_codigo)


if __name__ == "__main__":
    unittest.main()
