from __future__ import annotations

import hmac
import json
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from services.webhook_service import (
    VERSAO_ENVELOPE,
    EventoWebhook,
    RegistroConexoes,
    VerificadorAssinatura,
    WebhookError,
    WebhookErrorCode,
)

PROVEDOR = "microsoft_graph"

# O Graph aceita apenas estes três em `changeType`. Para o item raiz de um drive
# e para a lista do SharePoint, na prática só `updated` é emitido — os outros
# dois existem para as demais famílias de recurso.
TIPOS_CONHECIDOS = frozenset({"created", "updated", "deleted"})

# Os três disparam varredura, inclusive `deleted`: um documento removido na
# origem também precisa sair do índice, e é a varredura que descobre isso.
TIPOS_PROCESSAVEIS = frozenset(f"graph.{tipo}" for tipo in TIPOS_CONHECIDOS)


def _carregar_notificacoes(corpo: bytes) -> list[Any]:
    """Extrai a coleção `value` do corpo, ou recusa a entrega.

    Os três colaboradores do provedor — os dois verificadores e o tradutor —
    precisam da mesma leitura, e cada um falharia de um jeito diferente se
    fizesse a sua. Centralizar aqui garante que "corpo ilegível" signifique a
    mesma coisa nos três.
    """
    try:
        bruto: Any = json.loads(corpo)
        notificacoes = bruto["value"]
    except (json.JSONDecodeError, KeyError, TypeError) as exc:
        raise WebhookError(WebhookErrorCode.CONTEUDO_MALFORMADO) from exc

    if not isinstance(notificacoes, list) or not notificacoes:
        raise WebhookError(WebhookErrorCode.CONTEUDO_MALFORMADO)

    return notificacoes


@dataclass(frozen=True)
class TradutorGraph:
    """Converte o corpo do Microsoft Graph em envelopes canônicos.

    É o único ponto do sistema que conhece o formato do provedor. Observar o
    OneDrive de desenvolvimento ou a biblioteca de documentos do SharePoint do
    parceiro produz exatamente o mesmo envelope: os dois são `driveItem`, e a
    diferença entre eles está no `resource` assinado, não no que chega aqui.

    O Graph agrupa várias mudanças numa entrega só quando elas acontecem
    próximas, por isso o retorno é uma sequência.
    """

    def traduzir(self, *, cabecalhos: Mapping[str, str], corpo: bytes) -> Sequence[EventoWebhook]:
        return [self._converter(n) for n in _carregar_notificacoes(corpo)]

    def _converter(self, notificacao: Any) -> EventoWebhook:
        try:
            subscription_id = notificacao["subscriptionId"]
            change_type = notificacao["changeType"]
            recurso = notificacao["resource"]
        except (KeyError, TypeError) as exc:
            raise WebhookError(WebhookErrorCode.CONTEUDO_MALFORMADO) from exc

        dados = notificacao.get("resourceData") or {}
        identificador = notificacao.get("id") or self._identificador_de_fallback(dados)
        if not identificador:
            # Sem identificador não há como garantir efeito único (TI-37), e
            # processar mesmo assim arriscaria aplicar o efeito duas vezes.
            raise WebhookError(WebhookErrorCode.CONTEUDO_MALFORMADO)

        return EventoWebhook(
            identificador=f"{subscription_id}:{identificador}",
            tipo=f"graph.{change_type}",
            versao=VERSAO_ENVELOPE,
            marca_de_tempo=datetime.now(UTC),
            correlacao=subscription_id,
            conteudo={
                "provedor": PROVEDOR,
                "subscription_id": subscription_id,
                "change_type": change_type,
                "resource": recurso,
                "resource_data": dados,
                "tenant_id": notificacao.get("tenantId"),
            },
        )

    def _identificador_de_fallback(self, dados: Mapping[str, Any]) -> str | None:
        """Usado quando a notificação não traz `id` — campo documentado como
        opcional pelo Graph (`changeNotification.id`).

        `resourceData.id` sozinho identifica o *item*, não a *entrega*: duas
        edições sucessivas do mesmo arquivo compartilham o mesmo `resourceData.id`,
        e usá-lo isolado como chave de idempotência faria a segunda edição parecer
        reentrega da primeira e ser descartada sem processar — perda silenciosa,
        não falha visível. O `@odata.etag` muda a cada edição do item, então
        compô-lo à chave distingue as duas. Se também faltar, ainda não há como
        diferenciar — limitação do que o provedor envia, não deste código.
        """
        item_id = dados.get("id")
        if not item_id:
            return None

        etag = dados.get("@odata.etag")
        return f"{item_id}:{etag}" if etag else item_id


@dataclass(frozen=True)
class VerificadorClientState:
    """Confere o segredo compartilhado que o Graph devolve em cada notificação.

    O `clientState` é definido pela aplicação ao criar a assinatura e devolvido
    pelo provedor em toda entrega. É a verificação de base que a documentação do
    Graph prescreve para notificações básicas, e sozinha ela cobre duas das três
    causas do caso TI-36: ausência e divergência.

    A terceira causa — entrega legítima porém antiga, reapresentada por quem a
    capturou — o `clientState` não cobre, porque ele é constante ao longo da vida
    da assinatura. Para ela é preciso `VerificadorAssinaturaAtiva`, e por isso
    este verificador é composto, e não usado sozinho: ver `VerificadorEmCadeia`.
    """

    esperado: str

    def verificar(self, *, cabecalhos: Mapping[str, str], corpo: bytes) -> None:
        recebidos = [n.get("clientState") for n in _carregar_notificacoes(corpo)]

        if any(valor is None for valor in recebidos):
            raise WebhookError(WebhookErrorCode.ASSINATURA_AUSENTE)

        for valor in recebidos:
            if not hmac.compare_digest(valor, self.esperado):
                raise WebhookError(WebhookErrorCode.ASSINATURA_INVALIDA)


def _agora() -> datetime:
    return datetime.now(UTC)


@dataclass(frozen=True)
class VerificadorAssinaturaAtiva:
    """Recusa entregas de assinaturas que já não valem mais.

    Esta é a resposta do projeto à terceira causa do caso TI-36. O Graph não
    assina a notificação nem carimba a hora dela, então não existe prova de
    frescor por entrega — a limitação está documentada na Seção 5.1.5. O que ele
    fornece são dois sinais aproveitáveis, e este verificador usa os dois:

    1. o `subscriptionId`, que confrontamos com as origens ativas em
       `integracao.conexao`: uma assinatura removida ou desativada deixa de ser
       aceita imediatamente;
    2. o `subscriptionExpirationDateTime` do próprio corpo, que recusa a entrega
       cuja assinatura já venceu.

    Não é frescor por entrega, e o texto da documentação diz isso com todas as
    letras. Dentro da janela de validade, quem impede o efeito repetido é a
    idempotência do caso TI-37, não este verificador.
    """

    conexoes: RegistroConexoes
    agora: Callable[[], datetime] = field(default=_agora)

    def verificar(self, *, cabecalhos: Mapping[str, str], corpo: bytes) -> None:
        instante = self.agora()

        for notificacao in _carregar_notificacoes(corpo):
            subscription_id = notificacao.get("subscriptionId") if isinstance(notificacao, dict) else None
            if not subscription_id:
                # Sem `subscriptionId` não há o que confrontar. Deixamos passar de
                # propósito para o tradutor recusar com 400 (TI-39): a entrega é
                # inválida por estrutura, não por autenticidade, e responder 401
                # aqui esconderia a causa real de quem estiver depurando.
                continue

            if not self.conexoes.assinatura_ativa(subscription_id):
                raise WebhookError(WebhookErrorCode.ASSINATURA_EXPIRADA)

            expira_em = notificacao.get("subscriptionExpirationDateTime")
            if expira_em and self._vencida(expira_em, instante):
                raise WebhookError(WebhookErrorCode.ASSINATURA_EXPIRADA)

    def _vencida(self, expira_em: str, instante: datetime) -> bool:
        try:
            return datetime.fromisoformat(expira_em) < instante
        except (TypeError, ValueError) as exc:
            raise WebhookError(WebhookErrorCode.CONTEUDO_MALFORMADO) from exc


@dataclass(frozen=True)
class VerificadorEmCadeia:
    """Aplica vários verificadores em ordem, parando no primeiro que recusar.

    Existe para que a autenticidade do Graph seja montada explicitamente a partir
    das duas peças que ela exige — segredo compartilhado e assinatura viva — em
    vez de um verificador único que pareça completo cobrindo só metade.
    """

    verificadores: tuple[VerificadorAssinatura, ...]

    def verificar(self, *, cabecalhos: Mapping[str, str], corpo: bytes) -> None:
        if not self.verificadores:
            raise ValueError("VerificadorEmCadeia exige ao menos um verificador.")
        for verificador in self.verificadores:
            verificador.verificar(cabecalhos=cabecalhos, corpo=corpo)
