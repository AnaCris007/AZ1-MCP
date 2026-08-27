# Ajuste fino do classificador de intenções

- Dataset: `intencoes_exemplos.csv`
- Validação cruzada estratificada de 5 dobras, semente 42
- Candidatos avaliados: 960
- Pré-processamentos: os 20 melhores de comparativo_preprocessamento.csv (11644 linhas).

Este relatório ajusta o MODELO. O que preparar do texto é decidido em
`comparativo_preprocessamento.md`, por `experimento.py`.

## Recomendação

- **Melhor absoluta:** 0.6896 ± 0.0601 — `s=1       prior=treino | tfidf n=1 | [tok:split] minusculas > remover_acentos > remover_pontuacao`
- **Mais simples entre as empatadas:** 0.6735 — `s=1       prior=treino | bow n=1 | [tok:regex] remover_numeros > stemming`

Valores para `classificador.py`:

```python
CONFIG_PRE_PADRAO = ConfigPreprocessamento(remover_numeros=True, morfologia=ModoMorfologia.STEMMING, tokenizacao=Tokenizacao.REGEX)
CONFIG_VET_PADRAO = ConfigVetorizacao(ModoVetorizacao.BOW, n_max=1)
ALPHA_PADRAO      = 1.0
FIT_PRIOR_PADRAO  = True
```

## Suavização

Comparação **pareada** em 160 combinações idênticas nos demais eixos.

| opção | F1 médio | vs melhor |
|---|---|---|
| `1.0` | 0.6537 | +0.0000 |
| `0.5` | 0.6454 | -0.0083 |
| `2.0` | 0.6446 | -0.0091 |
| `0.1` | 0.6190 | -0.0347 |
| `0.05` | 0.6077 | -0.0460 |
| `0.01` | 0.5920 | -0.0617 |

## Probabilidades a priori

Comparação **pareada** em 480 combinações idênticas nos demais eixos.

| opção | F1 médio | vs melhor |
|---|---|---|
| `True` | 0.6271 | +0.0000 |
| `False` | 0.6271 | +0.0000 |

## Vetorização

Comparação **pareada** em 240 combinações idênticas nos demais eixos.

| opção | F1 médio | vs melhor |
|---|---|---|
| `bow n=1` | 0.6401 | +0.0000 |
| `tfidf n=1` | 0.6276 | -0.0125 |
| `bow n=1-2` | 0.6258 | -0.0143 |
| `tfidf n=1-2` | 0.6148 | -0.0252 |

## Ranking (top 30)

| # | F1-macro | ±dp | configuração |
|---|---|---|---|
| 1 | 0.6896 | 0.0601 | `s=1       prior=treino \| tfidf n=1 \| [tok:split] minusculas > remover_acentos > remover_pontuacao` |
| 2 | 0.6896 | 0.0601 | `s=1       prior=unif \| tfidf n=1 \| [tok:split] minusculas > remover_acentos > remover_pontuacao` |
| 3 | 0.6896 | 0.0601 | `s=1       prior=treino \| tfidf n=1 \| [tok:regex] minusculas > remover_acentos > remover_pontuacao` |
| 4 | 0.6896 | 0.0601 | `s=1       prior=unif \| tfidf n=1 \| [tok:regex] minusculas > remover_acentos > remover_pontuacao` |
| 5 | 0.6896 | 0.0601 | `s=1       prior=treino \| tfidf n=1 \| [tok:linguistico] minusculas > remover_acentos > remover_pontuacao` |
| 6 | 0.6896 | 0.0601 | `s=1       prior=unif \| tfidf n=1 \| [tok:linguistico] minusculas > remover_acentos > remover_pontuacao` |
| 7 | 0.6777 | 0.0459 | `s=0.5     prior=treino \| bow n=1 \| [tok:regex] minusculas > remover_acentos > remover_numeros` |
| 8 | 0.6777 | 0.0459 | `s=0.5     prior=unif \| bow n=1 \| [tok:regex] minusculas > remover_acentos > remover_numeros` |
| 9 | 0.6765 | 0.0623 | `s=2       prior=treino \| tfidf n=1 \| [tok:regex] remover_numeros > stemming` |
| 10 | 0.6765 | 0.0623 | `s=2       prior=unif \| tfidf n=1 \| [tok:regex] remover_numeros > stemming` |
| 11 | 0.6765 | 0.0623 | `s=2       prior=treino \| tfidf n=1 \| [tok:regex] minusculas > remover_numeros > stemming` |
| 12 | 0.6765 | 0.0623 | `s=2       prior=unif \| tfidf n=1 \| [tok:regex] minusculas > remover_numeros > stemming` |
| 13 | 0.6752 | 0.0634 | `s=1       prior=treino \| tfidf n=1 \| [tok:split] minusculas > remover_acentos > remover_pontuacao > remover_numeros` |
| 14 | 0.6752 | 0.0634 | `s=1       prior=unif \| tfidf n=1 \| [tok:split] minusculas > remover_acentos > remover_pontuacao > remover_numeros` |
| 15 | 0.6752 | 0.0634 | `s=1       prior=treino \| tfidf n=1 \| [tok:regex] minusculas > remover_acentos > remover_pontuacao > remover_numeros` |
| 16 | 0.6752 | 0.0634 | `s=1       prior=unif \| tfidf n=1 \| [tok:regex] minusculas > remover_acentos > remover_pontuacao > remover_numeros` |
| 17 | 0.6752 | 0.0634 | `s=1       prior=treino \| tfidf n=1 \| [tok:linguistico] minusculas > remover_acentos > remover_pontuacao > remover_numeros` |
| 18 | 0.6752 | 0.0634 | `s=1       prior=unif \| tfidf n=1 \| [tok:linguistico] minusculas > remover_acentos > remover_pontuacao > remover_numeros` |
| 19 | 0.6751 | 0.0407 | `s=0.5     prior=treino \| bow n=1 \| [tok:regex] minusculas > remover_acentos` |
| 20 | 0.6751 | 0.0407 | `s=0.5     prior=unif \| bow n=1 \| [tok:regex] minusculas > remover_acentos` |
| 21 | 0.6748 | 0.0406 | `s=0.5     prior=treino \| bow n=1 \| [tok:linguistico] minusculas > remover_acentos` |
| 22 | 0.6748 | 0.0406 | `s=0.5     prior=unif \| bow n=1 \| [tok:linguistico] minusculas > remover_acentos` |
| 23 | 0.6735 | 0.0685 | `s=1       prior=treino \| bow n=1 \| [tok:regex] remover_numeros > stemming` |
| 24 | 0.6735 | 0.0685 | `s=1       prior=unif \| bow n=1 \| [tok:regex] remover_numeros > stemming` |
| 25 | 0.6735 | 0.0685 | `s=1       prior=treino \| bow n=1 \| [tok:regex] minusculas > remover_numeros > stemming` |
| 26 | 0.6735 | 0.0685 | `s=1       prior=unif \| bow n=1 \| [tok:regex] minusculas > remover_numeros > stemming` |
| 27 | 0.6731 | 0.0635 | `s=1       prior=treino \| bow n=1 \| [tok:regex] minusculas > remover_acentos` |
| 28 | 0.6731 | 0.0635 | `s=1       prior=unif \| bow n=1 \| [tok:regex] minusculas > remover_acentos` |
| 29 | 0.6717 | 0.0658 | `s=1       prior=treino \| bow n=1 \| [tok:regex] minusculas > remover_acentos > remover_numeros` |
| 30 | 0.6717 | 0.0658 | `s=1       prior=unif \| bow n=1 \| [tok:regex] minusculas > remover_acentos > remover_numeros` |
