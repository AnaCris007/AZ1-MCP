# Bancada de medição de desempenho do pipeline de PLN.
#
# Mede o que o RNF01 e o RNF10 cobram e que o repositório não media: latência
# de inferência em percentis, tempo de treino, e pico de memória do treino em
# função do tamanho do dataset. Sem isto, "ficou mais rápido" e "coube na
# memória" são opinião.
#
# A saída vai para `resultados/bancada.md`, no mesmo regime dos demais
# relatórios: arquivo gerado, nunca editado à mão.
#
# ESCOLHA DE INSTRUMENTO
# ----------------------
# A memória é medida com `tracemalloc`, da biblioteca padrão, e não com o RSS
# do processo. O motivo é que `psutil` não é dependência do projeto e as cinco
# bibliotecas do pipeline estão fixadas em versão exata para manter as métricas
# reproduzíveis — acrescentar dependência aqui custaria mais do que entrega.
#
# A consequência precisa ser dita: `tracemalloc` contabiliza alocações feitas
# pelo Python, e não as feitas dentro do NumPy e do scikit-learn em C. O número
# é um piso do consumo real, adequado para comparar RAZÕES entre tamanhos de
# dataset, que é exatamente a forma como o RNF10 está redigido. Ele não serve
# para dimensionar o contêiner.

from __future__ import annotations

import argparse
import platform
import statistics
import sys
import time
import tracemalloc
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from pln.caminhos import DATASET_PADRAO, garantir_dir_de_resultados
from pln.classificador import (
    SEMENTE,
    carregar_dataset,
    construir_classificador,
    prever_intencao,
)

# Percentis exigidos pelos requisitos: o RNF01 fala em 80% das consultas, o
# RNF10 em p95. O p50 entra como referência de comportamento típico.
PERCENTIS = (50, 80, 95)

# Fatores de escala do RNF10: 1x, 2x, 5x e 10x.
FATORES_DE_ESCALA = (1, 2, 5, 10)

# O RNF10 limita a razão de pico de memória de treino entre `10x` e `1x`.
LIMITE_RAZAO_PICO_TREINO = 8.0

AQUECIMENTO_PADRAO = 5
REPETICOES_PADRAO = 200


@dataclass(frozen=True)
class ResumoDeLatencia:
    amostras: int
    media_ms: float
    percentis_ms: dict[int, float]


@dataclass(frozen=True)
class ResumoDeTreino:
    exemplos: int
    segundos: float
    pico_mib: float


# Percentil pelo método do posto mais próximo. `statistics.quantiles` interpola
# entre observações e devolveria um valor que nenhuma execução mediu; para
# comparar contra um limite contratual, o valor observado é o defensável.
def percentil(amostras_ordenadas: list[float], q: int) -> float:
    if not amostras_ordenadas:
        raise ValueError("sem amostras para calcular percentil")
    posto = max(1, -(-q * len(amostras_ordenadas) // 100))  # teto, sem float
    return amostras_ordenadas[posto - 1]


# As primeiras chamadas pagam a carga preguiçosa do spaCy, do NLTK e dos caches
# de `preprocessamento`, e não representam o regime servido. O planejamento do
# RNF01 já previa descartar a requisição de aquecimento; aqui vale o mesmo.
def medir_latencia(funcao, entradas: list[str], repeticoes: int, aquecimento: int) -> ResumoDeLatencia:
    if not entradas:
        raise ValueError("sem entradas para medir")

    for i in range(aquecimento):
        funcao(entradas[i % len(entradas)])

    duracoes: list[float] = []
    for i in range(repeticoes):
        entrada = entradas[i % len(entradas)]
        inicio = time.perf_counter()
        funcao(entrada)
        duracoes.append((time.perf_counter() - inicio) * 1000.0)

    duracoes.sort()
    return ResumoDeLatencia(
        amostras=len(duracoes),
        media_ms=statistics.fmean(duracoes),
        percentis_ms={q: percentil(duracoes, q) for q in PERCENTIS},
    )


def medir_treino(textos: list[str], rotulos: list[str]) -> ResumoDeTreino:
    modelo = construir_classificador()

    tracemalloc.start()
    tracemalloc.reset_peak()
    inicio = time.perf_counter()
    modelo.fit(textos, rotulos)
    segundos = time.perf_counter() - inicio
    _, pico = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    return ResumoDeTreino(exemplos=len(textos), segundos=segundos, pico_mib=pico / (1024 * 1024))


# Replicação estratificada para as curvas de escala do RNF10.
#
# ATENÇÃO: serve só para medir tempo e memória. Usar um dataset replicado para
# medir F1 produz vazamento — o mesmo exemplo cai em dobras de treino e de
# teste — e o número sai inflado. A separação é responsabilidade de quem chama.
def replicar(textos: list[str], rotulos: list[str], fator: int) -> tuple[list[str], list[str]]:
    if fator < 1:
        raise ValueError("fator de replicação precisa ser >= 1")
    if fator == 1:
        return list(textos), list(rotulos)

    por_classe: dict[str, list[str]] = defaultdict(list)
    for texto, rotulo in zip(textos, rotulos, strict=True):
        por_classe[rotulo].append(texto)

    saida_textos: list[str] = []
    saida_rotulos: list[str] = []
    for rotulo in sorted(por_classe):
        exemplos = por_classe[rotulo]
        saida_textos.extend(exemplos * fator)
        saida_rotulos.extend([rotulo] * len(exemplos) * fator)
    return saida_textos, saida_rotulos


def _cabecalho() -> list[str]:
    return [
        "# Bancada de desempenho do pipeline de PLN",
        "",
        "Arquivo gerado por `python -m pln.bancada`. Não editar à mão.",
        "",
        f"- Python: {platform.python_version()} ({platform.machine()})",
        f"- Sistema: {platform.system()} {platform.release()}",
        f"- Semente: {SEMENTE}",
        "",
    ]


def _secao_latencia(modelo, textos: list[str], repeticoes: int, aquecimento: int) -> list[str]:
    from pln.classificador import CONFIG_PRE_PADRAO
    from pln.preprocessamento import preprocessar

    ponta_a_ponta = medir_latencia(lambda t: prever_intencao(modelo, t), textos, repeticoes, aquecimento)
    so_pre = medir_latencia(lambda t: preprocessar(t, CONFIG_PRE_PADRAO), textos, repeticoes, aquecimento)

    mediana = ponta_a_ponta.percentis_ms[50]
    fatia = (so_pre.percentis_ms[50] / mediana * 100) if mediana else 0.0

    return [
        "## Latência de inferência",
        "",
        "Uma consulta por vez, processo já aquecido. O RNF01 mede a consulta completa,",
        "que inclui transcrição e geração de resposta; aqui está apenas a parcela do",
        "classificador, que é a que este pipeline controla.",
        "",
        "| Trecho medido | Amostras | Média | p50 | p80 | p95 |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
        f"| `prever_intencao` (ponta a ponta) | {ponta_a_ponta.amostras} "
        f"| {ponta_a_ponta.media_ms:.3f} ms | {ponta_a_ponta.percentis_ms[50]:.3f} ms "
        f"| {ponta_a_ponta.percentis_ms[80]:.3f} ms | {ponta_a_ponta.percentis_ms[95]:.3f} ms |",
        f"| `preprocessar` (isolado) | {so_pre.amostras} "
        f"| {so_pre.media_ms:.3f} ms | {so_pre.percentis_ms[50]:.3f} ms "
        f"| {so_pre.percentis_ms[80]:.3f} ms | {so_pre.percentis_ms[95]:.3f} ms |",
        "",
        f"O pré-processamento responde por **{fatia:.0f}%** da mediana ponta a ponta.",
        "É onde uma otimização de latência tem efeito; o `predict_proba` sobre uma",
        "matriz esparsa de uma linha é a parcela pequena.",
        "",
    ]


def _secao_escala(textos: list[str], rotulos: list[str], fatores: tuple[int, ...]) -> list[str]:
    medidas = {f: medir_treino(*replicar(textos, rotulos, f)) for f in fatores}
    base = medidas[fatores[0]]

    linhas = [
        "## Treino: tempo e pico de memória por tamanho de dataset",
        "",
        "Datasets `Nx` são replicação estratificada do dataset real, e servem só para",
        "medir custo. **Não** medem qualidade: o mesmo exemplo apareceria em dobras de",
        "treino e de teste, e o F1 sairia inflado.",
        "",
        "Ressalva de leitura: a replicação não cria vocabulário novo, então o",
        "vocabulário fica constante enquanto o número de linhas cresce. O consumo",
        "medido é um **piso** do que um dataset real de mesmo tamanho custaria. A",
        "medição definitiva do RNF10 precisa do dataset ampliado, não deste.",
        "",
        "| Fator | Exemplos | Tempo de treino | Razão de tempo | Pico de memória | Razão de pico |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for f in fatores:
        m = medidas[f]
        razao_tempo = m.segundos / base.segundos if base.segundos else float("nan")
        razao_pico = m.pico_mib / base.pico_mib if base.pico_mib else float("nan")
        linhas.append(
            f"| {f}x | {m.exemplos} | {m.segundos:.3f} s | {razao_tempo:.2f}x "
            f"| {m.pico_mib:.2f} MiB | {razao_pico:.2f}x |"
        )

    maior = medidas[fatores[-1]]
    razao = maior.pico_mib / base.pico_mib if base.pico_mib else float("nan")
    veredito = "dentro" if razao <= LIMITE_RAZAO_PICO_TREINO else "acima"
    linhas += [
        "",
        f"O RNF10 limita a razão de pico de treino entre `{fatores[-1]}x` e `1x` a "
        f"{LIMITE_RAZAO_PICO_TREINO:.0f}. Medido: **{razao:.2f}x** — {veredito} do limite.",
        "",
    ]
    return linhas


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Mede latência, tempo de treino e pico de memória do pipeline de PLN."
    )
    parser.add_argument("--dataset", type=Path, default=DATASET_PADRAO)
    parser.add_argument("--repeticoes", type=int, default=REPETICOES_PADRAO,
                        help="medições de latência por trecho")
    parser.add_argument("--aquecimento", type=int, default=AQUECIMENTO_PADRAO,
                        help="chamadas descartadas antes de medir")
    parser.add_argument("--sem-escala", action="store_true",
                        help="pula a curva de escala, que é a parte demorada")
    parser.add_argument("--salvar", type=Path, default=None,
                        help="destino do relatório (padrão: resultados/bancada.md)")
    args = parser.parse_args(argv)

    textos, rotulos = carregar_dataset(args.dataset)
    print(f"Dataset: {args.dataset}  ({len(textos)} exemplos, {len(set(rotulos))} classes)")

    print("Treinando o modelo de referência...")
    modelo = construir_classificador()
    modelo.fit(textos, rotulos)

    print(f"Medindo latência ({args.repeticoes} repetições, {args.aquecimento} de aquecimento)...")
    linhas = _cabecalho() + _secao_latencia(modelo, textos, args.repeticoes, args.aquecimento)

    if args.sem_escala:
        linhas += ["## Treino: tempo e pico de memória", "", "Não medido (`--sem-escala`).", ""]
    else:
        rotulo_fatores = ", ".join(f"{f}x" for f in FATORES_DE_ESCALA)
        print(f"Medindo escala de treino em {rotulo_fatores}...")
        linhas += _secao_escala(textos, rotulos, FATORES_DE_ESCALA)

    destino = args.salvar or (garantir_dir_de_resultados() / "bancada.md")
    destino.write_text("\n".join(linhas) + "\n", encoding="utf-8")

    print()
    print("\n".join(linhas[8:]))
    print(f"Relatório salvo em {destino}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
