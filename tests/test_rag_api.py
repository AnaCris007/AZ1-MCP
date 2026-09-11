# Testes de contrato da rota de busca semântica e dos dois endpoints de saúde.
#
# A busca chega à rota por injeção, e não por import de módulo, justamente para
# que estes testes existam: sem isso, exercitar `POST /rag/search` exigiria um
# Supabase de verdade e uma chamada ao Gemini de 12 segundos.

from __future__ import annotations

import unittest

from fastapi.testclient import TestClient

from az1_api.dependencies import get_connection_pool, get_document_searcher
from az1_api.main import app
from rag.retriever import ResultadoBusca
from services.database_service import BancoNaoConfigurado

RESULTADO = ResultadoBusca(
    texto="O marco de entrega foi replanejado para outubro.",
    score=0.87,
    projeto_id="SYN-004",
    tipo_documento="cronograma",
    secao="Marcos",
    arquivo_origem="02_cronograma.xlsx",
    chunk_id="9f2b1c7d4e5a6b8c9d0e1f2a3b4c5d6e",
)


class _BaseDeApi(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.addCleanup(app.dependency_overrides.clear)


class TesteBuscaRag(_BaseDeApi):
    def _com_busca(self, funcao):
        app.dependency_overrides[get_document_searcher] = lambda: funcao

    def test_devolve_os_resultados_com_as_fontes(self):
        # As fontes são o que o RNF12 cobra: referência recuperável para cada
        # afirmação. Se a rota perder `arquivo_origem` ou `secao`, o requisito
        # cai sem que a resposta pareça errada.
        self._com_busca(lambda *a, **kw: [RESULTADO])

        resposta = self.client.post("/api/v1/rag/search", json={"query": "marcos do projeto"})

        self.assertEqual(resposta.status_code, 200)
        corpo = resposta.json()
        self.assertEqual(corpo["query"], "marcos do projeto")
        self.assertEqual(len(corpo["resultados"]), 1)
        self.assertEqual(corpo["resultados"][0]["arquivo_origem"], "02_cronograma.xlsx")
        self.assertEqual(corpo["resultados"][0]["secao"], "Marcos")
        self.assertAlmostEqual(corpo["resultados"][0]["score"], 0.87)
        # Sem o `chunk_id` a resposta cita a fonte mas não permite voltar até
        # ela, e é justamente ele que `auditoria.mensagem_fonte` grava.
        self.assertEqual(
            corpo["resultados"][0]["chunk_id"], "9f2b1c7d4e5a6b8c9d0e1f2a3b4c5d6e"
        )

    def test_repassa_os_filtros_para_a_busca(self):
        recebidos = {}

        def espiao(query, **kwargs):
            recebidos.update(kwargs)
            recebidos["query"] = query
            return []

        self._com_busca(espiao)
        self.client.post(
            "/api/v1/rag/search",
            json={
                "query": "riscos",
                "n_resultados": 3,
                "projeto_id": "SYN-004",
                "tipo_documento": "riscos_problemas",
            },
        )

        self.assertEqual(recebidos["query"], "riscos")
        self.assertEqual(recebidos["n_resultados"], 3)
        self.assertEqual(recebidos["projeto_id"], "SYN-004")
        self.assertEqual(recebidos["tipo_documento"], "riscos_problemas")

    def test_sem_resultados_devolve_lista_vazia_e_nao_erro(self):
        self._com_busca(lambda *a, **kw: [])
        resposta = self.client.post("/api/v1/rag/search", json={"query": "nada"})
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta.json()["resultados"], [])

    def test_recusa_n_resultados_fora_da_faixa(self):
        self._com_busca(lambda *a, **kw: [])
        for n in (0, 21):
            resposta = self.client.post(
                "/api/v1/rag/search", json={"query": "x", "n_resultados": n}
            )
            self.assertEqual(resposta.status_code, 422)

    def test_exige_a_query(self):
        self._com_busca(lambda *a, **kw: [])
        self.assertEqual(self.client.post("/api/v1/rag/search", json={}).status_code, 422)


class TesteSaude(_BaseDeApi):
    def test_health_nao_toca_o_banco(self):
        # O RNF07 exige 200 em até dois segundos. Se `/health` dependesse do
        # banco, o requisito passaria a depender da latência de terceiros — este
        # teste falha se alguém ligar o pool nele.
        def explodir():
            raise AssertionError("/health não pode tocar o banco")

        app.dependency_overrides[get_connection_pool] = explodir

        resposta = self.client.get("/health")
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta.json(), {"status": "ok"})

    def test_ready_responde_200_com_banco_utilizavel(self):
        from unittest import mock

        pool = mock.MagicMock()
        cursor = pool.connection.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value
        cursor.fetchone.return_value = (1,)
        app.dependency_overrides[get_connection_pool] = lambda: pool

        resposta = self.client.get("/health/ready")
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta.json()["status"], "ok")

    def test_ready_responde_503_sem_configuracao(self):
        # Banco não configurado é indisponibilidade para quem chama, e não erro
        # de programação: precisa sair como 503, não como 500.
        def sem_config():
            raise BancoNaoConfigurado("SUPABASE_DB_URL não configurada.")

        app.dependency_overrides[get_connection_pool] = sem_config

        resposta = self.client.get("/health/ready")
        self.assertEqual(resposta.status_code, 503)
        self.assertIn("SUPABASE_DB_URL", resposta.json()["motivo"])

    def test_ready_responde_503_quando_a_conexao_falha(self):
        # O pool abre sem bloquear: `open()` só sobe os trabalhadores de fundo.
        # Banco inalcançável aparece no `pool.connection()`, dentro de
        # `verificar_conexao` — é esse caminho que precisa virar 503.
        from unittest import mock

        pool = mock.MagicMock()
        pool.connection.side_effect = OSError("conexão recusada")
        app.dependency_overrides[get_connection_pool] = lambda: pool

        resposta = self.client.get("/health/ready")
        self.assertEqual(resposta.status_code, 503)
        self.assertIn("OSError", resposta.json()["motivo"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
