"""Suíte de contrato do servidor MCP (casos TI-43 a TI-49).

O que esta suíte protege são as quatro promessas que o conector do Copilot
Studio faz ao agente, e que nenhum teste existente cobria:

1. SEM CHAVE CONFIGURADA, NÃO HÁ SUPERFÍCIE. Quem sobe a API sem intenção de
   expor MCP não ganha um caminho novo por descuido.
2. COM CHAVE CONFIGURADA, CHAVE ERRADA NÃO ENTRA. É o único controle de acesso
   deste caminho, então ele é verificado antes de qualquer outra coisa.
3. A FERRAMENTA É UMA SÓ, E É A DE ALTO NÍVEL. Se alguém acrescentar ao
   catálogo uma ferramenta que devolve trecho cru, o recuo fundamentado deixa
   de governar a resposta sem que nada falhe. O caso TI-47 falha no lugar.
4. O RECUO ATRAVESSA. Uma recusa precisa chegar ao agente marcada como recusa,
   senão o orquestrador a trata como resposta ruim e tenta melhorá-la, que é
   exatamente o que o recuo existe para impedir.

As asserções dos três primeiros casos são em código HTTP porque é essa a
linguagem do conector: é o status que decide se o Power Platform considera a
*connection* válida.
"""

from __future__ import annotations

import os
import unittest
from unittest import mock

from fastapi.testclient import TestClient

from mcp_servidor import seguranca

CHAVE = "chave-de-teste-nao-usar-em-producao"


class AmbienteComChave(unittest.TestCase):
    """Base que mantém a variável de ambiente viva durante a requisição.

    Duas armadilhas justificam esta classe. A primeira: `az1_api.main` decide
    montar o `/mcp` no momento da importação, então recarregar o módulo é a
    única forma de exercitar os dois lados da condição no mesmo processo. A
    segunda: a guarda relê `AZ1_MCP_API_KEY` A CADA requisição, de propósito,
    para permitir rotação sem reiniciar. Se a variável só existisse durante o
    reload, a montagem aconteceria e a requisição receberia 503 em vez de 401,
    que foi exatamente o que esta suíte flagrou na primeira execução.
    """

    def construir_app(self, chaves: str | None):
        import importlib

        import az1_api.main

        ambiente = {"AZ1_AUTH_MODE": "disabled"}
        if chaves is not None:
            ambiente["AZ1_MCP_API_KEY"] = chaves
        self.enterContext(mock.patch.dict(os.environ, ambiente, clear=False))
        if chaves is None:
            self.enterContext(mock.patch.dict(os.environ, {}, clear=False))
            os.environ.pop("AZ1_MCP_API_KEY", None)
        return importlib.reload(az1_api.main).app


class ChaveDeApi(AmbienteComChave):
    """TI-43 a TI-46: a guarda, antes de qualquer semântica de protocolo."""

    def test_ti43_sem_chave_configurada_o_caminho_nao_existe(self) -> None:
        with TestClient(self.construir_app(None)) as cliente:
            self.assertEqual(cliente.post("/mcp", json={}).status_code, 404)

    def test_ti44_chave_ausente_no_cabecalho_e_recusada(self) -> None:
        with TestClient(self.construir_app(CHAVE)) as cliente:
            resposta = cliente.post("/mcp", json={})
        self.assertEqual(resposta.status_code, 401)
        self.assertEqual(resposta.json()["error"], "mcp_nao_autorizado")

    def test_ti45_chave_errada_e_recusada(self) -> None:
        with TestClient(self.construir_app(CHAVE)) as cliente:
            resposta = cliente.post("/mcp", json={}, headers={"x-api-key": "errada"})
        self.assertEqual(resposta.status_code, 401)

    def test_ti46b_caminho_sem_barra_nao_redireciona(self) -> None:
        """A URL documentada precisa funcionar exatamente como está escrita.

        Sem a normalização, o roteador responde `/mcp` com 307 para `/mcp/`, e
        a guarda só é alcançada depois do salto. Clientes que não preservam
        cabeçalho personalizado através de redirecionamento perderiam o
        `x-api-key` e receberiam 401 sem explicação possível. A asserção é pelo
        status NÃO ser 307: o redirecionamento é que não pode existir.
        """
        with TestClient(self.construir_app(CHAVE), follow_redirects=False) as cliente:
            resposta = cliente.post("/mcp", json={})
        self.assertEqual(resposta.status_code, 401)

    def test_ti46_chave_certa_passa_da_guarda(self) -> None:
        """Passar da guarda é o que se verifica, e não o protocolo.

        Um corpo vazio não é mensagem MCP válida, então o sub-aplicativo
        responderá com erro próprio. O que importa aqui é que o erro NÃO seja
        401: a requisição chegou ao MCP.
        """
        with TestClient(self.construir_app(CHAVE)) as cliente:
            resposta = cliente.post("/mcp", json={}, headers={"x-api-key": CHAVE})
        self.assertNotEqual(resposta.status_code, 401)


class RotacaoDeChave(unittest.TestCase):
    """A rotação sem janela de indisponibilidade, que é o motivo da lista."""

    def test_duas_chaves_simultaneas_sao_aceitas(self) -> None:
        with mock.patch.dict(os.environ, {seguranca.VARIAVEL: "antiga, nova"}):
            self.assertTrue(seguranca.chave_valida("antiga"))
            self.assertTrue(seguranca.chave_valida("nova"))
            self.assertFalse(seguranca.chave_valida("terceira"))

    def test_chave_vazia_ou_ausente_nunca_vale(self) -> None:
        with mock.patch.dict(os.environ, {seguranca.VARIAVEL: "   ,  "}):
            self.assertEqual(seguranca.chaves_aceitas(), ())
            self.assertFalse(seguranca.chave_valida(""))
            self.assertFalse(seguranca.chave_valida(None))


class CatalogoDeFerramentas(unittest.IsolatedAsyncioTestCase):
    """TI-47: o catálogo exposto ao agente."""

    async def test_ti47_expoe_apenas_a_ferramenta_de_alto_nivel(self) -> None:
        from mcp_servidor.servidor import mcp

        ferramentas = {f.name: f for f in await mcp._list_tools()}
        self.assertEqual(
            sorted(ferramentas),
            ["responder_consulta"],
            "Expor trecho cru ao orquestrador contorna o recuo fundamentado; "
            "ver o docstring de mcp_servidor/servidor.py antes de alterar.",
        )

    async def test_a_descricao_orienta_o_agente_a_nao_reescrever_recusa(self) -> None:
        """A descrição é o único canal de instrução para o orquestrador.

        Sem a menção ao `recuou`, o modelo do Copilot Studio trata a recusa
        como resposta insatisfatória e tenta completá-la por conta própria.
        """
        from mcp_servidor.servidor import mcp

        ferramentas = {f.name: f for f in await mcp._list_tools()}
        descricao = ferramentas["responder_consulta"].description or ""
        self.assertIn("recuou", descricao)


class RecuoAtravessaAFerramenta(unittest.TestCase):
    """TI-48 e TI-49: a recusa chega ao agente marcada como recusa."""

    def _chamar(self, resultado: str, fontes: list):
        from routes.chat import TurnoRespondido

        respondido = TurnoRespondido(
            texto="Não encontrei essa informação na base.",
            fontes=fontes,
            turno=None,
            resultado=resultado,
        )
        with (
            mock.patch("mcp_servidor.servidor.responder_turno", return_value=respondido),
            mock.patch("mcp_servidor.servidor.get_conversa_repository"),
            mock.patch("mcp_servidor.servidor.get_chat_answerer"),
            mock.patch("mcp_servidor.servidor.get_classificador_de_intencao"),
            mock.patch("mcp_servidor.servidor.get_agente"),
            mock.patch("mcp_servidor.servidor.identidade_de_servico"),
        ):
            from mcp_servidor.servidor import responder_consulta

            return responder_consulta(pergunta="E a Linha Laranja?", id_conversa="")

    def test_ti48_recusa_chega_marcada(self) -> None:
        self.assertTrue(self._chamar("recusada", []).recuou)

    def test_ti49_resposta_do_portfolio_sem_fontes_nao_e_lida_como_recuo(self) -> None:
        """O caso que a heurística ingênua erraria.

        Uma ação do portfólio responde com dado estruturado e não cita fonte.
        Deduzir recuo da lista de fontes vazia marcaria essa resposta como
        recusa, e o agente deixaria de apresentá-la.
        """
        self.assertFalse(self._chamar("sucesso", []).recuou)


if __name__ == "__main__":
    unittest.main()
