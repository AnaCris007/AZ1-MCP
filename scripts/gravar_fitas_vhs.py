"""Sessão controlada de gravação das fitas do módulo VHS (TI-59).

Este roteiro faz o que a suíte de `tests/test_integracao_vhs.py` deliberadamente
não faz: aciona os provedores **reais** uma vez cada, com massa sintética, e
guarda a interação genuína para replay posterior. É a "primeira gravação" da
tabela da Seção 6.4.3 — a única modalidade em que a rede é permitida, e apenas
dentro de uma sessão controlada como esta.

A massa é inventada aqui, e nenhum dado do parceiro sai da máquina. O áudio
enviado ao provedor de transcrição é gerado pelo próprio provedor de voz, no
primeiro passo: uma frase sintética do domínio, falada por uma voz sintética.

Ordem dos passos e o que cada um alimenta:

    1. TTS, sucesso ........... TI-11, e produz o áudio dos passos 2 e 4
    2. STT, sucesso ........... TI-06
    3. STT, sem fala .......... TI-08 (silêncio, resposta de texto vazio)
    4. STT, credencial errada . TI-07, uma das três causas
    5. Chat, sucesso .......... TI-20
    6. Embedding, sucesso ..... TI-55 e TI-59

O teto de chamadas reais é fixado no manifesto ANTES da primeira chamada, como
o item 10 do contrato exige, e a campanha para ao atingi-lo. Ao final, cada
fita é reaberta em modo `reproduzir`, com a rede bloqueada, para confirmar que
o replay devolve o mesmo conteúdo sem sair para a rede — e as gravações são
varridas em busca de credencial.

Uso:

    python scripts/gravar_fitas_vhs.py            # grava o que falta
    python scripts/gravar_fitas_vhs.py --conferir # só reproduz o que existe

Reexecutar completa o que falta dentro da campanha aberta, preservando o que
já foi gasto: o teto vale por campanha, e zerá-lo exige `--reabrir-campanha`.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

from dotenv import load_dotenv

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from tests.apoio_integracao import (  # noqa: E402 - depende do sys.path acima
    FRASE,
    IDIOMA,
    MODELO_STT,
    PERGUNTA_CHAT,
    TERMOS,
    TEXTO_EMBEDDING,
    VOZ,
    silencio,
)
from tests.vhs import (  # noqa: E402 - depende do sys.path acima
    ChaveVhs,
    Modo,
    Vhs,
    chave_chat,
    chave_embedding,
    chave_stt,
    chave_tts,
    versao_de_pacote,
)
from tests.vhs.erros import ErroVhs  # noqa: E402

FITAS = RAIZ / "tests" / "fixtures" / "vhs"
TETO_DE_CHAMADAS_REAIS = 8

# A massa sintética vive em `tests/apoio_integracao.py`, e é importada acima.
# Ela é a mesma que as suítes TI-06 em diante usam para montar a chave da fita:
# redeclarada aqui, bastaria um acento diferente entre os dois arquivos para o
# replay procurar uma gravação que esta sessão nunca fez.


class FetcherDeMemoria:
    """Entrega o áudio da massa sem tocar no armazenamento de objetos."""

    def __init__(self, conteudo: bytes) -> None:
        self._conteudo = conteudo

    def fetch(self, *, key: str) -> bytes:  # noqa: ARG002 - assinatura do Protocol
        return self._conteudo


def _chaves(audio: bytes, *, modelo_chat: str) -> dict[str, ChaveVhs]:
    # A instrução de sistema real, e não um rótulo: é ela que TI-52 exige que
    # entre na chave. Com um texto de fachada, alterar a instrução do agente
    # deixaria a chave intacta e o replay serviria a resposta antiga — que é
    # exatamente o reaproveitamento indevido que o caso existe para impedir.
    #
    # `modelo_chat` chega de fora pelo mesmo motivo. Quem decide o modelo é
    # `GEMINI_MODEL`, com queda para `DEFAULT_MODEL`; escrever um alias aqui
    # faria o manifesto declarar um modelo que não foi chamado, e trocar a
    # variável não mudaria a chave — a fita velha responderia pelo modelo novo.
    from services.gemini_service import SYSTEM_INSTRUCTION

    return {
        "tts": chave_tts(texto=FRASE, voz=VOZ, modelo="gemini-2.5-flash-preview-tts", formato="wav", cenario="sucesso"),
        "stt": chave_stt(audio=audio, idioma=IDIOMA, modelo=MODELO_STT, termos=TERMOS, cenario="sucesso"),
        "stt_sem_fala": chave_stt(
            audio=silencio(), idioma=IDIOMA, modelo=MODELO_STT, termos=TERMOS, cenario="sem-fala"
        ),
        "stt_credencial": chave_stt(
            audio=audio, idioma=IDIOMA, modelo=MODELO_STT, termos=TERMOS, cenario="credencial-invalida"
        ),
        "chat": chave_chat(
            mensagem=PERGUNTA_CHAT, instrucao=SYSTEM_INSTRUCTION, modelo=modelo_chat, cenario="sucesso"
        ),
        "embedding": chave_embedding(
            texto=TEXTO_EMBEDDING, modelo="gemini-embedding-001", dimensao=1536, cenario="sucesso"
        ),
    }


def gravar(vhs: Vhs) -> None:
    """Executa a sessão, um provedor por vez, relatando cada passo."""
    import os

    from rag.embedder import vetorizar_consulta
    from services.gemini_service import GeminiChatModel, GeminiSettings
    from services.gemini_speech_service import GeminiSpeechModel
    from services.speech_service import GenerateSpeech
    from services.transcription_service import TranscribeAudio, TranscriptionError

    gemini = os.environ["GEMINI_API_KEY"]
    deepgram = os.environ["DEEPGRAM_API_KEY"]
    ajustes_chat = GeminiSettings.from_environment()

    # 1. TTS — produz o áudio que os passos seguintes usam.
    chave_voz = chave_tts(
        texto=FRASE, voz=VOZ, modelo="gemini-2.5-flash-preview-tts", formato="wav", cenario="sucesso"
    )
    with vhs.fita(chave_voz, origem="real"):
        fala = GenerateSpeech(GeminiSpeechModel.from_api_key(gemini)).generate(FRASE, voice=VOZ)
    audio = fala.content
    print(f"  1. TTS .................. {len(audio)} bytes de WAV")

    chaves = _chaves(audio, modelo_chat=ajustes_chat.model)

    # 2. STT, sucesso.
    with vhs.fita(chaves["stt"], origem="real"):
        resultado = asyncio.run(
            TranscribeAudio(FetcherDeMemoria(audio), deepgram).transcribe(audio_id="massa", language=IDIOMA)
        )
    print(f"  2. STT sucesso .......... {resultado.text[:60]!r}")

    # 3. STT sem fala.
    with vhs.fita(chaves["stt_sem_fala"], origem="real"):
        vazio = asyncio.run(
            TranscribeAudio(FetcherDeMemoria(silencio()), deepgram).transcribe(audio_id="silencio", language=IDIOMA)
        )
    print(f"  3. STT sem fala ......... texto {vazio.text!r}")

    # 4. STT com credencial deliberadamente errada. O adaptador traduz a recusa
    #    do provedor em exceção; a fita guarda a resposta HTTP que veio.
    with vhs.fita(chaves["stt_credencial"], origem="real"):
        try:
            asyncio.run(
                TranscribeAudio(FetcherDeMemoria(audio), "chave-invalida-de-proposito").transcribe(
                    audio_id="massa", language=IDIOMA
                )
            )
            print("  4. STT credencial ....... ATENÇÃO: o provedor aceitou uma chave inválida")
        except TranscriptionError as erro:
            print(f"  4. STT credencial ....... recusado, {erro.code.value}")

    # 5. Chat.
    with vhs.fita(chaves["chat"], origem="real"):
        resposta = GeminiChatModel.from_settings(ajustes_chat).generate_reply(PERGUNTA_CHAT)
    print(f"  5. Chat ................. {resposta.texto[:60]!r}")

    # 6. Embedding.
    with vhs.fita(chaves["embedding"], origem="real"):
        vetor = vetorizar_consulta(TEXTO_EMBEDDING)
    print(f"  6. Embedding ............ {len(vetor)} dimensões")


def conferir() -> int:
    """Reexecuta cada adaptador em modo `reproduzir`, com a rede bloqueada.

    Conferir o manifesto não é conferir o replay: o hash diz que o arquivo está
    íntegro, e não que o SDK consegue ler dele. Aqui os mesmos adaptadores são
    acionados de novo, agora servidos pela fita. Qualquer tentativa de sair
    para a rede levanta `RedeBloqueada`, então um acerto aqui não pode vir do
    provedor.

    Rodar com `--conferir` satisfaz também a exigência de processo novo do item
    4 do contrato: nada do estado da gravação sobrevive entre os dois comandos.
    """
    import asyncio as _asyncio
    import os

    from rag.embedder import vetorizar_consulta
    from services.gemini_service import DEFAULT_MODEL, GeminiChatModel, GeminiSettings
    from services.gemini_speech_service import GeminiSpeechModel
    from services.speech_service import GenerateSpeech
    from services.transcription_service import TranscribeAudio, TranscriptionError

    leitor = Vhs(raiz=FITAS, modo=Modo.REPRODUZIR)
    gemini = os.environ.get("GEMINI_API_KEY", "irrelevante-no-replay")
    deepgram = os.environ.get("DEEPGRAM_API_KEY", "irrelevante-no-replay")

    # O embedding é o único passo que NÃO recebe a credencial por parâmetro:
    # `rag.embedder._cliente` a lê do ambiente por dentro e recusa subir sem
    # ela, mesmo quando nada vai à rede. Sem este `setdefault`, `--conferir`
    # quebra em qualquer lugar sem `.env` — foi assim que o pipeline do GitLab
    # falhou, e não localmente, onde o `.env` existe no disco e é carregado.
    #
    # `setdefault`, e não atribuição: numa sessão de gravação a chave real já
    # está no ambiente e é ela que deve valer. Aqui a de fachada só preenche o
    # vazio, e não chega ao provedor — quem responde é a fita.
    os.environ.setdefault("GEMINI_API_KEY", gemini)

    # Montado à mão, e não por `from_environment`, para que conferir o replay
    # não dependa de credencial: o modelo é o que importa aqui, porque é ele
    # que compõe a chave da fita, e a chave da API não chega ao provedor.
    ajustes_chat = GeminiSettings(api_key=gemini, model=os.environ.get("GEMINI_MODEL", DEFAULT_MODEL))
    falhas = 0

    def relatar(nome: str, chave: ChaveVhs, resumo: str, reproducoes: int) -> None:
        registro = leitor.manifesto.validar(chave)
        print(f"  {nome:<14} {resumo:<34} play_count={reproducoes}, origem={registro.origem}")

    try:
        # 1. TTS — o áudio reproduzido é o que dá a chave dos passos de STT.
        chave_voz = chave_tts(
            texto=FRASE, voz=VOZ, modelo="gemini-2.5-flash-preview-tts", formato="wav", cenario="sucesso"
        )
        with leitor.fita(chave_voz) as fita:
            fala = GenerateSpeech(GeminiSpeechModel.from_api_key(gemini)).generate(FRASE, voice=VOZ)
        relatar("tts", chave_voz, f"{len(fala.content)} bytes de WAV", fita.play_count)

        chaves = _chaves(fala.content, modelo_chat=ajustes_chat.model)

        with leitor.fita(chaves["stt"]) as fita:
            texto = _asyncio.run(
                TranscribeAudio(FetcherDeMemoria(fala.content), deepgram).transcribe(
                    audio_id="massa", language=IDIOMA
                )
            ).text
        relatar("stt", chaves["stt"], f"{texto[:30]!r}...", fita.play_count)

        with leitor.fita(chaves["stt_sem_fala"]) as fita:
            vazio = _asyncio.run(
                TranscribeAudio(FetcherDeMemoria(silencio()), deepgram).transcribe(
                    audio_id="silencio", language=IDIOMA
                )
            ).text
        relatar("stt_sem_fala", chaves["stt_sem_fala"], f"texto {vazio!r}", fita.play_count)

        with leitor.fita(chaves["stt_credencial"]) as fita:
            try:
                _asyncio.run(
                    TranscribeAudio(FetcherDeMemoria(fala.content), "chave-invalida-de-proposito").transcribe(
                        audio_id="massa", language=IDIOMA
                    )
                )
                recusa = "ATENÇÃO: não recusou"
            except TranscriptionError as erro:
                recusa = f"recusado, {erro.code.value}"
        relatar("stt_credencial", chaves["stt_credencial"], recusa, fita.play_count)

        with leitor.fita(chaves["chat"]) as fita:
            resposta = GeminiChatModel.from_settings(ajustes_chat).generate_reply(PERGUNTA_CHAT)
        relatar("chat", chaves["chat"], f"{resposta.texto[:30]!r}...", fita.play_count)

        with leitor.fita(chaves["embedding"]) as fita:
            vetor = vetorizar_consulta(TEXTO_EMBEDDING)
        relatar("embedding", chaves["embedding"], f"{len(vetor)} dimensões", fita.play_count)

    except ErroVhs as erro:
        falhas += 1
        print(f"  FALHOU: {type(erro).__name__}: {erro}")

    return falhas


def main() -> int:
    analisador = argparse.ArgumentParser(description=__doc__)
    analisador.add_argument("--conferir", action="store_true", help="não grava; só valida o que já existe")
    analisador.add_argument(
        "--reabrir-campanha",
        action="store_true",
        help="abre campanha nova sobre uma em andamento, devolvendo o orçamento de chamadas reais",
    )
    argumentos = analisador.parse_args()

    load_dotenv(RAIZ / ".env")

    vhs = Vhs(raiz=FITAS, modo=Modo.GRAVAR, versao_sdk=versao_de_pacote("google-genai"))

    if argumentos.conferir:
        return 1 if conferir() else 0

    # O teto entra ANTES da primeira chamada: é ele que interrompe a campanha.
    # Abrir zera o contador, e é por isso que a segunda execução NÃO abre: o
    # uso normal do roteiro é completar o que falta, e reabrir ali devolveria o
    # orçamento inteiro — o teto passaria a limitar a execução, não a campanha.
    # Continuar na campanha aberta preserva o que já foi gasto, e o item 10
    # segue valendo: esgotado o saldo, a próxima gravação é barrada.
    campanha = vhs.manifesto.campanha
    em_andamento = campanha.encerramento is None and campanha.chamadas_reais > 0

    if em_andamento and not argumentos.reabrir_campanha:
        restante = campanha.limite_chamadas_reais - campanha.chamadas_reais
        print(
            f"Campanha em andamento desde {campanha.inicio}: "
            f"{campanha.chamadas_reais} de {campanha.limite_chamadas_reais} chamadas reais gastas, "
            f"{restante} de saldo.\nSeguindo nela; use --reabrir-campanha para começar outra do zero.\n"
        )
    else:
        vhs.manifesto.abrir_campanha(
            limite_chamadas_reais=TETO_DE_CHAMADAS_REAIS,
            forcar=argumentos.reabrir_campanha,
        )
        print(f"Campanha aberta, teto de {TETO_DE_CHAMADAS_REAIS} chamadas reais.\n")

    gravar(vhs)

    print(f"\nChamadas reais gastas: {vhs.manifesto.campanha.chamadas_reais}")
    print("\nConferindo o replay, com a rede bloqueada:")
    falhas = conferir()

    achados = vhs.varredura_de_segredos()
    print(f"\nVarredura de segredos: {achados or 'nada encontrado'}")

    return 1 if falhas or achados else 0


if __name__ == "__main__":
    raise SystemExit(main())
