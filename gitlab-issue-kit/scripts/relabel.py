#!/usr/bin/env python3
"""Adiciona e/ou remove labels em issues que já existem.

Utilitário à parte do kit: o create_issues.py só cria, nunca edita.

    # trocar uma label por outra
    python scripts/relabel.py --when DOCUMENTATION --add DOCS --remove DOCUMENTATION --dry-run

    # só remover
    python scripts/relabel.py --when DOCS --remove DOCUMENTATION

Usa PUT /issues/:iid com add_labels / remove_labels, que mexem apenas nas
labels indicadas em vez de reescrever a lista inteira — nenhuma outra label da
issue é afetada, e não há risco de corrida com quem estiver mexendo no board.
"""

import argparse
import sys
import time
from pathlib import Path

import requests

from gitlab_kit import DEFAULT_CONFIG_PATH, Config, load_credentials


def listar_issues(creds, config) -> list[dict]:
    issues, pagina = [], 1
    while True:
        resposta = requests.get(
            f"{creds.api_base}/issues",
            headers=creds.headers,
            params={"state": "all", "per_page": 100, "page": pagina},
            timeout=config.timeout_seconds,
        )
        resposta.raise_for_status()
        lote = resposta.json()
        issues += lote
        if len(lote) < 100:
            return issues
        pagina += 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--when", required=True, help="só nas issues que têm esta label")
    ap.add_argument("--add", default=None, help="label a adicionar")
    ap.add_argument("--remove", default=None, help="label a remover")
    ap.add_argument("--milestone", default=None, help="restringe a uma milestone")
    ap.add_argument("--exclude-iid", type=int, nargs="*", default=[],
                    help="iids a não tocar")
    ap.add_argument("--dry-run", action="store_true", help="não escreve nada")
    ap.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    args = ap.parse_args()

    if not args.add and not args.remove:
        ap.error("informe pelo menos --add ou --remove")

    config = Config.load(args.config)
    creds = load_credentials()

    acao = " e ".join(
        p for p in (f"+{args.add}" if args.add else "",
                    f"-{args.remove}" if args.remove else "") if p
    )
    modo = "DRY-RUN" if args.dry_run else "REAL"
    print(f"\n🏷  {acao} nas issues com '{args.when}' — modo: {modo}")
    print(f"   Destino: {creds.url} (projeto {creds.project_id})\n")

    issues = listar_issues(creds, config)
    alvo = []
    for issue in issues:
        labels = set(issue["labels"])
        if args.when not in labels:
            continue
        if issue["iid"] in args.exclude_iid:
            continue
        if args.milestone is not None:
            if (issue.get("milestone") or {}).get("title") != args.milestone:
                continue
        # já está no estado desejado? então não gasta chamada
        if args.remove and args.remove not in labels:
            continue
        if args.add and args.add in labels and not args.remove:
            continue
        alvo.append(issue)

    print(f"📋 {len(alvo)} issue(s) afetada(s) de {len(issues)} no projeto.\n")
    if not alvo:
        return 0

    payload_base = {}
    if args.add:
        payload_base["add_labels"] = args.add
    if args.remove:
        payload_base["remove_labels"] = args.remove

    ok = falhas = 0
    for n, issue in enumerate(alvo, 1):
        iid, titulo = issue["iid"], issue["title"]
        print(f"[{n}/{len(alvo)}] #{iid} {titulo[:60]}")
        if args.dry_run:
            restante = set(issue["labels"])
            if args.remove:
                restante.discard(args.remove)
            if args.add:
                restante.add(args.add)
            print(f"    [DRY-RUN] ficaria: {', '.join(sorted(restante))}")
            ok += 1
            continue
        try:
            resposta = requests.put(
                f"{creds.api_base}/issues/{iid}",
                headers=creds.headers,
                json=payload_base,
                timeout=config.timeout_seconds,
            )
            resposta.raise_for_status()
            print(f"  ✓ ok — {', '.join(sorted(resposta.json()['labels']))}")
            ok += 1
        except Exception as exc:  # noqa: BLE001
            print(f"  ✗ falha em #{iid}: {exc}")
            falhas += 1
        time.sleep(config.request_delay_seconds)

    print("\n" + "=" * 60)
    print(f"✅ Atualizadas: {ok}" + (f" | Falhas: {falhas}" if falhas else ""))
    return 1 if falhas else 0


if __name__ == "__main__":
    sys.exit(main())
