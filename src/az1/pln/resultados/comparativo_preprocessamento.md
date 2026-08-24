# Comparativo de pré-processamento e vetorização

- Dataset: `intencoes_exemplo.csv`
- Validação cruzada estratificada de 5 dobras, semente 42
- Classificador fixo: `MultinomialNB(alpha=1.0)` — régua de medição, não o modelo final

## Varredura exaustiva — pré-processamento x vetorização

Produto cartesiano completo: cada pré-processamento contra as 4 vetorizações.
Permutações de ordem examinadas: 19767. Execuções distintas: 8248.

### Efeito de cada etapa booleana

| etapa | com | sem | efeito |
|---|---|---|---|
| remover_numeros | 0.6652 | 0.6501 | +0.0151 |
| minusculas | 0.6619 | 0.6520 | +0.0099 |
| remover_acentos | 0.6554 | 0.6660 | -0.0105 |
| remover_pontuacao | 0.6293 | 0.7145 | -0.0851 |

### Stopwords

Comparação **pareada** em 576 configurações idênticas nas demais escolhas.

| opção | F1 médio | vs manter |
|---|---|---|
| manter | 0.7519 | +0.0000 |
| remover_tudo | 0.6388 | -0.1131 |
| preservar_negacoes | 0.6768 | -0.0751 |

### Morfologia

Comparação **pareada** em 576 configurações idênticas nas demais escolhas.

| opção | F1 médio | vs nenhuma |
|---|---|---|
| nenhuma | 0.6806 | +0.0000 |
| stemming | 0.6897 | +0.0091 |
| lematizacao | 0.6972 | +0.0166 |

### Tokenizacao

Comparação **pareada** em 576 configurações idênticas nas demais escolhas.

| opção | F1 médio | vs split |
|---|---|---|
| split | 0.6806 | +0.0000 |
| regex | 0.6934 | +0.0129 |
| linguistico | 0.6935 | +0.0130 |

### A ordem importa?

- Grupos em que a ordem muda o texto: **1240 de 1728**
- Amplitude média de F1 nesses grupos: **0.0366**
- Amplitude máxima: **0.1429**
- Ordem padrão foi a melhor em **620/1240 (50%)** dos grupos

### Efeito da vetorização

Comparação **pareada** em 2062 pré-processamentos: cada um foi
avaliado sob as quatro vetorizações, e é esse quarteto que se compara entre si.

| escolha | com | sem | efeito |
|---|---|---|---|
| tfidf (vs bow) | 0.6524 | 0.6642 | -0.0118 |
| bigrama (vs só uni) | 0.6424 | 0.6742 | -0.0317 |

### Ranking (top 30)

| # | F1-macro | ±dp | vocab | vetorização | pré-processamento |
|---|---|---|---|---|---|
| 1 | 0.8480 | 0.0652 | 280 | bow n=1 | [tok:regex] remover_numeros |
| 2 | 0.8480 | 0.0652 | 280 | bow n=1 | [tok:linguistico] remover_numeros |
| 3 | 0.8480 | 0.0652 | 277 | bow n=1 | [tok:regex] remover_acentos > remover_numeros |
| 4 | 0.8480 | 0.0652 | 277 | bow n=1 | [tok:linguistico] remover_acentos > remover_numeros |
| 5 | 0.8474 | 0.0901 | 284 | bow n=1 | [tok:regex] minusculas |
| 6 | 0.8474 | 0.0901 | 284 | bow n=1 | [tok:linguistico] minusculas |
| 7 | 0.8465 | 0.0919 | 275 | bow n=1 | [tok:regex] minusculas > remover_numeros |
| 8 | 0.8465 | 0.0919 | 275 | bow n=1 | [tok:linguistico] minusculas > remover_numeros |
| 9 | 0.8465 | 0.0919 | 272 | bow n=1 | [tok:regex] minusculas > remover_acentos > remover_numeros |
| 10 | 0.8465 | 0.0919 | 272 | bow n=1 | [tok:linguistico] minusculas > remover_acentos > remover_numeros |
| 11 | 0.8402 | 0.0811 | 289 | bow n=1 | [tok:regex] (texto cru) |
| 12 | 0.8402 | 0.0811 | 289 | bow n=1 | [tok:linguistico] (texto cru) |
| 13 | 0.8402 | 0.0811 | 287 | bow n=1 | [tok:regex] remover_acentos |
| 14 | 0.8402 | 0.0811 | 287 | bow n=1 | [tok:linguistico] remover_acentos |
| 15 | 0.8391 | 0.1073 | 281 | bow n=1 | [tok:regex] minusculas > remover_acentos |
| 16 | 0.8391 | 0.1073 | 281 | bow n=1 | [tok:linguistico] minusculas > remover_acentos |
| 17 | 0.8379 | 0.0985 | 232 | tfidf n=1 | [tok:split] minusculas > lematizacao |
| 18 | 0.8379 | 0.0985 | 232 | tfidf n=1 | [tok:regex] minusculas > lematizacao |
| 19 | 0.8379 | 0.0985 | 232 | tfidf n=1 | [tok:linguistico] minusculas > lematizacao |
| 20 | 0.8379 | 0.0985 | 231 | tfidf n=1 | [tok:split] minusculas > lematizacao > remover_acentos |
| 21 | 0.8379 | 0.0985 | 231 | tfidf n=1 | [tok:regex] minusculas > lematizacao > remover_acentos |
| 22 | 0.8379 | 0.0985 | 231 | tfidf n=1 | [tok:linguistico] minusculas > lematizacao > remover_acentos |
| 23 | 0.8375 | 0.0874 | 242 | bow n=1 | [tok:split] lematizacao |
| 24 | 0.8375 | 0.0874 | 242 | bow n=1 | [tok:regex] lematizacao |
| 25 | 0.8375 | 0.0874 | 242 | bow n=1 | [tok:linguistico] lematizacao |
| 26 | 0.8375 | 0.0874 | 233 | bow n=1 | [tok:split] remover_numeros > lematizacao |
| 27 | 0.8375 | 0.0874 | 233 | bow n=1 | [tok:regex] remover_numeros > lematizacao |
| 28 | 0.8375 | 0.0874 | 233 | bow n=1 | [tok:linguistico] remover_numeros > lematizacao |
| 29 | 0.8375 | 0.0874 | 241 | bow n=1 | [tok:split] lematizacao > remover_acentos |
| 30 | 0.8375 | 0.0874 | 241 | bow n=1 | [tok:regex] lematizacao > remover_acentos |