#!/usr/bin/env python3
# =============================================================================
# gerar_pln_completo.py — monta entregas/pln_completo.py a partir dos módulos
# =============================================================================
# O arquivo único existe porque a entrega da faculdade pede um script que rode
# sozinho. O problema de mantê-lo à mão é conhecido e já aconteceu neste
# repositório: viram duas cópias da mesma lógica, e todo conserto precisa ser
# feito duas vezes. A cópia antiga tinha 1769 linhas e já divergia dos módulos.
#
# Aqui a direção é só uma: `src/pln/` é a fonte, `entregas/pln_completo.py` é
# saída. Editar a saída é trabalho perdido — o gerador sobrescreve.
#
#     python scripts/gerar_pln_completo.py            # regera
#     python scripts/gerar_pln_completo.py --conferir # só verifica se está atual
#
# `tests/test_entrega_unica.py` roda o modo `--conferir`, então o arquivo não
# tem como envelhecer sem alguém ficar sabendo.
#
# COMO A JUNÇÃO É FEITA
# ---------------------
# Concatenar os arquivos não basta: nomes de topo repetidos se apagam em
# silêncio, porque o segundo `def` simplesmente sobrescreve o primeiro sem erro
# nenhum. As três regras abaixo tratam isso.
#
# 1. IMPORTS são recolhidos de todos os módulos, unidos e reemitidos uma vez no
#    topo. Os imports internos (`from pln.x import ...`) são descartados: no
#    arquivo único não há mais o que importar.
#
# 2. NOMES REPETIDOS são detectados. Se dois módulos definem o mesmo nome com
#    código IDÊNTICO (o caso de `SEMENTE = 42`), a segunda cópia é removida. Se
#    definem com código DIFERENTE, o gerador PARA com erro — é o sinal de que
#    alguém precisa renomear na fonte, e não de que a junção deve escolher um
#    vencedor sozinha.
#
# 3. OS `main()` são renomeados para `main_<modulo>`, e a Seção final adiciona
#    uma linha de comando com subcomandos que apenas DESPACHA para eles. Nenhum
#    corpo de função é copiado — foi assim que a versão anterior acumulou
#    divergência.
# =============================================================================

from __future__ import annotations

import argparse
import ast
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
DIR_PACOTE = RAIZ / "src" / "pln"
DESTINO = RAIZ / "entregas" / "pln_completo.py"

# A ordem importa: é a ordem de definição no arquivo final, e um módulo só pode
# usar nomes já definidos acima dele no momento em que o módulo é executado.
MODULOS: tuple[tuple[str, str], ...] = (
    ("caminhos", "onde ficam os dados e os resultados"),
    ("preprocessamento", "texto bruto vira tokens"),
    ("vetorizacao", "tokens viram matriz numérica"),
    ("classificador", "o modelo do produto"),
    ("experimento", "a busca do TEXTO: pré-processamento x vetorização"),
    ("ajuste_fino", "a busca do MODELO: variante x suavização x priori"),
)

# Módulos cujo `main()` vira subcomando da linha de comando unificada.
COM_CLI: tuple[str, ...] = ("classificador", "experimento", "ajuste_fino")


CABECALHO = '''# =============================================================================
# pln_completo.py — O pipeline inteiro de PLN em UM arquivo
# =============================================================================
#           ██  ARQUIVO GERADO — NÃO EDITE ESTE ARQUIVO À MÃO  ██
#
# Toda alteração aqui é perdida na próxima geração. A fonte é `src/pln/`:
#
#     edite      src/pln/<modulo>.py
#     regenere   python scripts/gerar_pln_completo.py
#
# `tests/test_entrega_unica.py` falha se este arquivo estiver diferente do que
# o gerador produziria — então uma edição manual não passa despercebida, ela
# quebra a suíte.
#
# POR QUE ELE EXISTE
# ------------------
# É a versão de ENTREGA: roda sem instalar o pacote e sem import nenhum entre
# partes.
#
#     python entregas/pln_completo.py treinar
#     python entregas/pln_completo.py prever "Quais prazos vencem esta semana?"
#     python entregas/pln_completo.py experimento --sem-ordem
#
# O código é o mesmo dos módulos, na ordem em que um depende do outro:
#
{indice}#
# Dependências de dados, baixadas uma vez:
#     python -m nltk.downloader stopwords rslp
#     python -m spacy download pt_core_news_sm
# =============================================================================
'''


CLI = '''# =============================================================================
# SEÇÃO {numero} — LINHA DE COMANDO
# =============================================================================
# Os módulos originais têm um `main()` cada: um treina o classificador, o outro
# roda o experimento. Juntá-los faria o segundo `def main` apagar o primeiro em
# silêncio, então o gerador renomeia os dois e põe UM ponto de entrada aqui.
#
# Esta função não reimplementa nada: ela repassa os argumentos restantes para o
# `main` do módulo correspondente. É o que garante que o arquivo único e os
# módulos se comportem igual — não existe segunda cópia da lógica para divergir.
#
#     python entregas/pln_completo.py treinar               == python -m pln.classificador
#     python entregas/pln_completo.py prever "..."          == python -m pln.classificador --prever "..."
#     python entregas/pln_completo.py experimento           == python -m pln.experimento
#     python entregas/pln_completo.py ajuste                == python -m pln.ajuste_fino
# =============================================================================

USO = """uso: pln_completo.py <comando> [opções]

comandos:
  treinar              treina, avalia por validação cruzada e salva o modelo
  prever "<frase>"     classifica uma frase com o modelo salvo
  experimento          busca a melhor preparação do TEXTO
  ajuste               busca os hiperparâmetros do MODELO (rode o experimento antes)

`<comando> --help` mostra as opções de cada um."""


def main(argv: list[str] | None = None) -> int:
    argumentos = list(sys.argv[1:] if argv is None else argv)

    if not argumentos or argumentos[0] in {{"-h", "--help"}}:
        print(USO)
        return 0

    comando, resto = argumentos[0], argumentos[1:]

    if comando == "treinar":
        return main_classificador(resto)

    # `prever` é `--prever` do classificador. Fica como subcomando próprio
    # porque `pln_completo.py prever "frase"` lê melhor do que a flag.
    if comando == "prever":
        if not resto:
            print('faltou a frase: pln_completo.py prever "Quais prazos vencem?"')
            return 2
        return main_classificador(["--prever", *resto])

    if comando == "experimento":
        return main_experimento(resto)

    # `ajuste` lê o CSV que `experimento` grava, então a ordem importa.
    if comando == "ajuste":
        return main_ajuste_fino(resto)

    print(f"comando desconhecido: {{comando}}\\n")
    print(USO)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
'''


class ColisaoDeNomes(Exception):
    pass


# Um nome definido no topo de um módulo, com o texto que o define.
class Definicao:
    def __init__(self, nome: str, modulo: str, fonte: str, linha_inicial: int, linha_final: int) -> None:
        self.nome = nome
        self.modulo = modulo
        self.fonte = fonte
        self.linha_inicial = linha_inicial
        self.linha_final = linha_final


# Os nomes que um nó de topo passa a definir. Só interessam os três tipos que
# aparecem nestes módulos; qualquer outro não define nome nenhum e é ignorado.
def nomes_definidos(no: ast.stmt) -> list[str]:
    if isinstance(no, ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef):
        return [no.name]
    if isinstance(no, ast.Assign):
        return [alvo.id for alvo in no.targets if isinstance(alvo, ast.Name)]
    if isinstance(no, ast.AnnAssign) and isinstance(no.target, ast.Name):
        return [no.target.id]
    return []


# Um `def`/`class` começa na primeira linha do seu decorador, se houver — sem
# isto o decorador ficaria órfão no arquivo gerado.
def primeira_linha(no: ast.stmt) -> int:
    if isinstance(no, ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef) and no.decorator_list:
        return min(d.lineno for d in no.decorator_list)
    return no.lineno


# Comentários coladas acima de uma definição pertencem a ela: quando a definição
# é removida por ser duplicata, eles saem junto. O banner de seção (`# ===`) é a
# exceção — ele organiza o arquivo, não descreve a definição seguinte.
def inicio_com_comentarios(linhas: list[str], linha_inicial: int) -> int:
    indice = linha_inicial - 1
    while indice > 0:
        anterior = linhas[indice - 1].strip()
        if anterior.startswith("# ===") or anterior.startswith("# ---") or not anterior.startswith("#"):
            break
        indice -= 1
    return indice + 1


def ler_modulo(nome: str) -> tuple[list[ast.stmt], list[str], str]:
    fonte = (DIR_PACOTE / f"{nome}.py").read_text(encoding="utf-8")
    arvore = ast.parse(fonte)
    return arvore.body, fonte.splitlines(), fonte


# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------


def eh_import_interno(no: ast.stmt) -> bool:
    return isinstance(no, ast.ImportFrom) and (no.module or "").split(".")[0] == "pln"


def eh_future(no: ast.stmt) -> bool:
    return isinstance(no, ast.ImportFrom) and no.module == "__future__"


def eh_stdlib(modulo: str) -> bool:
    return modulo.split(".")[0] in sys.stdlib_module_names


# Junta os imports de todos os módulos, unindo os nomes vindos de um mesmo
# módulo (`from dataclasses import dataclass` e `... import dataclass, replace`
# viram uma linha só) e ordenando como o ruff/isort espera: stdlib antes de
# terceiros, `import x` antes de `from x import y`, alfabético dentro de cada
# grupo. Se sair fora de ordem, o `ruff check` do CI acusa.
def montar_imports(modulos: list[tuple[str, list[ast.stmt]]]) -> str:
    simples: set[str] = set()
    de: dict[str, set[str]] = {}

    for _, corpo in modulos:
        for no in corpo:
            if eh_future(no) or eh_import_interno(no):
                continue
            if isinstance(no, ast.Import):
                for alias in no.names:
                    simples.add(f"{alias.name} as {alias.asname}" if alias.asname else alias.name)
            elif isinstance(no, ast.ImportFrom) and no.module and no.level == 0:
                nomes = de.setdefault(no.module, set())
                for alias in no.names:
                    nomes.add(f"{alias.name} as {alias.asname}" if alias.asname else alias.name)

    def bloco(padrao_stdlib: bool) -> list[str]:
        linhas = [f"import {m}" for m in sorted(simples) if eh_stdlib(m) is padrao_stdlib]
        linhas += [
            f"from {m} import {', '.join(sorted(de[m]))}"
            for m in sorted(de)
            if eh_stdlib(m) is padrao_stdlib
        ]
        return linhas

    partes = ["from __future__ import annotations"]
    for padrao_stdlib in (True, False):
        if linhas := bloco(padrao_stdlib):
            partes.append("\n".join(linhas))
    return "\n\n".join(partes)


# -----------------------------------------------------------------------------
# Corpo de cada módulo
# -----------------------------------------------------------------------------


# Devolve o texto do módulo sem imports, sem o bloco `if __name__`, sem as
# definições que já apareceram antes, e com `main` renomeado.
def montar_corpo(
    nome: str,
    corpo: list[ast.stmt],
    linhas: list[str],
    ja_definidos: dict[str, Definicao],
) -> str:
    descartar: set[int] = set()  # linhas 1-based a remover

    def descartar_intervalo(inicio: int, fim: int) -> None:
        descartar.update(range(inicio, fim + 1))

    for no in corpo:
        fim = no.end_lineno or no.lineno

        if isinstance(no, ast.Import | ast.ImportFrom):
            descartar_intervalo(no.lineno, fim)
            continue

        # `if __name__ == "__main__": raise SystemExit(main())` — a Seção final
        # do arquivo gerado tem o seu próprio.
        if isinstance(no, ast.If) and ast.unparse(no.test).startswith("__name__"):
            descartar_intervalo(inicio_com_comentarios(linhas, no.lineno), fim)
            continue

        # O docstring do módulo, quando existe, já foi substituído pelo cabeçalho.
        if no is corpo[0] and isinstance(no, ast.Expr) and isinstance(no.value, ast.Constant) \
                and isinstance(no.value.value, str):
            descartar_intervalo(no.lineno, fim)
            continue

        inicio = primeira_linha(no)
        fonte_do_no = "\n".join(linhas[inicio - 1 : fim])

        for bruto in nomes_definidos(no):
            # `main` é renomeado adiante para `main_<modulo>`; o registro precisa
            # usar o nome FINAL, senão os dois `main` colidem sem ter colidido.
            definido = f"main_{nome}" if bruto == "main" and nome in COM_CLI else bruto
            anterior = ja_definidos.get(definido)
            if anterior is None:
                ja_definidos[definido] = Definicao(definido, nome, fonte_do_no, inicio, fim)
                continue

            if anterior.fonte != fonte_do_no:
                raise ColisaoDeNomes(
                    f"`{definido}` é definido de formas DIFERENTES em "
                    f"{anterior.modulo}.py e {nome}.py.\n"
                    f"O arquivo único não pode ter os dois, e escolher um sozinho seria "
                    f"mudar o comportamento em silêncio.\n"
                    f"Renomeie um dos dois em src/pln/ e rode o gerador de novo."
                )
            # Idênticos: a segunda cópia é redundante e sai, junto com os
            # comentários que a explicavam.
            descartar_intervalo(inicio_com_comentarios(linhas, inicio), fim)

    texto = "\n".join(linha for numero, linha in enumerate(linhas, start=1) if numero not in descartar)

    if nome in COM_CLI:
        antes = "def main(argv: list[str] | None = None) -> int:"
        depois = f"def main_{nome}(argv: list[str] | None = None) -> int:"
        if texto.count(antes) != 1:
            raise ColisaoDeNomes(
                f"{nome}.py: esperava exatamente um `{antes}` para renomear, "
                f"achei {texto.count(antes)}."
            )
        texto = texto.replace(antes, depois)

    return texto.strip("\n")


# -----------------------------------------------------------------------------
# Montagem
# -----------------------------------------------------------------------------


# O primeiro comando de topo que não é import nem docstring — é ele que define
# quantas linhas em branco o isort espera depois do bloco de imports.
def primeiro_comando_real(corpo: list[ast.stmt]) -> ast.stmt | None:
    for no in corpo:
        if isinstance(no, ast.Import | ast.ImportFrom):
            continue
        if isinstance(no, ast.Expr) and isinstance(no.value, ast.Constant) and isinstance(no.value.value, str):
            continue
        return no
    return None


def gerar() -> str:
    lidos = [(nome, *ler_modulo(nome)) for nome, _ in MODULOS]
    modulos_ast = [(nome, corpo) for nome, corpo, _, _ in lidos]

    indice = "".join(
        f"#     SEÇÃO {numero} — {nome}.py: {descricao}\n"
        for numero, (nome, descricao) in enumerate(MODULOS, start=1)
    )
    indice += f"#     SEÇÃO {len(MODULOS) + 1} — a linha de comando unificada\n"

    ja_definidos: dict[str, Definicao] = {}
    secoes: list[str] = []
    for numero, ((nome, corpo, linhas, _), (_, descricao)) in enumerate(zip(lidos, MODULOS, strict=True), start=1):
        banner = (
            "# =============================================================================\n"
            f"# SEÇÃO {numero} — {nome.upper()}: {descricao}\n"
            f"# Fonte: src/pln/{nome}.py\n"
            "# ============================================================================="
        )
        secoes.append(f"{banner}\n\n{montar_corpo(nome, corpo, linhas, ja_definidos)}")

    secoes.append(CLI.format(numero=len(MODULOS) + 1).strip("\n"))

    # Entre seções, duas linhas em branco — o espaçamento de topo de arquivo.
    corpo_do_arquivo = "\n\n\n".join(secoes)

    # Depois do bloco de imports, porém, o ruff aplica a regra do isort com
    # `lines-after-imports = -1`: DUAS linhas em branco se o que vem a seguir é
    # um `def`/`class`, UMA em qualquer outro caso. O banner de seção é
    # comentário e não conta — quem decide é o primeiro comando de verdade.
    # Fixar o espaçamento aqui faria o `ruff check` do CI reclamar do arquivo
    # gerado sempre que a primeira seção começasse com uma constante.
    primeiro = primeiro_comando_real(lidos[0][1])
    em_branco = 2 if isinstance(primeiro, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef) else 1

    return "\n".join([
        CABECALHO.format(indice=indice),
        "",
        montar_imports(modulos_ast),
        *([""] * em_branco),
        corpo_do_arquivo,
        "",
    ])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Gera entregas/pln_completo.py a partir de src/pln/.")
    parser.add_argument("--conferir", action="store_true",
                        help="não escreve; sai com 1 se o arquivo estiver desatualizado")
    args = parser.parse_args(argv)

    try:
        conteudo = gerar()
    except ColisaoDeNomes as erro:
        print(f"❌ {erro}")
        return 1

    if args.conferir:
        atual = DESTINO.read_text(encoding="utf-8") if DESTINO.exists() else ""
        if atual == conteudo:
            print(f"✅ {DESTINO.relative_to(RAIZ)} está atualizado.")
            return 0
        print(f"❌ {DESTINO.relative_to(RAIZ)} está DESATUALIZADO em relação a src/pln/.\n"
              f"   Rode: python scripts/gerar_pln_completo.py")
        return 1

    DESTINO.parent.mkdir(parents=True, exist_ok=True)
    DESTINO.write_text(conteudo, encoding="utf-8")
    print(f"✅ {DESTINO.relative_to(RAIZ)} gerado — {len(conteudo.splitlines())} linhas, "
          f"a partir de {len(MODULOS)} módulos.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
