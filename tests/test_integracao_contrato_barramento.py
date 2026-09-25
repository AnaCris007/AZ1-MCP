"""Suíte de contrato do barramento de mensagens (casos TI-41 a TI-46).

Espelha `tests/test_integracao_contrato_webhook.py`: a classe abstrata
`ContratoBarramentoMensagens` descreve o comportamento exigido de QUALQUER
barramento, sem citar RabbitMQ, e tem um único ponto de extensão — a fábrica
`construir_ambiente`, que monta produtor + broker + consumidor. A suíte é
exercitada aqui contra um BROKER-FAKE EM MEMÓRIA (fila em memória com ack, nack,
dead-letter e contador de tentativas). Uma subclasse opcional
`TestContratoBarramentoRabbitMQ`, guardada por `TEST_RABBITMQ_URL` (no estilo do
`TEST_DATABASE_URL` da suíte destrutiva), roda o mesmo contrato contra um
RabbitMQ real quando a variável está presente.

Os nomes dos métodos de teste são os EXATOS da Seção 6.4.4 do `docs/Projeto.md`.
"""

from __future__ import annotations

import contextlib
import itertools
import os
import time
import unittest
from abc import ABC, abstractmethod
from collections import deque
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime

from mensageria.config import MensageriaSettings
from mensageria.consumidor import ConsumidorVarredura
from mensageria.envelope import serializar
from mensageria.publicador import (
    PublicacaoIndisponivel,
    PublicadorRabbitMQ,
    declarar_topologia,
)
from services.webhook_service import VERSAO_ENVELOPE, EventoWebhook


def _evento(*, identificador: str, correlacao: str = "sub-1") -> EventoWebhook:
    return EventoWebhook(
        identificador=identificador,
        tipo="graph.updated",
        versao=VERSAO_ENVELOPE,
        marca_de_tempo=datetime(2026, 9, 21, 14, 30, 15, tzinfo=UTC),
        correlacao=correlacao,
        conteudo={"item": identificador},
    )


class AmbienteBarramento(ABC):
    """O que uma subclasse precisa fornecer para exercitar o contrato.

    Cada implementação sabe publicar um envelope, consumir uma rodada (entregando
    as mensagens pendentes ao consumidor) e reportar o estado observável: o que
    o consumidor efetivou, o que sobrou na fila e o que foi parar na fila morta.
    """

    @abstractmethod
    def publicar(self, evento: EventoWebhook) -> None:
        """Publica um envelope. Levanta se o barramento estiver inacessível."""

    @abstractmethod
    def publicar_bruto(self, corpo: bytes) -> None:
        """Publica bytes crus, para exercitar payload indesserializável."""

    @abstractmethod
    def consumir_rodada(self) -> None:
        """Entrega ao consumidor as mensagens hoje disponíveis na fila."""

    @abstractmethod
    def efeitos_aplicados(self) -> int:
        """Quantas varreduras distintas o consumidor efetivou (correlacoes varridas)."""

    @abstractmethod
    def mensagens_na_fila(self) -> int: ...

    @abstractmethod
    def mensagens_mortas(self) -> list[tuple[bytes, str]]:
        """Mensagens na fila morta, como (corpo, causa)."""

    @abstractmethod
    def derrubar_broker(self) -> None:
        """Torna a publicação seguinte inacessível (TI-46)."""

    @abstractmethod
    def fazer_consumidor_reprovar(self, *, sempre: bool = False) -> None:
        """Faz o processamento do consumidor levantar (uma vez, ou sempre)."""

    @abstractmethod
    def parar_de_reprovar(self) -> None:
        """Restaura o consumidor ao processamento normal (bem-sucedido)."""


class ContratoBarramentoMensagens:
    """Comportamento exigido de qualquer barramento de mensagens do AZ1.

    Não herda de TestCase de propósito: assim o contrato não é coletado sozinho.
    As subclasses herdam de (ContratoBarramentoMensagens, unittest.TestCase) e
    implementam apenas `construir_ambiente`.
    """

    def construir_ambiente(self) -> AmbienteBarramento:
        raise NotImplementedError

    def setUp(self) -> None:
        self.ambiente = self.construir_ambiente()

    # TI-41
    def test_publica_e_consome_o_envelope_integro(self) -> None:
        self.ambiente.publicar(_evento(identificador="evt-1", correlacao="sub-42"))

        self.ambiente.consumir_rodada()

        self.assertEqual(self.ambiente.efeitos_aplicados(), 1)
        self.assertEqual(self.ambiente.mensagens_na_fila(), 0)
        self.assertEqual(self.ambiente.mensagens_mortas(), [])

    # TI-42
    def test_confirmacao_remove_e_recusa_devolve_a_mensagem(self) -> None:
        # Confirmação remove: uma mensagem consumida com sucesso some da fila.
        self.ambiente.publicar(_evento(identificador="evt-ok"))
        self.ambiente.consumir_rodada()
        self.assertEqual(self.ambiente.mensagens_na_fila(), 0)
        self.assertEqual(self.ambiente.efeitos_aplicados(), 1)

        # Recusa devolve: uma mensagem cujo processamento levanta uma vez volta a
        # ficar disponível para a próxima rodada (requeue), e então é processada.
        self.ambiente.fazer_consumidor_reprovar(sempre=False)
        self.ambiente.publicar(_evento(identificador="evt-retry", correlacao="sub-2"))
        self.ambiente.consumir_rodada()  # reprova → devolve à fila
        self.assertEqual(self.ambiente.mensagens_na_fila(), 1)

        self.ambiente.consumir_rodada()  # segunda tentativa → sucesso
        self.assertEqual(self.ambiente.mensagens_na_fila(), 0)

    # TI-43
    def test_falha_persistente_vai_para_dead_letter(self) -> None:
        self.ambiente.fazer_consumidor_reprovar(sempre=True)
        self.ambiente.publicar(_evento(identificador="evt-veneno", correlacao="sub-x"))

        # Cada rodada reprova e incrementa o contador de tentativas. Enquanto a
        # mensagem ainda estiver na fila, houve reentrega; o laço para quando ela
        # sai da fila — seja porque foi para a morta, seja por segurança contra
        # laço infinito. O limite de segurança é generoso: max_tentativas + 2.
        limite_de_seguranca = self.ambiente.broker.max_tentativas + 2
        rodadas = 0
        tentativas_observadas = []
        while self.ambiente.mensagens_na_fila() > 0 or rodadas == 0:
            self.ambiente.consumir_rodada()
            rodadas += 1
            tentativas_observadas.append(rodadas)
            if rodadas > limite_de_seguranca:
                self.fail("a mensagem-veneno nunca foi para a fila morta")

        # O contador subiu a cada reentrega (uma rodada por tentativa).
        self.assertGreater(len(tentativas_observadas), 1)
        self.assertEqual(self.ambiente.mensagens_na_fila(), 0)
        mortas = self.ambiente.mensagens_mortas()
        self.assertEqual(len(mortas), 1)
        _corpo, causa = mortas[0]
        self.assertTrue(causa)  # a causa fica registrada

        # A fila principal segue processando: uma mensagem sã depois do veneno
        # é varrida normalmente.
        self.ambiente.parar_de_reprovar()
        self.ambiente.publicar(_evento(identificador="evt-sao", correlacao="sub-sao"))
        self.ambiente.consumir_rodada()
        self.assertEqual(self.ambiente.efeitos_aplicados(), 1)

    # TI-43 (parte indesserializável)
    def test_payload_indesserializavel_vai_de_imediato_para_dead_letter(self) -> None:
        self.ambiente.publicar_bruto(b"nao e um envelope json")

        self.ambiente.consumir_rodada()

        # Sem reentrega: vai direto para a fila morta.
        self.assertEqual(self.ambiente.mensagens_na_fila(), 0)
        self.assertEqual(len(self.ambiente.mensagens_mortas()), 1)

    # TI-44
    def test_consumo_duplicado_produz_efeito_unico(self) -> None:
        evento = _evento(identificador="evt-dup", correlacao="sub-dup")

        self.ambiente.publicar(evento)
        self.ambiente.publicar(evento)
        self.ambiente.consumir_rodada()

        # Marcar delta_pendente = FALSE duas vezes tem efeito único: a mesma
        # correlacao foi varrida, e varrer de novo não muda nada.
        self.assertEqual(self.ambiente.efeitos_aplicados(), 1)

    # TI-45
    def test_consumidor_nao_depende_de_ordem_global(self) -> None:
        # Publica fora de ordem: identificadores decrescentes, correlacoes
        # distintas. O consumidor processa todas sem pressupor ordem de chegada.
        for indice in (3, 1, 2):
            self.ambiente.publicar(
                _evento(identificador=f"evt-{indice}", correlacao=f"sub-{indice}")
            )

        self.ambiente.consumir_rodada()

        self.assertEqual(self.ambiente.efeitos_aplicados(), 3)
        self.assertEqual(self.ambiente.mensagens_na_fila(), 0)

    # TI-46
    def test_indisponibilidade_na_publicacao_e_reportada(self) -> None:
        self.ambiente.derrubar_broker()

        with self.assertRaises(PublicacaoIndisponivel):
            self.ambiente.publicar(_evento(identificador="evt-perdido"))


# ---------------------------------------------------------------------------
# Broker-fake em memória
# ---------------------------------------------------------------------------
# Reproduz as propriedades do RabbitMQ que o contrato exige: fila durável em
# memória, dead-letter-exchange com fila morta, contador de tentativas por
# mensagem e a mesma API de canal (basic_ack / basic_nack / delivery_tag) que
# `ConsumidorVarredura._tratar` consome. Assim o contrato exercita o consumidor
# de verdade, e não uma maquete dele, antes mesmo de tocar num broker real.


@dataclass
class _Mensagem:
    corpo: bytes
    tentativas: int = 0


@dataclass
class _Metodo:
    """Contraparte do `method` do pika passado ao callback."""

    delivery_tag: int
    mensagem: _Mensagem


@dataclass
class BrokerEmMemoria:
    max_tentativas: int
    fila: deque[_Mensagem] = field(default_factory=deque)
    morta: list[tuple[bytes, str]] = field(default_factory=list)
    fora_do_ar: bool = False
    _proximo_tag: int = 0

    # -- lado do produtor ---------------------------------------------------
    def publicar(self, corpo: bytes) -> None:
        if self.fora_do_ar:
            raise PublicacaoIndisponivel("broker fora do ar (fake)")
        self.fila.append(_Mensagem(corpo=corpo))

    # -- API de canal consumida por ConsumidorVarredura._tratar -------------
    def basic_ack(self, *, delivery_tag: int) -> None:
        self._em_voo.pop(delivery_tag, None)

    def basic_nack(self, *, delivery_tag: int, requeue: bool) -> None:
        mensagem = self._em_voo.pop(delivery_tag, None)
        if mensagem is None:
            return
        if not requeue:
            # Recusa em definitivo (payload indesserializável / versão
            # desconhecida): dead-letter imediato, sem consumir tentativas. É a
            # semântica de basic_nack(requeue=False) sobre uma quorum queue.
            self.morta.append((mensagem.corpo, "recusada_sem_reentrega"))
            return
        # requeue=True: devolve à fila, mas a quorum queue aplica
        # `x-delivery-limit`. `tentativas` já foi incrementado na entrega desta
        # rodada; ao ultrapassar o limite, o broker dead-letter-a sozinho.
        if mensagem.tentativas > self.max_tentativas:
            self.morta.append((mensagem.corpo, "x-delivery-limit atingido"))
        else:
            self.fila.appendleft(mensagem)

    def __post_init__(self) -> None:
        self._em_voo: dict[int, _Mensagem] = {}

    def entregar_disponiveis(self, callback) -> None:
        """Entrega ao callback cada mensagem hoje na fila, uma vez."""
        pendentes = list(self.fila)
        self.fila.clear()
        for mensagem in pendentes:
            mensagem.tentativas += 1
            self._proximo_tag += 1
            tag = self._proximo_tag
            self._em_voo[tag] = mensagem
            metodo = _Metodo(delivery_tag=tag, mensagem=mensagem)
            callback(self, metodo, None, mensagem.corpo)


class _VarreduraFake:
    """Contraparte em memória de `VarreduraDeConexao`.

    Marca a correlacao como varrida num conjunto — marcar de novo é efeito
    único (idempotência do TI-44). Pode ser instruída a reprovar (uma vez ou
    sempre) para exercitar o requeue e a dead-letter.
    """

    def __init__(self) -> None:
        self.varridas: set[str] = set()
        self._reprovar_sempre = False
        self._reprovar_uma_vez = False

    def varrer(self, evento: EventoWebhook) -> None:
        if self._reprovar_sempre:
            raise RuntimeError("falha simulada persistente de varredura")
        if self._reprovar_uma_vez:
            self._reprovar_uma_vez = False
            raise RuntimeError("falha simulada única de varredura")
        self.varridas.add(evento.correlacao)


class AmbienteEmMemoria(AmbienteBarramento):
    def __init__(self) -> None:
        self.settings = MensageriaSettings(url="amqp://em-memoria")
        self.broker = BrokerEmMemoria(max_tentativas=self.settings.max_tentativas)
        self.varredura = _VarreduraFake()
        self.consumidor = ConsumidorVarredura(self.settings, self.varredura)

    def publicar(self, evento: EventoWebhook) -> None:
        self.broker.publicar(serializar(evento))

    def publicar_bruto(self, corpo: bytes) -> None:
        self.broker.publicar(corpo)

    def consumir_rodada(self) -> None:
        self.broker.entregar_disponiveis(
            lambda canal, metodo, _props, corpo: self.consumidor._tratar(canal, metodo, corpo)
        )

    def efeitos_aplicados(self) -> int:
        return len(self.varredura.varridas)

    def mensagens_na_fila(self) -> int:
        return len(self.broker.fila)

    def mensagens_mortas(self) -> list[tuple[bytes, str]]:
        return list(self.broker.morta)

    def derrubar_broker(self) -> None:
        self.broker.fora_do_ar = True

    def fazer_consumidor_reprovar(self, *, sempre: bool = False) -> None:
        if sempre:
            self.varredura._reprovar_sempre = True
        else:
            self.varredura._reprovar_sempre = False
            self.varredura._reprovar_uma_vez = True

    def parar_de_reprovar(self) -> None:
        self.varredura._reprovar_sempre = False
        self.varredura._reprovar_uma_vez = False


class TestContratoBarramentoEmMemoria(ContratoBarramentoMensagens, unittest.TestCase):
    """Exercita o contrato contra o broker-fake em memória (TI-41 a TI-46)."""

    def construir_ambiente(self) -> AmbienteBarramento:
        return AmbienteEmMemoria()


# ---------------------------------------------------------------------------
# Ambiente contra um RabbitMQ real
# ---------------------------------------------------------------------------
# O MESMO contrato, agora contra um broker de verdade. É o que confirma que o
# broker-fake acima modela a realidade — em especial a contagem do
# `x-delivery-limit` da quorum queue, o roteamento da dead-letter e os publisher
# confirms, que o fake apenas imita. A varredura continua sendo o dublê contável
# (`_VarreduraFake`): o alvo deste contrato é o BROKER, não a varredura, então o
# consumidor real roda sobre ela e a inspeção é feita por um canal de admin via
# pika. Cada instância usa nomes de topologia únicos (sufixo), para os testes se
# isolarem sem purga entre si; `fechar()` remove filas e exchanges ao fim.

# Contador de instâncias, para compor nomes de fila únicos por teste sem depender
# de aleatoriedade (que quebraria a reprodutibilidade).
_contador_ambiente = itertools.count()

# Quorum queues são assíncronas: um `nack(requeue)` que devolve a mensagem, ou o
# roteamento para a dead-letter, não são refletidos instantaneamente no
# `message_count`. Depois de uma rodada de consumo, deixa-se o broker estabilizar
# antes de o contrato ler as filas. É o preço de exercitar o broker DE VERDADE —
# o ambiente em memória é síncrono e não precisa disto.
_SETTLE_SEGUNDOS = 0.6

# Endereço deliberadamente inacessível para o TI-46: a porta 1 recusa conexão, e
# a próxima publicação do produtor apontado para cá vira PublicacaoIndisponivel.
_URL_INACESSIVEL = "amqp://az1:az1@127.0.0.1:1/"


class AmbienteRabbitMQ(AmbienteBarramento):
    """Encaixe do contrato contra um RabbitMQ real (produtor + consumidor + pika)."""

    def __init__(self, url: str, sufixo: str) -> None:
        import pika

        self._pika = pika
        base = MensageriaSettings(url=url)
        # Nomes únicos por instância → cada teste parte de filas limpas.
        self.settings = replace(
            base,
            exchange=f"{base.exchange}.test.{sufixo}",
            dlx=f"{base.dlx}.test.{sufixo}",
            fila=f"{base.fila}.test.{sufixo}",
            fila_morta=f"{base.fila_morta}.test.{sufixo}",
        )
        self.broker = self.settings  # o contrato TI-43 lê `broker.max_tentativas`

        self.publicador = PublicadorRabbitMQ(self.settings)
        self.varredura = _VarreduraFake()
        self.consumidor = ConsumidorVarredura(self.settings, self.varredura)

        # Canal de administração: publica bytes crus, conta e drena filas.
        self._conexao = pika.BlockingConnection(pika.URLParameters(url))
        self._canal = self._conexao.channel()
        declarar_topologia(self._canal, self.settings)
        # Publisher confirms também no canal de admin: sem isto, o `publicar_bruto`
        # é fire-and-forget e a mensagem pode não estar na fila quando a rodada de
        # consumo conta — uma corrida que só o payload cru sofre (o `publicar`
        # normal já confirma). Com confirms, `basic_publish` bloqueia até o aceite.
        self._canal.confirm_delivery()

    def publicar(self, evento: EventoWebhook) -> None:
        self.publicador.publicar(evento)

    def publicar_bruto(self, corpo: bytes) -> None:
        self._canal.basic_publish(
            exchange=self.settings.exchange,
            routing_key=self.settings.routing_key,
            body=corpo,
            properties=self._pika.BasicProperties(delivery_mode=2),
        )

    def consumir_rodada(self) -> None:
        # Só as mensagens disponíveis AGORA, uma vez cada — o que for devolvido
        # (nack requeue) fica para a próxima rodada, como no ambiente em memória.
        for _ in range(self._prontas()):
            metodo, _props, corpo = self._canal.basic_get(
                queue=self.settings.fila, auto_ack=False
            )
            if metodo is None:
                break
            self.consumidor._tratar(self._canal, metodo, corpo)
        # Deixa o requeue / roteamento para a dead-letter se refletir antes de o
        # contrato ler os contadores (quorum queue é assíncrona).
        time.sleep(_SETTLE_SEGUNDOS)

    def efeitos_aplicados(self) -> int:
        return len(self.varredura.varridas)

    def mensagens_na_fila(self) -> int:
        return self._prontas()

    def mensagens_mortas(self) -> list[tuple[bytes, str]]:
        mortas: list[tuple[bytes, str]] = []
        while True:
            metodo, props, corpo = self._canal.basic_get(
                queue=self.settings.fila_morta, auto_ack=True
            )
            if metodo is None:
                break
            mortas.append((corpo, self._causa(props)))
        return mortas

    def derrubar_broker(self) -> None:
        # Aponta o produtor para um endereço inacessível: a próxima publicação
        # falha ao conectar e o `PublicadorRabbitMQ` a converte em
        # PublicacaoIndisponivel (TI-46).
        self.publicador = PublicadorRabbitMQ(replace(self.settings, url=_URL_INACESSIVEL))

    def fazer_consumidor_reprovar(self, *, sempre: bool = False) -> None:
        if sempre:
            self.varredura._reprovar_sempre = True
        else:
            self.varredura._reprovar_sempre = False
            self.varredura._reprovar_uma_vez = True

    def parar_de_reprovar(self) -> None:
        self.varredura._reprovar_sempre = False
        self.varredura._reprovar_uma_vez = False

    # -- inspeção -----------------------------------------------------------

    def _prontas(self) -> int:
        return self._canal.queue_declare(
            queue=self.settings.fila, passive=True
        ).method.message_count

    @staticmethod
    def _causa(props: object) -> str:
        """Deriva a causa da morte do header `x-death` que o broker adiciona."""
        headers = getattr(props, "headers", None) or {}
        morte = headers.get("x-death")
        if isinstance(morte, list) and morte:
            return str(morte[0].get("reason", "dead-letter"))
        return "dead-letter"

    def fechar(self) -> None:
        with contextlib.suppress(Exception):
            self.publicador.fechar()
        for fila in (self.settings.fila, self.settings.fila_morta):
            with contextlib.suppress(Exception):
                self._canal.queue_delete(queue=fila)
        for exchange in (self.settings.exchange, self.settings.dlx):
            with contextlib.suppress(Exception):
                self._canal.exchange_delete(exchange=exchange)
        with contextlib.suppress(Exception):
            if self._conexao.is_open:
                self._conexao.close()


@unittest.skipUnless(
    os.environ.get("TEST_RABBITMQ_URL"),
    "defina TEST_RABBITMQ_URL para exercitar o contrato contra um RabbitMQ real",
)
class TestContratoBarramentoRabbitMQ(ContratoBarramentoMensagens, unittest.TestCase):
    """Exercita o contrato (TI-41 a TI-46) contra um RabbitMQ real.

    Guardada por `TEST_RABBITMQ_URL`, no mesmo estilo do `TEST_DATABASE_URL` da
    suíte destrutiva: sem a variável, é pulada, então não roda no CI puro. Herda
    os seis casos sem reescrever nenhum — só troca o ambiente.
    """

    def construir_ambiente(self) -> AmbienteBarramento:
        sufixo = f"{os.getpid()}-{next(_contador_ambiente)}"
        self._ambiente = AmbienteRabbitMQ(os.environ["TEST_RABBITMQ_URL"], sufixo)
        return self._ambiente

    def tearDown(self) -> None:
        ambiente = getattr(self, "_ambiente", None)
        if ambiente is not None:
            ambiente.fechar()


if __name__ == "__main__":
    unittest.main(verbosity=2)
