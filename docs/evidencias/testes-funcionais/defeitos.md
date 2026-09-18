# Problemas encontrados e ações corretivas

Commit candidato: `f1b3591123f2488791012dfeebaa0b6b04c601bb`. Rodada de
18/09/2026. Nenhuma correção de regra de negócio foi aplicada nesta task de
testes. Este documento é o registro local dos problemas da campanha acadêmica;
as evidências e ações propostas são suficientes para registrar as reprovações.
Não se exige abrir issues no GitLab nesta task.

## DF-01 — RF02 consulta fontes para solicitação fora do domínio

- **Caso / prioridade:** CT-RF02-07; alta.
- **Classificação:** defeito de implementação diante do critério de RF02.
- **Entrada:** `Qual a previsão do tempo em Marte?`.
- **Passos:** injetar busca instrumentada no `GeminiChatModel` real; integrar
  ao `AnswerChatMessage` e à rota; enviar POST `/api/v1/chat`; contar buscas.
- **Esperado:** informar limite sem consultar fontes; zero chamadas à busca.
- **Observado:** uma chamada à busca e resposta de recusa por falta de evidência.
  A recusa segura final não satisfaz a proibição de consulta.
- **Evidência:** registro CT-RF02-07 de [funcionais.json](funcionais.json) e
  [log da campanha](funcionais.log). Cliente externo do modelo não foi chamado.
- **Ação proposta:** identificar intenção/escopo antes da recuperação; recusar
  fora do domínio sem consulta. Não mudar o oráculo para aceitar a busca atual.
- **Diagnóstico adicional:** o modelo treinado classificou a pergunta sobre
  Marte como `consultar_projeto_sintetico`, com confiança aproximadamente 0,382.
  Ver [previsões do classificador](classificador-diagnostico.json). Ligar esse
  classificador antes da busca, isoladamente, não corrige o exemplo. Não foi
  introduzido um limiar arbitrário nem uma regra específica para a frase apenas
  para obter aprovação; a melhoria depende de revisar classificação/diálogo.
- **Reteste necessário:** casos cegos fora do domínio, negação e consultas
  legítimas; contar zero buscas nas recusas e preservar consulta válida.
- **Estado:** falha documentada; correção e reteste são melhorias futuras.

## DF-02 — RF02 consulta fontes antes de esclarecer projeto ausente

- **Caso / prioridade:** CT-RF02-06; alta.
- **Classificação:** defeito de implementação diante do critério de RF02.
- **Entrada:** `Qual é o avanço do projeto?` em conversa nova.
- **Passos:** preparar recuperação instrumentada sem contexto anterior;
  enviar POST `/api/v1/chat`; inspecionar busca e resposta.
- **Esperado:** solicitar projeto faltante antes de consultar fontes.
- **Observado:** uma chamada à busca; resposta genérica de ausência de fundamento,
  sem resolver o projeto que falta. Não houve chamada ao gerador externo.
- **Evidência:** registro CT-RF02-06 de [funcionais.json](funcionais.json).
- **Ação proposta:** extrair/verificar projeto e dado antes da recuperação;
  implementar esclarecimento explícito e retomada após resposta do usuário.
- **Reteste necessário:** projeto ausente, indicador ausente, nomes semelhantes
  e retomada; nenhuma busca de negócio antes de dados suficientes.
- **Estado:** falha documentada; correção e reteste são melhorias futuras.

## OBS-01 — feedback de indisponibilidade genérico na interface

- **Caso / prioridade:** CT-RF01-15; média; observação técnica de interface.
- **Ambiente:** Chrome nativo, frontend Vite real em `127.0.0.1:5175`, harness
  `/tests/functional.html`, componente `AgentPage` e cliente HTTP reais.
  O harness dispensa a tela de login somente neste ensaio isolado; não é SSO.
- **Entrada:** `Qual o status do SYN-01?`, com API da porta 8010 ausente.
- **Observado:** proxy informa `ECONNREFUSED`; tela exibe `Ocorreu um erro
  inesperado ao processar sua mensagem. Tente novamente.`. Nenhum dado de
  demonstração foi apresentado. O erro aparece com botões de ouvir e avaliar
  resposta, o que pode confundir o usuário sobre a natureza da mensagem.
- **Evidência:** [captura recortada](CT-RF01-15.png),
  [registro de navegador](navegador.json), [log do proxy](navegador-proxy.log).
- **Ação proposta:** distinguir indisponibilidade de erro interno e separar
  mensagens de erro das ações de reprodução/avaliação de resposta.
- **Estado:** ausência de conteúdo fictício verificada; aceite sistêmico do
  fluxo autenticado e compreensão com participantes permanecem pendentes.
  Não atribuir esta observação a feedback externo inexistente.

## Preparação e problemas do instrumento — não são reprovações de RF

| Registro | Problema | Ação aplicada / resultado |
|---|---|---|
| Docker do host | Daemon desligado e acesso sujeito à permissão | Docker Desktop iniciado; execução autorizada em ambiente dedicado |
| MinIO Docker Hub | Pull da imagem configurada recusado | Mesma release obtida em `quay.io/minio/minio`; ver `minio-start.log` |
| `backend-rodada1.log` | Oito erros por arquivos ausentes no contêiner (`infra`, `requirements.txt`, `docs`) | Mounts somente de leitura acrescentados; rodada final com 502 testes aprovados |
| `funcionais-preparacao-rodada2.log` | Reexecução encontrou bucket já pertencente ao executor | Script aceita somente `BucketAlreadyOwnedByYou` para a mesma massa; outros erros permanecem fatais; rodada final executada |
| Browser connector | Nenhum navegador conectado ao controle de abas | Chrome nativo controlado via CUA; captura real do ensaio de indisponibilidade |
| `frontend-lint.log` | Oito avisos React em código existente | Registrar para triagem; não corrigidos nem omitidos nesta task |
| `frontend-build.log` | Aviso de bundle superior a 500 kB | Build passou; otimização deve ser avaliada separadamente |
