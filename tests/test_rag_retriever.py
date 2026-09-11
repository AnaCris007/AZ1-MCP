# Testes do retriever do RAG.
#
# Duas coisas concentram o risco neste módulo, e nenhuma delas levantava erro
# quando quebrava:
#
#   1. A MONTAGEM DO FILTRO. `vecs` aceita no máximo uma entrada por filtro, de
#      modo que dois critérios exigem `$and`. Montar errado não falha — devolve
#      resultados de outro projeto, que parecem legítimos.
#   2. O REPASSE DO `chunk_id`. `indexador.buscar` sempre devolveu o id, e o
#      retriever o descartava. Sem ele `auditoria.mensagem_fonte.chunk_id` (NOT
#      NULL) não tem o que gravar, e o RNF12 deixa de ser verificável.

from __future__ import annotations

import unittest
from unittest import mock

from rag import retriever


def _bruto(identificador="c1", distancia=0.13, **metadados):
    base = {
        "projeto_id": "SYN-004",
        "tipo_documento": "cronograma",
        "secao": "Marcos",
        "arquivo_origem": "02_cronograma.xlsx",
    }
    base.update(metadados)
    return {
        "id": identificador,
        "distancia": distancia,
        "metadados": base,
        "texto": "O marco de entrega foi replanejado.",
    }


class _Ambiente:
    """Substitui o embedder e o indexador, os dois lados externos do retriever."""

    def __init__(self, brutos=None):
        self.brutos = brutos if brutos is not None else [_bruto()]
        self.chamada_ao_indexador = {}

    def __enter__(self):
        def buscar_falso(embedding, *, n_resultados=5, filtro=None):
            self.chamada_ao_indexador = {
                "embedding": embedding,
                "n_resultados": n_resultados,
                "filtro": filtro,
            }
            return self.brutos

        self._patches = [
            mock.patch.object(retriever, "vetorizar_consulta", return_value=[0.1, 0.2]),
            mock.patch.object(retriever.indexador, "buscar", buscar_falso),
        ]
        for p in self._patches:
            p.start()
        return self

    def __exit__(self, *args):
        for p in self._patches:
            p.stop()
        return False


class TesteRepasseDoChunkId(unittest.TestCase):
    def test_o_id_do_chunk_chega_ao_resultado(self):
        with _Ambiente([_bruto(identificador="9f2b1c7d")]):
            resultado = retriever.buscar("marcos")[0]
        self.assertEqual(resultado.chunk_id, "9f2b1c7d")

    def test_converte_distancia_de_cosseno_em_score(self):
        with _Ambiente([_bruto(distancia=0.13)]):
            self.assertAlmostEqual(retriever.buscar("marcos")[0].score, 0.87)

    def test_metadado_ausente_vira_string_vazia_e_nao_erro(self):
        # Chunk indexado antes de um campo existir não pode derrubar a busca.
        with _Ambiente([{"id": "c1", "distancia": 0.1, "metadados": {}, "texto": "t"}]):
            resultado = retriever.buscar("x")[0]
        self.assertEqual(resultado.secao, "")
        self.assertEqual(resultado.arquivo_origem, "")


class TesteMontagemDoFiltro(unittest.TestCase):
    def test_sem_criterio_nao_envia_filtro(self):
        with _Ambiente() as ambiente:
            retriever.buscar("marcos")
        self.assertIsNone(ambiente.chamada_ao_indexador["filtro"])

    def test_um_criterio_vai_sozinho(self):
        with _Ambiente() as ambiente:
            retriever.buscar("marcos", projeto_id="SYN-004")
        self.assertEqual(
            ambiente.chamada_ao_indexador["filtro"], {"projeto_id": {"$eq": "SYN-004"}}
        )

    def test_dois_criterios_exigem_and(self):
        # `vecs` aceita no máximo uma entrada por filtro: juntar os dois num
        # dicionário só faria o segundo ser ignorado em silêncio.
        with _Ambiente() as ambiente:
            retriever.buscar("marcos", projeto_id="SYN-004", tipo_documento="riscos_problemas")
        self.assertEqual(
            ambiente.chamada_ao_indexador["filtro"],
            {
                "$and": [
                    {"projeto_id": {"$eq": "SYN-004"}},
                    {"tipo_documento": {"$eq": "riscos_problemas"}},
                ]
            },
        )

    def test_criterio_vazio_conta_como_ausente(self):
        with _Ambiente() as ambiente:
            retriever.buscar("marcos", projeto_id="", tipo_documento=None)
        self.assertIsNone(ambiente.chamada_ao_indexador["filtro"])


class TesteVetorizacaoDaConsulta(unittest.TestCase):
    def test_usa_a_funcao_de_consulta_e_nao_a_de_documento(self):
        # Vetorizar a pergunta como documento degrada a recuperação sem erro, e
        # perde o cache que evita os 12 s do limitador.
        with mock.patch.object(
            retriever, "vetorizar_consulta", return_value=[0.5]
        ) as vetorizar, mock.patch.object(retriever.indexador, "buscar", return_value=[]):
            retriever.buscar("uma pergunta")
        vetorizar.assert_called_once_with("uma pergunta")

    def test_repassa_n_resultados(self):
        with _Ambiente() as ambiente:
            retriever.buscar("marcos", n_resultados=3)
        self.assertEqual(ambiente.chamada_ao_indexador["n_resultados"], 3)


if __name__ == "__main__":
    unittest.main(verbosity=2)
