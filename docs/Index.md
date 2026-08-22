# Índice da Documentação — AZ1

Navegação central dos documentos do projeto G01 — AZ1.

Este índice apresenta somente os documentos consolidados e navegáveis na versão atual do projeto. Novos artefatos devem ser adicionados conforme forem desenvolvidos e validados pela equipe.

## Documentos principais

| Documento | Descrição | Uso esperado |
|---|---|---|
| [Projeto](./Projeto.md) | Documento central do projeto, reunindo contexto do parceiro, problema, visão e objetivo do produto, personas, jornadas, fluxo de negócio, ideação, Canvas do MVP, riscos, requisitos e visão inicial da solução técnica. | Consulta principal para compreensão técnica e de negócio da solução. |
| [Gestão do Projeto](./GestaoProjeto.md) | Consolida os acordos permanentes da equipe, o processo de desenvolvimento, o acompanhamento de riscos, as retrospectivas, as ações de melhoria e o planejamento das sprints. | Referência para acompanhamento da organização da equipe e da evolução do projeto. |
| [Pipeline de PLN](./PipelinePLN.md) | Documentação técnica do módulo `src/az1/pln`: estrutura dos arquivos, as opções de pré-processamento e vetorização, a metodologia de avaliação do experimento, como rodar, como testar e como trocar o dataset. | Referência para quem for mexer no código do pipeline ou interpretar os comparativos. |
| [Gestão de Configuração](./GestaoConfiguracao.md) | Define o Gitflow adotado, o papel das branches, as convenções de nomenclatura, as políticas de commits e Merge Requests, os procedimentos de integração e os exemplos de aplicação. | Referência para versionamento, rastreabilidade e colaboração no GitLab. |

## Guia rápido por tema

| Quero entender… | Ir para |
|---|---|
| O problema, o parceiro e a proposta do produto | [Projeto.md — Entendimento de Negócio](./Projeto.md#1-entendimento-de-negócio) |
| As personas, jornadas e o fluxo de negócio | [Projeto.md — Personas e Jornada](./Projeto.md#15-personas-e-jornada-do-usuário) |
| Os requisitos e a solução técnica | [Projeto.md — Especificação de Requisitos](./Projeto.md#2-especificação-de-requisitos-de-software-sprint-1) |
| Os riscos do projeto | [Projeto.md — Matriz de Risco](./Projeto.md#19-matriz-de-risco-do-projeto) |
| Como o pipeline de PLN funciona e como rodá-lo | [PipelinePLN.md](./PipelinePLN.md) |
| Como trocar o dataset de teste do pipeline | [PipelinePLN.md — Como trocar o dataset](./PipelinePLN.md#9-como-trocar-o-dataset) |
| A gestão das sprints e os acordos da equipe | [GestaoProjeto.md](./GestaoProjeto.md) |
| O Gitflow, as branches, os commits e os MRs | [GestaoConfiguracao.md](./GestaoConfiguracao.md) |

## Artefatos visuais

Os diagramas e as imagens utilizados pelos documentos estão armazenados na pasta [`assets`](../assets/). Entre os artefatos atuais estão:

- personas do Diretor, da Analista de PMO e do Líder de Projeto;
- jornadas das três personas;
- Matriz SWOT;
- Matriz de Riscos;
- diagrama do fluxo Gitflow.

## Estrutura atual da documentação

```text
docs/
├── Index.md
├── Projeto.md
├── PipelinePLN.md
├── GestaoProjeto.md
├── GestaoConfiguracao.md
```