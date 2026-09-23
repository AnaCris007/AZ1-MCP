# Rotas do domínio de portfólio.
#
# As três existem porque o frontend já as chamava e elas não existiam:
# `TasksView.jsx` e `CalendarView.jsx` caíam num `console.info('backend
# indisponível, usando dados de exemplo')` e renderizavam uma lista fixa. Numa
# ferramenta de PMO, dado de exemplo indistinguível de dado real é pior do que
# tela vazia.

from __future__ import annotations

from collections.abc import Sequence
from datetime import date

from fastapi import APIRouter, Depends

from az1_api.dependencies import get_portfolio_repository
from schemas.portfolio import (
    CalendarDayResponse,
    CalendarEventResponse,
    CalendarResponse,
    ProjetoResponse,
    ProjetosResponse,
    TaskPatchRequest,
    TaskResponse,
)
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
    projetos: Sequence[SituacaoProjeto], pendencias: Sequence[Pendencia]
) -> list[CalendarDayResponse]:
    """Agrupa marcos e prazos por dia.

    Não há tabela de compromissos no modelo: não existe reunião, nem hora. As
    duas únicas datas reais são `projeto.data_termino_prevista` e
    `pendencia.prazo`. Inventar um horário para preencher a coluna da interface
    seria fabricar dado — exatamente o que esta entrega veio corrigir; por isso
    o campo `time` não existe no contrato.
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

    return [
        CalendarDayResponse(
            date=formatar_dia(dia),
            weekday=formatar_dia_da_semana(dia),
            events=eventos,
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


@router.get("/calendar/events", response_model=CalendarResponse)
def listar_eventos(repositorio: Repositorio = Depends(get_portfolio_repository)):
    return CalendarResponse(
        days=montar_agenda(
            repositorio.situacao_dos_projetos(), repositorio.pendencias()
        )
    )
