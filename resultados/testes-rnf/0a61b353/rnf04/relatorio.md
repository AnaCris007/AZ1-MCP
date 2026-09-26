# Execução do RNF04 — rastreabilidade das consultas

- Status: **Reprovado**
- Commit: `0a61b353829dee491537bb2863facbe589d48cc8`
- Banco dedicado: `az1_rnf04_0a61b353_20260925_r2`
- Período UTC: 2026-09-25T17:06:03.392431+00:00 a 2026-09-25T17:06:03.480389+00:00
- Interações completas: **10/20 (50.00%)**
- Texto: **10/10**
- Voz: **0/10**
- Falhas controladas rastreadas: **0/2**
- Registro incompleto de controle detectado: **sim**

## Método

As 20 interações passaram pelas rotas reais da aplicação: HTTP para texto e
WebSocket para voz. LLM, STT e TTS tiveram respostas controladas, enquanto a
persistência usou `ConversaRepository` e PostgreSQL real. O checklist consultou
`auditoria.vw_turno`, `auditoria.mensagem_fonte`, avaliações e os objetos de
texto arquivados.

## Conclusão

O critério exige 100% das 20 interações completas, as falhas externas e de
processamento associadas ao mesmo identificador e a detecção do registro
incompleto de controle. O resultado foi **Reprovado**.

## Inconsistências

- `RNF04-V01` (voz): nenhum registro recuperado por conversa_id
- `RNF04-V02` (voz): nenhum registro recuperado por conversa_id
- `RNF04-V03` (voz): nenhum registro recuperado por conversa_id
- `RNF04-V04` (voz): nenhum registro recuperado por conversa_id
- `RNF04-V05` (voz): nenhum registro recuperado por conversa_id
- `RNF04-V06` (voz): nenhum registro recuperado por conversa_id
- `RNF04-V07` (voz): nenhum registro recuperado por conversa_id
- `RNF04-V08` (voz): nenhum registro recuperado por conversa_id
- `RNF04-V09` (voz): nenhum registro recuperado por conversa_id
- `RNF04-V10` (voz): nenhum registro recuperado por conversa_id

As falhas controladas retornaram erro ao cliente, mas não produziram registro correlacionado com `resultado=falha` e `categoria_erro`.

## Validação auxiliar

As suítes focadas das rotas de chat e voz passaram em **41/41 testes**. O
detalhe está em `validacao_auxiliar.md`.
