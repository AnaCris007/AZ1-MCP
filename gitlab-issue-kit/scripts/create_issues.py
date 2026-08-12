#!/usr/bin/env python3
"""
create_issues.py — Cria issues no GitLab em lote, a partir de um CSV.

Uso:
    python create_issues.py --csv backlog_exemplo.csv --dry-run
    python create_issues.py --csv backlog_sprint1.csv

O comportamento específico do projeto (labels, cores, tamanhos, formato da
descrição) vive em config.yml — edite lá, não aqui.

Credenciais: GITLAB_URL, GITLAB_TOKEN, GITLAB_PROJECT_ID (ver .env.example).
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import requests

from gitlab_kit import DEFAULT_CONFIG_PATH, Config, GitLabClient, load_credentials

REQUIRED_COLUMNS = {
    "title",
    "description",
    "objective",
    "tasks",
    "dor",
    "dod",
    "labels",
    "size",
    "milestone",
}


# ---------------------------------------------------------------------------
# Modelos
# ---------------------------------------------------------------------------


@dataclass
class IssueInput:
    row_number: int
    title: str
    description: str
    objective: str
    dependencies: list[str]
    tasks: list[str]
    dor: list[str]
    dod: list[str]
    labels: list[str]
    size: str
    milestone: str
    priority: str
    kind: str

    @classmethod
    def from_csv_row(cls, row: dict[str, str], row_number: int, config: Config) -> "IssueInput":
        def split(value: str) -> list[str]:
            return [v.strip() for v in (value or "").split(config.list_separator) if v.strip()]

        return cls(
            row_number=row_number,
            title=(row.get("title") or "").strip(),
            description=(row.get("description") or "").strip(),
            objective=(row.get("objective") or "").strip(),
            dependencies=split(row.get("dependencies", "")),
            tasks=split(row.get("tasks", "")),
            dor=split(row.get("dor", "")),
            dod=split(row.get("dod", "")),
            labels=[
                lb.strip()
                for lb in (row.get("labels") or "").split(config.label_separator)
                if lb.strip()
            ],
            size=(row.get("size") or "").strip().upper(),
            milestone=(row.get("milestone") or "").strip(),
            priority=(row.get("priority") or "").strip().lower(),
            kind=(row.get("kind") or "").strip().upper(),
        )


@dataclass
class CreatedIssue:
    iid: int
    title: str
    url: str
    labels: list[str]
    milestone: Optional[str]


# ---------------------------------------------------------------------------
# Montagem da issue
# ---------------------------------------------------------------------------


def format_checklist(items: list[str], config: Config) -> str:
    return "\n".join(f"{config.checklist_marker}{item}" for item in items)


def format_dependencies(items: list[str], config: Config) -> str:
    if not items or [i.lower() for i in items] == ["nenhuma"]:
        return config.no_dependencies_text
    return "\n".join(f"{config.bullet_marker}{item}" for item in items)


def derive_kind(issue: IssueInput, config: Config) -> str:
    """Resolve a label de tipo de trabalho: valor do CSV, ou inferido da camada."""
    if issue.kind:
        return issue.kind

    for label in issue.labels:
        if label in config.kind_from_labels:
            return config.kind_from_labels[label]

    return config.default_kind


def build_labels(issue: IssueInput, config: Config) -> list[str]:
    labels = set(issue.labels)
    labels.add(config.size_label(issue.size))

    priority_label = config.priority_label(issue.priority)
    if priority_label:
        labels.add(priority_label)

    labels.add(derive_kind(issue, config))
    return sorted(labels)


def build_description(issue: IssueInput, config: Config) -> str:
    fields = {
        "title": issue.title,
        "objective": issue.objective,
        "context": issue.description,
        "dependencies": format_dependencies(issue.dependencies, config),
        "tasks": format_checklist(issue.tasks, config),
        "dor": format_checklist(issue.dor, config),
        "dod": format_checklist(issue.dod, config),
        "size": issue.size,
        "size_description": config.sizes.get(issue.size, ""),
        "milestone": issue.milestone,
        "priority": issue.priority,
        "kind": derive_kind(issue, config),
    }
    try:
        return config.template.format(**fields)
    except (KeyError, IndexError) as exc:
        print(
            f"❌ `description.template` do config.yml usa um placeholder inválido: {exc}\n"
            f"   Chaves literais {{ }} precisam ser escritas duplicadas: {{{{ }}}}\n"
            f"   Placeholders válidos: {', '.join(sorted(fields))}",
            file=sys.stderr,
        )
        sys.exit(1)


# ---------------------------------------------------------------------------
# Leitura e validação do CSV
# ---------------------------------------------------------------------------


def load_issues(path: Path, config: Config) -> list[IssueInput]:
    with path.open(encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)

        missing = REQUIRED_COLUMNS - set(reader.fieldnames or [])
        if missing:
            print(f"❌ CSV com colunas obrigatórias faltando: {sorted(missing)}", file=sys.stderr)
            sys.exit(1)

        issues: list[IssueInput] = []
        for line_no, row in enumerate(reader, start=2):
            if not (row.get("title") or "").strip():
                print(f"  ⚠  linha {line_no} ignorada (título vazio)")
                continue
            issues.append(IssueInput.from_csv_row(row, line_no, config))

    return issues


def validate(issues: list[IssueInput], config: Config) -> list[str]:
    """Checa o lote inteiro antes de criar qualquer coisa no GitLab.

    Erros abortam; avisos apenas informam. Falhar cedo evita o pior cenário:
    metade das issues criadas e o resto travado num CSV mal formado.
    """
    errors: list[str] = []
    valid_sizes = set(config.sizes)
    allowed_kinds = set(config.allowed_kinds)
    seen_titles: dict[str, int] = {}

    for issue in issues:
        prefix = f"linha {issue.row_number} ({issue.title[:50]})"

        if issue.size not in valid_sizes:
            errors.append(f"{prefix}: size '{issue.size}' inválido — use um de {sorted(valid_sizes)}")

        if issue.kind and allowed_kinds and issue.kind not in allowed_kinds:
            errors.append(f"{prefix}: kind '{issue.kind}' inválido — use um de {sorted(allowed_kinds)}")

        if not issue.tasks:
            print(f"  ⚠  {prefix}: sem tasks")
        if not issue.milestone:
            print(f"  ⚠  {prefix}: sem milestone — issue ficará fora da sprint")

        if issue.title in seen_titles:
            print(f"  ⚠  {prefix}: título duplicado (já aparece na linha {seen_titles[issue.title]})")
        else:
            seen_titles[issue.title] = issue.row_number

    return errors


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def save_report(created: list[CreatedIssue], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    report_path = output_dir / "issues_created.json"
    report_path.write_text(
        json.dumps(
            [
                {
                    "iid": c.iid,
                    "title": c.title,
                    "url": c.url,
                    "labels": c.labels,
                    "milestone": c.milestone,
                }
                for c in created
            ],
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    print(f"\n📄 Relatório salvo em: {report_path}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Cria issues no GitLab a partir de um arquivo CSV.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--csv", required=True, type=Path, help="Caminho do CSV de backlog.")
    parser.add_argument("--dry-run", action="store_true", help="Simula tudo, sem tocar no GitLab.")
    parser.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_CONFIG_PATH,
        help=f"Config do projeto (padrão: {DEFAULT_CONFIG_PATH.name} ao lado do script).",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("outputs"),
        help="Onde salvar o relatório JSON (padrão: outputs).",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if not args.csv.exists():
        print(f"❌ CSV não encontrado: {args.csv}", file=sys.stderr)
        return 1

    config = Config.load(args.config)
    credentials = load_credentials(required=not args.dry_run)

    mode = "DRY-RUN" if args.dry_run else "PRODUÇÃO"
    target = f"{credentials.url} (projeto {credentials.project_id})" if credentials else "—"
    print(f"\n🚀 Criando issues — modo: {mode}")
    print(f"   Destino: {target}")
    print(f"   Config:  {args.config}")
    print(f"   CSV:     {args.csv}\n")

    issues = load_issues(args.csv, config)
    if not issues:
        print("Nada a criar — CSV sem linhas válidas.")
        return 1

    validation_errors = validate(issues, config)
    if validation_errors:
        print(f"\n❌ {len(validation_errors)} erro(s) de validação — nada foi criado:", file=sys.stderr)
        for err in validation_errors:
            print(f"   - {err}", file=sys.stderr)
        return 1

    print(f"\n📋 {len(issues)} issue(s) válida(s) no CSV.\n")

    client = GitLabClient(config, credentials, dry_run=args.dry_run)
    created: list[CreatedIssue] = []
    failures: list[tuple[str, str]] = []

    for idx, issue in enumerate(issues, start=1):
        print(f"[{idx}/{len(issues)}] {issue.title}")
        try:
            labels = build_labels(issue, config)
            client.ensure_labels(labels)

            payload: dict = {
                "title": issue.title,
                "description": build_description(issue, config),
                "labels": ",".join(labels),
            }
            if issue.milestone:
                milestone_id = client.resolve_milestone_id(issue.milestone)
                if milestone_id:
                    payload["milestone_id"] = milestone_id

            data = client.create_issue(payload)
            created.append(
                CreatedIssue(
                    iid=data.get("iid", 0),
                    title=data.get("title", issue.title),
                    url=data.get("web_url", "dry-run"),
                    labels=labels,
                    milestone=issue.milestone or None,
                )
            )
            if args.dry_run:
                print("  ✓ [DRY-RUN] ok")
            else:
                print(f"  ✓ #{created[-1].iid} → {created[-1].url}")

        except requests.HTTPError as exc:
            detail = exc.response.text[:200] if exc.response is not None else str(exc)
            print(f"  ✗ HTTP {exc.response.status_code if exc.response is not None else '?'}: {detail}")
            failures.append((issue.title, detail))
        except Exception as exc:  # noqa: BLE001
            print(f"  ✗ erro: {exc}")
            failures.append((issue.title, str(exc)))

    print(f"\n{'=' * 60}")
    print(f"✅ Criadas: {len(created)}")
    if failures:
        print(f"❌ Falhas:  {len(failures)}")
        for title, err in failures:
            print(f"   - {title}: {err}")

    if not args.dry_run and created:
        save_report(created, args.output_dir)

    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
