# Bancada de desempenho do pipeline de PLN

Arquivo gerado por `python -m pln.bancada`. Não editar à mão.

- Python: 3.12.3 (x86_64)
- Sistema: Linux 7.0.0-31-generic
- Semente: 42

## Latência de inferência

Uma consulta por vez, processo já aquecido. O RNF01 mede a consulta completa,
que inclui transcrição e geração de resposta; aqui está apenas a parcela do
classificador, que é a que este pipeline controla.

| Trecho medido | Amostras | Média | p50 | p80 | p95 |
| --- | ---: | ---: | ---: | ---: | ---: |
| `prever_intencao` (ponta a ponta) | 200 | 2.107 ms | 1.953 ms | 2.252 ms | 3.092 ms |
| `preprocessar` (isolado) | 200 | 0.015 ms | 0.014 ms | 0.016 ms | 0.019 ms |

O pré-processamento responde por **1%** da mediana ponta a ponta.
É onde uma otimização de latência tem efeito; o `predict_proba` sobre uma
matriz esparsa de uma linha é a parcela pequena.

## Treino: tempo e pico de memória por tamanho de dataset

Datasets `Nx` são replicação estratificada do dataset real, e servem só para
medir custo. **Não** medem qualidade: o mesmo exemplo apareceria em dobras de
treino e de teste, e o F1 sairia inflado.

Ressalva de leitura: a replicação não cria vocabulário novo, então o
vocabulário fica constante enquanto o número de linhas cresce. O consumo
medido é um **piso** do que um dataset real de mesmo tamanho custaria. A
medição definitiva do RNF10 precisa do dataset ampliado, não deste.

| Fator | Exemplos | Tempo de treino | Razão de tempo | Pico de memória | Razão de pico |
| --- | ---: | ---: | ---: | ---: | ---: |
| 1x | 881 | 0.219 s | 1.00x | 2.55 MiB | 1.00x |
| 2x | 1762 | 0.584 s | 2.66x | 3.20 MiB | 1.26x |
| 5x | 4405 | 1.057 s | 4.82x | 5.62 MiB | 2.21x |
| 10x | 8810 | 3.576 s | 16.30x | 9.84 MiB | 3.86x |

O RNF10 limita a razão de pico de treino entre `10x` e `1x` a 8. Medido: **3.86x** — dentro do limite.

