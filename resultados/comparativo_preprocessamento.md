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
| remover_acentos | 0.6987 | 0.6951 | +0.0035 |
| minusculas | 0.6979 | 0.6975 | +0.0003 |
| remover_numeros | 0.6966 | 0.6996 | -0.0029 |
| remover_pontuacao | 0.6960 | 0.7020 | -0.0060 |

### Stopwords

Comparação **pareada** em 576 configurações idênticas nas demais escolhas.

| opção | F1 médio | vs manter |
|---|---|---|
| manter | 0.7496 | +0.0000 |
| remover_tudo | 0.6978 | -0.0519 |
| preservar_negacoes | 0.6985 | -0.0512 |

### Morfologia

Comparação **pareada** em 576 configurações idênticas nas demais escolhas.

| opção | F1 médio | vs nenhuma |
|---|---|---|
| nenhuma | 0.7182 | +0.0000 |
| stemming | 0.7221 | +0.0039 |
| lematizacao | 0.7056 | -0.0125 |

### Tokenizacao

Comparação **pareada** em 576 configurações idênticas nas demais escolhas.

| opção | F1 médio | vs split |
|---|---|---|
| split | 0.7124 | +0.0000 |
| regex | 0.7172 | +0.0048 |
| linguistico | 0.7162 | +0.0038 |

### A ordem importa?

- Grupos em que a ordem muda o texto: **1332 de 1728**
- Amplitude média de F1 nesses grupos: **0.0137**
- Amplitude máxima: **0.0576**
- Ordem padrão foi a melhor em **569/1332 (43%)** dos grupos

### Efeito da vetorização

Comparação **pareada** em 2971 pré-processamentos: cada um foi
avaliado sob as 4 vetorizações, e é esse conjunto que se compara entre si.

| escolha | com | sem | efeito |
|---|---|---|---|
| bigrama (vs só uni) | 0.6844 | 0.7110 | -0.0266 |
| tfidf (vs bow) | 0.6806 | 0.7149 | -0.0343 |

### Ranking (top 30)

| # | F1-macro | ±dp | vocab | vetorização | pré-processamento |
|---|---|---|---|---|---|
| 1 | 0.7872 | 0.0308 | 3906 | bow n=1-2 | [tok:linguistico] remover_numeros > stemming |
| 2 | 0.7872 | 0.0308 | 3906 | bow n=1-2 | [tok:linguistico] minusculas > remover_numeros > stemming |
| 3 | 0.7871 | 0.0246 | 3839 | bow n=1-2 | [tok:linguistico] remover_numeros > stemming > remover_acentos |
| 4 | 0.7871 | 0.0246 | 3839 | bow n=1-2 | [tok:linguistico] minusculas > remover_numeros > stemming > remover_acentos |
| 5 | 0.7861 | 0.0293 | 3913 | bow n=1-2 | [tok:regex] remover_numeros > stemming |
| 6 | 0.7861 | 0.0293 | 3913 | bow n=1-2 | [tok:regex] minusculas > remover_numeros > stemming |
| 7 | 0.7860 | 0.0354 | 4375 | bow n=1-2 | [tok:regex] minusculas > remover_acentos > remover_numeros |
| 8 | 0.7857 | 0.0360 | 4367 | bow n=1-2 | [tok:linguistico] minusculas > remover_acentos > remover_numeros |
| 9 | 0.7849 | 0.0247 | 3965 | bow n=1-2 | [tok:regex] stemming |
| 10 | 0.7849 | 0.0247 | 3965 | bow n=1-2 | [tok:regex] minusculas > stemming |
| 11 | 0.7848 | 0.0236 | 3845 | bow n=1-2 | [tok:regex] remover_numeros > stemming > remover_acentos |
| 12 | 0.7848 | 0.0236 | 3845 | bow n=1-2 | [tok:regex] minusculas > remover_numeros > stemming > remover_acentos |
| 13 | 0.7846 | 0.0286 | 3949 | bow n=1-2 | [tok:linguistico] stemming |
| 14 | 0.7846 | 0.0286 | 3949 | bow n=1-2 | [tok:linguistico] minusculas > stemming |
| 15 | 0.7844 | 0.0164 | 3928 | bow n=1-2 | [tok:regex] remover_acentos > stemming |
| 16 | 0.7844 | 0.0164 | 3928 | bow n=1-2 | [tok:regex] minusculas > remover_acentos > stemming |
| 17 | 0.7844 | 0.0305 | 1061 | bow n=1 | [tok:regex] minusculas > remover_acentos > remover_numeros |
| 18 | 0.7841 | 0.0218 | 3876 | bow n=1-2 | [tok:regex] remover_acentos > remover_numeros > stemming |
| 19 | 0.7841 | 0.0218 | 3876 | bow n=1-2 | [tok:regex] minusculas > remover_acentos > remover_numeros > stemming |
| 20 | 0.7837 | 0.0344 | 4426 | bow n=1-2 | [tok:regex] minusculas > remover_acentos |
| 21 | 0.7834 | 0.0188 | 3896 | bow n=1-2 | [tok:regex] stemming > remover_acentos |
| 22 | 0.7834 | 0.0188 | 3896 | bow n=1-2 | [tok:regex] minusculas > stemming > remover_acentos |
| 23 | 0.7833 | 0.0213 | 3882 | bow n=1-2 | [tok:linguistico] stemming > remover_acentos |
| 24 | 0.7833 | 0.0213 | 3882 | bow n=1-2 | [tok:linguistico] minusculas > stemming > remover_acentos |
| 25 | 0.7830 | 0.0188 | 3913 | bow n=1-2 | [tok:linguistico] remover_acentos > stemming |
| 26 | 0.7830 | 0.0188 | 3913 | bow n=1-2 | [tok:linguistico] minusculas > remover_acentos > stemming |
| 27 | 0.7827 | 0.0230 | 3870 | bow n=1-2 | [tok:linguistico] remover_acentos > remover_numeros > stemming |
| 28 | 0.7827 | 0.0230 | 3870 | bow n=1-2 | [tok:linguistico] minusculas > remover_acentos > remover_numeros > stemming |
| 29 | 0.7817 | 0.0375 | 1059 | bow n=1 | [tok:linguistico] minusculas > remover_acentos > remover_numeros |
| 30 | 0.7809 | 0.0373 | 1079 | bow n=1 | [tok:regex] minusculas > remover_acentos |