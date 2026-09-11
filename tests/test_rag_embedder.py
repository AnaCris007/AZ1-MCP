# Testes do embedder do RAG.
#
# Este módulo não tinha teste nenhum, e duas correções acabaram de entrar nele:
# a dimensão que cabe no índice do pgvector e o limitador de requisições com
# trava. São exatamente essas duas que os testes abaixo prendem — a primeira
# porque quebrá-la só apareceria na hora de criar o índice, e a segunda porque
# a corrida antiga não levantava erro: ela estourava a cota silenciosamente.

from __future__ import annotations

import threading
import unittest
from unittest import mock

from rag import embedder, indexador

# Limite do pgvector para índices HNSW e IVFFlat.
LIMITE_PGVECTOR = 2000


class _RespostaFalsa:
    def __init__(self, vetores):
        self.embeddings = [mock.Mock(values=v) for v in vetores]


def _cliente_falso(vetores):
    cliente = mock.Mock()
    cliente.models.embed_content.return_value = _RespostaFalsa(vetores)
    return cliente


class TesteDimensao(unittest.TestCase):
    def test_cabe_no_limite_de_indice_do_pgvector(self):
        # Acima de 2000 o `create_index` falha e toda busca vira varredura
        # sequencial. O valor nativo do modelo é 3072, então este teste é o que
        # impede alguém de "restaurar" o padrão sem saber o que quebra.
        self.assertLessEqual(embedder.DIMENSAO_EMBEDDING, LIMITE_PGVECTOR)

    def test_indexador_usa_a_mesma_constante_do_embedder(self):
        # Duas constantes separadas divergiriam em silêncio: a coleção seria
        # criada com um tamanho e o modelo produziria outro.
        self.assertIs(indexador.DIMENSAO_EMBEDDING, embedder.DIMENSAO_EMBEDDING)


class TesteNormalizacao(unittest.TestCase):
    # Só a saída de 3072 vem normalizada de fábrica. Truncada, precisa desta
    # etapa, senão a distância de cosseno compara vetores de módulos diferentes.
    def test_resultado_tem_norma_unitaria(self):
        vetor = embedder.normalizar([3.0, 4.0])
        self.assertAlmostEqual(sum(v * v for v in vetor) ** 0.5, 1.0)

    def test_preserva_a_direcao(self):
        self.assertEqual(embedder.normalizar([3.0, 4.0]), [0.6, 0.8])

    def test_vetor_nulo_nao_divide_por_zero(self):
        self.assertEqual(embedder.normalizar([0.0, 0.0]), [0.0, 0.0])


class TesteLimitadorDeRequisicoes(unittest.TestCase):
    def setUp(self):
        embedder._proxima_vaga = 0.0

    def test_chamadas_sequenciais_recebem_vagas_espacadas(self):
        esperas = []
        with mock.patch.object(embedder.time, "sleep", esperas.append):
            for _ in range(3):
                embedder._aguardar_vaga()

        # A primeira não espera; as seguintes esperam o intervalo acumulado.
        self.assertEqual(len(esperas), 2)
        self.assertAlmostEqual(esperas[0], embedder._INTERVALO_MIN, delta=0.5)
        self.assertAlmostEqual(esperas[1], 2 * embedder._INTERVALO_MIN, delta=0.5)

    def test_threads_concorrentes_nao_disputam_a_mesma_vaga(self):
        # ESTE É O TESTE DA CORREÇÃO. A versão antiga lia e escrevia uma global
        # sem trava: as cinco threads liam o mesmo valor, todas concluíam que
        # podiam chamar agora, e as cinco esperas saíam iguais a zero — cota
        # estourada sem erro nenhum. Com a reserva sob trava, cada uma recebe
        # uma vaga distinta.
        esperas: list[float] = []
        trava_da_lista = threading.Lock()

        def registrar(segundos):
            with trava_da_lista:
                esperas.append(segundos)

        with mock.patch.object(embedder.time, "sleep", registrar):
            threads = [threading.Thread(target=embedder._aguardar_vaga) for _ in range(5)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()

        # Uma thread sai sem esperar; as outras quatro esperam valores distintos.
        self.assertEqual(len(esperas), 4)
        self.assertEqual(len({round(e, 3) for e in esperas}), 4)

    def test_a_fila_avanca_um_intervalo_por_chamada(self):
        with mock.patch.object(embedder.time, "sleep", lambda _: None):
            embedder._aguardar_vaga()
            primeira = embedder._proxima_vaga
            embedder._aguardar_vaga()

        self.assertAlmostEqual(
            embedder._proxima_vaga - primeira, embedder._INTERVALO_MIN, delta=0.5
        )


class TesteChamadaAApi(unittest.TestCase):
    def setUp(self):
        embedder._proxima_vaga = 0.0
        embedder.limpar_cache_de_consultas()
        sleep = mock.patch.object(embedder.time, "sleep", lambda _: None)
        sleep.start()
        self.addCleanup(sleep.stop)

    def _config_da_ultima_chamada(self, cliente):
        return cliente.models.embed_content.call_args.kwargs["config"]

    def test_pede_a_dimensao_truncada_e_um_timeout(self):
        cliente = _cliente_falso([[3.0, 4.0]])
        with mock.patch.object(embedder, "_cliente", return_value=cliente):
            embedder.vetorizar_documentos(["um trecho"])

        config = self._config_da_ultima_chamada(cliente)
        self.assertEqual(config.output_dimensionality, embedder.DIMENSAO_EMBEDDING)
        # Sem timeout, uma chamada pendurada consome o orçamento inteiro do RNF01.
        self.assertEqual(config.http_options.timeout, embedder.TIMEOUT_MS)

    def test_documento_e_consulta_usam_tarefas_diferentes(self):
        # Usar a mesma tarefa nos dois lados degrada a recuperação sem erro.
        cliente = _cliente_falso([[3.0, 4.0]])
        with mock.patch.object(embedder, "_cliente", return_value=cliente):
            embedder.vetorizar_documentos(["um trecho"])
            tarefa_documento = self._config_da_ultima_chamada(cliente).task_type

            embedder.vetorizar_consulta("uma pergunta")
            tarefa_consulta = self._config_da_ultima_chamada(cliente).task_type

        self.assertEqual(tarefa_documento, embedder.TAREFA_DOCUMENTO)
        self.assertEqual(tarefa_consulta, embedder.TAREFA_CONSULTA)
        self.assertNotEqual(tarefa_documento, tarefa_consulta)

    def test_normaliza_o_que_a_api_devolve(self):
        cliente = _cliente_falso([[3.0, 4.0]])
        with mock.patch.object(embedder, "_cliente", return_value=cliente):
            saida = embedder.vetorizar_documentos(["um trecho"])
        self.assertEqual(saida, [[0.6, 0.8]])

    def test_lista_vazia_nao_chama_a_api(self):
        cliente = _cliente_falso([])
        with mock.patch.object(embedder, "_cliente", return_value=cliente):
            self.assertEqual(embedder.vetorizar_documentos([]), [])
        cliente.models.embed_content.assert_not_called()

    def test_quebra_em_lotes(self):
        textos = [f"t{i}" for i in range(embedder.TAMANHO_LOTE * 2 + 1)]
        cliente = _cliente_falso([[1.0, 0.0]])
        with mock.patch.object(embedder, "_cliente", return_value=cliente):
            embedder.vetorizar_documentos(textos)
        self.assertEqual(cliente.models.embed_content.call_count, 3)


class TesteCacheDeConsultas(unittest.TestCase):
    def setUp(self):
        embedder._proxima_vaga = 0.0
        embedder.limpar_cache_de_consultas()
        self.addCleanup(embedder.limpar_cache_de_consultas)
        sleep = mock.patch.object(embedder.time, "sleep", lambda _: None)
        sleep.start()
        self.addCleanup(sleep.stop)

    def test_consulta_repetida_nao_chama_a_api_de_novo(self):
        # Cada acerto de cache economiza uma espera de 12 s no caminho da busca.
        cliente = _cliente_falso([[3.0, 4.0]])
        with mock.patch.object(embedder, "_cliente", return_value=cliente):
            primeira = embedder.vetorizar_consulta("mesma pergunta")
            segunda = embedder.vetorizar_consulta("mesma pergunta")

        self.assertEqual(cliente.models.embed_content.call_count, 1)
        self.assertEqual(primeira, segunda)

    def test_consultas_distintas_chamam_a_api(self):
        cliente = _cliente_falso([[3.0, 4.0]])
        with mock.patch.object(embedder, "_cliente", return_value=cliente):
            embedder.vetorizar_consulta("pergunta A")
            embedder.vetorizar_consulta("pergunta B")
        self.assertEqual(cliente.models.embed_content.call_count, 2)

    def test_devolve_lista_nova_a_cada_chamada(self):
        # O cache guarda tupla justamente para isto: se devolvesse a mesma
        # lista, um chamador que a alterasse corromperia as consultas seguintes.
        cliente = _cliente_falso([[3.0, 4.0]])
        with mock.patch.object(embedder, "_cliente", return_value=cliente):
            primeira = embedder.vetorizar_consulta("pergunta")
            primeira.append(99.0)
            segunda = embedder.vetorizar_consulta("pergunta")

        self.assertEqual(segunda, [0.6, 0.8])


if __name__ == "__main__":
    unittest.main(verbosity=2)
