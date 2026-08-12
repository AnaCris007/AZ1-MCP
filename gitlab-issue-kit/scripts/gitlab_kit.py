#!/usr/bin/env python3
"""
gitlab_kit.py — Núcleo compartilhado do kit.

Concentra o que create_issues.py e setup_labels.py têm em comum:
carregamento do config.yml, credenciais do .env e o cliente HTTP do GitLab.

Não é executável — importe a partir dos scripts de CLI.
"""

from __future__ import annotations

import json
import os
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

try:
    import requests
    import yaml
    from dotenv import load_dotenv
except ImportError as exc:  # pragma: no cover
    print(
        f"❌ Dependência faltando: {exc.name}\n"
        f"   Instale com: pip install -r requirements.txt",
        file=sys.stderr,
    )
    sys.exit(1)


KIT_DIR = Path(__file__).resolve().parent
DEFAULT_CONFIG_PATH = KIT_DIR / "config.yml"


# O console padrão do Windows (cp1252) não encoda os emojis das mensagens de
# progresso e derruba o script com UnicodeEncodeError. Forçar UTF-8 na saída
# resolve; onde não der (stream redirecionado sem reconfigure), seguimos.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
    except (AttributeError, OSError, ValueError):
        pass


# ---------------------------------------------------------------------------
# Credenciais
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Credentials:
    url: str
    token: str
    project_id: str

    @property
    def api_base(self) -> str:
        return f"{self.url}/api/v4/projects/{self.project_id}"

    @property
    def headers(self) -> dict[str, str]:
        return {"PRIVATE-TOKEN": self.token, "Content-Type": "application/json"}


def load_credentials(required: bool = True) -> Optional[Credentials]:
    """Lê GITLAB_URL / GITLAB_TOKEN / GITLAB_PROJECT_ID do ambiente.

    Procura um .env no diretório atual (subindo na árvore) e, como fallback,
    o .env que estiver ao lado deste arquivo. Assim o kit funciona tanto
    copiado para dentro de um projeto quanto usado de fora dele.

    Com required=False, devolve None em vez de abortar — usado pelo --dry-run,
    que não faz nenhuma chamada de rede e portanto não precisa de token.
    """
    load_dotenv()
    load_dotenv(KIT_DIR / ".env")

    url = os.environ.get("GITLAB_URL", "").strip().rstrip("/")
    token = os.environ.get("GITLAB_TOKEN", "").strip()
    project_id = os.environ.get("GITLAB_PROJECT_ID", "").strip()

    missing = [
        name
        for name, value in (
            ("GITLAB_URL", url),
            ("GITLAB_TOKEN", token),
            ("GITLAB_PROJECT_ID", project_id),
        )
        if not value
    ]

    if missing:
        if not required:
            return None
        print(
            f"❌ Variáveis de ambiente faltando: {', '.join(missing)}\n"
            f"   Copie .env.example para .env e preencha os valores.\n"
            f"   (dica: rode com --dry-run para validar o CSV sem credenciais)",
            file=sys.stderr,
        )
        sys.exit(1)

    return Credentials(url=url, token=token, project_id=project_id)


# ---------------------------------------------------------------------------
# Configuração
# ---------------------------------------------------------------------------


@dataclass
class Config:
    """Espelho tipado do config.yml."""

    raw: dict[str, Any]

    # api
    request_delay_seconds: float = 0.4
    timeout_seconds: int = 15
    create_missing_milestone: bool = True

    # csv
    list_separator: str = ";"
    label_separator: str = ","

    # sizes / prioridade / kind
    sizes: dict[str, str] = field(default_factory=dict)
    size_label_prefix: str = "SIZE_"
    priority_labels: dict[str, str] = field(default_factory=dict)
    allowed_kinds: list[str] = field(default_factory=list)
    default_kind: str = "FEATURE"
    kind_from_labels: dict[str, str] = field(default_factory=dict)

    # labels
    labels: list[dict[str, str]] = field(default_factory=list)
    default_label_color: str = "#cccccc"

    # descrição
    no_dependencies_text: str = "Nenhuma dependência identificada."
    checklist_marker: str = "- [ ] "
    bullet_marker: str = "- "
    template: str = ""

    @classmethod
    def load(cls, path: Path) -> "Config":
        if not path.exists():
            print(f"❌ Config não encontrado: {path}", file=sys.stderr)
            sys.exit(1)

        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}

        api = raw.get("api", {}) or {}
        csv_cfg = raw.get("csv", {}) or {}
        kind = raw.get("kind", {}) or {}
        desc = raw.get("description", {}) or {}

        cfg = cls(
            raw=raw,
            request_delay_seconds=float(api.get("request_delay_seconds", 0.4)),
            timeout_seconds=int(api.get("timeout_seconds", 15)),
            create_missing_milestone=bool(api.get("create_missing_milestone", True)),
            list_separator=csv_cfg.get("list_separator", ";"),
            label_separator=csv_cfg.get("label_separator", ","),
            sizes=raw.get("sizes", {}) or {},
            size_label_prefix=raw.get("size_label_prefix", "SIZE_"),
            priority_labels={
                str(k).lower(): v for k, v in (raw.get("priority_labels", {}) or {}).items()
            },
            allowed_kinds=list(kind.get("allowed", [])),
            default_kind=kind.get("default", "FEATURE"),
            kind_from_labels=kind.get("infer_from_labels", {}) or {},
            labels=raw.get("labels", []) or [],
            default_label_color=raw.get("default_label_color", "#cccccc"),
            no_dependencies_text=desc.get(
                "no_dependencies_text", "Nenhuma dependência identificada."
            ),
            checklist_marker=desc.get("checklist_marker", "- [ ] "),
            bullet_marker=desc.get("bullet_marker", "- "),
            template=desc.get("template", ""),
        )

        if not cfg.template.strip():
            print(f"❌ Config sem `description.template`: {path}", file=sys.stderr)
            sys.exit(1)

        return cfg

    # --- consultas ---

    def label_color(self, name: str) -> str:
        for entry in self.labels:
            if entry.get("name") == name:
                return entry.get("color", self.default_label_color)
        return self.default_label_color

    def size_label(self, size: str) -> str:
        return f"{self.size_label_prefix}{size}"

    def priority_label(self, priority: str) -> Optional[str]:
        return self.priority_labels.get(priority.strip().lower())


# ---------------------------------------------------------------------------
# Cliente GitLab
# ---------------------------------------------------------------------------


class GitLabClient:
    """Wrapper fino sobre a API v4 do GitLab, com suporte a dry-run.

    Em dry-run nenhuma chamada de rede acontece — nem de leitura — para que o
    CSV possa ser validado sem token configurado.
    """

    def __init__(self, config: Config, credentials: Optional[Credentials], dry_run: bool = False) -> None:
        self.config = config
        self.credentials = credentials
        self.dry_run = dry_run
        self._milestone_cache: dict[str, Optional[int]] = {}
        self._known_labels: Optional[set[str]] = None

    # --- HTTP ---

    def _get(self, path: str, params: dict | None = None) -> Any:
        assert self.credentials is not None, "dry-run não deveria fazer GET"
        response = requests.get(
            f"{self.credentials.api_base}{path}",
            headers=self.credentials.headers,
            params=params or {},
            timeout=self.config.timeout_seconds,
        )
        response.raise_for_status()
        return response.json()

    def _post(self, path: str, payload: dict) -> dict:
        if self.dry_run:
            preview = json.dumps(payload, ensure_ascii=False)[:200]
            print(f"    [DRY-RUN] POST {path}")
            print(f"    payload: {preview}")
            return {"iid": 0, "title": payload.get("title", ""), "web_url": "dry-run", "labels": []}

        assert self.credentials is not None
        response = requests.post(
            f"{self.credentials.api_base}{path}",
            headers=self.credentials.headers,
            json=payload,
            timeout=self.config.timeout_seconds,
        )
        response.raise_for_status()
        time.sleep(self.config.request_delay_seconds)
        return response.json()

    # --- Milestones ---

    def resolve_milestone_id(self, title: str) -> Optional[int]:
        if self.dry_run:
            print(f"    [DRY-RUN] usaria milestone '{title}'")
            return None

        if title in self._milestone_cache:
            return self._milestone_cache[title]

        data = self._get("/milestones", {"title": title, "per_page": 5})
        matches = [m for m in data if m["title"].strip().lower() == title.strip().lower()]

        if matches:
            mid = matches[0]["id"]
        elif self.config.create_missing_milestone:
            print(f"  ⚠  Milestone '{title}' não existe — criando.")
            mid = self._post("/milestones", {"title": title}).get("id")
        else:
            print(f"  ⚠  Milestone '{title}' não existe e create_missing_milestone=false — issue ficará sem milestone.")
            mid = None

        self._milestone_cache[title] = mid
        return mid

    # --- Labels ---

    def existing_labels(self) -> set[str]:
        """Labels do projeto, buscadas uma única vez e mantidas em cache.

        Paginado: um projeto com muitas labels não cabe em uma página só.
        """
        if self._known_labels is not None:
            return self._known_labels

        if self.dry_run:
            self._known_labels = set()
            return self._known_labels

        names: set[str] = set()
        page = 1
        while True:
            batch = self._get("/labels", {"per_page": 100, "page": page})
            if not batch:
                break
            names.update(lb["name"] for lb in batch)
            if len(batch) < 100:
                break
            page += 1

        self._known_labels = names
        return names

    def ensure_labels(self, names: list[str]) -> None:
        """Cria no GitLab qualquer label da lista que ainda não exista."""
        if self.dry_run:
            print(f"    [DRY-RUN] labels: {', '.join(names)}")
            return

        existing = self.existing_labels()
        for name in names:
            if name in existing:
                continue
            color = self.config.label_color(name)
            print(f"  + criando label '{name}' ({color})")
            try:
                self._post("/labels", {"name": name, "color": color})
            except requests.HTTPError as exc:
                # 409 = criada em paralelo por outra chamada; não é erro real.
                if exc.response is None or exc.response.status_code != 409:
                    raise
            existing.add(name)

    def create_label(self, label: dict[str, str]) -> str:
        """Cria uma label a partir de uma entrada do catálogo. Devolve o status."""
        if self.dry_run:
            print(f"  [DRY-RUN] criaria: {label['name']} ({label.get('color')})")
            return "dry-run"

        assert self.credentials is not None
        response = requests.post(
            f"{self.credentials.api_base}/labels",
            headers=self.credentials.headers,
            json=label,
            timeout=self.config.timeout_seconds,
        )
        if response.status_code == 409:
            print(f"  ~ já existe: {label['name']}")
            return "exists"

        response.raise_for_status()
        time.sleep(self.config.request_delay_seconds)
        print(f"  + criada: {label['name']}")
        return "created"

    # --- Issues ---

    def create_issue(self, payload: dict) -> dict:
        return self._post("/issues", payload)
