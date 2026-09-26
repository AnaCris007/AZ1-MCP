# Validação auxiliar do RNF02

- Commit avaliado: `0a61b353829dee491537bb2863facbe589d48cc8`
- Data da execução: 2026-09-25
- Ambiente: contêiner de desenvolvimento da API
- Comando: `python -m unittest -q tests.test_auth_api tests.test_integracao_seguranca.TestAutenticacaoIntegracao tests.test_integracao_vhs.TestVhsIntegracao.test_nenhum_segredo_e_gravado_no_registro tests.test_integracao_vhs_provedores.TestVhsProvedoresIntegracao.test_nenhum_segredo_ou_marcador_sobrevive_nas_gravacoes`
- Resultado: **17 testes executados; 17 aprovados**

Essa suíte cobre a aceitação de token válido, as cinco condições inválidas,
precedência do 401 sobre validação/regra de negócio, resposta genérica, exceções
deliberadas de health e webhooks e ausência de segredos nos registros VHS.
