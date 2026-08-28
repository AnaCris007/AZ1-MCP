# pln/

Pipeline de linguagem natural: decide **como preparar texto** antes de classificar intenções.

> **Documentação completa em [docs/PipelinePLN.md](../../docs/PipelinePLN.md)** — estrutura do
> código, as opções de cada etapa, a metodologia de avaliação, como testar e como trocar o dataset.
> Este arquivo é só a referência rápida de quem já está na pasta.

| Arquivo | Papel |
|---|---|
| `caminhos.py` | onde ficam os dados e para onde vão os resultados |
| `preprocessamento.py` | texto → tokens |
| `vetorizacao.py` | tokens → matriz numérica |
| `classificador.py` | o modelo do produto — Naive Bayes |
| `experimento.py` | a busca do **texto** — pré-processamento × vetorização |
| `ajuste_fino.py` | a busca do **modelo** — variante × suavização × priori |
| `dados/` | datasets rotulados (colunas `texto`, `intencao`) |

Saídas geradas **não** ficam aqui. Vão para `resultados/`, na raiz do repositório: comparativos e
modelo treinado são artefato de execução, não código-fonte.

## Rodar

```bash
python -m pln.experimento                    # varredura exaustiva
python -m pln.experimento --sem-ordem        # só a ordem padrão, rápido
python -m pln.experimento --dataset seus.csv --k 10
```

Depois do experimento — o ajuste fino lê o relatório que ele grava:

```bash
python -m pln.ajuste_fino                    # sobre os 5 melhores pré-processamentos
python -m pln.ajuste_fino --top-pre 0        # sobre todos
```

```bash
python -m pln.classificador                                       # treina, avalia e salva
python -m pln.classificador --prever "Quais prazos vencem hoje?"  # usa o modelo salvo
```

```bash
python -m unittest discover tests -v         # 106 testes
```

Dados necessários, uma vez só:

```bash
python -m nltk.downloader stopwords rslp
python -m spacy download pt_core_news_sm    # lematização e tokenização linguística
python -m spacy download pt_core_news_md    # vetores da vetorização densa
```

## O arquivo único de entrega

`entregas/pln_completo.py` é este pipeline inteiro em um arquivo só, que roda sem instalar o pacote.
Ele é **gerado**, nunca editado à mão:

```bash
python scripts/gerar_pln_completo.py         # regera a partir de src/pln/
python entregas/pln_completo.py treinar
python entregas/pln_completo.py experimento
python entregas/pln_completo.py ajuste
```

`tests/test_entrega_unica.py` falha se ele estiver diferente do que o gerador produziria — é o que
impede a entrega de divergir dos módulos.

## Princípio

Não existe pré-processamento universalmente melhor — nem conjunto de etapas, nem ordem, nem tokenização,
nem vetorização. Nada é assumido: tudo é medido no dataset real, e quem decide é o número.

> **Ressalva atual.** No dataset de exemplo as duas buscas saturam: F1-macro 1,0000 para milhares de
> configurações no experimento, e 2010 de 3000 candidatos empatados no ajuste fino. Elas medem certo,
> mas não conseguem mais ORDENAR — as frases são geradas por gabarito e fáceis demais. Ver a ressalva em
> `classificador.py` e a seção 7.1 de [docs/PipelinePLN.md](../../docs/PipelinePLN.md).

> **Sobre a vetorização densa.** Os vetores do `pt_core_news_md` são fastText **CBOW**, não Word2Vec
> skip-gram — por isso o modo se chama `embedding`. Ver a seção 5.2 da documentação.

## O que NUNCA entra

- Regra de negócio do PMO. O pipeline transforma e classifica texto; o que fazer com a intenção é
  responsabilidade de quem chama
- Acesso a banco, configuração de ambiente ou chamada de rede
- Referência a canal de atendimento
