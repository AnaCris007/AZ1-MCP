# Execução RNF01 — desempenho das consultas textuais

**Resultado global: REPROVADO**

O RNF01 exige aprovação separada dos casos positivo e negativo. A rodada
positiva passou, mas a aplicação não encerrou as cinco dependências de 65
segundos dentro do teto de 60 segundos na rodada negativa.

| Indicador | CT-RNF01-P | CT-RNF01-N | Limite |
|---|---:|---:|---:|
| Tentativas | 100 | 100 | 100 por caso |
| Respostas completas em até 15 s | 100 (100%) | 90 (90%) | ≥ 80% |
| Desfechos em até 60 s | 100 (100%) | 95 (95%) | 100% |
| HTTP 2xx | 100 | 95 | informativo |
| p50 | 0,063 s | 0,002 s | informativo |
| p80 | 0,088 s | 0,003 s | informativo |
| p95 | 0,140 s | 20,011 s | informativo |
| Maior duração observada | 0,206 s | 61,067 s | ≤ 60 s |

## Execução

- Commit: `0a61b353829dee491537bb2863facbe589d48cc8`
- Rodadas sequenciais, com uma consulta de aquecimento descartada em cada caso.
- Massa: 100 consultas sintéticas; 50 simples e 50 complexas.
- Positivo: fluxo integrado com serviços configurados, sem exclusões.
- Negativo: 90 respostas sem atraso adicional, cinco atrasos reais de 20 s e
  cinco atrasos reais de 65 s, nas posições versionadas na massa.
- Percentis: método nearest-rank (posto superior), conforme o planejamento.
- Observador HTTP: limite de 61 s, menor que os 65 s injetados e suficiente para
  observar a violação do teto de 60 s.
- Amostra pontual de recursos após a campanha: CPU 20,42%; memória 376,2 MiB de
  7,75 GiB (4,74%).

## Interpretação

Os cinco atrasos de 20 s completaram entre 20,004 s e 20,011 s: contam como
desfecho, mas não como resposta completa em 15 s. Os cinco atrasos de 65 s não
receberam erro controlado da aplicação; o cliente encerrou a observação entre
61,008 s e 61,067 s. Cancelamento do cliente não conta como desfecho da
aplicação, portanto o critério de 100% em 60 s foi violado.

Autenticação e persistência lateral foram isoladas na instância de ensaio. A
persistência ocorre em tarefa posterior à resposta e não integra a latência
percebida; o isolamento também evitou poluir a trilha normal com 200 registros
de carga.

