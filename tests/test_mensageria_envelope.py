"""Round-trip do envelope canônico no barramento.

Serializar e desserializar precisam ser inversas exatas: os seis campos do
`EventoWebhook` que o produtor grava têm de chegar idênticos ao consumidor. O
que mais fácil se perde nesse trânsito é a `marca_de_tempo` com fuso — um
descuido a transforma em datetime ingênuo do outro lado — e a `versao`, sem a
qual o consumidor não sabe interpretar a mensagem. Estes testes fecham as duas
portas, além de exigir que um payload corrompido levante em vez de devolver um
envelope pela metade.
"""

from __future__ import annotations

import unittest
from datetime import UTC, datetime, timedelta, timezone

from mensageria.envelope import EnvelopeInvalido, desserializar, serializar
from services.webhook_service import VERSAO_ENVELOPE, EventoWebhook


class TesteEnvelopeRoundTrip(unittest.TestCase):
    def _evento(self, **overrides) -> EventoWebhook:
        base = {
            "identificador": "microsoft_graph:evt-1",
            "tipo": "graph.updated",
            "versao": VERSAO_ENVELOPE,
            "marca_de_tempo": datetime(2026, 9, 21, 14, 30, 15, tzinfo=UTC),
            "correlacao": "sub-123",
            "conteudo": {"item": 42, "aninhado": {"a": [1, 2, 3], "b": "texto"}},
        }
        base.update(overrides)
        return EventoWebhook(**base)  # type: ignore[arg-type]

    def test_round_trip_preserva_os_seis_campos(self) -> None:
        original = self._evento()

        recuperado = desserializar(serializar(original))

        self.assertEqual(recuperado, original)
        self.assertEqual(recuperado.identificador, original.identificador)
        self.assertEqual(recuperado.tipo, original.tipo)
        self.assertEqual(recuperado.versao, original.versao)
        self.assertEqual(recuperado.marca_de_tempo, original.marca_de_tempo)
        self.assertEqual(recuperado.correlacao, original.correlacao)
        self.assertEqual(recuperado.conteudo, original.conteudo)

    def test_versao_preservada(self) -> None:
        original = self._evento(versao="7")

        recuperado = desserializar(serializar(original))

        self.assertEqual(recuperado.versao, "7")

    def test_datetime_tz_aware_preservado(self) -> None:
        # Fuso diferente de UTC: se a serialização perdesse o deslocamento, a
        # comparação de instantes falharia ou o datetime voltaria ingênuo.
        fuso = timezone(timedelta(hours=-3))
        original = self._evento(marca_de_tempo=datetime(2026, 9, 21, 11, 30, 15, tzinfo=fuso))

        recuperado = desserializar(serializar(original))

        self.assertIsNotNone(recuperado.marca_de_tempo.tzinfo)
        self.assertEqual(recuperado.marca_de_tempo, original.marca_de_tempo)
        self.assertEqual(recuperado.marca_de_tempo.utcoffset(), timedelta(hours=-3))

    def test_conteudo_aninhado_preservado(self) -> None:
        original = self._evento(
            conteudo={"lista": [{"x": 1}, {"y": [True, None, "s"]}], "n": 3.14}
        )

        recuperado = desserializar(serializar(original))

        self.assertEqual(recuperado.conteudo, original.conteudo)

    def test_payload_corrompido_levanta(self) -> None:
        with self.assertRaises(EnvelopeInvalido):
            desserializar(b"isto nao e json")

    def test_payload_incompleto_levanta(self) -> None:
        # JSON válido, mas sem os campos do envelope.
        with self.assertRaises(EnvelopeInvalido):
            desserializar(b'{"identificador": "x"}')

    def test_marca_de_tempo_invalida_levanta(self) -> None:
        with self.assertRaises(EnvelopeInvalido):
            desserializar(
                b'{"identificador":"x","tipo":"t","versao":"1",'
                b'"marca_de_tempo":"nao-e-data","correlacao":"c","conteudo":{}}'
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
