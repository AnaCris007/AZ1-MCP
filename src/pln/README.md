# pln/

Pipeline de linguagem natural: prepara o texto e classifica a intenção da solicitação.

Arquitetura, decisões e resultados dos experimentos estão em
[docs/Projeto.md § 3.3](../../docs/Projeto.md#33-algoritmo-de-nlp-e-implementação).

| Arquivo | Papel |
|---|---|
| `caminhos.py` | caminhos de entrada e saída |
| `preprocessamento.py` | texto para tokens |
| `vetorizacao.py` | tokens para matriz numérica |
| `classificador.py` | o modelo do produto |
| `experimento.py` | busca do texto: pré-processamento × vetorização |
| `ajuste_fino.py` | busca dos parâmetros: suavização × priori × vetorização |
| `dados/` | datasets rotulados (colunas `texto`, `intencao`) |

O classificador é `MultinomialNB` no experimento e no produto. Ele foi escolhido pela velocidade,
que é o que torna a varredura exaustiva praticável, e usá-lo nos dois lugares garante que o
pré-processamento tenha sido escolhido medindo com o modelo que de fato roda.

Saídas geradas vão para `resultados/`, na raiz do repositório.

## Instalação

```bash
pip install -e .
python -m nltk.downloader stopwords rslp
python -m spacy download pt_core_news_sm
```

## Uso

```bash
python -m pln.classificador                                       # treina, avalia e salva
python -m pln.classificador --prever "Quais prazos vencem hoje?"  # usa o modelo salvo
```

As duas buscas rodam nesta ordem, porque o ajuste fino lê o relatório que o experimento grava:

```bash
python -m pln.experimento      # varredura exaustiva, ~6 min
python -m pln.ajuste_fino      # ~40 s
```

Colar os valores recomendados por elas nos padrões de `classificador.py` é passo manual.

## Testes

```bash
python -m unittest discover tests
```
