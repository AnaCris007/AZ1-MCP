# Execução do RNF05 — interoperabilidade entre aplicações clientes

- Status: **Aprovado**
- Commit: `0a61b353829dee491537bb2863facbe589d48cc8`
- Pares equivalentes: **23/23 (100.00%)**
- Positivos: **20/20**
- Negativos: **3/3**
- Regras de negócio duplicadas nos clientes: **não**

## Clientes exercitados

1. Adaptador real da interface React: `sendMessage` de `src/frontend/src/lib/api.js`, executado pelo Vitest/Node.
2. Cliente Python independente: `scripts/rnf05_cliente_python.py`, usando HTTPX.

Os dois consumiram a mesma instância controlada da API. Classificação,
recuperação de fontes, tratamento de erros e montagem da resposta permaneceram
no servidor; os clientes limitaram-se ao transporte HTTP e ao tratamento do
contrato.

## Massa e comparação

Foram executadas 20 solicitações válidas e três negativas: entrada vazia,
credencial inválida e falha controlada do serviço. A comparação considerou
método, rota, status, esquema, intenção processada no servidor, fontes, dados
estruturados e categoria de erro.

## Divergências

- Nenhuma.

## Validação auxiliar

A campanha React passou em **23/23 testes** e a suíte preexistente do adaptador
HTTP passou em **8/8 testes**. A instância temporária foi encerrada após a
coleta. Consulte `validacao_auxiliar.md`.
