#!/usr/bin/env python3
"""Cria no projeto todas as labels do catálogo do config.yml.

Roda uma vez por projeto novo. É idempotente: label que já existe é pulada,
então rodar de novo não duplica nem sobrescreve cor.

    python scripts/setup_labels.py --dry-run    # lista sem tocar na rede
    python scripts/setup_labels.py              # cria de verdade

Não é obrigatório: o create_issues.py cria sob demanda qualquer label que uma
issue precise. O que este script adiciona é provisionar o catálogo inteiro de
uma vez — inclusive as aplicadas à mão durante a sprint, como BUG e BLOCK, que
nenhuma issue traz do CSV e portanto nunca nasceriam sozinhas.

Falha numa label não interrompe as demais; o resumo final lista o que falhou.
"""

import argparse
import sys
from pathlib import Path

from gitlab_kit import DEFAULT_CONFIG_PATH, Config, GitLabClient, load_credentials


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true",
                    help="não faz nenhuma chamada de rede")
    ap.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    args = ap.parse_args()

    config = Config.load(args.config)
    creds = load_credentials(required=not args.dry_run)
    client = GitLabClient(config, creds, dry_run=args.dry_run)

    destino = creds.project_id if creds else "(sem credenciais)"
    print(f"\n🏷  Sincronizando {len(config.labels)} labels em projeto {destino}")
    print(f"   Config: {args.config}\n")

    # Em dry-run devolve conjunto vazio sem ir na rede: tudo aparece como novo.
    existentes = client.existing_labels()

    criadas = ja_existiam = falhas = 0
    for label in config.labels:
        nome = label["name"]
        if nome in existentes:
            print(f"  ✓ já existe: {nome}")
            ja_existiam += 1
            continue
        try:
            status = client.create_label(label)
            if status == "exists":
                ja_existiam += 1
            else:
                criadas += 1
        except Exception as exc:  # noqa: BLE001
            print(f"  ✗ falha em '{nome}': {exc}")
            falhas += 1

    print("\n" + "=" * 40)
    resumo = f"✅ Criadas: {criadas} | Já existiam: {ja_existiam}"
    if falhas:
        resumo += f" | Falhas: {falhas}"
    print(resumo)
    return 1 if falhas else 0


if __name__ == "__main__":
    sys.exit(main())
