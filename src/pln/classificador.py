# =============================================================================
# classificador.py — Classificador de intenções com Naive Bayes
# =============================================================================
# Este é o MODELO DO PRODUTO.
#
# DE ONDE VÊM OS PADRÕES — E O QUE AINDA NÃO FOI MEDIDO
# -----------------------------------------------------
# `CONFIG_PRE_PADRAO` e `CONFIG_VET_PADRAO` saíram da varredura exaustiva de
# `experimento.py`, registrada em `resultados/comparativo_preprocessamento.md`.
#
# LEIA A RESSALVA ANTES DE CONFIAR NESSES DOIS. No dataset de exemplo atual, a
# varredura devolve F1-macro 1,0000 com desvio 0,0000 — e não devolve isso para
# a vencedora, devolve para 2261 das 6456 configurações avaliadas. A medição não
# está errada; ela está SATURADA, e uma medição saturada não ordena nada.
#
# A causa está no dataset, não no pipeline: são 300 frases geradas por gabarito,
# com apenas 16 primeiras palavras distintas entre elas, e 77% dos exemplos são
# decididos pela primeira palavra sozinha. A validação cruzada acaba colocando
# frases quase idênticas no treino e no teste ao mesmo tempo, e todo mundo
# acerta tudo. Com 20 exemplos por classe o F1 já é 0,9366; os outros 80 por
# classe não acrescentam dificuldade, só repetição.
#
# Consequência prática: entre as 2261 empatadas, o critério que sobrou foi
# SIMPLICIDADE — a configuração que não faz nada com o texto vence porque
# nenhuma etapa se mostrou capaz de melhorar o que já está em 1,0000. É uma
# escolha defensável (não manter etapa que não paga por si), mas é diferente de
# "esta é a melhor forma de preparar o texto". Para o experimento voltar a
# discriminar, o dataset precisa de frases que ele erre — redação livre, não
# gabarito. Ver a seção de ressalvas em docs/PipelinePLN.md.
#
# `VARIANTE_PADRAO`, `ALPHA_PADRAO` e `FIT_PRIOR_PADRAO` vêm de OUTRA medição, e
# precisam vir: `experimento.py` varre pré-processamento e vetorização com o
# classificador FIXO em `MultinomialNB(alpha=1.0)` — ele nunca comparou
# variantes de Naive Bayes nem valores de suavização. Quem faz isso é
# `ajuste_fino.py`, e o resultado está em `resultados/ajuste_fino.md`:
#
#     python -m pln.ajuste_fino
#
# Na última rodada, 3000 candidatos, `multinomial` levou por 0,0011 sobre
# `bernoulli` e 0,0042 sobre `complement`; a suavização mal se moveu entre 0,01 e
# 1,0 e só piorou em 2,0; e `fit_prior` não fez NENHUMA diferença — coerente com
# as três classes do dataset terem exatamente o mesmo tamanho.
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
#   confirma a si mesmo. Continua valendo como comparação RELATIVA entre
#   pré-processamentos, que é para o que ele serve.
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
from sklearn.naive_bayes import BernoulliNB, ComplementNB, GaussianNB, MultinomialNB
from sklearn.pipeline import Pipeline

from pln.caminhos import DATASET_PADRAO, MODELO_PADRAO, garantir_dir_de_resultados
from pln.preprocessamento import ConfigPreprocessamento, Tokenizacao, preprocessar
from pln.vetorizacao import ConfigVetorizacao, ModoVetorizacao, construir_vetorizador

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
    # normalmente apareceria. Em frases curtas isso costuma vencer, e chegou a
    # ser o padrão daqui por esse argumento. `ajuste_fino.py` mediu e ele ficou
    # em SEGUNDO, atrás de `multinomial` por 0,0011 — o argumento era plausível
    # e o número não o confirmou.

    # GAUSSIANO: assume COORDENADA CONTÍNUA. Modela cada dimensão como uma
    # normal dentro de cada classe, estimando média e variância. É a única das
    # quatro que aceita valor negativo — e por isso a única compatível com a
    # vetorização por embeddings, cujos vetores são posições num espaço centrado
    # na origem. Em contrapartida, é péssima em matriz esparsa de contagem:
    # milhares de colunas quase sempre zero não têm distribuição normal nenhuma.

    MULTINOMIAL = "multinomial"
    COMPLEMENT = "complement"
    BERNOULLI = "bernoulli"
    GAUSSIANO = "gaussiano"


_CLASSES_NB = {
    VarianteNB.MULTINOMIAL: MultinomialNB,
    VarianteNB.COMPLEMENT: ComplementNB,
    VarianteNB.BERNOULLI: BernoulliNB,
    VarianteNB.GAUSSIANO: GaussianNB,
}

# As três primeiras contam ocorrência e exigem entrada não-negativa; a última
# lê coordenada contínua e exige entrada densa. A escolha não é livre: ela é
# determinada pela vetorização, e combinar errado não é questão de gosto, é erro.
VARIANTES_PARA_ESPARSO: tuple[VarianteNB, ...] = (
    VarianteNB.MULTINOMIAL,
    VarianteNB.COMPLEMENT,
    VarianteNB.BERNOULLI,
)
VARIANTES_PARA_DENSO: tuple[VarianteNB, ...] = (VarianteNB.GAUSSIANO,)


# Quais variantes fazem sentido para uma dada vetorização.
#
# Usada pelo ajuste fino para não gastar avaliação em combinação impossível, e
# por `construir_classificador` para recusar a combinação com uma mensagem que
# diz o que fazer — em vez do `ValueError: Negative values in data` cru do
# scikit-learn, que não menciona nem embeddings nem Naive Bayes.
def variantes_compativeis(config_vet: ConfigVetorizacao) -> tuple[VarianteNB, ...]:
    return VARIANTES_PARA_DENSO if config_vet.produz_vetores_densos() else VARIANTES_PARA_ESPARSO


# GaussianNB não tem `alpha` nem `fit_prior` — os equivalentes são
# `var_smoothing` e `priors`, com semântica diferente. Passar os parâmetros
# errados levantaria TypeError, então cada família recebe os seus.
def construir_estimador_nb(variante: VarianteNB, alpha: float, fit_prior: bool):
    if variante is VarianteNB.GAUSSIANO:
        # `alpha` entra como `var_smoothing`. Os dois são regularização — uma
        # quantidade somada antes de o número virar probabilidade — mas NÃO são
        # intercambiáveis em escala: `alpha` útil vive perto de 1, e
        # `var_smoothing` tem padrão 1e-9. Passar 1.0 aqui não é "suavizar
        # bastante", é achatar a variância de todas as dimensões e destruir o
        # modelo.
        #
        # Quem varre precisa usar uma grade por variante. `ajuste_fino.py` tem
        # `GRADE_ALPHA` e `GRADE_VAR_SMOOTHING` separadas exatamente por isso.
        return GaussianNB(var_smoothing=alpha)
    return _CLASSES_NB[variante](alpha=alpha, fit_prior=fit_prior)

# -----------------------------------------------------------------------------
# Os padrões
# -----------------------------------------------------------------------------
# ATENÇÃO — estes valores valem para O DATASET DE EXEMPLO. Trocar o dataset os
# invalida, e o conserto são dois comandos, nesta ordem:
#
#     python -m pln.experimento  --dataset seus_dados.csv   # os dois primeiros
#     python -m pln.ajuste_fino  --dataset seus_dados.csv   # os três últimos
#
# Nenhum deles se edita a olho: cada um é o vencedor de uma busca medida, e o
# segundo comando lê o relatório do primeiro.
#
# `ConfigPreprocessamento()` sem argumento nenhum é o texto CRU: nenhuma das seis
# etapas ligada. Está escrito com a tokenização explícita, e não pelos padrões da
# dataclass, porque aqui isso é uma decisão registrada — não uma omissão.
CONFIG_PRE_PADRAO = ConfigPreprocessamento(tokenizacao=Tokenizacao.SPLIT)
CONFIG_VET_PADRAO = ConfigVetorizacao(ModoVetorizacao.BOW, n_max=1)
VARIANTE_PADRAO = VarianteNB.MULTINOMIAL
ALPHA_PADRAO = 1.0
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
    compativeis = variantes_compativeis(config_vet)
    if variante not in compativeis:
        densa = config_vet.produz_vetores_densos()
        raise ValueError(
            f"`{variante.value}` não pode ser usado com a vetorização `{config_vet.descrever()}`.\n"
            f"  Ela produz vetores {'densos com valores negativos' if densa else 'esparsos de contagem'}, "
            f"e as variantes compatíveis são: {', '.join(v.value for v in compativeis)}.\n"
            f"  Ver a explicação em `VarianteNB`."
        )

    return Pipeline(
        [
            ("preprocessamento", PreprocessadorDeTexto(config_pre)),
            ("vetorizador", construir_vetorizador(config_vet)),
            ("classificador", construir_estimador_nb(variante, alpha, fit_prior)),
        ]
    )


def carregar_dataset(caminho: Path) -> tuple[list[str], list[str]]:
    with caminho.open(encoding="utf-8", newline="") as arquivo:
        linhas = list(csv.DictReader(arquivo))
    return [linha["texto"] for linha in linhas], [linha["intencao"] for linha in linhas]


# Avalia por validação cruzada e devolve (F1-macro, relatório, matriz, classes).
#
# O nome diz "classificador" para não colidir com `experimento.medir_configuracao`,
# que também faz validação cruzada mas responde outra pergunta: aquela mede UMA
# CONFIGURAÇÃO e devolve F1 médio e desvio; esta avalia UM MODELO PRONTO e devolve
# o relatório por classe. Os dois já se chamaram `avaliar_com_validacao_cruzada`, e
# juntar os arquivos fazia um sobrescrever o outro em silêncio.
#
# Usa `cross_val_predict`, que devolve, para cada exemplo, a previsão feita
# quando ele estava FORA do treino. Isso permite montar um relatório por classe
# e uma matriz de confusão sobre o dataset inteiro, sem que nenhuma previsão
# tenha visto o próprio exemplo durante o treino.
#
# Por que não avaliar sobre o treino: o modelo acerta quase tudo no que já viu.
# A nota de treino mede memória, não capacidade de generalizar.
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
    parser.add_argument("--variante", type=VarianteNB, choices=list(VarianteNB),
                        default=VARIANTE_PADRAO, help="variante de Naive Bayes")
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
    print(f"Classificador    : {_CLASSES_NB[args.variante].__name__}"
          f"(alpha={args.alpha}, fit_prior={fit_prior})\n")

    modelo = construir_classificador(variante=args.variante, alpha=args.alpha, fit_prior=fit_prior)
    f1, relatorio, matriz, classes = avaliar_classificador(textos, rotulos, modelo, args.k)

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
    print('Teste: python -m pln.classificador --prever "Quais prazos vencem esta semana?"')
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
