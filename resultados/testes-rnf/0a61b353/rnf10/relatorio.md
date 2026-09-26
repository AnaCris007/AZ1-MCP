# Execução RNF10 — escalabilidade do agente

**Resultado: APROVADO**

As duas dimensões obrigatórias foram executadas e aprovadas: crescimento da
concorrência HTTP e crescimento de memória do pipeline de PLN.

## Concorrência

Foram realizadas três progressões completas de `5 → 10 → 25 → 50`
requisições simultâneas e três picos diretos de 50, com servidor reiniciado
antes de cada repetição. Cada estágio durou cinco minutos, após um minuto de
aquecimento. A dependência determinística levou 0,5 s em todas as chamadas.

| Indicador | Medido | Limite | Resultado |
|---|---:|---:|---|
| `B`: mediana dos p95 em 1x | 0,515 s | linha de base | — |
| `C`: mediana dos p95 em 10x progressivo | 0,975 s | ≤ 20 s | Passou |
| `P`: mediana dos p95 no pico | 0,968 s | ≤ 20 s | Passou |
| `C / B` | 1,892x | ≤ 2x | Passou |
| `P / B` | 1,879x | ≤ 2x | Passou |
| Respostas completas | 212.691/212.691 | 100% | Passou |
| Concorrência máxima observada | 50/50 | 50 | Passou |

O pico de RSS observado na API foi 242,85 MiB no progressivo de 50 e
242,20 MiB no pico direto. O throughput nos estágios de 50 ficou próximo de
78,5 respostas por segundo.

## Memória

Os datasets controlados tiveram 1x, 2x, 5x e 10x. O cenário adverso 10x
acrescentou um termo exclusivo a cada cópia, elevando o vocabulário aproximado
de 1.578 para 10.388 termos. Cada treino e cada processo servido foram medidos
três vezes em processo novo; RSS foi amostrada a cada 100 ms. O serviço ficou
30 segundos sem carga e a mediana dos últimos dez segundos foi usada como RSS
estabilizada, seguida por 100 inferências.

| Condição 10x / linha de base 1x | Treino | Serviço estabilizado | Pico de inferência |
|---|---:|---:|---:|
| Controlada | 1,042x | 1,015x | 1,014x |
| Adversa | 1,059x | 1,008x | 1,009x |
| Limite | ≤ 8x | ≤ 2x | ≤ 2x |

Todas as razões ficaram dentro dos limites cumulativos do requisito.

## Limitações

A campanha mede a capacidade interna da API com dependência externa
determinística; não estima limites comerciais de Gemini, Supabase ou outro
provedor. A massa e os datasets são sintéticos. O pico de RSS é uma amostragem
e pode não capturar variações inferiores a 100 ms, limitação já prevista no
planejamento.

