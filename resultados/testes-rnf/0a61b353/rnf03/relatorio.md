# Execucao do RNF03

- Estado: **Reprovado**
- Conjunto cego: 200 exemplos, 20 por classe, SHA-256 `c51ca6466caf45c068beca25b9d43a94ec20f72f0671e989b071b29bf32c9eb3`
- Modelo: `classificador.joblib`, SHA-256 `75ab09d9249e13bc2d3ecd95d517517f11e4b7721e897f587822c4eec4ea05c5`
- Limiar congelado: **0.20**
- F1-macro: **0.4975** (meta >= 0.85; nao atende)
- Cobertura: **69.4%** (meta >= 90%; nao atende)
- Aceitacao indevida: **15.0%** (meta <= 15%; atende)
- Acertos: 98/200
- Sobreposicoes exatas normalizadas com o historico: 0

A inferencia foi feita uma unica vez com o artefato ja existente. O conjunto cego
nao foi usado para treinar, ajustar o modelo ou escolher o limiar desta execucao.
A verificacao automatica de isolamento cobre coincidencia exata normalizada; a
declaracao formal do custodiante continua sendo evidencia humana separada.
