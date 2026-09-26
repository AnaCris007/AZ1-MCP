# Defeitos encontrados no RNF09

## RNF09-D01 — rota administrativa acessível a usuário comum

Uma identidade comum autenticada recebeu HTTP 200 em
`GET /api/v1/auditoria/consultas` e obteve os três registros da massa. A rota
está protegida por autenticação, mas não verifica atributo administrativo.

## RNF09-D02 — conversa auditável pode ser alterada

O papel `az1_app` conseguiu atualizar `auditoria.conversa.titulo` e
`auditoria.conversa.arquivada_em`. O planejamento do RNF09 determina que somente
o feedback pode receber atualização controlada; renomear ou arquivar a conversa
deve ser classificado como falha mesmo quando o SQL atual concede a permissão.

## RNF09-D03 — ausência de sanitização de segredos fictícios

O caminho real de `ConversaRepository` persistiu os marcadores sintéticos de
senha/token em `auditoria.mensagem.conteudo`. O banco também aceitou o marcador
em `auditoria.evento_plataforma.detalhe`. O comentário no DDL declara a
proibição, mas não há controle que a imponha.

## RNF09-D04 — falha de auditoria sem contingência completa

Com a persistência indisponível, ocorreu uma tentativa e foi emitido um log
técnico. Não foram observados buffer, alerta operacional nem nova tentativa.
Logo, o evento continua sujeito a perda silenciosa após o log.

