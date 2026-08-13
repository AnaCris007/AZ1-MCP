<p align='center'>
  <a href='https://www.inteli.edu.br/'>
    <img src='../assets/inteli.png' alt='Inteli - Instituto de Tecnologia e Liderança' width='300'>
  </a>
</p>

# G01

## Integrantes

- [Ana Cristina Jardim](https://www.linkedin.com/in/ana-cristina-jardim/)
- [Felipe Simão](https://www.linkedin.com/in/felipefmsimao/)
- [Karol Barbosa Rocha](https://www.linkedin.com/in/karolbarbosarocha/)
- [Matheus Ferreira da Silva](https://www.linkedin.com/in/matheusferreirads-/)
- [Paulo Henrique Bueno Fernandes](https://www.linkedin.com/in/paulo-henrique0601/)
- [Rui Facó](https://www.linkedin.com/in/ruifac%C3%B3/)
- [Tobias Viana](https://www.linkedin.com/in/tobias-viana/)

## Orientadora

- [Vanessa Nunes](https://www.linkedin.com/in/vanunes/)



## Professores:
### Orientador(a)
- <a href="https://www.linkedin.com/in/vanunes/">Vanessa Nunes</a>
### Instrutores
- <a href="https://www.linkedin.com/in/reginaldo-arakaki-9574222b/">Computação - Reginaldo Arakaki</a>
- <a href="https://www.linkedin.com/in/bryan-kano/">Computação - Bryan Kano</a>
- <a href="https://www.linkedin.com/in/fernando-pizzo-208b526a/">Matemática e Física - Fernando Pizzo</a>
- <a href="https://www.linkedin.com/in/lisane-valdo/">Negócios - Lisane Valdo</a>
- <a href="https://www.linkedin.com/in/bruno-grandchamp-rodilha/?locale=pt">Design - Bruno Rodilha</a>
- <a href="https://www.linkedin.com/in/professor1/">Liderança - Filipe Gonçalves</a>

---

## Projeto: Azum

# Gestão de Configuração

## Sumário

<details>
<summary><strong>1. Introdução</strong></summary>

- [1.1 Objetivo do documento](#11-objetivo-do-documento)
- [1.2 Princípios da gestão de configuração](#12-princípios-da-gestão-de-configuração)

</details>

<details>
<summary><strong>2. Fluxo Gitflow</strong></summary>

- [2.1 Visão geral](#21-visão-geral)
- [2.2 Estrutura de branches](#22-estrutura-de-branches)
- [2.3 Fluxo entre branches](#23-fluxo-entre-branches)

</details>

<details>
<summary><strong>3. Política de Criação de Branches</strong></summary>

- [3.1 Convenção de nomenclatura](#31-convenção-de-nomenclatura)
- [3.2 Procedimento de criação](#32-procedimento-de-criação)

</details>

<details>
<summary><strong>4. Política de Integração e Exclusão</strong></summary>

- [4.1 Merge Requests](#41-merge-requests)
- [4.2 Procedimento de merge](#42-procedimento-de-merge)
- [4.3 Exclusão de branches](#43-exclusão-de-branches)
- [4.4 Releases e hotfixes](#44-releases-e-hotfixes)

</details>

<details>
<summary><strong>5. Rastreabilidade e Commits</strong></summary>

- [5.1 Vínculo com tasks](#51-vínculo-com-tasks)
- [5.2 Convenção de commits](#52-convenção-de-commits)
- [5.3 Evidências de aplicação](#53-evidências-de-aplicação)

</details>

<details>
<summary><strong>6. Exemplos Práticos</strong></summary>

- [6.1 Desenvolvimento de uma feature](#61-desenvolvimento-de-uma-feature)
- [6.2 Preparação de uma release](#62-preparação-de-uma-release)
- [6.3 Correção por hotfix](#63-correção-por-hotfix)

</details>

- [7. Checklist de Conformidade](#7-checklist-de-conformidade)
- [Referências](#referências)

---

# 1. Introdução

## 1.1 Objetivo do documento

<!-- Explique que este documento define o Gitflow, as convenções de branches e os procedimentos de criação, integração e exclusão utilizados pela equipe. -->

_Conteúdo a ser preenchido pela equipe._

## 1.2 Princípios da gestão de configuração

<!-- Registre princípios como rastreabilidade, revisão por pares, proteção das branches estáveis e associação das mudanças às tasks. -->

_Conteúdo a ser preenchido pela equipe._

---

# 2. Fluxo Gitflow

## 2.1 Visão geral

<!-- Apresente o Gitflow e justifique sua aplicabilidade ao projeto. -->

_Conteúdo a ser preenchido pela equipe._

## 2.2 Estrutura de branches

| Branch | Origem | Finalidade | Destino do merge | Permanência |
|---|---|---|---|---|
| main | — | Versões estáveis e entregáveis | — | Permanente |
| develop | main | Integração do trabalho da sprint | main, por release | Permanente |
| feature/<issue-id>-<descricao> | develop | Nova funcionalidade ou artefato | develop | Temporária |
| release/<versao> | develop | Estabilização de uma entrega | main e develop | Temporária |
| hotfix/<issue-id>-<descricao> | main | Correção urgente de versão estável | main e develop | Temporária |

<!-- Confirme ou ajuste os nomes conforme a política realmente adotada pelo grupo. -->

## 2.3 Fluxo entre branches

    main ───────────────●──────────────●────
                       ▲              ▲
    release ───────────┘              │
                       └────► develop │
    develop ──●────●──────────●───────┘────
              ▲    ▲
    feature ──┘    └───────────────────────

    hotfix: main → hotfix → main + develop

<!-- Ajuste o diagrama caso o fluxo definido pela equipe seja diferente. -->

---

# 3. Política de Criação de Branches

## 3.1 Convenção de nomenclatura

Formato geral:

    <tipo>/<issue-id>-<descricao-curta-em-kebab-case>

Exemplos:

    feature/42-classificador-intencoes
    release/v0.2.0
    hotfix/87-corrigir-carregamento-modelo

Regras a confirmar pela equipe:

- utilizar letras minúsculas;
- separar palavras com hífen;
- evitar acentos, espaços e caracteres especiais;
- incluir o identificador da issue quando aplicável;
- manter a descrição curta e representativa.

## 3.2 Procedimento de criação

<!-- Substitua o exemplo pelos passos efetivamente adotados. -->

    git switch develop
    git pull origin develop
    git switch -c feature/42-classificador-intencoes
    git push -u origin feature/42-classificador-intencoes

Antes do trabalho, a task correspondente deve estar pronta conforme a Definition of Ready registrada em GestaoProjeto.md.

---

# 4. Política de Integração e Exclusão

## 4.1 Merge Requests

| Critério | Regra da equipe |
|---|---|
| Branch de destino correta | [Preencher] |
| Quantidade mínima de revisores | [Preencher] |
| Critérios de aprovação | [Preencher] |
| Tratamento de conflitos | [Preencher] |
| Evidências obrigatórias | [Preencher] |

## 4.2 Procedimento de merge

<!-- Informe a sequência e a estratégia adotada: merge commit, squash ou rebase. -->

1. [Preencher].
2. [Preencher].
3. [Preencher].
4. [Preencher].

## 4.3 Exclusão de branches

<!-- Defina quando branches locais e remotas são excluídas e quem verifica a conclusão. -->

    git branch -d feature/42-classificador-intencoes
    git push origin --delete feature/42-classificador-intencoes

## 4.4 Releases e hotfixes

<!-- Descreva como criar, validar, integrar e encerrar branches de release e hotfix, incluindo tag quando aplicável. -->

_Conteúdo a ser preenchido pela equipe._

---

# 5. Rastreabilidade e Commits

## 5.1 Vínculo com tasks

<!-- Explique como branches, commits e Merge Requests serão associados às issues do GitLab. -->

_Conteúdo a ser preenchido pela equipe._

## 5.2 Convenção de commits

Formato adotado:

    <tipo>(<escopo opcional>): <descrição objetiva>

| Tipo | Uso |
|---|---|
| feat | Nova funcionalidade |
| fix | Correção de defeito |
| docs | Alteração de documentação |
| test | Inclusão ou ajuste de testes |
| refactor | Refatoração sem mudança funcional |
| chore | Manutenção de ferramentas ou tarefas auxiliares |

Exemplo:

    feat(nlp): classificar intenção de consulta

<!-- Confirme tipos, idioma e regras com a política registrada em GestaoProjeto.md. -->

## 5.3 Evidências de aplicação

| Evidência | Link | O que demonstra |
|---|---|---|
| Issue | [Inserir link] | [Preencher] |
| Branch | [Inserir link] | [Preencher] |
| Merge Request | [Inserir link] | [Preencher] |
| Histórico de commits | [Inserir link] | [Preencher] |

---

# 6. Exemplos Práticos

## 6.1 Desenvolvimento de uma feature

<!-- Descreva um exemplo real: issue, branch a partir de develop, commits, Merge Request, revisão, merge e exclusão. -->

_Exemplo a ser preenchido pela equipe._

## 6.2 Preparação de uma release

<!-- Descreva criação, estabilização, merge em main e develop e criação de tag. -->

_Exemplo a ser preenchido pela equipe._

## 6.3 Correção por hotfix

<!-- Descreva uma correção criada a partir de main e reintegrada em main e develop. -->

_Exemplo a ser preenchido pela equipe._

---

# 7. Checklist de Conformidade

- [ ] A task possui informações suficientes para começar.
- [ ] A branch foi criada a partir da origem correta.
- [ ] O nome da branch segue a convenção.
- [ ] Os commits são claros e vinculados à mudança.
- [ ] A Merge Request aponta para a branch correta.
- [ ] A revisão por pares foi concluída.
- [ ] Os critérios técnicos e documentais foram verificados.
- [ ] O merge seguiu a estratégia definida.
- [ ] A branch temporária foi excluída.
- [ ] A task e o Kanban foram atualizados.

---

# Referências

- [A successful Git branching model — Vincent Driessen](https://nvie.com/posts/a-successful-git-branching-model/)
- [GitLab Flow](https://docs.gitlab.com/topics/gitlab_flow/)
- [Protected branches — GitLab](https://docs.gitlab.com/user/project/repository/branches/protected/)
- [Conventional Commits](https://www.conventionalcommits.org/pt-br/v1.0.0/)