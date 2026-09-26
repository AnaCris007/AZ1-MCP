# Defeito RNF03 — modelo atualizado não generaliza no novo conjunto cego

- Estado: Aberto
- Severidade sugerida: Alta
- Responsável nominal: A definir pela equipe de PLN
- Versão afetada: commit `0a61b353829dee491537bb2863facbe589d48cc8`
- Casos: `CT-RNF03-P` e `CT-RNF03-N`
- Modelo: `classificador.joblib`, SHA-256 `75ab09d9249e13bc2d3ecd95d517517f11e4b7721e897f587822c4eec4ea05c5`
- Conjunto: `CSV_1.csv`, SHA-256 `c51ca6466caf45c068beca25b9d43a94ec20f72f0671e989b071b29bf32c9eb3`
- Limiar congelado: 0,20

## Resultado esperado

Atender simultaneamente a F1-macro mínima de 0,85, cobertura mínima de 90% nas
intenções conhecidas e aceitação indevida máxima de 15% nos exemplos
`fora_do_catalogo`.

## Resultado observado

- F1-macro: 0,4975 — falhou.
- Cobertura: 69,44% — falhou.
- Aceitação indevida: 15,00% (3 de 20) — passou no limite.
- Acertos finais: 98 de 200.
- Intenções conhecidas classificadas como `fora_do_catalogo`: 55 de 180.
- Rejeições adicionais pelo limiar de 0,20: 0; a menor confiança observada foi 0,2125.

As classes com menor F1 foram `consultar_projeto_sintetico` (0,1538),
`gerar_alertas_pendencias` (0,3478) e `orientar_entregas_cronograma` (0,3571).

## Reprodução

```bash
PYTHONPATH=src .venv/bin/python scripts/executar_rnf03.py \
  --conjunto assets/data/CSV_1.csv \
  --saida resultados/testes-rnf/0a61b353/rnf03
```

O código de saída esperado para a falha dos critérios é 1. As previsões
individuais, a matriz de confusão e o resumo estão preservados na mesma pasta.

## Política de reteste

Este conjunto agora foi revelado ao processo de avaliação. Se seus exemplos ou
resultados forem usados para alterar corpus, pré-processamento, modelo,
hiperparâmetros ou limiar, ele não poderá ser reutilizado como teste final. O
próximo reteste deverá usar outro conjunto cego inédito.
