"""Cliente Python independente usado pelo RNF05; contém somente transporte HTTP."""

from __future__ import annotations

import hashlib
import json
import os
import platform
from pathlib import Path

import httpx


SAIDA = Path(os.environ["RNF05_OUTPUT_DIR"])
MASSA = json.loads((SAIDA / "massa.json").read_text(encoding="utf-8"))
BASE_URL = os.environ.get("RNF05_BASE_URL", "http://127.0.0.1:8001")


def executar() -> None:
    resultados = []
    with httpx.Client(base_url=BASE_URL, timeout=10.0) as cliente:
        openapi = cliente.get("/openapi.json")
        openapi.raise_for_status()
        contrato = openapi.json()["paths"]["/api/v1/chat"]["post"]
        contrato_bytes = json.dumps(contrato, sort_keys=True).encode("utf-8")
        (SAIDA / "contrato_chat.json").write_text(
            json.dumps(contrato, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        for caso in MASSA:
            token = (
                "rnf05-python-valido"
                if caso["token"] == "valido"
                else "rnf05-python-invalido"
            )
            resposta = cliente.post(
                "/api/v1/chat",
                headers={"Authorization": f"Bearer {token}"},
                json={
                    "message": caso["mensagem"],
                    "conversation_id": caso["conversation_id"],
                },
            )
            resultados.append(
                {
                    "id": caso["id"],
                    "client": "python",
                    "method": "POST",
                    "route": "/api/v1/chat",
                    "status": resposta.status_code,
                    "body": resposta.json(),
                }
            )
    documento = {
        "ambiente": {
            "aplicacao": "cliente Python independente",
            "python": platform.python_version(),
            "httpx": httpx.__version__,
            "base_url": BASE_URL,
        },
        "contrato_chat_sha256": hashlib.sha256(contrato_bytes).hexdigest(),
        "resultados": resultados,
    }
    (SAIDA / "resultados_python.json").write_text(
        json.dumps(documento, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"cliente_python={len(resultados)}")


if __name__ == "__main__":
    executar()
