# Separa o corpus em desenvolvimento e teste retido.
#
# Até aqui toda medição do projeto vinha de validação cruzada sobre as mesmas
# 400 frases. Validação cruzada mede bem, mas o mesmo corpus escolheu o
# pré-processamento (11.644 execuções), escolheu os hiperparâmetros e calibrou
# o limiar. Um número medido sobre dados que participaram de todas essas
# escolhas é otimista por construção, e não há como saber por quanto.
#
# ISTO NÃO É O CONJUNTO CEGO DA SEÇÃO 6.3.
# ----------------------------------------
# A Seção 6.3 reserva esse nome para 200 frases NOVAS, custodiadas por quem não
# participa do ajuste. O que este módulo produz é um teste retido: honesto
# quanto à generalização, e insuficiente como evidência final. A distinção
# precisa sobreviver a quem ler só o relatório.
#
# POR QUE HASH, E NÃO EMBARALHAR COM SEMENTE
# ------------------------------------------
# Um `shuffle` com semente fixa é reprodutível, mas não é ESTÁVEL SOB
# CRESCIMENTO: acrescentar cem frases ao pool recalcula o sorteio inteiro, e
# exemplos que estavam no teste migram para o desenvolvimento. O modelo da
# rodada anterior foi ajustado sobre eles. O conjunto retido vaza sem que
# ninguém tenha feito nada errado.
#
# Atribuir a partição por hash do próprio texto resolve por construção: cada
# frase tem um destino que depende só dela e da semente. Acrescentar exemplos
# nunca move os que já existem, e reexecutar é idempotente.
#
# O custo é que a proporção por classe passa a ser aproximada, e não exata —
# ruído binomial em torno da fração pedida. Por isso o relatório imprime as
# contagens reais em vez de prometê-las.

from __future__ import annotations

import argparse
import csv
import hashlib
import re
import sys
import unicodedata
from collections import Counter
from pathlib import Path

from pln.caminhos import DATASET_PADRAO, DATASET_POOL, DATASET_TESTE

SEMENTE = 42
FRACAO_TESTE_PADRAO = 0.20

# Abaixo disto, o F1 daquela classe no retido vira ruído: cada exemplo vale
# mais de 10 pontos percentuais de recall, e o F1-macro herda a instabilidade.
# Não é erro — é a dispersão binomial que a atribuição por hash implica, e o
# remédio é corpus maior, não fração maior.
MINIMO_POR_CLASSE_NO_RETIDO = 10

_NAO_ALFANUMERICO = re.compile(r"[^\w\s]", flags=re.UNICODE)
_ESPACOS = re.compile(r"\s+")


# A chave de comparação entre as duas partições: é sobre ela que se afirma
# "nenhum exemplo do teste participou do treino". Sem normalizar, a mesma
# pergunta escrita com um acento a mais passaria por duas frases diferentes, e
# a garantia seria só aparente.
def normalizar(texto: str) -> str:
    decomposto = unicodedata.normalize("NFKD", texto.lower())
    sem_acento = "".join(c for c in decomposto if not unicodedata.combining(c))
    return _ESPACOS.sub(" ", _NAO_ALFANUMERICO.sub(" ", sem_acento)).strip()


def _sorte(texto: str, semente: int) -> float:
    digest = hashlib.sha256(f"{semente}:{normalizar(texto)}".encode()).digest()
    # Oito bytes bastam: 2^64 posições distintas sobre um corpus de milhares.
    return int.from_bytes(digest[:8], "big") / 2**64


def e_do_teste(texto: str, fracao_teste: float = FRACAO_TESTE_PADRAO, semente: int = SEMENTE) -> bool:
    return _sorte(texto, semente) < fracao_teste


def separar(
    linhas: list[tuple[str, str]],
    fracao_teste: float = FRACAO_TESTE_PADRAO,
    semente: int = SEMENTE,
) -> tuple[list[tuple[str, str]], list[tuple[str, str]]]:
    if not 0 < fracao_teste < 1:
        raise ValueError("fração de teste precisa estar em (0, 1)")

    desenvolvimento: list[tuple[str, str]] = []
    teste: list[tuple[str, str]] = []
    for texto, intencao in linhas:
        destino = teste if e_do_teste(texto, fracao_teste, semente) else desenvolvimento
        destino.append((texto, intencao))
    return desenvolvimento, teste


def carregar(caminho: Path) -> list[tuple[str, str]]:
    with caminho.open(encoding="utf-8", newline="") as arquivo:
        return [(linha["texto"], linha["intencao"]) for linha in csv.DictReader(arquivo)]


def gravar(caminho: Path, linhas: list[tuple[str, str]]) -> None:
    with caminho.open("w", encoding="utf-8", newline="") as arquivo:
        escritor = csv.writer(arquivo)
        escritor.writerow(["texto", "intencao"])
        escritor.writerows(linhas)


# Duplicata dentro do pool é mais traiçoeira do que parece: a mesma frase cai
# sempre na mesma partição (é o ponto do hash), então ela não vaza — mas infla
# a contagem e distorce a métrica da classe em silêncio.
def duplicatas(linhas: list[tuple[str, str]]) -> list[str]:
    contagem = Counter(normalizar(texto) for texto, _ in linhas)
    return sorted(chave for chave, quantas in contagem.items() if quantas > 1)


def classes_rasas_no_retido(
    teste: list[tuple[str, str]], minimo: int = MINIMO_POR_CLASSE_NO_RETIDO
) -> list[tuple[str, int]]:
    contagem = Counter(intencao for _, intencao in teste)
    return sorted((c, n) for c, n in contagem.items() if n < minimo)


def _tabela_por_classe(
    desenvolvimento: list[tuple[str, str]], teste: list[tuple[str, str]]
) -> list[str]:
    dev = Counter(intencao for _, intencao in desenvolvimento)
    ret = Counter(intencao for _, intencao in teste)
    largura = max((len(c) for c in set(dev) | set(ret)), default=10)

    linhas = [f"{'intenção':>{largura}}  {'dev':>5} {'teste':>6} {'% teste':>8}"]
    for intencao in sorted(set(dev) | set(ret)):
        d, r = dev[intencao], ret[intencao]
        proporcao = r / (d + r) if (d + r) else 0.0
        marca = "  <-- raso" if r < MINIMO_POR_CLASSE_NO_RETIDO else ""
        linhas.append(f"{intencao:>{largura}}  {d:>5} {r:>6} {proporcao:>7.1%}{marca}")
    return linhas


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Separa o pool de exemplos em desenvolvimento e teste retido."
    )
    parser.add_argument("--pool", type=Path, default=DATASET_POOL)
    parser.add_argument("--fracao-teste", type=float, default=FRACAO_TESTE_PADRAO)
    parser.add_argument("--semente", type=int, default=SEMENTE)
    parser.add_argument("--desenvolvimento", type=Path, default=DATASET_PADRAO)
    parser.add_argument("--teste", type=Path, default=DATASET_TESTE)
    args = parser.parse_args(argv)

    if not args.pool.exists():
        print(
            f"❌ Pool não encontrado em {args.pool}.\n"
            f"   É o arquivo autoral com TODOS os exemplos; os outros dois são gerados a partir dele."
        )
        return 1

    linhas = carregar(args.pool)
    repetidas = duplicatas(linhas)
    if repetidas:
        print(f"❌ {len(repetidas)} texto(s) repetido(s) no pool. Os três primeiros:")
        for chave in repetidas[:3]:
            print(f"   {chave!r}")
        print("   Repetição infla a contagem da classe e distorce a métrica sem acusar.")
        return 1

    desenvolvimento, teste = separar(linhas, args.fracao_teste, args.semente)

    gravar(args.desenvolvimento, desenvolvimento)
    gravar(args.teste, teste)

    print(f"Pool: {args.pool}  ({len(linhas)} exemplos)")
    print(f"Fração de teste pedida: {args.fracao_teste:.0%}  (semente {args.semente})\n")
    print("\n".join(_tabela_por_classe(desenvolvimento, teste)))
    print(f"\nDesenvolvimento: {len(desenvolvimento)} exemplos -> {args.desenvolvimento}")
    print(f"Teste retido   : {len(teste)} exemplos -> {args.teste}")

    rasas = classes_rasas_no_retido(teste)
    if rasas:
        print(
            f"\n⚠  {len(rasas)} classe(s) com menos de {MINIMO_POR_CLASSE_NO_RETIDO} "
            f"exemplos no retido: " + ", ".join(f"{c} ({n})" for c, n in rasas)
        )
        print(
            "   O F1 dessas classes no retido é ruidoso, e o F1-macro herda o ruído.\n"
            "   A atribuição por hash tem dispersão binomial por construção: o que\n"
            "   corrige é ampliar o corpus, não aumentar a fração de teste."
        )
    print(
        "\nO teste retido é lido SOMENTE por `python -m pln.metricas --teste`.\n"
        "Não é o conjunto cego da Seção 6.3, que exige frases novas e custodiadas."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
