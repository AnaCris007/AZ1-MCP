# Rotas do domínio de portfólio.
#
# As três existem porque o frontend já as chamava e elas não existiam:
# `TasksView.jsx` e `CalendarView.jsx` caíam num `console.info('backend
# indisponível, usando dados de exemplo')` e renderizavam uma lista fixa. Numa
# ferramenta de PMO, dado de exemplo indistinguível de dado real é pior do que
# tela vazia.

from __future__ import annotations

from collections.abc import Sequence
from datetime import date, time

from fastapi import APIRouter, Depends, Response

from az1_api.dependencies import (
    get_evento_local_repository,
    get_portfolio_repository,
    require_authenticated_user,
)
from schemas.portfolio import (
    CalendarDayResponse,
    CalendarEventResponse,
    CalendarResponse,
    EventoLocalCreateRequest,
    EventoLocalResponse,
    ProjetoResponse,
    ProjetosResponse,
    TaskPatchRequest,
    TaskResponse,
)
from services.auth_service import AuthenticatedUser
from services.evento_local_repository import EventoLocal, EventoLocalRepository
from services.portfolio_repository import (
    SITUACAO_ABERTA,
    SITUACAO_RESOLVIDA,
    Pendencia,
    PortfolioRepository,
    SituacaoProjeto,
)

router = APIRouter(tags=["portfolio"])

Repositorio = PortfolioRepository


class PortfolioAPIError(Exception):
    def __init__(self, status_code: int, error: str, message: str) -> None:
        self.status_code = status_code
        self.error = error
        self.message = message


def _identidade(usuario: AuthenticatedUser) -> int:
    """O id de domínio, ou 422 se ele não existe.

    É None com `AZ1_AUTH_MODE=disabled` e quando `ResolveOrCreateUsuario`
    falhou (mesmo caso de `routes/conversas.py:_identidade`). Sem identidade
    não há dono para atribuir a um evento criado ou apagado.
    """
    if usuario.domain_user_id is None:
        raise PortfolioAPIError(
            422, "sem_identidade", "A sessão não está ligada a um usuário do portfólio."
        )
    return usuario.domain_user_id


# `criticidade` tem quatro valores no banco e a interface tem três faixas. O
# colapso é com perda — Crítico e Alto voltam iguais —, e só é aceitável porque
# o PATCH não escreve criticidade: nada é gravado a partir deste mapa.
_PRIORIDADE_POR_CRITICIDADE = {
    "Crítico": "alta",
    "Alto": "alta",
    "Moderado": "media",
    "Baixo": "baixa",
}
_PRIORIDADE_PADRAO = "media"

# Formatar data em português com `locale` é frágil: o nome do mês muda entre o
# Windows da máquina de desenvolvimento e a imagem Alpine do contêiner, e a
# falha aparece como texto errado, não como exceção. Tuplas fixas são
# determinísticas e testáveis.
_MESES = (
    "janeiro", "fevereiro", "março", "abril", "maio", "junho",
    "julho", "agosto", "setembro", "outubro", "novembro", "dezembro",
)
_DIAS_DA_SEMANA = (
    "segunda-feira", "terça-feira", "quarta-feira", "quinta-feira",
    "sexta-feira", "sábado", "domingo",
)


def formatar_dia(dia: date) -> str:
    return f"{dia.day} de {_MESES[dia.month - 1]}"


def formatar_dia_da_semana(dia: date) -> str:
    return _DIAS_DA_SEMANA[dia.weekday()]


def _para_task(pendencia: Pendencia) -> TaskResponse:
    return TaskResponse(
        id=str(pendencia.id),
        title=pendencia.titulo,
        project=f"{pendencia.projeto_codigo} — {pendencia.projeto_nome}",
        priority=_PRIORIDADE_POR_CRITICIDADE.get(
            pendencia.criticidade or "", _PRIORIDADE_PADRAO
        ),
        dueDate=pendencia.prazo.isoformat() if pendencia.prazo else "",
        description=pendencia.descricao or "",
        done=pendencia.resolvida,
    )


def _para_projeto(projeto: SituacaoProjeto) -> ProjetoResponse:
    return ProjetoResponse(
        codigo=projeto.codigo,
        nome=projeto.nome,
        portfolio=projeto.portfolio,
        fase=projeto.fase,
        status=projeto.status,
        percentual_previsto=projeto.percentual_previsto,
        percentual_avanco=projeto.percentual_avanco,
        desvio_pp=projeto.desvio_pp,
        data_termino_prevista=(
            projeto.data_termino_prevista.isoformat()
            if projeto.data_termino_prevista
            else ""
        ),
        lider=projeto.lider,
        pendencias_abertas=projeto.pendencias_abertas,
        artefatos=projeto.artefatos,
    )


def montar_agenda(
    projetos: Sequence[SituacaoProjeto],
    pendencias: Sequence[Pendencia],
    eventos_locais: Sequence[EventoLocal] = (),
) -> list[CalendarDayResponse]:
    """Agrupa marcos, prazos e eventos próprios por dia.

    `marco` e `prazo` continuam sem hora: as únicas datas reais para eles são
    `projeto.data_termino_prevista` e `pendencia.prazo`, sem componente de
    horário no banco, e inventar um seria fabricar dado. `evento` é a
    exceção — criado pelo próprio usuário (ver
    `services.evento_local_repository`), com hora real quando informada.
    """
    por_dia: dict[date, list[CalendarEventResponse]] = {}

    for projeto in projetos:
        if projeto.data_termino_prevista is None:
            continue
        por_dia.setdefault(projeto.data_termino_prevista, []).append(
            CalendarEventResponse(
                id=f"marco-{projeto.codigo}",
                title=f"Término previsto — {projeto.nome}",
                type="marco",
                project=projeto.codigo,
            )
        )

    for pendencia in pendencias:
        if pendencia.prazo is None or pendencia.resolvida:
            continue
        por_dia.setdefault(pendencia.prazo, []).append(
            CalendarEventResponse(
                id=f"prazo-{pendencia.id}",
                title=pendencia.titulo,
                type="prazo",
                project=pendencia.projeto_codigo,
            )
        )

    for evento in eventos_locais:
        por_dia.setdefault(evento.data, []).append(
            CalendarEventResponse(
                id=f"evento-{evento.id}",
                title=evento.titulo,
                type="evento",
                time="" if evento.hora is None else evento.hora.strftime("%H:%M"),
            )
        )

    return [
        CalendarDayResponse(
            date=formatar_dia(dia),
            weekday=formatar_dia_da_semana(dia),
            events=eventos,
            iso=dia.isoformat(),
        )
        for dia, eventos in sorted(por_dia.items())
    ]


@router.get("/projetos", response_model=ProjetosResponse)
def listar_projetos(repositorio: Repositorio = Depends(get_portfolio_repository)):
    return ProjetosResponse(
        projetos=[_para_projeto(p) for p in repositorio.situacao_dos_projetos()]
    )


@router.get("/tasks", response_model=list[TaskResponse])
def listar_tasks(repositorio: Repositorio = Depends(get_portfolio_repository)):
    return [_para_task(p) for p in repositorio.pendencias()]


@router.patch("/tasks/{pendencia_id}", response_model=TaskResponse)
def atualizar_task(
    pendencia_id: int,
    payload: TaskPatchRequest,
    repositorio: Repositorio = Depends(get_portfolio_repository),
):
    """Marca ou desmarca uma pendência.

    Só `situacao` é gravada. Os outros campos que o modal de edição envia são
    aceitos e ignorados — ver a justificativa em
    `PortfolioRepository.alterar_situacao`.

    `done: false` devolve a pendência para `aberta`, o que **perde estado**: uma
    que estava em `em_tratamento`, marcada e desmarcada, não volta para lá. É
    limitação de representar quatro situações num booleano, e a saída para quem
    precisa das quatro é mandar `situacao` explicitamente.
    """
    situacao = payload.situacao
    if situacao is None:
        if payload.done is None:
            raise PortfolioAPIError(
                422, "payload_invalido", "Informe `done` ou `situacao`."
            )
        situacao = SITUACAO_RESOLVIDA if payload.done else SITUACAO_ABERTA

    try:
        atualizada = repositorio.alterar_situacao(
            pendencia_id=pendencia_id, situacao=situacao
        )
    except ValueError as erro:
        raise PortfolioAPIError(422, "situacao_invalida", str(erro)) from erro

    if atualizada is None:
        raise PortfolioAPIError(
            404, "pendencia_nao_encontrada", f"Pendência {pendencia_id} não encontrada."
        )
    return _para_task(atualizada)


def _para_evento_local(evento: EventoLocal) -> EventoLocalResponse:
    return EventoLocalResponse(
        id=evento.id,
        title=evento.titulo,
        date=evento.data.isoformat(),
        time="" if evento.hora is None else evento.hora.strftime("%H:%M"),
        description=evento.descricao,
    )


@router.get("/calendar/events", response_model=CalendarResponse)
def listar_eventos(
    repositorio: Repositorio = Depends(get_portfolio_repository),
    repositorio_eventos_locais: EventoLocalRepository = Depends(get_evento_local_repository),
    usuario: AuthenticatedUser = Depends(require_authenticated_user),
):
    # Sem identidade (AZ1_AUTH_MODE=disabled, ou ResolveOrCreateUsuario
    # falhou) não há "meus eventos". E, como migração de banco e deploy de
    # código são passos separados neste projeto, uma instalação que ainda não
    # rodou 07_evento_local.sql não pode derrubar a Agenda inteira por causa
    # disso — a Agenda segue respondendo só sem essa seção.
    try:
        eventos_locais = (
            repositorio_eventos_locais.listar(usuario.domain_user_id)
            if usuario.domain_user_id is not None
            else []
        )
    except Exception:
        eventos_locais = []

    return CalendarResponse(
        days=montar_agenda(
            repositorio.situacao_dos_projetos(),
            repositorio.pendencias(),
            eventos_locais,
        )
    )


@router.post("/calendar/events", response_model=EventoLocalResponse, status_code=201)
def criar_evento_local(
    payload: EventoLocalCreateRequest,
    repositorio: EventoLocalRepository = Depends(get_evento_local_repository),
    usuario: AuthenticatedUser = Depends(require_authenticated_user),
):
    usuario_id = _identidade(usuario)

    titulo = payload.titulo.strip()
    if not titulo:
        raise PortfolioAPIError(422, "titulo_obrigatorio", "Informe um título para o evento.")

    try:
        data = date.fromisoformat(payload.data)
    except ValueError as erro:
        raise PortfolioAPIError(422, "data_invalida", "Data inválida; use o formato AAAA-MM-DD.") from erro

    hora = None
    if payload.hora:
        try:
            hora = time.fromisoformat(payload.hora)
        except ValueError as erro:
            raise PortfolioAPIError(422, "hora_invalida", "Hora inválida; use o formato HH:MM.") from erro

    criado = repositorio.criar(
        usuario_id=usuario_id,
        titulo=titulo,
        data=data,
        hora=hora,
        descricao=payload.descricao.strip(),
    )
    return _para_evento_local(criado)


@router.delete("/calendar/events/{evento_id}", status_code=204)
def apagar_evento_local(
    evento_id: int,
    repositorio: EventoLocalRepository = Depends(get_evento_local_repository),
    usuario: AuthenticatedUser = Depends(require_authenticated_user),
):
    usuario_id = _identidade(usuario)
    if not repositorio.apagar(usuario_id=usuario_id, evento_id=evento_id):
        raise PortfolioAPIError(404, "evento_nao_encontrado", f"Evento {evento_id} não encontrado.")
    return Response(status_code=204)
