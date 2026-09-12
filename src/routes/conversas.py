# Leitura da trilha de conversas.
#
# A trilha era escrita e nunca lida. O histórico da barra lateral vivia em
# `useState` no frontend: recarregar a página o apagava, embora as conversas
# estivessem no banco com título, autor e fontes. Estas duas rotas fecham esse
# laço.
#
# O filtro por usuário está no SQL, e não aqui: enquanto a RLS não estiver em
# vigor — a aplicação conecta como dono do schema —, é o `WHERE usuario_id` que
# impede alguém de ler a conversa de outra pessoa informando o UUID dela.

from __future__ import annotations

from fastapi import APIRouter, Depends

from az1_api.dependencies import get_conversa_repository, require_authenticated_user
from schemas.conversa import (
    AvaliacaoRequest,
    ConversaResumoResponse,
    ConversasResponse,
    MensagemResponse,
    MensagensResponse,
)
from services.auth_service import AuthenticatedUser
from services.conversa_repository import (
    ConversaNaoGravada,
    ConversaRepository,
    PersistenciaDesligada,
    conversa_uuid,
)

router = APIRouter(tags=["conversas"])


class ConversaAPIError(Exception):
    def __init__(self, status_code: int, error: str, message: str) -> None:
        self.status_code = status_code
        self.error = error
        self.message = message


def _identidade(usuario: AuthenticatedUser) -> int:
    """O id de domínio, ou 422 se ele não existe.

    É None com `AZ1_AUTH_MODE=disabled` e quando `ResolveOrCreateUsuario`
    falhou. Sem identidade não há "minhas conversas" — e devolver a lista de
    outra pessoa, ou todas, seria pior do que recusar.
    """
    if usuario.domain_user_id is None:
        raise ConversaAPIError(
            422,
            "sem_identidade",
            "A sessão não está ligada a um usuário do portfólio.",
        )
    return usuario.domain_user_id


@router.get("/conversas", response_model=ConversasResponse)
def listar_conversas(
    repositorio: ConversaRepository | PersistenciaDesligada = Depends(get_conversa_repository),
    usuario: AuthenticatedUser = Depends(require_authenticated_user),
):
    conversas = repositorio.listar_conversas(_identidade(usuario))
    return ConversasResponse(
        conversas=[
            ConversaResumoResponse(
                id=c.id, titulo=c.titulo, atualizada_em=c.atualizada_em
            )
            for c in conversas
        ]
    )


@router.get("/conversas/{conversa_id}/mensagens", response_model=MensagensResponse)
def listar_mensagens(
    conversa_id: str,
    repositorio: ConversaRepository | PersistenciaDesligada = Depends(get_conversa_repository),
    usuario: AuthenticatedUser = Depends(require_authenticated_user),
):
    identificador = conversa_uuid(conversa_id)
    if identificador is None:
        raise ConversaAPIError(
            422, "conversa_invalida", "O identificador da conversa não é um UUID."
        )

    mensagens = repositorio.mensagens_da_conversa(identificador, _identidade(usuario))
    if not mensagens:
        # Conversa inexistente e conversa de outra pessoa devolvem a MESMA
        # resposta, de propósito: distinguir as duas diria a quem tentou que o
        # UUID existe e é de outro alguém.
        raise ConversaAPIError(
            404, "conversa_nao_encontrada", "Conversa não encontrada."
        )

    return MensagensResponse(
        mensagens=[
            MensagemResponse(ordem=m.ordem, papel=m.papel, conteudo=m.conteudo)
            for m in mensagens
        ]
    )


@router.post("/conversas/avaliacoes", status_code=201)
def avaliar_resposta(
    payload: AvaliacaoRequest,
    repositorio: ConversaRepository | PersistenciaDesligada = Depends(get_conversa_repository),
    usuario: AuthenticatedUser = Depends(require_authenticated_user),
):
    """Registra polegar para cima ou para baixo numa resposta.

    Sem isto, `auditoria.avaliacao` ficava vazia e não havia sinal nenhum para
    melhorar o modelo — a tabela estava modelada, com policies e colunas, e nada
    escrevia nela.
    """
    identificador = conversa_uuid(payload.conversa_id)
    if identificador is None:
        raise ConversaAPIError(
            422, "conversa_invalida", "O identificador da conversa não é um UUID."
        )

    try:
        registrada = repositorio.registrar_avaliacao(
            usuario_id=_identidade(usuario),
            conversa_id=identificador,
            ordem=payload.ordem,
            polaridade=payload.polaridade,
            motivo=payload.motivo,
            comentario=payload.comentario,
        )
    except ConversaNaoGravada as erro:
        raise ConversaAPIError(422, "avaliacao_invalida", str(erro)) from erro

    if not registrada:
        raise ConversaAPIError(
            404, "mensagem_nao_encontrada", "Mensagem não encontrada nesta conversa."
        )
    return {"status": "registrada"}
