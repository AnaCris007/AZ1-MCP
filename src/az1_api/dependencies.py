import os
from collections.abc import Callable
from functools import lru_cache

from psycopg_pool import ConnectionPool

from services.analysis_service import AnalyzeAudio
from services.audio_service import ReceiveAudio
from services.chat_service import AnswerChatMessage
from services.drive_push_service import PROVEDOR as PROVEDOR_DRIVE
from services.drive_push_service import TIPOS_PROCESSAVEIS as TIPOS_DRIVE
from services.drive_push_service import (
    TradutorDrive,
    VerificadorCanalAtivo,
    VerificadorChannelToken,
)
from services.gemini_service import GeminiChatModel, GeminiSettings
from services.gemini_speech_service import DEFAULT_TTS_MODEL, GeminiSpeechModel
from services.graph_push_service import PROVEDOR as PROVEDOR_GRAPH
from services.graph_push_service import TIPOS_PROCESSAVEIS as TIPOS_GRAPH
from services.graph_push_service import (
    TradutorGraph,
    VerificadorAssinaturaAtiva,
    VerificadorClientState,
    VerificadorEmCadeia,
)
from services.speech_service import GenerateSpeech
from services.storage_service import S3AudioStorage, S3StorageSettings
from services.transcription_service import TranscribeAudio
from services.webhook_registry_service import (
    PostgresSettings,
    ProcessadorVarreduraPendente,
    RegistroConexoesPostgres,
    RegistroEventosPostgres,
)
from services.webhook_service import ReceberEventoWebhook


@lru_cache
def get_audio_receiver() -> ReceiveAudio:
    settings = S3StorageSettings.from_environment()
    return ReceiveAudio(storage=S3AudioStorage.from_settings(settings))


@lru_cache
def get_transcriber() -> TranscribeAudio:
    settings = S3StorageSettings.from_environment()
    api_key = os.environ["DEEPGRAM_API_KEY"]
    return TranscribeAudio(
        fetcher=S3AudioStorage.from_settings(settings),
        api_key=api_key,
    )


@lru_cache
def get_analyzer() -> AnalyzeAudio:
    import sys

    import pln.classificador as _pln_mod
    from pln.caminhos import MODELO_PADRAO
    from pln.classificador import carregar_modelo

    # Modelos serializados via 'python -m pln.classificador' registram classes como
    # '__main__'; via loky/spawn registram como '__mp_main__'. O shim abaixo
    # resolve ambos para 'pln.classificador' durante a desserialização.
    _aliases = ("__main__", "__mp_main__")
    _saved = {k: sys.modules.get(k) for k in _aliases}
    for k in _aliases:
        sys.modules[k] = _pln_mod
    try:
        modelo = carregar_modelo(MODELO_PADRAO)
    finally:
        for k, v in _saved.items():
            if v is None:
                sys.modules.pop(k, None)
            else:
                sys.modules[k] = v

    return AnalyzeAudio(transcriber=get_transcriber(), modelo=modelo)


@lru_cache
def get_chat_answerer() -> AnswerChatMessage:
    settings = GeminiSettings.from_environment()
    return AnswerChatMessage(model=GeminiChatModel.from_settings(settings))


@lru_cache
def get_speech_generator() -> GenerateSpeech:
    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY não configurada para geração de áudio.")
    model = os.environ.get("GEMINI_TTS_MODEL", DEFAULT_TTS_MODEL)
    return GenerateSpeech(model=GeminiSpeechModel.from_api_key(api_key, model))


@lru_cache
def get_connection_pool() -> ConnectionPool:
    """Pool compartilhado pelos dois receptores de webhook.

    É `lru_cache` e não uma variável de módulo para que o pool só seja aberto
    quando alguém precisar dele. Uma instalação que ainda não subiu o Postgres
    continua servindo as demais rotas, e o handshake de validação do Graph
    responde mesmo assim — que é o que permite criar a assinatura antes de o
    banco existir.
    """
    pool = ConnectionPool(PostgresSettings.from_environment().dsn, min_size=1, max_size=4, open=False)
    pool.open()
    return pool


def _segredo(variavel: str, provedor: str) -> str:
    valor = os.environ.get(variavel)
    if not valor:
        raise RuntimeError(
            f"{variavel} não definido. É o segredo compartilhado registrado na criação "
            f"da origem em {provedor}, e sem ele nenhuma entrega pode ser autenticada."
        )
    return valor


@lru_cache
def get_webhook_receiver() -> ReceberEventoWebhook:
    """Monta o receptor de webhooks do Microsoft Graph.

    A autenticidade é composta de duas peças, e não de uma. O `clientState` cobre
    ausência e divergência do segredo; a validade da assinatura cobre a entrega
    antiga reapresentada por quem a capturou — que o `clientState` sozinho não
    pega, por ser constante ao longo da vida da assinatura.

    O que *não* entra na cadeia é o `validationTokens`: ele só acompanha
    notificações com dados de recurso, e `driveItem` não as suporta. A Seção
    5.1.5 registra a limitação e a decisão tomada em cima dela.

    Os testes de API substituem esta função por `app.dependency_overrides`, como
    as demais dependências deste módulo.
    """
    pool = get_connection_pool()
    conexoes = RegistroConexoesPostgres(pool, PROVEDOR_GRAPH)

    return ReceberEventoWebhook(
        verificador=VerificadorEmCadeia(
            verificadores=(
                VerificadorClientState(esperado=_segredo("MS_WEBHOOK_CLIENT_STATE", "Microsoft Graph")),
                VerificadorAssinaturaAtiva(conexoes=conexoes),
            )
        ),
        tradutor=TradutorGraph(),
        registro=RegistroEventosPostgres(pool, PROVEDOR_GRAPH),
        processador=ProcessadorVarreduraPendente(pool, PROVEDOR_GRAPH, TIPOS_GRAPH),
    )


@lru_cache
def get_drive_webhook_receiver() -> ReceberEventoWebhook:
    """Monta o receptor de webhooks do Google Drive.

    Note que só mudam as três peças específicas do provedor — os dois
    verificadores e o tradutor. O serviço, a persistência e o processador são
    literalmente os mesmos objetos usados pelo Graph, parametrizados pelo nome do
    provedor. É essa simetria que a Seção 5.1 apresenta como evidência de que o
    núcleo é desacoplado da plataforma.
    """
    pool = get_connection_pool()
    conexoes = RegistroConexoesPostgres(pool, PROVEDOR_DRIVE)

    return ReceberEventoWebhook(
        verificador=VerificadorEmCadeia(
            verificadores=(
                VerificadorChannelToken(esperado=_segredo("GOOGLE_WEBHOOK_CHANNEL_TOKEN", "Google Drive")),
                VerificadorCanalAtivo(conexoes=conexoes),
            )
        ),
        tradutor=TradutorDrive(),
        registro=RegistroEventosPostgres(pool, PROVEDOR_DRIVE),
        processador=ProcessadorVarreduraPendente(pool, PROVEDOR_DRIVE, TIPOS_DRIVE),
    )


def get_webhook_receiver_provider() -> Callable[[], ReceberEventoWebhook]:
    """Entrega a fábrica do receptor, e não o receptor construído.

    O handshake de validação do Microsoft Graph chega na mesma rota das
    notificações e precisa responder mesmo quando o receptor ainda não pode ser
    montado — é ele que autoriza a criação da assinatura. Como o FastAPI resolve
    as dependências antes de entrar no handler, construir o receptor aqui faria
    o handshake falhar numa instalação nova.
    """
    return get_webhook_receiver


def get_drive_webhook_receiver_provider() -> Callable[[], ReceberEventoWebhook]:
    """Entrega a fábrica do receptor do Drive.

    O Drive não tem handshake, então aqui o adiamento não é estritamente
    necessário. Mantém-se por simetria: as duas rotas têm a mesma forma, e o
    contrato de teste substitui as duas do mesmo jeito.
    """
    return get_drive_webhook_receiver
