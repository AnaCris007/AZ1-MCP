# Ajuste fino do classificador de intenções

- Dataset: `intencoes_exemplos.csv`
- Validação cruzada estratificada de 5 dobras, semente 42
- Candidatos avaliados: 240
- Pré-processamentos: os 5 melhores de comparativo_preprocessamento.csv (11884 linhas).

Este relatório ajusta o MODELO. O que preparar do texto é decidido em
`comparativo_preprocessamento.md`, por `experimento.py`.

## Recomendação

- **Melhor absoluta:** 0.7932 ± 0.0190 — `s=1       prior=unif | tfidf n=1-2 | [tok:linguistico] remover_acentos > remover_numeros > stemming`
- **Mais simples entre as empatadas:** 0.7787 — `s=1       prior=treino | bow n=1 | [tok:linguistico] remover_numeros > stemming`

Valores para `classificador.py`:

```python
CONFIG_PRE_PADRAO = ConfigPreprocessamento(remover_numeros=True, morfologia=ModoMorfologia.STEMMING, tokenizacao=Tokenizacao.LINGUISTICO)
CONFIG_VET_PADRAO = ConfigVetorizacao(ModoVetorizacao.BOW, n_max=1)
ALPHA_PADRAO      = 1.0
FIT_PRIOR_PADRAO  = True
```

## Suavização

Comparação **pareada** em 40 combinações idênticas nos demais eixos.

| opção | F1 médio | vs melhor |
|---|---|---|
| `0.5` | 0.7694 | +0.0000 |
| `1.0` | 0.7662 | -0.0032 |
| `0.1` | 0.7464 | -0.0230 |
| `0.05` | 0.7322 | -0.0373 |
| `2.0` | 0.7297 | -0.0398 |
| `0.01` | 0.7056 | -0.0638 |

## Probabilidades a priori

Comparação **pareada** em 120 combinações idênticas nos demais eixos.

| opção | F1 médio | vs melhor |
|---|---|---|
| `False` | 0.7459 | +0.0000 |
| `True` | 0.7372 | -0.0087 |

## Vetorização

Comparação **pareada** em 60 combinações idênticas nos demais eixos.

| opção | F1 médio | vs melhor |
|---|---|---|
| `bow n=1-2` | 0.7586 | +0.0000 |
| `tfidf n=1-2` | 0.7444 | -0.0142 |
| `bow n=1` | 0.7427 | -0.0159 |
| `tfidf n=1` | 0.7207 | -0.0379 |

## Ranking (top 30)

| # | F1-macro | ±dp | configuração |
|---|---|---|---|
| 1 | 0.7932 | 0.0190 | `s=1       prior=unif \| tfidf n=1-2 \| [tok:linguistico] remover_acentos > remover_numeros > stemming` |
| 2 | 0.7932 | 0.0190 | `s=1       prior=unif \| tfidf n=1-2 \| [tok:linguistico] minusculas > remover_acentos > remover_numeros > stemming` |
| 3 | 0.7892 | 0.0260 | `s=0.5     prior=treino \| tfidf n=1-2 \| [tok:linguistico] remover_acentos > remover_numeros > stemming` |
| 4 | 0.7892 | 0.0260 | `s=0.5     prior=treino \| tfidf n=1-2 \| [tok:linguistico] minusculas > remover_acentos > remover_numeros > stemming` |
| 5 | 0.7877 | 0.0183 | `s=1       prior=unif \| tfidf n=1-2 \| [tok:linguistico] remover_numeros > stemming` |
| 6 | 0.7877 | 0.0183 | `s=1       prior=unif \| tfidf n=1-2 \| [tok:linguistico] minusculas > remover_numeros > stemming` |
| 7 | 0.7872 | 0.0308 | `s=1       prior=treino \| bow n=1-2 \| [tok:linguistico] remover_numeros > stemming` |
| 8 | 0.7872 | 0.0308 | `s=1       prior=treino \| bow n=1-2 \| [tok:linguistico] minusculas > remover_numeros > stemming` |
| 9 | 0.7861 | 0.0293 | `s=1       prior=treino \| bow n=1-2 \| [tok:regex] remover_numeros > stemming` |
| 10 | 0.7860 | 0.0189 | `s=0.5     prior=unif \| tfidf n=1-2 \| [tok:linguistico] remover_acentos > remover_numeros > stemming` |
| 11 | 0.7860 | 0.0189 | `s=0.5     prior=unif \| tfidf n=1-2 \| [tok:linguistico] minusculas > remover_acentos > remover_numeros > stemming` |
| 12 | 0.7856 | 0.0193 | `s=2       prior=unif \| tfidf n=1-2 \| [tok:linguistico] remover_numeros > stemming` |
| 13 | 0.7856 | 0.0193 | `s=2       prior=unif \| tfidf n=1-2 \| [tok:linguistico] minusculas > remover_numeros > stemming` |
| 14 | 0.7854 | 0.0199 | `s=2       prior=unif \| tfidf n=1-2 \| [tok:regex] remover_numeros > stemming` |
| 15 | 0.7854 | 0.0191 | `s=1       prior=unif \| tfidf n=1-2 \| [tok:regex] remover_numeros > stemming` |
| 16 | 0.7839 | 0.0119 | `s=2       prior=unif \| tfidf n=1-2 \| [tok:linguistico] remover_acentos > remover_numeros > stemming` |
| 17 | 0.7839 | 0.0119 | `s=2       prior=unif \| tfidf n=1-2 \| [tok:linguistico] minusculas > remover_acentos > remover_numeros > stemming` |
| 18 | 0.7829 | 0.0142 | `s=0.5     prior=unif \| tfidf n=1-2 \| [tok:linguistico] remover_numeros > stemming` |
| 19 | 0.7829 | 0.0142 | `s=0.5     prior=unif \| tfidf n=1-2 \| [tok:linguistico] minusculas > remover_numeros > stemming` |
| 20 | 0.7827 | 0.0230 | `s=1       prior=treino \| bow n=1-2 \| [tok:linguistico] remover_acentos > remover_numeros > stemming` |
| 21 | 0.7827 | 0.0230 | `s=1       prior=treino \| bow n=1-2 \| [tok:linguistico] minusculas > remover_acentos > remover_numeros > stemming` |
| 22 | 0.7825 | 0.0178 | `s=0.5     prior=unif \| tfidf n=1-2 \| [tok:regex] remover_numeros > stemming` |
| 23 | 0.7816 | 0.0259 | `s=1       prior=unif \| bow n=1-2 \| [tok:regex] remover_numeros > stemming` |
| 24 | 0.7815 | 0.0263 | `s=1       prior=unif \| bow n=1-2 \| [tok:linguistico] remover_numeros > stemming` |
| 25 | 0.7815 | 0.0263 | `s=1       prior=unif \| bow n=1-2 \| [tok:linguistico] minusculas > remover_numeros > stemming` |
| 26 | 0.7813 | 0.0233 | `s=2       prior=treino \| bow n=1-2 \| [tok:linguistico] remover_numeros > stemming` |
| 27 | 0.7813 | 0.0233 | `s=2       prior=treino \| bow n=1-2 \| [tok:linguistico] minusculas > remover_numeros > stemming` |
| 28 | 0.7811 | 0.0259 | `s=0.5     prior=treino \| tfidf n=1-2 \| [tok:regex] remover_numeros > stemming` |
| 29 | 0.7806 | 0.0263 | `s=0.5     prior=treino \| tfidf n=1-2 \| [tok:linguistico] remover_numeros > stemming` |
| 30 | 0.7806 | 0.0263 | `s=0.5     prior=treino \| tfidf n=1-2 \| [tok:linguistico] minusculas > remover_numeros > stemming` |
