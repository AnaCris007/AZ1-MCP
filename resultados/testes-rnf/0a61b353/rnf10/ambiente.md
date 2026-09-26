# Ambiente do RNF10

- Data: 2026-09-25
- Commit: `0a61b353829dee491537bb2863facbe589d48cc8`
- Execução: contêiner de desenvolvimento da API
- Dependência de resposta: determinística, 0,5 s, sem rede externa
- Carga: HTTPX/asyncio, pool de 60 conexões, carga fechada
- Estágios oficiais: 300 s; aquecimento: 60 s
- Repetições: três progressivas e três de pico
- RSS: `/proc/<pid>/status`, amostragem a cada 100 ms
- CPU: ticks do processo em `/proc/<pid>/stat`
- Dados: exclusivamente sintéticos
- Segredos: nenhum usado ou persistido nas evidências
