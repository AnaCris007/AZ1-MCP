# Leitura do domínio de portfólio.
#
# As tabelas de `portfolio` tinham dado semeado e NENHUM leitor: 8 projetos, 37
# artefatos e 18 pendências que nenhuma linha de Python consultava. Enquanto
# isso, o frontend chamava `/api/v1/tasks` e `/api/v1/calendar/events`, que não
# existiam, e caía num `console.info` para mostrar dados de exemplo como se
# fossem reais.
#
# POR QUE ISTO NÃO É O MESMO QUE O RAG
# ------------------------------------
# O índice vetorial responde por similaridade sobre texto: ótimo para "quais os
# riscos da ventilação", inútil para "quais projetos estão com desvio acima de
# 10 pontos". A segunda é uma pergunta de WHERE sobre uma coluna, e nenhum
# trecho isolado a contém. As duas fontes são complementares, não substitutas.
#
# POR QUE psycopg E NÃO SQLAlchemy
# --------------------------------
# `alerta_service` e `auditoria_service` usam SQLAlchemy por herança, e mantêm
# um segundo pool contra o mesmo Supabase — que cobra conexão. Todo acesso
# relacional novo converge no pool de `database_service`, que é também o único
# que aplica o `SET ROLE` do `configure=`.

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from psycopg_pool import ConnectionPool

# Espelha o CHECK de `portfolio.pendencia.situacao`. Duplicar tem um custo — as
# duas listas podem divergir —, pago por um teste que lê o DDL e compara.
SITUACOES_VALIDAS = frozenset({"aberta", "em_tratamento", "materializada", "resolvida"})

SITUACAO_RESOLVIDA = "resolvida"
SITUACAO_ABERTA = "aberta"


class SituacaoInvalida(ValueError):
    """Valor fora do domínio de `portfolio.pendencia.situacao`."""


@dataclass(frozen=True)
class SituacaoProjeto:
    """Uma linha de `portfolio.vw_projeto_situacao`.

    A view já resolve as contagens de pendências e artefatos e os dois JOINs com
    portfólio e líder. Refazer isso à mão aqui seria duplicar lógica que o DDL
    já mantém — e que o time revisa junto com o modelo.
    """

    id: int
    codigo: str
    nome: str
    fase: str
    status: str
    data_inicio: date | None
    data_termino_prevista: date | None
    percentual_previsto: float
    percentual_avanco: float
    desvio_pp: float
    lider: str
    lider_email: str
    pendencias_abertas: int
    artefatos: int


@dataclass(frozen=True)
class Pendencia:
    id: int
    projeto_codigo: str
    projeto_nome: str
    codigo: str | None
    tipo: str
    titulo: str
    descricao: str | None
    criticidade: str | None
    responsavel: str | None
    prazo: date | None
    situacao: str

    @property
    def resolvida(self) -> bool:
        return self.situacao == SITUACAO_RESOLVIDA


_SQL_PROJETOS = """
SELECT id, codigo, nome, fase, status,
       data_inicio, data_termino_prevista,
       percentual_previsto, percentual_avanco, desvio_pp,
       lider, lider_email, pendencias_abertas, artefatos
  FROM portfolio.vw_projeto_situacao
 ORDER BY desvio_pp ASC, codigo ASC
"""

# `desvio_pp` crescente põe o projeto mais atrasado primeiro — é a ordem em que
# um PMO quer ler, e a mesma que serve de resumo para o chat.

_SQL_PENDENCIAS = """
SELECT p.id, j.codigo, j.nome, p.codigo, p.tipo, p.titulo, p.descricao,
       p.criticidade, p.responsavel, p.prazo, p.situacao
  FROM portfolio.pendencia p
  JOIN portfolio.projeto  j ON j.id = p.projeto_id
 ORDER BY p.prazo NULLS LAST, p.id
"""

_SQL_UMA_PENDENCIA = """
SELECT p.id, j.codigo, j.nome, p.codigo, p.tipo, p.titulo, p.descricao,
       p.criticidade, p.responsavel, p.prazo, p.situacao
  FROM portfolio.pendencia p
  JOIN portfolio.projeto  j ON j.id = p.projeto_id
 WHERE p.id = %s
"""

# Só `situacao`. Ver a nota sobre imutabilidade em `alterar_situacao`.
_SQL_ALTERAR_SITUACAO = """
UPDATE portfolio.pendencia SET situacao = %s WHERE id = %s RETURNING id
"""


def _para_projeto(linha: tuple) -> SituacaoProjeto:
    # Mapeamento POSICIONAL: os índices seguem a ordem das colunas de
    # `_SQL_PROJETOS`, que segue a de `portfolio.vw_projeto_situacao`. Mexer na
    # ordem em qualquer um dos três exige renumerar aqui — e o erro não avisa:
    # trocar `lider` com `lider_email` mantém os dois como texto e passa.
    return SituacaoProjeto(
        id=linha[0],
        codigo=linha[1],
        nome=linha[2],
        fase=linha[3],
        status=linha[4],
        data_inicio=linha[5],
        data_termino_prevista=linha[6],
        percentual_previsto=float(linha[7] or 0),
        percentual_avanco=float(linha[8] or 0),
        desvio_pp=float(linha[9] or 0),
        lider=linha[10] or "",
        lider_email=linha[11] or "",
        pendencias_abertas=linha[12] or 0,
        artefatos=linha[13] or 0,
    )


def _para_pendencia(linha: tuple) -> Pendencia:
    return Pendencia(
        id=linha[0],
        projeto_codigo=linha[1],
        projeto_nome=linha[2],
        codigo=linha[3],
        tipo=linha[4],
        titulo=linha[5],
        descricao=linha[6],
        criticidade=linha[7],
        responsavel=linha[8],
        prazo=linha[9],
        situacao=linha[10],
    )


class PortfolioRepository:
    def __init__(self, pool: ConnectionPool) -> None:
        self._pool = pool

    def situacao_dos_projetos(self) -> tuple[SituacaoProjeto, ...]:
        with self._pool.connection() as conexao, conexao.cursor() as cursor:
            cursor.execute(_SQL_PROJETOS)
            return tuple(_para_projeto(linha) for linha in cursor.fetchall())

    def pendencias(self) -> tuple[Pendencia, ...]:
        with self._pool.connection() as conexao, conexao.cursor() as cursor:
            cursor.execute(_SQL_PENDENCIAS)
            return tuple(_para_pendencia(linha) for linha in cursor.fetchall())

    def obter_pendencia(self, pendencia_id: int) -> Pendencia | None:
        with self._pool.connection() as conexao, conexao.cursor() as cursor:
            cursor.execute(_SQL_UMA_PENDENCIA, (pendencia_id,))
            linha = cursor.fetchone()
            return _para_pendencia(linha) if linha else None

    def alterar_situacao(self, *, pendencia_id: int, situacao: str) -> Pendencia | None:
        """Altera APENAS a situação da pendência. Devolve None se ela não existe.

        Título e descrição não são alteráveis, e a razão é concreta: esse texto
        veio de `04_Riscos_e_Problemas.xlsx` e **está vetorizado** em
        `vecs.documentos_metro`. Editá-lo aqui faria a linha relacional e o
        trecho citado pelo chat discordarem — que é exatamente a incoerência que
        o RNF12 existe para impedir. Mover de projeto também não: `projeto_id` é
        chave estrangeira, não rótulo.

        ATENÇÃO À RLS: `portfolio.pendencia` tem RLS ligada com política apenas
        de SELECT (`03_rls_policies.sql`). Este UPDATE funciona hoje porque a
        aplicação conecta como dono do schema. No dia em que `AZ1_DB_ROLE` for
        preenchida, ele passa a atualizar ZERO linhas **sem erro** — e este
        método devolveria None como se a pendência não existisse. Criar a
        política de UPDATE é pré-requisito de ligar o papel.
        """
        if situacao not in SITUACOES_VALIDAS:
            raise SituacaoInvalida(
                f"situacao {situacao!r} fora do domínio: {sorted(SITUACOES_VALIDAS)}."
            )

        with self._pool.connection() as conexao:
            with conexao.cursor() as cursor:
                cursor.execute(_SQL_ALTERAR_SITUACAO, (situacao, pendencia_id))
                if cursor.fetchone() is None:
                    return None
            # Relê depois do UPDATE, na mesma transação: é a linha real que volta
            # para o cliente, e não o que ele mandou. Sem isso a interface exibe
            # o que pediu, e não o que o banco aceitou.
            with conexao.cursor() as cursor:
                cursor.execute(_SQL_UMA_PENDENCIA, (pendencia_id,))
                linha = cursor.fetchone()
        return _para_pendencia(linha) if linha else None
