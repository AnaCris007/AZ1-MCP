# pln/

Pipeline de linguagem natural: prepara o texto e classifica a intenção da solicitação.

Arquitetura, decisões e resultados dos experimentos estão em
[docs/Projeto.md § 3.3](../../docs/Projeto.md#33-algoritmo-de-nlp-e-implementação).

| Arquivo | Papel |
|---|---|
| `caminhos.py` | caminhos de entrada e saída |
| `preprocessamento.py` | texto para tokens |
| `vetorizacao.py` | tokens para matriz numérica |
| `classificador.py` | o modelo do produto |
| `intencao.py` | o contrato da fronteira: detecção e regra de rejeição |
| `particao.py` | separa o pool em desenvolvimento e teste retido |
| `experimento.py` | busca do texto: pré-processamento × vetorização |
| `ajuste_fino.py` | busca dos parâmetros: suavização × priori × vetorização |
| `comparativo_modelos.py` | compara famílias, cada uma no melhor texto DELA |
| `metricas.py` | as três métricas do RNF03, a curva do limiar e o teste retido |
| `bancada.py` | latência, tempo de treino e pico de memória |
| `dados/` | datasets rotulados (colunas `texto`, `intencao`) |

## Produto e régua deixaram de ser o mesmo modelo

Até a Sprint 3 o `MultinomialNB` era os dois, e isso era apresentado como condição de validade:
o pré-processamento é escolhido medindo com um classificador fixo, então um produto diferente
herdaria uma escolha de texto feita para outro.

A busca de três estágios desfez o argumento ao medir cada família sobre o **seu próprio** melhor
texto. Medido assim, o `MultinomialNB` ficou em último de quatro e falha em dois dos três limites
do RNF03 no conjunto retido; o `LinearSVC` calibrado atende aos três e separa-se das outras três
em teste pareado de 50 medições.

| Papel | Modelo | Por quê |
|---|---|---|
| **Produto** | `CalibratedClassifierCV(LinearSVC, C=1.0)` | vence a comparação e atende ao RNF03 no retido |
| **Régua do estágio 1** | `MultinomialNB(alpha=1.0)` | 0,05 s por validação cruzada contra 21,69 s da regressão logística — é o que torna 11.884 execuções praticáveis |

O custo da separação está declarado: o `LinearSVC` não expõe `predict_proba`, vive embrulhado em
`CalibratedClassifierCV`, e isso cobra 6x em latência de inferência, enterra os pesos por termo
em três modelos internos e exige ao menos 3 exemplos por classe em cada dobra de treino.

Saídas geradas vão para `resultados/`, na raiz do repositório.

## Os três arquivos de dados

```
dados/intencoes_pool.csv       <- AUTORAL: todos os exemplos, editado à mão
dados/intencoes_exemplos.csv   <- GERADO: desenvolvimento (treino, busca, ajuste, calibração)
dados/intencoes_teste.csv      <- GERADO: teste retido, lido uma vez só
```

São arquivos separados, e não uma coluna `particao` num CSV único, de propósito: assim
`experimento.py`, `ajuste_fino.py` e `bancada.py` ficam **incapazes** de enxergar o teste, em vez
de apenas instruídos a não enxergá-lo.

A atribuição é por hash do próprio texto, e não por embaralhamento com semente. Um `shuffle`
semeado é reprodutível, mas não sobrevive ao crescimento do corpus: acrescentar frases recalcula
o sorteio, e exemplos migram do teste para o desenvolvimento — onde o modelo da rodada anterior
já foi ajustado sobre eles. Com hash, acrescentar nunca move quem já existe.

> **O teste retido não é o conjunto cego da Seção 6.3.** Aquele exige frases novas, escritas
> depois e custodiadas por quem não participou do ajuste. Este mede generalização com honestidade
> e não substitui a medição cega.

## Instalação

```bash
pip install -e .
python -m nltk.downloader stopwords rslp
python -m spacy download pt_core_news_sm
```

## Uso

```bash
python -m pln.classificador                                       # treina, avalia e salva
python -m pln.classificador --prever "Quais prazos vencem hoje?"  # usa o modelo salvo
```

Ao trocar ou ampliar o pool, a sequência inteira precisa ser refeita **nesta ordem** — cada
comando consome o que o anterior grava:

```bash
python -m pln.particao          # regera desenvolvimento e teste retido

# Estágio 1 — UMA varredura exaustiva POR FAMÍLIA, cada uma como régua de si
# mesma. Sem isso, as demais herdam o ranking do Naive Bayes e a comparação
# favorece quem o produziu. A saída é sufixada pela régua.
python -m pln.experimento --regua multinomialnb        # ~20 min
python -m pln.experimento --regua linearsvc            # ~15 min
python -m pln.experimento --regua sgd                  # ~5 min
python -m pln.experimento --regua logisticregression   # ~2h30, 45.240 parâmetros

python -m pln.ajuste_fino       # suavização e priori DA RÉGUA, não do produto
#   (colar os valores recomendados nas constantes de classificador.py — passo manual)
python -m pln.classificador     # treina e salva o modelo
python -m pln.metricas          # RNF03 no desenvolvimento, com a curva do limiar
python -m pln.metricas --teste  # RNF03 no teste retido, UMA vez
# Estágios 2 e 3, pares dois a dois e confirmação no retido
python -m pln.comparativo_modelos --confirmar-no-retido
python -m pln.bancada
```

Colar os valores recomendados nos padrões de `classificador.py` é passo manual de propósito: é a
única etapa em que alguém decide, e automatizá-la esconderia a decisão.

## A regra de rejeição mora num lugar só

`intencao.py` define `aplicar_limiar` e `LIMIAR_PADRAO`, e é **a mesma função** que `metricas.py`
usa para medir e que a API usa para decidir. Antes ela existia em quatro versões que não
concordavam — o relatório do RNF03 descrevia uma regra que o serviço não aplicava.

```python
from pln.intencao import DetectarIntencao

detector = DetectarIntencao(modelo)
deteccao = detector("o que precisa da minha atenção?")

deteccao.prevista    # o argmax cru do modelo, o que vai para a trilha de auditoria
deteccao.rejeitada   # confiança abaixo do limiar calibrado
deteccao.intencao    # já com a regra aplicada
```

`prevista` e `intencao` são separados porque o sistema precisa das duas leituras: *"o modelo disse
`fora_do_catalogo` com confiança"* leva à recusa do RF02, enquanto *"o modelo não teve confiança"*
deixa o RAG responder.

## Testes

```bash
python -m unittest discover tests
```
