"""Análise e pipeline de PLN — casos TI-16 a TI-19 (Seção 6.4.4).

A rota `POST /api/v1/audio/{audio_id}/analyze` encadeia duas coisas que vivem em
mundos diferentes: a transcrição, que atravessa a rede até o Deepgram, e a
classificação, que roda em processo sobre um artefato `.joblib` carregado do
disco. O que esta suíte verifica é a JUNTA entre as duas — que o texto sai de
uma e entra na outra, e que o rótulo previsto atravessa o schema de resposta.

O trecho de transcrição vem da mesma fita de sucesso que a suíte de TI-06 usa,
pela mesma chave: é a resposta real do provedor, gravada uma vez. O modelo é
carregado do disco sem dublê nenhum, como a Seção 6.4.4 determina.

**O que esta suíte NÃO mede.** O acerto da classificação. O F1-macro do
classificador é 0,6736 contra os 0,85 do RNF03, e essa distância é assunto da
Seção 6.3, não daqui. Os casos abaixo validam a FORMA do contrato: que o rótulo
pertence ao catálogo de dez intenções da Seção 3.1, que a confiança é uma
probabilidade, e que o encadeamento não perde o texto pelo caminho. Um caso que
exigisse acerto de rótulo aqui estaria medindo o modelo com o instrumento
errado, e quebraria a cada retreino.

Execução:

    python -m unittest tests.test_integracao_analise_pln -v
"""

from __future__ import annotations

import unittest
import uuid
from unittest import mock

import pln.caminhos
from az1_api.dependencies import (
    carregar_modelo_padrao,
    get_agente,
    get_alerta_dispatcher,
    get_analyzer,
    get_chat_answerer,
    get_classificador_de_intencao,
    get_conversa_repository,
)
from services.agente_service import AgenteDesligado
from services.analysis_service import AnalyzeAudio
from services.conversa_repository import PersistenciaDesligada
from services.transcription_service import TranscribeAudio, TranscriptionResult
from tests.apoio_integracao import (
    IDIOMA,
    FetcherDeMemoria,
    audio_de_referencia,
    chave_stt_da_massa,
    cliente,
    leitor_vhs,
    limpar_overrides,
)

# Os dez rótulos técnicos da Seção 3.1. Escritos aqui, e não lidos de
# `modelo.classes_`, de propósito: lidos do próprio modelo, a asserção seria
# circular — qualquer rótulo que o modelo inventasse passaria por pertencer ao
# catálogo. É a lista do DOCUMENTO que o contrato promete.
CATALOGO_DE_INTENCOES = frozenset(
    {
        "analisar_completude_coerencia",
        "consultar_documentos_normativos",
        "consultar_projeto_sintetico",
        "fora_do_catalogo",
        "gerar_alertas_pendencias",
        "orientar_avanco_mensal",
        "orientar_entregas_cronograma",
        "orientar_mapa_beneficios",
        "orientar_riscos_problemas",
        "orientar_tap",
    }
)

# Pedido claramente fora do escopo do agente de PMO, para TI-18.
PEDIDO_FORA_DO_CATALOGO = "Me conta uma piada sobre gatos por favor"


class _DispatcherSilencioso:
    """Absorve o despacho de alertas, que é efeito colateral da rota.

    `analyze` agenda `dispatcher.despachar` como tarefa de fundo. O despachante
    real abre conexão com o banco; deixá-lo em pé aqui arrastaria a fronteira do
    PostgreSQL para dentro de uma suíte que é sobre PLN — e ela tem casos
    próprios em TI-24 a TI-29.
    """

    def __init__(self) -> None:
        self.despachos: list[dict] = []

    def despachar(self, **argumentos: object) -> None:
        self.despachos.append(argumentos)


class _TranscritorFixo:
    """Devolve um texto dado, sem tocar em provedor nenhum.

    Usado só onde a massa precisa ser outra e não há fita correspondente —
    hoje, TI-18. A origem simulada está declarada no caso, conforme a regra da
    Seção 6.4.4 para dublês.
    """

    def __init__(self, texto: str) -> None:
        self._texto = texto

    async def transcribe(self, *, audio_id: str, language: str = IDIOMA) -> TranscriptionResult:
        return TranscriptionResult(
            text=self._texto, language=language, confidence=0.99, duration_seconds=2.0
        )


class TestAnaliseIntegracao(unittest.TestCase):
    """TI-16 a TI-19."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.audio = audio_de_referencia()
        cls.modelo = carregar_modelo_padrao()

    def tearDown(self) -> None:
        limpar_overrides()

    def _analisar(self, analisador: AnalyzeAudio, *, audio_id: str = "aud_massa"):
        http = cliente(
            {
                get_analyzer: lambda: analisador,
                get_alerta_dispatcher: _DispatcherSilencioso,
            }
        )
        return http.post(f"/api/v1/audio/{audio_id}/analyze?language={IDIOMA}")

    def _analisador_com_fita(self) -> AnalyzeAudio:
        return AnalyzeAudio(
            transcriber=TranscribeAudio(FetcherDeMemoria(self.audio), "irrelevante-no-replay"),
            modelo=self.modelo,
        )

    # -- TI-16 ---------------------------------------------------------------

    def test_transcricao_recebe_intencao_do_catalogo(self) -> None:
        """O texto transcrito chega ao classificador e volta como rótulo válido."""
        with leitor_vhs().fita(chave_stt_da_massa(self.audio, cenario="sucesso")) as fita:
            resposta = self._analisar(self._analisador_com_fita())

        self.assertEqual(resposta.status_code, 200)
        corpo = resposta.json()

        # O encadeamento preservou o texto da transcrição.
        self.assertTrue(corpo["text"].strip())
        self.assertEqual(corpo["language"], "pt-BR")
        self.assertGreater(corpo["duration_seconds"], 0)

        # E acrescentou a classificação.
        self.assertIn(corpo["intencao"], CATALOGO_DE_INTENCOES)
        self.assertNotRegex(
            corpo["intencao"],
            r"^INT-\d+$",
            "o contrato devolve o rótulo técnico, não o código INT-nn da Seção 3.1",
        )
        self.assertGreaterEqual(corpo["confianca_pln"], 0.0)
        self.assertLessEqual(corpo["confianca_pln"], 1.0)
        self.assertEqual(fita.play_count, 1)

    # -- TI-17 ---------------------------------------------------------------

    def test_texto_digitado_e_transcrito_produzem_a_mesma_intencao(self) -> None:
        """Caracterização: `/chat` classifica, mas não devolve a intenção.

        O planejamento registrou este caso como dependente de implementação, e
        ele continua sendo. O que mudou desde então é que `/chat` passou a
        classificar a mensagem — só que como OBSERVADOR: o rótulo vai para
        `auditoria.mensagem.intencao` e não aparece no corpo da resposta
        (`src/routes/chat.py`, `classificar_sem_interferir`).

        Então o que se pode afirmar hoje, e o que este caso afirma, é: (a) o
        pipeline de classificação é o MESMO nos dois caminhos, porque os dois
        resolvem `carregar_modelo_padrao`; (b) o contrato de `/chat` não expõe
        `intencao`, e portanto a igualdade pedida pelo planejamento não é
        observável pela API. Afirmar mais que isso seria inventar um contrato.
        """
        from az1_api.dependencies import get_classificador_de_intencao as fabrica

        # (a) mesmo pipeline nos dois caminhos.
        classificador = fabrica()
        self.assertIsNotNone(classificador, "o modelo precisa estar carregado para o ensaio")

        with leitor_vhs().fita(chave_stt_da_massa(self.audio, cenario="sucesso")):
            resposta_audio = self._analisar(self._analisador_com_fita())
        self.assertEqual(resposta_audio.status_code, 200)
        texto_transcrito = resposta_audio.json()["text"]

        rotulo_direto, _ = classificador(texto_transcrito)
        self.assertEqual(
            rotulo_direto,
            resposta_audio.json()["intencao"],
            "a rota e a chamada direta usam o mesmo modelo; divergir aqui seria dois pipelines",
        )

        # (b) o contrato de /chat não expõe a intenção.
        http = cliente(
            {
                get_chat_answerer: lambda: _AnswerFixo("resposta qualquer"),
                get_conversa_repository: lambda: PersistenciaDesligada("teste"),
                get_classificador_de_intencao: lambda: None,
                get_agente: lambda: AgenteDesligado("teste"),
            }
        )
        resposta_chat = http.post(
            "/api/v1/chat",
            json={"message": texto_transcrito, "conversation_id": str(uuid.uuid4())},
        )
        self.assertEqual(resposta_chat.status_code, 200)
        self.assertNotIn(
            "intencao",
            resposta_chat.json(),
            "se /chat passar a devolver intenção, este caso deve virar a comparação que o plano previu",
        )

    # -- TI-18 ---------------------------------------------------------------

    def test_solicitacao_fora_do_catalogo_retorna_intencao_valida(self) -> None:
        """Pedido fora do escopo recebe o rótulo `fora_do_catalogo`.

        A transcrição é SIMULADA aqui, e não vem de fita: não há gravação de um
        áudio fora do catálogo, e produzir uma custaria uma chamada real ao
        provedor para exercitar uma fronteira — a do classificador — que não
        depende dela. A origem simulada fica declarada, como a Seção 6.4.4 exige
        dos dublês.
        """
        analisador = AnalyzeAudio(
            transcriber=_TranscritorFixo(PEDIDO_FORA_DO_CATALOGO), modelo=self.modelo
        )

        resposta = self._analisar(analisador)

        self.assertEqual(resposta.status_code, 200)
        corpo = resposta.json()
        self.assertIn(corpo["intencao"], CATALOGO_DE_INTENCOES)
        self.assertEqual(corpo["intencao"], "fora_do_catalogo")

    # -- TI-19 ---------------------------------------------------------------

    def test_modelo_ausente_falha_na_composicao(self) -> None:
        """Sem o `.joblib`, a composição falha e a requisição sai como 500.

        O cache de composição é limpo antes do ensaio, como a ficha do caso
        pede: `carregar_modelo_padrao` e `get_analyzer` são `lru_cache`, e sem
        limpar o modelo já carregado responderia por um arquivo que o teste
        acabou de esconder.

        Não se exige falha na subida da aplicação: a dependência é preguiçosa,
        e o `.joblib` só é procurado na primeira requisição que precisa dele.
        """
        ausente = pln.caminhos.MODELO_PADRAO.with_name("classificador-que-nao-existe.joblib")
        self.assertFalse(ausente.exists(), "o ensaio depende de o arquivo realmente não existir")

        carregar_modelo_padrao.cache_clear()
        get_analyzer.cache_clear()
        try:
            with mock.patch.object(pln.caminhos, "MODELO_PADRAO", ausente):
                # A composição falha por si só...
                with self.assertRaises(Exception):
                    carregar_modelo_padrao()

                # ...e, acionada por requisição, sai pelo manipulador global.
                http = cliente({get_alerta_dispatcher: _DispatcherSilencioso})
                resposta = http.post(f"/api/v1/audio/aud_massa/analyze?language={IDIOMA}")

            self.assertEqual(resposta.status_code, 500)
            self.assertEqual(resposta.json()["error"], "internal_error")
        finally:
            # Devolve o processo ao estado anterior: as próximas suítes contam
            # com o modelo de verdade carregado.
            carregar_modelo_padrao.cache_clear()
            get_analyzer.cache_clear()


class _AnswerFixo:
    """Responde sempre o mesmo, sem provedor. Só para o ramo (b) de TI-17."""

    def __init__(self, texto: str) -> None:
        self._texto = texto

    def answer(self, message: str, conversation_id: str | None = None):
        from services.chat_service import ChatReply

        return ChatReply(text=self._texto)


if __name__ == "__main__":
    unittest.main()
