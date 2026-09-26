"""Prepara e consolida a campanha do RNF05 usando apenas a biblioteca padrão."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import subprocess
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path


INTENCOES = (
    "consultar_documentos_normativos",
    "consultar_projeto_sintetico",
    "orientar_mapa_beneficios",
    "orientar_tap",
    "orientar_entregas_cronograma",
    "orientar_avanco_mensal",
    "orientar_riscos_problemas",
    "analisar_completude_coerencia",
    "gerar_alertas_pendencias",
    "fora_do_catalogo",
)


def commit_atual(raiz: Path) -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=raiz, text=True
    ).strip()


def fonte(indice: int, posicao: int) -> dict[str, object]:
    return {
        "posicao": posicao,
        "projeto_id": f"SYN-{(indice % 8) + 1:02d}",
        "tipo_documento": "cronograma",
        "arquivo_origem": f"02_Cronograma_RNF05_{indice:02d}.xlsx",
        "secao": "Marcos",
        "score": round(0.95 - posicao / 100, 2),
        "chunk_id": f"rnf05-{indice:02d}-{posicao}",
        "trecho": f"Trecho controlado {posicao} do caso RNF05-P{indice:02d}.",
    }


def criar_massa(commit: str) -> list[dict[str, object]]:
    namespace = uuid.uuid5(uuid.NAMESPACE_URL, f"az1:rnf05:{commit}")
    massa: list[dict[str, object]] = []
    for indice in range(1, 21):
        caso_id = f"RNF05-P{indice:02d}"
        qtd_fontes = 2 if indice % 5 == 0 else (1 if indice % 3 == 0 else 0)
        fontes = [fonte(indice, p) for p in range(1, qtd_fontes + 1)]
        citacoes = " " + "".join(f"[{p}]" for p in range(1, qtd_fontes + 1)) if fontes else ""
        massa.append(
            {
                "id": caso_id,
                "tipo": "positivo",
                "mensagem": f"[{caso_id}] Consulte o projeto sintético.",
                "conversation_id": str(uuid.uuid5(namespace, caso_id)),
                "intencao_esperada": INTENCOES[(indice - 1) % len(INTENCOES)],
                "resposta_bruta": f"Resposta controlada do caso {caso_id}.{citacoes}",
                "resposta_esperada": f"Resposta controlada do caso {caso_id}.",
                "fontes_esperadas": fontes,
                "token": "valido",
                "status_esperado": 200,
            }
        )

    negativos = (
        ("RNF05-N01", "entrada_invalida", "   ", "valido", 422, "empty_message"),
        (
            "RNF05-N02",
            "credencial_invalida",
            "Consulta com credencial inválida.",
            "invalido",
            401,
            "unauthorized",
        ),
        (
            "RNF05-N03",
            "falha_servico",
            "Falha controlada do serviço externo.",
            "valido",
            503,
            "service_unavailable",
        ),
    )
    for caso_id, categoria, mensagem, token, status, erro in negativos:
        massa.append(
            {
                "id": caso_id,
                "tipo": "negativo",
                "categoria": categoria,
                "mensagem": mensagem,
                "conversation_id": str(uuid.uuid5(namespace, caso_id)),
                "intencao_esperada": (
                    "consultar_projeto_sintetico" if categoria == "falha_servico" else None
                ),
                "resposta_bruta": None,
                "resposta_esperada": None,
                "fontes_esperadas": [],
                "token": token,
                "status_esperado": status,
                "erro_esperado": erro,
            }
        )
    return massa


def preparar(args: argparse.Namespace) -> int:
    raiz = Path(__file__).resolve().parents[1]
    saida = (raiz / args.saida).resolve()
    saida.mkdir(parents=True, exist_ok=True)
    commit = args.commit or commit_atual(raiz)
    massa = criar_massa(commit)
    (saida / "massa.json").write_text(
        json.dumps(massa, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (saida / "inicio.json").write_text(
        json.dumps(
            {"commit": commit, "inicio_utc": datetime.now(UTC).isoformat()},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"massa={len(massa)} positivos=20 negativos=3 saida={saida}")
    return 0


def ler_jsonl(caminho: Path) -> list[dict[str, object]]:
    if not caminho.exists():
        return []
    return [json.loads(linha) for linha in caminho.read_text(encoding="utf-8").splitlines() if linha]


def esquema(resultado: dict[str, object]) -> list[str]:
    corpo = resultado.get("body")
    return sorted(corpo) if isinstance(corpo, dict) else []


def consolidar(args: argparse.Namespace) -> int:
    raiz = Path(__file__).resolve().parents[1]
    saida = (raiz / args.saida).resolve()
    massa = json.loads((saida / "massa.json").read_text(encoding="utf-8"))
    react = json.loads((saida / "resultados_react.json").read_text(encoding="utf-8"))
    python = json.loads((saida / "resultados_python.json").read_text(encoding="utf-8"))
    requisicoes = ler_jsonl(saida / "requisicoes_servidor.jsonl")
    classificacoes = ler_jsonl(saida / "classificacoes_servidor.jsonl")
    por_id_react = {r["id"]: r for r in react["resultados"]}
    por_id_python = {r["id"]: r for r in python["resultados"]}

    linhas: list[dict[str, object]] = []
    equivalentes = 0
    for caso in massa:
        rid = caso["id"]
        r = por_id_react.get(rid, {})
        p = por_id_python.get(rid, {})
        logs = [x for x in requisicoes if x.get("id") == rid]
        classes = [x for x in classificacoes if x.get("id") == rid]
        esperadas_classes = 0 if caso["intencao_esperada"] is None else 2
        verificacoes = {
            "dois_resultados": bool(r) and bool(p),
            "metodo_rota": (
                r.get("method") == p.get("method") == "POST"
                and r.get("route") == p.get("route") == "/api/v1/chat"
            ),
            "status": r.get("status") == p.get("status") == caso["status_esperado"],
            "esquema": esquema(r) == esquema(p),
            "intencao": (
                len(classes) == esperadas_classes
                and all(c.get("intencao") == caso["intencao_esperada"] for c in classes)
            ),
            "fontes": (
                r.get("body", {}).get("fontes", [])
                == p.get("body", {}).get("fontes", [])
                == caso["fontes_esperadas"]
            )
            if caso["tipo"] == "positivo"
            else True,
            "resultado_negocio": (
                r.get("body", {}).get("reply")
                == p.get("body", {}).get("reply")
                == caso["resposta_esperada"]
            )
            if caso["tipo"] == "positivo"
            else True,
            "categoria_erro": (
                r.get("body", {}).get("error")
                == p.get("body", {}).get("error")
                == caso.get("erro_esperado")
            )
            if caso["tipo"] == "negativo"
            else True,
            "mesma_instancia": (
                len(logs) == 2
                and len({x.get("instance_id") for x in logs}) == 1
                and {x.get("cliente") for x in logs} == {"react", "python"}
            ),
        }
        falhas = [nome for nome, passou in verificacoes.items() if not passou]
        passou = not falhas
        equivalentes += int(passou)
        linhas.append(
            {
                "id": rid,
                "tipo": caso["tipo"],
                "status_react": r.get("status"),
                "status_python": p.get("status"),
                "intencao": caso["intencao_esperada"] or "n/a",
                "equivalente": "sim" if passou else "não",
                "divergencias": "; ".join(falhas),
                "verificacoes": json.dumps(verificacoes, ensure_ascii=False),
            }
        )

    with (saida / "comparacao.csv").open("w", newline="", encoding="utf-8") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=list(linhas[0]))
        escritor.writeheader()
        escritor.writerows(linhas)

    python_cliente = (raiz / "scripts" / "rnf05_cliente_python.py").read_text(encoding="utf-8")
    react_cliente = (raiz / "src" / "frontend" / "src" / "lib" / "api.js").read_text(
        encoding="utf-8"
    )
    proibidos = ("pln.", "rag.", "services.agente", "classificar", "recuperar_fontes")
    sem_duplicacao = not any(p in python_cliente for p in proibidos) and "fetch(" in react_cliente
    aprovado = equivalentes == len(massa) and sem_duplicacao
    inicio = json.loads((saida / "inicio.json").read_text(encoding="utf-8"))
    resultado = {
        "requisito": "RNF05",
        "status": "Aprovado" if aprovado else "Reprovado",
        "commit": inicio["commit"],
        "inicio_utc": inicio["inicio_utc"],
        "fim_utc": datetime.now(UTC).isoformat(),
        "pares_total": len(massa),
        "pares_positivos": 20,
        "pares_negativos": 3,
        "pares_equivalentes": equivalentes,
        "taxa_equivalencia": equivalentes / len(massa),
        "sem_duplicacao_regras_negocio": sem_duplicacao,
        "clientes": {
            "react": react["ambiente"],
            "python": python["ambiente"],
        },
        "contrato_chat_sha256": python["contrato_chat_sha256"],
        "instance_ids": sorted({str(x.get("instance_id")) for x in requisicoes}),
    }
    (saida / "resultado.json").write_text(
        json.dumps(resultado, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    divergentes = [linha for linha in linhas if linha["equivalente"] == "não"]
    relatorio = f"""# Execução do RNF05 — interoperabilidade entre aplicações clientes

- Status: **{resultado['status']}**
- Commit: `{resultado['commit']}`
- Pares equivalentes: **{equivalentes}/{len(massa)} ({equivalentes / len(massa):.2%})**
- Positivos: **{sum(l['tipo'] == 'positivo' and l['equivalente'] == 'sim' for l in linhas)}/20**
- Negativos: **{sum(l['tipo'] == 'negativo' and l['equivalente'] == 'sim' for l in linhas)}/3**
- Regras de negócio duplicadas nos clientes: **{'não' if sem_duplicacao else 'sim'}**

## Clientes exercitados

1. Adaptador real da interface React: `sendMessage` de `src/frontend/src/lib/api.js`, executado pelo Vitest/Node.
2. Cliente Python independente: `scripts/rnf05_cliente_python.py`, usando HTTPX.

Os dois consumiram a mesma instância controlada da API. Classificação,
recuperação de fontes, tratamento de erros e montagem da resposta permaneceram
no servidor; os clientes limitaram-se ao transporte HTTP e ao tratamento do
contrato.

## Massa e comparação

Foram executadas 20 solicitações válidas e três negativas: entrada vazia,
credencial inválida e falha controlada do serviço. A comparação considerou
método, rota, status, esquema, intenção processada no servidor, fontes, dados
estruturados e categoria de erro.

## Divergências

"""
    if divergentes:
        relatorio += "\n".join(
            f"- `{l['id']}`: {l['divergencias']}" for l in divergentes
        )
    else:
        relatorio += "- Nenhuma."
    relatorio += "\n"
    (saida / "relatorio.md").write_text(relatorio, encoding="utf-8")
    if divergentes:
        (saida / "defeito.md").write_text(
            "# Divergências do RNF05\n\n"
            + "\n".join(f"- `{l['id']}`: {l['divergencias']}" for l in divergentes)
            + "\n",
            encoding="utf-8",
        )
    print(json.dumps(resultado, ensure_ascii=False, indent=2))
    return 0 if aprovado else 1


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="acao", required=True)
    p = sub.add_parser("preparar")
    p.add_argument("--saida", required=True)
    p.add_argument("--commit")
    c = sub.add_parser("consolidar")
    c.add_argument("--saida", required=True)
    args = parser.parse_args()
    return preparar(args) if args.acao == "preparar" else consolidar(args)


if __name__ == "__main__":
    sys.exit(main())
