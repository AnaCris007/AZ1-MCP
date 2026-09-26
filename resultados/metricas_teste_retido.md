# RNF03 no conjunto de teste retido

Arquivo gerado por `python -m pln.metricas --teste`. Não editar à mão.

> **Isto não é o conjunto cego da Seção 6.3.** Aquele exige frases novas,
> escritas depois e custodiadas por quem não participou do ajuste. Este é um
> teste retido: separado do pool por `python -m pln.particao` ANTES de
> qualquer treino, escolha de pré-processamento, ajuste de hiperparâmetro ou
> calibração de limiar, e lido uma única vez, aqui. Ele mede generalização
> com honestidade e não substitui a medição cega.

- Desenvolvimento: 881 exemplos (treino, busca, ajuste e calibração)
- Teste retido: 223 exemplos, nunca vistos
- Exemplos de intenções conhecidas no retido: 174
- Exemplos `fora_do_catalogo` no retido: 49

## Limiar congelado

**0.00**, escolhido SOMENTE sobre o desenvolvimento, onde media:

- F1-macro 0.8244, cobertura 95.9%, aceitação indevida 9.7%

A diferença entre esses números e os de baixo é o custo de generalizar. Se ela
for grande, o modelo decorou o corpus de desenvolvimento.

## Resultado no retido

- F1-macro: **0.8735** (mínimo 0.85)
- Cobertura: **96.0%** (mínimo 90%)
- Aceitação indevida: **8.2%** (máximo 15%)

**Atende aos três limites simultaneamente.**

## Relatório por classe (com a rejeição aplicada)

```
                                 precision    recall  f1-score   support

  analisar_completude_coerencia      1.000     0.786     0.880        14
consultar_documentos_normativos      0.944     0.895     0.919        19
    consultar_projeto_sintetico      0.944     0.708     0.810        24
               fora_do_catalogo      0.865     0.918     0.891        49
       gerar_alertas_pendencias      0.800     0.870     0.833        23
         orientar_avanco_mensal      0.824     0.778     0.800        18
   orientar_entregas_cronograma      0.895     1.000     0.944        17
       orientar_mapa_beneficios      1.000     0.882     0.938        17
      orientar_riscos_problemas      0.852     1.000     0.920        23
                   orientar_tap      0.762     0.842     0.800        19

                       accuracy                          0.874       223
                      macro avg      0.889     0.868     0.873       223
                   weighted avg      0.881     0.874     0.874       223

```

