#!/usr/bin/env python3
"""Mede RSS de treino e serviço em subprocessos descartáveis."""

from __future__ import annotations

import csv
import json
import statistics
import subprocess
import sys
import time
from pathlib import Path


def rss_mib(pid: int) -> float | None:
    try:
        for linha in Path(f"/proc/{pid}/status").read_text().splitlines():
            if linha.startswith("VmRSS:"):
                return int(linha.split()[1]) / 1024
    except (FileNotFoundError, ProcessLookupError):
        return None
    return None


def medir(comando: list[str], fase: str, fator: int, repeticao: int, adverso: bool) -> dict:
    inicio = time.monotonic()
    processo = subprocess.Popen(comando, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    amostras: list[tuple[float, float]] = []
    while processo.poll() is None:
        valor = rss_mib(processo.pid)
        if valor is not None:
            amostras.append((time.monotonic() - inicio, valor))
        time.sleep(0.1)
    stdout, stderr = processo.communicate()
    if processo.returncode != 0:
        raise RuntimeError(f"worker falhou ({fase} {fator}x r{repeticao}): {stderr[-2000:]}")
    eventos = [json.loads(linha) for linha in stdout.splitlines() if linha.startswith("{")]
    estabilizadas = [rss for segundo, rss in amostras if 20 <= segundo <= 30]
    inferencia = [rss for segundo, rss in amostras if segundo >= 30]
    return {
        "fase": fase,
        "fator": fator,
        "repeticao": repeticao,
        "adverso": adverso,
        "amostras": len(amostras),
        "rss_pico_mib": max((rss for _, rss in amostras), default=0),
        "rss_estabilizada_mib": statistics.median(estabilizadas) if estabilizadas else "",
        "rss_pico_inferencia_mib": max(inferencia, default=0) if fase == "servico" else "",
        "duracao_processo_s": time.monotonic() - inicio,
        "eventos": eventos,
    }


def mediana(linhas: list[dict], chave: str) -> float:
    return statistics.median(float(linha[chave]) for linha in linhas)


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit("uso: executar_rnf10_memoria.py DIRETORIO")
    saida = Path(sys.argv[1])
    saida.mkdir(parents=True, exist_ok=True)
    modelos = saida / "modelos_temporarios"
    worker = "/app/rnf10_memoria_worker.py"
    python = sys.executable
    linhas: list[dict] = []
    condicoes = [(1, False), (2, False), (5, False), (10, False), (10, True)]
    for fator, adverso in condicoes:
        rotulo = "adverso" if adverso else "controlado"
        for repeticao in range(1, 4):
            modelo = modelos / f"{rotulo}-{fator}x-r{repeticao}.joblib"
            treino = medir(
                [python, worker, "treino", "--fator", str(fator), "--modelo", str(modelo), *( ["--adverso"] if adverso else [])],
                "treino", fator, repeticao, adverso,
            )
            linhas.append(treino)
            print(f"treino {rotulo} {fator}x r{repeticao}: pico={treino['rss_pico_mib']:.2f} MiB", flush=True)
            servico = medir(
                [python, worker, "servico", "--fator", str(fator), "--modelo", str(modelo), *( ["--adverso"] if adverso else [])],
                "servico", fator, repeticao, adverso,
            )
            linhas.append(servico)
            print(
                f"serviço {rotulo} {fator}x r{repeticao}: estabilizada={servico['rss_estabilizada_mib']:.2f} MiB pico={servico['rss_pico_inferencia_mib']:.2f} MiB",
                flush=True,
            )

    campos = ["fase", "fator", "repeticao", "adverso", "amostras", "rss_pico_mib", "rss_estabilizada_mib", "rss_pico_inferencia_mib", "duracao_processo_s", "eventos"]
    with (saida / "medicoes.csv").open("w", newline="", encoding="utf-8") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=campos)
        escritor.writeheader()
        escritor.writerows({**linha, "eventos": json.dumps(linha["eventos"], ensure_ascii=False)} for linha in linhas)

    def grupo(fase: str, fator: int, adverso: bool) -> list[dict]:
        return [l for l in linhas if l["fase"] == fase and l["fator"] == fator and l["adverso"] == adverso]

    base_t = mediana(grupo("treino", 1, False), "rss_pico_mib")
    base_s = mediana(grupo("servico", 1, False), "rss_estabilizada_mib")
    base_i = mediana(grupo("servico", 1, False), "rss_pico_inferencia_mib")
    resumos = {}
    aprovado = True
    for adverso in (False, True):
        nome = "adverso_10x" if adverso else "controlado_10x"
        pico_t = mediana(grupo("treino", 10, adverso), "rss_pico_mib")
        est_s = mediana(grupo("servico", 10, adverso), "rss_estabilizada_mib")
        pico_i = mediana(grupo("servico", 10, adverso), "rss_pico_inferencia_mib")
        resumo = {
            "razao_treino": pico_t / base_t,
            "razao_servico_estabilizada": est_s / base_s,
            "razao_servico_pico": pico_i / base_i,
        }
        resumo["aprovado"] = resumo["razao_treino"] <= 8 and resumo["razao_servico_estabilizada"] <= 2 and resumo["razao_servico_pico"] <= 2
        aprovado &= resumo["aprovado"]
        resumos[nome] = resumo
    resultado = {"resultado": "APROVADO" if aprovado else "REPROVADO", "linha_base": {"treino_pico_mib": base_t, "servico_estabilizada_mib": base_s, "servico_pico_mib": base_i}, "comparacoes": resumos, "amostragem_rss_ms": 100}
    (saida / "resultado.json").write_text(json.dumps(resultado, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("RESULTADO=" + json.dumps(resultado, ensure_ascii=False), flush=True)
    return 0 if aprovado else 1


if __name__ == "__main__":
    raise SystemExit(main())
