# Comparativo de famílias de classificador

Arquivo gerado por `python -m pln.comparativo_modelos`. Não editar à mão.

- Dataset: `intencoes_exemplos.csv` (881 exemplos)
- Validação cruzada estratificada de 5 dobras, semente 42
- Busca conjunta: 4 famílias, **128 medições**
- Cada família lê o ranking de texto **dela própria**, produzido por
  `python -m pln.experimento --regua <familia>` com ela como instrumento de medida.
  Herdar o ranking de uma família favorece quem o produziu.
- Escolher o máximo entre milhares de estimativas de validação cruzada é otimista
  por construção. As quatro pagam esse otimismo igualmente, o que preserva a
  comparação entre elas — mas infla o número absoluto de todas. É o conjunto
  retido que corrige, e por isso `--confirmar-no-retido` existe.
- Limites do RNF03: F1-macro ≥ 0.85, cobertura ≥ 90%, aceitação indevida ≤ 15%

`Melhor limiar` é o ponto de operação que atende aos três limites; quando nenhum
atende, é o que chega mais perto. `Tempo` é o custo da validação cruzada inteira,
não de uma inferência.

| Modelo | F1 sem rejeição | Melhor limiar | F1 | Cobertura | Aceitação indevida | Atende | Tempo |
| --- | ---: | ---: | ---: | ---: | ---: | :---: | ---: |
| LinearSVC calibrado | 0.8244 | 0.00 | 0.8244 | 95.9% | 9.7% | — | 0.9s |
| LogisticRegression | 0.8056 | 0.30 | 0.8090 | 92.4% | 8.4% | — | 1.0s |
| MultinomialNB | 0.7763 | 0.50 | 0.7680 | 89.4% | 14.8% | — | 0.4s |
| SGD modified_huber | 0.8086 | 0.40 | 0.8120 | 93.7% | 14.2% | — | 1.0s |

## Cada família prefere o mesmo texto?

Esta é a pergunta que medir todas sobre uma configuração fixa não responde. O
pré-processamento não é neutro entre famílias de classificador: uma fronteira
discriminativa e uma contagem por classe não pedem o mesmo texto.

| Modelo | Melhor texto encontrado | Hiperparâmetros | F1 | Cobertura | Aceitação indevida |
| --- | --- | --- | ---: | ---: | ---: |
| LinearSVC calibrado | `bow n=1-2 \| [tok:regex] minusculas > remover_acentos > remover_numeros` | padrão | 0.8244 | 95.9% | 9.7% |
| LogisticRegression | `bow n=1 \| [tok:split] minusculas > remover_acentos > remover_pontuacao > remover_numeros` | C=5.0 | 0.8090 | 92.4% | 8.4% |
| MultinomialNB | `bow n=1-2 \| [tok:linguistico] remover_acentos > remover_numeros > stemming` | alpha=2.0, fit_prior=True | 0.7680 | 89.4% | 14.8% |
| SGD modified_huber | `tfidf n=1-2 \| [tok:regex] minusculas > remover_acentos` | padrão | 0.8120 | 93.7% | 14.2% |

**As famílias preferiram 4 textos diferentes.** É a evidência de que medir todas sobre a configuração escolhida pelo `MultinomialNB` daria vantagem indevida a ele: o pré-processamento não é neutro entre famílias, e tratá-lo como constante escondia parte da diferença.

## O que o ajuste de hiperparâmetro mudou

Terceiro estágio: a grade de cada família, sobre o melhor texto dela. Até esta
rodada a comparação media todo mundo em configuração PADRÃO — e o padrão do
scikit-learn é um chute razoável, não o ótimo de cada família. `ajuste_fino.py`
só sabe buscar `alpha` e `fit_prior`, que são do Naive Bayes: o pipeline estava
completo para ele e incompleto para os demais.

| Modelo | Hiperparâmetros | F1 | Cobertura | Aceit. indevida | Distância até o RNF03 |
| --- | --- | ---: | ---: | ---: | ---: |
| LinearSVC calibrado | padrão (a grade não superou) | 0.8244 | 95.9% | 9.7% | 0.030 |
| LogisticRegression | padrão | 0.8064 | 91.3% | 6.5% | 0.051 |
| | **C=5.0** | **0.8090** | **92.4%** | **8.4%** | **0.048** |
| MultinomialNB | padrão | 0.7794 | 87.2% | 12.9% | 0.114 |
| | **alpha=2.0, fit_prior=True** | **0.7680** | **89.4%** | **14.8%** | **0.103** |
| SGD modified_huber | padrão (a grade não superou) | 0.8120 | 93.7% | 14.2% | 0.045 |

A grade mudou a escolha em **2 de 4** famílias. Nas demais, o padrão do scikit-learn já era o melhor ponto da grade — o que é informação, e não ausência de resultado.

**A escolha é pela menor distância até o RNF03, e não pelo maior F1.** Por isso uma família pode aparecer com F1 MENOR depois de ajustada: trocou F1 por cobertura e chegou mais perto de atender aos três limites simultaneamente, que é o que o requisito cobra. Ordenar por F1 sozinho premiaria quem serve menos gente.

## Onde cada família ganha

F1 por intenção, no ponto de operação de cada família — que é o que o sistema de
fato faria. O agregado da tabela acima diz *quanto* uma família ganha; esta diz
*onde*, que é a pergunta que permite decidir se o ganho serve ao requisito.

| Intenção | LinearSVC calibrado | LogisticRegression | MultinomialNB | SGD modified_huber | Melhor |
| --- | ---: | ---: | ---: | ---: | --- |
| `analisar_completude_coerencia` | 0.807 | **0.818** | 0.778 | 0.814 | LogisticRegression |
| `consultar_documentos_normativos` | **0.896** | 0.846 | 0.848 | 0.852 | LinearSVC calibrado |
| `consultar_projeto_sintetico` | 0.762 | **0.778** | 0.757 | 0.729 | LogisticRegression |
| `fora_do_catalogo` | **0.862** | 0.807 | 0.725 | 0.796 | LinearSVC calibrado |
| `gerar_alertas_pendencias` | **0.761** | 0.737 | 0.656 | 0.745 | LinearSVC calibrado |
| `orientar_avanco_mensal` | **0.818** | 0.812 | 0.723 | 0.813 | LinearSVC calibrado |
| `orientar_entregas_cronograma` | 0.849 | 0.840 | 0.763 | **0.852** | SGD modified_huber |
| `orientar_mapa_beneficios` | 0.838 | 0.814 | 0.816 | **0.852** | SGD modified_huber |
| `orientar_riscos_problemas` | 0.816 | 0.813 | 0.827 | **0.831** | SGD modified_huber |
| `orientar_tap` | **0.835** | 0.825 | 0.788 | **0.835** | LinearSVC calibrado |

Placar por intenção: LinearSVC calibrado em 5, SGD modified_huber em 3, LogisticRegression em 2.

A leitura por linha importa mais que o placar. Uma família que vence em muitas intenções fáceis e perde em `fora_do_catalogo` piora a aceitação indevida do RNF03, que é medida só sobre essa classe.

## Todos os pares, dois a dois

Validação cruzada de 10 dobras repetida 5 vezes — 50 medições por família, todas sobre as MESMAS partições.
Cada família foi medida uma vez; os pares saem por aritmética sobre essas notas.

| Par | Diferença média | t | IC 95% | Separáveis? |
| --- | ---: | ---: | --- | :---: |
| `LogisticRegression` − `LinearSVC calibrado` | -0.0208 | -4.871 | [-0.0292, -0.0124] | **sim** |
| `MultinomialNB` − `LinearSVC calibrado` | -0.0453 | -8.861 | [-0.0553, -0.0353] | **sim** |
| `SGD modified_huber` − `LinearSVC calibrado` | -0.0151 | -3.429 | [-0.0238, -0.0065] | **sim** |
| `MultinomialNB` − `LogisticRegression` | -0.0245 | -4.181 | [-0.0359, -0.0130] | **sim** |
| `SGD modified_huber` − `LogisticRegression` | +0.0057 | +1.385 | [-0.0024, +0.0137] | não |
| `SGD modified_huber` − `MultinomialNB` | +0.0301 | +5.942 | [+0.0202, +0.0401] | **sim** |

**5 de 6** pares se separam a 5%. Um par que NÃO se separa não autoriza dizer que uma das duas é melhor — só que esta amostra não conseguiu distingui-las, que é coisa diferente de serem iguais.

## Os dois primeiros estão mesmo separados?

Ordenar não é separar. `LinearSVC calibrado` aparece à frente de `SGD modified_huber` na tabela,
mas a diferença pode ser efeito real ou sorteio das dobras — e trocar o modelo do
produto por um terceiro decimal que não se sustenta seria o pior dos dois erros.

Validação cruzada de 10 dobras REPETIDA 5 vezes com partições
diferentes — 50 comparações, e as MESMAS partições para os dois modelos. O
pareamento cancela a variação entre dobras, que é grande, e deixa só a diferença.

A repetição não é zelo: com 10 dobras apenas, esta mesma comparação devolveu
t = 1,502 e foi lida como empate. Poucas medições produzem 'não detectei', que não
é 'são iguais' — e as duas leituras levam a decisões opostas.

| | `SGD modified_huber` | `LinearSVC calibrado` | Diferença |
| --- | ---: | ---: | ---: |
| média das 50 medições | 0.8120 | 0.8272 | **+0.0151** |
| desvio | 0.0466 | 0.0403 | 0.0312 |

`LinearSVC calibrado` venceu em **33 de 50**. Teste t pareado: **t = 3.429** com 49 graus de liberdade. Intervalo de 95% da diferença: **[+0.0065, +0.0238]**.

**A diferença é significativa a 5%, e o intervalo não inclui zero.** `LinearSVC calibrado` separa-se de `SGD modified_huber` de forma que não se explica por sorteio de partições.

A consequência é direta: **o desempate por critério de engenharia deixa de ser legítimo aqui**. Latência e simplicidade de manutenção decidem entre modelos equivalentes; diante de uma diferença medida, escolher o de baixo é escolher o pior de propósito. Se o custo de engenharia do vencedor for inaceitável, isso precisa ser argumentado como tal, e não disfarçado de empate técnico.

## Confirmação no teste retido

Cada família treinada no desenvolvimento inteiro e medida **uma única vez** no
conjunto retido, com o limiar congelado do desenvolvimento. Os números da tabela
acima são otimistas por construção — escolhem o máximo entre milhares de
estimativas —, e é aqui que se vê quanto desse otimismo sobrevive.

| Modelo | Limiar | F1 | Cobertura | Aceit. indevida | Atende aos 3 |
| --- | ---: | ---: | ---: | ---: | :---: |
| LinearSVC calibrado | 0.00 | 0.8735 | 96.0% | 8.2% | **sim** |
| SGD modified_huber | 0.40 | 0.8774 | 96.0% | 16.3% | — |
| LogisticRegression | 0.30 | 0.8710 | 94.3% | 10.2% | **sim** |
| MultinomialNB | 0.50 | 0.8084 | 89.1% | 8.2% | — |

Retido: 223 exemplos, dos quais 49 de `fora_do_catalogo`.

**Atende aos três limites do RNF03 no retido:** LinearSVC calibrado, LogisticRegression.

Atender aqui não é o mesmo que cumprir o requisito. O conjunto retido é uma
separação interna do corpus, feita pela mesma equipe que o escreveu; a Seção 6.3
exige frases novas e custodiadas por quem não participa do ajuste. Além disso,
com pouco mais de duzentos exemplos o intervalo de confiança do F1 é largo —
a estimativa pontual pode passar de 0,85 com o intervalo incluindo valores que
não passam.

## Leitura

**A referência continua sendo a melhor.** Nenhuma das famílias testadas chega
mais perto do RNF03 que o `MultinomialNB` sobre este corpus, então não há troca
a considerar e a Seção 3.3.2 segue válida como está.

A varredura de `experimento.py` não muda de régua em nenhum cenário: são milhares de medições, e é a velocidade do `MultinomialNB` que as torna praticáveis. O número exato de execuções desta rodada está em `comparativo_preprocessamento.md`.

## Por que cada candidato entrou

- **LinearSVC calibrado** — referência: é o modelo em produção desde a Sprint 3
- **LogisticRegression** — venceu o comparativo da Sprint 3 e foi o produto por uma rodada
- **MultinomialNB** — linha de base histórica: foi o produto até a Sprint 3, e segue sendo a régua
- **SGD modified_huber** — probabilidade nativa com custo de treino baixo

