"""Extrai as fichas existentes e consolida a campanha sem inferir aprovação.

Uso: python3 scripts/consolidar_testes_funcionais.py.
Mantém 62 IDs estáveis, incluindo seis fora do recorte. Gera catálogo detalhado,
matriz CSV e relatório Markdown; não altera critérios para acomodar o código.
"""
import csv
import hashlib
import json
import re
import subprocess
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/evidencias/testes-funcionais"
DOCUMENT = ROOT / "docs/Projeto.md"


def guardar_manifesto(report):
    """Atualiza hashes após consolidar, preservando a versão da execução HTTP."""
    paths = [DOCUMENT, ROOT / "scripts/executar_testes_funcionais.py",
             ROOT / "scripts/consolidar_testes_funcionais.py",
             ROOT / "src/frontend/src/pages/AgentPage.test.jsx",
             ROOT / "src/frontend/tests/functional.html",
             ROOT / "src/frontend/tests/functional.jsx", ROOT / "pyproject.toml",
             ROOT / "requirements.txt", ROOT / "src/frontend/package-lock.json"]
    paths.extend(path for path in OUT.iterdir() if path.is_file() and path.name != "manifesto.json")
    manifest = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "base_commit": report.get("commit", "não registrado"),
        "consolidation_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "scope": "Campanha acadêmica local; hashes dos arquivos atuais. Atualizar documentação não reexecuta testes nem altera resultados históricos.",
        "functional_run_started_at_utc": report.get("started_at_utc"),
        "functional_run_finished_at_utc": report.get("finished_at_utc"),
        "sha256": {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
                   for path in sorted(set(paths)) if path.exists()},
    }
    (OUT / "manifesto.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    text = DOCUMENT.read_text()
    original = text.split("### 6.2.3 Procedimentos de Teste", 1)[1].split("### 6.2.4", 1)[0]
    complement = text.split("### 6.2.6", 1)[1].split("## 6.3", 1)[0]
    cases = {}
    for match in re.finditer(r"##### (CT-RF\d{2}-\d{2})\n(.*?)(?=\n##### |\Z)", original, re.S):
        fields = dict(re.findall(r"^\| ([^|]+?) \| (.*?) \|$", match[2], re.M))
        cases[match[1]] = fields
    for line in complement.splitlines():
        if line.startswith("| CT-RF"):
            fields = [item.strip() for item in line.strip("|").split("|")]
            cases[fields[0]] = dict(zip(["Requisito e componente", "Propósito", "Procedimento", "Resultado esperado"], fields[1:]))
    assert len(cases) == 62, f"Catálogo incompleto: {len(cases)}"
    report = json.loads((OUT / "funcionais.json").read_text()) if (OUT / "funcionais.json").exists() else {"records": []}
    frontend_records = []
    browser_records = []
    if (OUT / "navegador.json").exists():
        browser = json.loads((OUT / "navegador.json").read_text())
        browser_records.append(browser)
    if (OUT / "frontend.json").exists():
        frontend = json.loads((OUT / "frontend.json").read_text())
        mapping = {
            "apresenta a transcrição no campo de texto sem enviá-la automaticamente": "CT-RF01-03",
            "CT-RF01-19: envia somente a transcrição corrigida após confirmação": "CT-RF01-19",
            "não envia a transcrição quando o usuário descarta": "CT-RF01-19",
            "CT-RF01-15: falha de rede apresenta erro sem resposta fictícia": "CT-RF01-15",
        }
        for file in frontend["testResults"]:
            for assertion in file["assertionResults"]:
                if assertion["title"] in mapping:
                    frontend_records.append({"case": mapping[assertion["title"]], "variant": assertion["title"],
                        "status": "Aprovado" if assertion["status"] == "passed" else "Reprovado",
                        "scope": "componente jsdom; microfone/HTTP controlados"})
    exclusions = {"CT-RF02-10", *(f"CT-RF06-{i:02}" for i in range(1, 6))}
    # A aprovação agregada é restrita a casos com todos os observáveis executados.
    complete = {*(f"CT-RF01-{i:02}" for i in [4, 6, 7, 8, 9, 10, 11, 13, 14, 16, 17, 18])}
    rows = []
    detailed = ["# Catálogo operacional da campanha funcional", "", "Fichas herdadas de Projeto.md, Seções 6.2.3 e 6.2.6. Pré-condições e massas: Seções 6.1.3 e 6.2.3. Preparar o estado, executar a entrada, comparar todos os observáveis, registrar e restaurar. Estados abaixo são resultados desta campanha, não a coluna histórica de prontidão.", ""]
    for case, fields in sorted(cases.items()):
        executed = [r for r in report["records"] + frontend_records + browser_records if r["case"] == case]
        rf = case[3:7]
        if case in exclusions:
            status, reason = "Fora do recorte", "D04/D07; preservar caso histórico; escrita futura não entra no aceite do MVP."
        elif any(r["status"] == "Reprovado" for r in executed):
            status, reason = "Reprovado", "Observável obrigatório divergente; consultar funcionais.json e registro de defeitos."
        elif executed and case in complete:
            status, reason = "Aprovado controlado", "Todos os observáveis deste caso passaram no recorte controlado; não comprova SSO/modelo externo real."
        elif executed:
            status, reason = "Parcial", "Variantes executadas não atendem todas as pré-condições/observáveis da ficha; não contabilizar aprovação integral."
        else:
            status = "Bloqueado"
            if rf == "RF01":
                reason = "Falta execução navegador/microfone real ou gravações faladas nos quatro formatos; comparação comum de intenção pendente."
            elif rf == "RF02" and case[-2:] in {"01", "02", "03", "14"}:
                reason = "Base cega independente e entidades de referência não disponibilizadas/congeladas; não usar base saturada para aceitar requisito."
            elif rf == "RF02" or rf == "RF03":
                reason = "Massa E/F e recuperação vetorial real com versões, referências e gabaritos dedicados não provisionadas nesta campanha."
            elif rf == "RF04":
                reason = "Fluxo integrado por campo e massa G não disponíveis; campo_artefato sem massa nesta campanha."
            elif rf == "RF05":
                reason = "Agendador/canal de entrega e configuração de elegibilidade não disponibilizados; assinantes/webhooks não comprovam notificação automática."
            else:
                reason = "Fonte dedicada para comparação antes/depois e diálogo explicativo do MVP ainda precisam ser exercitados conjuntamente."
        priority = "Alta" if rf in {"RF01", "RF02", "RF03", "RF05"} else "Média"
        evidence = "frontend.json" if any(r["case"] == case for r in frontend_records) else "funcionais.json" if executed else ""
        if any(r["case"] == case for r in browser_records):
            evidence += "; navegador.json; CT-RF01-15.png"
        rows.append({"id": case, "rf": rf, "prioridade": priority, "status": status, "motivo": reason, "variantes_executadas": len(executed), "evidencia": evidence, "proxima_etapa": "Reteste após correção" if status == "Reprovado" else "Sprint 4/5: cumprir pré-condições e executar ficha" if status in {"Bloqueado", "Parcial"} else "Revisão humana"})
        detailed += [f"## {case}", "", f"Estado: **{status}**. {reason}", ""]
        detailed += [f"- **{key}:** {value}" for key, value in fields.items() if key not in {"Campo", "---"}]
        detailed += [""]
    with (OUT / "matriz.csv").open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    (OUT / "catalogo.md").write_text("\n".join(detailed) + "\n")
    (OUT / "catalogo.json").write_text(json.dumps(cases, ensure_ascii=False, indent=2) + "\n")
    table = ["| Caso | Prioridade | Resultado | Variantes | Motivo / dependência |", "|---|---|---|---:|---|"]
    table += [f"| {row['id']} | {row['prioridade']} | {row['status']} | {row['variantes_executadas']} | {row['motivo']} |" for row in rows]
    (OUT / "matriz.md").write_text("\n".join(table) + "\n")
    marker_start, marker_end = "<!-- MATRIZ-FUNCIONAL-INICIO -->", "<!-- MATRIZ-FUNCIONAL-FIM -->"
    if marker_start in text and marker_end in text:
        counts = Counter(row["status"] for row in rows)
        labels = {"Parcial": "parciais", "Bloqueado": "bloqueados", "Aprovado controlado": "aprovados no recorte controlado", "Reprovado": "reprovados", "Fora do recorte": "fora do recorte"}
        summary = "; ".join(f"{value} {labels[key]}" for key, value in counts.items())
        generated = f"\n**Resultado agregado:** {summary}. São 56 IDs aplicáveis e seis históricos fora do recorte. Aprovação controlada não equivale a homologação sistêmica.\n\n" + "\n".join(table) + "\n"
        text = text.split(marker_start)[0] + marker_start + generated + marker_end + text.split(marker_end, 1)[1]
        DOCUMENT.write_text(text)
    results_start, results_end = "<!-- RESULTADOS-FUNCIONAIS-INICIO -->", "<!-- RESULTADOS-FUNCIONAIS-FIM -->"
    if results_start in text and results_end in text and report["records"]:
        variants = Counter(record["status"] for record in report["records"])
        results = [
            "", "| Execução | Resultado desta rodada | Evidência |", "|---|---|---|",
            f"| Variantes funcionais HTTP | {len(report['records'])} variantes; {variants['Aprovado']} passaram nos observáveis técnicos e {variants['Reprovado']} reprovaram. Agregação por caso somente em 6.7.3 | [JSON](evidencias/testes-funcionais/funcionais.json), [log](evidencias/testes-funcionais/funcionais.log) |",
        ]
        backend = (OUT / "backend.log").read_text() if (OUT / "backend.log").exists() else ""
        total = re.search(r"Ran (\d+) tests", backend)
        if total:
            verdict = "aprovados, sem falhas nem testes ignorados" if backend.rstrip().endswith("OK") else "resultado não aprovado; consultar log"
            results.append(f"| Regressão backend | {total[1]} testes: {verdict}; PostgreSQL real exclusivo | [Log final](evidencias/testes-funcionais/backend.log) |")
        if (OUT / "frontend.json").exists():
            frontend = json.loads((OUT / "frontend.json").read_text())
            results.append(f"| Regressão frontend | {frontend['numPassedTests']}/{frontend['numTotalTests']} testes passaram, {frontend['numFailedTests']} falhas; jsdom e dependências controladas | [JSON](evidencias/testes-funcionais/frontend.json), [log](evidencias/testes-funcionais/frontend.log) |")
        results += [
            "| Build API | Imagem dev construída com as dependências do projeto | [Log](evidencias/testes-funcionais/build-api.log) |",
            "| DDL, massa e políticas | Executados no PostgreSQL de testes; índice vetorial ausente, comparação RAG não executada | [DDL](evidencias/testes-funcionais/database-ddl.log), [massa](evidencias/testes-funcionais/database-massa.log), [políticas](evidencias/testes-funcionais/database-permissoes.log) |",
            "| Build frontend | Aprovado; aviso sobre bundle superior a 500 kB | [Log](evidencias/testes-funcionais/frontend-build.log) |",
            "| Lint frontend | Comando terminou com sucesso, mas emitiu oito avisos React; não apresentar como zero avisos | [Log](evidencias/testes-funcionais/frontend-lint.log) |",
            "| Navegador | Envio real com API ausente, pelo harness; erro genérico e nenhum conteúdo fictício; resultado parcial | [Registro](evidencias/testes-funcionais/navegador.json), [captura](evidencias/testes-funcionais/CT-RF01-15.png) |",
            "", "A primeira rodada da regressão teve oito erros de preparação por arquivos não montados. Os mounts foram corrigidos e a suíte inteira foi repetida; o [log inicial](evidencias/testes-funcionais/backend-rodada1.log) foi preservado. A repetição do instrumento funcional também revelou bucket já existente; corrigiu-se a preparação sem alterar os oráculos. Os registros de desenvolvimento `funcionais-rodada1.*` são anteriores à revisão de rastreabilidade: a entrada de projeto ausente estava identificada incorretamente como RF02-08, corrigida para RF02-06 na rodada final. Somente `funcionais.json`/`funcionais.log` finais alimentam a matriz.",
            "", "As duas reprovações finais são CT-RF02-06 (consulta sem projeto e sem esclarecimento prévio) e CT-RF02-07 (busca para pedido fora do domínio). A recuperação foi chamada uma vez em cada cenário; a recusa por falta de evidência não elimina essa divergência. Correção e reteste funcionais permanecem pendentes.", "",
        ]
        text = text.split(results_start)[0] + results_start + "\n".join(results) + results_end + text.split(results_end, 1)[1]
        DOCUMENT.write_text(text)
    guardar_manifesto(report)
    print(json.dumps(Counter(row["status"] for row in rows), ensure_ascii=False))


if __name__ == "__main__":
    main()
