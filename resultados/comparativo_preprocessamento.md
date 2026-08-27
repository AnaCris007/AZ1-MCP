# Comparativo de pré-processamento e vetorização

- Dataset: `intencoes_exemplos.csv`
- Validação cruzada estratificada de 5 dobras, semente 42
- Régua fixa: `MultinomialNB(alpha=1.0)` — instrumento de medida, não o modelo final
- A MESMA régua nas quatro vetorizações, que são todas esparsas: é o que torna a comparação entre elas identificável

## Varredura exaustiva — pré-processamento x vetorização

Produto cartesiano completo: cada pré-processamento contra as 4 vetorizações.
Permutações de ordem examinadas: 19767. Execuções distintas: 11644.

### Efeito de cada etapa booleana

| etapa | com | sem | efeito |
|---|---|---|---|
| minusculas | 0.5952 | 0.5893 | +0.0059 |
| remover_acentos | 0.5923 | 0.5946 | -0.0023 |
| remover_numeros | 0.5876 | 0.6014 | -0.0137 |
| remover_pontuacao | 0.5889 | 0.6030 | -0.0141 |

### Stopwords

Comparação **pareada** em 576 configurações idênticas nas demais escolhas.

| opção | F1 médio | vs manter |
|---|---|---|
| manter | 0.6332 | +0.0000 |
| remover_tudo | 0.5942 | -0.0390 |
| preservar_negacoes | 0.5943 | -0.0389 |

### Morfologia

Comparação **pareada** em 576 configurações idênticas nas demais escolhas.

| opção | F1 médio | vs nenhuma |
|---|---|---|
| nenhuma | 0.5962 | +0.0000 |
| stemming | 0.6247 | +0.0285 |
| lematizacao | 0.6009 | +0.0047 |

### Tokenizacao

Comparação **pareada** em 576 configurações idênticas nas demais escolhas.

| opção | F1 médio | vs split |
|---|---|---|
| split | 0.5951 | +0.0000 |
| regex | 0.6133 | +0.0182 |
| linguistico | 0.6134 | +0.0184 |

### A ordem importa?

- Grupos em que a ordem muda o texto: **1320 de 1728**
- Amplitude média de F1 nesses grupos: **0.0148**
- Amplitude máxima: **0.0820**
- Ordem padrão foi a melhor em **585/1320 (44%)** dos grupos

### Efeito da vetorização

Comparação **pareada** em 2911 pré-processamentos: cada um foi
avaliado sob as 4 vetorizações, e é esse conjunto que se compara entre si.

| escolha | com | sem | efeito |
|---|---|---|---|
| tfidf (vs bow) | 0.5869 | 0.5990 | -0.0120 |
| bigrama (vs só uni) | 0.5811 | 0.6048 | -0.0237 |

### Ranking (top 30)

| # | F1-macro | ±dp | vocab | vetorização | pré-processamento |
|---|---|---|---|---|---|
| 1 | 0.6896 | 0.0601 | 677 | tfidf n=1 | [tok:split] minusculas > remover_acentos > remover_pontuacao |
| 2 | 0.6896 | 0.0601 | 677 | tfidf n=1 | [tok:regex] minusculas > remover_acentos > remover_pontuacao |
| 3 | 0.6896 | 0.0601 | 677 | tfidf n=1 | [tok:linguistico] minusculas > remover_acentos > remover_pontuacao |
| 4 | 0.6752 | 0.0634 | 661 | tfidf n=1 | [tok:split] minusculas > remover_acentos > remover_pontuacao > remover_numeros |
| 5 | 0.6752 | 0.0634 | 661 | tfidf n=1 | [tok:regex] minusculas > remover_acentos > remover_pontuacao > remover_numeros |
| 6 | 0.6752 | 0.0634 | 661 | tfidf n=1 | [tok:linguistico] minusculas > remover_acentos > remover_pontuacao > remover_numeros |
| 7 | 0.6749 | 0.0432 | 485 | bow n=1 | [tok:regex] stemming > sw:remover_tudo > remover_acentos |
| 8 | 0.6749 | 0.0432 | 485 | bow n=1 | [tok:regex] minusculas > stemming > sw:remover_tudo > remover_acentos |
| 9 | 0.6739 | 0.0463 | 497 | bow n=1 | [tok:regex] sw:preservar_negacoes > remover_acentos > stemming |
| 10 | 0.6739 | 0.0463 | 497 | bow n=1 | [tok:regex] minusculas > sw:preservar_negacoes > remover_acentos > stemming |
| 11 | 0.6735 | 0.0685 | 531 | bow n=1 | [tok:regex] remover_numeros > stemming |
| 12 | 0.6735 | 0.0685 | 531 | bow n=1 | [tok:regex] minusculas > remover_numeros > stemming |
| 13 | 0.6731 | 0.0635 | 683 | bow n=1 | [tok:regex] minusculas > remover_acentos |
| 14 | 0.6722 | 0.0438 | 479 | bow n=1 | [tok:regex] stemming > remover_acentos > sw:remover_tudo |
| 15 | 0.6722 | 0.0438 | 479 | bow n=1 | [tok:regex] minusculas > stemming > remover_acentos > sw:remover_tudo |
| 16 | 0.6721 | 0.0398 | 481 | bow n=1 | [tok:linguistico] stemming > sw:preservar_negacoes > remover_acentos |
| 17 | 0.6721 | 0.0398 | 481 | bow n=1 | [tok:linguistico] minusculas > stemming > sw:preservar_negacoes > remover_acentos |
| 18 | 0.6717 | 0.0658 | 667 | bow n=1 | [tok:regex] minusculas > remover_acentos > remover_numeros |
| 19 | 0.6714 | 0.0573 | 678 | bow n=1 | [tok:linguistico] minusculas > remover_acentos |
| 20 | 0.6714 | 0.0484 | 685 | tfidf n=1 | [tok:split] minusculas > remover_pontuacao > remover_numeros |
| 21 | 0.6714 | 0.0484 | 685 | tfidf n=1 | [tok:regex] minusculas > remover_pontuacao > remover_numeros |
| 22 | 0.6714 | 0.0484 | 685 | tfidf n=1 | [tok:linguistico] minusculas > remover_pontuacao > remover_numeros |
| 23 | 0.6714 | 0.0460 | 490 | bow n=1 | [tok:regex] sw:preservar_negacoes > stemming > remover_acentos |
| 24 | 0.6714 | 0.0460 | 490 | bow n=1 | [tok:regex] minusculas > sw:preservar_negacoes > stemming > remover_acentos |
| 25 | 0.6713 | 0.0423 | 486 | bow n=1 | [tok:linguistico] sw:preservar_negacoes > stemming > remover_acentos |
| 26 | 0.6713 | 0.0423 | 486 | bow n=1 | [tok:linguistico] minusculas > sw:preservar_negacoes > stemming > remover_acentos |
| 27 | 0.6712 | 0.0479 | 470 | bow n=1 | [tok:regex] remover_numeros > stemming > sw:preservar_negacoes > remover_acentos |
| 28 | 0.6712 | 0.0479 | 470 | bow n=1 | [tok:regex] minusculas > remover_numeros > stemming > sw:preservar_negacoes > remover_acentos |
| 29 | 0.6711 | 0.0453 | 489 | bow n=1 | [tok:linguistico] remover_acentos > sw:preservar_negacoes > stemming |
| 30 | 0.6711 | 0.0453 | 489 | bow n=1 | [tok:linguistico] minusculas > remover_acentos > sw:preservar_negacoes > stemming |