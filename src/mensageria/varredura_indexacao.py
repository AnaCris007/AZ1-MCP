"""Varredura REAL: baixa do Drive o que mudou e reindexa no pgvector.

É a implementação que preenche o ponto de encaixe descrito em
`mensageria.varredura` (o stub `VarreduraDeConexao`, que só fecha o estado). Tem
a MESMA interface — `varrer(evento)` — então o consumidor troca uma pela outra
sem mudar nada mais.

O fluxo, para uma notificação de mudança do Drive:

  1. lê o `delta_token` da conexão correlacionada;
  2. `changes.list` a partir dele → lista de arquivos mudados + novo token;
  3. para cada arquivo indexável (.docx/.xlsx, direto ou exportado):
       baixa → grava num temp cuja PASTA tem o nome da pasta-pai no Drive
       (para `parsers.extrair` derivar o `projeto_id` SYN-xx como sempre)
       → extrair → chunkar → vetorizar → indexar no pgvector;
  4. grava o novo `delta_token` e marca `delta_pendente = FALSE`, na mesma
     transação: só se dá a origem por varrida depois de o feed ter avançado.

PERMISSÃO DE BANCO: diferente do stub, esta varredura faz `UPDATE (delta_token)`
em `integracao.conexao` e escreve na coleção `vecs` do pgvector — além do
`az1_webhook`, que só pode `UPDATE (delta_pendente)`. Por isso o worker de
indexação roda com o papel do `SUPABASE_DB_URL` (dono/app), não com `az1_webhook`.
No host da PoC é o mesmo DSN que o `drive_channel_service` já usa.

IDEMPOTÊNCIA: reindexar o mesmo arquivo faz `upsert` na coleção (o id do chunk é
derivado do conteúdo, ver `rag.indexador._chunk_id`), então consumir a mesma
mensagem duas vezes não duplica — mantém o efeito único do TI-44.
"""

from __future__ import annotations

import logging
import re
import shutil
import tempfile
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from rag import indexador
from rag.chunker import chunkar
from rag.embedder import vetorizar_documentos
from rag.parsers import extrair
from services.drive_download_service import DriveClient
from services.webhook_service import EventoWebhook

logger = logging.getLogger(__name__)

# Nome de pasta que o `parsers._projeto_id` reconhece. Só usamos para decidir o
# nome do diretório temporário; a derivação de fato continua no parsers.
_PADRAO_PROJETO = re.compile(r"SYN-\d+")

# Acima disto, um feed é "grande" e o worker avisa sobre o risco de consumer_timeout
# do RabbitMQ sob o rate limit de 5 RPM do Gemini (ver `varrer`).
_FEED_GRANDE = 50


@dataclass
class _CacheVarredura:
    """Caches de estrutura de pastas VÁLIDOS POR UMA varredura.

    Nascem em `varrer` e morrem no fim dela, de propósito: o worker é longevo e a
    estrutura de pastas do Drive PODE mudar entre varreduras (uma pasta movida).
    Um cache de instância ficaria velho; escopar por chamada garante que cada
    varredura parta de uma leitura fresca. Dentro de UMA varredura a árvore é
    estável, então cachear aqui evita `files.get` repetido para o mesmo id.

      • `pais`  → id da pasta → suas pastas-pai (usado por `_sob_raiz`);
      • `nomes` → id da pasta → seu nome (usado por `_projeto_id`).
    """

    pais: dict[str, list[str]] = field(default_factory=dict)
    nomes: dict[str, str] = field(default_factory=dict)


class VarreduraComIndexacao:
    """Baixa do Drive os arquivos mudados e os reindexa no banco vetorial."""

    def __init__(
        self,
        pool: Any,
        drive_factory: Callable[[], DriveClient] = DriveClient.autenticado,
        pasta_raiz: str | None = None,
    ) -> None:
        self._pool = pool
        # Fábrica, e não instância pronta: o cliente renova o access token na
        # construção, e o worker é longevo. Recriar por varredura garante token
        # válido sem guardar lógica de expiração aqui. Injetável para teste.
        self._drive_factory = drive_factory
        # ID da pasta do PMO. `changes.list` monitora o Drive INTEIRO, então sem
        # este escopo o worker indexaria qualquer .docx/.xlsx da conta. Com ele,
        # só arquivos sob esta pasta (em qualquer nível) entram no RAG. None =
        # sem escopo (indexa tudo) — o consumidor avisa quando não está definido.
        self._pasta_raiz = pasta_raiz

    def varrer(self, evento: EventoWebhook) -> None:
        conexao_id, delta_token = self._origem(evento.correlacao)
        if conexao_id is None:
            logger.info(
                "Varredura sem origem ativa para correlacao=%s (identificador=%s); "
                "origem provavelmente desativada após a publicação.",
                evento.correlacao,
                evento.identificador,
            )
            return

        drive = self._drive_factory()
        mudancas, novo_token = drive.listar_mudancas(delta_token or "")

        # Cache de estrutura de pastas VÁLIDO SÓ NESTA varredura (ver
        # `_CacheVarredura`). Nasce aqui e é passado adiante, para cada varredura
        # partir de uma leitura fresca do Drive.
        cache = _CacheVarredura()

        # O feed inteiro é processado dentro de UMA mensagem, antes do ack. Com o
        # limite de 5 RPM do Gemini no plano gratuito (~12s por lote de embeddings),
        # um feed grande pode ultrapassar o `consumer_timeout` do RabbitMQ (30 min
        # por padrão): o broker fecha o canal, a mensagem volta e o feed reprocessa
        # do zero. Um backfill ou a notificação `sync` inicial é o caso típico.
        if len(mudancas) > _FEED_GRANDE:
            logger.warning(
                "Feed com %d mudanças para correlacao=%s: sob 5 RPM do Gemini isso pode "
                "levar minutos e esbarrar no consumer_timeout do RabbitMQ. Considere cota "
                "paga de embeddings ou aumentar o consumer_timeout da fila.",
                len(mudancas),
                evento.correlacao,
            )

        indexados = 0
        for mudanca in mudancas:
            indexados += self._processar_mudanca(drive, mudanca, cache)

        # Só avança o token e dá a origem por varrida depois de o feed ter sido
        # consumido por inteiro. Se algo acima levantou, não chegamos aqui: a
        # mensagem volta à fila (o consumidor faz nack/requeue) e o token fica no
        # ponto anterior, então nada se perde.
        self._concluir(conexao_id, novo_token)
        logger.info(
            "Varredura de correlacao=%s concluída: %d arquivo(s) indexado(s), %d mudança(s) no feed.",
            evento.correlacao,
            indexados,
            len(mudancas),
        )

    # -- passos -------------------------------------------------------------

    def _processar_mudanca(
        self, drive: DriveClient, mudanca: dict[str, Any], cache: _CacheVarredura
    ) -> int:
        """Baixa e indexa um arquivo mudado. Retorna 1 se indexou, 0 se pulou."""
        arquivo = mudanca.get("file") or {}
        file_id = mudanca.get("fileId", "")

        # Removido do Drive ou na lixeira: nada a baixar. (A remoção do que já foi
        # indexado é trabalho futuro — hoje o feed só adiciona/atualiza.)
        if mudanca.get("removed") or arquivo.get("trashed"):
            return 0

        parents = arquivo.get("parents") or []
        # Escopo: se há pasta do PMO configurada, só indexa o que está sob ela.
        # A checagem vem ANTES do download, para não baixar o que será descartado.
        if self._pasta_raiz and not self._sob_raiz(drive, parents, cache):
            logger.debug("Arquivo %s fora da pasta do PMO; ignorando.", file_id)
            return 0

        mime = arquivo.get("mimeType", "")
        baixado = drive.baixar(file_id, mime)
        if baixado is None:
            logger.debug("Tipo não indexável (%s) para file_id=%s; pulando.", mime, file_id)
            return 0

        conteudo, extensao = baixado
        projeto_id = self._projeto_id(drive, parents, cache)
        nome = arquivo.get("name") or file_id

        self._indexar(nome, extensao, projeto_id, conteudo)
        return 1

    def _indexar(self, nome: str, extensao: str, projeto_id: str, conteudo: bytes) -> None:
        """Grava o arquivo num temp e roda o pipeline extrair→chunkar→vetorizar→indexar.

        O truque de metadados: `parsers.extrair` deriva o `projeto_id` do NOME DA
        PASTA-PAI e o `tipo_documento` do PREFIXO DO NOME. Então gravamos em
        `<tmp>/<projeto_id>/<nome com extensão>` e o parser produz os mesmos
        metadados de sempre, sem precisar de parâmetro novo.
        """
        base = Path(tempfile.mkdtemp(prefix="varredura-"))
        try:
            pasta = base / projeto_id
            pasta.mkdir(parents=True, exist_ok=True)
            # `nome` vem cru do Drive: Path(...).name descarta qualquer componente
            # de diretório ("/" ou "..") para o arquivo não escapar de `pasta`.
            nome_seguro = Path(nome).name or "arquivo"
            caminho = pasta / self._com_extensao(nome_seguro, extensao)
            caminho.write_bytes(conteudo)

            textos = extrair(caminho)
            if not textos:
                logger.info("Arquivo %s sem conteúdo extraível; nada a indexar.", nome)
                return

            chunks = chunkar(textos)
            embeddings = vetorizar_documentos([c.texto for c in chunks])
            n = indexador.indexar(chunks, embeddings)
            logger.info("Indexado %s (projeto=%s): %d chunk(s).", nome, projeto_id, n)
        finally:
            shutil.rmtree(base, ignore_errors=True)

    # -- banco --------------------------------------------------------------

    def _origem(self, correlacao: str) -> tuple[int | None, str | None]:
        with self._pool.connection() as conexao:
            linha = conexao.execute(
                """
                SELECT id, delta_token FROM integracao.conexao
                 WHERE subscription_id = %s AND ativa
                """,
                (correlacao,),
            ).fetchone()
        return (linha[0], linha[1]) if linha else (None, None)

    def _concluir(self, conexao_id: int, novo_token: str | None) -> None:
        with self._pool.connection() as conexao:
            conexao.execute(
                """
                UPDATE integracao.conexao
                   SET delta_pendente = FALSE,
                       delta_token = COALESCE(%s, delta_token)
                 WHERE id = %s
                """,
                (novo_token, conexao_id),
            )

    # -- helpers ------------------------------------------------------------

    def _projeto_id(self, drive: DriveClient, parents: list[str], cache: _CacheVarredura) -> str:
        """Deriva o SYN-xx do nome da pasta-pai; 'PORTFOLIO' se não casar."""
        if not parents:
            return "PORTFOLIO"
        nome_pasta = self._nome_pasta(drive, parents[0], cache)
        achado = _PADRAO_PROJETO.search(nome_pasta or "")
        return achado.group(0) if achado else "PORTFOLIO"

    def _sob_raiz(self, drive: DriveClient, parents: list[str], cache: _CacheVarredura) -> bool:
        """Diz se um arquivo está sob `self._pasta_raiz`, em qualquer profundidade.

        Sobe a árvore de pastas a partir dos `parents` do arquivo até encontrar a
        raiz do PMO ou esgotar os ancestrais. As pastas-pai visitadas são
        cacheadas (`cache.pais`, válido só nesta varredura) porque muitos arquivos
        compartilham a mesma árvore, e a estrutura de pastas não muda durante uma
        varredura.
        """
        fila = list(parents)
        vistos: set[str] = set()
        while fila:
            atual = fila.pop()
            if atual == self._pasta_raiz:
                return True
            if atual in vistos:
                continue
            vistos.add(atual)
            avos = cache.pais.get(atual)
            if avos is None:
                avos = drive.pais(atual)
                cache.pais[atual] = avos
            fila.extend(avos)
        return False

    @staticmethod
    def _nome_pasta(drive: DriveClient, folder_id: str, cache: _CacheVarredura) -> str:
        """Nome da pasta-pai, memoizado nesta varredura para não repetir `files.get`."""
        nome = cache.nomes.get(folder_id)
        if nome is None:
            nome = drive.nome_da_pasta(folder_id)
            cache.nomes[folder_id] = nome
        return nome

    @staticmethod
    def _com_extensao(nome: str, extensao: str) -> str:
        """Garante que o nome termine na extensão baixada (docs nativos vêm sem)."""
        return nome if nome.lower().endswith(extensao) else f"{nome}{extensao}"
