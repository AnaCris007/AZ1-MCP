from __future__ import annotations

import unittest
from unittest.mock import Mock

from google.genai import errors

from rag.retriever import ResultadoBusca
from services.chat_service import ChatModelUnavailableError
from services.gemini_service import (
    MAX_OUTPUT_TOKENS,
    MENSAGEM_BASE_INDISPONIVEL,
    MENSAGEM_SEM_FUNDAMENTO,
    SCORE_MINIMO_CONTEXTO,
    GeminiChatModel,
)


# O buscador passou a receber filtros e a devolver (trechos, focou) — o
# segundo elemento é o que torna "a sugestão da classificação valeu"
# observável. Os dublês daqui não exercitam o foco; devolvem sempre o mesmo e
# declaram `focou=False`, que é o que a busca ampla faz.
def _busca_fixa(resultados):
    def buscar(query, *, tipo_documento=None, projeto_codigo=None, score_minimo=0.0):
        return resultados, False

    return buscar


class TestGeminiChatModel(unittest.TestCase):
    def test_gera_resposta_com_contrato_esperado(self) -> None:
        client = Mock()
        client.models.generate_content.return_value = Mock(text="resposta do modelo")
        model = GeminiChatModel(client=client, model="gemini-3.5-flash-lite")

        reply = model.generate_reply("Oi")

        self.assertEqual(reply.texto, "resposta do modelo")
        self.assertEqual(reply.fontes, ())
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
            buscar_contexto=_busca_fixa([resultado]),
        )

        model.generate_reply("Qual é o SLA de resposta?")

        texto_enviado = client.models.generate_content.call_args.kwargs["contents"][0]["parts"][0]["text"]
        self.assertIn("O SLA de resposta é de 24 horas.", texto_enviado)
        self.assertIn("Qual é o SLA de resposta?", texto_enviado)

    def test_sem_trecho_relevante_devolve_mensagem_padrao_sem_chamar_o_modelo(self) -> None:
        # ANTES este teste fixava o oposto: sem resultado, a pergunta crua ia
        # para o Gemini e ele respondia do proprio conhecimento. Num agente de
        # PMO isso produz percentual e data com a forma certa e sem lastro --
        # que foi o que aconteceu enquanto a colecao vetorial esteve com
        # dimensao incompativel.
        #
        # A recusa e deterministica de proposito: nao chamar o modelo e a unica
        # forma de garantir que ela aconteca 100% das vezes.
        client = Mock()
        model = GeminiChatModel(
            client=client,
            model="gemini-3.5-flash-lite",
            buscar_contexto=_busca_fixa([]),
        )

        reply = model.generate_reply("Qual o avanco do SYN-04?")

        self.assertEqual(reply.texto, MENSAGEM_SEM_FUNDAMENTO)
        self.assertEqual(reply.fontes, ())
        client.models.generate_content.assert_not_called()

    def test_trecho_abaixo_do_score_minimo_nao_conta_como_fundamento(self) -> None:
        # A busca vetorial sempre devolve os k mais proximos, mesmo para uma
        # pergunta fora do assunto. Sem um piso de similaridade, qualquer coisa
        # "tem fonte" e a citacao vira teatro.
        client = Mock()
        irrelevante = ResultadoBusca(
            texto="Trecho qualquer.",
            score=SCORE_MINIMO_CONTEXTO - 0.01,
            projeto_id="az1",
            tipo_documento="gestao",
            secao="1",
            arquivo_origem="Projeto.md",
        )
        model = GeminiChatModel(
            client=client,
            model="gemini-3.5-flash-lite",
            buscar_contexto=_busca_fixa([irrelevante]),
        )

        reply = model.generate_reply("Pergunta fora do assunto")

        self.assertEqual(reply.texto, MENSAGEM_SEM_FUNDAMENTO)
        client.models.generate_content.assert_not_called()

    def test_busca_indisponivel_e_dita_e_nao_disfarcada(self) -> None:
        client = Mock()
        client.models.generate_content.return_value = Mock(text="resposta")

        def busca_com_falha(query: str, **_) -> list[ResultadoBusca]:
            raise RuntimeError("SUPABASE_DB_URL não configurada.")

        model = GeminiChatModel(
            client=client,
            model="gemini-3.5-flash-lite",
            buscar_contexto=busca_com_falha,
        )

        reply = model.generate_reply("Oi")

        # Indisponibilidade da base agora e DITA, nao disfarcada de resposta.
        # Responder sem contexto quando a busca falha foi o que manteve uma
        # incompatibilidade de esquema invisivel por semanas.
        self.assertEqual(reply.texto, MENSAGEM_BASE_INDISPONIVEL)
        self.assertEqual(reply.fontes, ())
        client.models.generate_content.assert_not_called()

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
            buscar_contexto=_busca_fixa([resultado]),
        )

        model.generate_reply("Primeira pergunta", conversation_id="c1")
        client.models.generate_content.return_value = Mock(text="resposta 2")
        model.generate_reply("Segunda pergunta", conversation_id="c1")

        primeiro_turno = client.models.generate_content.call_args.kwargs["contents"][0]
        self.assertEqual(primeiro_turno, {"role": "user", "parts": [{"text": "Primeira pergunta"}]})


if __name__ == "__main__":
    unittest.main()
