#!/usr/bin/env python3
"""Processo descartável medido pelo executor de memória do RNF10."""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import joblib

from pln.caminhos import DATASET_PADRAO
from pln.classificador import carregar_dataset, construir_classificador, prever_intencao


def dados(fator: int, adverso: bool) -> tuple[list[str], list[str]]:
    textos, rotulos = carregar_dataset(DATASET_PADRAO)
    saida_textos: list[str] = []
    saida_rotulos: list[str] = []
    for copia in range(fator):
        for indice, (texto, rotulo) in enumerate(zip(textos, rotulos, strict=True)):
            sufixo = f" termo_exclusivo_{copia}_{indice}" if adverso else ""
            saida_textos.append(texto + sufixo)
            saida_rotulos.append(rotulo)
    return saida_textos, saida_rotulos


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("modo", choices=("treino", "servico"))
    parser.add_argument("--fator", type=int, required=True)
    parser.add_argument("--modelo", type=Path, required=True)
    parser.add_argument("--adverso", action="store_true")
    args = parser.parse_args()
    if args.modo == "treino":
        textos, rotulos = dados(args.fator, args.adverso)
        inicio = time.perf_counter()
        modelo = construir_classificador()
        modelo.fit(textos, rotulos)
        args.modelo.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(modelo, args.modelo)
        print(json.dumps({"fase": "treino", "exemplos": len(textos), "duracao_s": time.perf_counter() - inicio}), flush=True)
        return

    inicio = time.perf_counter()
    modelo = joblib.load(args.modelo)
    textos, _ = dados(args.fator, args.adverso)
    carga_s = time.perf_counter() - inicio
    print(json.dumps({"fase": "carregado", "carga_s": carga_s}), flush=True)
    time.sleep(30)
    inicio_inferencia = time.perf_counter()
    for indice in range(100):
        prever_intencao(modelo, textos[indice % len(textos)])
    print(json.dumps({"fase": "servico", "inferencias": 100, "duracao_s": time.perf_counter() - inicio_inferencia}), flush=True)


if __name__ == "__main__":
    main()
