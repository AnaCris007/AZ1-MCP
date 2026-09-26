"""Cliente de LEITURA do Google Drive para a varredura da Sprint 5.

O `drive_channel_service` abre/fecha o canal de push e sabe autenticar; este
módulo é o passo seguinte, que a notificação sozinha não resolve: descobrir O QUE
mudou e baixar o conteúdo para reindexar.

Uma notificação do Drive diz apenas "algo mudou na origem", nunca qual arquivo.
Descobrir exige o feed de mudanças (`changes.list`), partindo do `delta_token`
guardado quando o canal foi aberto. Cada mudança traz o `fileId`; o conteúdo vem
de `files.get?alt=media` (binários já no formato Office) ou de `files.export`
(documentos nativos do Google, convertidos para .docx/.xlsx).

Reusa deliberadamente a mesma stack do `drive_channel_service`: `Config`,
`obter_token` e o endpoint `DRIVE`, mais o helper `pedir` de `webhook_http` para
as chamadas JSON. Só o download binário é novo, porque `pedir` devolve JSON e o
conteúdo do arquivo não é JSON — daí `_baixar_binario` com urllib direto.

Autenticação: o `obter_token` lê o `refresh_token` de `.google_token.json` (o
mesmo arquivo que o `abrir` gravou). Por isso o worker roda no host, onde esse
arquivo existe — a decisão de operação registrada na Seção 5.1.6.
"""

from __future__ import annotations

import logging
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any

from services.drive_channel_service import DRIVE, Config, obter_token
from services.webhook_http import ErroDeOperacao, ErroHTTP
from services.webhook_http import pedir as _pedir

logger = logging.getLogger(__name__)

# Documentos NATIVOS do Google não têm bytes para baixar direto: exigem `export`
# para um formato concreto. Mapeia o mimeType nativo → (mime de exportação, ext).
# As extensões são as que `rag.parsers.extrair` sabe ler.
_EXPORTAVEIS: dict[str, tuple[str, str]] = {
    "application/vnd.google-apps.document": (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".docx",
    ),
    "application/vnd.google-apps.spreadsheet": (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ".xlsx",
    ),
}

# Arquivos já em formato Office, enviados ao Drive: baixam direto com `alt=media`.
_BAIXAVEIS: dict[str, str] = {
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
}

# Campos pedidos ao `changes.list`. Trazer o `file` embutido evita um `files.get`
# por mudança só para saber nome/tipo/pasta — uma chamada em vez de N.
_CAMPOS_MUDANCAS = (
    "nextPageToken,newStartPageToken,"
    "changes(fileId,removed,file(id,name,mimeType,trashed,parents))"
)


@dataclass(frozen=True)
class ArquivoBaixado:
    """Um arquivo do Drive já em bytes, com o que `extrair` precisa para os metadados."""

    file_id: str
    nome: str          # nome original no Drive, ex.: "01_Termo_de_Abertura.docx"
    extensao: str      # ".docx" ou ".xlsx"
    projeto_id: str    # derivado da pasta-pai (SYN-xx) ou "PORTFOLIO"
    conteudo: bytes


class DriveClient:
    """Lê o feed de mudanças e baixa o conteúdo dos arquivos alterados."""

    def __init__(self, config: Config, token: str) -> None:
        self._config = config
        self._token = token

    @classmethod
    def autenticado(cls) -> DriveClient:
        """Constrói o cliente lendo o `.env` e renovando o access token gravado."""
        config = Config.from_environment()
        return cls(config, obter_token(config))

    # -- feed de mudanças ---------------------------------------------------

    def listar_mudancas(self, delta_token: str) -> tuple[list[dict[str, Any]], str | None]:
        """Retorna (mudanças desde `delta_token`, novo ponto de retomada).

        Pagina o feed até o fim. O `newStartPageToken` vem só na última página e é
        o que deve ser gravado de volta em `integracao.conexao.delta_token`: da
        próxima vez a varredura parte daí, sem reprocessar o que já viu.
        """
        mudancas: list[dict[str, Any]] = []
        pagina = delta_token
        # Defesa em profundidade contra laço infinito: se o provedor devolvesse o
        # mesmo `nextPageToken` (bug ou resposta corrompida), paginaríamos para
        # sempre. Guardamos os tokens já pedidos e paramos ao reencontrar um,
        # no mesmo espírito do `vistos` de `_sob_raiz`.
        vistos: set[str] = set()
        while True:
            url = (
                f"{DRIVE}/changes"
                f"?pageToken={urllib.parse.quote(pagina)}"
                f"&pageSize=100&includeRemoved=true"
                f"&fields={urllib.parse.quote(_CAMPOS_MUDANCAS)}"
            )
            vistos.add(pagina)
            resposta = _pedir(url, token=self._token)
            mudancas.extend(resposta.get("changes", []))

            proxima = resposta.get("nextPageToken")
            if proxima and proxima not in vistos:
                pagina = proxima
                continue
            if proxima:
                logger.warning(
                    "changes.list repetiu o pageToken; interrompendo a paginação para "
                    "evitar laço infinito. O feed pode ter ficado parcial."
                )
            return mudancas, resposta.get("newStartPageToken")

    # -- download -----------------------------------------------------------

    def baixar(self, file_id: str, mime_type: str) -> tuple[bytes, str] | None:
        """Baixa o arquivo. Retorna (bytes, extensão) ou None se o tipo não é indexável.

        `None` para pasta, imagem, PDF etc.: o pipeline de indexação só entende
        .docx e .xlsx (ver `rag.parsers.extrair`), então tipos fora disso são
        pulados sem erro — mudança registrada, mas nada a vetorizar.
        """
        if mime_type in _EXPORTAVEIS:
            export_mime, extensao = _EXPORTAVEIS[mime_type]
            url = (
                f"{DRIVE}/files/{file_id}/export"
                f"?mimeType={urllib.parse.quote(export_mime)}"
            )
            return self._baixar_binario(url), extensao

        if mime_type in _BAIXAVEIS:
            url = f"{DRIVE}/files/{file_id}?alt=media"
            return self._baixar_binario(url), _BAIXAVEIS[mime_type]

        return None

    def nome_da_pasta(self, folder_id: str) -> str:
        """Nome da pasta-pai, para derivar o `projeto_id` (SYN-xx) como o `parsers` faz."""
        return _pedir(f"{DRIVE}/files/{folder_id}?fields=name", token=self._token).get("name", "")

    def pais(self, item_id: str) -> list[str]:
        """IDs das pastas-pai de um item (arquivo ou pasta).

        Usado para subir a árvore e decidir se um arquivo está sob a pasta do PMO:
        `changes.list` monitora o Drive inteiro, então o escopo é feito aqui.
        """
        return _pedir(f"{DRIVE}/files/{item_id}?fields=parents", token=self._token).get("parents") or []

    def _baixar_binario(self, url: str) -> bytes:
        """Faz um GET autenticado e devolve o corpo cru.

        Existe separado do `pedir` de `webhook_http` porque aquele desserializa o
        corpo como JSON, e o conteúdo de um arquivo não é JSON.
        """
        requisicao = urllib.request.Request(
            url, headers={"Authorization": f"Bearer {self._token}"}, method="GET"
        )
        try:
            with urllib.request.urlopen(requisicao, timeout=60) as resposta:
                return resposta.read()
        except urllib.error.HTTPError as exc:
            texto = exc.read().decode("utf-8", errors="replace")
            raise ErroHTTP(exc.code, texto, url) from exc
        except urllib.error.URLError as exc:
            raise ErroDeOperacao(f"Não foi possível baixar {url}: {exc.reason}") from exc
