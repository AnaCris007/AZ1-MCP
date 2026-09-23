"""Módulo VHS contra os SDKs reais — casos TI-59 a TI-61 (Seção 6.4.4).

Esta suíte fecha a parte que a Sprint 4 deixou aberta. `tests/test_integracao_vhs.py`
já provava o HARNESS — chave, validade, sanitização, ausência de rede, os quatro
modos — contra um servidor HTTP sintético. O que faltava, e é o que está aqui, é
o replay de gravações dos provedores de verdade: Deepgram e Google, alcançados
pelo transporte `httpx` que os dois SDKs constroem por baixo.

As gravações vieram da sessão controlada de `scripts/gravar_fitas_vhs.py`, com
teto de chamadas reais fixado no manifesto antes da primeira chamada (item 10 do
contrato da Seção 6.4.3). Nenhum caso desta suíte grava fita: todos rodam em
modo `reproduzir`, com a rede bloqueada.

**O que estes casos provam, e o que não provam.** Provam que a interação
gravada é real, que está sanitizada, que o replay devolve o mesmo conteúdo sem
sair para a rede, e que uma mudança de modelo, idioma ou instrução invalida a
gravação em vez de reaproveitá-la. NÃO provam que o contrato do provedor hoje é
o que está na fita — para isso existe o smoke real do item 10, que depende de
sessão com credencial e não roda em CI. Aprovar replay antigo não aprova o
provedor atual, e a Seção 6.4.3 já dizia isso.

Execução:

    python -m unittest tests.test_integracao_vhs_provedores -v
"""

from __future__ import annotations

import asyncio
import shutil
import tempfile
import unittest
from datetime import timedelta
from pathlib import Path

from tests.apoio_integracao import (
    DIMENSAO_EMBEDDING,
    FITAS,
    FRASE,
    IDIOMA,
    MODELO_STT,
    MODELO_TTS,
    PERGUNTA_CHAT,
    TERMOS,
    TEXTO_EMBEDDING,
    VOZ,
    FetcherDeMemoria,
    audio_de_referencia,
    chave_chat_da_massa,
    chave_embedding_da_massa,
    chave_stt_da_massa,
    chave_tts_da_massa,
    embedding_sem_cache,
    leitor_vhs,
    modelo_de_chat,
    silencio,
)
from tests.vhs import ChaveVhs, Modo, Vhs, chave_stt
from tests.vhs.erros import RegistroAusente, RegistroCorrompido, RegistroVencido
from tests.vhs.manifesto import Manifesto, agora_utc
from tests.vhs.sanitizacao import varrer_segredos

CHAVE_IRRELEVANTE = "irrelevante-no-replay"

# Marcadores sintéticos que TI-61 procura nas gravações. Nenhum é um segredo de
# verdade: são as FORMAS que um segredo teria, e achá-las no arquivo significa
# que a sanitização deixou passar aquela categoria.
NOMES_PROIBIDOS = ("authorization", "x-goog-api-key", "set-cookie", "cookie", "api-key")


def _reproduzir_tts(vhs: Vhs) -> tuple[bytes, int]:
    from services.gemini_speech_service import GeminiSpeechModel
    from services.speech_service import GenerateSpeech

    with vhs.fita(chave_tts_da_massa()) as fita:
        fala = GenerateSpeech(
            GeminiSpeechModel.from_api_key(CHAVE_IRRELEVANTE, MODELO_TTS)
        ).generate(FRASE, voice=VOZ)
    return fala.content, fita.play_count


def _reproduzir_stt(vhs: Vhs, audio: bytes, *, cenario: str) -> tuple[str, int]:
    from services.transcription_service import TranscribeAudio

    with vhs.fita(chave_stt_da_massa(audio, cenario=cenario)) as fita:
        resultado = asyncio.run(
            TranscribeAudio(FetcherDeMemoria(audio), CHAVE_IRRELEVANTE).transcribe(
                audio_id="massa", language=IDIOMA
            )
        )
    return resultado.text, fita.play_count


def _reproduzir_chat(vhs: Vhs) -> tuple[str, int]:
    from services.gemini_service import GeminiChatModel, GeminiSettings

    with vhs.fita(chave_chat_da_massa()) as fita:
        resposta = GeminiChatModel.from_settings(
            GeminiSettings(api_key=CHAVE_IRRELEVANTE, model=modelo_de_chat())
        ).generate_reply(PERGUNTA_CHAT)
    return resposta.texto, fita.play_count


def _reproduzir_embedding(vhs: Vhs) -> tuple[int, int]:
    from rag.embedder import vetorizar_consulta

    with embedding_sem_cache(), vhs.fita(chave_embedding_da_massa()) as fita:
        vetor = vetorizar_consulta(TEXTO_EMBEDDING)
    return len(vetor), fita.play_count


class TestVhsProvedoresIntegracao(unittest.TestCase):
    """TI-59 a TI-61."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.audio = audio_de_referencia()

    def setUp(self) -> None:
        self.vhs = leitor_vhs()

    # -- TI-59 ---------------------------------------------------------------

    def test_gravacoes_dos_dois_sdks_reproduzem_sem_rede(self) -> None:
        """Cada SDK reproduz sua gravação real, e o `play_count` incrementa.

        A rede está bloqueada pelo módulo VHS durante todo o bloco: um replay
        que precisasse sair para o provedor levantaria `RedeBloqueada` em vez de
        passar. É essa a medida de "zero novas chamadas" que o item 4 do
        contrato pede, e ela é independente do `play_count`.
        """
        # Google, síntese de fala.
        audio, reproducoes = _reproduzir_tts(self.vhs)
        self.assertTrue(audio.startswith(b"RIFF"))
        self.assertEqual(reproducoes, 1)

        # Deepgram, transcrição.
        texto, reproducoes = _reproduzir_stt(self.vhs, self.audio, cenario="sucesso")
        self.assertTrue(texto.strip())
        self.assertEqual(reproducoes, 1)

        # Google, chat.
        resposta, reproducoes = _reproduzir_chat(self.vhs)
        self.assertTrue(resposta.strip())
        self.assertEqual(reproducoes, 1)

        # Google, embedding — a dimensão é a que o RAG espera.
        dimensao, reproducoes = _reproduzir_embedding(self.vhs)
        self.assertEqual(dimensao, DIMENSAO_EMBEDDING)
        self.assertEqual(reproducoes, 1)

    def test_manifesto_declara_origem_real_para_cada_gravacao(self) -> None:
        """Toda fita versionada é interação genuína, e está dentro do prazo.

        `origem` distingue gravação real de fixture escrita à mão. A Seção 6.4.3
        é explícita: "uma fixture escrita manualmente é simulada, não uma
        gravação real", e um replay de fixture não prova contrato de provedor
        nenhum. Este caso é o que impede que uma entre no lugar de outra.
        """
        chaves = {
            "TTS": chave_tts_da_massa(),
            "STT sucesso": chave_stt_da_massa(self.audio, cenario="sucesso"),
            "STT sem fala": chave_stt_da_massa(silencio(), cenario="sem-fala"),
            "STT credencial inválida": chave_stt_da_massa(
                self.audio, cenario="credencial-invalida"
            ),
            "chat": chave_chat_da_massa(),
            "embedding": chave_embedding_da_massa(),
        }

        for nome, chave in chaves.items():
            with self.subTest(fita=nome):
                registro = self.vhs.manifesto.validar(chave)
                self.assertEqual(registro.origem, "real", f"{nome} não é gravação real")
                self.assertTrue(registro.sha256)
                self.assertTrue(registro.versao_sdk)
                self.assertFalse(registro.temporario, "temporário não deve chegar ao commit")

    def test_reproducao_funciona_em_processo_novo(self) -> None:
        """Item 4 do contrato: o replay não depende da memória da gravação.

        Roda o conferidor do roteiro de gravação em subprocesso. Se alguma fita
        dependesse de estado deixado na sessão que a gravou, funcionaria aqui
        dentro e falharia lá — que é justamente o que o item exige descartar.
        """
        import subprocess
        import sys

        resultado = subprocess.run(
            [sys.executable, "scripts/gravar_fitas_vhs.py", "--conferir"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).resolve().parent.parent,
            timeout=180,
        )

        self.assertEqual(
            resultado.returncode,
            0,
            f"o conferidor falhou em processo novo:\n{resultado.stdout}\n{resultado.stderr}",
        )
        self.assertIn("origem=real", resultado.stdout)

    # -- TI-60 ---------------------------------------------------------------

    def test_erro_http_gravado_reproduz_e_vira_o_status_da_rota(self) -> None:
        """A recusa real do provedor é reproduzida e traduzida pelo contrato.

        A fita `credencial-invalida` guarda o 401 que o Deepgram devolveu a uma
        chave deliberadamente errada. Aqui ela é reproduzida sem rede, e o que
        se verifica é a tradução: o adaptador converte em `TranscriptionError`,
        e a rota em `502 transcription_failed` (verificado em TI-07).
        """
        from services.transcription_service import TranscribeAudio, TranscriptionError

        chave = chave_stt_da_massa(self.audio, cenario="credencial-invalida")
        with self.vhs.fita(chave) as fita, self.assertRaises(TranscriptionError) as capturado:
            asyncio.run(
                TranscribeAudio(FetcherDeMemoria(self.audio), CHAVE_IRRELEVANTE).transcribe(
                    audio_id="massa", language=IDIOMA
                )
            )

        self.assertEqual(capturado.exception.code.name, "TRANSCRIPTION_FAILED")
        self.assertEqual(fita.play_count, 1, "o erro veio da fita, não de uma chamada nova")

    def test_timeout_sem_resposta_nao_tem_fita_e_e_declarado_simulado(self) -> None:
        """Ausência de resposta não é gravável, e o registro não finge que é.

        O VCR.py grava interação; um tempo limite estourado é a ausência de uma.
        A Seção 6.4.3 já previa isto ("não se afirma que VCR.py grave
        automaticamente essa ausência de resposta"), e o caso o torna verificável:
        não existe fita de timeout no manifesto, e a simulação correspondente
        vive em `tests/test_integracao_transcricao.py`, com a origem declarada.
        """
        cenarios_gravados = {
            registro.cenario for registro in self.vhs.manifesto.registros.values()
        }

        for inventado in ("timeout", "tempo-limite", "conexao-recusada", "rede-fora"):
            self.assertNotIn(
                inventado,
                cenarios_gravados,
                f"há uma fita de '{inventado}' no manifesto; ausência de resposta não se grava",
            )

    # -- TI-61 ---------------------------------------------------------------

    def test_nenhum_segredo_ou_marcador_sobrevive_nas_gravacoes(self) -> None:
        """Varredura das fitas versionadas, por nome e por valor.

        Complementa TI-50, que vigia o mesmo no harness sintético: aqui os
        arquivos varridos são os das interações reais com Deepgram e Google, que
        são os que de fato carregariam uma credencial corporativa.
        """
        achados = self.vhs.varredura_de_segredos()
        self.assertEqual(achados, [], f"segredo encontrado nas gravações: {achados}")

        # E nenhum cabeçalho de credencial sobreviveu por nome.
        for arquivo in FITAS.rglob("*.yaml"):
            conteudo = arquivo.read_text(encoding="utf-8", errors="replace").lower()
            for proibido in NOMES_PROIBIDOS:
                self.assertNotIn(
                    proibido,
                    conteudo,
                    f"{arquivo.relative_to(FITAS)} ainda contém o cabeçalho {proibido!r}",
                )

    def test_mudanca_de_modelo_idioma_ou_termos_invalida_a_gravacao(self) -> None:
        """Alterado o que é semanticamente relevante, a fita antiga não serve.

        Este é o TI-52 aplicado às gravações REAIS: cada variação abaixo produz
        uma chave que não existe no manifesto, e o replay falha com
        `RegistroAusente` em vez de servir a resposta do modelo anterior.
        """
        variacoes = {
            "outro modelo de STT": chave_stt(
                audio=self.audio, idioma=IDIOMA, modelo="nova-2", termos=TERMOS, cenario="sucesso"
            ),
            "outro idioma": chave_stt(
                audio=self.audio, idioma="en-US", modelo=MODELO_STT, termos=TERMOS, cenario="sucesso"
            ),
            "outros termos de domínio": chave_stt(
                audio=self.audio, idioma=IDIOMA, modelo=MODELO_STT, termos=("outro",), cenario="sucesso"
            ),
            "outra massa de áudio": chave_stt_da_massa(silencio(3.0), cenario="sucesso"),
            "outra instrução de sistema": chave_chat_da_massa(mensagem="pergunta diferente"),
        }

        for descricao, chave in variacoes.items():
            with self.subTest(mudanca=descricao), self.assertRaises(RegistroAusente):
                self.vhs.manifesto.validar(chave)

    def test_registro_vencido_ou_corrompido_falha_sem_rede(self) -> None:
        """Validade e integridade barram o replay antes de a fita abrir.

        Opera sobre uma CÓPIA das gravações, num diretório temporário: corromper
        o arquivo versionado para depois consertá-lo deixaria o repositório
        refém de o teste terminar bem.
        """
        with tempfile.TemporaryDirectory() as temporario:
            raiz = Path(temporario) / "vhs"
            shutil.copytree(FITAS, raiz)
            chave = chave_stt_da_massa(self.audio, cenario="sucesso")

            # Íntegra e no prazo: valida.
            copia = Vhs(raiz=raiz, modo=Modo.REPRODUZIR)
            copia.manifesto.validar(chave)

            # Vencida: o relógio injetável evita esperar trinta dias.
            registro = copia.manifesto.registros[chave.caminho_relativo.as_posix()]
            depois_do_prazo = agora_utc() + timedelta(days=(registro.validade_dias or 30) + 1)
            envelhecido = Manifesto.carregar(raiz, agora=lambda: depois_do_prazo)
            with self.assertRaises(RegistroVencido):
                envelhecido.validar(chave)

            # Corrompida: o hash deixa de conferir.
            arquivo = raiz / chave.caminho_relativo
            arquivo.write_text(
                arquivo.read_text(encoding="utf-8") + "\n# byte a mais\n", encoding="utf-8"
            )
            with self.assertRaises(RegistroCorrompido):
                Manifesto.carregar(raiz).validar(chave)

    def test_replay_com_chave_ausente_nao_alcanca_a_rede(self) -> None:
        """A falha por ausência acontece ANTES de qualquer tentativa de conexão.

        A distinção importa: falhar por `RedeBloqueada` significaria que o
        código tentou sair, e o bloqueio é que salvou. Falhar por
        `RegistroAusente` significa que nem chegou a tentar — que é a garantia
        que o modo `reproduzir` promete.
        """
        inexistente = ChaveVhs.construir(
            provedor="deepgram",
            modelo=MODELO_STT,
            cenario="cenario-que-nunca-foi-gravado",
            atributos={"massa": "inexistente"},
        )

        with self.assertRaises(RegistroAusente), self.vhs.fita(inexistente):
            self.fail("o corpo da fita não deveria ser alcançado")

    def test_varredura_de_segredos_acha_o_que_deve_achar(self) -> None:
        """Controle do próprio instrumento: a varredura não é vacuamente vazia.

        Um verificador que nunca acusa nada passaria em TI-61 mesmo com as
        fitas cheias de credencial. Plantar um valor conhecido numa cópia e
        exigir que ele seja encontrado é o que prova que o instrumento funciona.
        """
        with tempfile.TemporaryDirectory() as temporario:
            raiz = Path(temporario) / "vhs"
            shutil.copytree(FITAS, raiz)
            plantado = "segredo-plantado-para-o-controle-do-instrumento"
            alvo = next(raiz.rglob("*.yaml"))
            alvo.write_text(
                alvo.read_text(encoding="utf-8") + f"\n# {plantado}\n", encoding="utf-8"
            )

            achados = varrer_segredos(raiz, (plantado,))

            self.assertTrue(achados, "a varredura não encontrou um segredo plantado de propósito")


if __name__ == "__main__":
    unittest.main()
