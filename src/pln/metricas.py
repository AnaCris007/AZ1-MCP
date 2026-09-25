# As três métricas do RNF03, e o limiar de confiança que duas delas dependem.
#
# O `classificador.py` calcula F1-macro e nada mais. O RNF03 exige três números
# simultâneos, e os outros dois nunca foram medidos neste projeto:
#
#     F1-macro entre as dez intenções        >= 0,85
#     cobertura sobre as nove conhecidas     >= 0,90
#     aceitação indevida de fora_do_catalogo <= 0,15
#
# DEFINIÇÕES, LITERAIS DA SEÇÃO 6.3
# ---------------------------------
# Cobertura é `exemplos conhecidos não rejeitados / 180`. Repare no que ela NÃO
# é: um exemplo conhecido classificado na intenção conhecida ERRADA continua
# contando como coberto, porque não foi encaminhado à rejeição. Cobertura mede
# disposição a responder, não acerto — quem mede acerto é o F1.
#
# Aceitação indevida é `exemplos fora do catálogo classificados como intenção
# conhecida / 20`.
#
# POR QUE AS DUAS PRECISAM DO LIMIAR
# ----------------------------------
# Ambas são definidas sobre a decisão de rejeitar, que não existe no modelo: o
# `predict` devolve sempre a classe de maior probabilidade. A rejeição é uma
# regra aplicada por cima, comparando a confiança contra um limiar. Subir o
# limiar melhora a aceitação indevida e piora a cobertura, sempre — por isso o
# relatório traz a curva inteira, e não um ponto.
#
# O limiar é calibrado SOMENTE em dados de desenvolvimento. A Seção 6.3 é
# explícita: usar o conjunto cego para escolher limiar queima o conjunto cego.

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from sklearn.metrics import classification_report, f1_score
from sklearn.model_selection import StratifiedKFold, cross_val_predict

from pln.caminhos import DATASET_PADRAO, DATASET_TESTE, garantir_dir_de_resultados
from pln.classificador import (
    SEMENTE,
    carregar_dataset,
    construir_classificador,
)

# A regra de rejeição e o rótulo de recusa vêm de `pln.intencao`, e não são
# redefinidos aqui. É a mesma função que o serviço aplica em produção: medir
# uma regra e executar outra faria este relatório descrever um sistema que não
# existe.
from pln.intencao import INTENCAO_FORA_DO_CATALOGO, aplicar_limiar_em_lote

META_F1_MACRO = 0.85
META_COBERTURA = 0.90
META_ACEITACAO_INDEVIDA = 0.15

# O limiar varre de 0 a 1. Em 0,00 nada é rejeitado (cobertura 100%, aceitação
# indevida máxima); perto de 1,00 quase tudo é (o inverso).
LIMIARES_PADRAO: tuple[float, ...] = tuple(round(0.05 * i, 2) for i in range(21))

# Frações do dataset usadas na curva de aprendizado.
FRACOES_PADRAO: tuple[float, ...] = (0.2, 0.4, 0.6, 0.8, 1.0)


@dataclass(frozen=True)
class ResultadoRNF03:
    limiar: float
    f1_macro: float
    cobertura: float
    aceitacao_indevida: float
    conhecidos: int
    fora_do_catalogo: int

    # Os três limites são cumulativos: a Seção 6.3 exige que sejam atendidos
    # simultaneamente, então não existe "aprovado em dois de três".
    @property
    def aprovado(self) -> bool:
        return (
            self.f1_macro >= META_F1_MACRO
            and self.cobertura >= META_COBERTURA
            and self.aceitacao_indevida <= META_ACEITACAO_INDEVIDA
        )

    def descrever(self) -> str:
        return (
            f"limiar={self.limiar:.2f}  F1={self.f1_macro:.4f}  "
            f"cobertura={self.cobertura:.1%}  aceitação indevida={self.aceitacao_indevida:.1%}"
        )


# Recebe as previsões cruas (argmax e confiança) e devolve as três métricas já
# com a rejeição aplicada. Separado de quem produz as previsões para que sirva
# tanto à validação cruzada quanto ao conjunto cego, que vem de arquivo.
def avaliar_rnf03(
    reais: list[str], previstos: list[str], confiancas: list[float], limiar: float
) -> ResultadoRNF03:
    if not reais:
        raise ValueError("sem exemplos para avaliar")

    com_rejeicao = aplicar_limiar_em_lote(previstos, confiancas, limiar)

    # O F1-macro é sobre as dez classes do catálogo, e não sobre as nove
    # conhecidas: `fora_do_catalogo` sai do treino (quando sai), nunca da métrica.
    classes = sorted(set(reais) | {INTENCAO_FORA_DO_CATALOGO})
    f1 = f1_score(reais, com_rejeicao, average="macro", labels=classes, zero_division=0)

    pares = list(zip(reais, com_rejeicao, strict=True))
    conhecidos = [(r, p) for r, p in pares if r != INTENCAO_FORA_DO_CATALOGO]
    fora = [(r, p) for r, p in pares if r == INTENCAO_FORA_DO_CATALOGO]

    # "Não rejeitado" é a definição da Seção 6.3 — inclui o conhecido que caiu
    # na intenção conhecida errada.
    nao_rejeitados = sum(1 for _, p in conhecidos if p != INTENCAO_FORA_DO_CATALOGO)
    aceitos_indevidamente = sum(1 for _, p in fora if p != INTENCAO_FORA_DO_CATALOGO)

    return ResultadoRNF03(
        limiar=limiar,
        f1_macro=float(f1),
        cobertura=nao_rejeitados / len(conhecidos) if conhecidos else 0.0,
        aceitacao_indevida=aceitos_indevidamente / len(fora) if fora else 0.0,
        conhecidos=len(conhecidos),
        fora_do_catalogo=len(fora),
    )


def curva_do_limiar(
    reais: list[str],
    previstos: list[str],
    confiancas: list[float],
    limiares: tuple[float, ...] = LIMIARES_PADRAO,
) -> list[ResultadoRNF03]:
    return [avaliar_rnf03(reais, previstos, confiancas, limiar) for limiar in limiares]


# O ponto de operação: entre os limiares que atendem aos três limites, o de
# maior F1. Devolve `None` quando nenhum atende — e esse `None` é informação, não
# falha: significa que o problema é o modelo, e nenhum limiar o conserta.
def escolher_limiar(curva: list[ResultadoRNF03]) -> ResultadoRNF03 | None:
    aprovados = [r for r in curva if r.aprovado]
    if not aprovados:
        return None
    return max(aprovados, key=lambda r: r.f1_macro)


# Quanto falta para atender ao RNF03, somando as três violações normalizadas
# pelos respectivos limites. Zero significa aprovado.
#
# Função de módulo, e não closure, porque comparar MODELOS precisa da mesma
# régua que comparar limiares. Sem ela, "qual é melhor" vira uma discussão
# sobre qual das três métricas olhar — e como cobertura e aceitação indevida
# trocam entre si, sempre existe uma escolha de métrica que faz qualquer
# candidato vencer.
def distancia_do_requisito(r: ResultadoRNF03) -> float:
    return (
        max(0.0, META_F1_MACRO - r.f1_macro) / META_F1_MACRO
        + max(0.0, META_COBERTURA - r.cobertura) / META_COBERTURA
        + max(0.0, r.aceitacao_indevida - META_ACEITACAO_INDEVIDA) / META_ACEITACAO_INDEVIDA
    )


# Mesmo não havendo ponto aprovado, é útil saber qual limiar chega mais perto.
def limiar_menos_distante(curva: list[ResultadoRNF03]) -> ResultadoRNF03:
    return min(curva, key=distancia_do_requisito)


# Previsões fora da amostra para todo o dataset: cada exemplo é previsto por um
# modelo que não o viu. É o que permite medir sem separar um conjunto de teste
# fixo, que com 400 exemplos custaria caro.
def prever_por_validacao_cruzada(
    textos: list[str], rotulos: list[str], modelo=None, k: int = 5
) -> tuple[list[str], list[float]]:
    modelo = modelo if modelo is not None else construir_classificador()
    dobras = StratifiedKFold(n_splits=k, shuffle=True, random_state=SEMENTE)

    probabilidades = cross_val_predict(
        modelo, textos, rotulos, cv=dobras, method="predict_proba"
    )
    # `cross_val_predict` ordena as colunas por `np.unique(y)`, e não pela ordem
    # de aparição no CSV. Ler as classes daqui, e não do estimador, é o que
    # mantém rótulo e coluna alinhados.
    classes = np.unique(rotulos)
    indices = probabilidades.argmax(axis=1)

    previstos = [str(classes[i]) for i in indices]
    confiancas = [float(probabilidades[linha, i]) for linha, i in enumerate(indices)]
    return previstos, confiancas


# Previsões de um modelo JÁ TREINADO sobre textos que ele nunca viu.
#
# Não confundir com `prever_por_validacao_cruzada`, logo acima: lá cada exemplo
# é previsto por um modelo diferente, treinado nas outras dobras do MESMO
# corpus. Aqui existe um modelo só, e os textos vêm de outro arquivo. É a
# diferença entre estimar o desempenho e medi-lo.
def prever_com_modelo(modelo, textos: list[str]) -> tuple[list[str], list[float]]:
    probabilidades = modelo.predict_proba(textos)
    classes = modelo.named_steps["classificador"].classes_
    indices = probabilidades.argmax(axis=1)

    previstos = [str(classes[i]) for i in indices]
    confiancas = [float(probabilidades[linha, i]) for linha, i in enumerate(indices)]
    return previstos, confiancas


@dataclass(frozen=True)
class MedicaoNoRetido:
    limiar: float
    escolhido_no_desenvolvimento: ResultadoRNF03
    no_retido: ResultadoRNF03
    reais: list[str]
    previstos: list[str]
    confiancas: list[float]

    # O relatório por classe precisa ver o que o sistema FARIA, e não o argmax
    # cru: é a rejeição que produz `fora_do_catalogo` nas linhas de baixa
    # confiança, e é dela que saem cobertura e aceitação indevida.
    def previstos_com_rejeicao(self) -> list[str]:
        return aplicar_limiar_em_lote(self.previstos, self.confiancas, self.limiar)


# A ORDEM DESTES TRÊS PASSOS É A MEDIÇÃO.
#
# O limiar sai do desenvolvimento e entra congelado no retido. Escolhê-lo
# olhando o retido — mesmo "só para ver" — transformaria a medição num ajuste,
# e o número publicado voltaria a ser otimista por construção, que é
# exatamente o que separar o conjunto pretendia resolver.
def avaliar_no_teste_retido(
    dev_textos: list[str],
    dev_rotulos: list[str],
    teste_textos: list[str],
    teste_rotulos: list[str],
    k: int = 5,
) -> MedicaoNoRetido:
    previstos_dev, confiancas_dev = prever_por_validacao_cruzada(dev_textos, dev_rotulos, k=k)
    curva = curva_do_limiar(dev_rotulos, previstos_dev, confiancas_dev)
    escolhido = escolher_limiar(curva) or limiar_menos_distante(curva)

    modelo = construir_classificador()
    modelo.fit(dev_textos, dev_rotulos)

    previstos, confiancas = prever_com_modelo(modelo, teste_textos)
    return MedicaoNoRetido(
        limiar=escolhido.limiar,
        escolhido_no_desenvolvimento=escolhido,
        no_retido=avaliar_rnf03(teste_rotulos, previstos, confiancas, escolhido.limiar),
        reais=teste_rotulos,
        previstos=previstos,
        confiancas=confiancas,
    )


# Subamostra estratificada: mantém a proporção entre classes para que a curva
# meça o efeito do TAMANHO, e não de um desbalanceamento introduzido no caminho.
def subamostrar(
    textos: list[str], rotulos: list[str], fracao: float, semente: int = SEMENTE
) -> tuple[list[str], list[str]]:
    if not 0 < fracao <= 1:
        raise ValueError("fração precisa estar em (0, 1]")
    if fracao == 1.0:
        return list(textos), list(rotulos)

    gerador = np.random.default_rng(semente)
    por_classe: dict[str, list[int]] = {}
    for indice, rotulo in enumerate(rotulos):
        por_classe.setdefault(rotulo, []).append(indice)

    escolhidos: list[int] = []
    for rotulo in sorted(por_classe):
        indices = por_classe[rotulo]
        # Pelo menos 2 por classe, senão a validação cruzada estratificada quebra.
        quantos = max(2, round(len(indices) * fracao))
        escolhidos.extend(gerador.choice(indices, size=min(quantos, len(indices)), replace=False))

    escolhidos.sort()
    return [textos[i] for i in escolhidos], [rotulos[i] for i in escolhidos]


# A curva que responde se mais dados fecham o gap. Se o F1 ainda sobe em 100%
# do dataset atual, ampliar o corpus é o caminho; se já achatou, o caminho é
# trocar a arquitetura.
def curva_de_aprendizado(
    textos: list[str],
    rotulos: list[str],
    fracoes: tuple[float, ...] = FRACOES_PADRAO,
    k: int = 5,
) -> list[tuple[float, int, float]]:
    curva: list[tuple[float, int, float]] = []
    for fracao in fracoes:
        parte_textos, parte_rotulos = subamostrar(textos, rotulos, fracao)
        dobras = StratifiedKFold(n_splits=k, shuffle=True, random_state=SEMENTE)
        previstos = cross_val_predict(
            construir_classificador(), parte_textos, parte_rotulos, cv=dobras
        )
        f1 = f1_score(parte_rotulos, previstos, average="macro", zero_division=0)
        curva.append((fracao, len(parte_textos), float(f1)))
    return curva


def _secao_curva_do_limiar(curva: list[ResultadoRNF03]) -> list[str]:
    linhas = [
        "## Curva do limiar de confiança",
        "",
        "Cobertura e aceitação indevida trocam entre si: todo limiar que melhora uma",
        "piora a outra. O ponto de operação é o que atende aos três limites ao mesmo",
        "tempo — se não existir nenhum, o problema é o modelo, e não o limiar.",
        "",
        "| Limiar | F1-macro | Cobertura | Aceitação indevida | Atende aos 3 |",
        "| ---: | ---: | ---: | ---: | :---: |",
    ]
    for r in curva:
        marca = "sim" if r.aprovado else "—"
        linhas.append(
            f"| {r.limiar:.2f} | {r.f1_macro:.4f} | {r.cobertura:.1%} "
            f"| {r.aceitacao_indevida:.1%} | {marca} |"
        )
    return linhas + [""]


def _secao_veredito(curva: list[ResultadoRNF03]) -> list[str]:
    escolhido = escolher_limiar(curva)

    if escolhido is not None:
        return [
            "## Ponto de operação",
            "",
            f"**Limiar {escolhido.limiar:.2f}** atende aos três limites do RNF03:",
            "",
            f"- F1-macro **{escolhido.f1_macro:.4f}** (mínimo {META_F1_MACRO:.2f})",
            f"- Cobertura **{escolhido.cobertura:.1%}** (mínimo {META_COBERTURA:.0%})",
            f"- Aceitação indevida **{escolhido.aceitacao_indevida:.1%}** "
            f"(máximo {META_ACEITACAO_INDEVIDA:.0%})",
            "",
            "Calibrado em dados de desenvolvimento. A validação final exige o conjunto",
            "cego custodiado da Seção 6.3, medido uma única vez.",
            "",
        ]

    proximo = limiar_menos_distante(curva)
    return [
        "## Ponto de operação",
        "",
        "**Nenhum limiar atende aos três limites simultaneamente.**",
        "",
        "Isto não é um problema de calibração: significa que o modelo não separa as",
        "classes o suficiente para que exista um ponto de corte viável. Ajustar o",
        "limiar apenas troca qual dos três critérios falha.",
        "",
        f"O mais próximo é o limiar **{proximo.limiar:.2f}**:",
        "",
        f"- F1-macro **{proximo.f1_macro:.4f}** (mínimo {META_F1_MACRO:.2f})",
        f"- Cobertura **{proximo.cobertura:.1%}** (mínimo {META_COBERTURA:.0%})",
        f"- Aceitação indevida **{proximo.aceitacao_indevida:.1%}** "
        f"(máximo {META_ACEITACAO_INDEVIDA:.0%})",
        "",
    ]


def _secao_curva_de_aprendizado(curva: list[tuple[float, int, float]]) -> list[str]:
    linhas = [
        "## Curva de aprendizado",
        "",
        "F1-macro em função do tamanho do corpus, por subamostragem estratificada.",
        "É o que diz se ampliar o dataset fecha a distância até 0,85: curva ainda",
        "subindo em 100% significa que sim; curva achatada significa que o caminho",
        "é trocar a arquitetura, não juntar mais frases.",
        "",
        "| Fração | Exemplos | F1-macro | Ganho sobre a anterior |",
        "| ---: | ---: | ---: | ---: |",
    ]
    anterior: float | None = None
    for fracao, quantos, f1 in curva:
        ganho = "—" if anterior is None else f"{f1 - anterior:+.4f}"
        linhas.append(f"| {fracao:.0%} | {quantos} | {f1:.4f} | {ganho} |")
        anterior = f1

    if len(curva) >= 2:
        ultimo_ganho = curva[-1][2] - curva[-2][2]
        if ultimo_ganho > 0.01:
            leitura = (
                f"O último degrau ainda rende **{ultimo_ganho:+.4f}**: a curva não achatou, "
                "e ampliar o corpus deve continuar rendendo."
            )
        else:
            leitura = (
                f"O último degrau rende apenas **{ultimo_ganho:+.4f}**: a curva achatou. "
                "Mais exemplos do mesmo tipo tendem a render pouco; o ganho terá de vir "
                "de representação ou de família de modelo."
            )
        linhas += ["", leitura]
    return linhas + [""]


def _relatorio_do_retido(medicao: MedicaoNoRetido, dev: int, retido: int) -> list[str]:
    r = medicao.no_retido
    escolhido = medicao.escolhido_no_desenvolvimento
    return [
        "# RNF03 no conjunto de teste retido",
        "",
        "Arquivo gerado por `python -m pln.metricas --teste`. Não editar à mão.",
        "",
        "> **Isto não é o conjunto cego da Seção 6.3.** Aquele exige frases novas,",
        "> escritas depois e custodiadas por quem não participou do ajuste. Este é um",
        "> teste retido: separado do pool por `python -m pln.particao` ANTES de",
        "> qualquer treino, escolha de pré-processamento, ajuste de hiperparâmetro ou",
        "> calibração de limiar, e lido uma única vez, aqui. Ele mede generalização",
        "> com honestidade e não substitui a medição cega.",
        "",
        f"- Desenvolvimento: {dev} exemplos (treino, busca, ajuste e calibração)",
        f"- Teste retido: {retido} exemplos, nunca vistos",
        f"- Exemplos de intenções conhecidas no retido: {r.conhecidos}",
        f"- Exemplos `fora_do_catalogo` no retido: {r.fora_do_catalogo}",
        "",
        "## Limiar congelado",
        "",
        f"**{medicao.limiar:.2f}**, escolhido SOMENTE sobre o desenvolvimento, onde media:",
        "",
        f"- F1-macro {escolhido.f1_macro:.4f}, cobertura {escolhido.cobertura:.1%}, "
        f"aceitação indevida {escolhido.aceitacao_indevida:.1%}",
        "",
        "A diferença entre esses números e os de baixo é o custo de generalizar. Se ela",
        "for grande, o modelo decorou o corpus de desenvolvimento.",
        "",
        "## Resultado no retido",
        "",
        f"- F1-macro: **{r.f1_macro:.4f}** (mínimo {META_F1_MACRO:.2f})",
        f"- Cobertura: **{r.cobertura:.1%}** (mínimo {META_COBERTURA:.0%})",
        f"- Aceitação indevida: **{r.aceitacao_indevida:.1%}** "
        f"(máximo {META_ACEITACAO_INDEVIDA:.0%})",
        "",
        f"**{'Atende' if r.aprovado else 'NÃO atende'} aos três limites simultaneamente.**",
        "",
        "## Relatório por classe (com a rejeição aplicada)",
        "",
        "```",
        classification_report(
            medicao.reais, medicao.previstos_com_rejeicao(), digits=3, zero_division=0
        ),
        "```",
        "",
    ]


def _medir_no_retido(args: argparse.Namespace) -> int:
    if not args.teste_retido.exists():
        print(
            f"❌ Teste retido não encontrado em {args.teste_retido}.\n"
            f"   Gere as duas partições primeiro:  python -m pln.particao"
        )
        return 1

    dev_textos, dev_rotulos = carregar_dataset(args.dataset)
    teste_textos, teste_rotulos = carregar_dataset(args.teste_retido)

    print(f"Desenvolvimento: {args.dataset}  ({len(dev_textos)} exemplos)")
    print(f"Teste retido   : {args.teste_retido}  ({len(teste_textos)} exemplos)")
    print(f"Calibrando o limiar no desenvolvimento ({args.k} dobras)...")

    medicao = avaliar_no_teste_retido(
        dev_textos, dev_rotulos, teste_textos, teste_rotulos, k=args.k
    )

    destino = args.salvar or (garantir_dir_de_resultados() / "metricas_teste_retido.md")
    linhas = _relatorio_do_retido(medicao, len(dev_textos), len(teste_textos))
    destino.write_text("\n".join(linhas) + "\n", encoding="utf-8")

    print(f"\nLimiar congelado do desenvolvimento: {medicao.limiar:.2f}")
    print(f"No retido: {medicao.no_retido.descrever()}")
    print(f"\nRelatório salvo em {destino}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Mede as três métricas do RNF03.")
    parser.add_argument("--dataset", type=Path, default=DATASET_PADRAO)
    parser.add_argument("--k", type=int, default=5, help="dobras da validação cruzada")
    parser.add_argument("--sem-curva-de-aprendizado", action="store_true",
                        help="pula a curva de aprendizado, que é a parte demorada")
    parser.add_argument("--salvar", type=Path, default=None,
                        help="destino do relatório (padrão: resultados/metricas_rnf03.md)")
    parser.add_argument("--teste", action="store_true",
                        help="mede uma vez no conjunto retido, com o limiar calibrado "
                             "no desenvolvimento")
    parser.add_argument("--teste-retido", type=Path, default=DATASET_TESTE,
                        help="arquivo do conjunto retido")
    args = parser.parse_args(argv)

    if args.teste:
        return _medir_no_retido(args)

    textos, rotulos = carregar_dataset(args.dataset)
    print(f"Dataset: {args.dataset}  ({len(textos)} exemplos, {len(set(rotulos))} classes)")

    print(f"Prevendo por validação cruzada de {args.k} dobras...")
    previstos, confiancas = prever_por_validacao_cruzada(textos, rotulos, k=args.k)

    curva = curva_do_limiar(rotulos, previstos, confiancas)
    sem_rejeicao = avaliar_rnf03(rotulos, previstos, confiancas, limiar=0.0)

    linhas = [
        "# Métricas do RNF03",
        "",
        "Arquivo gerado por `python -m pln.metricas`. Não editar à mão.",
        "",
        f"- Dataset: `{args.dataset.name}` ({len(textos)} exemplos)",
        f"- Validação cruzada estratificada de {args.k} dobras, semente {SEMENTE}",
        f"- Exemplos de intenções conhecidas: {sem_rejeicao.conhecidos}",
        f"- Exemplos `fora_do_catalogo`: {sem_rejeicao.fora_do_catalogo}",
        "",
        "## Sem rejeição (comportamento atual em produção)",
        "",
        "Com limiar 0,00 nada é rejeitado — é exatamente o que o serviço faz hoje,",
        "já que nenhum limiar é aplicado em `analysis_service`.",
        "",
        f"- F1-macro: **{sem_rejeicao.f1_macro:.4f}** (mínimo {META_F1_MACRO:.2f})",
        f"- Cobertura: **{sem_rejeicao.cobertura:.1%}** (mínimo {META_COBERTURA:.0%})",
        f"- Aceitação indevida: **{sem_rejeicao.aceitacao_indevida:.1%}** "
        f"(máximo {META_ACEITACAO_INDEVIDA:.0%})",
        "",
        *_secao_veredito(curva),
        *_secao_curva_do_limiar(curva),
    ]

    if not args.sem_curva_de_aprendizado:
        print("Medindo a curva de aprendizado...")
        linhas += _secao_curva_de_aprendizado(curva_de_aprendizado(textos, rotulos, k=args.k))

    linhas += [
        "## Relatório por classe (sem rejeição)",
        "",
        "```",
        classification_report(rotulos, previstos, digits=3, zero_division=0),
        "```",
        "",
    ]

    destino = args.salvar or (garantir_dir_de_resultados() / "metricas_rnf03.md")
    destino.write_text("\n".join(linhas) + "\n", encoding="utf-8")

    print()
    print(f"Sem rejeição : {sem_rejeicao.descrever()}")
    escolhido = escolher_limiar(curva)
    if escolhido is not None:
        print(f"Ponto de operação: {escolhido.descrever()}")
    else:
        print("Nenhum limiar atende aos três limites do RNF03.")
        print(f"Mais próximo    : {limiar_menos_distante(curva).descrever()}")
    print(f"\nRelatório salvo em {destino}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
