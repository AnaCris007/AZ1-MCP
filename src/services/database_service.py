# Acesso ao banco relacional do Supabase.
#
# Até aqui o projeto tinha o modelo inteiro em SQL — 14 tabelas nos schemas
# `portfolio` e `auditoria`, com RLS, views e trigger — e nenhuma linha de
# Python que falasse com ele. Este módulo é essa ponte.
#
# É o MESMO banco do índice vetorial. `SUPABASE_DB_URL` serve aos dois: o
# schema `vecs` (chunks do RAG, via `src/rag/indexador.py`) e os schemas
# `portfolio`/`auditoria` (aqui). Isso é deliberado — é o que permite
# `auditoria.mensagem_fonte.chunk_id` apontar para um chunk sem consulta
# cruzada entre instâncias.
#
# SOBRE O PAPEL E A RLS
# ---------------------
# O DDL cria `az1_app` e ativa RLS nas 14 tabelas, com policies que dependem de
# `portfolio.usuario_atual()`, que por sua vez lê o `sub` do JWT em
# `request.jwt.claims`.
#
# Enquanto a aplicação não autentica, esse claim não existe: assumir `az1_app`
# agora faria as policies negarem tudo, porque `usuario_atual()` devolveria
# NULL. Por isso o papel é OPCIONAL e vem de `AZ1_DB_ROLE`.
#
# A consequência de deixá-lo vazio precisa ser dita sem eufemismo: conectando
# como dono do banco, **a RLS não é aplicada**. É débito de segurança conhecido,
# ligado ao RNF02, e a variável existe para ser preenchida assim que o login
# entrar — não para ser esquecida.
#
# Quando `AZ1_DB_ROLE` está definida e o `SET ROLE` falha, a conexão falha junto,
# de propósito. Cair em silêncio para o dono seria trocar a postura de segurança
# sem ninguém perceber.

from __future__ import annotations

import os
from dataclasses import dataclass

from psycopg import Connection
from psycopg_pool import ConnectionPool

# Um pool pequeno: o Supabase cobra conexões, e o tráfego desta fase é baixo.
TAMANHO_MINIMO_PADRAO = 1
TAMANHO_MAXIMO_PADRAO = 4

# Segundos que uma requisição espera por uma conexão livre antes de desistir.
# Sem limite, uma rajada enfileira requisições até estourar o orçamento de 15 s
# do RNF01 sem que nada acuse.
ESPERA_MAXIMA_PADRAO = 5.0


class BancoNaoConfigurado(RuntimeError):
    """`SUPABASE_DB_URL` ausente ou vazia."""


@dataclass(frozen=True)
class PostgresSettings:
    dsn: str
    papel: str | None = None
    tamanho_minimo: int = TAMANHO_MINIMO_PADRAO
    tamanho_maximo: int = TAMANHO_MAXIMO_PADRAO
    espera_maxima: float = ESPERA_MAXIMA_PADRAO

    @classmethod
    def from_environment(cls) -> PostgresSettings:
        dsn = os.environ.get("SUPABASE_DB_URL", "").strip()
        if not dsn:
            raise BancoNaoConfigurado(
                "SUPABASE_DB_URL não configurada. Use a connection string PostgreSQL do "
                "Supabase (Settings → Database → Connection string → URI). É a mesma URL "
                "usada pelo índice vetorial."
            )
        # String vazia e variável ausente significam a mesma coisa aqui: sem papel.
        papel = os.environ.get("AZ1_DB_ROLE", "").strip() or None
        return cls(dsn=dsn, papel=papel)


# Roda a cada conexão nova do pool, e não a cada consulta: `SET ROLE` vale pela
# sessão inteira, então repetir por consulta seria desperdício.
def _configurar_conexao(conexao: Connection, papel: str | None) -> None:
    if papel is None:
        return
    # Identificador não pode ser parametrizado; por isso `papel` é validado na
    # construção das settings e não vem de entrada de usuário.
    with conexao.cursor() as cursor:
        cursor.execute(f"SET ROLE {_identificador_seguro(papel)}")
    # O callback do pool deve terminar sem transação aberta.
    conexao.commit()


# `SET ROLE` não aceita parâmetro ligado, então o nome entra no SQL por
# interpolação. A validação abaixo é o que impede que uma variável de ambiente
# mal preenchida vire injeção.
def _identificador_seguro(nome: str) -> str:
    if not nome.replace("_", "").isalnum():
        raise ValueError(
            f"AZ1_DB_ROLE inválido: {nome!r}. Use apenas letras, dígitos e sublinhado."
        )
    return nome


def criar_pool(settings: PostgresSettings) -> ConnectionPool:
    """Monta o pool. Não abre conexão aqui — ver `abrir_pool`."""
    return ConnectionPool(
        conninfo=settings.dsn,
        min_size=settings.tamanho_minimo,
        max_size=settings.tamanho_maximo,
        timeout=settings.espera_maxima,
        configure=lambda conexao: _configurar_conexao(conexao, settings.papel),
        open=False,
    )


def abrir_pool(settings: PostgresSettings) -> ConnectionPool:
    """Monta e abre o pool."""
    pool = criar_pool(settings)
    pool.open()
    return pool


# Usada pelo endpoint de prontidão. Deliberadamente trivial: o que se quer
# saber é se há conexão utilizável, não se o schema está correto.
def verificar_conexao(pool: ConnectionPool) -> bool:
    with pool.connection() as conexao, conexao.cursor() as cursor:
        cursor.execute("SELECT 1")
        return cursor.fetchone() == (1,)
