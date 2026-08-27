from __future__ import annotations

import unittest
from unittest.mock import Mock

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
        self.assertEqual(kwargs["contents"], "Oi")
        self.assertTrue(kwargs["config"].system_instruction)
        self.assertEqual(kwargs["config"].max_output_tokens, MAX_OUTPUT_TOKENS)
        self.assertEqual(kwargs["config"].thinking_config.thinking_level, "MINIMAL")


if __name__ == "__main__":
    unittest.main()
