# =============================================================================
# classificador.py — Classificador de intenções com Naive Bayes
# =============================================================================
# Este é o MODELO DO PRODUTO. Os hiperparâmetros abaixo não foram escolhidos a
# dedo: saíram da busca em `ajuste_fino.py` (ver resultados/ajuste_fino.md).
#
# POR QUE NAIVE BAYES — E O QUE SE PERDEU NA TROCA
# ------------------------------------------------
# Este arquivo usava regressão logística. A troca foi feita por medição, e o
# argumento que sustentava a escolha anterior continua parcialmente de pé; vale
# registrar os dois lados, porque quem mexer aqui depois precisa saber o que
# está sendo trocado por quê.
#
# A FAVOR:
#
# - Mede melhor neste dataset. Com os hiperparâmetros ajustados, 0,8725 de
#   F1-macro contra 0,8443 da regressão logística — mesmas dobras, mesma
#   semente. A diferença é menor que o desvio padrão entre dobras, então o
#   honesto é dizer "não perde", e não "ganha".
#
# - Aprende com pouquíssimo dado. Naive Bayes estima uma contagem por termo e
#   classe; não há otimização iterativa que precise de exemplos suficientes para
#   convergir. Com 120 frases, isso deixou de ser detalhe e virou o argumento
#   principal.
#
# - É determinístico. Sem sorteio interno, sem `random_state`, sem depender de
#   o otimizador ter convergido. Duas execuções dão exatamente o mesmo modelo.
#
# - A régua do experimento passa a ser da mesma família do modelo do produto.
#   `experimento.py` escolheu o pré-processamento medindo com `MultinomialNB`, e
#   a documentação registrava a ressalva de que a regressão logística poderia
#   preferir outro. Essa ressalva morre aqui. A contrapartida é que o
#   experimento deixa de ser um teste independente do produto — ele agora
#   confirma a si mesmo, e é por isso que `ajuste_fino.py` varre o
#   pré-processamento de novo em vez de aceitar o veredito da régua.
#
# CONTRA — o que se perdeu, e continua verdade:
#
# - A CALIBRAÇÃO DA CONFIANÇA PIOROU. Naive Bayes multiplica probabilidades
#   assumindo termos independentes; como não são, a evidência é contada mais de
#   uma vez e o resultado satura perto de 0 e 1. `prever_intencao` continua
#   devolvendo um número entre 0 e 1, mas ele ordena bem e calibra mal: serve
#   para comparar duas frases entre si, não para ser lido como "92% de chance de
#   estar certo". Um limiar de recusa fixado sobre este número vai recusar de
#   menos. Ver a ressalva em `prever_intencao`.
#
# - A suposição de independência continua falsa. Termos que sempre aparecem
#   juntos — "material rodante", "estrutura analítica" — são contados como duas
#   evidências separadas. É o preço do modelo, e não some com ajuste.
#
# O pipeline completo é um único objeto do scikit-learn:
#
#     texto bruto -> PreprocessadorDeTexto -> Vetorizador -> NaiveBayes
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
from enum import StrEnum
from pathlib import Path

import joblib
import numpy as np
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.metrics import classification_report, confusion_matrix, f1_score
from sklearn.model_selection import StratifiedKFold, cross_val_predict
from sklearn.naive_bayes import BernoulliNB, ComplementNB, MultinomialNB
from sklearn.pipeline import Pipeline

from az1.pln.preprocessamento import ConfigPreprocessamento, Tokenizacao, preprocessar
from az1.pln.vetorizacao import ConfigVetorizacao, ModoVetorizacao, construir_vetorizador

DATASET_PADRAO = Path(__file__).resolve().parent / "dados" / "intencoes_exemplo.csv"
MODELO_PADRAO = Path(__file__).resolve().parent / "resultados" / "classificador.joblib"

SEMENTE = 42


class VarianteNB(StrEnum):
    # As três formas de Naive Bayes aplicáveis a texto. Diferem no que assumem
    # sobre a natureza do número que o vetorizador entrega.
    #
    # MULTINOMIAL: assume CONTAGEM. Modela cada classe como um sorteio de
    # palavras com reposição, então um termo que aparece três vezes pesa três
    # vezes mais. É o padrão da área para classificação de texto.
    #
    # COMPLEMENT: mesma mecânica, mas estima os pesos a partir do COMPLEMENTO da
    # classe — de tudo que NÃO é ela. Foi proposto (Rennie et al., 2003) para
    # corrigir o viés do multinomial em favor das classes maiores. Com classes
    # equilibradas a diferença é pequena; com dataset real desequilibrado, é a
    # variante que tende a segurar melhor a classe rara.
    #
    # BERNOULLI: assume PRESENÇA E AUSÊNCIA. Binariza a matriz — só importa se o
    # termo apareceu, não quantas vezes — e, diferente dos outros dois, usa a
    # AUSÊNCIA de um termo como evidência positiva para as classes em que ele
    # normalmente apareceria. Em frases curtas isso costuma vencer, e é o que
    # acontece aqui: nossas intenções são perguntas de uma linha, onde repetição
    # praticamente não ocorre e o que distingue é qual palavra está lá.

    MULTINOMIAL = "multinomial"
    COMPLEMENT = "complement"
    BERNOULLI = "bernoulli"


_CLASSES_NB = {
    VarianteNB.MULTINOMIAL: MultinomialNB,
    VarianteNB.COMPLEMENT: ComplementNB,
    VarianteNB.BERNOULLI: BernoulliNB,
}

# -----------------------------------------------------------------------------
# Os padrões, todos vindos de `ajuste_fino.py`
# -----------------------------------------------------------------------------
# ATENÇÃO — estes valores valem para o dataset de exemplo. Trocar o dataset os
# invalida, e o conserto é uma linha:
#
#     python -m az1.pln.ajuste_fino --dataset seus_dados.csv
#
# Não os edite a olho. Cada um é o vencedor de uma busca medida.
CONFIG_PRE_PADRAO = ConfigPreprocessamento(remover_numeros=True, tokenizacao=Tokenizacao.REGEX)
CONFIG_VET_PADRAO = ConfigVetorizacao(ModoVetorizacao.BOW, n_max=1)
VARIANTE_PADRAO = VarianteNB.BERNOULLI
ALPHA_PADRAO = 0.1
FIT_PRIOR_PADRAO = True


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
# Sobre os parâmetros do Naive Bayes:
#
# - `alpha` é a suavização de Laplace/Lidstone: a contagem fictícia somada a
#   TODO par (termo, classe) antes de virar probabilidade. Sem ela, um termo
#   que nunca apareceu numa classe teria probabilidade zero, e um único zero
#   zera o produto inteiro — uma palavra desconhecida bastaria para eliminar
#   uma intenção, por mais que todo o resto da frase apontasse para ela.
#
#   O valor controla o quanto o modelo confia nas contagens observadas. ALTO
#   puxa tudo para a distribuição uniforme e apaga as diferenças entre classes;
#   BAIXO confia em contagens vistas duas ou três vezes e decora. Com 120
#   frases o ótimo medido ficou em 0,1 — abaixo do padrão 1,0 do scikit-learn,
#   o que é coerente: vocabulário pequeno e frases curtas produzem contagens
#   baixas, que a suavização padrão abafaria.
#
#   É o `alpha` que faz aqui o papel que `C` fazia na regressão logística, com
#   o sentido INVERTIDO: `C` alto = menos regularização, `alpha` alto = mais.
#
# - `fit_prior` decide se as probabilidades a priori das classes são aprendidas
#   da frequência no treino (`True`) ou fixadas em uniformes (`False`).
#   `False` é o análogo mais próximo do `class_weight="balanced"` que a
#   regressão logística usava — Naive Bayes não tem `class_weight`. Fica em
#   `True` porque foi o que mediu melhor e porque as três classes do dataset de
#   exemplo têm o mesmo tamanho, o que torna a escolha quase inócua aqui.
#   Em dataset real desequilibrado, vale medir os dois de novo.
#
# - Não há `random_state`. Naive Bayes é determinístico: nada a semear.
def construir_classificador(
    config_pre: ConfigPreprocessamento = CONFIG_PRE_PADRAO,
    config_vet: ConfigVetorizacao = CONFIG_VET_PADRAO,
    variante: VarianteNB = VARIANTE_PADRAO,
    alpha: float = ALPHA_PADRAO,
    fit_prior: bool = FIT_PRIOR_PADRAO,
) -> Pipeline:
    return Pipeline(
        [
            ("preprocessamento", PreprocessadorDeTexto(config_pre)),
            ("vetorizador", construir_vetorizador(config_vet)),
            ("classificador", _CLASSES_NB[variante](alpha=alpha, fit_prior=fit_prior)),
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


# As palavras que mais distinguem cada intenção. Exige o modelo já treinado.
#
# COMO SE LÊ UM NAIVE BAYES — e por que não basta olhar `feature_log_prob_`
# -------------------------------------------------------------------------
# A regressão logística tinha `coef_`: um peso por termo e classe, já
# centrado, em que positivo significa "empurra para esta classe". Naive Bayes
# não tem isso — e, desde o scikit-learn 1.2, também não tem mais o `coef_` de
# compatibilidade que existiu até a 1.0. O que existe é `feature_log_prob_`,
# que é log P(termo | classe): quão PROVÁVEL o termo é dentro da classe.
#
# Ordenar por esse número cru dá a lista errada. Ele é dominado pelos termos
# mais frequentes do corpus — "de", "do", "projeto" —, que são prováveis em
# TODAS as classes e por isso não distinguem nenhuma. O topo sairia idêntico
# para as três intenções.
#
# O que distingue é o CONTRASTE: o quanto o termo é mais provável nesta classe
# do que nas demais. É a razão de chances em log,
#
#     log P(termo | classe)  -  média de log P(termo | outras classes)
#
# que zera para termos indiferentes e cresce só para os característicos. Isso
# recupera exatamente a leitura que `coef_` dava, e por isso a função mantém o
# nome e o contrato: (termo, peso), do mais característico ao menos.
#
# Sobre as três variantes: `feature_log_prob_` do ComplementNB é estimado sobre
# o complemento da classe, mas o scikit-learn já o armazena NEGADO (`norm=False`,
# o padrão), de modo que "maior = mais indicativo desta classe" vale para as
# três. Se alguém ligar `norm=True`, esse sinal se inverte e esta função passa a
# listar o oposto do pretendido.
#
# Auditar esta lista costuma revelar problemas do dataset antes de qualquer
# métrica: se uma intenção estiver sendo decidida por uma palavra que só
# aparece por acaso nos exemplos daquela classe, aparece aqui.
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


# Devolve (intenção, confiança) para um texto.
#
# RESSALVA IMPORTANTE — A CONFIANÇA DO NAIVE BAYES É MAL CALIBRADA
# -----------------------------------------------------------------
# O número devolvido é `predict_proba` da classe escolhida, entre 0 e 1, e as
# três somam 1. Mas ele NÃO deve ser lido como "chance de estar certo".
#
# Naive Bayes multiplica a probabilidade de cada termo assumindo que são
# independentes. Não são: "prazo" e "vencer" aparecem juntos o tempo todo, e
# cada par correlacionado é contado como se fosse evidência nova. Multiplicar
# dezenas dessas evidências infladas empurra o resultado para os extremos, e a
# saída satura em 0,99 mesmo quando o modelo está em dúvida. A regressão
# logística que este arquivo usava antes calibrava melhor; foi o que se perdeu
# na troca.
#
# O que o número AINDA serve para fazer: ORDENAR. Entre duas frases, a de maior
# confiança é de fato aquela sobre a qual o modelo tem mais evidência. Então um
# limiar de recusa continua utilizável — mas o valor do limiar tem de ser
# calibrado empiricamente sobre dados rotulados, e não escolhido por intuição.
# Um "0,7" pensado para regressão logística aqui não recusa quase nada.
#
# RESSALVA SEPARADA — a confiança não resolve o caso fora do catálogo. Um modelo
# que conhece três classes é obrigado a escolher uma delas, e pode fazê-lo com
# convicção alta para uma pergunta sem relação nenhuma com o portfólio. Só o
# dataset resolve isso, com exemplos rotulados da categoria fora do catálogo.
def prever_intencao(modelo: Pipeline, texto: str) -> tuple[str, float]:
    probabilidades = modelo.predict_proba([texto])[0]
    indice = probabilidades.argmax()
    return str(modelo.named_steps["classificador"].classes_[indice]), float(probabilidades[indice])


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
    parser.add_argument("--variante", type=VarianteNB, choices=list(VarianteNB),
                        default=VARIANTE_PADRAO, help="variante de Naive Bayes")
    parser.add_argument("--alpha", type=float, default=ALPHA_PADRAO,
                        help="suavização de Laplace/Lidstone")
    parser.add_argument("--sem-priori", action="store_true",
                        help="usa probabilidades a priori uniformes em vez das do treino")
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

    fit_prior = not args.sem_priori
    textos, rotulos = carregar_dataset(args.dataset)
    print(f"Dataset: {args.dataset}  ({len(textos)} exemplos, {len(set(rotulos))} classes)")
    print(f"Pré-processamento: {CONFIG_PRE_PADRAO.descrever()}")
    print(f"Vetorização      : {CONFIG_VET_PADRAO.descrever()}")
    print(f"Classificador    : {_CLASSES_NB[args.variante].__name__}"
          f"(alpha={args.alpha}, fit_prior={fit_prior})\n")

    modelo = construir_classificador(variante=args.variante, alpha=args.alpha, fit_prior=fit_prior)
    f1, relatorio, matriz, classes = avaliar_com_validacao_cruzada(textos, rotulos, modelo, args.k)

    print(f"F1-macro (validação cruzada de {args.k} dobras): {f1:.4f}\n")
    print(relatorio)
    imprimir_matriz_de_confusao(matriz, classes)

    # Treina no dataset completo para salvar. A avaliação acima já foi feita
    # sem que nenhuma previsão visse o próprio exemplo; aqui o objetivo é
    # aproveitar todos os dados disponíveis no modelo que vai a disco.
    modelo.fit(textos, rotulos)
    print("\nPalavras que mais distinguem cada intenção")
    for classe, termos in listar_palavras_de_maior_peso_por_intencao(modelo).items():
        print(f"  {classe:>10}: " + ", ".join(termo for termo, _ in termos))

    salvar_modelo(modelo, args.salvar)
    print(f"\nModelo treinado no dataset completo e salvo em {args.salvar}")
    print('Teste: python -m az1.pln.classificador --prever "Quais prazos vencem esta semana?"')
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
