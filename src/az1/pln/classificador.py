# =============================================================================
# classificador.py — Classificador de intenções com regressão logística
# =============================================================================
# Este é o MODELO DO PRODUTO. O MultinomialNB de vetorizacao.py é outra coisa:
# a régua do experimento, escolhida por ser determinística e rápida, porque
# roda milhares de vezes.
#
# Por que regressão logística:
#
# - Devolve PROBABILIDADE, não só o rótulo. O AZ1 precisa poder responder "não
#   entendi bem o que você quis dizer" em vez de chutar uma intenção, e isso
#   exige um número de confiança comparável entre classes. Naive Bayes também
#   expõe `predict_proba`, mas seus valores são notoriamente mal calibrados —
#   saturam perto de 0 e 1 mesmo quando o modelo está incerto.
#
# - Os pesos são interpretáveis. Cada palavra tem um coeficiente por classe, e
#   dá para mostrar quais palavras levaram a cada decisão. Em um produto de
#   apoio à decisão do PMO isso não é luxo: é o que permite justificar uma
#   classificação a quem for auditá-la.
#
# - Não assume independência entre palavras. Naive Bayes assume, e por isso
#   lida mal com termos que sempre aparecem juntos — "material rodante",
#   "estrutura analítica" — contando a mesma evidência duas vezes.
#
# O pipeline completo é um único objeto do scikit-learn:
#
#     texto bruto -> PreprocessadorDeTexto -> Vetorizador -> LogisticRegression
#
# Isso importa na prática: treinar, avaliar, salvar e prever passam a operar
# sobre TEXTO BRUTO. Não existe a possibilidade de alguém treinar com um
# pré-processamento e prever com outro — o erro mais comum e mais difícil de
# diagnosticar em PLN, porque não levanta exceção nenhuma: o modelo
# simplesmente erra mais.
# =============================================================================

from __future__ import annotations

import argparse
import csv
from pathlib import Path

import joblib
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, confusion_matrix, f1_score
from sklearn.model_selection import StratifiedKFold, cross_val_predict
from sklearn.pipeline import Pipeline

from az1.pln.preprocessamento import ConfigPreprocessamento, Tokenizacao, preprocessar
from az1.pln.vetorizacao import ConfigVetorizacao, ModoVetorizacao, construir_vetorizador

DATASET_PADRAO = Path(__file__).resolve().parent / "dados" / "intencoes_exemplo.csv"
MODELO_PADRAO = Path(__file__).resolve().parent / "resultados" / "classificador.joblib"

SEMENTE = 42

# Configuração vinda do experimento (ver docs/PipelinePLN.md).
#
# ATENÇÃO — estes valores foram escolhidos medindo com Naive Bayes como régua,
# sobre o dataset de exemplo. Duas coisas os invalidam: trocar o dataset, e a
# possibilidade de a regressão logística preferir outro pré-processamento. O
# caminho rigoroso é rodar o experimento de novo com este classificador no
# lugar da régua. Enquanto isso não é feito, estes são o melhor palpite
# disponível — e são um palpite medido, não uma escolha arbitrária.
CONFIG_PRE_PADRAO = ConfigPreprocessamento(tokenizacao=Tokenizacao.REGEX)
CONFIG_VET_PADRAO = ConfigVetorizacao(ModoVetorizacao.BOW, n_max=1)


# Adapta `preprocessar` à interface de transformador do scikit-learn.
#
# Com isto, o pré-processamento vira uma etapa do Pipeline em vez de um passo
# solto que alguém precisa lembrar de aplicar. O ganho é que o objeto salvo em
# disco carrega a própria configuração: quem carregar o modelo depois não tem
# como aplicar outra por engano.
class PreprocessadorDeTexto(BaseEstimator, TransformerMixin):
    # A configuração fica em `self.config` sem nenhuma alteração, e não em um
    # atributo derivado. É exigência do `clone()`, que a validação cruzada usa
    # para criar uma cópia limpa a cada dobra: ele reconstrói o objeto a partir
    # dos parâmetros do `__init__`, e qualquer processamento feito ali se perde.
    def __init__(self, config: ConfigPreprocessamento = CONFIG_PRE_PADRAO) -> None:
        self.config = config

    # Não faz nada porque o pré-processamento não aprende nada dos dados — é
    # uma transformação determinística. Ainda assim precisa existir e devolver
    # `self`, que é o contrato do scikit-learn.
    def fit(self, X, y=None):  # noqa: N803 — nomes exigidos pela interface do sklearn
        return self

    def transform(self, X):  # noqa: N803
        return [preprocessar(texto, self.config) for texto in X]


# Monta o pipeline completo: texto bruto -> intenção.
#
# Sobre os parâmetros da regressão logística:
#
# - `C` é o inverso da força de regularização. Valor ALTO deixa o modelo livre
#   para se ajustar aos dados de treino (e decorar); valor BAIXO o força a
#   soluções mais simples. Com vocabulário grande e poucos exemplos —
#   exatamente o nosso caso — regularizar importa muito, porque há mais
#   palavras do que frases e o modelo consegue decorar o treino inteiro.
#
# - `class_weight="balanced"` compensa classes de tamanhos diferentes, pesando
#   cada uma pelo inverso da sua frequência. No dataset de exemplo as três
#   classes têm o mesmo tamanho e o efeito é nulo; fica ligado porque o dataset
#   real dificilmente será equilibrado, e sem isso a classe rara seria
#   sacrificada em favor da comum.
#
# - `max_iter=1000` em vez do padrão 100. Com matrizes esparsas de texto o
#   otimizador costuma não convergir em 100 iterações e o scikit-learn emite um
#   aviso — que na prática significa "o modelo parou antes de terminar".
#
# - `random_state` fixo pela mesma razão da semente do experimento: resultado
#   reproduzível entre execuções.
def construir_classificador(
    config_pre: ConfigPreprocessamento = CONFIG_PRE_PADRAO,
    config_vet: ConfigVetorizacao = CONFIG_VET_PADRAO,
    C: float = 1.0,  # noqa: N803 — `C` é o nome do parâmetro no scikit-learn
    class_weight: str | None = "balanced",
) -> Pipeline:
    return Pipeline(
        [
            ("preprocessamento", PreprocessadorDeTexto(config_pre)),
            ("vetorizador", construir_vetorizador(config_vet)),
            (
                "classificador",
                LogisticRegression(
                    C=C,
                    class_weight=class_weight,
                    max_iter=1000,
                    random_state=SEMENTE,
                ),
            ),
        ]
    )


def carregar_dataset(caminho: Path) -> tuple[list[str], list[str]]:
    with caminho.open(encoding="utf-8", newline="") as arquivo:
        linhas = list(csv.DictReader(arquivo))
    return [linha["texto"] for linha in linhas], [linha["intencao"] for linha in linhas]


# Avalia por validação cruzada e devolve (F1-macro, relatório, matriz, classes).
#
# Usa `cross_val_predict`, que devolve, para cada exemplo, a previsão feita
# quando ele estava FORA do treino. Isso permite montar um relatório por classe
# e uma matriz de confusão sobre o dataset inteiro, sem que nenhuma previsão
# tenha visto o próprio exemplo durante o treino.
#
# Por que não avaliar sobre o treino: o modelo acerta quase tudo no que já viu.
# A nota de treino mede memória, não capacidade de generalizar.
def avaliar_com_validacao_cruzada(
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


# As palavras de maior peso para cada intenção. Exige o modelo já treinado.
#
# Cada termo do vocabulário tem um coeficiente por classe. Coeficiente alto
# significa que a presença daquele termo empurra a decisão para aquela classe.
# Listar os maiores é a forma mais direta de auditar o modelo — e costuma
# revelar problemas do dataset antes de qualquer métrica: se uma intenção
# estiver sendo decidida por uma palavra que só aparece por acaso nos exemplos
# daquela classe, aparece aqui.
def listar_palavras_de_maior_peso_por_intencao(
    modelo: Pipeline, quantas: int = 8
) -> dict[str, list[tuple[str, float]]]:
    vetorizador = modelo.named_steps["vetorizador"]
    classificador = modelo.named_steps["classificador"]
    termos = vetorizador.get_feature_names_out()

    por_classe: dict[str, list[tuple[str, float]]] = {}
    for indice, classe in enumerate(classificador.classes_):
        pesos = classificador.coef_[indice]
        ordenados = sorted(zip(termos, pesos, strict=True), key=lambda par: par[1], reverse=True)
        por_classe[classe] = ordenados[:quantas]
    return por_classe


# Devolve (intenção, confiança) para um texto.
#
# A confiança é a probabilidade da classe escolhida. Ela é o que permite ao
# agente recusar-se a responder: abaixo de um limiar acordado, o caminho
# correto é pedir reformulação, não entregar a intenção mais provável como se
# fosse certeza.
#
# RESSALVA — a confiança NÃO resolve o caso fora do catálogo. Um modelo que
# conhece três classes é obrigado a escolher uma delas, e pode fazê-lo com
# convicção alta para uma pergunta sem relação nenhuma com o portfólio. Só o
# dataset resolve isso, com exemplos rotulados da categoria fora do catálogo.
def prever_intencao(modelo: Pipeline, texto: str) -> tuple[str, float]:
    probabilidades = modelo.predict_proba([texto])[0]
    indice = probabilidades.argmax()
    return modelo.named_steps["classificador"].classes_[indice], float(probabilidades[indice])


def salvar_modelo(modelo: Pipeline, caminho: Path) -> None:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(modelo, caminho)


def carregar_modelo(caminho: Path) -> Pipeline:
    return joblib.load(caminho)


def imprimir_matriz_de_confusao(matriz: list[list[int]], classes: list[str]) -> None:
    largura = max(len(c) for c in classes) + 2
    print("Matriz de confusão — linha = intenção real, coluna = prevista")
    print(" " * largura + "".join(f"{c:>{largura}}" for c in classes))
    for classe, linha in zip(classes, matriz, strict=True):
        print(f"{classe:>{largura}}" + "".join(f"{v:>{largura}}" for v in linha))


def main() -> int:
    parser = argparse.ArgumentParser(description="Treina e avalia o classificador de intenções.")
    parser.add_argument("--dataset", type=Path, default=DATASET_PADRAO)
    parser.add_argument("--k", type=int, default=5, help="dobras da validação cruzada")
    parser.add_argument("--C", type=float, default=1.0, help="inverso da regularização")
    parser.add_argument("--salvar", type=Path, default=MODELO_PADRAO, help="onde gravar o modelo")
    parser.add_argument("--prever", type=str, default=None, help="classifica uma frase e sai")
    args = parser.parse_args()

    if args.prever is not None:
        if not args.salvar.exists():
            print(f"❌ Modelo não encontrado em {args.salvar}. Treine primeiro:\n"
                  f"    python -m az1.pln.classificador")
            return 1
        intencao, confianca = prever_intencao(carregar_modelo(args.salvar), args.prever)
        print(f"{args.prever!r}\n  -> {intencao}  (confiança {confianca:.1%})")
        return 0

    textos, rotulos = carregar_dataset(args.dataset)
    print(f"Dataset: {args.dataset}  ({len(textos)} exemplos, {len(set(rotulos))} classes)")
    print(f"Pré-processamento: {CONFIG_PRE_PADRAO.descrever()}")
    print(f"Vetorização      : {CONFIG_VET_PADRAO.descrever()}")
    print(f"Classificador    : LogisticRegression(C={args.C}, class_weight='balanced')\n")

    modelo = construir_classificador(C=args.C)
    f1, relatorio, matriz, classes = avaliar_com_validacao_cruzada(textos, rotulos, modelo, args.k)

    print(f"F1-macro (validação cruzada de {args.k} dobras): {f1:.4f}\n")
    print(relatorio)
    imprimir_matriz_de_confusao(matriz, classes)

    # Treina no dataset completo para salvar. A avaliação acima já foi feita
    # sem que nenhuma previsão visse o próprio exemplo; aqui o objetivo é
    # aproveitar todos os dados disponíveis no modelo que vai a disco.
    modelo.fit(textos, rotulos)
    print("\nPalavras de maior peso por intenção")
    for classe, termos in listar_palavras_de_maior_peso_por_intencao(modelo).items():
        print(f"  {classe:>10}: " + ", ".join(termo for termo, _ in termos))

    salvar_modelo(modelo, args.salvar)
    print(f"\nModelo treinado no dataset completo e salvo em {args.salvar}")
    print('Teste: python -m az1.pln.classificador --prever "Quais prazos vencem esta semana?"')
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
