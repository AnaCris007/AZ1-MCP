from typing import Literal

from pydantic import BaseModel, Field

WebhookErrorCode = Literal[
    "bad_request",
    "unauthorized",
    "malformed_payload",
    "processing_unavailable",
    "internal_error",
]


class ResourceData(BaseModel):
    """Identificação do recurso que mudou.

    O Graph não diz *o que* mudou no item, apenas qual item mudou — descobrir a
    mudança exige uma chamada `delta` posterior. Por isso só o identificador e a
    etag interessam aqui.
    """

    id: str | None = None
    odata_type: str | None = Field(default=None, alias="@odata.type")
    odata_id: str | None = Field(default=None, alias="@odata.id")
    odata_etag: str | None = Field(default=None, alias="@odata.etag")

    model_config = {"populate_by_name": True, "extra": "allow"}


class ChangeNotification(BaseModel):
    """Uma notificação isolada dentro da coleção enviada pelo provedor."""

    subscription_id: str = Field(alias="subscriptionId")
    change_type: str = Field(alias="changeType")
    resource: str
    client_state: str | None = Field(default=None, alias="clientState")
    subscription_expiration_date_time: str | None = Field(default=None, alias="subscriptionExpirationDateTime")
    tenant_id: str | None = Field(default=None, alias="tenantId")
    resource_data: ResourceData | None = Field(default=None, alias="resourceData")
    id: str | None = None

    model_config = {"populate_by_name": True, "extra": "allow"}


class ChangeNotificationCollection(BaseModel):
    """Corpo do POST do Microsoft Graph.

    O provedor agrupa várias mudanças numa entrega só quando elas acontecem
    próximas, por isso `value` é lista e não objeto.
    """

    value: list[ChangeNotification]
    validation_tokens: list[str] | None = Field(default=None, alias="validationTokens")

    model_config = {"populate_by_name": True, "extra": "allow"}


class WebhookAceite(BaseModel):
    """Resposta devolvida ao provedor quando a entrega é aceita.

    Traz a contagem por situação porque uma entrega pode carregar várias
    mudanças com desfechos diferentes: parte processada, parte já conhecida de
    uma reentrega anterior, parte fora do catálogo. `eventos` é o total, e a
    soma das outras três bate com ele.
    """

    eventos: int
    processados: int
    ignorados: int
    duplicados: int
