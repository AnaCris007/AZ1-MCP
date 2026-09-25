# Comparativo de pré-processamento e vetorização

- Dataset: `intencoes_exemplos.csv`
- Validação cruzada estratificada de 5 dobras, semente 42
- Régua fixa: `MultinomialNB(alpha=1.0)`, instrumento de medida, não o modelo final
- A MESMA régua nas quatro vetorizações, que são todas esparsas: é o que torna a comparação entre elas identificável

## Varredura exaustiva — pré-processamento x vetorização

Produto cartesiano completo: cada pré-processamento contra as 4 vetorizações.
Permutações de ordem examinadas: 19767. Execuções distintas: 11884.

### Efeito de cada etapa booleana

| etapa | com | sem | efeito |
|---|---|---|---|
| minusculas | 0.7104 | 0.7070 | +0.0034 |
| remover_acentos | 0.7098 | 0.7070 | +0.0028 |
| remover_numeros | 0.7091 | 0.7090 | +0.0001 |
| remover_pontuacao | 0.7050 | 0.7191 | -0.0141 |

### Stopwords

Comparação **pareada** em 576 configurações idênticas nas demais escolhas.

| opção | F1 médio | vs manter |
|---|---|---|
| manter | 0.7652 | +0.0000 |
| remover_tudo | 0.7061 | -0.0591 |
| preservar_negacoes | 0.7114 | -0.0538 |

### Morfologia

Comparação **pareada** em 576 configurações idênticas nas demais escolhas.

| opção | F1 médio | vs nenhuma |
|---|---|---|
| nenhuma | 0.7318 | +0.0000 |
| stemming | 0.7289 | -0.0029 |
| lematizacao | 0.7221 | -0.0096 |

### Tokenizacao

Comparação **pareada** em 576 configurações idênticas nas demais escolhas.

| opção | F1 médio | vs split |
|---|---|---|
| split | 0.7209 | +0.0000 |
| regex | 0.7312 | +0.0103 |
| linguistico | 0.7307 | +0.0098 |

### A ordem importa?

- Grupos em que a ordem muda o texto: **1332 de 1728**
- Amplitude média de F1 nesses grupos: **0.0191**
- Amplitude máxima: **0.0714**
- Ordem padrão foi a melhor em **481/1332 (36%)** dos grupos

### Efeito da vetorização

Comparação **pareada** em 2971 pré-processamentos: cada um foi
avaliado sob as 4 vetorizações, e é esse conjunto que se compara entre si.

| escolha | com | sem | efeito |
|---|---|---|---|
| tfidf (vs bow) | 0.7199 | 0.6982 | +0.0217 |
| bigrama (vs só uni) | 0.7085 | 0.7096 | -0.0011 |

### Ranking (top 30)

| # | F1-macro | ±dp | vocab | vetorização | pré-processamento |
|---|---|---|---|---|---|
| 1 | 0.8131 | 0.0203 | 4506 | tfidf n=1-2 | [tok:linguistico] remover_acentos > remover_numeros |
| 2 | 0.8116 | 0.0173 | 4605 | tfidf n=1-2 | [tok:regex] remover_numeros |
| 3 | 0.8089 | 0.0256 | 4426 | tfidf n=1-2 | [tok:regex] minusculas > remover_acentos |
| 4 | 0.8087 | 0.0182 | 4409 | tfidf n=1-2 | [tok:linguistico] minusculas > remover_acentos |
| 5 | 0.8076 | 0.0156 | 4658 | tfidf n=1-2 | [tok:regex] (texto cru) |
| 6 | 0.8075 | 0.0124 | 4475 | tfidf n=1-2 | [tok:regex] minusculas > remover_numeros |
| 7 | 0.8071 | 0.0092 | 4514 | tfidf n=1-2 | [tok:regex] remover_acentos > remover_numeros |
| 8 | 0.8068 | 0.0080 | 3906 | tfidf n=1-2 | [tok:linguistico] remover_numeros > stemming |
| 9 | 0.8068 | 0.0080 | 3906 | tfidf n=1-2 | [tok:linguistico] minusculas > remover_numeros > stemming |
| 10 | 0.8050 | 0.0127 | 3896 | tfidf n=1-2 | [tok:regex] stemming > remover_acentos |
| 11 | 0.8050 | 0.0127 | 3896 | tfidf n=1-2 | [tok:regex] minusculas > stemming > remover_acentos |
| 12 | 0.8043 | 0.0327 | 3839 | tfidf n=1-2 | [tok:linguistico] remover_numeros > stemming > remover_acentos |
| 13 | 0.8043 | 0.0327 | 3839 | tfidf n=1-2 | [tok:linguistico] minusculas > remover_numeros > stemming > remover_acentos |
| 14 | 0.8041 | 0.0189 | 4367 | tfidf n=1-2 | [tok:linguistico] minusculas > remover_acentos > remover_numeros |
| 15 | 0.8035 | 0.0129 | 3913 | tfidf n=1-2 | [tok:regex] remover_numeros > stemming |
| 16 | 0.8035 | 0.0129 | 3913 | tfidf n=1-2 | [tok:regex] minusculas > remover_numeros > stemming |
| 17 | 0.8030 | 0.0244 | 3870 | tfidf n=1-2 | [tok:linguistico] remover_acentos > remover_numeros > stemming |
| 18 | 0.8030 | 0.0244 | 3870 | tfidf n=1-2 | [tok:linguistico] minusculas > remover_acentos > remover_numeros > stemming |
| 19 | 0.8022 | 0.0181 | 3493 | tfidf n=1-2 | [tok:split] remover_acentos > remover_pontuacao > remover_numeros > stemming |
| 20 | 0.8022 | 0.0181 | 3493 | tfidf n=1-2 | [tok:regex] remover_acentos > remover_pontuacao > remover_numeros > stemming |
| 21 | 0.8022 | 0.0181 | 3493 | tfidf n=1-2 | [tok:linguistico] remover_acentos > remover_pontuacao > remover_numeros > stemming |
| 22 | 0.8022 | 0.0181 | 3493 | tfidf n=1-2 | [tok:split] minusculas > remover_acentos > remover_pontuacao > remover_numeros > stemming |
| 23 | 0.8022 | 0.0181 | 3493 | tfidf n=1-2 | [tok:regex] minusculas > remover_acentos > remover_pontuacao > remover_numeros > stemming |
| 24 | 0.8022 | 0.0181 | 3493 | tfidf n=1-2 | [tok:linguistico] minusculas > remover_acentos > remover_pontuacao > remover_numeros > stemming |
| 25 | 0.8018 | 0.0120 | 4375 | tfidf n=1-2 | [tok:regex] minusculas > remover_acentos > remover_numeros |
| 26 | 0.8018 | 0.0159 | 4597 | tfidf n=1-2 | [tok:linguistico] remover_numeros |
| 27 | 0.8016 | 0.0266 | 3831 | tfidf n=1-2 | [tok:regex] minusculas > remover_acentos > remover_numeros > lematizacao |
| 28 | 0.8016 | 0.0266 | 3831 | tfidf n=1-2 | [tok:regex] minusculas > remover_acentos > lematizacao > remover_numeros |
| 29 | 0.8014 | 0.0347 | 3913 | tfidf n=1-2 | [tok:linguistico] remover_acentos > stemming |
| 30 | 0.8014 | 0.0347 | 3913 | tfidf n=1-2 | [tok:linguistico] minusculas > remover_acentos > stemming |