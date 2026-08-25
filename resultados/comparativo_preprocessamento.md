# Comparativo de pré-processamento e vetorização

- Dataset: `intencoes_exemplos.csv`
- Validação cruzada estratificada de 5 dobras, semente 42
- Classificador fixo: `MultinomialNB(alpha=1.0)` — régua de medição, não o modelo final

## Varredura exaustiva — pré-processamento x vetorização

Produto cartesiano completo: cada pré-processamento contra as 5 vetorizações.
Permutações de ordem examinadas: 19767. Execuções distintas: 8070.

### Efeito de cada etapa booleana

| etapa | com | sem | efeito |
|---|---|---|---|
| remover_numeros | 0.9529 | 0.9417 | +0.0112 |
| remover_acentos | 0.9473 | 0.9508 | -0.0036 |
| minusculas | 0.9468 | 0.9513 | -0.0045 |
| remover_pontuacao | 0.9401 | 0.9614 | -0.0213 |

### Stopwords

Comparação **pareada** em 720 configurações idênticas nas demais escolhas.

| opção | F1 médio | vs manter |
|---|---|---|
| manter | 0.9716 | +0.0000 |
| remover_tudo | 0.9459 | -0.0257 |
| preservar_negacoes | 0.9467 | -0.0249 |

### Morfologia

Comparação **pareada** em 720 configurações idênticas nas demais escolhas.

| opção | F1 médio | vs nenhuma |
|---|---|---|
| nenhuma | 0.9579 | +0.0000 |
| stemming | 0.9514 | -0.0065 |
| lematizacao | 0.9550 | -0.0028 |

### Tokenizacao

Comparação **pareada** em 720 configurações idênticas nas demais escolhas.

| opção | F1 médio | vs split |
|---|---|---|
| split | 0.9550 | +0.0000 |
| regex | 0.9547 | -0.0003 |
| linguistico | 0.9547 | -0.0003 |

### A ordem importa?

- Grupos em que a ordem muda o texto: **1280 de 2160**
- Amplitude média de F1 nesses grupos: **0.0116**
- Amplitude máxima: **0.0965**
- Ordem padrão foi a melhor em **698/1280 (55%)** dos grupos

### Efeito da vetorização

Comparação **pareada** em 1614 pré-processamentos: cada um foi
avaliado sob as 5 vetorizações, e é esse conjunto que se compara entre si.

| escolha | com | sem | efeito |
|---|---|---|---|
| tfidf (vs bow) | 0.9839 | 0.9776 | +0.0063 |
| bigrama (vs só uni) | 0.9837 | 0.9779 | +0.0058 |
| embedding (vs esparsas) | 0.8192 | 0.9808 | -0.1616 |

### Ranking (top 30)

| # | F1-macro | ±dp | vocab | vetorização | pré-processamento |
|---|---|---|---|---|---|
| 1 | 1.0000 | 0.0000 | 141 | bow n=1 | [tok:split] (texto cru) |
| 2 | 1.0000 | 0.0000 | 382 | bow n=1-2 | [tok:split] (texto cru) |
| 3 | 1.0000 | 0.0000 | 141 | tfidf n=1 | [tok:split] (texto cru) |
| 4 | 1.0000 | 0.0000 | 382 | tfidf n=1-2 | [tok:split] (texto cru) |
| 5 | 1.0000 | 0.0000 | 368 | bow n=1-2 | [tok:regex] (texto cru) |
| 6 | 1.0000 | 0.0000 | 122 | tfidf n=1 | [tok:regex] (texto cru) |
| 7 | 1.0000 | 0.0000 | 368 | tfidf n=1-2 | [tok:regex] (texto cru) |
| 8 | 1.0000 | 0.0000 | 368 | bow n=1-2 | [tok:linguistico] (texto cru) |
| 9 | 1.0000 | 0.0000 | 122 | tfidf n=1 | [tok:linguistico] (texto cru) |
| 10 | 1.0000 | 0.0000 | 368 | tfidf n=1-2 | [tok:linguistico] (texto cru) |
| 11 | 1.0000 | 0.0000 | 131 | bow n=1 | [tok:split] stemming |
| 12 | 1.0000 | 0.0000 | 370 | bow n=1-2 | [tok:split] stemming |
| 13 | 1.0000 | 0.0000 | 131 | tfidf n=1 | [tok:split] stemming |
| 14 | 1.0000 | 0.0000 | 370 | tfidf n=1-2 | [tok:split] stemming |
| 15 | 1.0000 | 0.0000 | 111 | bow n=1 | [tok:regex] stemming |
| 16 | 1.0000 | 0.0000 | 355 | bow n=1-2 | [tok:regex] stemming |
| 17 | 1.0000 | 0.0000 | 111 | tfidf n=1 | [tok:regex] stemming |
| 18 | 1.0000 | 0.0000 | 355 | tfidf n=1-2 | [tok:regex] stemming |
| 19 | 1.0000 | 0.0000 | 111 | bow n=1 | [tok:linguistico] stemming |
| 20 | 1.0000 | 0.0000 | 355 | bow n=1-2 | [tok:linguistico] stemming |
| 21 | 1.0000 | 0.0000 | 111 | tfidf n=1 | [tok:linguistico] stemming |
| 22 | 1.0000 | 0.0000 | 355 | tfidf n=1-2 | [tok:linguistico] stemming |
| 23 | 1.0000 | 0.0000 | 108 | bow n=1 | [tok:split] lematizacao |
| 24 | 1.0000 | 0.0000 | 326 | bow n=1-2 | [tok:split] lematizacao |
| 25 | 1.0000 | 0.0000 | 108 | tfidf n=1 | [tok:split] lematizacao |
| 26 | 1.0000 | 0.0000 | 326 | tfidf n=1-2 | [tok:split] lematizacao |
| 27 | 1.0000 | 0.0000 | 108 | bow n=1 | [tok:regex] lematizacao |
| 28 | 1.0000 | 0.0000 | 326 | bow n=1-2 | [tok:regex] lematizacao |
| 29 | 1.0000 | 0.0000 | 108 | tfidf n=1 | [tok:regex] lematizacao |
| 30 | 1.0000 | 0.0000 | 326 | tfidf n=1-2 | [tok:regex] lematizacao |