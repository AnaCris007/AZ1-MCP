# Classificador de intenções, o modelo do produto.
#
# O pipeline é um único objeto do sklearn (texto bruto -> pré-processamento ->
# vetorização -> classificador), o que impede treinar com um pré-processamento e
# prever com outro.
#
# O PRODUTO DEIXOU DE SER O MESMO MODELO DA RÉGUA
# -----------------------------------------------
# Até a Sprint 3 este arquivo montava `MultinomialNB`, o mesmo que
# `experimento.py` usa como instrumento de medida, e isso era apresentado como
# condição de validade: o pré-processamento é escolhido medindo com ele.
#
# A busca de três estágios de `comparativo_modelos.py` desfez o argumento ao
# medir cada família sobre o SEU melhor texto. O `MultinomialNB` ficou em sexto
# de sete e falhava nos três limites do RNF03 no conjunto retido (F1 0,7549,
# cobertura 81,6%, aceitação indevida 18,4%); a regressão logística atende aos
# três (F1 0,8716, cobertura 94,8%, aceitação indevida 8,2%).
#
# A régua de `experimento.py` CONTINUA sendo `MultinomialNB`, porque é a
# velocidade dele que torna a varredura praticável. A consequência precisa ser
# dita: o ranking de textos do estágio 1 é produzido sob uma família que não é
# mais a que roda. `comparativo_modelos.py` mede cada família sobre esse
# ranking, o que limita o dano, mas não o elimina — ver a Seção 3.3.7.
#
# POR QUE REGRESSÃO LOGÍSTICA, E NÃO `LinearSVC`
# ----------------------------------------------
# Os dois empatam dentro do ruído no conjunto retido (0,8716 contra 0,8735, com
# intervalos de 95% praticamente sobrepostos). O desempate é de engenharia: o
# `LinearSVC` não tem `predict_proba` e precisa de `CalibratedClassifierCV`, o
# que custa 5,8x em latência (1,618 ms contra 0,277 ms) e enterra os pesos por
# termo dentro de três modelos internos. A regressão logística otimiza
# diretamente a probabilidade sobre a qual a regra de rejeição de
# `pln.intencao` é construída.

from __future__ import annotations

import argparse
import csv
from pathlib import Path

import joblib
import numpy as np
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import classification_report, confusion_matrix, f1_score
from sklearn.model_selection import StratifiedKFold, cross_val_predict
from sklearn.pipeline import Pipeline
from sklearn.svm import LinearSVC

from pln.caminhos import DATASET_PADRAO, MODELO_PADRAO, garantir_dir_de_resultados
from pln.preprocessamento import (
    ConfigPreprocessamento,
    Tokenizacao,
    preprocessar,
)
from pln.vetorizacao import ConfigVetorizacao, ModoVetorizacao, construir_vetorizador

SEMENTE = 42

# Vencedores da busca de TRÊS estágios, válidos para o dataset em `dados/`.
# Trocar o dataset os invalida; regerar exige, nesta ordem:
#
#     python -m pln.particao              # separa desenvolvimento e teste retido
#     python -m pln.experimento           # estágio 1: ranqueia os textos
#     python -m pln.comparativo_modelos   # estágios 2 e 3: família e hiperparâmetro
CONFIG_PRE_PADRAO = ConfigPreprocessamento(
    minusculas=True, remover_acentos=True, remover_numeros=True,
    tokenizacao=Tokenizacao.REGEX,
)
CONFIG_VET_PADRAO = ConfigVetorizacao(ModoVetorizacao.BOW, n_max=2)

# Regularização inversa do `LinearSVC`. A grade do estágio 3 varreu
# 0,1 a 10 e não superou o padrão do scikit-learn — o que é resultado: a
# liderança dele não vinha de ter calhado num hiperparâmetro afortunado.
C_PADRAO = 1.0

# `lbfgs` sobre contagem bruta converge devagar; 2000 é o que basta sem avisos.
MAX_ITER_PADRAO = 2000

# DO NAIVE BAYES, que deixou de ser o produto e segue sendo a RÉGUA de
# `experimento.py`. Ficam aqui porque `ajuste_fino.py` os busca e
# `comparativo_modelos.py` os usa para montar o candidato de referência.
ALPHA_PADRAO = 1.0
FIT_PRIOR_PADRAO = True


# Como etapa do Pipeline, a configuração de pré-processamento viaja junto com o
# modelo salvo em disco.
class PreprocessadorDeTexto(BaseEstimator, TransformerMixin):
    # `clone()` reconstrói o objeto a partir dos parâmetros do `__init__` a cada
    # dobra da validação cruzada, então `config` não pode ser transformada aqui.
    def __init__(self, config: ConfigPreprocessamento = CONFIG_PRE_PADRAO) -> None:
        self.config = config

    def fit(self, X, y=None):  # noqa: N803 — nomes exigidos pela interface do sklearn
        return self

    def transform(self, X):  # noqa: N803
        return [preprocessar(texto, self.config) for texto in X]


# `estimador` existe para `comparativo_modelos.py` e `ajuste_fino.py` poderem
# trocar SÓ a última etapa, mantendo pré-processamento e vetorização idênticos
# — sem isso, a comparação entre famílias mediria também diferença de texto.
#
# NÃO HÁ MAIS `alpha`/`fit_prior` AQUI, e a remoção é deliberada. Eles são
# parâmetros do `MultinomialNB`; com o produto deixando de ser Naive Bayes,
# continuar aceitando-os faria `ajuste_fino.py` passar valores que o estimador
# padrão ignoraria em silêncio — uma busca inteira medindo sempre a mesma
# coisa, sem erro nenhum. Quem quer Naive Bayes agora o entrega construído.
def construir_classificador(
    config_pre: ConfigPreprocessamento = CONFIG_PRE_PADRAO,
    config_vet: ConfigVetorizacao = CONFIG_VET_PADRAO,
    estimador=None,
) -> Pipeline:
    if estimador is None:
        estimador = CalibratedClassifierCV(
            LinearSVC(C=C_PADRAO, random_state=SEMENTE), method="sigmoid", cv=3
        )
    return Pipeline(
        [
            ("preprocessamento", PreprocessadorDeTexto(config_pre)),
            ("vetorizador", construir_vetorizador(config_vet)),
            ("classificador", estimador),
        ]
    )


def carregar_dataset(caminho: Path) -> tuple[list[str], list[str]]:
    with caminho.open(encoding="utf-8", newline="") as arquivo:
        linhas = list(csv.DictReader(arquivo))
    return [linha["texto"] for linha in linhas], [linha["intencao"] for linha in linhas]


# Avalia um modelo pronto e devolve o relatório por classe, não confundir com
# `experimento.medir_configuracao`, que mede uma configuração.
def avaliar_classificador(
    textos: list[str], rotulos: list[str], modelo: Pipeline, k: int = 5
) -> tuple[float, str, list[list[int]], list[str]]:
    dobras = StratifiedKFold(n_splits=k, shuffle=True, random_state=SEMENTE)
    preditos = cross_val_predict(modelo, textos, rotulos, cv=dobras)

    classes = sorted(set(rotulos))
    return (
        f1_score(rotulos, preditos, average="macro"),
        classification_report(rotulos, preditos, digits=3, zero_division=0),
        confusion_matrix(rotulos, preditos, labels=classes).tolist(),
        classes,
    )


# O peso por termo e classe, na forma que cada família expõe.
#
# DUAS FAMÍLIAS, DUAS CONTAS DIFERENTES, e confundi-las produz uma lista
# plausível e errada:
#
# `MultinomialNB` guarda `feature_log_prob_`, que é GERATIVO — a probabilidade
# do termo DADA a classe. Ordená-lo cru devolve os termos frequentes do corpus
# inteiro, iguais para todas as classes; é preciso contrastar contra a média
# das demais para isolar o que distingue.
#
# A regressão logística guarda `coef_`, que já é DISCRIMINATIVO: o coeficiente
# mede o quanto o termo empurra PARA aquela classe e contra as outras.
# Contrastá-lo de novo seria subtrair duas vezes.
#
# A função despacha pela capacidade do objeto, e não por `isinstance`: qualquer
# família linear que exponha `coef_` passa a ter explicabilidade sem tocar aqui.
def _pesos_por_classe(classificador) -> np.ndarray:
    coef = getattr(classificador, "coef_", None)
    if coef is not None:
        return np.asarray(coef)

    # `CalibratedClassifierCV` não expõe `coef_`: ele guarda N modelos internos,
    # um por dobra da calibração, cada um com os seus. A MÉDIA entre eles é a
    # leitura honesta — os N foram treinados em partições diferentes do mesmo
    # dado, e nenhum tem primazia sobre os outros.
    #
    # Isto é o custo de explicabilidade da calibração, e ele é real: os pesos
    # deixam de ser "os do modelo" e passam a ser um resumo de N modelos. Para
    # listar termos característicos serve; para auditar uma decisão específica,
    # seria preciso olhar o modelo que a produziu.
    calibrados = getattr(classificador, "calibrated_classifiers_", None)
    if calibrados:
        internos = [
            np.asarray(c.estimator.coef_) for c in calibrados
            if hasattr(getattr(c, "estimator", None), "coef_")
        ]
        if internos:
            return np.mean(internos, axis=0)

    log_prob = classificador.feature_log_prob_
    contrastes = []
    for indice in range(len(log_prob)):
        outras = np.delete(log_prob, indice, axis=0)
        # Com uma classe só não há contraste possível; o peso vira o log-prob cru.
        contrastes.append(log_prob[indice] - (outras.mean(axis=0) if outras.size else 0.0))
    return np.asarray(contrastes)


# Exige o modelo já treinado.
def listar_palavras_de_maior_peso_por_intencao(
    modelo: Pipeline, quantas: int = 8
) -> dict[str, list[tuple[str, float]]]:
    vetorizador = modelo.named_steps["vetorizador"]
    classificador = modelo.named_steps["classificador"]
    termos = vetorizador.get_feature_names_out()
    pesos = _pesos_por_classe(classificador)

    por_classe: dict[str, list[tuple[str, float]]] = {}
    for indice, classe in enumerate(classificador.classes_):
        ordenados = sorted(
            zip(termos, pesos[indice].tolist(), strict=True),
            key=lambda par: par[1], reverse=True,
        )
        por_classe[str(classe)] = ordenados[:quantas]
    return por_classe


# A confiança devolvida ordena bem e calibra mal: serve para comparar frases
# entre si, não como probabilidade de acerto. Um limiar de recusa sobre ela
# precisa ser calibrado empiricamente.
def prever_intencao(modelo: Pipeline, texto: str) -> tuple[str, float]:
    probabilidades = modelo.predict_proba([texto])[0]
    indice = probabilidades.argmax()
    return str(modelo.named_steps["classificador"].classes_[indice]), float(probabilidades[indice])


def salvar_modelo(modelo: Pipeline, caminho: Path) -> None:
    garantir_dir_de_resultados()
    joblib.dump(modelo, caminho)


def carregar_modelo(caminho: Path) -> Pipeline:
    return joblib.load(caminho)


def imprimir_matriz_de_confusao(matriz: list[list[int]], classes: list[str]) -> None:
    largura = max(len(c) for c in classes) + 2
    print("Matriz de confusão: linha = intenção real, coluna = prevista")
    print(" " * largura + "".join(f"{c:>{largura}}" for c in classes))
    for classe, linha in zip(classes, matriz, strict=True):
        print(f"{classe:>{largura}}" + "".join(f"{v:>{largura}}" for v in linha))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Treina e avalia o classificador de intenções.")
    parser.add_argument("--dataset", type=Path, default=DATASET_PADRAO)
    parser.add_argument("--k", type=int, default=5, help="dobras da validação cruzada")
    parser.add_argument("--C", type=float, default=C_PADRAO, dest="c",
                        help="regularização inversa do LinearSVC")
    parser.add_argument("--salvar", type=Path, default=MODELO_PADRAO, help="onde gravar o modelo")
    parser.add_argument("--prever", type=str, default=None, help="classifica uma frase e sai")
    args = parser.parse_args(argv)

    if args.prever is not None:
        if not args.salvar.exists():
            print(f"❌ Modelo não encontrado em {args.salvar}. Treine primeiro:\n"
                  f"    python -m pln.classificador")
            return 1
        intencao, confianca = prever_intencao(carregar_modelo(args.salvar), args.prever)
        print(f"{args.prever!r}\n  -> {intencao}  (confiança {confianca:.1%})")
        return 0

    textos, rotulos = carregar_dataset(args.dataset)
    print(f"Dataset: {args.dataset}  ({len(textos)} exemplos, {len(set(rotulos))} classes)")
    print(f"Pré-processamento: {CONFIG_PRE_PADRAO.descrever()}")
    print(f"Vetorização      : {CONFIG_VET_PADRAO.descrever()}")
    print(f"Classificador    : LinearSVC(C={args.c}) calibrado\n")

    modelo = construir_classificador(
        estimador=CalibratedClassifierCV(
            LinearSVC(C=args.c, random_state=SEMENTE), method="sigmoid", cv=3
        )
    )
    f1, relatorio, matriz, classes = avaliar_classificador(textos, rotulos, modelo, args.k)

    print(f"F1-macro (validação cruzada de {args.k} dobras): {f1:.4f}\n")
    print(relatorio)
    imprimir_matriz_de_confusao(matriz, classes)

    # O modelo que vai a disco é treinado no dataset completo; a avaliação acima
    # já foi feita sem que nenhuma previsão visse o próprio exemplo.
    modelo.fit(textos, rotulos)
    print("\nPalavras que mais distinguem cada intenção")
    for classe, termos in listar_palavras_de_maior_peso_por_intencao(modelo).items():
        print(f"  {classe:>32}: " + ", ".join(termo for termo, _ in termos))

    salvar_modelo(modelo, args.salvar)
    print(f"\nModelo treinado no dataset completo e salvo em {args.salvar}")
    print('Teste: python -m pln.classificador --prever "Quais prazos vencem esta semana?"')
    return 0


if __name__ == "__main__":
    # Delega ao módulo importado em vez de chamar `main()` direto. Sob
    # `python -m pln.classificador`, este arquivo é carregado como `__main__`, e
    # o pickle do modelo gravaria `PreprocessadorDeTexto` com esse caminho,
    # tornando o `.joblib` carregável só de dentro do próprio CLI.
    from pln.classificador import main as main_do_modulo

    raise SystemExit(main_do_modulo())
