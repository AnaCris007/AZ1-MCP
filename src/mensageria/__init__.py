"""Barramento de mensagens assíncrono da Sprint 5 (Seção 6.4.4).

O receptor de webhook é o PRODUTOR deste barramento; um worker autônomo
(`mensageria.consumidor`) é o CONSUMIDOR que faz a varredura da origem marcada
como pendente. A publicação é ADITIVA e OPCIONAL: sem `RABBITMQ_URL` o
comportamento da Sprint 4 permanece intacto (publicador no-op); com
`RABBITMQ_URL` cada evento é publicado no barramento além de marcar
`delta_pendente = TRUE`, e o consumidor o marca de volta como `FALSE`.
"""
