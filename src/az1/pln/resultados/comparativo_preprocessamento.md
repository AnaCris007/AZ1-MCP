# Comparativo de pré-processamento e vetorização

- Dataset: `intencoes_exemplo.csv`
- Validação cruzada estratificada de 5 dobras, semente 42
- Classificador fixo: `MultinomialNB(alpha=1.0)` — régua de medição, não o modelo final

## Varredura exaustiva — pré-processamento x vetorização

Produto cartesiano completo: cada pré-processamento contra as 4 vetorizações.
Permutações de ordem examinadas: 432. Execuções distintas: 1728.

### Efeito de cada etapa booleana

| etapa | com | sem | efeito |
|---|---|---|---|
| minusculas | 0.6946 | 0.6838 | +0.0109 |
| remover_numeros | 0.6941 | 0.6842 | +0.0099 |
| remover_acentos | 0.6871 | 0.6912 | -0.0041 |
| remover_pontuacao | 0.6523 | 0.7261 | -0.0738 |

### Stopwords

Comparação **pareada** em 12 configurações idênticas nas demais escolhas.

| opção | F1 médio | vs manter |
|---|---|---|
| manter | 0.7232 | +0.0000 |
| remover_tudo | 0.5888 | -0.1344 |
| preservar_negacoes | 0.6414 | -0.0818 |

### Morfologia

Comparação **pareada** em 24 configurações idênticas nas demais escolhas.

| opção | F1 médio | vs nenhuma |
|---|---|---|
| nenhuma | 0.6151 | +0.0000 |
| stemming | 0.6351 | +0.0199 |
| lematizacao | 0.6664 | +0.0513 |

### Tokenizacao

Comparação **pareada** em 44 configurações idênticas nas demais escolhas.

| opção | F1 médio | vs split |
|---|---|---|
| split | 0.6898 | +0.0000 |
| regex | 0.6979 | +0.0081 |
| linguistico | 0.6979 | +0.0081 |

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
| 20 | 0.8375 | 0.0874 | 242 | bow n=1 | [tok:split] lematizacao |
| 21 | 0.8375 | 0.0874 | 242 | bow n=1 | [tok:regex] lematizacao |
| 22 | 0.8375 | 0.0874 | 242 | bow n=1 | [tok:linguistico] lematizacao |
| 23 | 0.8375 | 0.0874 | 233 | bow n=1 | [tok:split] remover_numeros > lematizacao |
| 24 | 0.8375 | 0.0874 | 233 | bow n=1 | [tok:regex] remover_numeros > lematizacao |
| 25 | 0.8375 | 0.0874 | 233 | bow n=1 | [tok:linguistico] remover_numeros > lematizacao |
| 26 | 0.8297 | 0.0915 | 223 | tfidf n=1 | [tok:split] minusculas > remover_numeros > lematizacao |
| 27 | 0.8297 | 0.0915 | 223 | tfidf n=1 | [tok:regex] minusculas > remover_numeros > lematizacao |
| 28 | 0.8297 | 0.0915 | 223 | tfidf n=1 | [tok:linguistico] minusculas > remover_numeros > lematizacao |
| 29 | 0.8292 | 0.1002 | 232 | bow n=1 | [tok:split] minusculas > lematizacao |
| 30 | 0.8292 | 0.1002 | 232 | bow n=1 | [tok:regex] minusculas > lematizacao |