# Métricas do RNF03

Arquivo gerado por `python -m pln.metricas`. Não editar à mão.

- Dataset: `intencoes_exemplos.csv` (400 exemplos)
- Validação cruzada estratificada de 5 dobras, semente 42
- Exemplos de intenções conhecidas: 360
- Exemplos `fora_do_catalogo`: 40

## Sem rejeição (comportamento atual em produção)

Com limiar 0,00 nada é rejeitado — é exatamente o que o serviço faz hoje,
já que nenhum limiar é aplicado em `analysis_service`.

- F1-macro: **0.6736** (mínimo 0.85)
- Cobertura: **99.2%** (mínimo 90%)
- Aceitação indevida: **80.0%** (máximo 15%)

## Ponto de operação

**Nenhum limiar atende aos três limites simultaneamente.**

Isto não é um problema de calibração: significa que o modelo não separa as
classes o suficiente para que exista um ponto de corte viável. Ajustar o
limiar apenas troca qual dos três critérios falha.

O mais próximo é o limiar **0.70**:

- F1-macro **0.5730** (mínimo 0.85)
- Cobertura **51.9%** (mínimo 90%)
- Aceitação indevida **15.0%** (máximo 15%)

## Curva do limiar de confiança

Cobertura e aceitação indevida trocam entre si: todo limiar que melhora uma
piora a outra. O ponto de operação é o que atende aos três limites ao mesmo
tempo — se não existir nenhum, o problema é o modelo, e não o limiar.

| Limiar | F1-macro | Cobertura | Aceitação indevida | Atende aos 3 |
| ---: | ---: | ---: | ---: | :---: |
| 0.00 | 0.6736 | 99.2% | 80.0% | — |
| 0.05 | 0.6736 | 99.2% | 80.0% | — |
| 0.10 | 0.6736 | 99.2% | 80.0% | — |
| 0.15 | 0.6736 | 99.2% | 80.0% | — |
| 0.20 | 0.6819 | 99.2% | 75.0% | — |
| 0.25 | 0.6907 | 98.3% | 67.5% | — |
| 0.30 | 0.6949 | 95.8% | 55.0% | — |
| 0.35 | 0.6990 | 91.4% | 40.0% | — |
| 0.40 | 0.6859 | 86.1% | 35.0% | — |
| 0.45 | 0.6774 | 80.0% | 30.0% | — |
| 0.50 | 0.6634 | 73.6% | 27.5% | — |
| 0.55 | 0.6483 | 69.7% | 27.5% | — |
| 0.60 | 0.6126 | 62.2% | 22.5% | — |
| 0.65 | 0.5897 | 56.7% | 20.0% | — |
| 0.70 | 0.5730 | 51.9% | 15.0% | — |
| 0.75 | 0.5331 | 46.1% | 10.0% | — |
| 0.80 | 0.4909 | 40.8% | 7.5% | — |
| 0.85 | 0.4254 | 32.2% | 5.0% | — |
| 0.90 | 0.3408 | 24.4% | 5.0% | — |
| 0.95 | 0.2445 | 15.6% | 2.5% | — |
| 1.00 | 0.0182 | 0.0% | 0.0% | — |

## Curva de aprendizado

F1-macro em função do tamanho do corpus, por subamostragem estratificada.
É o que diz se ampliar o dataset fecha a distância até 0,85: curva ainda
subindo em 100% significa que sim; curva achatada significa que o caminho
é trocar a arquitetura, não juntar mais frases.

| Fração | Exemplos | F1-macro | Ganho sobre a anterior |
| ---: | ---: | ---: | ---: |
| 20% | 80 | 0.2771 | — |
| 40% | 160 | 0.5628 | +0.2857 |
| 60% | 240 | 0.5862 | +0.0234 |
| 80% | 320 | 0.6398 | +0.0536 |
| 100% | 400 | 0.6736 | +0.0338 |

O último degrau ainda rende **+0.0338**: a curva não achatou, e ampliar o corpus deve continuar rendendo.

## Relatório por classe (sem rejeição)

```
                                 precision    recall  f1-score   support

  analisar_completude_coerencia      0.733     0.825     0.776        40
consultar_documentos_normativos      0.676     0.575     0.622        40
    consultar_projeto_sintetico      0.640     0.800     0.711        40
               fora_do_catalogo      0.727     0.200     0.314        40
       gerar_alertas_pendencias      0.880     0.550     0.677        40
         orientar_avanco_mensal      0.745     0.875     0.805        40
   orientar_entregas_cronograma      0.718     0.700     0.709        40
       orientar_mapa_beneficios      0.632     0.900     0.742        40
      orientar_riscos_problemas      0.762     0.800     0.780        40
                   orientar_tap      0.540     0.675     0.600        40

                       accuracy                          0.690       400
                      macro avg      0.705     0.690     0.674       400
                   weighted avg      0.705     0.690     0.674       400

```

