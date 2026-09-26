#!/usr/bin/env python3
"""Executa as 40 consultas do RNF12 e preserva respostas e referências.

A autenticação é substituída por uma identidade sintética porque o objeto do
RNF12 é fundamentação, não SSO. Busca vetorial, classificador, orquestração e
Gemini permanecem reais e usam a configuração do ambiente.
"""

from __future__ import annotations

import json
import os
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

import openpyxl
import psycopg2
from dotenv import load_dotenv
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

load_dotenv(ROOT / ".env")

from az1_api.dependencies import get_conversa_repository, require_authenticated_user  # noqa: E402
from az1_api.main import app  # noqa: E402
from services.auth_service import AuthenticatedUser  # noqa: E402
from services.conversa_repository import PersistenciaDesligada  # noqa: E402

USUARIO = AuthenticatedUser(
    subject="rnf12-synthetic-user",
    email="rnf12@example.invalid",
    name="Avaliador técnico RNF12",
    provider="test",
)


def carregar_consultas(caminho: Path) -> list[dict]:
    workbook = openpyxl.load_workbook(caminho, data_only=True, read_only=True)
    sheet = workbook["Consultas"]
    rows = sheet.iter_rows()
    headers = [cell.value for cell in next(rows)]
    return [dict(zip(headers, (cell.value for cell in row))) for row in rows]


def dsn_psycopg2() -> str:
    dsn = os.environ["SUPABASE_DB_URL"]
    return dsn.replace("postgresql+psycopg2://", "postgresql://", 1).replace(
        "postgresql+psycopg://", "postgresql://", 1
    )


def chunks_existentes(ids: set[str]) -> set[str]:
    if not ids:
        return set()
    with psycopg2.connect(dsn_psycopg2()) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                'SELECT id FROM vecs."documentos_metro" WHERE id = ANY(%s)',
                (list(ids),),
            )
            return {str(row[0]) for row in cursor.fetchall()}


def main() -> int:
    workbook_path = ROOT / "outputs" / "rnf12" / "campanha_rnf12.xlsx"
    output_dir = ROOT / "resultados" / "testes-rnf" / "0a61b353" / "rnf12"
    output_dir.mkdir(parents=True, exist_ok=True)
    consultas = carregar_consultas(workbook_path)

    app.dependency_overrides[require_authenticated_user] = lambda: USUARIO
    app.dependency_overrides[get_conversa_repository] = lambda: PersistenciaDesligada(
        "campanha RNF12: persistência desligada para não misturar evidência de teste"
    )

    respostas: list[dict] = []
    inicio_rodada = datetime.now(timezone.utc).isoformat()
    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            for numero, consulta in enumerate(consultas, start=1):
                case_id = str(consulta["ID"])
                conversation_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"az1-rnf12-{case_id}"))
                inicio = time.perf_counter()
                response = client.post(
                    "/api/v1/chat",
                    json={"message": consulta["Consulta"], "conversation_id": conversation_id},
                )
                duration = time.perf_counter() - inicio
                try:
                    body = response.json()
                except ValueError:
                    body = {"raw": response.text}
                fontes = body.get("fontes", []) if isinstance(body, dict) else []
                respostas.append(
                    {
                        "id": case_id,
                        "caso": consulta["Caso"],
                        "categoria_condicao": consulta["Categoria/condição"],
                        "projeto": consulta["Projeto"],
                        "consulta": consulta["Consulta"],
                        "resposta_esperada": consulta["Resposta ou comportamento esperado"],
                        "fonte_esperada": consulta["Fonte esperada"],
                        "fato_limitacao_pre_registrada": consulta[
                            "Fato ou limitação pré-registrada"
                        ],
                        "conversation_id": conversation_id,
                        "status_http": response.status_code,
                        "duracao_s": round(duration, 6),
                        "reply": body.get("reply", "") if isinstance(body, dict) else "",
                        "fontes": fontes,
                    }
                )
                print(
                    f"{numero:02d}/{len(consultas)} {case_id} status={response.status_code} "
                    f"fontes={len(fontes)} duracao={duration:.2f}s",
                    flush=True,
                )
    finally:
        app.dependency_overrides.clear()

    chunk_ids = {
        str(fonte.get("chunk_id"))
        for resposta in respostas
        for fonte in resposta["fontes"]
        if fonte.get("chunk_id")
    }
    existentes = chunks_existentes(chunk_ids)
    for resposta in respostas:
        for fonte in resposta["fontes"]:
            chunk_id = str(fonte.get("chunk_id", ""))
            fonte["recuperavel_no_indice"] = bool(chunk_id and chunk_id in existentes)

    references = [fonte for resposta in respostas for fonte in resposta["fontes"]]
    positives = [r for r in respostas if r["caso"] == "CT-RNF12-P"]
    negatives = [r for r in respostas if r["caso"] == "CT-RNF12-N"]
    summary = {
        "rnf": "RNF12",
        "estado_tecnico": "EXECUTADO_AGUARDANDO_AVALIACAO_HUMANA",
        "iniciado_em_utc": inicio_rodada,
        "finalizado_em_utc": datetime.now(timezone.utc).isoformat(),
        "consultas": len(respostas),
        "positivas": len(positives),
        "negativas": len(negatives),
        "http_200": sum(r["status_http"] == 200 for r in respostas),
        "positivas_com_fonte": sum(bool(r["fontes"]) for r in positives),
        "negativas_com_fonte": sum(bool(r["fontes"]) for r in negatives),
        "referencias_apresentadas": len(references),
        "referencias_recuperaveis": sum(
            bool(f.get("recuperavel_no_indice")) for f in references
        ),
        "percentual_referencias_recuperaveis": (
            sum(bool(f.get("recuperavel_no_indice")) for f in references) / len(references)
            if references
            else None
        ),
        "avaliacao_afirmacoes": "PENDENTE",
        "resultado_final": "PENDENTE",
    }
    (output_dir / "respostas_execucao.json").write_text(
        json.dumps(respostas, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (output_dir / "execucao_tecnica.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print("RESUMO=" + json.dumps(summary, ensure_ascii=False), flush=True)
    return 0 if len(respostas) == 40 else 2


if __name__ == "__main__":
    raise SystemExit(main())
