#!/usr/bin/env python3
"""Gera a massa, mede RNF01 por HTTP e consolida uma rodada."""

from __future__ import annotations

import csv
import json
import math
import platform
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

import httpx


PROJETOS = [f"SYN-{i:02d}" for i in range(1, 9)]
SIMPLES = [
    "Qual é o status do projeto {p}?",
    "Qual é o avanço atual do projeto {p}?",
    "Qual é o prazo previsto do projeto {p}?",
    "Quais pendências estão abertas no projeto {p}?",
    "Quais riscos estão abertos no projeto {p}?",
]
COMPLEXAS = [
    "Resuma status, avanço e prazo do projeto {p}.",
    "Apresente as pendências, riscos e responsáveis do projeto {p}.",
    "Explique o desvio de avanço e os próximos marcos do projeto {p}.",
    "Quais documentos, riscos e prazos merecem atenção no projeto {p}?",
    "Forneça uma visão executiva do projeto {p}, incluindo avanço, status e pendências.",
]
ATRASO_20 = {10, 30, 50, 70, 90}
ATRASO_65 = {20, 40, 60, 80, 100}


def massa(caso: str) -> list[dict]:
    itens = []
    for indice in range(1, 101):
        if indice <= 50:
            modelo = SIMPLES[(indice - 1) % len(SIMPLES)]
            estrato = "simples"
        else:
            modelo = COMPLEXAS[(indice - 51) % len(COMPLEXAS)]
            estrato = "complexa"
        mensagem = modelo.format(p=PROJETOS[(indice - 1) % len(PROJETOS)])
        atraso = 0
        if caso == "CT-RNF01-N":
            atraso = 20 if indice in ATRASO_20 else 65 if indice in ATRASO_65 else 0
            mensagem = f"[delay={atraso}] {mensagem}"
        itens.append(
            {
                "id": f"Q{indice:03d}",
                "message": mensagem,
                "conversation_id": str(uuid.uuid5(uuid.NAMESPACE_URL, f"az1-rnf01-{caso}-{indice}")),
                "estrato": estrato,
                "atraso_injetado_s": atraso,
            }
        )
    return itens


def percentil(valores: list[float], proporcao: float) -> float | None:
    if not valores:
        return None
    ordenados = sorted(valores)
    return ordenados[max(0, math.ceil(proporcao * len(ordenados)) - 1)]


def main() -> int:
    if len(sys.argv) != 4:
        raise SystemExit("uso: executar_rnf01.py CASO BASE_URL DIRETORIO")
    caso, base_url, diretorio = sys.argv[1], sys.argv[2].rstrip("/"), Path(sys.argv[3])
    diretorio.mkdir(parents=True, exist_ok=True)
    itens = massa(caso)
    (diretorio / "massa.json").write_text(json.dumps(itens, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    timeout = httpx.Timeout(61.0, connect=5.0)
    registros = []
    with httpx.Client(timeout=timeout) as cliente:
        # Aquecimento explicitamente descartado.
        try:
            cliente.post(
                base_url + "/api/v1/chat",
                json={"message": itens[0]["message"], "conversation_id": str(uuid.uuid4())},
            )
        except httpx.HTTPError:
            pass

        for numero, item in enumerate(itens, 1):
            inicio_iso = datetime.now(timezone.utc).isoformat()
            inicio = time.perf_counter()
            status = None
            erro = ""
            completa = False
            try:
                resposta = cliente.post(
                    base_url + "/api/v1/chat",
                    json={"message": item["message"], "conversation_id": item["conversation_id"]},
                )
                status = resposta.status_code
                if resposta.status_code == 200:
                    corpo = resposta.json()
                    texto = corpo.get("reply")
                    completa = isinstance(texto, str) and bool(texto.strip())
                    if not completa:
                        erro = "contrato_incompleto"
                else:
                    erro = "http_error"
            except httpx.TimeoutException:
                erro = "limite_total_cliente"
            except httpx.HTTPError:
                erro = "transporte"
            except (ValueError, AttributeError):
                erro = "contrato"
            duracao = time.perf_counter() - inicio
            desfecho_60 = duracao <= 60 and (status is not None or erro not in {"limite_total_cliente", "transporte"})
            completa_15 = completa and duracao <= 15
            registro = {
                "caso": caso,
                "id": item["id"],
                "estrato": item["estrato"],
                "atraso_injetado_s": item["atraso_injetado_s"],
                "inicio_utc": inicio_iso,
                "duracao_s": f"{duracao:.6f}",
                "status_http": status if status is not None else "",
                "erro": erro,
                "resposta_completa": completa,
                "completa_ate_15s": completa_15,
                "desfecho_ate_60s": desfecho_60,
                "elegivel": True,
            }
            registros.append(registro)
            print(f"{caso} {numero:03d}/100 status={status} duracao={duracao:.3f}s erro={erro}", flush=True)

    with (diretorio / "tentativas.csv").open("w", newline="", encoding="utf-8") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=list(registros[0]))
        escritor.writeheader()
        escritor.writerows(registros)

    duracoes = [float(r["duracao_s"]) for r in registros]
    completas_15 = sum(str(r["completa_ate_15s"]) == "True" for r in registros)
    desfechos_60 = sum(str(r["desfecho_ate_60s"]) == "True" for r in registros)
    completas = sum(str(r["resposta_completa"]) == "True" for r in registros)
    resultado = {
        "caso": caso,
        "resultado": "APROVADO" if completas_15 >= 80 and desfechos_60 == 100 else "REPROVADO",
        "tentativas": len(registros),
        "respostas_completas": completas,
        "completas_ate_15s": completas_15,
        "percentual_completas_ate_15s": completas_15,
        "desfechos_ate_60s": desfechos_60,
        "percentual_desfechos_ate_60s": desfechos_60,
        "http_2xx": sum(isinstance(r["status_http"], int) and 200 <= r["status_http"] < 300 for r in registros),
        "p50_s": percentil(duracoes, 0.50),
        "p80_s": percentil(duracoes, 0.80),
        "p95_s": percentil(duracoes, 0.95),
        "min_s": min(duracoes),
        "max_s": max(duracoes),
        "metodo_percentil": "nearest-rank (posto superior)",
    }
    (diretorio / "resultado.json").write_text(json.dumps(resultado, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (diretorio / "ambiente.json").write_text(
        json.dumps(
            {
                "commit": "0a61b353829dee491537bb2863facbe589d48cc8",
                "python": platform.python_version(),
                "plataforma": platform.platform(),
                "base_url": base_url,
                "execucao": "sequencial",
                "aquecimento_descartado": 1,
                "timeout_observacao_cliente_s": 61,
                "servicos_reais": caso == "CT-RNF01-P",
                "dependencia_controlada": caso == "CT-RNF01-N",
            },
            ensure_ascii=False,
            indent=2,
        ) + "\n",
        encoding="utf-8",
    )
    print("RESULTADO=" + json.dumps(resultado, ensure_ascii=False), flush=True)
    return 0 if resultado["resultado"] == "APROVADO" else 1


if __name__ == "__main__":
    raise SystemExit(main())
