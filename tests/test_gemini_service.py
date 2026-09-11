from __future__ import annotations

import unittest
from unittest.mock import Mock

from google.genai import errors

from rag.retriever import ResultadoBusca
from services.chat_service import ChatModelUnavailableError
from services.gemini_service import MAX_OUTPUT_TOKENS, GeminiChatModel


class TestGeminiChatModel(unittest.TestCase):
    def test_gera_resposta_com_contrato_esperado(self) -> None:
        client = Mock()
        client.models.generate_content.return_value = Mock(text="resposta do modelo")
        model = GeminiChatModel(client=client, model="gemini-3.5-flash-lite")

        reply = model.generate_reply("Oi")

        self.assertEqual(reply, "resposta do modelo")
        client.models.generate_content.assert_called_once()
        kwargs = client.models.generate_content.call_args.kwargs
        self.assertEqual(kwargs["model"], "gemini-3.5-flash-lite")
        # `contents` deixou de ser a string crua quando o histórico por conversa
        # entrou: agora é sempre a lista de turnos, mesmo com um turno só. Fixar
        # a forma `role`/`parts` aqui é o que impede que um refactor volte a
        # mandar texto solto — o SDK aceita os dois, e o histórico sumiria sem
        # erro nenhum.
        self.assertEqual(kwargs["contents"], [{"role": "user", "parts": [{"text": "Oi"}]}])
        self.assertTrue(kwargs["config"].system_instruction)
        self.assertEqual(kwargs["config"].max_output_tokens, MAX_OUTPUT_TOKENS)
        self.assertEqual(kwargs["config"].thinking_config.thinking_level, "MINIMAL")

    def test_converte_server_error_em_chat_model_unavailable(self) -> None:
        client = Mock()
        client.models.generate_content.side_effect = errors.ServerError(
            503, {"error": {"message": "sobrecarregado"}}
        )
        model = GeminiChatModel(client=client, model="gemini-3.5-flash-lite")

        with self.assertRaises(ChatModelUnavailableError):
            model.generate_reply("Oi")

    def test_converte_client_error_429_em_chat_model_unavailable(self) -> None:
        client = Mock()
        client.models.generate_content.side_effect = errors.ClientError(
            429, {"error": {"message": "limite de requisições excedido"}}
        )
        model = GeminiChatModel(client=client, model="gemini-3.5-flash-lite")

        with self.assertRaises(ChatModelUnavailableError):
            model.generate_reply("Oi")

    def test_repropaga_client_error_diferente_de_429(self) -> None:
        client = Mock()
        client.models.generate_content.side_effect = errors.ClientError(
            400, {"error": {"message": "requisição inválida"}}
        )
        model = GeminiChatModel(client=client, model="gemini-3.5-flash-lite")

        with self.assertRaises(errors.ClientError):
            model.generate_reply("Oi")

    def test_inclui_contexto_recuperado_quando_disponivel(self) -> None:
        client = Mock()
        client.models.generate_content.return_value = Mock(text="resposta com contexto")
        resultado = ResultadoBusca(
            texto="O SLA de resposta é de 24 horas.",
            score=0.9,
            projeto_id="az1",
            tipo_documento="gestao",
            secao="2.1.5",
            arquivo_origem="GestaoProjeto.md",
        )
        model = GeminiChatModel(
            client=client,
            model="gemini-3.5-flash-lite",
            buscar_contexto=lambda query: [resultado],
        )

        model.generate_reply("Qual é o SLA de resposta?")

        texto_enviado = client.models.generate_content.call_args.kwargs["contents"][0]["parts"][0]["text"]
        self.assertIn("O SLA de resposta é de 24 horas.", texto_enviado)
        self.assertIn("Qual é o SLA de resposta?", texto_enviado)

    def test_ignora_contexto_quando_busca_nao_retorna_resultados(self) -> None:
        client = Mock()
        client.models.generate_content.return_value = Mock(text="resposta")
        model = GeminiChatModel(
            client=client,
            model="gemini-3.5-flash-lite",
            buscar_contexto=lambda query: [],
        )

        model.generate_reply("Oi")

        kwargs = client.models.generate_content.call_args.kwargs
        self.assertEqual(kwargs["contents"], [{"role": "user", "parts": [{"text": "Oi"}]}])

    def test_responde_sem_contexto_quando_busca_falha(self) -> None:
        client = Mock()
        client.models.generate_content.return_value = Mock(text="resposta")

        def busca_com_falha(query: str) -> list[ResultadoBusca]:
            raise RuntimeError("SUPABASE_DB_URL não configurada.")

        model = GeminiChatModel(
            client=client,
            model="gemini-3.5-flash-lite",
            buscar_contexto=busca_com_falha,
        )

        reply = model.generate_reply("Oi")

        self.assertEqual(reply, "resposta")
        kwargs = client.models.generate_content.call_args.kwargs
        self.assertEqual(kwargs["contents"], [{"role": "user", "parts": [{"text": "Oi"}]}])

    def test_historico_guarda_mensagem_original_sem_contexto_recuperado(self) -> None:
        client = Mock()
        client.models.generate_content.return_value = Mock(text="resposta 1")
        resultado = ResultadoBusca(
            texto="Trecho recuperado.",
            score=0.8,
            projeto_id="az1",
            tipo_documento="gestao",
            secao="1",
            arquivo_origem="Projeto.md",
        )
        model = GeminiChatModel(
            client=client,
            model="gemini-3.5-flash-lite",
            buscar_contexto=lambda query: [resultado],
        )

        model.generate_reply("Primeira pergunta", conversation_id="c1")
        client.models.generate_content.return_value = Mock(text="resposta 2")
        model.generate_reply("Segunda pergunta", conversation_id="c1")

        primeiro_turno = client.models.generate_content.call_args.kwargs["contents"][0]
        self.assertEqual(primeiro_turno, {"role": "user", "parts": [{"text": "Primeira pergunta"}]})


if __name__ == "__main__":
    unittest.main()
