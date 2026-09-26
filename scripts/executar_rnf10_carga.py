#!/usr/bin/env python3
"""Executa as três repetições progressivas e de pico do RNF10."""

from __future__ import annotations

import asyncio
import csv
import json
import math
import os
import statistics
import subprocess
import sys
import time
import uuid
from pathlib import Path

import httpx


PORTA = 8012
BASE_URL = f"http://127.0.0.1:{PORTA}"
DURACAO_ESTAGIO_S = int(os.environ.get("RNF10_DURACAO_ESTAGIO_S", "300"))
AQUECIMENTO_S = int(os.environ.get("RNF10_AQUECIMENTO_S", "60"))
CONCORRENCIAS = (5, 10, 25, 50)


def percentil(valores: list[float], q: float) -> float:
    ordenados = sorted(valores)
    return ordenados[max(0, math.ceil(q * len(ordenados)) - 1)]


def rss_mib(pid: int) -> float | None:
    try:
        for linha in Path(f"/proc/{pid}/status").read_text().splitlines():
            if linha.startswith("VmRSS:"):
                return int(linha.split()[1]) / 1024
    except FileNotFoundError:
        return None
    return None


def cpu_ticks(pid: int) -> int | None:
    try:
        campos = Path(f"/proc/{pid}/stat").read_text().split()
        return int(campos[13]) + int(campos[14])
    except FileNotFoundError:
        return None


async def monitorar(pid: int, parar: asyncio.Event, recursos: list[dict], contexto: dict) -> None:
    clk = os.sysconf(os.sysconf_names["SC_CLK_TCK"])
    anterior_t = time.monotonic()
    anterior_ticks = cpu_ticks(pid)
    while not parar.is_set():
        agora = time.monotonic()
        ticks = cpu_ticks(pid)
        cpu = ""
        if ticks is not None and anterior_ticks is not None and agora > anterior_t:
            cpu = (ticks - anterior_ticks) / clk / (agora - anterior_t) * 100
        recursos.append(
            {
                **contexto,
                "monotonico_s": f"{agora:.6f}",
                "rss_mib": rss_mib(pid) or "",
                "cpu_percent": cpu,
            }
        )
        anterior_t, anterior_ticks = agora, ticks
        try:
            await asyncio.wait_for(parar.wait(), timeout=0.1)
        except TimeoutError:
            pass


async def requisicao(cliente: httpx.AsyncClient, indice: int) -> tuple[float, int | None, bool, str]:
    inicio = time.perf_counter()
    status = None
    completa = False
    erro = ""
    try:
        async with asyncio.timeout(65):
            resposta = await cliente.post(
                BASE_URL + "/api/v1/chat",
                json={
                    "message": f"Consulta sintética RNF10 número {indice % 100:03d}",
                    "conversation_id": str(uuid.uuid5(uuid.NAMESPACE_URL, f"rnf10-{indice}")),
                },
            )
        status = resposta.status_code
        if status == 200:
            corpo = resposta.json()
            completa = isinstance(corpo.get("reply"), str) and bool(corpo["reply"].strip())
            if not completa:
                erro = "contrato_incompleto"
        else:
            erro = "http_error"
    except TimeoutError:
        erro = "timeout_total"
    except httpx.HTTPError:
        erro = "transporte"
    return time.perf_counter() - inicio, status, completa, erro


async def estagio(
    *, tipo: str, repeticao: int, concorrencia: int, duracao: int,
    tentativas: list[dict], recursos: list[dict], pid: int, registrar: bool,
) -> dict:
    fim = time.monotonic() + duracao
    contador = 0
    lock = asyncio.Lock()
    em_andamento = 0
    pico_andamento = 0
    parar_monitor = asyncio.Event()
    contexto = {"tipo": tipo, "repeticao": repeticao, "concorrencia": concorrencia}
    monitor = asyncio.create_task(monitorar(pid, parar_monitor, recursos, contexto))
    limites = httpx.Limits(max_connections=60, max_keepalive_connections=60)
    async with httpx.AsyncClient(timeout=httpx.Timeout(65, connect=5), limits=limites) as cliente:
        async def trabalhador(worker: int) -> None:
            nonlocal contador, em_andamento, pico_andamento
            while time.monotonic() < fim:
                async with lock:
                    indice = contador
                    contador += 1
                    em_andamento += 1
                    pico_andamento = max(pico_andamento, em_andamento)
                duracao_req, status, completa, erro = await requisicao(cliente, repeticao * 10_000_000 + worker * 100_000 + indice)
                async with lock:
                    em_andamento -= 1
                if registrar:
                    tentativas.append(
                        {
                            "tipo": tipo,
                            "repeticao": repeticao,
                            "concorrencia": concorrencia,
                            "indice": indice,
                            "duracao_s": f"{duracao_req:.6f}",
                            "status_http": status if status is not None else "",
                            "resposta_completa": completa,
                            "erro": erro,
                        }
                    )
        inicio = time.monotonic()
        await asyncio.gather(*(trabalhador(i) for i in range(concorrencia)))
        decorrido = time.monotonic() - inicio
    parar_monitor.set()
    await monitor
    grupo = tentativas[-contador:] if registrar else []
    duracoes = [float(x["duracao_s"]) for x in grupo]
    resumo = {
        "tipo": tipo,
        "repeticao": repeticao,
        "concorrencia": concorrencia,
        "tentativas": contador,
        "pico_concorrencia_observado": pico_andamento,
        "duracao_s": decorrido,
        "throughput_rps": contador / decorrido,
        "respostas_completas": sum(str(x["resposta_completa"]) == "True" for x in grupo),
        "erros": sum(bool(x["erro"]) for x in grupo),
        "p50_s": percentil(duracoes, 0.50) if duracoes else "",
        "p80_s": percentil(duracoes, 0.80) if duracoes else "",
        "p95_s": percentil(duracoes, 0.95) if duracoes else "",
    }
    return resumo


def iniciar_servidor() -> subprocess.Popen:
    processo = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "rnf10_servidor:app", "--host", "127.0.0.1", "--port", str(PORTA), "--log-level", "error"],
        cwd="/app", stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    limite = time.monotonic() + 30
    while time.monotonic() < limite:
        if processo.poll() is not None:
            raise RuntimeError("servidor RNF10 encerrou durante a inicialização")
        try:
            if httpx.get(BASE_URL + "/health", timeout=1).status_code == 200:
                return processo
        except httpx.HTTPError:
            pass
        time.sleep(0.25)
    processo.terminate()
    raise RuntimeError("servidor RNF10 não ficou pronto em 30 segundos")


def parar_servidor(processo: subprocess.Popen) -> None:
    processo.terminate()
    try:
        processo.wait(timeout=10)
    except subprocess.TimeoutExpired:
        processo.kill()
        processo.wait(timeout=5)


async def campanha(saida: Path) -> dict:
    tentativas: list[dict] = []
    recursos: list[dict] = []
    resumos: list[dict] = []
    for repeticao in range(1, 4):
        servidor = iniciar_servidor()
        try:
            print(f"progressivo r{repeticao}: aquecimento 5 concorrentes por {AQUECIMENTO_S}s", flush=True)
            await estagio(tipo="aquecimento_progressivo", repeticao=repeticao, concorrencia=5, duracao=AQUECIMENTO_S, tentativas=tentativas, recursos=recursos, pid=servidor.pid, registrar=False)
            for concorrencia in CONCORRENCIAS:
                print(f"progressivo r{repeticao}: {concorrencia} concorrentes por {DURACAO_ESTAGIO_S}s", flush=True)
                resumo = await estagio(tipo="progressivo", repeticao=repeticao, concorrencia=concorrencia, duracao=DURACAO_ESTAGIO_S, tentativas=tentativas, recursos=recursos, pid=servidor.pid, registrar=True)
                resumos.append(resumo)
                print("RESUMO=" + json.dumps(resumo, ensure_ascii=False), flush=True)
        finally:
            parar_servidor(servidor)

    for repeticao in range(1, 4):
        servidor = iniciar_servidor()
        try:
            print(f"pico r{repeticao}: aquecimento 5 concorrentes por {AQUECIMENTO_S}s", flush=True)
            await estagio(tipo="aquecimento_pico", repeticao=repeticao, concorrencia=5, duracao=AQUECIMENTO_S, tentativas=tentativas, recursos=recursos, pid=servidor.pid, registrar=False)
            print(f"pico r{repeticao}: 50 concorrentes por {DURACAO_ESTAGIO_S}s", flush=True)
            resumo = await estagio(tipo="pico", repeticao=repeticao, concorrencia=50, duracao=DURACAO_ESTAGIO_S, tentativas=tentativas, recursos=recursos, pid=servidor.pid, registrar=True)
            resumos.append(resumo)
            print("RESUMO=" + json.dumps(resumo, ensure_ascii=False), flush=True)
        finally:
            parar_servidor(servidor)

    with (saida / "tentativas.csv").open("w", newline="", encoding="utf-8") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=list(tentativas[0]))
        escritor.writeheader(); escritor.writerows(tentativas)
    with (saida / "recursos.csv").open("w", newline="", encoding="utf-8") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=list(recursos[0]))
        escritor.writeheader(); escritor.writerows(recursos)
    with (saida / "estagios.csv").open("w", newline="", encoding="utf-8") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=list(resumos[0]))
        escritor.writeheader(); escritor.writerows(resumos)

    p95_base = [float(r["p95_s"]) for r in resumos if r["tipo"] == "progressivo" and r["concorrencia"] == 5]
    p95_10x = [float(r["p95_s"]) for r in resumos if r["tipo"] == "progressivo" and r["concorrencia"] == 50]
    p95_pico = [float(r["p95_s"]) for r in resumos if r["tipo"] == "pico"]
    B, C, P = statistics.median(p95_base), statistics.median(p95_10x), statistics.median(p95_pico)
    completas = all(r["respostas_completas"] == r["tentativas"] and r["erros"] == 0 for r in resumos)
    carga_atingida = all(r["pico_concorrencia_observado"] == r["concorrencia"] for r in resumos)
    aprovado = C <= 20 and P <= 20 and C / B <= 2 and P / B <= 2 and completas and carga_atingida
    resultado = {
        "resultado": "APROVADO" if aprovado else "REPROVADO",
        "B_p95_mediano_1x_s": B,
        "C_p95_mediano_10x_progressivo_s": C,
        "P_p95_mediano_pico_s": P,
        "razao_C_B": C / B,
        "razao_P_B": P / B,
        "limite_absoluto_s": 20,
        "limite_relativo": 2,
        "respostas_completas_em_todos_estagios": completas,
        "carga_atingida": carga_atingida,
        "tentativas_totais": len(tentativas),
        "duracao_estagio_s": DURACAO_ESTAGIO_S,
        "aquecimento_s": AQUECIMENTO_S,
    }
    (saida / "resultado.json").write_text(json.dumps(resultado, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return resultado


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit("uso: executar_rnf10_carga.py DIRETORIO")
    saida = Path(sys.argv[1]); saida.mkdir(parents=True, exist_ok=True)
    resultado = asyncio.run(campanha(saida))
    print("RESULTADO=" + json.dumps(resultado, ensure_ascii=False), flush=True)
    return 0 if resultado["resultado"] == "APROVADO" else 1


if __name__ == "__main__":
    raise SystemExit(main())
