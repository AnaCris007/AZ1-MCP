"""Suíte de contrato do barramento de mensagens — casos TI-41 a TI-46.

Mesma estratégia que a Seção 6.4 abre para os webhooks, e pelo mesmo motivo: a
tecnologia do barramento ainda não foi escolhida. `ContratoBarramentoMensagens`
descreve o comportamento exigido de QUALQUER intermediário, sem citar nenhum, e
tem um único ponto de extensão — o método de fábrica `construir_ambiente`.
Exercitada aqui contra um intermediário determinístico em memória; quando a
tecnologia for selecionada, uma nova subclasse injeta o adaptador real e herda
os mesmos casos, sem reescrever nenhum.

É exatamente o caminho que `ContratoWebhookInbound` já percorreu: escrito na
Sprint 4 contra um dublê, hoje reexecutado sem alteração contra o Microsoft
Graph, o Google Drive e o PostgreSQL. O valor de escrever o contrato antes do
adaptador é esse — quando o barramento chegar, o que se discute é o adaptador,
não o que se espera dele.

**Colisão de identificadores, registrada.** `TI-41` e `TI-42` aparecem em dois
lugares do catálogo: aqui, como os dois primeiros casos de mensageria, e em
`tests/test_integracao_contrato_webhook.py`, onde foram acrescentados na Sprint
4 para cobrir lote de mudanças — situação que a Seção 6.4.4 não previa. A
Seção 5.2 do `docs/Projeto.md` já registra a duplicidade. Os dois pares
coexistem e não se substituem: aprovar os de webhook não aprova os daqui.

**O que estes casos provam, e o que não provam.** Provam que o contrato está
escrito, é coerente e é satisfazível — um intermediário em memória o cumpre
inteiro. NÃO provam nada sobre um barramento real: entrega em ordem parcial,
particionamento, latência e semântica de confirmação variam por produto, e é
para isso que existe o ponto de extensão.

Execução:

    python -m unittest tests.test_integracao_contrato_mensageria -v

Não requer infraestrutura.
"""

from __future__ import annotations

import json
import unittest
import uuid
from abc import ABC, abstractmethod
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime

# O envelope da Seção 6.4.4: seis campos, nem mais nem menos. `versao` existe
# para que um consumidor antigo possa recusar um formato novo em vez de
# interpretá-lo errado, e `correlacao` é o que liga a mensagem ao turno de
# conversa que a originou — sem ele, a trilha de auditoria perde o vínculo.
CAMPOS_DO_ENVELOPE = ("identificador", "tipo", "versao", "marca_de_tempo", "correlacao", "conteudo")

TIPO_CONHECIDO = "pendencia.vencida"
LIMITE_DE_TENTATIVAS = 3


@dataclass(frozen=True)
class Envelope:
    identificador: str
    tipo: str
    versao: str
    marca_de_tempo: str
    correlacao: str
    conteudo: dict

    def como_dicionario(self) -> dict:
        return {campo: getattr(self, campo) for campo in CAMPOS_DO_ENVELOPE}


@dataclass
class Entregue:
    """Uma mensagem entregue ao consumidor, com o contador de tentativas."""

    envelope: Envelope
    tentativa: int


class BarramentoIndisponivel(RuntimeError):
    """O produtor não conseguiu publicar. Nunca é silencioso — é o TI-46."""


class AmbienteBarramento(ABC):
    """O que uma implementação precisa oferecer para ser exercitada.

    Deliberadamente pequeno: publicar, consumir, inspecionar a fila de mortas e
    provocar indisponibilidade. Um contrato que exigisse mais estaria
    descrevendo um produto, e não o comportamento comum a todos eles.
    """

    @abstractmethod
    def publicar(self, envelope: Envelope) -> None: ...

    @abstractmethod
    def consumir(self, processar: Callable[[Entregue], None], *, quantidade: int = 1) -> int:
        """Entrega até `quantidade` mensagens. Devolve quantas foram processadas.

        Exceção levantada por `processar` significa recusa: a mensagem volta
        para a fila. Retorno normal significa confirmação.
        """

    @abstractmethod
    def publicar_bruto(self, bruto: bytes) -> None:
        """Enfileira sem passar pelo envelope — a massa de payload inválido.

        Faz parte do contrato, e não só do dublê: TI-43 exige que um payload
        indesserializável seja isolado de imediato, e sem uma porta para
        publicar lixo não há como exercitar isso contra o barramento real.
        """

    @abstractmethod
    def mensagens_mortas(self) -> Sequence[tuple[Envelope, str]]: ...

    @abstractmethod
    def pendentes(self) -> int: ...

    @abstractmethod
    def derrubar(self) -> None: ...

    def envelope(self, *, tipo: str = TIPO_CONHECIDO, identificador: str | None = None, **conteudo) -> Envelope:
        return Envelope(
            identificador=identificador or f"msg-{uuid.uuid4().hex[:8]}",
            tipo=tipo,
            versao="1",
            marca_de_tempo=datetime.now(UTC).isoformat(),
            correlacao=f"conv-{uuid.uuid4().hex[:8]}",
            conteudo=dict(conteudo) or {"projeto": "SYN-04"},
        )


class ContratoBarramentoMensagens:
    """TI-41 a TI-46. Sem herdar `TestCase`: quem herda é a subclasse concreta.

    O mesmo arranjo de `ContratoWebhookInbound` — assim a classe de contrato não
    é coletada pelo descobridor como suíte solta, e cada ambiente decide quando
    exercitá-la.
    """

    def construir_ambiente(self) -> AmbienteBarramento:
        raise NotImplementedError

    def setUp(self) -> None:
        self.ambiente = self.construir_ambiente()

    # -- TI-41 ---------------------------------------------------------------

    def test_publica_e_consome_o_envelope_integro(self) -> None:
        """Os seis campos do envelope chegam ao consumidor preservados."""
        publicado = self.ambiente.envelope(projeto="SYN-04", pendencia=17)
        self.ambiente.publicar(publicado)

        recebidos: list[Envelope] = []
        processadas = self.ambiente.consumir(lambda e: recebidos.append(e.envelope))

        self.assertEqual(processadas, 1)
        self.assertEqual(len(recebidos), 1)
        self.assertEqual(
            recebidos[0].como_dicionario(),
            publicado.como_dicionario(),
            "o envelope chegou diferente do que foi publicado",
        )
        # E nenhum campo do contrato se perdeu no caminho.
        for campo in CAMPOS_DO_ENVELOPE:
            self.assertIsNotNone(getattr(recebidos[0], campo, None), f"campo {campo} ausente")

    # -- TI-42 ---------------------------------------------------------------

    def test_confirmacao_remove_e_recusa_devolve_a_mensagem(self) -> None:
        """Confirmada não volta; recusada volta para a fila.

        As duas metades no mesmo caso porque é a diferença entre elas que
        importa: um barramento que removesse a mensagem antes do processamento
        passaria na primeira e perderia a segunda em silêncio.
        """
        confirmada = self.ambiente.envelope(identificador="msg-ok")
        self.ambiente.publicar(confirmada)
        self.ambiente.consumir(lambda _e: None)
        self.assertEqual(self.ambiente.pendentes(), 0, "mensagem confirmada continuou na fila")

        recusada = self.ambiente.envelope(identificador="msg-recusada")
        self.ambiente.publicar(recusada)

        def explodir(_entregue: Entregue) -> None:
            raise RuntimeError("consumidor falhou (simulado)")

        self.ambiente.consumir(explodir)
        self.assertEqual(self.ambiente.pendentes(), 1, "mensagem recusada não voltou para a fila")

        # E, de volta na fila, ela continua entregável.
        vistas: list[str] = []
        self.ambiente.consumir(lambda e: vistas.append(e.envelope.identificador))
        self.assertEqual(vistas, ["msg-recusada"])

    # -- TI-43 ---------------------------------------------------------------

    def test_falha_persistente_vai_para_dead_letter(self) -> None:
        """Contador cresce a cada reentrega; no limite, a mensagem é isolada.

        E a fila principal segue processando — é a parte que separa "isolar a
        mensagem ruim" de "parar por causa dela".
        """
        problematica = self.ambiente.envelope(identificador="msg-ruim")
        self.ambiente.publicar(problematica)

        tentativas: list[int] = []

        def sempre_reprova(entregue: Entregue) -> None:
            tentativas.append(entregue.tentativa)
            raise RuntimeError("processamento reprovou (simulado)")

        for _ in range(LIMITE_DE_TENTATIVAS):
            self.ambiente.consumir(sempre_reprova)

        self.assertEqual(
            tentativas,
            list(range(1, LIMITE_DE_TENTATIVAS + 1)),
            "o contador de tentativas não acompanhou as reentregas",
        )
        mortas = self.ambiente.mensagens_mortas()
        self.assertEqual(len(mortas), 1)
        self.assertEqual(mortas[0][0].identificador, "msg-ruim")
        self.assertTrue(mortas[0][1], "a causa precisa ficar registrada junto da mensagem morta")
        self.assertEqual(self.ambiente.pendentes(), 0)

        # A fila principal não ficou travada pela mensagem isolada.
        boa = self.ambiente.envelope(identificador="msg-boa")
        self.ambiente.publicar(boa)
        entregues: list[str] = []
        self.assertEqual(self.ambiente.consumir(lambda e: entregues.append(e.envelope.identificador)), 1)
        self.assertEqual(entregues, ["msg-boa"])

    def test_payload_indesserializavel_vai_direto_para_dead_letter(self) -> None:
        """A segunda causa de TI-43: sem reentrega, porque não há o que tentar.

        Reentregar um payload que não desserializa é gastar o orçamento de
        tentativas com algo que nunca vai mudar. O contrato manda isolar de
        imediato.
        """
        self.ambiente.publicar_bruto(b"{isto nao e json valido")

        self.ambiente.consumir(lambda _e: None)

        mortas = self.ambiente.mensagens_mortas()
        self.assertEqual(len(mortas), 1)
        self.assertIn("desserial", mortas[0][1].lower())
        self.assertEqual(self.ambiente.pendentes(), 0)

    # -- TI-44 ---------------------------------------------------------------

    def test_consumo_duplicado_produz_efeito_unico(self) -> None:
        """A mesma mensagem processada duas vezes aplica o efeito uma vez.

        A deduplicação é do CONSUMIDOR, e não do barramento: entrega ao menos
        uma vez é o que quase todo produto oferece, e exigir exatamente uma vez
        do intermediário restringiria a escolha sem necessidade. O que o
        contrato exige é que o identificador seja estável o bastante para o
        consumidor reconhecer a repetição.
        """
        envelope = self.ambiente.envelope(identificador="msg-repetida")
        efeitos: list[str] = []
        aplicados: set[str] = set()

        def processar_idempotente(entregue: Entregue) -> None:
            if entregue.envelope.identificador in aplicados:
                return
            aplicados.add(entregue.envelope.identificador)
            efeitos.append(entregue.envelope.identificador)

        self.ambiente.publicar(envelope)
        self.ambiente.consumir(processar_idempotente)
        self.ambiente.publicar(envelope)
        self.ambiente.consumir(processar_idempotente)

        self.assertEqual(efeitos, ["msg-repetida"], "o efeito foi aplicado mais de uma vez")

    # -- TI-45 ---------------------------------------------------------------

    def test_consumidor_nao_depende_de_ordem_global(self) -> None:
        """Publicadas fora de ordem, todas são processadas corretamente.

        O consumidor ordena pelo que está DENTRO do envelope — aqui, a marca de
        tempo —, e não pela ordem de chegada. Um consumidor que dependesse da
        ordem da fila quebraria no primeiro barramento particionado.
        """
        fora_de_ordem = [
            self.ambiente.envelope(identificador="msg-3", sequencia=3),
            self.ambiente.envelope(identificador="msg-1", sequencia=1),
            self.ambiente.envelope(identificador="msg-2", sequencia=2),
        ]
        for envelope in fora_de_ordem:
            self.ambiente.publicar(envelope)

        recebidos: list[Envelope] = []
        self.ambiente.consumir(lambda e: recebidos.append(e.envelope), quantidade=3)

        self.assertEqual(len(recebidos), 3, "nem todas as mensagens foram processadas")
        self.assertEqual(
            {e.identificador for e in recebidos},
            {"msg-1", "msg-2", "msg-3"},
            "alguma mensagem se perdeu por ter chegado fora de ordem",
        )
        # E o consumidor consegue reconstruir a ordem pelo conteúdo.
        por_sequencia = sorted(recebidos, key=lambda e: e.conteudo["sequencia"])
        self.assertEqual([e.identificador for e in por_sequencia], ["msg-1", "msg-2", "msg-3"])

    # -- TI-46 ---------------------------------------------------------------

    def test_indisponibilidade_na_publicacao_e_reportada(self) -> None:
        """Barramento fora do ar: erro explícito ao produtor, sem perda silenciosa.

        O ponto é o "sem perda silenciosa". Um `publicar` que engolisse a falha
        e devolvesse `None` deixaria o produtor achando que a mensagem está a
        caminho — e o alerta que ela carregava simplesmente nunca chegaria.
        """
        self.ambiente.derrubar()
        envelope = self.ambiente.envelope(identificador="msg-perdida")

        with self.assertRaises(BarramentoIndisponivel):
            self.ambiente.publicar(envelope)

        self.assertEqual(self.ambiente.pendentes(), 0, "a mensagem não pode ter sido enfileirada")
        self.assertEqual(self.ambiente.mensagens_mortas(), [])


# ---------------------------------------------------------------------------
# Intermediário em memória
# ---------------------------------------------------------------------------


@dataclass
class _NaFila:
    bruto: bytes
    tentativas: int = 0


class BarramentoEmMemoria(AmbienteBarramento):
    """Intermediário determinístico, com o mínimo que o contrato exige.

    Não imita produto nenhum de propósito: imitar o RabbitMQ aqui faria o
    contrato herdar decisões dele, e a subclasse do barramento escolhido teria
    de desfazê-las.
    """

    def __init__(self) -> None:
        self._fila: list[_NaFila] = []
        self._mortas: list[tuple[Envelope, str]] = []
        self._no_ar = True

    def publicar(self, envelope: Envelope) -> None:
        if not self._no_ar:
            raise BarramentoIndisponivel("barramento inacessível (simulado)")
        self._fila.append(_NaFila(bruto=json.dumps(envelope.como_dicionario()).encode()))

    def publicar_bruto(self, bruto: bytes) -> None:
        """Enfileira sem passar pelo envelope — a massa de payload inválido."""
        if not self._no_ar:
            raise BarramentoIndisponivel("barramento inacessível (simulado)")
        self._fila.append(_NaFila(bruto=bruto))

    def consumir(self, processar: Callable[[Entregue], None], *, quantidade: int = 1) -> int:
        processadas = 0
        for _ in range(quantidade):
            if not self._fila:
                break
            item = self._fila.pop(0)
            item.tentativas += 1

            try:
                envelope = self._desserializar(item.bruto)
            except ValueError as erro:
                # Indesserializável não ganha reentrega: não há o que mudar.
                self._mortas.append((self._envelope_ilegivel(item.bruto), f"falha ao desserializar: {erro}"))
                continue

            try:
                processar(Entregue(envelope=envelope, tentativa=item.tentativas))
            except Exception as erro:  # noqa: BLE001 — recusa do consumidor é caso previsto
                if item.tentativas >= LIMITE_DE_TENTATIVAS:
                    self._mortas.append((envelope, f"limite de tentativas: {erro}"))
                else:
                    self._fila.append(item)
                continue

            processadas += 1
        return processadas

    def mensagens_mortas(self) -> Sequence[tuple[Envelope, str]]:
        return list(self._mortas)

    def pendentes(self) -> int:
        return len(self._fila)

    def derrubar(self) -> None:
        self._no_ar = False

    @staticmethod
    def _desserializar(bruto: bytes) -> Envelope:
        try:
            dados = json.loads(bruto)
        except json.JSONDecodeError as erro:
            raise ValueError(str(erro)) from erro
        faltando = [campo for campo in CAMPOS_DO_ENVELOPE if campo not in dados]
        if faltando:
            raise ValueError(f"campos ausentes no envelope: {', '.join(faltando)}")
        return Envelope(**{campo: dados[campo] for campo in CAMPOS_DO_ENVELOPE})

    @staticmethod
    def _envelope_ilegivel(bruto: bytes) -> Envelope:
        """Um envelope de fachada para a fila de mortas guardar o que chegou.

        Descartar o corpo ilegível seria perder justamente a evidência de que
        alguém publicou algo fora do contrato.
        """
        return Envelope(
            identificador="(ilegível)",
            tipo="(ilegível)",
            versao="(ilegível)",
            marca_de_tempo=datetime.now(UTC).isoformat(),
            correlacao="(ilegível)",
            conteudo={"bruto": bruto.decode("utf-8", errors="replace")},
        )


class TestContratoBarramentoEmMemoria(ContratoBarramentoMensagens, unittest.TestCase):
    """Exercita o contrato contra o intermediário em memória (TI-41 a TI-46)."""

    def construir_ambiente(self) -> AmbienteBarramento:
        return BarramentoEmMemoria()


if __name__ == "__main__":
    unittest.main()
