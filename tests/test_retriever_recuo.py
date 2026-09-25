# O recuo da busca focada.
#
# A classificação sugere onde procurar, e erra em cerca de uma de cada oito
# vezes. Sem recuo, esse erro esconderia o trecho que responderia a pergunta e
# o usuário receberia "não encontrei" sobre informação que existe.
#
# O recuo transforma o custo do erro: de uma resposta pior para uma consulta
# vetorial a mais. Estes testes travam essa propriedade.

from __future__ import annotations

import unittest
from unittest import mock

from rag import retriever
from rag.retriever import ResultadoBusca, buscar_com_recuo


def _resultado(score: float, tipo: str = "riscos_problemas") -> ResultadoBusca:
    return ResultadoBusca(
        texto="trecho", score=score, projeto_id="SYN-01",
        tipo_documento=tipo, secao="", arquivo_origem="a.docx", chunk_id="c1",
    )


class TesteBuscaComRecuo(unittest.TestCase):
    def test_sem_filtro_nenhum_busca_uma_vez_so(self) -> None:
        """O caminho de quem não tem classificação não paga nada a mais."""
        with mock.patch.object(retriever, "buscar", return_value=[_resultado(0.7)]) as espiao:
            resultados, focou = buscar_com_recuo("pergunta", score_minimo=0.6)

        self.assertEqual(espiao.call_count, 1)
        self.assertFalse(focou)
        self.assertEqual(len(resultados), 1)

    def test_filtro_que_acha_material_relevante_prevalece(self) -> None:
        with mock.patch.object(retriever, "buscar", return_value=[_resultado(0.72)]) as espiao:
            _, focou = buscar_com_recuo(
                "riscos do projeto", tipo_documento="riscos_problemas", score_minimo=0.6
            )

        self.assertTrue(focou, "o filtro trouxe material acima do corte e deveria valer")
        self.assertEqual(espiao.call_count, 1, "não deveria ter recuado")

    def test_filtro_que_nao_sustenta_nada_recua_para_busca_ampla(self) -> None:
        """O caso do rótulo errado: filtra no documento errado e não acha nada."""
        chamadas = []

        def falso(query, **kwargs):
            chamadas.append(kwargs)
            # focada devolve trecho fraco; ampla devolve trecho bom
            return [_resultado(0.2)] if kwargs.get("tipo_documento") else [_resultado(0.8)]

        with mock.patch.object(retriever, "buscar", falso):
            resultados, focou = buscar_com_recuo(
                "pergunta", tipo_documento="termo_abertura", score_minimo=0.6
            )

        self.assertFalse(focou, "o filtro falhou e o recuo deveria ter valido")
        self.assertEqual(len(chamadas), 2, "deveria ter buscado focado e depois amplo")
        self.assertIsNone(chamadas[1].get("tipo_documento"), "o recuo tem de ser SEM filtro")
        self.assertEqual(resultados[0].score, 0.8)

    def test_o_recuo_devolve_o_resultado_amplo_e_nao_o_focado(self) -> None:
        # A falha que este teste pega: recuar, buscar de novo e devolver
        # mesmo assim a lista focada — o recuo viraria decorativo.
        def falso(query, **kwargs):
            return [] if kwargs.get("projeto_id") else [_resultado(0.9)]

        with mock.patch.object(retriever, "buscar", falso):
            resultados, _ = buscar_com_recuo("x", projeto_id="SYN-99", score_minimo=0.6)

        self.assertEqual(len(resultados), 1)

    def test_o_corte_e_por_score_e_nao_por_quantidade(self) -> None:
        """Cinco trechos irrelevantes não são melhores que nenhum."""
        def falso(query, **kwargs):
            if kwargs.get("tipo_documento"):
                return [_resultado(0.3), _resultado(0.31), _resultado(0.29)]
            return [_resultado(0.85)]

        with mock.patch.object(retriever, "buscar", falso):
            _, focou = buscar_com_recuo("x", tipo_documento="cronograma", score_minimo=0.6)

        self.assertFalse(focou)


if __name__ == "__main__":
    unittest.main()
