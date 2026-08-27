# Classificador de intenções — o modelo do produto.
#
# O pipeline é um único objeto do sklearn (texto bruto -> pré-processamento ->
# vetorização -> MultinomialNB), o que impede treinar com um pré-processamento e
# prever com outro.
#
# O classificador é o mesmo que `experimento.py` usa como régua. Isso é decisão:
# o pré-processamento é escolhido medindo com ele, então trocá-lo aqui faria a
# escolha do texto ter sido feita para um modelo que não é o que roda.

from __future__ import annotations

import argparse
import csv
from pathlib import Path

import joblib
import numpy as np
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.metrics import classification_report, confusion_matrix, f1_score
from sklearn.model_selection import StratifiedKFold, cross_val_predict
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import Pipeline

from pln.caminhos import DATASET_PADRAO, MODELO_PADRAO, garantir_dir_de_resultados
from pln.preprocessamento import (
    ConfigPreprocessamento,
    ModoMorfologia,
    Tokenizacao,
    preprocessar,
)
from pln.vetorizacao import ConfigVetorizacao, ModoVetorizacao, construir_vetorizador

SEMENTE = 42

# Vencedores das duas buscas medidas, válidos para o dataset em `dados/`. Trocar
# o dataset os invalida; regerar exige os dois comandos, nesta ordem:
#
#     python -m pln.experimento  --dataset seus_dados.csv   # os dois primeiros
#     python -m pln.ajuste_fino  --dataset seus_dados.csv   # os dois últimos
#
# A tokenização vai explícita para registrar a escolha em vez de herdá-la do
# padrão da dataclass.
CONFIG_PRE_PADRAO = ConfigPreprocessamento(
    remover_numeros=True, morfologia=ModoMorfologia.STEMMING, tokenizacao=Tokenizacao.REGEX
)
CONFIG_VET_PADRAO = ConfigVetorizacao(ModoVetorizacao.BOW, n_max=1)
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


def construir_classificador(
    config_pre: ConfigPreprocessamento = CONFIG_PRE_PADRAO,
    config_vet: ConfigVetorizacao = CONFIG_VET_PADRAO,
    alpha: float = ALPHA_PADRAO,
    fit_prior: bool = FIT_PRIOR_PADRAO,
) -> Pipeline:
    return Pipeline(
        [
            ("preprocessamento", PreprocessadorDeTexto(config_pre)),
            ("vetorizador", construir_vetorizador(config_vet)),
            ("classificador", MultinomialNB(alpha=alpha, fit_prior=fit_prior)),
        ]
    )


def carregar_dataset(caminho: Path) -> tuple[list[str], list[str]]:
    with caminho.open(encoding="utf-8", newline="") as arquivo:
        linhas = list(csv.DictReader(arquivo))
    return [linha["texto"] for linha in linhas], [linha["intencao"] for linha in linhas]


# Avalia um modelo pronto e devolve o relatório por classe — não confundir com
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


# Exige o modelo já treinado.
#
# Ordenar `feature_log_prob_` cru daria a mesma lista para todas as classes, por
# ser dominado pelos termos frequentes do corpus. O contraste contra a média das
# demais classes é o que isola os termos característicos.
#
def listar_palavras_de_maior_peso_por_intencao(
    modelo: Pipeline, quantas: int = 8
) -> dict[str, list[tuple[str, float]]]:
    vetorizador = modelo.named_steps["vetorizador"]
    classificador = modelo.named_steps["classificador"]
    termos = vetorizador.get_feature_names_out()
    log_prob = classificador.feature_log_prob_

    por_classe: dict[str, list[tuple[str, float]]] = {}
    for indice, classe in enumerate(classificador.classes_):
        outras = np.delete(log_prob, indice, axis=0)
        # Com uma classe só não há contraste possível; o peso vira o log-prob cru.
        contraste = log_prob[indice] - (outras.mean(axis=0) if outras.size else 0.0)
        ordenados = sorted(
            zip(termos, contraste.tolist(), strict=True), key=lambda par: par[1], reverse=True
        )
        por_classe[str(classe)] = ordenados[:quantas]
    return por_classe


# A confiança devolvida ordena bem e calibra mal — serve para comparar frases
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
    print("Matriz de confusão — linha = intenção real, coluna = prevista")
    print(" " * largura + "".join(f"{c:>{largura}}" for c in classes))
    for classe, linha in zip(classes, matriz, strict=True):
        print(f"{classe:>{largura}}" + "".join(f"{v:>{largura}}" for v in linha))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Treina e avalia o classificador de intenções.")
    parser.add_argument("--dataset", type=Path, default=DATASET_PADRAO)
    parser.add_argument("--k", type=int, default=5, help="dobras da validação cruzada")
    parser.add_argument("--alpha", type=float, default=ALPHA_PADRAO,
                        help="suavização de Laplace/Lidstone")
    parser.add_argument("--sem-priori", action="store_true",
                        help="usa probabilidades a priori uniformes em vez das do treino")
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

    fit_prior = not args.sem_priori
    textos, rotulos = carregar_dataset(args.dataset)
    print(f"Dataset: {args.dataset}  ({len(textos)} exemplos, {len(set(rotulos))} classes)")
    print(f"Pré-processamento: {CONFIG_PRE_PADRAO.descrever()}")
    print(f"Vetorização      : {CONFIG_VET_PADRAO.descrever()}")
    print(f"Classificador    : MultinomialNB(alpha={args.alpha}, fit_prior={fit_prior})\n")

    modelo = construir_classificador(alpha=args.alpha, fit_prior=fit_prior)
    f1, relatorio, matriz, classes = avaliar_classificador(textos, rotulos, modelo, args.k)

    print(f"F1-macro (validação cruzada de {args.k} dobras): {f1:.4f}\n")
    print(relatorio)
    imprimir_matriz_de_confusao(matriz, classes)

    # O modelo que vai a disco é treinado no dataset completo; a avaliação acima
    # já foi feita sem que nenhuma previsão visse o próprio exemplo.
    modelo.fit(textos, rotulos)
    print("\nPalavras que mais distinguem cada intenção")
    for classe, termos in listar_palavras_de_maior_peso_por_intencao(modelo).items():
        print(f"  {classe:>10}: " + ", ".join(termo for termo, _ in termos))

    salvar_modelo(modelo, args.salvar)
    print(f"\nModelo treinado no dataset completo e salvo em {args.salvar}")
    print('Teste: python -m pln.classificador --prever "Quais prazos vencem esta semana?"')
    return 0


if __name__ == "__main__":
    # Delega ao módulo importado em vez de chamar `main()` direto. Sob
    # `python -m pln.classificador`, este arquivo é carregado como `__main__`, e
    # o pickle do modelo gravaria `PreprocessadorDeTexto` com esse caminho —
    # tornando o `.joblib` carregável só de dentro do próprio CLI.
    from pln.classificador import main as main_do_modulo

    raise SystemExit(main_do_modulo())
