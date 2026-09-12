from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from fastapi import APIRouter, Depends, Request, Response

from az1_api.dependencies import (
    get_drive_webhook_receiver_provider,
    get_webhook_receiver_provider,
)
from schemas.webhook import WebhookAceite, WebhookErrorCode
from services.webhook_service import (
    STATUS_ACEITE,
    STATUS_POR_ERRO,
    ReceberEventoWebhook,
    ResultadoRecepcao,
    SituacaoEvento,
    WebhookError,
)
from services.webhook_service import (
    WebhookErrorCode as ServiceWebhookErrorCode,
)

router = APIRouter(tags=["webhooks"])


class WebhookAPIError(Exception):
    def __init__(self, status_code: int, error: WebhookErrorCode, message: str) -> None:
        self.status_code = status_code
        self.error = error
        self.message = message


@dataclass(frozen=True)
class _HTTPErrorDetails:
    error: WebhookErrorCode
    message: str


# O código de status vem de STATUS_POR_ERRO, no serviço, porque num webhook ele
# é parte do contrato com o provedor e não da apresentação. Aqui ficam apenas o
# rótulo e a mensagem devolvidos no corpo. As mensagens são deliberadamente
# genéricas quanto ao provedor: as duas rotas compartilham este mapa, e o que
# muda entre elas é o nome do campo, não a causa.
_ERROR_DETAILS = {
    ServiceWebhookErrorCode.ASSINATURA_AUSENTE: _HTTPErrorDetails(
        "unauthorized",
        "Notificação sem o segredo compartilhado da assinatura.",
    ),
    ServiceWebhookErrorCode.ASSINATURA_INVALIDA: _HTTPErrorDetails(
        "unauthorized",
        "Segredo compartilhado divergente do registrado para a assinatura.",
    ),
    ServiceWebhookErrorCode.ASSINATURA_EXPIRADA: _HTTPErrorDetails(
        "unauthorized",
        "Assinatura desconhecida, desativada ou expirada.",
    ),
    ServiceWebhookErrorCode.CONTEUDO_MALFORMADO: _HTTPErrorDetails(
        "malformed_payload",
        "Notificação malformada ou com campo obrigatório ausente.",
    ),
    ServiceWebhookErrorCode.FALHA_DE_PERSISTENCIA: _HTTPErrorDetails(
        "processing_unavailable",
        "Não foi possível registrar a notificação. Reenvie.",
    ),
    ServiceWebhookErrorCode.FALHA_DE_PROCESSAMENTO: _HTTPErrorDetails(
        "processing_unavailable",
        "Não foi possível processar a notificação. Reenvie.",
    ),
}


def _erro_de_api(exc: WebhookError) -> WebhookAPIError:
    details = _ERROR_DETAILS[exc.code]
    return WebhookAPIError(STATUS_POR_ERRO[exc.code], details.error, details.message)


def _aceite(resultado: ResultadoRecepcao) -> Response:
    """Monta a confirmação devolvida ao provedor.

    O corpo traz a contagem por situação, e não uma situação única, porque uma
    entrega pode carregar várias mudanças com desfechos diferentes. Para o
    provedor tudo isso é 202; a distinção serve a quem for depurar a integração
    ou auditar o que entrou.
    """
    return Response(
        content=WebhookAceite(
            eventos=len(resultado.resultados),
            processados=resultado.contar(SituacaoEvento.PROCESSADO),
            ignorados=resultado.contar(SituacaoEvento.IGNORADO),
            duplicados=resultado.contar(SituacaoEvento.DUPLICADO),
        ).model_dump_json(),
        media_type="application/json",
        status_code=STATUS_ACEITE,
    )


@router.post("/webhooks/microsoft")
async def receber_notificacao_microsoft(
    request: Request,
    validationToken: str | None = None,  # noqa: N803 — o nome vem do provedor
    provedor_do_receptor: Callable[[], ReceberEventoWebhook] = Depends(get_webhook_receiver_provider),
) -> Response:
    """Recebe as notificações de mudança do Microsoft Graph.

    A rota atende dois modos no mesmo endereço, porque é o mesmo que o provedor
    usa. Ao criar a assinatura, o Graph chama esta URL com `?validationToken=` e
    exige o token de volta em texto puro, com 200, em até dez segundos; se isso
    falhar, a assinatura nem chega a ser criada. Fora desse momento, a chamada é
    uma notificação de mudança.
    """
    # Modo handshake. Devolver JSON aqui, ou devolver o token escapado, faz a
    # criação da assinatura falhar sem mensagem de erro útil do lado do Graph.
    # A dependência entrega uma fábrica, e não o receptor pronto, porque o
    # FastAPI resolve `Depends` antes de entrar no handler: se o receptor fosse
    # construído aqui, uma instalação ainda sem configuração completa faria o
    # handshake responder 500, e a assinatura no Graph nunca chegaria a existir.
    if validationToken is not None:
        return Response(content=validationToken, media_type="text/plain", status_code=200)

    receptor = provedor_do_receptor()
    corpo = await request.body()

    try:
        resultado = receptor.receber(cabecalhos=dict(request.headers), corpo=corpo)
    except WebhookError as exc:
        raise _erro_de_api(exc) from exc

    return _aceite(resultado)


@router.post("/webhooks/google")
async def receber_notificacao_google(
    request: Request,
    provedor_do_receptor: Callable[[], ReceberEventoWebhook] = Depends(get_drive_webhook_receiver_provider),
) -> Response:
    """Recebe as notificações de mudança do Google Drive.

    Não há handshake aqui: em vez de validar a URL antes de abrir o canal, o
    Drive abre o canal e manda como primeira entrega uma notificação de estado
    `sync`, que o receptor registra e ignora. Por isso esta rota tem um modo só,
    enquanto a do Graph tem dois.

    A informação vem toda em cabeçalhos `X-Goog-*`; o corpo chega vazio. Ele é
    lido e repassado assim mesmo, porque o serviço é o mesmo para os dois
    provedores e é o tradutor de cada um que decide onde olhar.
    """
    receptor = provedor_do_receptor()
    corpo = await request.body()

    try:
        resultado = receptor.receber(cabecalhos=dict(request.headers), corpo=corpo)
    except WebhookError as exc:
        raise _erro_de_api(exc) from exc

    return _aceite(resultado)
