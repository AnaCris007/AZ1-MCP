# Leitura da trilha e registro de feedback.
#
# As duas coisas fecham laços que estavam abertos: a trilha era escrita e nunca
# lida, e `auditoria.avaliacao` tinha policies, colunas e zero linhas.
#
# O teste que mais importa aqui é o de ISOLAMENTO: enquanto a RLS não estiver em
# vigor — a aplicação conecta como dono do schema —, quem impede alguém de ler a
# conversa de outra pessoa é o `WHERE usuario_id` do SQL. Se ele cair, nada
# falha; só passa a vazar.

from __future__ import annotations

import dataclasses
import unittest

from fastapi.testclient import TestClient

from az1_api.dependencies import get_conversa_repository, require_authenticated_user
from az1_api.main import app
from services.auth_service import AuthenticatedUser
from services.conversa_repository import (
    ConversaNaoGravada,
    ConversaResumida,
    MensagemRegistrada,
)

_USUARIO = AuthenticatedUser(
    subject="s", email="e@x", name="n", provider="azure", domain_user_id=7
)
_UUID = "3f1c0c4e-0000-4000-8000-000000000001"


class _RepositorioFalso:
    def __init__(self, conversas=(), mensagens=(), avaliacao=True):
        self._conversas = tuple(conversas)
        self._mensagens = tuple(mensagens)
        self._avaliacao = avaliacao
        self.pedidos: list[tuple] = []
        self.avaliacoes: list[dict] = []

    def listar_conversas(self, usuario_id: int, limite: int = 50):
        self.pedidos.append(("listar", usuario_id))
        return self._conversas

    def mensagens_da_conversa(self, conversa_id: str, usuario_id: int):
        self.pedidos.append(("mensagens", conversa_id, usuario_id))
        return self._mensagens

    def registrar_avaliacao(self, **kwargs):
        self.avaliacoes.append(kwargs)
        if isinstance(self._avaliacao, Exception):
            raise self._avaliacao
        return self._avaliacao


class _Base(unittest.TestCase):
    def setUp(self):
        self.repositorio = _RepositorioFalso()
        app.dependency_overrides[require_authenticated_user] = lambda: _USUARIO
        app.dependency_overrides[get_conversa_repository] = lambda: self.repositorio
        self.client = TestClient(app, raise_server_exceptions=False)
        self.addCleanup(app.dependency_overrides.clear)

    def _com(self, repositorio):
        self.repositorio = repositorio
        app.dependency_overrides[get_conversa_repository] = lambda: repositorio


class TesteListagemDeConversas(_Base):
    def test_devolve_as_conversas_da_pessoa(self):
        self._com(
            _RepositorioFalso(
                conversas=[ConversaResumida(id=_UUID, titulo="Riscos", atualizada_em="2026-09-12T10:00:00")]
            )
        )
        corpo = self.client.get("/api/v1/conversas").json()

        self.assertEqual(len(corpo["conversas"]), 1)
        self.assertEqual(corpo["conversas"][0]["titulo"], "Riscos")

    def test_o_usuario_autenticado_e_quem_filtra(self):
        # Se o id parar de chegar ao repositório, a listagem passa a devolver as
        # conversas de todo mundo — e nada falha.
        self.client.get("/api/v1/conversas")
        self.assertEqual(self.repositorio.pedidos, [("listar", 7)])

    def test_sem_identidade_e_422(self):
        # Acontece com AZ1_AUTH_MODE=disabled. Devolver a lista de outra pessoa,
        # ou todas, seria pior do que recusar.
        sem_id = dataclasses.replace(_USUARIO, domain_user_id=None)
        app.dependency_overrides[require_authenticated_user] = lambda: sem_id
        self.assertEqual(self.client.get("/api/v1/conversas").status_code, 422)


class TesteMensagensDaConversa(_Base):
    def test_devolve_os_turnos_em_ordem(self):
        self._com(
            _RepositorioFalso(
                mensagens=[
                    MensagemRegistrada(ordem=1, papel="usuario", conteudo="pergunta"),
                    MensagemRegistrada(ordem=2, papel="agente", conteudo="resposta"),
                ]
            )
        )
        corpo = self.client.get(f"/api/v1/conversas/{_UUID}/mensagens").json()

        self.assertEqual([m["ordem"] for m in corpo["mensagens"]], [1, 2])
        self.assertEqual([m["papel"] for m in corpo["mensagens"]], ["usuario", "agente"])

    def test_o_dono_entra_na_consulta(self):
        self._com(_RepositorioFalso(mensagens=[MensagemRegistrada(1, "usuario", "x")]))
        self.client.get(f"/api/v1/conversas/{_UUID}/mensagens")
        self.assertEqual(self.repositorio.pedidos, [("mensagens", _UUID, 7)])

    def test_conversa_de_outra_pessoa_e_inexistente_dao_a_mesma_resposta(self):
        # Distinguir as duas diria a quem tentou que o UUID existe e é de outro
        # alguém.
        resposta = self.client.get(f"/api/v1/conversas/{_UUID}/mensagens")
        self.assertEqual(resposta.status_code, 404)

    def test_identificador_que_nao_e_uuid_e_422(self):
        self.assertEqual(
            self.client.get("/api/v1/conversas/conv_123/mensagens").status_code, 422
        )


class TesteAvaliacao(_Base):
    def _avaliar(self, **extra):
        corpo = {"conversa_id": _UUID, "ordem": 2, "polaridade": "positiva"}
        corpo.update(extra)
        return self.client.post("/api/v1/conversas/avaliacoes", json=corpo)

    def test_registra_o_polegar(self):
        self.assertEqual(self._avaliar().status_code, 201)
        registrada = self.repositorio.avaliacoes[0]
        self.assertEqual(registrada["usuario_id"], 7)
        self.assertEqual(registrada["ordem"], 2)
        self.assertEqual(registrada["polaridade"], "positiva")

    def test_mensagem_inexistente_e_404(self):
        self._com(_RepositorioFalso(avaliacao=False))
        self.assertEqual(self._avaliar().status_code, 404)

    def test_polaridade_fora_do_dominio_e_422(self):
        self._com(_RepositorioFalso(avaliacao=ConversaNaoGravada("polaridade inválida")))
        self.assertEqual(self._avaliar(polaridade="talvez").status_code, 422)

    def test_conversa_invalida_nao_chega_ao_repositorio(self):
        resposta = self._avaliar(conversa_id="conv_123")
        self.assertEqual(resposta.status_code, 422)
        self.assertEqual(self.repositorio.avaliacoes, [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
