"""Executa CT-RNF03-P/N uma unica vez sobre um conjunto cego.

O instrumento carrega o artefato de modelo ja existente, nao treina nem ajusta
qualquer parametro e nao procura um limiar que favoreca o resultado.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import subprocess
import unicodedata
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

from sklearn.metrics import classification_report, confusion_matrix

from pln.classificador import carregar_modelo
from pln.intencao import LIMIAR_PADRAO, aplicar_limiar_em_lote
from pln.metricas import (
    META_ACEITACAO_INDEVIDA,
    META_COBERTURA,
    META_F1_MACRO,
    avaliar_rnf03,
)


def sha256(caminho: Path) -> str:
    resumo = hashlib.sha256()
    with caminho.open("rb") as arquivo:
        for bloco in iter(lambda: arquivo.read(1024 * 1024), b""):
            resumo.update(bloco)
    return resumo.hexdigest()


def normalizar(texto: str) -> str:
    texto = unicodedata.normalize("NFKC", texto).casefold()
    return " ".join(
        "".join(caractere if caractere.isalnum() else " " for caractere in texto).split()
    )


def ler_csv(caminho: Path, *, exige_id: bool) -> list[dict[str, str]]:
    with caminho.open(encoding="utf-8-sig", newline="") as arquivo:
        leitor = csv.DictReader(arquivo)
        obrigatorias = {"texto", "intencao"} | ({"id"} if exige_id else set())
        ausentes = obrigatorias - set(leitor.fieldnames or [])
        if ausentes:
            raise ValueError(f"colunas ausentes em {caminho}: {sorted(ausentes)}")
        return list(leitor)


def commit_atual(raiz: Path) -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=raiz, text=True
    ).strip()


def executar(args: argparse.Namespace) -> int:
    raiz = Path(__file__).resolve().parents[1]
    conjunto = (raiz / args.conjunto).resolve()
    treino = (raiz / args.treino).resolve()
    historico = (raiz / args.historico).resolve()
    modelo_path = (raiz / args.modelo).resolve()
    saida = (raiz / args.saida).resolve()
    saida.mkdir(parents=True, exist_ok=True)

    linhas = ler_csv(conjunto, exige_id=True)
    linhas_historico = ler_csv(historico, exige_id=False)
    if len(linhas) != 200:
        raise ValueError(f"esperados 200 exemplos; encontrados {len(linhas)}")

    ids = [linha["id"] for linha in linhas]
    textos = [linha["texto"] for linha in linhas]
    reais = [linha["intencao"] for linha in linhas]
    if len(set(ids)) != 200:
        raise ValueError("o conjunto cego contem IDs duplicados")
    if len({normalizar(texto) for texto in textos}) != 200:
        raise ValueError("o conjunto cego contem textos duplicados")

    distribuicao = Counter(reais)
    if len(distribuicao) != 10 or set(distribuicao.values()) != {20}:
        raise ValueError(f"distribuicao invalida: {dict(sorted(distribuicao.items()))}")

    historico_normalizado = {normalizar(linha["texto"]) for linha in linhas_historico}
    sobrepostos = sorted({normalizar(texto) for texto in textos} & historico_normalizado)
    if sobrepostos:
        raise ValueError(
            f"{len(sobrepostos)} exemplos do conjunto cego coincidem com o histórico"
        )

    iniciado = datetime.now(UTC)
    modelo = carregar_modelo(modelo_path)
    classes_modelo = [str(valor) for valor in modelo.named_steps["classificador"].classes_]
    if set(classes_modelo) != set(distribuicao):
        raise ValueError(
            "classes do modelo divergem do conjunto: "
            f"modelo={sorted(classes_modelo)}, conjunto={sorted(distribuicao)}"
        )

    # Unica inferencia em lote da campanha. Nada e retreinado ou calibrado aqui.
    probabilidades = modelo.predict_proba(textos)
    indices = probabilidades.argmax(axis=1)
    previstos_crus = [classes_modelo[indice] for indice in indices]
    confiancas = [float(probabilidades[linha, indice]) for linha, indice in enumerate(indices)]
    previstos = aplicar_limiar_em_lote(previstos_crus, confiancas, args.limiar)

    metricas = avaliar_rnf03(reais, previstos_crus, confiancas, args.limiar)
    classes = sorted(distribuicao)
    matriz = confusion_matrix(reais, previstos, labels=classes).tolist()
    relatorio_classes = classification_report(
        reais,
        previstos,
        labels=classes,
        output_dict=True,
        zero_division=0,
    )
    finalizado = datetime.now(UTC)

    registros: list[dict[str, object]] = []
    for indice, linha in enumerate(linhas):
        registros.append(
            {
                "id": linha["id"],
                "texto": linha["texto"],
                "esperado": linha["intencao"],
                "previsto_cru": previstos_crus[indice],
                "confianca": confiancas[indice],
                "rejeitado_pelo_limiar": previstos[indice] != previstos_crus[indice],
                "previsto_final": previstos[indice],
                "correto": previstos[indice] == linha["intencao"],
            }
        )

    resumo = {
        "casos": ["CT-RNF03-P", "CT-RNF03-N"],
        "commit": commit_atual(raiz),
        "iniciado_em_utc": iniciado.isoformat(),
        "finalizado_em_utc": finalizado.isoformat(),
        "conjunto": conjunto.name,
        "conjunto_sha256": sha256(conjunto),
        "modelo": modelo_path.name,
        "modelo_sha256": sha256(modelo_path),
        "treino": treino.name,
        "treino_sha256": sha256(treino),
        "historico_de_desenvolvimento": historico.name,
        "historico_sha256": sha256(historico),
        "semente_documentada": 42,
        "limiar_congelado": args.limiar,
        "exemplos": len(linhas),
        "conhecidos": metricas.conhecidos,
        "fora_do_catalogo": metricas.fora_do_catalogo,
        "sobreposicoes_exatas_normalizadas_com_historico": len(sobrepostos),
        "f1_macro": metricas.f1_macro,
        "meta_f1_macro": META_F1_MACRO,
        "cobertura": metricas.cobertura,
        "meta_cobertura": META_COBERTURA,
        "aceitacao_indevida": metricas.aceitacao_indevida,
        "meta_aceitacao_indevida": META_ACEITACAO_INDEVIDA,
        "acertos": sum(bool(registro["correto"]) for registro in registros),
        "rejeitados_pelo_limiar": sum(
            bool(registro["rejeitado_pelo_limiar"]) for registro in registros
        ),
        "resultado": "Aprovado" if metricas.aprovado else "Reprovado",
    }

    with (saida / "previsoes.csv").open("w", encoding="utf-8", newline="") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=list(registros[0]))
        escritor.writeheader()
        escritor.writerows(registros)

    with (saida / "matriz_confusao.csv").open(
        "w", encoding="utf-8", newline=""
    ) as arquivo:
        escritor = csv.writer(arquivo)
        escritor.writerow(["real\\prevista", *classes])
        for classe, valores in zip(classes, matriz, strict=True):
            escritor.writerow([classe, *valores])

    (saida / "resultado.json").write_text(
        json.dumps(
            {
                "resumo": resumo,
                "distribuicao": dict(sorted(distribuicao.items())),
                "metricas_por_classe": relatorio_classes,
                "classes_matriz": classes,
                "matriz_confusao": matriz,
                "registros": registros,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    criterio_f1 = "atende" if metricas.f1_macro >= META_F1_MACRO else "nao atende"
    criterio_cobertura = "atende" if metricas.cobertura >= META_COBERTURA else "nao atende"
    criterio_aceitacao = (
        "atende" if metricas.aceitacao_indevida <= META_ACEITACAO_INDEVIDA else "nao atende"
    )
    linhas_relatorio = [
        "# Execucao do RNF03",
        "",
        f"- Estado: **{resumo['resultado']}**",
        f"- Conjunto cego: 200 exemplos, 20 por classe, SHA-256 `{resumo['conjunto_sha256']}`",
        f"- Modelo: `{resumo['modelo']}`, SHA-256 `{resumo['modelo_sha256']}`",
        f"- Limiar congelado: **{args.limiar:.2f}**",
        f"- F1-macro: **{metricas.f1_macro:.4f}** (meta >= {META_F1_MACRO:.2f}; {criterio_f1})",
        f"- Cobertura: **{metricas.cobertura:.1%}** (meta >= {META_COBERTURA:.0%}; {criterio_cobertura})",
        f"- Aceitacao indevida: **{metricas.aceitacao_indevida:.1%}** (meta <= {META_ACEITACAO_INDEVIDA:.0%}; {criterio_aceitacao})",
        f"- Acertos: {resumo['acertos']}/200",
        f"- Sobreposicoes exatas normalizadas com o historico: {len(sobrepostos)}",
        "",
        "A inferencia foi feita uma unica vez com o artefato ja existente. O conjunto cego",
        "nao foi usado para treinar, ajustar o modelo ou escolher o limiar desta execucao.",
        "A verificacao automatica de isolamento cobre coincidencia exata normalizada; a",
        "declaracao formal do custodiante continua sendo evidencia humana separada.",
    ]
    (saida / "relatorio.md").write_text(
        "\n".join(linhas_relatorio) + "\n", encoding="utf-8"
    )

    print(json.dumps(resumo, ensure_ascii=False, indent=2))
    return 0 if metricas.aprovado else 1


def parser() -> argparse.ArgumentParser:
    analisador = argparse.ArgumentParser(description="Executa o conjunto cego do RNF03.")
    analisador.add_argument("--conjunto", type=Path, required=True)
    analisador.add_argument(
        "--treino", type=Path, default=Path("src/pln/dados/intencoes_exemplos.csv")
    )
    analisador.add_argument(
        "--historico", type=Path, default=Path("src/pln/dados/intencoes_pool.csv")
    )
    analisador.add_argument(
        "--modelo", type=Path, default=Path("resultados/classificador.joblib")
    )
    analisador.add_argument("--limiar", type=float, default=LIMIAR_PADRAO)
    analisador.add_argument("--saida", type=Path, required=True)
    return analisador


if __name__ == "__main__":
    raise SystemExit(executar(parser().parse_args()))
