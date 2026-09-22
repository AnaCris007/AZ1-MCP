"""Contratos HTTP do domínio de portfólio.

Os nomes dos campos em `TaskResponse` e `CalendarDayResponse` **não** seguem a
convenção do resto da API (português, snake_case): eles espelham exatamente o
que `TasksView.jsx` e `CalendarView.jsx` já leem. Renomear aqui obrigaria a
mexer no frontend sem nenhum ganho, e a prioridade é fazer a interface parar de
exibir dados de exemplo como se fossem reais.
"""

from __future__ import annotations

from pydantic import BaseModel


class ProjetoResponse(BaseModel):
    codigo: str
    nome: str
    fase: str
    status: str
    percentual_previsto: float
    percentual_avanco: float
    desvio_pp: float
    data_termino_prevista: str = ""
    lider: str = ""
    pendencias_abertas: int = 0
    artefatos: int = 0


class ProjetosResponse(BaseModel):
    projetos: list[ProjetoResponse]


class TaskResponse(BaseModel):
    id: str
    title: str
    project: str
    priority: str
    dueDate: str = ""  # noqa: N815 — o frontend já lê com este nome
    description: str = ""
    done: bool = False


class TaskPatchRequest(BaseModel):
    """O que o frontend envia num PATCH.

    `done` é o único campo que chega ao banco. Os demais existem porque o modal
    de edição os envia inteiros — aceitá-los e ignorá-los é mais honesto que
    recusar a requisição com 422 por causa de campos que o cliente sempre mandou.

    `situacao` é a saída para quem quiser os quatro estados do CHECK em vez do
    booleano; ela vence quando presente.
    """

    done: bool | None = None
    situacao: str | None = None


class CalendarEventResponse(BaseModel):
    id: str
    title: str
    type: str
    project: str = ""


class CalendarDayResponse(BaseModel):
    date: str
    weekday: str
    events: list[CalendarEventResponse]


class CalendarResponse(BaseModel):
    days: list[CalendarDayResponse]
