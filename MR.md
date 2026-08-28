# Documentação do algoritmo de PLN e ajustes no pipeline

## O que este MR faz

Escrevi a Seção 3.3 do `Projeto.md` (Algoritmo de NLP e Implementação) e, para que ela descrevesse
o que o repositório de fato contém, ajustei algumas coisas no código do pipeline.

Parte dessas mudanças já existia e se perdeu num conflito de merge anterior, entre as issues #130 e
#108. Este MR as traz de volta junto com a documentação.

## Documentação

**`docs/Projeto.md`, Seção 3.3 reescrita.** Cobre finalidade e escopo, o algoritmo escolhido com a
justificativa, por que o pipeline combina opções em vez de fixar uma sequência, a arquitetura em
módulos com dois diagramas, o espaço de busca, o método de escolha com os resultados medidos, as
bibliotecas, como executar e o que os testes cobrem. Todos os exemplos de código foram executados
antes de entrar no texto, e os dois diagramas Mermaid foram renderizados para conferência.

Saiu a subseção que registrava a divergência entre o texto e o código: ela existia porque a
documentação descrevia um estado que o repositório havia perdido. Com o código restaurado, a
divergência deixou de existir.

**`docs/PipelinePLN.md` removido.** O conteúdo dele agora vive na Seção 3.3, que é o artefato
avaliado. Manter os dois significava manter duas fontes que divergiriam. `Index.md`, `README.md`,
`GestaoProjeto.md` e `src/pln/README.md` foram atualizados para apontar para a seção.

## Conjunto de treino

**`intencoes_exemplos.csv` passou de 300 para 400 frases**, de 3 classes genéricas para as **10
intenções do catálogo da Seção 3.1**, com 40 exemplos cada.

As frases foram escritas uma a uma, e não geradas por gabarito. O conjunto anterior era produto
cartesiano de 10 modelos de frase por 10 entidades, e isso deixava o benchmark saturado: F1-macro
1,0000 para milhares de configurações, com 77% dos exemplos decididos pela primeira palavra sozinha.

| | Antes (3 classes) | Agora (10 intenções) |
|---|---|---|
| Frases | 300 | 400 |
| Vocabulário | 120 palavras | 793 palavras |
| Decididos pela 1ª palavra | 77% | 20% |
| F1-macro da melhor configuração | 1,0000 (saturado) | 0,6896 |
| Ganho do pré-processamento sobre texto cru | zero | +0,0425 |

## Código

**Vetorização densa por embeddings removida.** Ela não era comparável com as esparsas sob a mesma
régua: vetores de embedding têm coordenadas negativas, que o `MultinomialNB` não aceita, o que
obrigava a trocar de classificador naquela linha do ranking. Com o classificador variando junto com
a representação, a comparação ficava confundida. Medido: a linha `embedding vs esparsas` marcava
−0,2114, dos quais −0,1499 eram só a troca de classificador. O efeito real da representação é
−0,0300. Saíram junto a variante `gaussiano` e a grade de `var_smoothing`, que só ela usava.

**`MultinomialNB` fixo no experimento e no produto.** Foi escolhido pela velocidade, que é o que
torna a varredura exaustiva praticável: 0,029 s por validação cruzada contra 12,472 s da regressão
logística na vetorização mais cara. Usar o mesmo classificador nos dois lugares garante que o
pré-processamento tenha sido escolhido medindo com o modelo que roda em produção.

**`--sem-ordem` removido do experimento.** Além de responder uma pergunta diferente, ele tinha um
defeito silencioso: a ordem que usava não coincidia com a ordem padrão calculada na varredura, e as
três tabelas pareadas do relatório saíam calculadas sobre 15, 30 e 55 grupos em vez de 576, sem erro
e com conclusões que chegavam a inverter.

**Varredura paralelizada.** A fase de avaliação foi separada da de pré-processamento e distribuída
entre processos. As notas saem idênticas em série e em paralelo, porque as tarefas são independentes
e a semente é fixa.

**Critério de desempate ajustado.** Entre configurações empatadas, a ordem padrão passa a vir antes
do F1. Entre permutações do mesmo conjunto de etapas, a diferença de F1 é menor que o desvio entre
dobras, então escolher por ela era escolher ruído.

**Correção no modelo salvo.** `python -m pln.classificador` carrega o módulo como `__main__`, e o
pickle gravava `PreprocessadorDeTexto` com esse caminho, o que tornava o `.joblib` carregável apenas
de dentro do próprio CLI. O agente, que importa `carregar_modelo`, recebia `AttributeError`.

**`entregas/pln_completo.py` e o gerador removidos.** Uma segunda cópia do mesmo código, ainda que
gerada, é superfície a mais para manter e documentar, e nada que ela fazia era inacessível por
`python -m pln.<módulo>`.

**Comentários revisados** nos seis módulos, para o padrão de código de produção: explicam restrição
técnica, incompatibilidade ou convenção, e não teoria nem histórico de decisão.

## Configuração adotada

```python
CONFIG_PRE_PADRAO = ConfigPreprocessamento(
    remover_numeros=True, morfologia=ModoMorfologia.STEMMING, tokenizacao=Tokenizacao.REGEX
)
CONFIG_VET_PADRAO = ConfigVetorizacao(ModoVetorizacao.BOW, n_max=1)
ALPHA_PADRAO      = 1.0
FIT_PRIOR_PADRAO  = True
```

F1-macro de **0,6736** em validação cruzada de 5 dobras. Os relatórios em `resultados/` foram
regerados com este dataset e esta configuração.

## Testes

100 testes do PLN passando, `ruff` limpo.

Acrescentei `tests/test_experimento.py`, que era o único módulo do pipeline sem arquivo de teste, e
foi essa ausência que deixou o defeito do `--sem-ordem` passar. Três testes existem especificamente
para impedir defeitos que não levantam exceção: `TesteNaoRetokeniza`, `TesteReguaUnica` e
`TesteComparacaoPareada`.

```bash
python -m unittest discover tests
```

Os testes de `chat`, `gemini`, `transcription`, `audio` e `storage` falham por dependência ausente
no ambiente local (`fastapi`, `boto3`, `av`, `google-genai`), não por esta mudança. `pip install -e .`
resolve.

## O que fica pendente

**O RNF03 não é atendido.** 0,6736 está 17,6 pontos percentuais abaixo dos 85% exigidos. A classe
`fora_do_catalogo` responde pela maior parte da distância, por ser categoria aberta, sem vocabulário
próprio e compartilhando termos com todas as demais. A Seção 3.3 registra isso explicitamente e
aponta as duas frentes para a Sprint 3: ampliar o dataset e calibrar um limiar de confiança sobre as
nove intenções conhecidas.

**Nenhuma métrica desta seção deve ser apresentada como evidência de atendimento do RNF03.**

**O ajuste fino não paraleliza.** Com `--top-pre 0`, os 20.736 candidatos não cabem em memória no
ambiente atual. O padrão de 5 e o `--top-pre 20` que rodei funcionam. Paralelizar como já se fez no
experimento resolveria.

## Como verificar

```bash
pip install -e .
python -m nltk.downloader stopwords rslp
python -m spacy download pt_core_news_sm
python -m unittest discover tests
python -m pln.classificador
```

Relacionado: #130, #108, #79.
