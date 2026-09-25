from __future__ import annotations

from dataclasses import dataclass

from rag import indexador
from rag.embedder import vetorizar_consulta


@dataclass(frozen=True)
class ResultadoBusca:
    texto: str
    score: float
    projeto_id: str
    tipo_documento: str
    secao: str
    arquivo_origem: str

    # O id do chunk na coleção vetorial. `indexador.buscar` sempre o devolveu, e
    # era descartado exatamente aqui — o que tornava
    # `auditoria.mensagem_fonte.chunk_id` (NOT NULL) impossível de preencher e,
    # com ele, o RNF12 inverificável: sem o id não há como voltar do que a
    # resposta afirmou para o trecho que a fundamentou.
    chunk_id: str = ""


def buscar(
    query: str,
    *,
    n_resultados: int = 5,
    projeto_id: str | None = None,
    tipo_documento: str | None = None,
) -> list[ResultadoBusca]:
    """Vetoriza a query e busca os chunks mais relevantes no índice."""
    # `vetorizar_consulta`, e não a de documento: o modelo projeta pergunta e
    # trecho em lados diferentes do mesmo espaço. Ela também é cacheada, o que
    # evita pagar os 12 s do limite de requisições quando a pergunta se repete.
    embedding = vetorizar_consulta(query)

    # vecs aceita no máximo uma entrada por filtro: dois critérios exigem $and.
    condicoes: list[dict] = []
    if projeto_id:
        condicoes.append({"projeto_id": {"$eq": projeto_id}})
    if tipo_documento:
        condicoes.append({"tipo_documento": {"$eq": tipo_documento}})

    filtro: dict | None = None
    if len(condicoes) == 1:
        filtro = condicoes[0]
    elif condicoes:
        filtro = {"$and": condicoes}

    brutos = indexador.buscar(embedding, n_resultados=n_resultados, filtro=filtro)

    return [
        ResultadoBusca(
            texto=r["texto"],
            score=float(1 - r["distancia"]),  # cosine distance → similarity score
            projeto_id=r["metadados"].get("projeto_id", ""),
            tipo_documento=r["metadados"].get("tipo_documento", ""),
            secao=r["metadados"].get("secao", ""),
            arquivo_origem=r["metadados"].get("arquivo_origem", ""),
            chunk_id=r["id"],
        )
        for r in brutos
    ]


# BUSCA FOCADA, COM RECUO.
#
# A classificação sugere onde procurar (ver `services/foco_da_busca.py`), mas
# sugerir não é mandar: com F1-macro de 0,87, cerca de uma em oito sugestões
# está errada, e um filtro errado esconde justamente o trecho que responderia.
#
# O recuo é o que torna a sugestão segura. Se a busca focada não trouxer
# material suficientemente relevante, a busca ampla roda e prevalece. O custo
# do erro passa a ser uma consulta vetorial a mais — não uma resposta pior.
#
# E ele é barato: `vetorizar_consulta` é cacheada por texto, então as duas
# buscas da mesma pergunta pagam UMA chamada de embedding. O que se repete é a
# consulta ao índice, que é local.
def buscar_com_recuo(
    query: str,
    *,
    n_resultados: int = 5,
    projeto_id: str | None = None,
    tipo_documento: str | None = None,
    score_minimo: float = 0.0,
) -> tuple[list[ResultadoBusca], bool]:
    """Devolve (resultados, focou) — `focou` diz se o filtro foi o que valeu.

    O segundo elemento não é detalhe: sem ele, quem chama não tem como saber se
    está olhando o resultado da sugestão ou o do recuo, e a decisão viraria
    invisível no log e na auditoria.
    """
    if projeto_id is None and tipo_documento is None:
        return buscar(query, n_resultados=n_resultados), False

    focados = buscar(
        query,
        n_resultados=n_resultados,
        projeto_id=projeto_id,
        tipo_documento=tipo_documento,
    )
    if any(r.score >= score_minimo for r in focados):
        return focados, True

    # O filtro não achou nada que se sustente. Pode ser classificação errada,
    # pode ser que o projeto não tenha aquele documento — as duas se corrigem
    # do mesmo jeito.
    return buscar(query, n_resultados=n_resultados), False

