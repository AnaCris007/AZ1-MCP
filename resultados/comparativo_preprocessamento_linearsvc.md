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
| remover_acentos | 0.7481 | 0.7446 | +0.0035 |
| minusculas | 0.7476 | 0.7466 | +0.0010 |
| remover_numeros | 0.7467 | 0.7479 | -0.0012 |
| remover_pontuacao | 0.7448 | 0.7531 | -0.0083 |

### Stopwords

Comparação **pareada** em 576 configurações idênticas nas demais escolhas.

| opção | F1 médio | vs manter |
|---|---|---|
| manter | 0.7986 | +0.0000 |
| remover_tudo | 0.7429 | -0.0557 |
| preservar_negacoes | 0.7455 | -0.0531 |

### Morfologia

Comparação **pareada** em 576 configurações idênticas nas demais escolhas.

| opção | F1 médio | vs nenhuma |
|---|---|---|
| nenhuma | 0.7645 | +0.0000 |
| stemming | 0.7672 | +0.0027 |
| lematizacao | 0.7552 | -0.0093 |

### Tokenizacao

Comparação **pareada** em 576 configurações idênticas nas demais escolhas.

| opção | F1 médio | vs split |
|---|---|---|
| split | 0.7561 | +0.0000 |
| regex | 0.7661 | +0.0099 |
| linguistico | 0.7648 | +0.0086 |

### A ordem importa?

- Grupos em que a ordem muda o texto: **1332 de 1728**
- Amplitude média de F1 nesses grupos: **0.0112**
- Amplitude máxima: **0.0472**
- Ordem padrão foi a melhor em **440/1332 (33%)** dos grupos

### Efeito da vetorização

Comparação **pareada** em 2971 pré-processamentos: cada um foi
avaliado sob as 4 vetorizações, e é esse conjunto que se compara entre si.

| escolha | com | sem | efeito |
|---|---|---|---|
| tfidf (vs bow) | 0.7450 | 0.7493 | -0.0043 |
| bigrama (vs só uni) | 0.7421 | 0.7523 | -0.0102 |

### Ranking (top 30)

| # | F1-macro | ±dp | vocab | vetorização | pré-processamento |
|---|---|---|---|---|---|
| 1 | 0.8236 | 0.0206 | 4375 | bow n=1-2 | [tok:regex] minusculas > remover_acentos > remover_numeros |
| 2 | 0.8222 | 0.0129 | 3845 | bow n=1-2 | [tok:regex] remover_numeros > stemming > remover_acentos |
| 3 | 0.8222 | 0.0129 | 3845 | bow n=1-2 | [tok:regex] minusculas > remover_numeros > stemming > remover_acentos |
| 4 | 0.8218 | 0.0218 | 4367 | bow n=1-2 | [tok:linguistico] minusculas > remover_acentos > remover_numeros |
| 5 | 0.8212 | 0.0138 | 3913 | bow n=1-2 | [tok:regex] remover_numeros > stemming |
| 6 | 0.8212 | 0.0138 | 3913 | bow n=1-2 | [tok:regex] minusculas > remover_numeros > stemming |
| 7 | 0.8210 | 0.0238 | 3493 | bow n=1-2 | [tok:split] remover_acentos > remover_pontuacao > remover_numeros > stemming |
| 8 | 0.8210 | 0.0238 | 3493 | bow n=1-2 | [tok:regex] remover_acentos > remover_pontuacao > remover_numeros > stemming |
| 9 | 0.8210 | 0.0238 | 3493 | bow n=1-2 | [tok:linguistico] remover_acentos > remover_pontuacao > remover_numeros > stemming |
| 10 | 0.8210 | 0.0238 | 3493 | bow n=1-2 | [tok:split] minusculas > remover_acentos > remover_pontuacao > remover_numeros > stemming |
| 11 | 0.8210 | 0.0238 | 3493 | bow n=1-2 | [tok:regex] minusculas > remover_acentos > remover_pontuacao > remover_numeros > stemming |
| 12 | 0.8210 | 0.0238 | 3493 | bow n=1-2 | [tok:linguistico] minusculas > remover_acentos > remover_pontuacao > remover_numeros > stemming |
| 13 | 0.8210 | 0.0139 | 3896 | bow n=1-2 | [tok:regex] stemming > remover_acentos |
| 14 | 0.8210 | 0.0139 | 3896 | bow n=1-2 | [tok:regex] minusculas > stemming > remover_acentos |
| 15 | 0.8209 | 0.0175 | 4567 | bow n=1-2 | [tok:regex] remover_acentos |
| 16 | 0.8204 | 0.0169 | 4506 | bow n=1-2 | [tok:linguistico] remover_acentos > remover_numeros |
| 17 | 0.8204 | 0.0145 | 3839 | bow n=1-2 | [tok:linguistico] remover_numeros > stemming > remover_acentos |
| 18 | 0.8204 | 0.0145 | 3839 | bow n=1-2 | [tok:linguistico] minusculas > remover_numeros > stemming > remover_acentos |
| 19 | 0.8200 | 0.0224 | 3495 | bow n=1-2 | [tok:linguistico] remover_acentos > remover_numeros > stemming > remover_pontuacao |
| 20 | 0.8200 | 0.0224 | 3495 | bow n=1-2 | [tok:linguistico] minusculas > remover_acentos > remover_numeros > stemming > remover_pontuacao |
| 21 | 0.8199 | 0.0125 | 3906 | bow n=1-2 | [tok:linguistico] remover_numeros > stemming |
| 22 | 0.8199 | 0.0125 | 3906 | bow n=1-2 | [tok:linguistico] minusculas > remover_numeros > stemming |
| 23 | 0.8198 | 0.0181 | 4514 | bow n=1-2 | [tok:regex] remover_acentos > remover_numeros |
| 24 | 0.8197 | 0.0230 | 4409 | bow n=1-2 | [tok:linguistico] minusculas > remover_acentos |
| 25 | 0.8196 | 0.0167 | 3882 | bow n=1-2 | [tok:linguistico] stemming > remover_acentos |
| 26 | 0.8196 | 0.0167 | 3882 | bow n=1-2 | [tok:linguistico] minusculas > stemming > remover_acentos |
| 27 | 0.8194 | 0.0231 | 4426 | bow n=1-2 | [tok:regex] minusculas > remover_acentos |
| 28 | 0.8193 | 0.0238 | 1102 | bow n=1 | [tok:regex] minusculas > remover_numeros |
| 29 | 0.8191 | 0.0218 | 4475 | bow n=1-2 | [tok:regex] minusculas > remover_numeros |
| 30 | 0.8190 | 0.0210 | 4550 | bow n=1-2 | [tok:linguistico] remover_acentos |