# A classificação chegando à busca — e os limites disso.
#
# O valor deste módulo está no que ele RECUSA a fazer. Com F1-macro de 0,87,
# cerca de uma em oito classificações está errada, e deixar um rótulo errado
# estreitar a busca esconderia justamente o trecho que responderia a pergunta.
# Por isso o foco é sugestão, não ordem: quem busca recua.

from __future__ import annotations

import unittest

from pln.entidades import EntidadesExtraidas
from pln.intencao import IntencaoDetectada
from rag.parsers import _TIPO_POR_PREFIXO
from services.foco_da_busca import (
    SEM_FOCO,
    TIPO_DOCUMENTO_POR_INTENCAO,
    FocoDaBusca,
    focar_busca,
)


def _detectada(intencao: str, confianca: float, limiar: float = 0.20) -> IntencaoDetectada:
    return IntencaoDetectada(prevista=intencao, confianca=confianca, limiar=limiar)


class TesteMapaDeTipos(unittest.TestCase):
    def test_todo_tipo_mapeado_existe_na_taxonomia_dos_documentos(self) -> None:
        """Um tipo escrito errado não levanta erro: devolve busca vazia.

        É falha silenciosa — a pergunta viraria "não encontrei" sem que nada
        acusasse. Este teste é o que a torna barulhenta.
        """
        conhecidos = set(_TIPO_POR_PREFIXO.values())

        for intencao, tipo in TIPO_DOCUMENTO_POR_INTENCAO.items():
            with self.subTest(intencao):
                self.assertIn(
                    tipo, conhecidos,
                    f"{intencao} aponta para '{tipo}', que nenhum documento tem",
                )

    def test_o_mapa_e_parcial_de_proposito(self) -> None:
        # Forçar as dez intenções a um tipo inventaria correspondência:
        # `consultar_projeto_sintetico` atravessa todos os documentos.
        self.assertLess(len(TIPO_DOCUMENTO_POR_INTENCAO), 10)


class TesteFocarBusca(unittest.TestCase):
    def test_intencao_confiante_sugere_o_tipo_de_documento(self) -> None:
        foco = focar_busca(_detectada("orientar_riscos_problemas", 0.90), None)

        self.assertEqual(foco.tipo_documento, "riscos_problemas")

    def test_intencao_rejeitada_nao_foca_nada(self) -> None:
        """Abaixo do limiar o rótulo é palpite, e palpite não estreita busca.

        Estreitar com base num palpite é a forma mais direta de o classificador
        PIORAR uma resposta que funcionaria sem ele.
        """
        foco = focar_busca(_detectada("orientar_riscos_problemas", 0.05), None)

        self.assertIsNone(foco.tipo_documento)

    def test_sem_classificador_nao_foca_nada(self) -> None:
        self.assertEqual(focar_busca(None, None), SEM_FOCO)

    def test_intencao_sem_tipo_associado_nao_inventa_um(self) -> None:
        foco = focar_busca(_detectada("consultar_projeto_sintetico", 0.95), None)

        self.assertIsNone(foco.tipo_documento)

    def test_codigo_do_projeto_entra_mesmo_sem_classificador(self) -> None:
        """A extração é por REGRA, não por modelo: casa ou não casa.

        Por isso ela não depende do F1 e vale mesmo quando a intenção foi
        rejeitada ou nem existe.
        """
        foco = focar_busca(None, EntidadesExtraidas(projeto_codigo="SYN-04"))

        self.assertEqual(foco.projeto_codigo, "SYN-04")

    def test_codigo_sobrevive_a_intencao_rejeitada(self) -> None:
        foco = focar_busca(
            _detectada("orientar_tap", 0.01), EntidadesExtraidas(projeto_codigo="SYN-01")
        )

        self.assertEqual(foco.projeto_codigo, "SYN-01")
        self.assertIsNone(foco.tipo_documento)

    def test_os_dois_filtros_convivem(self) -> None:
        foco = focar_busca(
            _detectada("orientar_tap", 0.95), EntidadesExtraidas(projeto_codigo="SYN-01")
        )

        self.assertEqual(foco.tipo_documento, "termo_abertura")
        self.assertEqual(foco.projeto_codigo, "SYN-01")


class TesteFocoVazio(unittest.TestCase):
    def test_sem_foco_e_vazio(self) -> None:
        self.assertTrue(SEM_FOCO.vazio)

    def test_qualquer_filtro_deixa_de_ser_vazio(self) -> None:
        self.assertFalse(FocoDaBusca(tipo_documento="cronograma").vazio)
        self.assertFalse(FocoDaBusca(projeto_codigo="SYN-01").vazio)


if __name__ == "__main__":
    unittest.main()
