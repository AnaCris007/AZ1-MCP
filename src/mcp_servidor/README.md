# Servidor MCP

Expõe a capacidade do AZ1 como ferramenta MCP, para que um agente do Microsoft
Copilot Studio responda usando este motor. O contexto completo da decisão está
em [`docs/GuiaImplantacaoCopilotStudio.md`](../../docs/GuiaImplantacaoCopilotStudio.md).

## O que existe aqui

| Arquivo | Papel |
|---|---|
| `servidor.py` | A ferramenta `responder_consulta` e o sub-aplicativo ASGI |
| `seguranca.py` | Guarda de chave de API e normalização do caminho |

Três decisões que o código não deixa adivinhar, e que estão justificadas nos
docstrings: o pacote se chama `mcp_servidor` para não sombrear a dependência
`mcp` do `fastmcp`; a ferramenta é **uma** e de alto nível, porque decompor
entrega trecho cru ao orquestrador e contorna o recuo fundamentado; e o `/mcp`
só é montado quando há chave configurada.

## Rodando localmente

```bash
export AZ1_MCP_API_KEY=$(python -c "import secrets; print(secrets.token_urlsafe(32))")
```

```bash
SUPABASE_DB_URL=... GEMINI_API_KEY=... PYTHONPATH=src uvicorn az1_api.main:app --port 8000
```

Sem `AZ1_MCP_API_KEY` o `/mcp` não é montado e responde 404. Com ela, responde
401 a quem não apresentar o cabeçalho `x-api-key`.

Conferindo o handshake e o catálogo, sem subir nada além da API:

```bash
curl -sS -X POST -H "x-api-key: $AZ1_MCP_API_KEY" -H "Content-Type: application/json" -H "Accept: application/json, text/event-stream" -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}' http://127.0.0.1:8000/mcp
```

## Publicando no Render

O [`render.yaml`](../../render.yaml) na raiz descreve o serviço. Ele sobe
**apenas a API**: sem MinIO, sem RabbitMQ e sem Postgres local, porque as
ferramentas MCP tocam o banco e o modelo, e o banco já vive no Supabase.

Quatro variáveis são marcadas `sync: false` e precisam ser preenchidas no
painel, nunca no repositório: `SUPABASE_DB_URL`, `GEMINI_API_KEY`,
`AZ1_MCP_API_KEY` e `AZ1_MCP_USUARIO_EMAIL`.

Duas armadilhas conhecidas do plano gratuito. O serviço **hiberna após 15
minutos** ociosos e leva de 30 a 60 segundos para acordar, o que estoura o
tempo limite do conector: um ping a cada 10 minutos no `/health` resolve, e
cabe nas 750 horas mensais da franquia. E a construção **treina o classificador
durante o build**, pelo estágio `trainer` do Dockerfile, então o primeiro
deploy demora mais que os seguintes.

## Ligando no Copilot Studio

No agente: *Ferramentas*, *Adicionar uma ferramenta*, *Model Context Protocol*.

| Campo | Valor |
|---|---|
| URL do servidor | `https://<servico>.onrender.com/mcp` |
| Transporte | Streamable HTTP |
| Autenticação | API key, tipo Header, nome `x-api-key` |

O valor da chave vai para a *connection* do Power Platform, separado da
definição da ferramenta. O assistente gera o conector customizado com a
propriedade `x-ms-agentic-protocol: mcp-streamable-1.0`, então não é preciso
escrever especificação à mão.

Nas instruções do agente, mande encaminhar toda pergunta de domínio à
`responder_consulta` e **repassar a resposta sem reescrever quando `recuou`
vier verdadeiro**. Sem essa instrução o orquestrador trata a recusa como
resposta insatisfatória e tenta completá-la, que é exatamente o que o recuo
existe para impedir.

## O limite deste caminho

A chave autentica o **cliente**, não a **pessoa**. Toda chamada chega como a
mesma identidade, `auditoria.mensagem` registra um usuário só, e a recuperação
continua sem filtrar por permissão. Isso define o uso: **piloto com massa
sintética, não acervo real do PMO.**

Levantar a restrição exige OAuth com o Entra ID, o que depende de duas coisas:
um registro de aplicativo no diretório do parceiro, que é decisão dele, e o
verificador da API aceitar token do Entra, que hoje valida token do Supabase.
A fronteira preparada para essa troca é `identidade_de_servico` em
`servidor.py`: quando o token real chegar, é ali que ele entra, sem mexer nas
ferramentas nem na persistência.
