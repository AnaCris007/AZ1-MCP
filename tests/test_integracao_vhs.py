"""Casos TI-47 a TI-52 — o módulo VHS (Seções 3.8.10 e 6.4.3).

O provedor exercitado aqui é um servidor HTTP local e sintético, e não a
Deepgram ou o Google. A escolha é deliberada e está dentro do que o plano pede:
o item 4 do contrato manda "gravar uma interação sintética com `once` e a porta
real do SDK, medindo chamadas de rede no transporte abaixo da interceptação".
O transporte real dos dois SDKs em uso é o `httpx` — `deepgram-sdk` 7.x e
`google-genai` 2.x constroem clientes `httpx` — e é sobre ele que o VCR.py
interpõe o `httpx_stubs`. Uma interação sintética contra `127.0.0.1` passa pelo
mesmo caminho de código que uma interação com o provedor, sem gastar chamada
externa e sem depender de credencial em CI.

O que esta suíte NÃO é: a prova de que o replay funciona com a Deepgram e com o
Google. Essa é TI-59, e exige gravar uma chamada de cada SDK em sessão
controlada. O que esta suíte prova é o harness: chave, validade, sanitização,
ausência de rede em replay e comportamento dos quatro modos.

As contagens vêm de duas fontes independentes, como o item 4 exige: o contador
do servidor local (chamadas que realmente chegaram) e o `play_count` da fita
(reproduções servidas). A primeira é a que responde "houve chamada nova?"; a
segunda, sozinha, não responderia.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import threading
import unittest
from datetime import UTC, datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import httpx

from tests.vhs import (
    ChaveVhs,
    Manifesto,
    Modo,
    RegistroAusente,
    RegistroCorrompido,
    RegistroVencido,
    Vhs,
    chave_chat,
    chave_stt,
    versao_de_pacote,
)
from tests.vhs.erros import CampanhaEmAndamento, CampanhaEncerrada, LimiteDeChamadasReais
from tests.vhs.manifesto import ORIGEM_SIMULADA
from tests.vhs.sanitizacao import MARCA

RAIZ_DO_REPOSITORIO = Path(__file__).resolve().parents[1]

AUDIO = b"RIFF....massa sintetica de audio para teste...."
TERMOS = ("portfólio", "PMO", "aderência")
MODELO_STT = "nova-3"


# ---------------------------------------------------------------------------
# Provedor sintético
# ---------------------------------------------------------------------------
# Um servidor HTTP de verdade, em porta efêmera. Ele conta o que recebeu — e é
# esse contador, e não o `play_count`, que sustenta as asserções de "nenhuma
# chamada nova".


class _Manipulador(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def do_POST(self) -> None:  # noqa: N802 - nome imposto por BaseHTTPRequestHandler
        provedor: ProvedorSintetico = self.server.provedor  # type: ignore[attr-defined]
        provedor.chamadas += 1
        self.rfile.read(int(self.headers.get("content-length") or 0))

        corpo = json.dumps(provedor.carga).encode("utf-8")
        self.send_response(provedor.status)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(corpo)))
        for nome, valor in provedor.cabecalhos_extra.items():
            self.send_header(nome, valor)
        self.end_headers()
        self.wfile.write(corpo)

    def log_message(self, *_args: object) -> None:
        """Silencia o log do servidor, que iria para o stderr da suíte."""


class ProvedorSintetico:
    """Servidor local que faz as vezes do serviço externo."""

    def __init__(self) -> None:
        self.chamadas = 0
        self.status = 200
        self.carga: dict[str, object] = {"texto": "relatório de aderência do portfólio", "idioma": "pt-BR"}
        self.cabecalhos_extra: dict[str, str] = {}

        self._servidor = ThreadingHTTPServer(("127.0.0.1", 0), _Manipulador)
        self._servidor.provedor = self  # type: ignore[attr-defined]
        self._thread = threading.Thread(target=self._servidor.serve_forever, daemon=True)
        self._thread.start()

    @property
    def porta(self) -> int:
        return self._servidor.server_address[1]

    def url(self, caminho: str = "/v1/listen", query: str = "language=pt-BR") -> str:
        return f"http://127.0.0.1:{self.porta}{caminho}?{query}"

    def encerrar(self) -> None:
        self._servidor.shutdown()
        self._servidor.server_close()
        self._thread.join(timeout=5)


class RelogioFalso:
    """Relógio injetável — o item 7 pede testar a validade sem esperar dias."""

    def __init__(self, inicio: datetime | None = None) -> None:
        self.momento = inicio or datetime(2026, 9, 19, 12, 0, tzinfo=UTC)

    def __call__(self) -> datetime:
        return self.momento

    def avancar(self, *, dias: int = 0, horas: int = 0) -> None:
        self.momento += timedelta(days=dias, hours=horas)


def adaptador(
    url: str,
    *,
    corpo: dict[str, object] | None = None,
    cabecalhos: dict[str, str] | None = None,
) -> httpx.Response:
    """O "adaptador real" destes casos: uma chamada `httpx` como a dos SDKs."""
    return httpx.post(url, json=corpo or {"audio": "sintetico"}, headers=cabecalhos or {}, timeout=10)


# ---------------------------------------------------------------------------
# TI-47 a TI-52
# ---------------------------------------------------------------------------


class TestVhsIntegracao(unittest.TestCase):
    """Casos do Módulo VHS, tabela da Seção 6.4.4."""

    def setUp(self) -> None:
        self.provedor = ProvedorSintetico()
        self.addCleanup(self.provedor.encerrar)

        temporario = tempfile.TemporaryDirectory()
        self.addCleanup(temporario.cleanup)
        self.raiz = Path(temporario.name)

        self.relogio = RelogioFalso()
        self.versao_sdk = versao_de_pacote("httpx")
        self.chave = chave_stt(
            audio=AUDIO,
            idioma="pt-BR",
            modelo=MODELO_STT,
            termos=TERMOS,
            cenario="sucesso",
        )

    def _vhs(self, modo: Modo, **extras: object) -> Vhs:
        return Vhs(
            raiz=self.raiz,
            modo=modo,
            versao_sdk=self.versao_sdk,
            agora=self.relogio,
            **extras,  # type: ignore[arg-type]
        )

    # -- TI-47 --------------------------------------------------------------

    def test_ausencia_ou_expiracao_aciona_o_adaptador_real(self) -> None:
        """Chave nova, ou registro vencido: grava chamando; reproduz falhando.

        As duas metades do caso são o mesmo fato visto de dois modos. Em
        `gravar`, a ausência e o vencimento autorizam a chamada real e
        produzem registro. Em `reproduzir`, os mesmos dois estados falham, e
        falham sem rede — a expiração não abre exceção para sair chamando em
        CI, que é o que o item 7 do contrato proíbe.
        """
        # Chave nova, modo gravar: chama e registra.
        with self._vhs(Modo.GRAVAR).fita(self.chave, validade_dias=1) as fita:
            resposta = adaptador(self.provedor.url())

        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(self.provedor.chamadas, 1)
        self.assertEqual(fita.play_count, 0)
        self.assertTrue((self.raiz / self.chave.caminho_relativo).exists())

        # Dentro da validade, reproduzir devolve o gravado sem tocar o provedor.
        self.relogio.avancar(horas=12)
        with self._vhs(Modo.REPRODUZIR).fita(self.chave) as fita:
            repetida = adaptador(self.provedor.url())

        self.assertEqual(repetida.json(), resposta.json())
        self.assertEqual(self.provedor.chamadas, 1)

        # Passada a validade de um dia, reproduzir falha — e sem rede.
        self.relogio.avancar(dias=2)
        with self.assertRaises(RegistroVencido), self._vhs(Modo.REPRODUZIR).fita(self.chave):
            self.fail("a fita não deveria ter aberto com o registro vencido")

        self.assertEqual(self.provedor.chamadas, 1)

        # Em gravação autorizada, o vencimento leva a nova captura e novo registro.
        with self._vhs(Modo.GRAVAR).fita(self.chave, validade_dias=1):
            adaptador(self.provedor.url())

        self.assertEqual(self.provedor.chamadas, 2)
        registro = Manifesto.carregar(self.raiz, agora=self.relogio).validar(self.chave)
        self.assertEqual(registro.gravado_em, self.relogio().isoformat())

    # -- TI-48 --------------------------------------------------------------

    def test_registro_existente_nao_aciona_o_adaptador(self) -> None:
        """Segunda chamada com a mesma entrada é servida pela fita.

        Vale para sucesso e para erro HTTP gravado: um 502 reproduzido continua
        502, e continua sem chamar o provedor. O replay é conferido também em
        **processo novo**, com o servidor já desligado, porque o item 4 exige
        que ele não dependa da memória da primeira execução — em processo
        único, um acerto poderia vir de cache do cliente, e não da fita.
        """
        with self._vhs(Modo.GRAVAR).fita(self.chave):
            primeira = adaptador(self.provedor.url())
        self.assertEqual(self.provedor.chamadas, 1)

        with self._vhs(Modo.REPRODUZIR).fita(self.chave) as fita:
            segunda = adaptador(self.provedor.url())

        self.assertEqual(segunda.status_code, primeira.status_code)
        self.assertEqual(segunda.json(), primeira.json())
        self.assertEqual(fita.play_count, 1)
        self.assertEqual(self.provedor.chamadas, 1, "replay não pode acionar o adaptador de novo")

        # Erro HTTP gravado: o 502 volta do arquivo, não do provedor.
        chave_erro = chave_stt(audio=AUDIO, idioma="pt-BR", modelo=MODELO_STT, termos=TERMOS, cenario="erro-502")
        self.provedor.status = 502
        self.provedor.carga = {"err_code": "PROVIDER_DOWN"}

        with self._vhs(Modo.GRAVAR).fita(chave_erro):
            adaptador(self.provedor.url())
        self.assertEqual(self.provedor.chamadas, 2)

        with self._vhs(Modo.REPRODUZIR).fita(chave_erro):
            reproduzido = adaptador(self.provedor.url())

        self.assertEqual(reproduzido.status_code, 502)
        self.assertEqual(reproduzido.json(), {"err_code": "PROVIDER_DOWN"})
        self.assertEqual(self.provedor.chamadas, 2)

        # Processo novo, provedor desligado.
        url = self.provedor.url()
        self.provedor.encerrar()
        concluido = self._replay_em_novo_processo(self.chave, url)

        self.assertEqual(concluido.returncode, 0, concluido.stderr)
        self.assertEqual(json.loads(concluido.stdout)["texto"], primeira.json()["texto"])

    def _replay_em_novo_processo(self, chave: ChaveVhs, url: str) -> subprocess.CompletedProcess[str]:
        """Roda o replay em um interpretador limpo, sem o estado desta execução."""
        roteiro = self.raiz / "replay.py"
        roteiro.write_text(
            "\n".join(
                [
                    "import json, sys",
                    "import httpx",
                    "from pathlib import Path",
                    "from tests.vhs import ChaveVhs, Modo, Vhs",
                    "raiz, url, identidade = sys.argv[1], sys.argv[2], json.loads(sys.argv[3])",
                    "chave = ChaveVhs.construir(**identidade)",
                    "with Vhs(raiz=Path(raiz), modo=Modo.REPRODUZIR).fita(chave):",
                    "    resposta = httpx.post(url, json={'audio': 'sintetico'}, timeout=10)",
                    "print(json.dumps(resposta.json()))",
                ]
            ),
            encoding="utf-8",
        )

        identidade = {
            "provedor": chave.provedor,
            "modelo": chave.modelo,
            "cenario": chave.cenario,
            "versao_contrato": chave.versao_contrato,
            "atributos": dict(chave.atributos),
        }
        return subprocess.run(
            [sys.executable, str(roteiro), str(self.raiz), url, json.dumps(identidade)],
            capture_output=True,
            text=True,
            cwd=RAIZ_DO_REPOSITORIO,
            # O roteiro mora no diretório temporário: sem isto, `sys.path[0]`
            # seria o tmpdir e `tests` não seria importável no processo novo.
            env={**os.environ, "PYTHONPATH": str(RAIZ_DO_REPOSITORIO)},
            timeout=120,
            check=False,
        )

    # -- TI-49 --------------------------------------------------------------

    def test_modo_reproduzir_sem_registro_valido_falha_sem_acessar_a_rede(self) -> None:
        """Ausência e corrupção falham, com mensagens distintas e sem rede.

        Distinguir as duas importa na hora de agir: registro ausente significa
        gravar; registro corrompido significa investigar o arquivo antes de
        substituí-lo, porque a diferença pode ser edição manual indevida.
        """
        with self.assertRaises(RegistroAusente), self._vhs(Modo.REPRODUZIR).fita(self.chave):
            self.fail("não deveria abrir fita inexistente")
        self.assertEqual(self.provedor.chamadas, 0)

        with self._vhs(Modo.GRAVAR).fita(self.chave):
            adaptador(self.provedor.url())
        self.assertEqual(self.provedor.chamadas, 1)

        arquivo = self.raiz / self.chave.caminho_relativo
        arquivo.write_text("interactions: [conteúdo adulterado]\n", encoding="utf-8")

        with self.assertRaises(RegistroCorrompido), self._vhs(Modo.REPRODUZIR).fita(self.chave):
            self.fail("não deveria abrir fita corrompida")
        self.assertEqual(self.provedor.chamadas, 1, "a falha por corrupção não pode virar chamada nova")

        # E o registro anotado no manifesto sem arquivo em disco é ausência,
        # não corrupção: o que sumiu não foi adulterado.
        arquivo.unlink()
        with self.assertRaises(RegistroAusente), self._vhs(Modo.REPRODUZIR).fita(self.chave):
            self.fail("não deveria abrir fita apagada")
        self.assertEqual(self.provedor.chamadas, 1)

    # -- TI-50 --------------------------------------------------------------

    def test_nenhum_segredo_e_gravado_no_registro(self) -> None:
        """Varredura das gravações de sucesso e de falha: nada de credencial.

        A prova de compatibilidade feita antes deste módulo mostrou o cenário
        contrário: sem os callbacks, `Authorization` e `Set-Cookie` ficam
        legíveis no YAML. Aqui os quatro vetores do item 3 são exercitados de
        uma vez — cabeçalho de autorização, cabeçalho de chave do Google,
        cookie de resposta e chave na query — mais a redação por valor de um
        segredo que aparece no corpo nos dois sentidos.
        """
        segredo = "chave-secreta-de-teste-0123456789"
        vhs = self._vhs(Modo.GRAVAR, segredos=(segredo,))

        self.provedor.cabecalhos_extra = {"set-cookie": f"sessao={segredo}; Path=/"}
        self.provedor.carga = {"texto": "ok", "eco_da_chave": segredo}

        with vhs.fita(self.chave):
            adaptador(
                self.provedor.url(query=f"language=pt-BR&key={segredo}"),
                corpo={"audio": "sintetico", "credencial": segredo},
                cabecalhos={
                    "authorization": f"Token {segredo}",
                    "x-goog-api-key": segredo,
                    "cookie": f"sessao={segredo}",
                },
            )

        chave_falha = chave_stt(audio=AUDIO, idioma="pt-BR", modelo=MODELO_STT, termos=TERMOS, cenario="falha-401")
        self.provedor.status = 401
        self.provedor.carga = {"err_msg": f"chave {segredo} inválida"}

        with vhs.fita(chave_falha):
            adaptador(self.provedor.url(), cabecalhos={"authorization": f"Token {segredo}"})

        self.assertEqual(vhs.varredura_de_segredos(), [])

        for arquivo in sorted(self.raiz.rglob("*.yaml")):
            bruto = arquivo.read_text(encoding="utf-8")
            with self.subTest(arquivo=arquivo.name):
                self.assertNotIn(segredo, bruto)
                self.assertNotIn("authorization", bruto.lower())
                self.assertNotIn("x-goog-api-key", bruto.lower())
                self.assertNotIn("set-cookie", bruto.lower())
                self.assertIn(MARCA, bruto, "a marca de redação deve ficar visível no lugar do segredo")

    # -- TI-51 --------------------------------------------------------------

    def test_modos_ignorar_e_atualizar_se_comportam_conforme_especificado(self) -> None:
        """Sem contexto não há fita; `atualizar` grava candidato, não sobrescreve.

        Os nomes "ignorar" e "atualizar" vêm da redação original do caso. Como
        a Seção 6.4.3 registra, não existe variável `VHS_MODO`: "ignorar" é o
        modo `desligado`, em que nenhum contexto VCR é aberto, e "atualizar" é
        o `all`, que produz uma versão candidata para revisão do diff antes de
        substituir a vigente.
        """
        # Desligado: chamada real, nenhum arquivo, nenhum registro.
        with self._vhs(Modo.DESLIGADO).fita(self.chave) as fita:
            adaptador(self.provedor.url())

        self.assertIsNone(fita)
        self.assertEqual(self.provedor.chamadas, 1)
        self.assertFalse((self.raiz / self.chave.caminho_relativo).exists())

        with self._vhs(Modo.GRAVAR).fita(self.chave):
            adaptador(self.provedor.url())

        arquivo = self.raiz / self.chave.caminho_relativo
        vigente = arquivo.read_bytes()
        self.assertEqual(self.provedor.chamadas, 2)

        # Atualizar: chama de novo, grava ao lado, deixa a vigente intacta.
        self.provedor.carga = {"texto": "resposta nova do provedor", "idioma": "pt-BR"}
        vhs = self._vhs(Modo.ATUALIZAR)
        with vhs.fita(self.chave):
            adaptador(self.provedor.url())

        candidato = arquivo.with_suffix(".candidato.yaml")
        self.assertEqual(self.provedor.chamadas, 3)
        self.assertTrue(candidato.exists())
        self.assertEqual(arquivo.read_bytes(), vigente, "a versão vigente não pode ser sobrescrita sem revisão")
        self.assertIn("resposta nova do provedor", candidato.read_text(encoding="utf-8"))

        # Promoção explícita: a partir daí o replay serve o conteúdo novo.
        vhs.promover_candidato(self.chave)
        self.assertFalse(candidato.exists())

        with self._vhs(Modo.REPRODUZIR).fita(self.chave):
            resposta = adaptador(self.provedor.url())

        self.assertEqual(resposta.json()["texto"], "resposta nova do provedor")
        self.assertEqual(self.provedor.chamadas, 3)

    # -- TI-52 --------------------------------------------------------------

    def test_chave_e_sensivel_a_mudanca_de_idioma_modelo_ou_instrucao(self) -> None:
        """Mudou idioma, modelo ou instrução: chave nova, registro não reusado.

        É a proteção contra o pior defeito possível em um mecanismo de replay —
        responder a pergunta de hoje com a gravação de ontem, feita com outra
        configuração, e chamar isso de teste verde.
        """
        with self._vhs(Modo.GRAVAR).fita(self.chave):
            adaptador(self.provedor.url())
        self.assertEqual(self.provedor.chamadas, 1)

        variantes = {
            "idioma": chave_stt(audio=AUDIO, idioma="en-US", modelo=MODELO_STT, termos=TERMOS, cenario="sucesso"),
            "modelo": chave_stt(audio=AUDIO, idioma="pt-BR", modelo="nova-2", termos=TERMOS, cenario="sucesso"),
            "termos": chave_stt(audio=AUDIO, idioma="pt-BR", modelo=MODELO_STT, termos=(), cenario="sucesso"),
            "audio": chave_stt(
                audio=b"outra massa", idioma="pt-BR", modelo=MODELO_STT, termos=TERMOS, cenario="sucesso"
            ),
        }

        for nome, variante in variantes.items():
            with self.subTest(mudanca=nome):
                self.assertNotEqual(variante.digest, self.chave.digest)
                with self.assertRaises(RegistroAusente), self._vhs(Modo.REPRODUZIR).fita(variante):
                    self.fail(f"a variante de {nome} não pode reaproveitar a gravação anterior")

        self.assertEqual(self.provedor.chamadas, 1)

        # A instrução de sistema é o atributo equivalente no chat, e separa
        # duas chaves com a mesma mensagem.
        comum = {"mensagem": "qual a aderência do projeto X?", "modelo": "gemini-2.5-flash", "cenario": "sucesso"}
        self.assertNotEqual(
            chave_chat(instrucao="responda apenas com base nas fontes", **comum).digest,
            chave_chat(instrucao="responda livremente", **comum).digest,
        )


# ---------------------------------------------------------------------------
# Contrato do harness: orçamento, campanha e temporários
# ---------------------------------------------------------------------------
# Itens 6 e 10 da Seção 6.4.3. Não têm ID de caso na tabela porque descrevem o
# próprio mecanismo, e não uma integração; mas são regras do plano, e regra sem
# teste é intenção.


class TestManifestoVhs(unittest.TestCase):
    def setUp(self) -> None:
        self.provedor = ProvedorSintetico()
        self.addCleanup(self.provedor.encerrar)

        temporario = tempfile.TemporaryDirectory()
        self.addCleanup(temporario.cleanup)
        self.raiz = Path(temporario.name)
        self.relogio = RelogioFalso()
        self.chave = chave_stt(audio=AUDIO, idioma="pt-BR", modelo=MODELO_STT, termos=TERMOS, cenario="sucesso")

    def test_teto_de_chamadas_reais_interrompe_a_campanha(self) -> None:
        """Atingido o limite do manifesto, a próxima gravação não sai."""
        vhs = Vhs(raiz=self.raiz, modo=Modo.GRAVAR, agora=self.relogio)
        vhs.manifesto.abrir_campanha(limite_chamadas_reais=1)

        with vhs.fita(self.chave):
            adaptador(self.provedor.url())

        outra = chave_stt(audio=b"segunda massa", idioma="pt-BR", modelo=MODELO_STT, termos=TERMOS, cenario="sucesso")
        with self.assertRaises(LimiteDeChamadasReais), vhs.fita(outra):
            self.fail("o teto deveria barrar antes da chamada")

        self.assertEqual(self.provedor.chamadas, 1)

    def test_abrir_campanha_nao_devolve_orcamento_ja_gasto(self) -> None:
        """Abrir zera o contador, e por isso não pode acontecer sem querer.

        O roteiro de gravação abre campanha antes de gravar. Rodado duas vezes,
        ele devolveria o orçamento inteiro e o manifesto passaria a declarar
        menos chamadas do que foram feitas — o teto do item 10 limitaria a
        execução, e não a campanha. Reabrir continua valendo, dito em voz alta.
        """
        vhs = Vhs(raiz=self.raiz, modo=Modo.GRAVAR, agora=self.relogio)
        vhs.manifesto.abrir_campanha(limite_chamadas_reais=2)

        with vhs.fita(self.chave):
            adaptador(self.provedor.url())
        self.assertEqual(vhs.manifesto.campanha.chamadas_reais, 1)

        with self.assertRaises(CampanhaEmAndamento):
            vhs.manifesto.abrir_campanha(limite_chamadas_reais=2)
        self.assertEqual(vhs.manifesto.campanha.chamadas_reais, 1, "a recusa não pode ter mexido no contador")

        vhs.manifesto.abrir_campanha(limite_chamadas_reais=2, forcar=True)
        self.assertEqual(vhs.manifesto.campanha.chamadas_reais, 0)

    def test_encerramento_remove_temporarios_e_barra_nova_gravacao(self) -> None:
        """O que não foi selecionado para regressão sai ao fechar a campanha."""
        vhs = Vhs(raiz=self.raiz, modo=Modo.GRAVAR, agora=self.relogio)
        with vhs.fita(self.chave, temporario=True, origem=ORIGEM_SIMULADA):
            adaptador(self.provedor.url())

        arquivo = self.raiz / self.chave.caminho_relativo
        self.assertTrue(arquivo.exists())

        removidos = vhs.manifesto.encerrar_campanha()

        self.assertEqual(removidos, [self.chave.caminho_relativo.as_posix()])
        self.assertFalse(arquivo.exists())
        with self.assertRaises(CampanhaEncerrada), vhs.fita(self.chave):
            self.fail("campanha encerrada não grava")

    def test_manifesto_sobrevive_a_recarga(self) -> None:
        """O estado é o arquivo, não a memória: outra instância lê o mesmo."""
        vhs = Vhs(raiz=self.raiz, modo=Modo.GRAVAR, versao_sdk="9.9.9", agora=self.relogio)
        with vhs.fita(self.chave, validade_dias=7):
            adaptador(self.provedor.url())

        recarregado = Manifesto.carregar(self.raiz, agora=self.relogio).validar(self.chave)

        self.assertEqual(recarregado.versao_sdk, "9.9.9")
        self.assertEqual(recarregado.validade_dias, 7)
        self.assertEqual(recarregado.provedor, "deepgram")
        self.assertEqual(recarregado.modelo, MODELO_STT)


if __name__ == "__main__":
    unittest.main()
