#!/usr/bin/env python3
"""Cria o template de descrição de merge request do projeto.

O conteúdo mora no config.yml, em `merge_request.template` — como todo o resto
do comportamento específico de projeto.

    python setup_mr_template.py --dry-run     # mostra o que seria escrito
    python setup_mr_template.py               # escreve o arquivo no repo
    python setup_mr_template.py --apply-remote  # + grava na config do projeto

O arquivo vai para .gitlab/merge_request_templates/<name>.md, que é onde o
GitLab procura os templates. Depois de commitado, o nome aparece no seletor
"Choose a template" ao abrir um MR.

--apply-remote grava o mesmo texto em `merge_requests_template` nas settings do
projeto, que preenche TODO merge request novo sem precisar escolher template.
Isso é uma escrita no GitLab e exige token com escopo `api`.
"""

import argparse
import sys
from pathlib import Path

import requests
import yaml

from gitlab_kit import DEFAULT_CONFIG_PATH, Config, load_credentials


def achar_raiz_repo() -> Path:
    """Sobe a partir deste arquivo até achar a pasta com .git."""
    for pasta in Path(__file__).resolve().parents:
        if (pasta / ".git").exists():
            return pasta
    # sem repo git à vista: assume a pasta acima do kit
    return Path(__file__).resolve().parents[2]


def carregar_template(caminho_config: Path) -> tuple[str, str]:
    raw = yaml.safe_load(caminho_config.read_text(encoding="utf-8")) or {}
    mr = raw.get("merge_request") or {}
    template = mr.get("template")
    if not template:
        raise SystemExit(
            f"❌ '{caminho_config}' não tem a seção merge_request.template"
        )
    return mr.get("name", "Default"), template


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", type=Path, default=None,
                    help="raiz do repositório (padrão: detectada pelo .git)")
    ap.add_argument("--apply-remote", action="store_true",
                    help="também grava em merge_requests_template do projeto")
    ap.add_argument("--dry-run", action="store_true", help="não escreve nada")
    ap.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    args = ap.parse_args()

    caminho_config = args.config
    nome, template = carregar_template(caminho_config)

    repo = args.repo.resolve() if args.repo else achar_raiz_repo()
    if not (repo / ".git").exists():
        print(f"⚠  '{repo}' não parece a raiz de um repositório git.")
        print("   Use --repo para apontar o caminho certo.")

    destino = repo / ".gitlab" / "merge_request_templates" / f"{nome}.md"
    modo = "DRY-RUN" if args.dry_run else "REAL"
    print(f"\n📝 Template de merge request '{nome}' — modo: {modo}")
    print(f"   Destino: {destino}\n")

    if destino.exists():
        atual = destino.read_text(encoding="utf-8")
        if atual == template:
            print("  ✓ já está em dia — nada a fazer.")
        else:
            print("  ⚠  arquivo já existe com conteúdo diferente e será sobrescrito.")
    if args.dry_run:
        print("-" * 60)
        print(template)
        print("-" * 60)
    else:
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(template, encoding="utf-8")
        print(f"  ✓ escrito ({len(template)} caracteres)")
        print("\n  Falta commitar — o GitLab só enxerga o template depois")
        print("  que ele chega na branch padrão do projeto.")

    if args.apply_remote:
        config = Config.load(caminho_config)
        creds = load_credentials()
        print(f"\n🌐 Gravando em merge_requests_template do projeto {creds.project_id}")
        if args.dry_run:
            print("  [DRY-RUN] PUT /projects/:id")
        else:
            resposta = requests.put(
                f"{creds.url}/api/v4/projects/{creds.project_id}",
                headers=creds.headers,
                json={"merge_requests_template": template},
                timeout=config.timeout_seconds,
            )
            resposta.raise_for_status()
            print("  ✓ ok — todo MR novo já nasce com essa descrição")

    return 0


if __name__ == "__main__":
    sys.exit(main())
