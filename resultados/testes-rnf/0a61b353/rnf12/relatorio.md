# Execução RNF12 — fundamentação das respostas de consulta

**Resultado: REPROVADO**

- Casos: `CT-RNF12-P` e `CT-RNF12-N`
- Commit: `0a61b353829dee491537bb2863facbe589d48cc8`
- Massa: 30 consultas positivas, 10 negativas e 8 documentos sintéticos
- Execução: 40/40 respostas HTTP 200

## Resultado observado

Das 30 consultas positivas, apenas quatro produziram uma resposta factual com
fonte (`P05`, `P15`, `P17` e `P26`). As quatro referências apresentadas foram
recuperadas no índice, atendendo isoladamente ao controle de existência da
referência.

As outras 26 positivas não entregaram a informação sustentada que existia na
massa. A resposta predominante foi “Não encontrei o projeto informado”. Em
`P21`, o sistema devolveu fatos sobre oito projetos diferentes sem apresentar
nenhuma fonte.

Mesmo usando a decomposição mais conservadora, há quatro afirmações candidatas
a sustentadas e pelo menos oito afirmações factuais sem citação em `P21`. Assim,
o melhor percentual possível nesse subconjunto é `4 / 12 = 33,33%`, já abaixo
da meta de 90%. As avaliações humanas podem rebaixar alguma das quatro
candidatas, mas não conseguem elevar esse teto; por isso a reprovação não
depende de fabricar rubricas.

No cenário negativo, apenas `N01`, `N02` e `N03` informaram uma limitação
compatível com a fonte ausente preparada. Nos demais, o sistema tratou
evidência insuficiente, conflito ou fonte irrelevante como projeto inexistente
ou solicitação fora do catálogo. Resultado: 3/10 limitações compatíveis, contra
a exigência de 10/10.

## Critérios

- Referências apresentadas e recuperáveis: **4/4 (100%)**.
- Afirmações sustentadas: **no máximo 33,33% no subconjunto factual mínimo**, abaixo de 90%.
- Negativas com limitação compatível: **3/10 (30%)**, abaixo de 100%.

O RNF12 está reprovado porque os critérios são cumulativos. A recuperação das
quatro referências não compensa a ausência de fundamentação nas demais
respostas nem o tratamento incorreto dos cenários negativos.

## Evidências

- `respostas_execucao.json`: respostas completas, fontes e recuperabilidade;
- `execucao_tecnica.json`: consolidação automática da rodada;
- `avaliacao_tecnica.csv`: decomposição mínima que estabelece o teto de 33,33%;
- `outputs/rnf12/campanha_rnf12_executada.xlsx`: consultas, gabaritos,
  respostas e campos preservados para avaliações independentes posteriores.

As colunas dos dois avaliadores e do desempate permanecem vazias. Elas podem ser
preenchidas para caracterizar cada falha, mas não são necessárias para alterar
o resultado já determinado pelos limites objetivos observados.
