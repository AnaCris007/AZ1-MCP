# Execução RNF09 — auditabilidade das interações

**Resultado: REPROVADO**

- Controles executados: 15
- Aprovados: 10
- Reprovados: 5
- Base: PostgreSQL real, dedicada e inicializada pelos scripts versionados
- Dados: exclusivamente sintéticos

## Falhas

- `ACESSO-COMUM` — Consulta da rota administrativa pela identidade comum: HTTP 200; registros=3
- `IMUT-CONV-TITULO` — Renomeação de conversa auditável: operação permitida
- `IMUT-CONV-ARQ` — Arquivamento de conversa auditável: operação permitida
- `PRIVACIDADE` — Senhas/tokens fictícios não persistem na auditoria: mensagem=1; evento=1
- `CONTINGENCIA` — Falha da persistência não perde o evento silenciosamente: registro_tecnico=True; buffer=False; alerta=False; tentativas=1

## Interpretação

O RNF09 exige aprovação de todos os controles. Assim, qualquer falha torna o
resultado global reprovado. Permissões existentes no SQL foram julgadas pelo
texto do requisito e pelo procedimento da Seção 6.3.4, não tratadas como
aprovação automática.
