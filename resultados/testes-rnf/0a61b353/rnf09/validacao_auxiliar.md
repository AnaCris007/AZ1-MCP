# Validação auxiliar do RNF09

- Data: 2026-09-25
- Base: `az1_rnf09_0a61b353_20260925`, dedicada ao ensaio
- Escopo: API de auditoria, lifecycle do MinIO e testes de integração de
  persistência/permissões
- Resultado: 12 testes iniciados; 7 aprovados e 5 encerrados com erro de fixture

Os cinco erros não são falhas de infraestrutura nem resultados dos controles do
RNF09. A fixture de `tests/test_integracao_persistencia.py` tenta inserir
`portfolio.usuario` sem informar `perfil`, coluna atualmente `NOT NULL`. Assim,
esses casos falham durante o `setUp`, antes de executar suas asserções.

A campanha principal não usa essa fixture: criou identidades válidas com perfil
e concluiu todos os 15 controles diretamente no PostgreSQL real. Por isso seu
resultado permanece válido e separado desta dívida da suíte auxiliar.
