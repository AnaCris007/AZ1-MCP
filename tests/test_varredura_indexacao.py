"""Testes da varredura com indexação (baixar do Drive → reindexar no pgvector).

Não tocam a rede, o Gemini nem o pgvector: o `DriveClient` é um dublê e o pipeline
RAG (`extrair`/`chunkar`/`vetorizar_documentos`/`indexar`) é substituído por
funções de captura. O que se verifica é a COSTURA — que a varredura baixa o que o
feed aponta, deriva o `projeto_id` da pasta-pai, pula o que não é indexável, e só
avança o `delta_token` depois de consumir o feed.
"""

from __future__ import annotations

import unittest
from datetime import UTC, datetime

from mensageria import varredura_indexacao
from mensageria.varredura_indexacao import VarreduraComIndexacao
from services.webhook_service import EventoWebhook


class _ConexaoFake:
    def __init__(self, registro: dict) -> None:
        self._registro = registro

    def __enter__(self) -> _ConexaoFake:
        return self

    def __exit__(self, *_a: object) -> None:
        return None

    def execute(self, sql: str, params: tuple) -> _ConexaoFake:
        if "SELECT" in sql:
            self._resultado = (self._registro["id"], self._registro["delta_token"])
        else:  # UPDATE de conclusão
            self._registro["delta_token"] = params[0] or self._registro["delta_token"]
            self._registro["delta_pendente"] = False
            self._resultado = None
        return self

    def fetchone(self) -> tuple | None:
        return self._resultado


class _PoolFake:
    def __init__(self, registro: dict) -> None:
        self._registro = registro

    def connection(self) -> _ConexaoFake:
        return _ConexaoFake(self._registro)


class _DriveFake:
    def __init__(self, mudancas: list[dict], novo_token: str, arvore: dict | None = None) -> None:
        self._mudancas = mudancas
        self._novo_token = novo_token
        self.baixados: list[str] = []
        # mapa pasta_id -> lista de pastas-pai, para o teste de escopo por pasta
        self._arvore = arvore or {}

    def listar_mudancas(self, delta_token: str) -> tuple[list[dict], str]:
        return self._mudancas, self._novo_token

    def baixar(self, file_id: str, mime_type: str) -> tuple[bytes, str] | None:
        if "spreadsheet" in mime_type or "sheet" in mime_type:
            self.baixados.append(file_id)
            return b"conteudo-fake", ".xlsx"
        if "document" in mime_type or "wordprocessing" in mime_type:
            self.baixados.append(file_id)
            return b"conteudo-fake", ".docx"
        return None  # tipo não indexável

    def nome_da_pasta(self, folder_id: str) -> str:
        return {"pasta-syn": "SYN-04 - Modernização", "pasta-solta": "Documentos gerais"}.get(folder_id, "")

    def pais(self, item_id: str) -> list[str]:
        return self._arvore.get(item_id, [])


def _evento(correlacao: str = "canal-1") -> EventoWebhook:
    return EventoWebhook(
        identificador=f"google_drive:{correlacao}:1",
        tipo="drive.change",
        versao="1",
        marca_de_tempo=datetime.now(UTC),
        correlacao=correlacao,
        conteudo={},
    )


class TesteVarreduraComIndexacao(unittest.TestCase):
    def setUp(self) -> None:
        # Substitui o pipeline RAG por capturas: nada de Gemini/pgvector reais.
        self._indexados: list[tuple[str, str]] = []  # (projeto_id, arquivo_origem)

        def _extrair_fake(caminho):
            # `extrair` deriva projeto_id da pasta-pai e o nome do arquivo; o dublê
            # devolve um objeto com esses dois campos, que é o que o teste checa.
            class _Texto:
                projeto_id = caminho.parent.name
                arquivo_origem = caminho.name
                texto = "texto extraido"

            return [_Texto()]

        def _chunkar_fake(textos):
            return list(textos)

        def _vetorizar_fake(textos):
            return [[0.0] * 4 for _ in textos]

        def _indexar_fake(chunks, embeddings):
            for c in chunks:
                self._indexados.append((c.projeto_id, c.arquivo_origem))
            return len(chunks)

        self._orig = (
            varredura_indexacao.extrair,
            varredura_indexacao.chunkar,
            varredura_indexacao.vetorizar_documentos,
            varredura_indexacao.indexador.indexar,
        )
        varredura_indexacao.extrair = _extrair_fake
        varredura_indexacao.chunkar = _chunkar_fake
        varredura_indexacao.vetorizar_documentos = _vetorizar_fake
        varredura_indexacao.indexador.indexar = _indexar_fake

    def tearDown(self) -> None:
        (
            varredura_indexacao.extrair,
            varredura_indexacao.chunkar,
            varredura_indexacao.vetorizar_documentos,
            varredura_indexacao.indexador.indexar,
        ) = self._orig

    def test_baixa_indexa_e_avanca_o_token(self) -> None:
        registro = {"id": 7, "delta_token": "t0", "delta_pendente": True}
        mudancas = [
            {
                "fileId": "doc-1",
                "file": {
                    "id": "doc-1",
                    "name": "01_Termo_de_Abertura.docx",
                    "mimeType": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    "parents": ["pasta-syn"],
                    "trashed": False,
                },
            },
        ]
        drive = _DriveFake(mudancas, novo_token="t1")
        varredura = VarreduraComIndexacao(_PoolFake(registro), drive_factory=lambda: drive)

        varredura.varrer(_evento())

        # Baixou o arquivo, indexou com projeto derivado da pasta-pai (SYN-04),
        # e avançou o token + fechou a pendência.
        self.assertEqual(drive.baixados, ["doc-1"])
        self.assertEqual(self._indexados, [("SYN-04", "01_Termo_de_Abertura.docx")])
        self.assertEqual(registro["delta_token"], "t1")
        self.assertFalse(registro["delta_pendente"])

    def test_pula_removido_e_tipo_nao_indexavel(self) -> None:
        registro = {"id": 7, "delta_token": "t0", "delta_pendente": True}
        mudancas = [
            {"fileId": "del-1", "removed": True, "file": None},
            {
                "fileId": "img-1",
                "file": {"id": "img-1", "name": "foto.png", "mimeType": "image/png", "parents": ["pasta-solta"]},
            },
        ]
        drive = _DriveFake(mudancas, novo_token="t1")
        varredura = VarreduraComIndexacao(_PoolFake(registro), drive_factory=lambda: drive)

        varredura.varrer(_evento())

        self.assertEqual(drive.baixados, [])          # nada baixado
        self.assertEqual(self._indexados, [])          # nada indexado
        self.assertEqual(registro["delta_token"], "t1")  # mas o feed avançou

    def test_pasta_sem_syn_cai_para_portfolio(self) -> None:
        registro = {"id": 7, "delta_token": "t0", "delta_pendente": True}
        mudancas = [
            {
                "fileId": "sheet-1",
                "file": {
                    "id": "sheet-1",
                    "name": "02_Cronograma.xlsx",
                    "mimeType": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    "parents": ["pasta-solta"],
                },
            },
        ]
        drive = _DriveFake(mudancas, novo_token="t1")
        varredura = VarreduraComIndexacao(_PoolFake(registro), drive_factory=lambda: drive)

        varredura.varrer(_evento())

        self.assertEqual(self._indexados, [("PORTFOLIO", "02_Cronograma.xlsx")])

    def test_escopo_indexa_sob_a_pasta_do_pmo(self) -> None:
        registro = {"id": 7, "delta_token": "t0", "delta_pendente": True}
        # doc-1 está em 'pasta-syn', que é filha de 'raiz-pmo' → sob a raiz.
        mudancas = [
            {
                "fileId": "doc-1",
                "file": {
                    "id": "doc-1",
                    "name": "01_Termo.docx",
                    "mimeType": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    "parents": ["pasta-syn"],
                },
            },
        ]
        drive = _DriveFake(mudancas, novo_token="t1", arvore={"pasta-syn": ["raiz-pmo"], "raiz-pmo": []})
        varredura = VarreduraComIndexacao(
            _PoolFake(registro), drive_factory=lambda: drive, pasta_raiz="raiz-pmo"
        )

        varredura.varrer(_evento())
        self.assertEqual(drive.baixados, ["doc-1"])
        self.assertEqual(self._indexados, [("SYN-04", "01_Termo.docx")])

    def test_escopo_ignora_fora_da_pasta_do_pmo(self) -> None:
        registro = {"id": 7, "delta_token": "t0", "delta_pendente": True}
        # doc-2 está em 'pasta-pessoal', que NÃO desce de 'raiz-pmo'.
        mudancas = [
            {
                "fileId": "doc-2",
                "file": {
                    "id": "doc-2",
                    "name": "meu_script.docx",
                    "mimeType": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    "parents": ["pasta-pessoal"],
                },
            },
        ]
        drive = _DriveFake(mudancas, novo_token="t1", arvore={"pasta-pessoal": ["meu-drive"], "meu-drive": []})
        varredura = VarreduraComIndexacao(
            _PoolFake(registro), drive_factory=lambda: drive, pasta_raiz="raiz-pmo"
        )

        varredura.varrer(_evento())
        self.assertEqual(drive.baixados, [])       # não baixou
        self.assertEqual(self._indexados, [])       # não indexou
        self.assertEqual(registro["delta_token"], "t1")  # mas o feed avançou

    def test_origem_inexistente_nao_baixa_nada(self) -> None:
        class _PoolVazio:
            def connection(self_):  # noqa: N805
                class _C:
                    def __enter__(self_c):  # noqa: N805
                        return self_c

                    def __exit__(self_c, *_a):  # noqa: N805
                        return None

                    def execute(self_c, *_a):  # noqa: N805
                        self_c._r = None
                        return self_c

                    def fetchone(self_c):  # noqa: N805
                        return None

                return _C()

        drive = _DriveFake([], novo_token="t1")
        varredura = VarreduraComIndexacao(_PoolVazio(), drive_factory=lambda: drive)

        varredura.varrer(_evento("inexistente"))
        self.assertEqual(drive.baixados, [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
