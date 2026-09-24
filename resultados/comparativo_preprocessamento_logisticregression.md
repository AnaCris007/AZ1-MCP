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
| remover_acentos | 0.7085 | 0.7050 | +0.0034 |
| minusculas | 0.7082 | 0.7066 | +0.0016 |
| remover_numeros | 0.7069 | 0.7087 | -0.0018 |
| remover_pontuacao | 0.7037 | 0.7171 | -0.0134 |

### Stopwords

Comparação **pareada** em 576 configurações idênticas nas demais escolhas.

| opção | F1 médio | vs manter |
|---|---|---|
| manter | 0.7751 | +0.0000 |
| remover_tudo | 0.7040 | -0.0711 |
| preservar_negacoes | 0.7053 | -0.0698 |

### Morfologia

Comparação **pareada** em 576 configurações idênticas nas demais escolhas.

| opção | F1 médio | vs nenhuma |
|---|---|---|
| nenhuma | 0.7298 | +0.0000 |
| stemming | 0.7333 | +0.0035 |
| lematizacao | 0.7213 | -0.0085 |

### Tokenizacao

Comparação **pareada** em 576 configurações idênticas nas demais escolhas.

| opção | F1 médio | vs split |
|---|---|---|
| split | 0.7214 | +0.0000 |
| regex | 0.7321 | +0.0107 |
| linguistico | 0.7309 | +0.0095 |

### A ordem importa?

- Grupos em que a ordem muda o texto: **1332 de 1728**
- Amplitude média de F1 nesses grupos: **0.0107**
- Amplitude máxima: **0.0429**
- Ordem padrão foi a melhor em **493/1332 (37%)** dos grupos

### Efeito da vetorização

Comparação **pareada** em 2971 pré-processamentos: cada um foi
avaliado sob as 4 vetorizações, e é esse conjunto que se compara entre si.

| escolha | com | sem | efeito |
|---|---|---|---|
| bigrama (vs só uni) | 0.6978 | 0.7173 | -0.0195 |
| tfidf (vs bow) | 0.6939 | 0.7213 | -0.0274 |

### Ranking (top 30)

| # | F1-macro | ±dp | vocab | vetorização | pré-processamento |
|---|---|---|---|---|---|
| 1 | 0.8047 | 0.0160 | 3845 | bow n=1-2 | [tok:regex] remover_numeros > stemming > remover_acentos |
| 2 | 0.8047 | 0.0160 | 3845 | bow n=1-2 | [tok:regex] minusculas > remover_numeros > stemming > remover_acentos |
| 3 | 0.8046 | 0.0049 | 3430 | bow n=1-2 | [tok:split] minusculas > remover_acentos > remover_pontuacao > remover_numeros > lematizacao |
| 4 | 0.8046 | 0.0049 | 3430 | bow n=1-2 | [tok:split] minusculas > remover_acentos > remover_pontuacao > lematizacao > remover_numeros |
| 5 | 0.8046 | 0.0049 | 3430 | bow n=1-2 | [tok:regex] minusculas > remover_acentos > remover_pontuacao > remover_numeros > lematizacao |
| 6 | 0.8046 | 0.0049 | 3430 | bow n=1-2 | [tok:regex] minusculas > remover_acentos > remover_pontuacao > lematizacao > remover_numeros |
| 7 | 0.8046 | 0.0049 | 3430 | bow n=1-2 | [tok:linguistico] minusculas > remover_acentos > remover_pontuacao > remover_numeros > lematizacao |
| 8 | 0.8046 | 0.0049 | 3430 | bow n=1-2 | [tok:linguistico] minusculas > remover_acentos > remover_pontuacao > lematizacao > remover_numeros |
| 9 | 0.8046 | 0.0288 | 1055 | bow n=1 | [tok:split] minusculas > remover_acentos > remover_pontuacao > remover_numeros |
| 10 | 0.8046 | 0.0288 | 1055 | bow n=1 | [tok:regex] minusculas > remover_acentos > remover_pontuacao > remover_numeros |
| 11 | 0.8046 | 0.0288 | 1055 | bow n=1 | [tok:linguistico] minusculas > remover_acentos > remover_pontuacao > remover_numeros |
| 12 | 0.8040 | 0.0145 | 3913 | bow n=1-2 | [tok:regex] remover_numeros > stemming |
| 13 | 0.8040 | 0.0145 | 3913 | bow n=1-2 | [tok:regex] minusculas > remover_numeros > stemming |
| 14 | 0.8040 | 0.0189 | 3839 | bow n=1-2 | [tok:linguistico] remover_numeros > stemming > remover_acentos |
| 15 | 0.8040 | 0.0189 | 3839 | bow n=1-2 | [tok:linguistico] minusculas > remover_numeros > stemming > remover_acentos |
| 16 | 0.8036 | 0.0160 | 3965 | bow n=1-2 | [tok:regex] stemming |
| 17 | 0.8036 | 0.0160 | 3965 | bow n=1-2 | [tok:regex] minusculas > stemming |
| 18 | 0.8036 | 0.0290 | 1073 | bow n=1 | [tok:split] minusculas > remover_acentos > remover_pontuacao |
| 19 | 0.8036 | 0.0290 | 1073 | bow n=1 | [tok:regex] minusculas > remover_acentos > remover_pontuacao |
| 20 | 0.8036 | 0.0290 | 1073 | bow n=1 | [tok:linguistico] minusculas > remover_acentos > remover_pontuacao |
| 21 | 0.8033 | 0.0281 | 1096 | bow n=1 | [tok:split] minusculas > remover_pontuacao > remover_numeros |
| 22 | 0.8033 | 0.0281 | 1096 | bow n=1 | [tok:regex] minusculas > remover_pontuacao > remover_numeros |
| 23 | 0.8033 | 0.0281 | 1096 | bow n=1 | [tok:linguistico] minusculas > remover_pontuacao > remover_numeros |
| 24 | 0.8027 | 0.0160 | 3876 | bow n=1-2 | [tok:regex] remover_acentos > remover_numeros > stemming |
| 25 | 0.8027 | 0.0160 | 3876 | bow n=1-2 | [tok:regex] minusculas > remover_acentos > remover_numeros > stemming |
| 26 | 0.8025 | 0.0296 | 1114 | bow n=1 | [tok:split] minusculas > remover_pontuacao |
| 27 | 0.8025 | 0.0296 | 1114 | bow n=1 | [tok:regex] minusculas > remover_pontuacao |
| 28 | 0.8025 | 0.0296 | 1114 | bow n=1 | [tok:linguistico] minusculas > remover_pontuacao |
| 29 | 0.8025 | 0.0114 | 3896 | bow n=1-2 | [tok:regex] stemming > remover_acentos |
| 30 | 0.8025 | 0.0114 | 3896 | bow n=1-2 | [tok:regex] minusculas > stemming > remover_acentos |