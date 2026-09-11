import os
from functools import lru_cache

from psycopg_pool import ConnectionPool

from services.analysis_service import AnalyzeAudio
from services.audio_service import ReceiveAudio
from services.chat_service import AnswerChatMessage
from services.conversa_repository import ConversaRepository
from services.database_service import PostgresSettings, abrir_pool
from services.gemini_service import GeminiChatModel, GeminiSettings
from services.gemini_speech_service import DEFAULT_TTS_MODEL, GeminiSpeechModel
from services.speech_service import GenerateSpeech
from services.storage_service import S3ObjectStorage, S3StorageSettings
from services.transcription_service import TranscribeAudio


@lru_cache
def get_audio_receiver() -> ReceiveAudio:
    settings = S3StorageSettings.from_environment()
    return ReceiveAudio(storage=S3ObjectStorage.from_settings(settings))


@lru_cache
def get_transcriber() -> TranscribeAudio:
    settings = S3StorageSettings.from_environment()
    api_key = os.environ["DEEPGRAM_API_KEY"]
    return TranscribeAudio(
        fetcher=S3ObjectStorage.from_settings(settings),
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


# O pool é compartilhado pelo processo inteiro e aberto sob demanda, e não na
# subida da aplicação: uma instalação sem `SUPABASE_DB_URL` continua servindo
# as rotas que não dependem de banco, em vez de não subir.
#
# `lru_cache` aqui é o que garante um pool só. Dois pools dobrariam as conexões
# contra o Supabase, que as cobra.
@lru_cache
def get_connection_pool() -> ConnectionPool:
    return abrir_pool(PostgresSettings.from_environment())


# A busca semântica passa por aqui, e não por import direto em `routes/rag.py`,
# para poder ser substituída em teste com `app.dependency_overrides`. É o mesmo
# motivo dos cinco provedores acima.
def get_document_searcher():
    from rag.retriever import buscar

    return buscar


# O repositório junta as duas pontas do RNF04: o objeto no S3 e a linha em
# `auditoria`. Depende do pool, então herda o comportamento dele — sem
# `SUPABASE_DB_URL` levanta `BancoNaoConfigurado`, que o manipulador de
# `main.py` traduz em 503.
#
# Ainda NÃO está ligado a `POST /api/v1/chat`, e o motivo é o schema:
# `auditoria.conversa.usuario_id` é NOT NULL e referencia `portfolio.usuario`.
# Sem autenticação não há identidade para gravar, e inventar um usuário fixo
# para contornar produziria uma trilha que atribui a uma pessoa errada tudo o
# que qualquer um perguntou — pior do que trilha nenhuma, porque parece
# confiável. A ligação entra junto com o login.
@lru_cache
def get_conversa_repository() -> ConversaRepository:
    return ConversaRepository(
        pool=get_connection_pool(),
        armazenamento=S3ObjectStorage.from_settings(S3StorageSettings.from_environment()),
    )
