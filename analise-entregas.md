# Análise Completa das Entregas — Projeto AZ1 (G01)

> Documento de análise crítica e consolidada de tudo que foi produzido na Sprint 1.
> Módulo 7 — Inteli, Instituto de Tecnologia e Liderança — 2026.

---

## Sumário

- [1. Visão Geral do Projeto](#1-visão-geral-do-projeto)
- [2. Mapa de Entregas](#2-mapa-de-entregas)
- [3. Análise Aprofundada — Trabalhos de Paulo Henrique](#3-análise-aprofundada--trabalhos-de-paulo-henrique)
  - [3.1 Definição do Problema](#31-definição-do-problema)
  - [3.2 Matriz SWOT](#32-matriz-swot)
  - [3.3 Visão do Produto e Features Priorizadas](#33-visão-do-produto-e-features-priorizadas)
- [4. Análise dos Arquivos de Gestão](#4-análise-dos-arquivos-de-gestão)
  - [4.1 GestaoProjeto.md](#41-gestaoprojetomd)
  - [4.2 GestaoConfiguracao.md](#42-gestaoconfiguracacaomd)
- [5. Demais Artefatos do Projeto](#5-demais-artefatos-do-projeto)
  - [5.1 Contexto da Indústria](#51-contexto-da-indústria)
  - [5.2 Personas e Jornadas](#52-personas-e-jornadas)
  - [5.3 Fluxo de Negócio (AS-IS / TO-BE)](#53-fluxo-de-negócio-as-is--to-be)
  - [5.4 Canvas do MVP e Tecnologias](#54-canvas-do-mvp-e-tecnologias)
  - [5.5 Requisitos Funcionais e Não-Funcionais](#55-requisitos-funcionais-e-não-funcionais)
  - [5.6 Arquitetura e Modelagem Técnica](#56-arquitetura-e-modelagem-técnica)
  - [5.7 Matriz de Risco](#57-matriz-de-risco)
- [6. Artefatos de Suporte e Infraestrutura](#6-artefatos-de-suporte-e-infraestrutura)
- [7. Avaliação Geral da Sprint 1](#7-avaliação-geral-da-sprint-1)

---

## 1. Visão Geral do Projeto

| Campo | Detalhe |
|---|---|
| **Nome** | AZ1 |
| **Grupo** | G01 |
| **Módulo** | 7 |
| **Versão entregue** | v0.1.0 (Sprint 1 — 14/08/2026) |
| **Parceiro** | PMO Corporativo do Metrô de São Paulo |
| **Natureza da solução** | Agente de IA conversacional para gestão de portfólio de projetos |
| **Dados utilizados** | Sintéticos (restrição do parceiro — nenhum dado real) |

**Equipe:**

| Integrante | LinkedIn |
|---|---|
| Ana Cristina Jardim | [linkedin.com/in/ana-cristina-jardim](https://www.linkedin.com/in/ana-cristina-jardim/) |
| Felipe Simão | [linkedin.com/in/felipefmsimao](https://www.linkedin.com/in/felipefmsimao/) |
| Karol Barbosa Rocha | [linkedin.com/in/karolbarbosarocha](https://www.linkedin.com/in/karolbarbosarocha/) |
| Matheus Ferreira da Silva | [linkedin.com/in/matheusferreirads-](https://www.linkedin.com/in/matheusferreirads-/) |
| Paulo Henrique Bueno Fernandes | [linkedin.com/in/paulo-henrique0601](https://www.linkedin.com/in/paulo-henrique0601/) |
| Rui Facó | [linkedin.com/in/ruifacó](https://www.linkedin.com/in/ruifac%C3%B3/) |
| Tobias Viana | [linkedin.com/in/tobias-viana](https://www.linkedin.com/in/tobias-viana/) |

**Orientadora:** Vanessa Nunes

---

## 2. Mapa de Entregas

Todos os artefatos previstos para a Sprint 1 foram entregues. A tabela abaixo mapeia o que foi produzido, por quem e onde está.

| Artefato | Responsável principal | Localização |
|---|---|---|
| Definição do Problema | **Paulo Henrique** | `docs/Projeto.md` — Seção 1.1 |
| Matriz SWOT | **Paulo Henrique** | `docs/Projeto.md` — Seção 1.1 / `assets/negócios/swot.png` |
| Visão do Produto e Features | **Paulo Henrique** | `docs/Projeto.md` — Seções 1.3 e 1.7 |
| Contexto da Indústria | Felipe Simão | `docs/Projeto.md` — Seção 1.2 |
| Persona + Jornada: Diretor | Karol Barbosa Rocha | `docs/Projeto.md` — Seção 1.5 / `assets/design/` |
| Persona + Jornada: PMO | Matheus Ferreira | `docs/Projeto.md` — Seção 1.5 / `assets/design/` |
| Persona + Jornada: Líder | Felipe Simão | `docs/Projeto.md` — Seção 1.5 / `assets/design/` |
| Fluxo de Negócio (AS-IS/TO-BE) | Tobias Viana | `docs/Projeto.md` — Seção 1.6 / `assets/negócios/` |
| Canvas do MVP | Rui Facó | `docs/Projeto.md` — Seção 1.8 |
| Tecnologias e Ferramentas | Rui Facó | `docs/Projeto.md` — Seção 2.5 |
| Requisitos Funcionais | Ana Cristina Jardim | `docs/Projeto.md` — Seção 2.2 |
| Requisitos Não-Funcionais | Karol Barbosa Rocha | `docs/Projeto.md` — Seção 2.3 |
| Visão Técnica e Arquitetura | Matheus Ferreira | `docs/Projeto.md` — Seção 2.4 |
| Modelagem (classes, sequência) | Ana Cristina Jardim | `docs/Projeto.md` / `assets/*.svg` |
| Matriz de Risco | Ana Cristina Jardim | `docs/Projeto.md` — Seção 1.9 / `assets/negócios/` |
| Gestão do Projeto | **Paulo Henrique** (org.) + time | `docs/GestaoProjeto.md` |
| Gestão de Configuração | Time (coletivo) | `docs/GestaoConfiguracao.md` |
| README principal | Time (coletivo) | `README.md` |
| Índice de documentação | Time (coletivo) | `docs/Index.md` |
| gitlab-issue-kit | Time (coletivo) | `gitlab-issue-kit/` |
| Scripts de banco de dados | Time (coletivo) | `src/database/` |

---

## 3. Análise Aprofundada — Trabalhos de Paulo Henrique

Esta seção foca nos artefatos de responsabilidade direta de Paulo Henrique Bueno Fernandes, conforme a Matriz de Papéis e Responsabilidades registrada no `GestaoProjeto.md`.

---

### 3.1 Definição do Problema

**Localização:** `docs/Projeto.md`, Seção 1.1  
**Papel definido na matriz:** "Compreensão do Problema e Visão do Produto" — responsável pela descrição do desafio e elaboração da SWOT.

#### O que foi entregue

A seção de problema entregue vai muito além de uma simples declaração de dificuldade. O texto foi estruturado em camadas progressivas de profundidade:

1. **Contexto operacional do parceiro** — apresentação do PMO Corporativo do Metrô, volume de empreendimentos (8 a 10 anos de duração, investimentos bilionários, centenas de contratos, dezenas de milhares de documentos), posicionando o leitor antes de qualquer diagnóstico.

2. **Diagnóstico da lacuna real** — identificação precisa de que o problema **não é** a ausência de processos ou ferramentas, mas o custo de interagir com eles. Essa distinção é fundamental: evita que a solução seja enquadrada como substituta dos sistemas existentes.

3. **Descrição do atrito operacional** — detalha os comportamentos concretos que consomem tempo: navegar por arquivos, listas e sistemas; aplicar filtros manualmente; analisar resultados dispersos; preencher campos obrigatórios com acesso às ferramentas corretas.

4. **Impacto no negócio** — conecta o atrito operacional a consequências reais: atrasos em análises, aumento de esforço em relatórios, e **limitação da capacidade preventiva do PMO** de identificar riscos, pendências e desvios antes que se tornem problemas.

5. **Agravante setorial** — contextualiza que empreendimentos com recursos públicos e impacto social direto tornam a rapidez e a confiabilidade das informações ainda mais críticas.

6. **Enunciado do problema central** — sintetiza tudo em uma frase precisa: *"tornar mais ágil, simples e intuitiva a consulta e a adição de informações na estrutura de gestão documental já utilizada pelo Metrô."*

7. **Proposta de direção da solução** — encerra com o enquadramento da IA como *nova camada de interação*, preservando processos, permissões e rastreabilidade.

#### Pontos fortes

- **Clareza do escopo negativo:** ao afirmar explicitamente que o problema não é ausência de estrutura, o texto previne o erro mais comum em projetos de IA corporativa — propor substituição onde a integração é o que o parceiro precisa.
- **Progressão lógica:** o raciocínio avança do contexto → diagnóstico → impacto → gravidade setorial → enunciado → direção. Não há saltos ou afirmações sem embasamento.
- **Linguagem técnica adequada:** a densidade de informação é alta, mas sem jargões desnecessários, o que torna o documento acessível para avaliadores técnicos e de negócio.
- **Alinhamento com o TAPI:** toda a delimitação ("não substituir sistemas") reflete diretamente os limites impostos pelo parceiro.

#### Pontos de atenção

- O problema está muito bem descrito, mas a seção ainda não quantifica o impacto atual (ex.: "uma consulta simples demanda X minutos"). Métricas de linha de base poderiam fortalecer ainda mais a justificativa para a solução proposta — algo que pode ser incorporado em sprints futuras com dados levantados junto ao parceiro.

---

### 3.2 Matriz SWOT

**Localização:** `docs/Projeto.md`, Seção 1.1 (imediatamente após a definição do problema)  
**Ativo visual:** `assets/negócios/swot.png`

#### O que foi entregue

A Matriz SWOT foi elaborada com foco específico no contexto do **PMO Corporativo e na gestão de informações de empreendimentos**, não na companhia como um todo — uma escolha de escopo que torna a análise muito mais útil e acionável para o projeto.

**Forças (Fatores Internos Positivos):**

| Força | Relevância para o projeto |
|---|---|
| Ampla experiência em gestão de empreendimentos de grande porte | Valida que os processos do parceiro já funcionam e que a solução deve integrar, não substituir |
| Profissionais especializados | Indica que a IA deve apoiar especialistas, não simplificar demais |
| Processos consolidados de governança e gestão documental | Confirma que o problema não é estrutural — é de interface |
| PMO Corporativo estruturado | Há um ponto de entrada claro e governança para adoção da solução |

**Fraquezas (Fatores Internos Negativos):**

| Fraqueza | Relevância para o projeto |
|---|---|
| Dimensão e complexidade das operações | Escala que amplifica o atrito operacional identificado no problema |
| Grande volume de documentos e longos períodos de execução | Justifica diretamente o agente conversacional como forma de navegar esse volume |
| Esforço manual de consolidação e verificação | Evidencia o custo operacional que a solução deve reduzir |
| Risco de inconsistências nos dados | Motiva o módulo de alertas e sugestões de preenchimento do agente |

**Oportunidades (Fatores Externos Positivos):**

| Oportunidade | Relevância para o projeto |
|---|---|
| Evolução contínua de IA, PLN e integração de dados | Sustenta a viabilidade técnica do projeto |
| Iniciativas de IA já em andamento no Metrô | Reduz barreira de adoção — o parceiro não está partindo do zero |
| Abertura institucional comprovada para novas tecnologias | Diminui risco de rejeição organizacional |
| Potencial de ampliar e especializar aplicações de IA | O projeto pode ser ponto de partida de um programa maior |

**Ameaças (Fatores Externos Negativos):**

| Ameaça | Relevância para o projeto |
|---|---|
| Restrições orçamentárias | Impacto na continuidade e sustentação da solução |
| Mudanças regulatórias | Podem alterar regras de acesso e confidencialidade |
| Dependência de fornecedores | Reforça a decisão de manter o núcleo desacoplado (RNF05) |
| Riscos de segurança da informação | Justifica o uso exclusivo de dados sintéticos no MVP |
| Possível troca da plataforma de gestão de portfólio | **Ameaça de alta relevância** que motivou diretamente o RNF05 — desacoplamento do núcleo PLN |

#### Pontos fortes da análise

- **SWOT como instrumento de rastreabilidade:** cada quadrante se conecta visivelmente a decisões de produto (escopo, restrições, requisitos não-funcionais). Não é uma SWOT genérica — é uma SWOT funcional.
- **Ameaça de troca de plataforma:** identificar que o Metrô pode mudar sua ferramenta de portfólio é uma insight de alto valor que diretamente justifica a decisão arquitetural de desacoplamento — essa conexão foi explicitada no texto.
- **Sequenciamento com o problema:** a SWOT aparece imediatamente após a definição do problema, aprofundando o entendimento do contexto antes de partir para a visão do produto — fluxo correto de raciocínio estratégico.
- **Texto analítico além da imagem:** além da imagem `swot.png`, foi produzida uma análise textual de cada quadrante com profundidade, o que agrega muito mais valor do que simplesmente listar itens na matriz visual.

#### Pontos de atenção

- O texto da SWOT é rico, mas poderia explicitar de forma mais direta a **interação entre quadrantes** (ex.: "a Força X combinada com a Oportunidade Y permite Z", ou "a Fraqueza W agravada pela Ameaça V cria risco de X"). Análises cruzadas (SO, WO, ST, WT) tornariam a SWOT ainda mais estratégica.
- A imagem `swot.png` está referenciada mas não foi possível avaliar visualmente neste documento — recomenda-se verificar se os itens visuais estão consistentes com o texto analítico.

---

### 3.3 Visão do Produto e Features Priorizadas

**Localização:** `docs/Projeto.md`, Seções 1.3 e 1.7  
**Responsabilidade:** definição da visão, escopo do produto e brainstorming + priorização de features.

#### O que foi entregue — Visão do Produto (Seção 1.3)

A visão do produto está estruturada em três camadas complementares:

**1. Descrição geral do agente AZ1:**
- Pipeline de PLN próprio (desenvolvido e avaliado pela equipe)
- Interface conversacional por texto e por voz
- Catálogo de intenções controlado (consulta, transação, alerta)
- Dados sintéticos no MVP

**2. Tabela do que o produto FAZ (12 funcionalidades mapeadas):**

| # | Funcionalidade | Destaque analítico |
|---|---|---|
| 1-2 | Interação por texto e por voz | Duplo canal de entrada aumenta acessibilidade |
| 3 | Interpretação e classificação de intenções | Núcleo técnico — PLN próprio |
| 4 | Controle do catálogo de intenções | Segurança de escopo — recusa interações fora de contexto |
| 5-6 | Consultas sobre projetos e normativos | Casos de uso primários do PMO |
| 7-9 | Apoio à análise e respostas estruturadas | Diferencial de qualidade de resposta |
| 10 | Alertas proativos | Capacidade preventiva — um dos principais benefícios |
| 11 | Sugestões de preenchimento | Inovação de experiência — IA que propõe, humano que decide |
| 12 | Segurança e governança | Requisito não-negociável do parceiro |

**3. Tabela do que o produto NÃO FAZ (10 itens explícitos de fora de escopo):**

Esta é uma das partes mais valiosas da visão. Delimitar o que **não** está no escopo com justificativas explícitas:
- Previne expectativas equivocadas do parceiro
- Protege o time de escopo que cresce sem controle
- Demonstra maturidade na gestão de produto

Os 10 itens fora de escopo cobrem: dados reais, integração com produção, ações automáticas sem aprovação humana, tomada de decisão, substituição de sistemas, acesso indevido, respostas fora do catálogo, respostas conclusivas sem dados e cobertura total do ambiente corporativo.

**Delimitação do MVP:** a seção encerra com um resumo executivo preciso — *"o agente consulta, interpreta, compara, responde, alerta e sugere preenchimentos utilizando dados sintéticos. O profissional analisa, registra e decide."*

#### Pontos fortes

- **Escopo positivo + negativo:** documentar tanto o que faz quanto o que não faz é uma prática madura que poucos documentos de produto de sprint inicial atingem com essa completude.
- **Coerência com o problema:** cada funcionalidade do escopo positivo é rastreável a um ponto de atrito identificado na seção 1.1.
- **Responsabilidade humana preservada:** a decisão de fazer as transações serem apenas sugestivas (sem escrita automática em sistemas) está explicitada e justificada — é uma decisão de produto, não uma limitação técnica.

---

## 4. Análise dos Arquivos de Gestão

### 4.1 GestaoProjeto.md

**Localização:** `docs/GestaoProjeto.md`  
**Natureza:** documento evolutivo — seção 2 é permanente; seções 3+ são acumuladas por sprint.

#### Estrutura e completude

O documento cobre quatro grandes blocos:

**Bloco 1 — Contrato de Convivência e SLA**

| Item | Detalhe entregue |
|---|---|
| Regra de Ouro | Entregas finalizadas até quinta-feira (Day -2 da Sprint Review) |
| Resolução de impasses técnicos | Maioria simples → empate → roleta entre empatados |
| Gestão de conflitos | 3 níveis: informal no Daily → retrospectiva → escalada ao orientador |
| Quadro Kanban | Ferramenta: GitLab. Info mínima por card: descrição, tipo, prioridade, estimativa, DoR, DoD, responsável, dependências |
| Canais oficiais | WhatsApp (operacional interno) + Slack (institucional com professores/orientadora) |
| SLA de comunicação | Mensagens comuns: próximo Daily. Bloqueios urgentes: mesmo período de trabalho |

**Bloco 2 — Rituais documentados:**

| Ritual | Frequência | Duração | Participantes | Registro |
|---|---|---|---|---|
| Daily | Diário (dias úteis) | 15 min máximo | Time | Impedimentos e decisões no canal oficial |
| Sprint Planning | Início da sprint | Definido em calendário | Time | Issues, responsáveis, revisores, prioridades, estimativas, milestone |
| Sprint Review | Final da sprint | Definido em calendário | Time + professores + orientadora + convidados | Feedback e ajustes necessários |
| Retrospectiva | Final da sprint | Definido em calendário | Time | Pontos fortes, fracos, riscos, conflitos, ações de melhoria |

**Bloco 3 — Retrospectiva da Sprint 1**

A análise retrospectiva é completa e honesta:

*Pontos fortes identificados:*
1. Divisão equilibrada de tarefas (sem sobrecarga individual)
2. Comunicação assertiva (decisões registradas, resolução rápida)
3. Reuniões internas de revisão de conteúdo antes dos MRs

*Pontos fracos identificados:*
1. Distribuição irregular de revisões de MR (concentração em poucos revisores)
2. Atrasos na atualização do Kanban (cards presos em colunas erradas)

*Ações de melhoria para Sprint 2:*
1. Definir revisor de MR no planejamento com garantia de rodízio (responsabilidade do Scrum Master)
2. Atualização diária do Kanban antes do Daily (cada integrante responsável pelo próprio card)

**Bloco 4 — Alinhamento com o Escritório de Projetos:**

Avaliação explícita de 28 critérios distribuídos em 3 categorias:
- **README:** 13/13 itens atendidos
- **Documentação:** 12/12 itens atendidos
- **Aplicação:** 1 atendido, 2 pendentes para sprints futuras (esperado para Sprint 1)

**Matriz de Papéis e Responsabilidades — Sprint 1:**

| Integrante | Papel | Artefato/Tarefa |
|---|---|---|
| Ana Cristina Jardim | Gestão de Riscos e Req. Funcionais | Matriz de Risco + Req. Funcionais + modelagem |
| Felipe Simão | Contexto da Indústria e Persona Líder | Contexto + persona + jornada do líder de projeto |
| Karol Barbosa Rocha | Persona Diretora e Req. Não-Funcionais | Persona + jornada da diretora + RNFs |
| Matheus Ferreira da Silva | Persona PMO e Visão Técnica Inicial | Persona + jornada PMO + visão técnica + componentes |
| **Paulo Henrique Bueno Fernandes** | **Problema e Visão do Produto** | **Problema + SWOT + visão + features priorizadas** |
| Rui Facó | Canvas MVP e Tecnologias | Canvas MVP + tecnologias selecionadas |
| Tobias Viana | Modelagem do Fluxo de Negócio | Fluxo AS-IS e TO-BE + BPMNs |

**Revisão dos Riscos na Sprint 1:**

Todos os 9 riscos foram avaliados. Nenhuma materialização ou ajuste de probabilidade/impacto necessário. Decisão coletiva: manter matriz original, atualizar responsáveis e respostas.

**Planejamento da Sprint 2:**

8 tarefas priorizadas por ordem de execução e dependência, com escala de estimativa definida (PP, P, M, G).

#### Análise crítica do GestaoProjeto.md

**Pontos fortes:**
- **Documento vivo bem estruturado:** a separação entre acordos permanentes (seção 2) e registros por sprint (seção 3+) é uma decisão de arquitetura documental acertada — evita reescrita e preserva histórico.
- **Honestidade retrospectiva:** identificar os pontos fracos (MR reviews concentrados, Kanban desatualizado) e transformá-los em ações concretas com responsáveis é sinal de maturidade de processo.
- **Completude dos rituais:** cada ritual tem frequência, duração, participantes e forma de registro — não há ambiguidade sobre como o time opera.
- **Rastreabilidade de PMO:** o alinhamento com 28 critérios do Escritório de Projetos com resultados explícitos (13/13, 12/12) demonstra aderência ao processo avaliativo do módulo.

**Pontos de atenção:**
- As ações de melhoria da Sprint 2 têm responsáveis definidos, mas não têm indicadores de verificação — como saberemos na Sprint 3 se as ações de melhoria funcionaram? Sugere-se adicionar um critério de verificação para cada ação.

---

### 4.2 GestaoConfiguracao.md

**Localização:** `docs/GestaoConfiguracao.md`  
**Natureza:** documento normativo de controle de versão e integração de código.

#### O que foi entregue

O documento cobre o ciclo de vida completo de contribuição ao projeto:

**Gitflow adotado:**

```
feature/* ──┐
docs/* ─────┼──> develop ──> release/* ──> main
fix/* ──────┘                    └──────> develop

main ──> hotfix/* ──> main + develop
```

**Nomenclatura de branches:**

Formato: `<prefixo>/<descrição-em-kebab-case>`

Prefixos válidos com casos de uso: `feature/`, `feat/`, `fix/`, `bugfix/`, `docs/`, `doc/`, `style/`, `refactor/`, `test/`, `chore/`, `perf/`, `ci/`, `build/`, `hotfix/`, `release/`

**Convenção de commits:**

Formato: `<tipo>(<escopo-opcional>): <descrição em português> (#N)`

Regras:
- Descrição no infinitivo
- Máximo 72 caracteres na primeira linha
- Um commit = uma intenção
- Referência à issue obrigatória (`#N`)
- Distribuição ao longo da sprint (anti-padrão: concentração no final)

**Política de MR:**

Requisitos mínimos para cada Merge Request:
- Seção "O que foi feito"
- Seção "Como testar" com passos numerados
- `Closes #N` para auto-fechamento da issue
- Mínimo 1 revisor diferente do autor
- Mínimo 1 comentário real de revisão (aprovação sem comentário não conta)

**Workflows documentados com comandos:**
- Criação e sincronização de branches
- Criação de release (com tag semântica)
- Hotfix de produção
- Resolução de conflitos

**Checklist de conformidade final** com 10 itens verificáveis.

#### Análise crítica do GestaoConfiguracao.md

**Pontos fortes:**
- **Exemplos concretos em todos os tópicos:** cada convenção vem acompanhada de exemplos válidos e inválidos — isso elimina dúvida de interpretação.
- **Cobertura completa do ciclo:** do momento de criar a branch até a exclusão após o merge, cada passo está documentado.
- **Anti-padrões explícitos:** o documento não apenas diz o que fazer — diz o que não fazer (branch com nome de pessoa, branch sem prefixo, commit com verbo conjugado, commit genérico). Isso é mais útil do que apenas listar regras positivas.
- **Regra de revisão com dente:** a exigência de que aprovação sem comentário não conta é uma salvaguarda real de qualidade — não é apenas processo por processo.
- **Checklists de compliance:** o checklist final é objetivo e verificável, funcionando como DoD de contribuição.

**Pontos de atenção:**
- O documento descreve em detalhes o fluxo manual, mas não menciona automações de CI/CD para verificação das convenções (ex.: lint de mensagem de commit). O arquivo `.gitlab-ci.yml` existe no repositório, mas a conexão entre as políticas documentadas e as verificações automatizadas não está explicitada.

---

## 5. Demais Artefatos do Projeto

### 5.1 Contexto da Indústria

**Responsável:** Felipe Simão  
**Localização:** `docs/Projeto.md`, Seção 1.2

Abrange três dimensões:
- **Visão geral do setor metroferroviário:** 1.137,5 km de malha, 2,57 bilhões de passageiros em 2024, 49 linhas em 73 municípios. Dados da ANPTrilhos 2024.
- **Tendências e desafios:** PPPs, modernização com CBTC, automação, digitalização, desafios de financiamento e coordenação multi-operadora.
- **Posicionamento do parceiro:** Metrô SP (fundado em 1968), 4 linhas operadas diretamente, 821 milhões de passageiros em 2025, ~116 km e +100 estações. Papel central no planejamento da expansão da rede.

**Análise:** contexto denso e bem referenciado. Serve de base para justificar a criticidade das informações gerenciadas pelo PMO.

---

### 5.2 Personas e Jornadas

**Responsáveis:** Karol (Diretora), Matheus (Analista PMO), Felipe (Líder de Projeto)  
**Localização:** `docs/Projeto.md`, Seção 1.5 / `assets/design/`

Três personas com perfis completos:

| Persona | Perfil | Dores principais | Ganho esperado |
|---|---|---|---|
| Robson Oliveira (Diretor) | Decisor estratégico com tempo limitado | Não ter visão rápida do portfólio | Alertas consolidados sem precisar abrir sistemas |
| Maria Eduarda (Analista PMO) | Responsável pela consolidação do portfólio | Consolidação manual de múltiplos sistemas, monitoramento reativo | Consultas rápidas, alertas proativos |
| Carlos Mendes (Líder de Projeto) | Gestor de projetos individuais | Documentação complexa, informação dispersa | Monitoramento de marcos e riscos sem navegar sistemas |

**Análise:** as três personas cobrem os níveis estratégico, tático e operacional do PMO — boa cobertura. Os ativos visuais (Persona-*.png, Jornada-*.png) complementam o texto com representações visuais do perfil e do fluxo de uso.

---

### 5.3 Fluxo de Negócio (AS-IS / TO-BE)

**Responsável:** Tobias Viana  
**Localização:** `docs/Projeto.md`, Seção 1.6 / `assets/negócios/`  
**Ativos:** `diagrama_as_is.svg`, `diagrama_to_be.svg`, `cadeia-de-valor.svg`

- **AS-IS:** mapeamento do processo atual de consulta e registro de informações no PMO, evidenciando os pontos de atrito manual.
- **TO-BE:** visão do processo com o AZ1 integrado, mostrando onde o agente entra na jornada sem substituir as etapas de decisão humana.
- **Cadeia de Valor:** análise das atividades de valor do parceiro.

**Análise:** os diagramas BPMN são fundamentais para alinhar a solução técnica com a realidade operacional do parceiro e demonstrar visualmente que a proposta respeita os processos existentes.

---

### 5.4 Canvas do MVP e Tecnologias

**Responsável:** Rui Facó  
**Localização:** `docs/Projeto.md`, Seções 1.8 e 2.5  
**Ativo:** `assets/negócios/BMC.png`

- **Canvas MVP:** define a proposta de valor por persona, canais de entrega, segmentos, atividades-chave, parcerias e estrutura de custos.
- **Tecnologias:** stack técnico selecionado com justificativas — NLP, backend, frontend, banco de dados, infraestrutura de cloud.

**Análise:** o BMC complementa a visão do produto com a perspectiva de modelo de negócio, algo frequentemente ausente em projetos acadêmicos que focam apenas na solução técnica.

---

### 5.5 Requisitos Funcionais e Não-Funcionais

**Responsáveis:** Ana Cristina Jardim (RF), Karol Barbosa Rocha (RNF)  
**Localização:** `docs/Projeto.md`, Seções 2.2 e 2.3

**Requisitos Funcionais (RF) principais:**

| RF | Funcionalidade |
|---|---|
| RF01 | Interface de consulta conversacional |
| RF02 | Resposta estruturada sobre projetos |
| RF03 | Análise comparativa entre projetos |
| RF04 | Sugestões de preenchimento de dados |
| RF05 | Alertas proativos e monitoramento |

**Requisitos Não-Funcionais (RNF) principais:**

| RNF | Critério |
|---|---|
| RNF01 | ≥80% das consultas textuais respondidas em até 15 segundos |
| RNF02 | Uso exclusivo de dados sintéticos |
| RNF03 | ≥85% de precisão na classificação de intenções |
| RNF04 | Rastreabilidade completa e controle de acesso |
| RNF05 | Núcleo PLN desacoplado com interfaces padronizadas |
| RNF08 | ≥80% dos participantes de teste compreendem a resposta sem auxílio |
| RNF11 | ≥85% das sugestões com referência válida e justificativa compreensível |

**Análise:** os RNFs têm critérios mensuráveis e verificáveis — percentuais e condições objetivas. Isso é um sinal de maturidade na especificação, pois permite que a validação nas sprints futuras seja objetiva e não subjetiva.

---

### 5.6 Arquitetura e Modelagem Técnica

**Responsável:** Matheus Ferreira da Silva (arquitetura) + Ana Cristina Jardim (modelagem)  
**Localização:** `docs/Projeto.md`, Seção 2.4 / `assets/`  
**Ativos:** `diagrama_componentes.svg`, `diagrama-de-classes.svg`, `sequencia-2.svg`, `sequencia-3.svg`

- **Diagrama de componentes:** visão do pipeline técnico do AZ1 — entradas (texto/voz), processamento PLN, integração com ecossistema Microsoft.
- **Diagrama de classes:** modelagem UML das entidades do domínio (projetos, marcos, riscos, documentos, usuários, permissões).
- **Diagramas de sequência:** fluxos de interação para os casos de uso principais — consulta, alerta, sugestão de preenchimento.

**Análise:** a presença de diagramas de sequência já em Sprint 1 demonstra maturidade técnica do time — é comum equipes iniciantes deixarem a modelagem dinâmica para depois.

---

### 5.7 Matriz de Risco

**Responsável:** Ana Cristina Jardim  
**Localização:** `docs/Projeto.md`, Seção 1.9 / `assets/negócios/matriz-de-risco.png`

9 riscos mapeados com estrutura completa para cada um:

| Código | Risco | Probabilidade | Impacto | Severidade |
|---|---|---|---|---|
| AM1 | Falhas de comunicação interna | 30% | Alto | Média |
| AM2 | Baixa precisão na identificação de intenções | 30% | Muito Alto | Alta |
| AM3 | Atraso no acesso ao ambiente Microsoft | 70% | Moderado | Alta |
| AM4 | Informações atrasadas do Metrô | 50% | Alto | Alta |
| AM5 | Projeto não concluído no prazo | 10% | Muito Alto | Média |
| AM6 | Dados insuficientes para validação | 70% | Alto | Muito Alta |
| AM7 | Indisponibilidade/sobrecarga de integrante | 50% | Moderado | Média |
| AM8 | Alucinação nas respostas do LLM | Alta | Muito Alto | Muito Alta |
| AM9 | Degradação de áudio em ambientes ruidosos | — | — | — |

3 oportunidades mapeadas (OP1, OP2, OP3).

**Análise:** incluir ameaças técnicas específicas de IA (AM8 — alucinação de LLM) em Sprint 1 é uma decisão estratégica importante. Muitos projetos de IA identificam esse risco tarde demais e não planejam mitigações desde o início. AM6 (dados insuficientes) e AM3 (acesso ao Microsoft) com probabilidade de 70% demonstram realismo sobre os desafios práticos do projeto.

---

## 6. Artefatos de Suporte e Infraestrutura

### gitlab-issue-kit

**Localização:** `gitlab-issue-kit/`  
**Natureza:** automação para criação em massa de issues a partir de CSV

Composto por:
- `create_issues.py` — criação em lote de issues
- `setup_labels.py` — criação do catálogo de labels
- `setup_mr_template.py` — configuração de templates de MR
- `relabel.py` — adição/remoção de labels em issues existentes
- `gitlab_kit.py` — módulo core compartilhado (credenciais, HTTP)
- `backlog_sprint01.csv` — backlog da Sprint 1 em CSV

**Análise:** a presença de um toolkit de automação de issues demonstra que o time foi além da documentação manual e investiu em eficiência de processo. A separação do kit em scripts especializados com um módulo core é uma decisão de arquitetura correta para manutenibilidade.

### Scripts de Banco de Dados

**Localização:** `src/database/`

- `01_create_database.sql` — criação do schema
- `02_initial_data.sql` — carga inicial de dados sintéticos

**Análise:** presença em Sprint 1 indica planejamento técnico antecipado — o time já tem uma estrutura de dados base para desenvolver as próximas sprints.

---

## 7. Avaliação Geral da Sprint 1

### Completude das entregas

| Critério | Status |
|---|---|
| Todos os artefatos planejados entregues | Sim — 3/3 artefatos principais |
| Avaliação do Escritório de Projetos | README 13/13 + Docs 12/12 |
| Retrospectiva realizada com ações de melhoria | Sim |
| Revisão dos riscos realizada | Sim — 9 riscos revisados |
| Planejamento da Sprint 2 documentado | Sim — 8 tarefas priorizadas |

### Qualidade técnica

| Dimensão | Avaliação |
|---|---|
| Profundidade da análise de negócio | Alta — problema, SWOT, contexto e visão bem articulados |
| Especificação de requisitos | Alta — RNFs com critérios mensuráveis |
| Modelagem técnica | Boa para Sprint 1 — componentes, classes e sequência presentes |
| Gestão de processo | Alta — rituais, SLA e políticas completos e aplicados |
| Gestão de configuração | Muito alta — Gitflow documentado com exemplos e checklists |
| Cobertura de riscos | Boa — 9 ameaças incluindo riscos específicos de IA |

### Contribuição de Paulo Henrique — síntese

A responsabilidade de Paulo Henrique centrou-se nos artefatos que **estabelecem o porquê do projeto**: o problema, o contexto estratégico (SWOT) e a direção da solução (visão do produto e features). Esses são os artefatos fundacionais que, se mal elaborados, comprometem toda a rastreabilidade das demais entregas.

A qualidade entregue nesses artefatos é alta, com destaque para:

1. **Distinção clara entre problema e solução** — o texto do problema delimita que o desafio é de interface, não de ausência de processos, o que previne o erro mais comum em projetos de IA corporativa.
2. **SWOT com rastreabilidade para decisões de produto** — a identificação da ameaça de troca de plataforma como motivador do RNF05 é um exemplo de como uma análise estratégica deve alimentar diretamente a especificação.
3. **Escopo positivo e negativo do produto** — documentar o que o AZ1 não faz com justificativas explícitas é uma prática de gestão de produto que protege o projeto e alinha expectativas com o parceiro.
4. **Delimitação clara do MVP** — o resumo executivo que fecha a visão do produto é preciso e acionável para as sprints seguintes.

---

*Documento produzido com base nos artefatos entregues na Sprint 1 do Projeto AZ1, G01, Módulo 7 — Inteli, 2026.*  
*Versão analisada: v0.1.0 (tag de release: 14/08/2026)*
