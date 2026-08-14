<p align='center'>
  <a href='https://www.inteli.edu.br/'>
    <img src='../assets/inteli.png' alt='Inteli - Instituto de Tecnologia e Liderança' width='300'>
  </a>
</p>

# Projeto: Azum

## Integrantes

- [Ana Cristina Jardim](https://www.linkedin.com/in/ana-cristina-jardim/)
- [Felipe Simão](https://www.linkedin.com/in/felipefmsimao/)
- [Karol Barbosa Rocha](https://www.linkedin.com/in/karolbarbosarocha/)
- [Matheus Ferreira da Silva](https://www.linkedin.com/in/matheusferreirads-/)
- [Paulo Henrique Bueno Fernandes](https://www.linkedin.com/in/paulo-henrique0601/)
- [Rui Facó](https://www.linkedin.com/in/ruifac%C3%B3/)
- [Tobias Viana](https://www.linkedin.com/in/tobias-viana/)


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
- [3.3 Atualização de uma branch de trabalho](#33-atualização-de-uma-branch-de-trabalho)

</details>

<details>
<summary><strong>4. Política de Integração e Exclusão</strong></summary>

- [4.1 Merge Requests](#41-merge-requests)
- [4.2 Procedimento de merge](#42-procedimento-de-merge)
- [4.3 Exclusão de branches](#43-exclusão-de-branches)
- [4.4 Releases e hotfixes](#44-releases-e-hotfixes)
- [4.5 Proteção de branches e conflitos](#45-proteção-de-branches-e-conflitos)

</details>

<details>
<summary><strong>5. Rastreabilidade e Commits</strong></summary>

- [5.1 Vínculo com tasks](#51-vínculo-com-tasks)
- [5.2 Convenção de commits](#52-convenção-de-commits)
- [5.3 Evidências de aplicação](#53-evidências-de-aplicação)

</details>

<details>
<summary><strong>6. Exemplos Práticos</strong></summary>

- [6.1 Desenvolvimento de uma feature de documentação](#61-desenvolvimento-de-uma-feature-de-documentação)
- [6.2 Preparação de uma release](#62-preparação-de-uma-release)
- [6.3 Correção por hotfix](#63-correção-por-hotfix)

</details>

- [7. Checklist de Conformidade](#7-checklist-de-conformidade)


---

# 1. Introdução

## 1.1 Objetivo do documento

 Este documento define as políticas de gestão de configuração adotadas pela equipe no projeto Azum ao longo do Módulo 7 do Inteli. Estão registrados aqui o fluxo Gitflow adaptado ao módulo, as convenções de nomenclatura de branches, os procedimentos de criação, integração e exclusão de branches, a política de commits e os exemplos práticos que ilustram a aplicação dessas políticas no contexto do projeto. O documento é complementar ao [GestaoProjeto.md](./GestaoProjeto.md), que registra as políticas de processo de desenvolvimento, os acordos de convivência e a gestão das sprints.


## 1.2 Princípios da gestão de configuração

 A gestão de configuração do projeto Azum é orientada por quatro princípios fundamentais. O primeiro é a **rastreabilidade**: toda mudança autoral no repositório deve estar associada a uma issue do GitLab, de modo que seja possível identificar por que a alteração foi feita, quem a fez e em qual sprint. Commits de merge gerados pelo GitLab são exceção ao formato autoral, pois sua rastreabilidade decorre do próprio Merge Request. O segundo princípio é a **revisão por pares**: nenhuma alteração é integrada às branches estáveis sem aprovação de um integrante diferente do autor, garantindo qualidade e distribuição do conhecimento. O terceiro é a **proteção das branches permanentes**: `main` e `develop` não recebem commits diretos; toda integração ocorre por Merge Request aprovado. O quarto é a **cadência distribuída**: o trabalho deve ser realizado ao longo da sprint, com commits frequentes e progressivos, evitando a concentração de entregas no último dia.

---

# 2. Fluxo Gitflow

## 2.1 Visão geral

 O projeto Azum adota um fluxo baseado no Gitflow, com as branches permanentes `main` e `develop` e as branches temporárias `feature/*`, `release/*` e `hotfix/*` exigidas pelo enunciado oficial. As branches `docs/*` e `fix/*` são especializações adotadas pela equipe para documentação e correções comuns. A branch `hmg` não é obrigatória e não existe entre as branches locais ou remotas inspecionadas; por isso, ela não integra o fluxo documentado.

- fluxo regular: `feature/*`, `docs/*` e `fix/*` → `develop`; uma `release/*` estabiliza o conteúdo e o promove para `main`;
- correção urgente: `hotfix/*` parte de `main` e retorna por MRs separados para `main` e `develop`.

## 2.2 Estrutura de branches


| Branch | Origem | Finalidade | Destino do merge | Permanência |
|---|---|---|---|---|
| `main` | — | Versões estáveis e entregáveis | — | Permanente |
| `develop` | `main` | Integração contínua do trabalho da sprint | `release/*`, por criação de branch | Permanente |
| `feature/<descricao>` | `develop` | Nova funcionalidade ou artefato | `develop`, por MR | Temporária |
| `docs/<descricao>` | `develop` | Documentação | `develop`, por MR | Temporária |
| `fix/<descricao>` | `develop` | Correção de bug | `develop`, por MR | Temporária |
| `hotfix/<descricao>` | `main` | Correção urgente em produção | `main` e `develop`, por MR | Temporária |
| `release/<versao>` | `develop` | Estabilização da versão candidata | `main` e `develop`, por MRs separados quando houver ajustes de estabilização | Temporária |

## 2.3 Fluxo entre branches

```text
feature/* ─┐
docs/* ────┼──> develop ──> release/* ──> main
fix/* ─────┘                    └────────> develop (ajustes da release)

main ──> hotfix/* ──> main
                 └──> develop
```

No fluxo regular, o trabalho é integrado a `develop`. A branch `release/*` é criada a partir de `develop` para estabilizar uma versão e promove o conteúdo aprovado para `main`; ajustes feitos durante a estabilização também retornam a `develop`. Um `hotfix/*` parte de `main` e retorna tanto para `main` quanto para `develop`, evitando que a correção se perca na próxima versão.

---

# 3. Política de Criação de Branches

## 3.1 Convenção de nomenclatura

 Todo nome de branch deve seguir o padrão validado pelo dashboard do módulo:

    <prefixo>/<descricao-curta-em-kebab-case>


 O dashboard valida o nome contra o seguinte padrão:

    ^(feature|feat|fix|bugfix|hotfix|docs|doc|style|refactor|test|chore|perf|ci|build|release)/


| Prefixo | Quando usar |
|---|---|
| `feature/` ou `feat/` | Nova funcionalidade |
| `fix/` ou `bugfix/` | Correção de bug |
| `docs/` ou `doc/` | Apenas documentação |
| `style/` | Formatação sem alteração de comportamento |
| `refactor/` | Reescrita sem nova feature nem correção |
| `test/` | Adição ou correção de testes |
| `chore/` | Manutenção, dependências, configurações |
| `perf/` | Melhoria de desempenho |
| `ci/` | Pipelines de integração e entrega contínua |
| `build/` | Build, empacotamento e scripts de release |
| `hotfix/` | Correção urgente em produção |
| `release/` | Estabilização antes de promover para `main` |

**Regras:**
- Letras minúsculas, sem acentos, sem espaços — usar hífen como separador;
- Descrição curta e objetiva, que identifique a issue sem precisar abri-la;
- Nunca usar nome de pessoa, número de sprint isolado ou termos genéricos como `desenvolvimento`, `tarefa` ou `atualização`.

**Exemplos válidos:**

    docs/brainstorming-features
    feature/classificador-intencoes-pln
    fix/corrigir-retorno-consulta-projeto
    refactor/reorganizar-modulo-pln
    test/cobrir-deteccao-fora-catalogo


**Exemplos inválidos:**

    desenvolvimento-ana  / sem prefixo, com nome de pessoa
    sprint2-documentacao /  sem prefixo com barra
    docs / sem descrição
    feature/Atualização Pipeline  maiúsculas, acento e espaço


## 3.2 Procedimento de criação

```bash
git checkout develop
git pull origin develop
git checkout -b docs/brainstorming-features
git push -u origin docs/brainstorming-features
```

 Antes de iniciar o trabalho, a issue correspondente deve estar refinada com DoR atendido, labels, milestone e assignee preenchidos, e o card movido de open para backlog no Kanban do GitLab.

## 3.3 Atualização de uma branch de trabalho

 Antes de abrir ou atualizar um Merge Request, o autor deve incorporar à branch de trabalho o estado mais recente de `develop`. O projeto adota merge explícito para essa sincronização, coerente com a preservação do histórico definida na Seção 4.2:

```bash
git checkout develop
git pull --ff-only origin develop
git checkout docs/brainstorming-features
git merge develop
```

 Depois da sincronização, o autor executa as verificações aplicáveis à task e envia a branch com `git push`. Se houver conflitos, o merge permanece local e incompleto até que sejam resolvidos conforme a Seção 4.5. Não se deve usar `git push --force` nas branches compartilhadas ou protegidas.

---

# 4. Política de Integração e Exclusão

## 4.1 Merge Requests

| Critério | Regra da equipe |
|---|---|
| Branch de destino correta | Branches de trabalho apontam para `develop`; releases promovem para `main`; hotfixes retornam para `main` e `develop` |
| Quantidade mínima de revisores | Um revisor, diferente do autor |
| Critérios de aprovação | Pelo menos um comentário de revisão real — aprovação sem comentário não conta |
| Tratamento de conflitos | O autor resolve os conflitos antes de solicitar a revisão |
| Evidências obrigatórias | `Closes #N` na descrição, seções `## O que foi feito` e `## Como testar`, labels e milestone preenchidos |

**Template mínimo de MR:**

```markdown
Closes #<número da issue>

## O que foi feito
- <ponto principal>
- <ponto secundário>

## Como testar
1. <passo>
2. <passo>
3. <resultado esperado>

## Checklist
- [ ] Sem warnings de lint
- [ ] Documentação atualizada (se aplicável)
- [ ] MR aprovado por 1 revisor
```

## 4.2 Procedimento de merge

1. Garantir que a branch de trabalho está atualizada em relação a `develop` e resolver eventuais conflitos antes de abrir o MR;
2. Abrir o MR no GitLab apontando para `develop`, preenchendo título descritivo, descrição com `Closes #N`, labels e milestone;
3. Designar o reviewer antes de solicitar o merge — o autor não revisa o próprio MR;
4. Aguardar a revisão com pelo menos um comentário registrado no MR e realizar os ajustes solicitados;
5. Após aprovação, realizar o merge pelo GitLab — a estratégia adotada é **merge commit** para preservar o histórico completo;
6. Excluir a branch de trabalho imediatamente após o merge.

As promoções seguem o mesmo controle: uma branch `release/*` parte de `develop` e abre um Merge Request para `main`. Se houver ajustes de estabilização exclusivos da release, eles retornam a `develop` por outro Merge Request. Cada integração exige revisão e aprovação próprias.

## 4.3 Exclusão de branches

 Branches de trabalho devem ser excluídas imediatamente após o merge, para manter o repositório organizado. A exclusão pode ser feita pelo GitLab no momento do merge (opção "Delete source branch") ou manualmente:

```bash
git push origin --delete docs/brainstorming-features
git branch -d docs/brainstorming-features
git checkout develop
git pull origin develop
```

## 4.4 Releases e hotfixes

**Release:**

```bash
git checkout develop && git pull origin develop
git checkout -b release/v1.0.0
# realizar e validar os ajustes de estabilização
git add <arquivos-alterados>
git commit -m "chore: preparar release v1.0.0 (#N)"
git push -u origin release/v1.0.0
```

 Após a estabilização, abrir um Merge Request de `release/*` para `main`. Se a release contiver ajustes que ainda não estejam em `develop`, abrir também um Merge Request de retorno para `develop`. Depois da integração em `main`, criar a tag e excluir a branch de release:

```bash
git checkout main && git pull origin main
git tag -a v1.0.0 -m "Release v1.0.0 — Sprint 1"
git push origin v1.0.0
git push origin --delete release/v1.0.0
```

**Hotfix:**

```bash
git checkout main && git pull origin main
git checkout -b hotfix/corrigir-falha-classificador
# realizar e validar a correção urgente
git add <arquivos-alterados>
git commit -m "fix(pln): corrigir falha na classificacao de intencao (#N)"
git push -u origin hotfix/corrigir-falha-classificador
```

 Após a correção, abrir um Merge Request para `main` e, depois do merge, abrir outro para sincronizar a alteração com `develop`. Excluir a branch de hotfix ao final.

## 4.5 Proteção de branches e conflitos

### Proteção

 Commits e pushes diretos para `main` e `develop` são proibidos. A integração deve ocorrer por Merge Request, com pelo menos um revisor diferente do autor e com os critérios da Seção 4.1 atendidos. Somente integrantes autorizados pelo grupo podem concluir o merge; o autor pode realizá-lo apenas depois da aprovação registrada pelo revisor. A rotação de responsáveis pelas promoções para `main` está definida no Contrato de Convivência.

 [PENDENTE — o responsável pela gestão de configuração deve anexar uma captura de tela ou um link acessível das regras de proteção configuradas no GitLab para `main` e `develop`, além da evidência de que um push direto foi recusado. O texto documenta a política, mas não comprova sua configuração.]

### Tratamento de conflitos

1. O autor atualiza `develop` e executa `git merge develop` em sua própria branch de trabalho;
2. identifica os arquivos marcados como conflitantes com `git status`;
3. consulta o autor do conteúdo afetado quando a escolha entre versões envolver decisão de negócio ou técnica;
4. resolve os marcadores de conflito nos arquivos e executa as verificações aplicáveis;
5. adiciona somente os arquivos resolvidos com `git add <arquivo>` e conclui o merge com `git commit`;
6. envia a branch atualizada e registra no Merge Request como o conflito foi resolvido;
7. solicita nova revisão caso a resolução tenha alterado conteúdo já aprovado.

 Conflitos nunca são resolvidos por commits diretos em `develop` ou `main`. Também não se utiliza `git reset --hard` ou push forçado como procedimento de resolução.

---

# 5. Rastreabilidade e Commits

## 5.1 Vínculo com tasks

 Toda branch de trabalho, todo commit autoral e todo Merge Request do projeto Azum devem estar associados a uma issue do GitLab. O vínculo é estabelecido de três formas: o nome da branch descreve a issue desenvolvida; cada commit autoral referencia a issue com `#N`; e o MR contém `Closes #N` na descrição, encerrando a issue automaticamente quando o merge é realizado. Commits de merge gerados pela plataforma são rastreados pelo MR correspondente e não precisam repetir o padrão de mensagem autoral.

## 5.2 Convenção de commits

 Os commits seguem o padrão Conventional Commits, padronizado em português. O formato adotado é:

    <tipo>(<escopo opcional>): <descrição curta em português> (#N)


**Regras:**
- Descrição no infinitivo (adicionar / correto — adicionei / incorreto);
- Máximo de 72 caracteres na primeira linha;
- Um commit = uma intenção — não misturar tipos diferentes;
- Referência à issue obrigatória com `#N`;
- Commits distribuídos ao longo da sprint — concentrar no último dia é anti-padrão penalizado pelo dashboard.

| Tipo | Quando usar |
|---|---|
| `feat` | Nova funcionalidade |
| `fix` | Correção de bug |
| `docs` | Apenas documentação |
| `style` | Formatação sem alteração de comportamento |
| `refactor` | Reescrita sem nova feature nem correção |
| `test` | Adicionar ou corrigir testes |
| `chore` | Manutenção, dependências, configurações |
| `perf` | Melhoria de performance |
| `ci` | Pipeline de CI/CD |
| `build` | Build, empacotamento, scripts de release |
| `revert` | Reverter um commit anterior |

**Exemplos válidos:**

    docs: adicionar brainstorming de features (#16)
    feat(pln): adicionar classificador de intencoes (#15)
    fix(api): corrigir retorno vazio em consulta de projeto (#23)
    test(intencoes): cobrir caso de solicitacao fora do catalogo (#19)


**Exemplos inválidos:**

    atualização documentação — sem tipo, sem #N
    docs: atualizei o brainstorming — verbo no passado
    feat: nova feature (#15) — descrição genérica


## 5.3 Evidências de aplicação

| Evidência | Link | O que demonstra |
|---|---|---|
| Issue | [Issue #16](https://git.inteli.edu.br/graduacao/2026-2a/t17/g01/-/issues/16) | Task refinada com DoR, DoD, labels, milestone e assignee |
| Branch | [docs/brainstorming-features](https://git.inteli.edu.br/graduacao/2026-2a/t17/g01/-/tree/docs/brainstorming-features) | Nomenclatura padronizada e origem em `develop` |
| Merge Request | [MR !11](https://git.inteli.edu.br/graduacao/2026-2a/t17/g01/-/merge_requests/11) | Vínculo com a issue, reviewer designado e revisão real |
| Histórico de commits | [Commits da branch](https://git.inteli.edu.br/graduacao/2026-2a/t17/g01/-/commits/docs/brainstorming-features) | Commits semânticos em português com `#N` distribuídos ao longo da sprint |

 Os links acima são evidências declaradas pela equipe. O histórico local confirma a existência de branches de trabalho com prefixos padronizados, commits autorais vinculados a issues e merges em `develop`. O conteúdo completo da issue e do Merge Request depende de acesso ao GitLab e, portanto, não pôde ser validado apenas com os arquivos locais. Não foram encontradas evidências locais de uso de `release/*` ou `hotfix/*`; as Seções 6.2 e 6.3 são exemplos de aplicação futura, não registros de execução.

---

# 6. Exemplos Práticos

## 6.1 Desenvolvimento de uma feature de documentação

**Contexto:** implementar a seção de brainstorming de features no `Projeto.md` (issue #16, Sprint 1).

```bash
git checkout develop && git pull origin develop
git checkout -b docs/brainstorming-features
git push -u origin docs/brainstorming-features

git commit -m "docs: adicionar introducao do brainstorming de features (#16)"
git commit -m "docs: adicionar tabela de priorizacao de features (#16)"
git commit -m "docs: adicionar analise das faixas de priorizacao (#16)"
git push -u origin docs/brainstorming-features
```

 O fluxo foi concluído pelo [Merge Request !11](https://git.inteli.edu.br/graduacao/2026-2a/t17/g01/-/merge_requests/11), aberto para `develop` com título descritivo, vínculo `Closes #16`, revisor designado, labels e milestone da Sprint 1. Após a aprovação e o merge, a branch de trabalho deve ser excluída.

## 6.2 Preparação de uma release

**Contexto ilustrativo:** estabilizar as entregas de uma sprint antes de promover a versão para `main`. Este exemplo descreve a política; não constitui evidência de que uma branch de release já tenha sido utilizada.

```bash
git checkout develop && git pull origin develop
git checkout -b release/v1.0.0
# realizar e validar os ajustes de estabilização
git add <arquivos-alterados>
git commit -m "chore: preparar release v1.0.0 (#N)"
git push -u origin release/v1.0.0
```

 Abrir um Merge Request da release para `main` e, se houver ajustes de estabilização ainda ausentes de `develop`, outro Merge Request de retorno para `develop`. Por fim, criar a tag em `main`:

```bash
git checkout main && git pull origin main
git tag -a v1.0.0 -m "Release v1.0.0 — Sprint 1"
git push origin v1.0.0
git push origin --delete release/v1.0.0
```

## 6.3 Correção por hotfix

**Contexto ilustrativo:** corrigir uma falha crítica no classificador de intenções após integração em `main`. A issue `#34` é usada apenas para demonstrar a convenção e não é apresentada como evidência de hotfix executado.

```bash
git checkout main && git pull origin main
git checkout -b hotfix/corrigir-falha-classificador
git push -u origin hotfix/corrigir-falha-classificador

git commit -m "fix(pln): corrigir falha na classificacao de intencao (#34)"
git commit -m "test(pln): adicionar caso de teste para falha corrigida (#34)"
git push -u origin hotfix/corrigir-falha-classificador
```

 Abrir um Merge Request para `main`. Após o merge, abrir outro Merge Request de sincronização para `develop` e excluir a branch.

---

# 7. Checklist de Conformidade

- [ ] A issue tem DoR, DoD, labels, milestone e assignee preenchidos e está em backlog antes de ir para doing.
- [ ] A branch foi criada a partir de `develop` (ou de `main`, no caso de hotfix).
- [ ] O nome da branch segue a convenção: `<prefixo>/<descricao-em-kebab-case>`.
- [ ] Os commits seguem Conventional Commits em português com `#N` e estão distribuídos ao longo da sprint.
- [ ] O MR aponta para a branch correta e contém `Closes #N`, `## O que foi feito` e `## Como testar`.
- [ ] O reviewer foi designado antes do merge e registrou pelo menos um comentário real.
- [ ] Labels e milestone estão preenchidos no MR.
- [ ] O merge seguiu a estratégia definida (merge commit).
- [ ] A branch temporária foi excluída após o merge.
- [ ] O card no Kanban foi movido para closed após o merge.
