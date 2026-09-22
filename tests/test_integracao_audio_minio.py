"""Recebimento de áudio e armazenamento de objetos — TI-01 a TI-05 e TI-62.

Aqui o armazenamento é REAL: um MinIO de verdade, provisionado por
`docker compose`, alcançado pelo mesmo `boto3` que a aplicação usa. É a
exigência da Seção 6.4 de que "a persistência ocorre em serviços reais e não em
dublês de memória", e é o que separa estes casos dos de `tests/test_audio_api.py`,
que substituem `ReceiveAudio` por um dublê e não tocam em bucket nenhum.

A verificação do efeito é feita POR FORA, com um cliente `boto3` independente do
que a aplicação usou (Seção 6.4.5). Reler pelo mesmo objeto que gravou provaria
que ele é coerente consigo mesmo; reler por outro prova que o byte chegou ao
serviço.

Preparação:

    docker compose up -d minio minio-init
    export TEST_AUDIO_STORAGE_ENDPOINT_URL=http://127.0.0.1:9000
    python -m unittest tests.test_integracao_audio_minio -v

Sem o endpoint declarado, a suíte inteira é PULADA em vez de falhar — e pular
é registro de execução parcial, não aprovação, como a Seção 6.4.5 insiste.

O bucket de teste é separado do bucket da aplicação e a suíte recusa rodar se os
dois coincidirem. A razão é a mesma que `tests/test_integracao_webhook_postgres.py`
documenta: esta suíte apaga objetos, e um apagão silencioso em cima do bucket de
demonstração já aconteceu neste projeto uma vez.
"""

from __future__ import annotations

import io
import json
import os
import unittest
import wave

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError

from az1_api.dependencies import get_audio_receiver, get_transcriber
from services.audio_service import ReceiveAudio
from services.storage_service import S3ObjectStorage, S3StorageSettings
from services.transcription_service import TranscribeAudio
from tests.apoio_integracao import RAIZ, cliente, limpar_overrides

ENDPOINT = os.environ.get("TEST_AUDIO_STORAGE_ENDPOINT_URL", "")
BUCKET = os.environ.get("TEST_AUDIO_STORAGE_BUCKET", "az1-audio-teste")
ACCESS_KEY = os.environ.get("TEST_AUDIO_STORAGE_ACCESS_KEY", "minioadmin")
SECRET_KEY = os.environ.get("TEST_AUDIO_STORAGE_SECRET_KEY", "minioadmin")
REGIAO = os.environ.get("TEST_AUDIO_STORAGE_REGION", "us-east-1")

POLITICA_VERSIONADA = RAIZ / "infra" / "minio" / "lifecycle.json"

# Timeout curto: os casos de indisponibilidade de TI-04 apontam para uma porta
# fechada, e o padrão do botocore é minuto a minuto com várias tentativas.
_RAPIDO = Config(
    connect_timeout=2, read_timeout=2, retries={"max_attempts": 1, "mode": "standard"}
)


def _ajustes(**trocas: str) -> S3StorageSettings:
    base = {
        "bucket_name": BUCKET,
        "endpoint_url": ENDPOINT,
        "region_name": REGIAO,
        "access_key": ACCESS_KEY,
        "secret_key": SECRET_KEY,
    }
    base.update(trocas)
    return S3StorageSettings(**base)


def _cliente_boto3(ajustes: S3StorageSettings):
    return boto3.client(
        "s3",
        endpoint_url=ajustes.endpoint_url,
        region_name=ajustes.region_name,
        aws_access_key_id=ajustes.access_key,
        aws_secret_access_key=ajustes.secret_key,
        config=_RAPIDO,
    )


def _motivo_para_pular() -> str | None:
    """Devolve o motivo de pular, ou None se o MinIO de teste responder."""
    if not ENDPOINT:
        return (
            "TEST_AUDIO_STORAGE_ENDPOINT_URL não definido. Suba o MinIO com "
            "`docker compose up -d minio minio-init` e aponte a variável para ele."
        )
    if os.environ.get("AUDIO_STORAGE_BUCKET") == BUCKET:
        return (
            "TEST_AUDIO_STORAGE_BUCKET é igual ao bucket da aplicação. "
            "Esta suíte apaga objetos; use um bucket separado."
        )
    try:
        cliente_s3 = _cliente_boto3(_ajustes())
        cliente_s3.list_buckets()
    except (ClientError, BotoCoreError) as erro:
        return f"MinIO de teste indisponível em {ENDPOINT}: {type(erro).__name__}"
    return None


MOTIVO = _motivo_para_pular()


def _wav(segundos: float = 0.5) -> bytes:
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as saida:
        saida.setnchannels(1)
        saida.setsampwidth(2)
        saida.setframerate(24_000)
        saida.writeframes(b"\x00\x01" * int(24_000 * segundos))
    return buffer.getvalue()


@unittest.skipIf(MOTIVO is not None, MOTIVO or "")
class TestRecebimentoAudioIntegracao(unittest.TestCase):
    """TI-01 a TI-05 e TI-62."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.ajustes = _ajustes()
        cls.conferidor = _cliente_boto3(cls.ajustes)
        try:
            cls.conferidor.head_bucket(Bucket=BUCKET)
        except ClientError:
            cls.conferidor.create_bucket(Bucket=BUCKET)

    def setUp(self) -> None:
        self.armazenamento = S3ObjectStorage.from_settings(self.ajustes)
        self.criados: list[str] = []

    def tearDown(self) -> None:
        limpar_overrides()
        for chave in self.criados:
            self.conferidor.delete_object(Bucket=BUCKET, Key=chave)

    def _chaves_no_bucket(self, prefixo: str = "incoming/") -> set[str]:
        """Lê o bucket por fora, com um cliente independente do da aplicação."""
        pagina = self.conferidor.list_objects_v2(Bucket=BUCKET, Prefix=prefixo)
        return {objeto["Key"] for objeto in pagina.get("Contents", [])}

    def _enviar(self, conteudo: bytes, *, nome: str = "consulta.wav", tipo: str = "audio/wav"):
        http = cliente({get_audio_receiver: lambda: ReceiveAudio(storage=self.armazenamento)})
        return http.post("/api/v1/audio", files={"audio": (nome, conteudo, tipo)})

    # -- TI-01 ---------------------------------------------------------------

    def test_upload_valido_grava_objeto_no_bucket(self) -> None:
        """O `201` corresponde a um objeto que existe, com os metadados certos."""
        conteudo = _wav()

        resposta = self._enviar(conteudo)

        self.assertEqual(resposta.status_code, 201)
        audio_id = resposta.json()["id"]
        self.assertTrue(audio_id.startswith("aud_"), f"identificador inesperado: {audio_id}")
        chave = f"incoming/{audio_id}"
        self.criados.append(chave)

        objeto = self.conferidor.get_object(Bucket=BUCKET, Key=chave)
        self.assertEqual(objeto["ContentType"], "audio/wav")
        self.assertEqual(objeto["Metadata"]["audio-format"], "wav")
        self.assertEqual(objeto["ContentLength"], len(conteudo))

    # -- TI-02 ---------------------------------------------------------------

    def test_leitura_devolve_bytes_identicos_ao_upload(self) -> None:
        """O que `TranscribeAudio` lê é byte a byte o que foi enviado.

        Esta é a junta entre as duas rotas: o identificador opaco `aud_<uuid>`
        devolvido pelo recebimento é o que o adaptador de leitura usa para
        montar a chave. Um prefixo divergente entre gravar e ler só apareceria
        aqui, com as duas pontas no mesmo caso.
        """
        conteudo = _wav(0.7)
        resposta = self._enviar(conteudo)
        self.assertEqual(resposta.status_code, 201)
        audio_id = resposta.json()["id"]
        self.criados.append(f"incoming/{audio_id}")

        lidos = self.armazenamento.fetch(key=f"incoming/{audio_id}")

        self.assertEqual(lidos, conteudo)

    # -- TI-03 ---------------------------------------------------------------

    def test_audio_id_inexistente_retorna_404(self) -> None:
        """A ausência do objeto vira `404 audio_not_found`, sem tocar no provedor.

        O `NoSuchKey` do botocore é traduzido em `KeyError` pelo adaptador, em
        `TranscriptionError.AUDIO_NOT_FOUND` pelo serviço e em `404` pela rota —
        três fronteiras numa só requisição. O provedor de transcrição não é
        alcançado, porque a leitura falha antes.
        """
        transcritor = TranscribeAudio(self.armazenamento, "irrelevante-nao-sera-usado")
        http = cliente({get_transcriber: lambda: transcritor})

        resposta = http.post("/api/v1/audio/aud_que_nunca_existiu/transcribe")

        self.assertEqual(resposta.status_code, 404)
        self.assertEqual(resposta.json()["error"], "audio_not_found")

    # -- TI-04 ---------------------------------------------------------------

    def test_falha_de_infraestrutura_retorna_500(self) -> None:
        """As três causas dão `500 internal_error`, sem detalhe de infraestrutura.

        A Seção 6.4.2 registra que o adaptador traduz apenas `NoSuchKey`; tudo
        o mais chega ao cliente como 500 indistinto. O caso fixa esse
        comportamento e serve de base para a eventual diferenciação de código,
        que continua sendo decisão em aberto.
        """
        causas = {
            "bucket inexistente": _ajustes(bucket_name="bucket-que-nao-existe-az1"),
            "credencial inválida": _ajustes(access_key="chave-errada", secret_key="segredo-errado"),
            "serviço inacessível": _ajustes(endpoint_url="http://127.0.0.1:9"),
        }

        for descricao, ajustes in causas.items():
            with self.subTest(causa=descricao):
                armazenamento = S3ObjectStorage(
                    client=_cliente_boto3(ajustes), bucket_name=ajustes.bucket_name
                )
                http = cliente({get_audio_receiver: lambda: ReceiveAudio(storage=armazenamento)})

                resposta = http.post(
                    "/api/v1/audio", files={"audio": ("consulta.wav", _wav(), "audio/wav")}
                )

                self.assertEqual(resposta.status_code, 500)
                corpo = resposta.json()
                self.assertEqual(corpo["error"], "internal_error")
                # Nada de endpoint, bucket, chave de acesso ou nome de biblioteca.
                for proibido in ("minio", "boto", "s3", "bucket", "127.0.0.1", "chave-errada"):
                    self.assertNotIn(proibido, corpo["message"].lower())

    # -- TI-05 ---------------------------------------------------------------

    def test_arquivo_rejeitado_nao_grava_objeto(self) -> None:
        """Extensão não é formato: um `.txt` renomeado é recusado pela assinatura.

        E o que o caso prova além do código HTTP é a ORDEM da Seção 6.4.1: o
        bucket é comparado antes e depois, e não ganhou nenhum objeto. Uma
        implementação que gravasse primeiro e validasse depois passaria no
        `415` e falharia aqui.
        """
        antes = self._chaves_no_bucket()

        resposta = self._enviar(
            b"isto e um arquivo de texto, nao um audio", nome="disfarcado.wav"
        )

        self.assertEqual(resposta.status_code, 415)
        self.assertEqual(resposta.json()["error"], "unsupported_format")
        self.assertEqual(self._chaves_no_bucket(), antes, "objeto gravado apesar da recusa")

    # -- TI-62 ---------------------------------------------------------------

    def test_politica_de_ciclo_de_vida_corresponde_ao_arquivo_versionado(self) -> None:
        """A regra aplicada no bucket é a que está no repositório.

        **O que este caso prova, e o que não prova.** Prova que a política
        declarada em `infra/minio/lifecycle.json` foi aplicada ao bucket, com o
        prefixo, o prazo e o estado que o arquivo declara. NÃO prova que o
        expurgo acontece aos sete dias: a Seção 3.2.5 trata de retenção, e
        verificar a exclusão real exigiria esperar uma semana ou usar uma
        política acelerada em bucket separado — que valida o mecanismo, não o
        prazo. A ficha de TI-62 já registrava essa distinção.
        """
        declarada = json.loads(POLITICA_VERSIONADA.read_text(encoding="utf-8"))

        try:
            aplicada = self.conferidor.get_bucket_lifecycle_configuration(Bucket=BUCKET)
        except ClientError as erro:
            if erro.response["Error"]["Code"] in ("NoSuchLifecycleConfiguration", "NoSuchLifecycle"):
                self.skipTest(
                    "o bucket de teste não tem ciclo de vida aplicado; rode `minio-init` "
                    "contra ele ou aplique infra/minio/lifecycle.json manualmente"
                )
            raise

        por_id = {regra["ID"]: regra for regra in aplicada["Rules"]}
        for regra in declarada["Rules"]:
            with self.subTest(regra=regra["ID"]):
                self.assertIn(regra["ID"], por_id, "regra declarada ausente no bucket")
                viva = por_id[regra["ID"]]
                self.assertEqual(viva["Status"], regra["Status"])
                self.assertEqual(viva["Expiration"]["Days"], regra["Expiration"]["Days"])
                self.assertEqual(
                    viva.get("Filter", {}).get("Prefix"), regra["Filter"]["Prefix"]
                )

        # E a regra que interessa ao áudio é a de `incoming/`, com sete dias.
        incoming = next(
            regra for regra in declarada["Rules"] if regra["Filter"]["Prefix"] == "incoming/"
        )
        self.assertEqual(incoming["Expiration"]["Days"], 7)
        self.assertEqual(incoming["Status"], "Enabled")

    def test_objeto_ausente_apos_expurgo_leva_a_404(self) -> None:
        """O efeito do expurgo, ensaiado por remoção direta.

        Apagar o objeto à mão reproduz o ESTADO em que o ciclo de vida deixa o
        bucket depois do prazo, sem esperar sete dias. O que se verifica é a
        consequência para quem chama: o identificador continua existindo do lado
        do cliente, e a transcrição responde 404. É a segunda metade de TI-62, e
        também não prova o prazo.
        """
        resposta = self._enviar(_wav())
        self.assertEqual(resposta.status_code, 201)
        audio_id = resposta.json()["id"]
        chave = f"incoming/{audio_id}"

        self.conferidor.delete_object(Bucket=BUCKET, Key=chave)
        self.assertNotIn(chave, self._chaves_no_bucket())

        transcritor = TranscribeAudio(self.armazenamento, "irrelevante-nao-sera-usado")
        http = cliente({get_transcriber: lambda: transcritor})
        depois = http.post(f"/api/v1/audio/{audio_id}/transcribe")

        self.assertEqual(depois.status_code, 404)
        self.assertEqual(depois.json()["error"], "audio_not_found")


if __name__ == "__main__":
    unittest.main()
