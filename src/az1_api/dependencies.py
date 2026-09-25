import dataclasses
import logging
import os
from collections.abc import Callable
from functools import lru_cache

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from psycopg_pool import ConnectionPool

# `BancoNaoConfigurado` NÃO vem daqui: `database/conexao.py` apenas reexporta a
# classe de `services/database_service.py`, importada mais abaixo. Duas classes
# homônimas fariam `@app.exception_handler` registrar só uma delas.
from database.conexao import obter_engine
from mensageria.config import MensageriaSettings
from mensageria.processador_publicador import ProcessadorComPublicacao
from mensageria.publicador import (
    PublicacaoDesligada,
    Publicador,
    PublicadorRabbitMQ,
)
from rag.retriever import buscar as buscar_contexto_rag
from services.agente_service import AgenteDesligado, ExecutarIntencao
from services.alerta_service import (
    ConfiguracaoAlertas,
    DesativarAssinante,
    DespachoDesligado,
    DispatcherAlerta,
    ListarAssinantes,
    RegistrarAssinante,
)
from services.analysis_service import AnalyzeAudio
from services.audio_service import ReceiveAudio
from services.auditoria_service import ListarConsultas
from services.auth_service import (
    AuthenticatedUser,
    AuthError,
    AuthMode,
    SupabaseAuthSettings,
    SupabaseTokenVerifier,
)
from services.chat_service import AnswerChatMessage
from services.conversa_repository import (
    ConversaRepository,
    PersistenciaDesligada,
    conversa_uuid,
)
from services.database_service import BancoNaoConfigurado, PostgresSettings, abrir_pool
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
from services.portfolio_repository import PortfolioRepository
from services.speech_service import GenerateSpeech
from services.storage_service import S3ObjectStorage, S3StorageSettings
from services.transcription_service import TranscribeAudio
from services.usuario_service import ResolveOrCreateUsuario
from services.webhook_registry_service import (
    ProcessadorVarreduraPendente,
    RegistroConexoesPostgres,
    RegistroEventosPostgres,
)
from services.webhook_service import ReceberEventoWebhook

logger = logging.getLogger(__name__)

_bearer_scheme = HTTPBearer(auto_error=False)

_DEV_MODE_USER = AuthenticatedUser(
    subject="dev-mode",
    email="dev@local",
    name="Usuário de desenvolvimento (AZ1_AUTH_MODE=disabled)",
    provider="disabled",
)


class AuthAPIError(Exception):
    """Erro HTTP de autenticação. O corpo é fixo (RNF02): não varia com a causa,
    para não funcionar como oráculo para quem está testando credenciais."""

    status_code = 401
    error = "unauthorized"
    message = "Token de autenticação ausente ou inválido."


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


# O `.joblib` é carregado uma vez e compartilhado. Estava embutido em
# `get_analyzer`; com o classificador passando a ser observado também no chat,
# deixá-lo lá faria o modelo ser desserializado duas vezes — e o shim de
# `sys.modules` viveria duplicado em dois lugares que teriam de concordar.
@lru_cache
def carregar_modelo_padrao():
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
        return carregar_modelo(MODELO_PADRAO)
    finally:
        for k, v in _saved.items():
            if v is None:
                sys.modules.pop(k, None)
            else:
                sys.modules[k] = v


@lru_cache
def get_analyzer() -> AnalyzeAudio:
    return AnalyzeAudio(transcriber=get_transcriber(), modelo=carregar_modelo_padrao())


# O classificador entra no chat como OBSERVADOR, e nada mais: o rótulo vai para
# `auditoria.mensagem.intencao` e não decide nem a busca, nem a recusa, nem a
# resposta.
#
# A distinção é o ponto. O modelo mede F1-macro 0,6736 contra os 0,85 do RNF03 —
# colocá-lo para decidir algo erraria em cerca de um terço das interações. Como
# observador, ele torna o RNF03 mensurável sobre tráfego real (hoje `intencao` é
# NULL em 100% das linhas) sem colocar a qualidade da resposta em suas mãos.
#
# Devolve None quando o modelo não pôde ser carregado: uma instalação sem o
# `.joblib` treinado continua conversando, apenas sem registrar a intenção.
@lru_cache
def get_classificador_de_intencao() -> Callable[[str], tuple[str, float]] | None:
    try:
        modelo = carregar_modelo_padrao()
    except Exception:
        logger.exception("Classificador indisponível; a intenção não será registrada.")
        return None

    from pln.classificador import prever_intencao

    return lambda texto: prever_intencao(modelo, texto)


def _historico_do_banco(conversa_id: str) -> list[tuple[str, str]]:
    """Turnos anteriores, lidos de `auditoria.mensagem`.

    Sem o `usuario_id` no filtro porque quem chama é o próprio modelo, já dentro
    de uma requisição autenticada cujo `conversation_id` veio do cliente. A rota
    de LEITURA da trilha (`routes/conversas.py`) filtra por usuário; aqui o que
    se busca é o contexto da conversa em andamento.
    """
    repositorio = get_conversa_repository()
    if isinstance(repositorio, PersistenciaDesligada):
        return []
    identificador = conversa_uuid(conversa_id)
    if identificador is None:
        return []
    with get_connection_pool().connection() as conexao, conexao.cursor() as cursor:
        cursor.execute(
            "SELECT papel, conteudo FROM auditoria.mensagem "
            "WHERE conversa_id = %s ORDER BY ordem",
            (identificador,),
        )
        return [(papel, conteudo) for papel, conteudo in cursor.fetchall()]


@lru_cache
def get_chat_answerer() -> AnswerChatMessage:
    settings = GeminiSettings.from_environment()
    model = GeminiChatModel.from_settings(
        settings,
        buscar_contexto=buscar_contexto_rag,
        carregar_historico=_historico_do_banco,
    )
    return AnswerChatMessage(model=model)


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
# A identidade vem de `AuthenticatedUser.domain_user_id`, preenchido por
# `ResolveOrCreateUsuario`. Substituiu o `GravarConsulta`, que gravava as mesmas
# linhas com `usuario_id = 0` — um id que, sendo a coluna GENERATED ALWAYS AS
# IDENTITY, não existe em banco algum criado pelo DDL. Ele só existia neste
# Supabase, inserido à mão, e foi aposentado por `05_migracao_usuario_zero.sql`.
#
# Degrada em vez de levantar porque gravar a trilha é EFEITO COLATERAL de
# `POST /chat`: sem `SUPABASE_DB_URL`, levantar aqui derrubaria a conversa
# inteira com 500. Mesma escolha de `get_alerta_dispatcher`, logo abaixo.
@lru_cache
def get_conversa_repository() -> ConversaRepository | PersistenciaDesligada:
    try:
        return ConversaRepository(
            pool=get_connection_pool(),
            armazenamento=S3ObjectStorage.from_settings(S3StorageSettings.from_environment()),
        )
    except BancoNaoConfigurado as erro:
        return PersistenciaDesligada(str(erro))


# Diferente de `get_conversa_repository`, este NÃO degrada: aqui o banco não é
# acessório, é a razão de o endpoint existir. Um `/tasks` que responde 200 com
# lista vazia sem banco seria a mesma mentira que os dados de exemplo do
# frontend. `BancoNaoConfigurado` vira 503 no manipulador de `main.py`.
@lru_cache
def get_portfolio_repository() -> PortfolioRepository:
    return PortfolioRepository(pool=get_connection_pool())


# Mesmo raciocínio de `get_alerta_dispatcher`, logo abaixo: o Agente é EFEITO
# de `POST /chat` existir, não a razão do endpoint. Sem `SUPABASE_DB_URL`,
# degrada para `AgenteDesligado` em vez de estourar a resolução das
# dependências e derrubar a rota inteira com 500.
@lru_cache
def get_agente() -> ExecutarIntencao | AgenteDesligado:
    try:
        return ExecutarIntencao(portfolio=get_portfolio_repository())
    except BancoNaoConfigurado as erro:
        return AgenteDesligado(str(erro))


@lru_cache
def get_alerta_registrador() -> RegistrarAssinante:
    return RegistrarAssinante(engine=obter_engine())


@lru_cache
def get_alerta_desativador() -> DesativarAssinante:
    return DesativarAssinante(engine=obter_engine())


@lru_cache
def get_alerta_listador() -> ListarAssinantes:
    return ListarAssinantes(engine=obter_engine())


# Os dois provedores abaixo sustentam EFEITOS COLATERAIS de rotas que existem
# por outro motivo — gravar a trilha em `POST /chat`, despachar alerta em
# `POST /audio/{id}/analyze`. Por isso degradam em vez de levantar: sem
# `SUPABASE_DB_URL`, `obter_engine()` estoura durante a resolução das
# dependências e a rota inteira responde 500, mesmo que a resposta ao usuário
# não dependesse de banco nenhum.
#
# Os outros quatro provedores continuam levantando de propósito: ali o banco
# não é acessório, é a razão do endpoint. `BancoNaoConfigurado` vira 503 no
# manipulador de `main.py`.
@lru_cache
def get_alerta_dispatcher() -> DispatcherAlerta | DespachoDesligado:
    try:
        return DispatcherAlerta(
            engine=obter_engine(), configuracao=ConfiguracaoAlertas.carregar()
        )
    except BancoNaoConfigurado as erro:
        return DespachoDesligado(str(erro))


@lru_cache
def get_listador_auditoria() -> ListarConsultas:
    return ListarConsultas(engine=obter_engine())


@lru_cache
def get_token_verifier() -> SupabaseTokenVerifier:
    return SupabaseTokenVerifier(SupabaseAuthSettings.from_environment())


@lru_cache
def get_usuario_resolver() -> ResolveOrCreateUsuario | None:
    # Best-effort de propósito: nada mais na API depende do banco relacional
    # hoje, então uma falha aqui não pode derrubar a autenticação inteira.
    # Ver ResolveOrCreateUsuario em src/services/usuario_service.py.
    dsn = os.environ.get("SUPABASE_DB_URL", "")
    if not dsn:
        logger.warning(
            "SUPABASE_DB_URL não configurada: login não será ligado a portfolio.usuario."
        )
        return None
    try:
        pool = ConnectionPool(dsn, min_size=1, max_size=5, open=True)
    except Exception:
        logger.exception("Falha ao abrir o pool de SUPABASE_DB_URL; login não será ligado a portfolio.usuario.")
        return None
    return ResolveOrCreateUsuario(pool)


def require_authenticated_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    verifier: SupabaseTokenVerifier = Depends(get_token_verifier),
    usuario_resolver: ResolveOrCreateUsuario | None = Depends(get_usuario_resolver),
) -> AuthenticatedUser:
    if verifier.settings.mode is AuthMode.DISABLED:
        return _DEV_MODE_USER

    if credentials is None:
        raise AuthAPIError()

    try:
        user = verifier.verify(credentials.credentials)
    except AuthError as exc:
        # A causa vai só para o log (RNF02 proíbe credenciais nos registros); o
        # corpo da resposta é sempre o mesmo, para não servir de oráculo.
        logger.warning("Falha de autenticação (%s): %s", exc.code.name, exc.detail)
        raise AuthAPIError() from exc

    if usuario_resolver is not None:
        try:
            domain_user = usuario_resolver.resolve(auth_user_id=user.subject, email=user.email, name=user.name)
            user = dataclasses.replace(user, domain_user_id=domain_user.id)
        except Exception:
            # Autenticação (RNF02) não depende de portfolio.usuario: uma falha
            # aqui não deve virar 401 nem 500 para quem só quer usar o agente.
            logger.exception("Não foi possível ligar %s a portfolio.usuario.", user.email)

    return user


@lru_cache
def get_webhook_connection_pool() -> ConnectionPool:
    """Mesmo banco do domínio por padrão, em sessão restrita aos webhooks.

    DATABASE_URL seleciona uma base explícita; sem ela, usa SUPABASE_DB_URL.
    O papel az1_webhook é obrigatório e não compartilha sessões com az1_app.
    """
    dsn = os.environ.get("DATABASE_URL", "").strip()
    if not dsn:
        dsn = PostgresSettings.from_environment().dsn
    return abrir_pool(PostgresSettings(dsn=dsn, papel="az1_webhook"))


# A publicação no barramento é ADITIVA e OPCIONAL. Sem `RABBITMQ_URL`, devolve o
# publicador no-op (`PublicacaoDesligada`) e o comportamento da Sprint 4 fica
# intacto — o composto `ProcessadorComPublicacao` passa a ser indistinguível do
# processador anterior, e os testes de contrato de webhook seguem verdes. Com
# `RABBITMQ_URL`, devolve o publicador real, que marca o delta E publica.
#
# `lru_cache` garante uma conexão só ao broker por processo, como nos demais
# provedores deste módulo.
@lru_cache
def get_publicador() -> Publicador:
    settings = MensageriaSettings.from_environment()
    if settings is None:
        return PublicacaoDesligada()
    return PublicadorRabbitMQ(settings)


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
    pool = get_webhook_connection_pool()
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
        processador=ProcessadorComPublicacao(
            ProcessadorVarreduraPendente(pool, PROVEDOR_GRAPH, TIPOS_GRAPH),
            get_publicador(),
        ),
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
    pool = get_webhook_connection_pool()
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
        processador=ProcessadorComPublicacao(
            ProcessadorVarreduraPendente(pool, PROVEDOR_DRIVE, TIPOS_DRIVE),
            get_publicador(),
        ),
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
