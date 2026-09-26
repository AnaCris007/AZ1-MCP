# Execucao do RNF07 — disponibilidade da solucao

## Resultado

**REPROVADO** na versao e no ambiente avaliados.

- CT-RNF07-P: **APROVADO** — 60/60 verificacoes elegiveis bem-sucedidas (100.0000%).
- CT-RNF07-N: **REPROVADO**.
- Janela executada: 60.0 minutos, ante 240 minutos do plano original.
- Intervalo: 60.0 segundos; amostras realizadas: 60.

## Desvio de escopo

Esta rodada foi deliberadamente reduzida de quatro horas para uma hora por restricao de tempo. Ela preserva o intervalo de uma verificacao por minuto, mas nao e equivalente as 240 verificacoes do criterio oficial. Nao foram preenchidas artificialmente amostras ausentes.

## Cenarios controlados

A indisponibilidade do banco foi simulada pela substituicao do pool somente dentro do processo de teste, sem interromper ou alterar o banco externo configurado. `/health/ready` retornou 503 durante a falha e 200 depois da recuperacao. O endpoint contratual `/health`, entretanto, retornou HTTP 200 durante a falha do banco. Registro tecnico observado: false; alerta observado: false.

O cenario de aplicacao internamente nao saudavel nao foi executavel: A versao avaliada nao expoe estado interno de saude nem mecanismo controlado que torne GET /health 503 mantendo o servidor HTTP acessivel. Esse impedimento conta como nao atendimento do caso negativo, e nao como aprovacao presumida.

## Conclusao

A janela reduzida de uma hora nao comprova o criterio oficial de quatro horas e limita a conclusao a esta execucao academica. O resultado global exige simultaneamente a disponibilidade natural e o comportamento previsto para as falhas controladas.

## Evidencias

- `verificacoes.csv`: cada chamada, duracao, status, corpo e elegibilidade.
- `cenarios_controlados.json`: eventos e observacoes dos testes negativos.
- `ambiente.json`: versao, configuracao e horarios.
- `resultado.json`: calculo consolidado e veredito.
- `monitor.log`: progresso do executor.
