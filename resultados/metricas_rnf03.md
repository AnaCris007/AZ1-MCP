# Métricas do RNF03

Arquivo gerado por `python -m pln.metricas`. Não editar à mão.

- Dataset: `intencoes_exemplos.csv` (881 exemplos)
- Validação cruzada estratificada de 5 dobras, semente 42
- Exemplos de intenções conhecidas: 726
- Exemplos `fora_do_catalogo`: 155

## Sem rejeição (comportamento atual em produção)

Com limiar 0,00 nada é rejeitado — é exatamente o que o serviço faz hoje,
já que nenhum limiar é aplicado em `analysis_service`.

- F1-macro: **0.8244** (mínimo 0.85)
- Cobertura: **95.9%** (mínimo 90%)
- Aceitação indevida: **9.7%** (máximo 15%)

## Ponto de operação

**Nenhum limiar atende aos três limites simultaneamente.**

Isto não é um problema de calibração: significa que o modelo não separa as
classes o suficiente para que exista um ponto de corte viável. Ajustar o
limiar apenas troca qual dos três critérios falha.

O mais próximo é o limiar **0.00**:

- F1-macro **0.8244** (mínimo 0.85)
- Cobertura **95.9%** (mínimo 90%)
- Aceitação indevida **9.7%** (máximo 15%)

## Curva do limiar de confiança

Cobertura e aceitação indevida trocam entre si: todo limiar que melhora uma
piora a outra. O ponto de operação é o que atende aos três limites ao mesmo
tempo — se não existir nenhum, o problema é o modelo, e não o limiar.

| Limiar | F1-macro | Cobertura | Aceitação indevida | Atende aos 3 |
| ---: | ---: | ---: | ---: | :---: |
| 0.00 | 0.8244 | 95.9% | 9.7% | — |
| 0.05 | 0.8244 | 95.9% | 9.7% | — |
| 0.10 | 0.8244 | 95.9% | 9.7% | — |
| 0.15 | 0.8244 | 95.9% | 9.7% | — |
| 0.20 | 0.8244 | 95.9% | 9.7% | — |
| 0.25 | 0.8233 | 94.5% | 7.7% | — |
| 0.30 | 0.8214 | 92.6% | 6.5% | — |
| 0.35 | 0.8146 | 89.7% | 6.5% | — |
| 0.40 | 0.8053 | 86.5% | 6.5% | — |
| 0.45 | 0.7896 | 83.2% | 5.8% | — |
| 0.50 | 0.7672 | 78.1% | 5.2% | — |
| 0.55 | 0.7396 | 70.7% | 3.2% | — |
| 0.60 | 0.7036 | 63.4% | 2.6% | — |
| 0.65 | 0.6492 | 53.7% | 1.9% | — |
| 0.70 | 0.5756 | 44.9% | 1.9% | — |
| 0.75 | 0.5037 | 36.8% | 1.9% | — |
| 0.80 | 0.3971 | 26.4% | 1.3% | — |
| 0.85 | 0.2734 | 16.0% | 0.6% | — |
| 0.90 | 0.1202 | 5.4% | 0.0% | — |
| 0.95 | 0.0323 | 0.1% | 0.0% | — |
| 1.00 | 0.0299 | 0.0% | 0.0% | — |

## Curva de aprendizado

F1-macro em função do tamanho do corpus, por subamostragem estratificada.
É o que diz se ampliar o dataset fecha a distância até 0,85: curva ainda
subindo em 100% significa que sim; curva achatada significa que o caminho
é trocar a arquitetura, não juntar mais frases.

| Fração | Exemplos | F1-macro | Ganho sobre a anterior |
| ---: | ---: | ---: | ---: |
| 20% | 175 | 0.6238 | — |
| 40% | 351 | 0.7593 | +0.1356 |
| 60% | 530 | 0.7646 | +0.0053 |
| 80% | 706 | 0.7980 | +0.0334 |
| 100% | 881 | 0.8244 | +0.0264 |

O último degrau ainda rende **+0.0264**: a curva não achatou, e ampliar o corpus deve continuar rendendo.

## Relatório por classe (sem rejeição)

```
                                 precision    recall  f1-score   support

  analisar_completude_coerencia      0.838     0.779     0.807        86
consultar_documentos_normativos      0.945     0.852     0.896        81
    consultar_projeto_sintetico      0.789     0.737     0.762        76
               fora_do_catalogo      0.824     0.903     0.862       155
       gerar_alertas_pendencias      0.756     0.766     0.761        77
         orientar_avanco_mensal      0.844     0.793     0.818        82
   orientar_entregas_cronograma      0.792     0.916     0.849        83
       orientar_mapa_beneficios      0.833     0.843     0.838        83
      orientar_riscos_problemas      0.827     0.805     0.816        77
                   orientar_tap      0.857     0.815     0.835        81

                       accuracy                          0.829       881
                      macro avg      0.830     0.821     0.824       881
                   weighted avg      0.830     0.829     0.828       881

```

