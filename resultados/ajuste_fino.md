# Ajuste fino do classificador de intenções

- Dataset: `intencoes_exemplos.csv`
- Validação cruzada estratificada de 5 dobras, semente 42
- Candidatos avaliados: 3000
- Pré-processamentos: os 20 melhores de comparativo_preprocessamento.csv (8070 linhas).

Este relatório ajusta o MODELO. O que preparar do texto é decidido em
`comparativo_preprocessamento.md`, por `experimento.py`.

## Recomendação

- **Melhor absoluta:** 1.0000 ± 0.0000 — `multinomial s=0.01    prior=treino | bow n=1 | [tok:split] (texto cru)`
- **Mais simples entre as empatadas:** 1.0000 — `multinomial s=1       prior=treino | bow n=1 | [tok:split] (texto cru)`

### Esparsa contra densa

O melhor que cada família de vetorização alcança — a comparação que as tabelas
pareadas abaixo não fazem, porque elas comparam DENTRO de cada família.

| vetorização | melhor F1 | configuração |
|---|---|---|
| esparsa | 1.0000 | `multinomial s=0.01    prior=treino \| bow n=1 \| [tok:split] (texto cru)` |
| densa | 0.8787 | `  gaussiano s=1e-11   \| embedding (pt_core_news_md) \| [tok:split] (texto cru)` |

Valores para `classificador.py`:

```python
CONFIG_PRE_PADRAO = ConfigPreprocessamento(tokenizacao=Tokenizacao.SPLIT)
CONFIG_VET_PADRAO = ConfigVetorizacao(ModoVetorizacao.BOW, n_max=1)
VARIANTE_PADRAO   = VarianteNB.MULTINOMIAL
ALPHA_PADRAO      = 1.0
FIT_PRIOR_PADRAO  = True
```

## Variante de naive bayes — vetorização esparsa

Comparação **pareada** em 960 combinações idênticas nos demais eixos.

| opção | F1 médio | vs melhor |
|---|---|---|
| `multinomial` | 0.9989 | +0.0000 |
| `bernoulli` | 0.9978 | -0.0011 |
| `complement` | 0.9947 | -0.0042 |

## Suavização — vetorização esparsa

Comparação **pareada** em 480 combinações idênticas nos demais eixos.

| opção | F1 médio | vs melhor |
|---|---|---|
| `0.5` | 0.9977 | +0.0000 |
| `0.01` | 0.9977 | -0.0000 |
| `0.05` | 0.9976 | -0.0001 |
| `0.1` | 0.9976 | -0.0002 |
| `1.0` | 0.9971 | -0.0006 |
| `2.0` | 0.9951 | -0.0026 |

## Probabilidades a priori — vetorização esparsa

Comparação **pareada** em 1440 combinações idênticas nos demais eixos.

| opção | F1 médio | vs melhor |
|---|---|---|
| `False` | 0.9971 | +0.0000 |
| `True` | 0.9971 | +0.0000 |

## Vetorização — vetorização esparsa

Comparação **pareada** em 720 combinações idênticas nos demais eixos.

| opção | F1 médio | vs melhor |
|---|---|---|
| `tfidf n=1-2` | 0.9988 | +0.0000 |
| `bow n=1-2` | 0.9982 | -0.0006 |
| `tfidf n=1` | 0.9965 | -0.0022 |
| `bow n=1` | 0.9950 | -0.0037 |

## Suavização — vetorização densa

Comparação **pareada** em 20 combinações idênticas nos demais eixos.

| opção | F1 médio | vs melhor |
|---|---|---|
| `1e-11` | 0.8170 | +0.0000 |
| `1e-09` | 0.8170 | +0.0000 |
| `1e-07` | 0.8170 | +0.0000 |
| `1e-05` | 0.8170 | +0.0000 |
| `0.001` | 0.8164 | -0.0006 |
| `0.1` | 0.7919 | -0.0251 |

## Ranking (top 30)

| # | F1-macro | ±dp | configuração |
|---|---|---|---|
| 1 | 1.0000 | 0.0000 | `multinomial s=0.01    prior=treino \| bow n=1 \| [tok:split] (texto cru)` |
| 2 | 1.0000 | 0.0000 | `multinomial s=0.01    prior=unif \| bow n=1 \| [tok:split] (texto cru)` |
| 3 | 1.0000 | 0.0000 | `multinomial s=0.05    prior=treino \| bow n=1 \| [tok:split] (texto cru)` |
| 4 | 1.0000 | 0.0000 | `multinomial s=0.05    prior=unif \| bow n=1 \| [tok:split] (texto cru)` |
| 5 | 1.0000 | 0.0000 | `multinomial s=0.1     prior=treino \| bow n=1 \| [tok:split] (texto cru)` |
| 6 | 1.0000 | 0.0000 | `multinomial s=0.1     prior=unif \| bow n=1 \| [tok:split] (texto cru)` |
| 7 | 1.0000 | 0.0000 | `multinomial s=0.5     prior=treino \| bow n=1 \| [tok:split] (texto cru)` |
| 8 | 1.0000 | 0.0000 | `multinomial s=0.5     prior=unif \| bow n=1 \| [tok:split] (texto cru)` |
| 9 | 1.0000 | 0.0000 | `multinomial s=1       prior=treino \| bow n=1 \| [tok:split] (texto cru)` |
| 10 | 1.0000 | 0.0000 | `multinomial s=1       prior=unif \| bow n=1 \| [tok:split] (texto cru)` |
| 11 | 1.0000 | 0.0000 | ` complement s=0.01    prior=treino \| bow n=1 \| [tok:split] (texto cru)` |
| 12 | 1.0000 | 0.0000 | ` complement s=0.01    prior=unif \| bow n=1 \| [tok:split] (texto cru)` |
| 13 | 1.0000 | 0.0000 | ` complement s=0.05    prior=treino \| bow n=1 \| [tok:split] (texto cru)` |
| 14 | 1.0000 | 0.0000 | ` complement s=0.05    prior=unif \| bow n=1 \| [tok:split] (texto cru)` |
| 15 | 1.0000 | 0.0000 | ` complement s=0.1     prior=treino \| bow n=1 \| [tok:split] (texto cru)` |
| 16 | 1.0000 | 0.0000 | ` complement s=0.1     prior=unif \| bow n=1 \| [tok:split] (texto cru)` |
| 17 | 1.0000 | 0.0000 | ` complement s=0.5     prior=treino \| bow n=1 \| [tok:split] (texto cru)` |
| 18 | 1.0000 | 0.0000 | ` complement s=0.5     prior=unif \| bow n=1 \| [tok:split] (texto cru)` |
| 19 | 1.0000 | 0.0000 | ` complement s=1       prior=treino \| bow n=1 \| [tok:split] (texto cru)` |
| 20 | 1.0000 | 0.0000 | ` complement s=1       prior=unif \| bow n=1 \| [tok:split] (texto cru)` |
| 21 | 1.0000 | 0.0000 | ` complement s=2       prior=treino \| bow n=1 \| [tok:split] (texto cru)` |
| 22 | 1.0000 | 0.0000 | ` complement s=2       prior=unif \| bow n=1 \| [tok:split] (texto cru)` |
| 23 | 1.0000 | 0.0000 | `  bernoulli s=0.01    prior=treino \| bow n=1 \| [tok:split] (texto cru)` |
| 24 | 1.0000 | 0.0000 | `  bernoulli s=0.01    prior=unif \| bow n=1 \| [tok:split] (texto cru)` |
| 25 | 1.0000 | 0.0000 | `  bernoulli s=0.05    prior=treino \| bow n=1 \| [tok:split] (texto cru)` |
| 26 | 1.0000 | 0.0000 | `  bernoulli s=0.05    prior=unif \| bow n=1 \| [tok:split] (texto cru)` |
| 27 | 1.0000 | 0.0000 | `  bernoulli s=0.1     prior=treino \| bow n=1 \| [tok:split] (texto cru)` |
| 28 | 1.0000 | 0.0000 | `  bernoulli s=0.1     prior=unif \| bow n=1 \| [tok:split] (texto cru)` |
| 29 | 1.0000 | 0.0000 | `  bernoulli s=0.5     prior=treino \| bow n=1 \| [tok:split] (texto cru)` |
| 30 | 1.0000 | 0.0000 | `  bernoulli s=0.5     prior=unif \| bow n=1 \| [tok:split] (texto cru)` |
