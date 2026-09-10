from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from enum import Enum, auto
from typing import Any, Protocol

# Versão do envelope canônico. Vai gravada em cada evento para que um consumidor
# da Sprint 5 saiba interpretar mensagens produzidas por uma versão anterior do
# receptor sem precisar inspecionar o provedor de origem.
VERSAO_ENVELOPE = "1"


class WebhookErrorCode(Enum):
    ASSINATURA_AUSENTE = auto()
    ASSINATURA_INVALIDA = auto()
    ASSINATURA_EXPIRADA = auto()
    CONTEUDO_MALFORMADO = auto()
    FALHA_DE_PERSISTENCIA = auto()
    FALHA_DE_PROCESSAMENTO = auto()


class WebhookError(Exception):
    def __init__(self, code: WebhookErrorCode) -> None:
        self.code = code
        super().__init__(code.name)


@dataclass(frozen=True)
class EventoWebhook:
    """Envelope canônico de um evento recebido de um provedor externo.

    Os seis campos são os mesmos que a Seção 6.4 especifica para o envelope do
    barramento de mensagens da Sprint 5. A coincidência é deliberada: o receptor
    do webhook é o produtor daquele barramento, e publicar passa a ser repassar
    este objeto, sem tradução intermediária.
    """

    identificador: str
    tipo: str
    versao: str
    marca_de_tempo: datetime
    correlacao: str
    conteudo: Mapping[str, Any]


class SituacaoEvento(Enum):
    PROCESSADO = auto()
    IGNORADO = auto()
    DUPLICADO = auto()


@dataclass(frozen=True)
class ResultadoEvento:
    situacao: SituacaoEvento
    evento: EventoWebhook


@dataclass(frozen=True)
class ResultadoRecepcao:
    """Desfecho de uma entrega, que pode conter mais de um evento.

    É uma coleção, e não um evento só, porque o provedor agrupa mudanças
    próximas numa entrega única. Tratar o lote como se fosse um evento faria o
    receptor confirmar a entrega inteira tendo processado apenas a primeira
    notificação, e as demais se perderiam sem reentrega.
    """

    resultados: tuple[ResultadoEvento, ...]

    def contar(self, situacao: SituacaoEvento) -> int:
        return sum(1 for resultado in self.resultados if resultado.situacao is situacao)


class VerificadorAssinatura(Protocol):
    """Porta de autenticidade. Levanta WebhookError quando a entrega não é legítima.

    As três causas do caso TI-36 são códigos distintos porque têm origens
    distintas: segredo ausente, segredo divergente e assinatura que já não vale
    mais. A rota traduz as três para 401.
    """

    def verificar(self, *, cabecalhos: Mapping[str, str], corpo: bytes) -> None: ...


class TradutorDeEvento(Protocol):
    """Porta do provedor. Converte a entrega crua em envelopes canônicos.

    É o único ponto que conhece o formato do provedor. Trocar Microsoft Graph
    por Power Automate, ou o `resource` do OneDrive pela biblioteca do
    SharePoint, é trocar a implementação desta porta.

    Devolve uma sequência, e não um evento: uma entrega pode carregar várias
    mudanças, e quem recebe não tem como saber quantas antes de traduzir.
    """

    def traduzir(self, *, cabecalhos: Mapping[str, str], corpo: bytes) -> Sequence[EventoWebhook]: ...


class ReivindicacaoDeEvento(Protocol):
    """Exclusividade de processamento sobre um evento, devolvida por `reivindicar`.

    Viva entre a chamada a `reivindicar` e a chamada a `concluir` ou `liberar` —
    o adaptador Postgres mantém uma transação aberta por esse intervalo inteiro,
    e é essa transação, não um prazo arbitrário, que serializa duas tentativas
    concorrentes sobre o mesmo evento (ver `RegistroEventos.reivindicar`).
    """

    def concluir(self, situacao: SituacaoEvento) -> None:
        """Marca o evento como concluído e libera a exclusividade."""
        ...

    def liberar(self) -> None:
        """Libera a exclusividade sem concluir.

        Usada quando o processamento falha (caso TI-38): o evento permanece
        visível na auditoria como pendente, e a próxima tentativa — seja a
        reentrega do provedor, seja uma segunda entrega concorrente que estava
        esperando — consegue reivindicá-lo de novo.
        """
        ...


class RegistroEventos(Protocol):
    """Porta de persistência e idempotência.

    A garantia de efeito único (TI-37) e a retomada após falha (TI-38) não são
    dois mecanismos: são a mesma reivindicação, vista em dois desfechos. Duas
    chamadas concorrentes de `reivindicar` para o mesmo evento não podem ambas
    devolver uma reivindicação viva — a segunda bloqueia até a primeira liberar
    ou concluir, e só então decide, com o estado já definitivo, se ainda há o
    que fazer. Um par de portas "registrar" + "marcar_processado" que não
    compartilhasse essa exclusividade pareceria correto e não seria: a janela
    entre as duas chamadas é exatamente onde uma segunda entrega do mesmo
    evento processaria em paralelo.
    """

    def reivindicar(self, evento: EventoWebhook) -> ReivindicacaoDeEvento | None:
        """Registra o evento, se ainda não existir, e reivindica exclusividade.

        Devolve None quando o evento já foi concluído antes (TI-37): nesse caso
        nada é escrito, e a chamada não bloqueia. Caso contrário, devolve uma
        reivindicação — mesmo que o evento já tivesse sido registrado por uma
        tentativa anterior que não concluiu, o que sustenta o TI-38. Entre duas
        chamadas concorrentes para o mesmo evento, uma delas espera a outra
        `concluir` ou `liberar` antes de saber qual dos dois desfechos aplica.
        """
        ...

    def registrar_recusa(self, *, motivo: str, corpo: bytes) -> None:
        """Grava uma entrega autêntica que não pôde ser interpretada.

        O caso TI-39 exige que o conteúdo malformado seja registrado sem efeito:
        a entrega provou vir do provedor, então o que chegou interessa à
        auditoria (RNF04), mesmo sem envelope válido.
        """
        ...


class RegistroConexoes(Protocol):
    """Porta das origens observadas.

    Existe para responder uma pergunta só: esta assinatura ainda vale? É o que
    permite recusar uma entrega legítima capturada e reapresentada depois que a
    assinatura foi removida ou expirou — a terceira causa do caso TI-36, que o
    Microsoft Graph não oferece meio de detectar por entrega (ver a Seção 5.1.5:
    `validationTokens` só existe em notificações com dados de recurso, e
    `driveItem` não as suporta).
    """

    def assinatura_ativa(self, subscription_id: str) -> bool: ...


class ProcessadorEvento(Protocol):
    """Porta do efeito de domínio.

    É o ponto de encaixe previsto para a indexação: hoje a implementação apenas
    marca a origem como pendente de varredura, e a vetorização entra depois como
    outra implementação desta mesma porta, sem alterar rota nem serviço.
    """

    def suporta(self, tipo: str) -> bool: ...

    def processar(self, evento: EventoWebhook) -> None: ...


class ReceberEventoWebhook:
    """Recebe uma entrega de webhook, na ordem verifica -> registra -> processa.

    A ordem não é acidental. A Seção 6.4.1 estabelece que "a validação de entrada
    precede sempre o efeito colateral", e o caso TI-38 exige que a confirmação ao
    provedor só ocorra depois da persistência: por isso o evento é gravado antes
    de ser processado, e o `marcar_processado` só acontece quando o efeito foi
    aplicado de fato.
    """

    def __init__(
        self,
        *,
        verificador: VerificadorAssinatura,
        tradutor: TradutorDeEvento,
        registro: RegistroEventos,
        processador: ProcessadorEvento,
    ) -> None:
        self._verificador = verificador
        self._tradutor = tradutor
        self._registro = registro
        self._processador = processador

    def receber(self, *, cabecalhos: Mapping[str, str], corpo: bytes) -> ResultadoRecepcao:
        # A verificação vem primeiro e, se falhar, não escreve nada. É deliberado:
        # registrar entregas não autenticadas daria a qualquer um na internet uma
        # forma de escrever na trilha de auditoria.
        self._verificador.verificar(cabecalhos=cabecalhos, corpo=corpo)

        try:
            eventos = self._tradutor.traduzir(cabecalhos=cabecalhos, corpo=corpo)
        except WebhookError as exc:
            # Daqui em diante a entrega já provou ser legítima, então o que chegou
            # fica registrado ainda que não possa ser processado (TI-39).
            self._registro.registrar_recusa(motivo=exc.code.name, corpo=corpo)
            raise

        # Se um evento do meio do lote falhar, os anteriores já estão concluídos e
        # o erro sobe, virando 5xx. O provedor reentrega o lote inteiro, e é a
        # idempotência do TI-37 que impede o efeito duplo: os já concluídos voltam
        # como DUPLICADO e só o que faltava é processado. Sem ela, uma falha
        # parcial reaplicaria tudo que veio antes a cada tentativa.
        return ResultadoRecepcao(resultados=tuple(self._receber_um(evento) for evento in eventos))

    def _receber_um(self, evento: EventoWebhook) -> ResultadoEvento:
        try:
            reivindicacao = self._registro.reivindicar(evento)
        except WebhookError:
            raise
        except Exception as exc:
            raise WebhookError(WebhookErrorCode.FALHA_DE_PERSISTENCIA) from exc

        if reivindicacao is None:
            return ResultadoEvento(situacao=SituacaoEvento.DUPLICADO, evento=evento)

        # Evento fora do catálogo é concluído sem efeito (TI-40), e não liberado:
        # reentregá-lo não produziria nada de diferente, e deixá-lo pendente
        # faria o provedor insistir à toa.
        if not self._processador.suporta(evento.tipo):
            reivindicacao.concluir(SituacaoEvento.IGNORADO)
            return ResultadoEvento(situacao=SituacaoEvento.IGNORADO, evento=evento)

        try:
            self._processador.processar(evento)
        except WebhookError:
            reivindicacao.liberar()
            raise
        except Exception as exc:
            reivindicacao.liberar()
            raise WebhookError(WebhookErrorCode.FALHA_DE_PROCESSAMENTO) from exc

        reivindicacao.concluir(SituacaoEvento.PROCESSADO)
        return ResultadoEvento(situacao=SituacaoEvento.PROCESSADO, evento=evento)


# O código de resposta faz parte do contrato do webhook, e não da camada de
# apresentação: é ele que decide se o provedor reentrega. O Microsoft Graph
# reentrega por até quatro horas diante de 5xx e desiste diante de 4xx. Por isso
# o mapeamento vive junto das causas, e a rota apenas o consulta.
STATUS_POR_ERRO: dict[WebhookErrorCode, int] = {
    WebhookErrorCode.ASSINATURA_AUSENTE: 401,
    WebhookErrorCode.ASSINATURA_INVALIDA: 401,
    WebhookErrorCode.ASSINATURA_EXPIRADA: 401,
    WebhookErrorCode.CONTEUDO_MALFORMADO: 400,
    WebhookErrorCode.FALHA_DE_PERSISTENCIA: 503,
    WebhookErrorCode.FALHA_DE_PROCESSAMENTO: 503,
}

# 202 e não 200: o efeito é aplicado fora da janela de três segundos que o Graph
# concede, e a própria documentação do provedor recomenda enfileirar e responder
# 202. As três situações — processado, ignorado e duplicado — compartilham este
# código porque, para o provedor, todas significam a mesma coisa: entrega aceita,
# não reenvie. A distinção entre elas interessa à auditoria, e vai no corpo.
STATUS_ACEITE = 202
