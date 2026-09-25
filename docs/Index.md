# Índice da Documentação do AZ1

Navegação central dos documentos do projeto G01, AZ1.

Este índice apresenta somente os documentos consolidados e navegáveis na versão atual do projeto. Novos artefatos devem ser adicionados conforme forem desenvolvidos e validados pela equipe.

## Documentos principais

| Documento | Descrição | Uso esperado |
|---|---|---|
| [Projeto](./Projeto.md) | Documento central do projeto. Reúne o entendimento de negócio (Seção 1), a especificação de requisitos (Seção 2), a definição técnica e arquitetural: APIs de voz, algoritmo de PLN, API de áudio, pilha, modelagem de dados, deploy, estratégia das Sprints 3 a 5 e projeto técnico e arquitetural (Seção 3): e a prototipação exploratória de design e UX (Seção 4). | Consulta principal para compreensão técnica e de negócio da solução. |
| [Gestão do Projeto](./GestaoProjeto.md) | Consolida os acordos permanentes da equipe, o processo de desenvolvimento, o acompanhamento de riscos, as retrospectivas, as ações de melhoria e o planejamento das sprints. | Referência para acompanhamento da organização da equipe e da evolução do projeto. |
| [Gestão de Configuração](./GestaoConfiguracao.md) | Define o Gitflow adotado, o papel das branches, as convenções de nomenclatura, as políticas de commits e Merge Requests, os procedimentos de integração e os exemplos de aplicação. | Referência para versionamento, rastreabilidade e colaboração no GitLab. |
| [Docker](./Docker.md) | Descreve a conteinerização da solução: as imagens de frontend e de API, a topologia dos serviços, os perfis de treino e de teste, as variáveis de ambiente, o uso de segredos, a build multiarquitetura e o processo de deploy. | Referência de operação para subir, testar e implantar a pilha. |
| [Roteiro do Protótipo A](./RoteiroPrototipoA.md) | Roteiro do vídeo encenado do Protótipo A, com as onze cenas que exercitam a interação proativa e contextual do agente, incluindo os casos de erro e de interação por áudio. | Evidência bruta da prototipação exploratória, complementar à Seção 4 do Projeto.md. |

## Guia rápido por tema

| Quero entender… | Ir para |
|---|---|
| O problema, o parceiro e a proposta do produto | [Projeto.md, Entendimento de Negócio](./Projeto.md#1-entendimento-de-negócio) |
| As personas, jornadas e o fluxo de negócio | [Projeto.md, Personas e Jornada](./Projeto.md#15-personas-e-jornada-do-usuário) |
| Os requisitos e a solução técnica | [Projeto.md, Especificação de Requisitos](./Projeto.md#2-especificação-de-requisitos-de-software-sprint-1) |
| Os riscos do projeto, na identificação inicial | [Projeto.md, Matriz de Risco](./Projeto.md#19-matriz-de-risco-do-projeto) |
| Os riscos atualizados e seu histórico por sprint | [GestaoProjeto.md, Matriz de Risco do Projeto](./GestaoProjeto.md#63-matriz-de-risco-do-projeto) |
| As APIs de voz, com endpoints, limites e exemplos | [Projeto.md, API de Speech to Text e Text to Speech](./Projeto.md#32-api-de-speech-to-text-e-text-to-speech) |
| O contrato da API de recebimento de áudios | [Projeto.md, API para Recebimento de Áudios](./Projeto.md#34-api-para-recebimento-de-áudios) |
| A pilha de tecnologias e as razões de cada escolha | [Projeto.md, Pilha de Tecnologias](./Projeto.md#35-pilha-de-tecnologias) |
| Os modelos conceitual, lógico e físico dos dados | [Projeto.md, Modelagem Conceitual e Lógica dos Dados](./Projeto.md#36-modelagem-conceitual-e-lógica-dos-dados) |
| Como criar, popular e verificar o banco de dados | [src/database/README.md](../src/database/README.md) |
| Como implantar a solução em nuvem | [Projeto.md, Processo de Deploy em Nuvem](./Projeto.md#37-processo-de-deploy-em-nuvem) |
| Os webhooks, sua escolha, contrato e tratamento de erros | [Projeto.md, Webhooks](./Projeto.md#51-webhooks) |
| Como ligar o webhook ao Google Drive, passo a passo | [Projeto.md, Manual de operação: Google Drive](./Projeto.md#516-exemplos-e-testes) |
| Como ligar o webhook ao SharePoint, passo a passo | [Projeto.md, Manual de operação: Microsoft Graph](./Projeto.md#516-exemplos-e-testes) |
| Por que as assinaturas de webhook expiram, e como renovar | [Projeto.md, Expiração das Assinaturas](./Projeto.md#517-expiração-das-assinaturas) |
| O que será entregue em cada uma das Sprints 3, 4 e 5 | [Projeto.md, Estratégia de Entrega](./Projeto.md#38-estratégia-de-entrega-para-as-sprints-3-4-e-5) |
| Os diagramas de classes, de componentes e de sequência | [Projeto.md, Projeto Técnico e Arquitetural](./Projeto.md#39-projeto-técnico-e-arquitetural) |
| O algoritmo de PLN, como ele foi escolhido e como rodá-lo | [Projeto.md, Algoritmo de NLP e Implementação](./Projeto.md#33-algoritmo-de-nlp-e-implementação) |
| Como os protótipos foram construídos e executados | [Projeto.md, Prototipação Exploratória](./Projeto.md#4-prototipação-exploratória-design-e-ux) |
| Os testes funcionais executados, resultados, defeitos e limites da liberação | [Projeto.md, Execução dos testes sistêmicos](./Projeto.md#67-execução-dos-testes-sistêmicos--campanha-funcional-da-sprint-4) |
| A gestão das sprints e os acordos da equipe | [GestaoProjeto.md](./GestaoProjeto.md) |
| Os papéis de cada integrante e a evidência da rotação | [GestaoProjeto.md, Matriz de Papéis da Sprint 4](./GestaoProjeto.md#64-matriz-de-papéis-e-responsabilidades-da-sprint-4) |
| Quanto custaria entregar a solução a um cliente real | [GestaoProjeto.md, Análise de Viabilidade Financeira](./GestaoProjeto.md#67-análise-de-viabilidade-financeira) |
| Como o backlog é publicado no GitLab em lote | [GestaoConfiguracao.md, Automação do quadro](./GestaoConfiguracao.md#66-automação-do-quadro-com-o-gitlab-issue-kit) |
| Como subir a pilha inteira em contêineres | [Docker.md](./Docker.md) |
| Por que cada decisão de imagem e de compose foi tomada | [Docker.md, Técnicas aplicadas](./Docker.md#12-técnicas-aplicadas) |
| O Gitflow, as branches, os commits e os MRs | [GestaoConfiguracao.md](./GestaoConfiguracao.md) |
| Se a política de versionamento é seguida na prática | [GestaoConfiguracao.md, Coerência entre Política e Prática](./GestaoConfiguracao.md#7-coerência-entre-política-e-prática) |

## Artefatos visuais

Os diagramas e as imagens utilizados pelos documentos estão armazenados na pasta [`assets`](../assets/). Entre os artefatos atuais estão:

- personas do Diretor, da Analista de PMO e do Líder de Projeto;
- jornadas das três personas;
- Matriz SWOT;
- Matriz de Riscos da Sprint 1 e suas atualizações nas Sprints 2, 3 e 4;
- diagramas de classes, de componentes e de sequência;
- diagramas BPMN dos fluxos AS-IS e TO-BE e a cadeia de valor;
- registros visuais dos protótipos A e B;
- diagrama do fluxo Gitflow;
- diagrama de implantação em nuvem e as capturas dos cinco passos de provisionamento da instância;
- modelos conceitual e lógico-relacional dos dados: o lógico foi regerado na
  Sprint 3 com as tabelas de conversa, trilha, avaliação e eventos;
- linha do tempo de entrega das Sprints 3, 4 e 5.

Os diagramas de classes, de componentes e de sequência criados na Seção 3.9 do `Projeto.md` estão escritos em Mermaid, dentro do próprio documento, e não como arquivos em `assets`. A conversão para SVG, caso a equipe a considere necessária, corresponde às tasks T05 a T07 do planejamento da Sprint 3.

## Estrutura atual da documentação

```text
docs/
├── Index.md
├── Projeto.md
├── GestaoProjeto.md
├── GestaoConfiguracao.md
├── Docker.md
└── RoteiroPrototipoA.md
```
A [auditoria do desenvolvimento](AuditoriaDesenvolvimento.md) reúne rastreabilidade e resultados executados da revisão técnica da Sprint 3.
