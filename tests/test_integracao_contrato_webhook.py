"""Suíte de contrato dos webhooks de entrada (casos TI-35 a TI-42).

A classe `ContratoWebhookInbound` descreve o comportamento exigido de qualquer
provedor, sem citar nenhum. Ela tem um único ponto de extensão: o método de
fábrica `construir_ambiente`. Esta suíte é exercitada contra um dublê
determinístico em memória; `tests/test_integracao_webhook.py` a herda de novo
para exercitá-la contra o adaptador do Microsoft Graph através da rota HTTP
real, sem reescrever nenhum caso.

Os casos TI-35 a TI-40 vêm da tabela da Seção 6.4.4. TI-41 e TI-42 foram
acrescentados na Sprint 4, quando a implementação do provedor revelou que uma
entrega pode carregar várias mudanças — situação que a especificação original
não previa e que, sem estes dois casos, passa despercebida.

As asserções são feitas em código de status HTTP porque é essa a linguagem da
tabela de casos — e porque, num webhook, o código de resposta não é detalhe de
apresentação: é ele que determina se o provedor reentrega.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import unittest
from abc import ABC, abstractmethod
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from services.webhook_service import (
    STATUS_ACEITE,
    STATUS_POR_ERRO,
    VERSAO_ENVELOPE,
    EventoWebhook,
    ReceberEventoWebhook,
    SituacaoEvento,
    WebhookError,
    WebhookErrorCode,
)

TIPO_CONHECIDO = "item.atualizado"
TIPO_DESCONHECIDO = "item.rebocado_por_um_trator"


@dataclass(frozen=True)
class Entrega:
    """Uma entrega crua, como o provedor a enviaria."""

    cabecalhos: Mapping[str, str]
    corpo: bytes


class AmbienteWebhook(ABC):
    """O que uma subclasse precisa fornecer para exercitar o contrato.

    Cada implementação sabe forjar entregas no formato do seu provedor e sabe
    entregá-las ao objeto sob teste, devolvendo o código de status observado.
    """

    @abstractmethod
    def entregar(self, entrega: Entrega) -> int:
        """Entrega o evento e devolve o código de status HTTP observado."""

    @abstractmethod
    def entrega_valida(self, *, tipo: str = TIPO_CONHECIDO, identificador: str = "evt-1") -> Entrega: ...

    @abstractmethod
    def entregas_de_lote(self, *, quantidade: int) -> Sequence[Entrega]:
        """As entregas que, juntas, carregam `quantidade` mudanças conhecidas.

        Um provedor que agrupa devolve uma entrega só com várias mudanças
        dentro; um que não agrupa devolve várias entregas de uma mudança cada.
        O contrato não se importa com qual dos dois é — importa que nenhuma
        mudança se perca no caminho.
        """

    @abstractmethod
    def entrega_sem_assinatura(self) -> Entrega: ...

    @abstractmethod
    def entrega_com_assinatura_incorreta(self) -> Entrega: ...

    @abstractmethod
    def entrega_com_assinatura_antiga(self) -> Entrega: ...

    @abstractmethod
    def entrega_malformada(self) -> Entrega: ...

    @abstractmethod
    def efeitos_aplicados(self) -> int: ...

    @abstractmethod
    def eventos_registrados(self) -> int: ...

    @abstractmethod
    def quebrar_processamento(self, *, depois_de: int = 0) -> None:
        """Faz o processamento falhar depois de `depois_de` efeitos aplicados."""


class ContratoWebhookInbound:
    """Comportamento exigido de qualquer receptor de webhook do AZ1.

    Não herda de TestCase de propósito: assim o contrato não é coletado nem
    executado sozinho. As subclasses herdam de (ContratoWebhookInbound,
    unittest.TestCase) e implementam apenas `construir_ambiente`.
    """

    def construir_ambiente(self) -> AmbienteWebhook:
        raise NotImplementedError

    def setUp(self) -> None:
        self.ambiente = self.construir_ambiente()

    # TI-35
    def test_entrega_com_assinatura_valida_e_processada(self) -> None:
        status = self.ambiente.entregar(self.ambiente.entrega_valida())

        self.assertIn(status, range(200, 300))
        self.assertEqual(self.ambiente.efeitos_aplicados(), 1)

    # TI-36
    def test_assinatura_invalida_e_rejeitada(self) -> None:
        causas = {
            "sem assinatura": self.ambiente.entrega_sem_assinatura(),
            "assinatura incorreta": self.ambiente.entrega_com_assinatura_incorreta(),
            "assinatura antiga": self.ambiente.entrega_com_assinatura_antiga(),
        }

        for nome, entrega in causas.items():
            with self.subTest(causa=nome):
                self.assertEqual(self.ambiente.entregar(entrega), 401)

        # Nenhuma das três pode ter produzido efeito nem deixado rastro de evento
        # aceito: a rejeição acontece antes de qualquer escrita.
        self.assertEqual(self.ambiente.efeitos_aplicados(), 0)
        self.assertEqual(self.ambiente.eventos_registrados(), 0)

    # TI-37
    def test_entrega_duplicada_produz_efeito_unico(self) -> None:
        entrega = self.ambiente.entrega_valida(identificador="evt-repetido")

        primeiro = self.ambiente.entregar(entrega)
        segundo = self.ambiente.entregar(entrega)

        self.assertIn(primeiro, range(200, 300))
        self.assertIn(segundo, range(200, 300))
        self.assertEqual(self.ambiente.efeitos_aplicados(), 1)

    # TI-38
    def test_confirmacao_so_ocorre_apos_persistencia(self) -> None:
        self.ambiente.quebrar_processamento()
        entrega = self.ambiente.entrega_valida(identificador="evt-que-falha")

        status = self.ambiente.entregar(entrega)

        self.assertGreaterEqual(status, 500)
        self.assertEqual(self.ambiente.efeitos_aplicados(), 0)

        # O 5xx existe para provocar reentrega. A reentrega precisa conseguir
        # aplicar o efeito: um evento que falhou não pode ficar marcado como
        # concluído e ser descartado como duplicata na segunda tentativa.
        self.assertIn(self.ambiente.entregar(entrega), range(200, 300))
        self.assertEqual(self.ambiente.efeitos_aplicados(), 1)

    # TI-39
    def test_conteudo_malformado_e_rejeitado(self) -> None:
        status = self.ambiente.entregar(self.ambiente.entrega_malformada())

        self.assertEqual(status, 400)
        self.assertEqual(self.ambiente.efeitos_aplicados(), 0)
        # "evento registrado sem efeito": a entrega é autêntica, então precisa
        # deixar rastro na auditoria mesmo sendo impossível de interpretar.
        self.assertEqual(self.ambiente.eventos_registrados(), 1)

    # TI-40
    def test_evento_de_tipo_desconhecido_e_registrado_e_ignorado(self) -> None:
        entrega = self.ambiente.entrega_valida(tipo=TIPO_DESCONHECIDO, identificador="evt-exotico")

        status = self.ambiente.entregar(entrega)

        self.assertIn(status, range(200, 300))
        self.assertEqual(self.ambiente.efeitos_aplicados(), 0)
        self.assertEqual(self.ambiente.eventos_registrados(), 1)

    # TI-41
    def test_lote_de_mudancas_produz_um_efeito_por_mudanca(self) -> None:
        """Três mudanças na origem produzem três efeitos.

        Vale igual para quem agrupa e para quem não agrupa. O caso existe porque
        um provedor que agrupa não reenvia o que sobrou depois de receber 2xx:
        um receptor que tratasse só a primeira notificação de cada entrega
        confirmaria o lote inteiro e perderia as demais em silêncio.
        """
        for entrega in self.ambiente.entregas_de_lote(quantidade=3):
            self.assertIn(self.ambiente.entregar(entrega), range(200, 300))

        self.assertEqual(self.ambiente.efeitos_aplicados(), 3)
        self.assertEqual(self.ambiente.eventos_registrados(), 3)

    # TI-42
    def test_reentrega_apos_falha_parcial_completa_sem_repetir(self) -> None:
        """A reentrega de um lote parcialmente processado completa, sem repetir.

        É o encontro do TI-38 com o TI-41. O provedor reentrega o que não foi
        confirmado — e, quando agrupa, reentrega o lote inteiro, inclusive as
        mudanças que já tinham sido aplicadas. É a idempotência do TI-37 que
        impede o efeito duplo nessas.
        """
        self.ambiente.quebrar_processamento(depois_de=1)
        entregas = self.ambiente.entregas_de_lote(quantidade=3)

        primeira_passagem = [self.ambiente.entregar(entrega) for entrega in entregas]

        self.assertTrue(any(status >= 500 for status in primeira_passagem))
        self.assertLess(self.ambiente.efeitos_aplicados(), 3)

        for entrega in entregas:
            self.assertIn(self.ambiente.entregar(entrega), range(200, 300))

        self.assertEqual(self.ambiente.efeitos_aplicados(), 3)


# ---------------------------------------------------------------------------
# Dublê determinístico em memória
# ---------------------------------------------------------------------------
# O contrato roda primeiro contra um provedor fictício com as mesmas propriedades
# do real: assinatura sobre o corpo, marca de tempo que envelhece, corpo JSON e
# identificador de evento. Assim os casos exercitam o serviço de verdade, e não
# uma maquete dele, antes mesmo de tocar no adaptador do provedor.
#
# Este dublê assina com HMAC e carimbo de tempo, o que o Microsoft Graph não faz
# em notificações de `driveItem` (Seção 5.1.5). A diferença é deliberada: o
# contrato descreve o que se exige de um provedor qualquer, e o dublê representa
# o caso favorável. O adaptador do Graph atende a mesma exigência por outro
# caminho — validade da assinatura em vez de frescor da entrega.

SEGREDO = b"segredo-de-teste"
JANELA_DE_ACEITE = timedelta(minutes=5)


def _assinar(corpo: bytes, marca: str) -> str:
    return hmac.new(SEGREDO, marca.encode() + b"." + corpo, hashlib.sha256).hexdigest()


class VerificadorEmMemoria:
    def verificar(self, *, cabecalhos: Mapping[str, str], corpo: bytes) -> None:
        assinatura = cabecalhos.get("x-assinatura")
        marca = cabecalhos.get("x-marca-de-tempo")
        if not assinatura or not marca:
            raise WebhookError(WebhookErrorCode.ASSINATURA_AUSENTE)

        if not hmac.compare_digest(assinatura, _assinar(corpo, marca)):
            raise WebhookError(WebhookErrorCode.ASSINATURA_INVALIDA)

        # Defesa contra reapresentação de uma entrega capturada antes: a assinatura
        # confere, mas a marca de tempo que ela protege já saiu da janela.
        if datetime.now(UTC) - datetime.fromisoformat(marca) > JANELA_DE_ACEITE:
            raise WebhookError(WebhookErrorCode.ASSINATURA_EXPIRADA)


class TradutorEmMemoria:
    def traduzir(self, *, cabecalhos: Mapping[str, str], corpo: bytes) -> Sequence[EventoWebhook]:
        try:
            bruto = json.loads(corpo)
            notificacoes = bruto if isinstance(bruto, list) else [bruto]
            return [self._converter(n, cabecalhos) for n in notificacoes]
        except (json.JSONDecodeError, TypeError) as exc:
            raise WebhookError(WebhookErrorCode.CONTEUDO_MALFORMADO) from exc

    def _converter(self, bruto: Mapping[str, object], cabecalhos: Mapping[str, str]) -> EventoWebhook:
        try:
            return EventoWebhook(
                identificador=bruto["id"],  # type: ignore[arg-type]
                tipo=bruto["tipo"],  # type: ignore[arg-type]
                versao=VERSAO_ENVELOPE,
                marca_de_tempo=datetime.fromisoformat(cabecalhos["x-marca-de-tempo"]),
                correlacao=bruto.get("correlacao", bruto["id"]),  # type: ignore[arg-type]
                conteudo=bruto.get("dados", {}),  # type: ignore[arg-type]
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise WebhookError(WebhookErrorCode.CONTEUDO_MALFORMADO) from exc


class RegistroEmMemoria:
    def __init__(self) -> None:
        self.eventos: dict[str, SituacaoEvento | None] = {}
        self.recusas: list[tuple[str, bytes]] = []

    def registrar_recusa(self, *, motivo: str, corpo: bytes) -> None:
        self.recusas.append((motivo, corpo))

    def registrar(self, evento: EventoWebhook) -> bool:
        if self.eventos.get(evento.identificador) is not None:
            return False
        self.eventos[evento.identificador] = None
        return True

    def marcar_processado(self, evento: EventoWebhook, situacao: SituacaoEvento) -> None:
        self.eventos[evento.identificador] = situacao


class ProcessadorEmMemoria:
    def __init__(self) -> None:
        self.efeitos = 0
        self.quebrar_em: int | None = None

    def suporta(self, tipo: str) -> bool:
        return tipo == TIPO_CONHECIDO

    def processar(self, evento: EventoWebhook) -> None:
        if self.quebrar_em is not None and self.efeitos == self.quebrar_em:
            self.quebrar_em = None
            raise RuntimeError("falha simulada de processamento")
        self.efeitos += 1


class AmbienteEmMemoria(AmbienteWebhook):
    def __init__(self) -> None:
        self.registro = RegistroEmMemoria()
        self.processador = ProcessadorEmMemoria()
        self.receptor = ReceberEventoWebhook(
            verificador=VerificadorEmMemoria(),
            tradutor=TradutorEmMemoria(),
            registro=self.registro,
            processador=self.processador,
        )

    def entregar(self, entrega: Entrega) -> int:
        try:
            self.receptor.receber(cabecalhos=entrega.cabecalhos, corpo=entrega.corpo)
        except WebhookError as exc:
            return STATUS_POR_ERRO[exc.code]
        return STATUS_ACEITE

    def _montar(self, corpo: bytes, *, idade: timedelta = timedelta(0)) -> Entrega:
        marca = (datetime.now(UTC) - idade).isoformat()
        return Entrega(
            cabecalhos={"x-marca-de-tempo": marca, "x-assinatura": _assinar(corpo, marca)},
            corpo=corpo,
        )

    def entrega_valida(self, *, tipo: str = TIPO_CONHECIDO, identificador: str = "evt-1") -> Entrega:
        return self._montar(json.dumps({"id": identificador, "tipo": tipo, "dados": {"item": 42}}).encode())

    def entregas_de_lote(self, *, quantidade: int) -> Sequence[Entrega]:
        # O provedor fictício agrupa, como o Graph: uma entrega, várias mudanças.
        notificacoes = [
            {"id": f"evt-lote-{indice}", "tipo": TIPO_CONHECIDO, "dados": {"item": indice}}
            for indice in range(quantidade)
        ]
        return [self._montar(json.dumps(notificacoes).encode())]

    def entrega_sem_assinatura(self) -> Entrega:
        return Entrega(cabecalhos={}, corpo=self.entrega_valida().corpo)

    def entrega_com_assinatura_incorreta(self) -> Entrega:
        valida = self.entrega_valida()
        return Entrega(
            cabecalhos={**valida.cabecalhos, "x-assinatura": "0" * 64},
            corpo=valida.corpo,
        )

    def entrega_com_assinatura_antiga(self) -> Entrega:
        corpo = json.dumps({"id": "evt-antigo", "tipo": TIPO_CONHECIDO, "dados": {}}).encode()
        return self._montar(corpo, idade=JANELA_DE_ACEITE + timedelta(minutes=1))

    def entrega_malformada(self) -> Entrega:
        return self._montar(b'{"id": "evt-torto", "dados": {}}')

    def efeitos_aplicados(self) -> int:
        return self.processador.efeitos

    def eventos_registrados(self) -> int:
        return len(self.registro.eventos) + len(self.registro.recusas)

    def quebrar_processamento(self, *, depois_de: int = 0) -> None:
        self.processador.quebrar_em = depois_de


class TestContratoWebhookEmMemoria(ContratoWebhookInbound, unittest.TestCase):
    """Exercita o contrato contra o dublê em memória (TI-35 a TI-42)."""

    def construir_ambiente(self) -> AmbienteWebhook:
        return AmbienteEmMemoria()
