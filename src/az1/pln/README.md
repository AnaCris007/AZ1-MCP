# pln/

Pipeline de linguagem natural: decide **como preparar texto** antes de classificar intenções.

> **Documentação completa em [docs/PipelinePLN.md](../../../docs/PipelinePLN.md)** — estrutura do
> código, as opções de cada etapa, a metodologia de avaliação, como testar e como trocar o dataset.
> Este arquivo é só a referência rápida de quem já está na pasta.

| Arquivo | Papel |
|---|---|
| `preprocessamento.py` | texto → tokens |
| `vetorizacao.py` | tokens → matriz numérica |
| `classificador.py` | o modelo do produto — regressão logística |
| `experimento.py` | a busca e as análises |
| `dados/` | datasets rotulados (colunas `texto`, `intencao`) |
| `resultados/` | comparativos gerados, versionados |

## Rodar

```bash
python -m az1.pln.experimento                    # varredura exaustiva (padrão, ~4 min)
python -m az1.pln.experimento --sem-ordem        # só a ordem padrão, rápido
python -m az1.pln.experimento --duas-fases       # busca em estágios, 1/4 das avaliações
python -m az1.pln.experimento --dataset seus.csv --k 10
```

```bash
python -m az1.pln.classificador                                       # treina, avalia e salva
python -m az1.pln.classificador --prever "Quais prazos vencem hoje?"  # usa o modelo salvo
```

```bash
python -m unittest discover tests -v             # 64 testes
```

Dados necessários, uma vez só:

```bash
python -m nltk.downloader stopwords rslp && python -m spacy download pt_core_news_sm
```

## Princípio

Não existe pré-processamento universalmente melhor — nem conjunto de etapas, nem ordem, nem tokenização,
nem vetorização. Nada é assumido: tudo é medido no dataset real, e quem decide é o número.

## O que NUNCA entra

- Regra de negócio do PMO. O pipeline transforma e classifica texto; o que fazer com a intenção é
  responsabilidade de quem chama
- Acesso a banco, configuração de ambiente ou chamada de rede
- Referência a canal de atendimento
