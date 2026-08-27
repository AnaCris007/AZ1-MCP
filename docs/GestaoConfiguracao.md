<p align='center'>
  <a href='https://www.inteli.edu.br/'>
    <img src='../assets/inteli.png' alt='Inteli - Instituto de Tecnologia e Liderança' width='300'>
  </a>
</p>

# Projeto: AZ1

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
- [6.4 Promoção da entrega da sprint por `hmg`](#64-promoção-da-entrega-da-sprint-por-hmg)
- [6.5 Verificação automática da mensagem de commit](#65-verificação-automática-da-mensagem-de-commit)

</details>

- [7. Checklist de Conformidade](#7-checklist-de-conformidade)


---

# 1. Introdução

## 1.1 Objetivo do documento

 Este documento define as políticas de gestão de configuração adotadas pela equipe no projeto AZ1 ao longo do Módulo 7 do Inteli. Estão registrados aqui o fluxo Gitflow adaptado ao módulo, as convenções de nomenclatura de branches, os procedimentos de criação, integração e exclusão de branches, a política de commits e os exemplos práticos que ilustram a aplicação dessas políticas no contexto do projeto. O documento é complementar ao [GestaoProjeto.md](./GestaoProjeto.md), que registra as políticas de processo de desenvolvimento, os acordos de convivência e a gestão das sprints.


## 1.2 Princípios da gestão de configuração

 A gestão de configuração do projeto AZ1 é orientada por quatro princípios fundamentais. O primeiro é a **rastreabilidade**: toda mudança autoral no repositório deve estar associada a uma issue do GitLab, de modo que seja possível identificar por que a alteração foi feita, quem a fez e em qual sprint. Commits de merge gerados pelo GitLab são exceção ao formato autoral, pois sua rastreabilidade decorre do próprio Merge Request. O segundo princípio é a **revisão por pares**: nenhuma alteração é integrada às branches estáveis sem aprovação de um integrante diferente do autor, garantindo qualidade e distribuição do conhecimento. O terceiro é a **proteção das branches permanentes**: `main` e `develop` não recebem commits diretos; toda integração ocorre por Merge Request aprovado. O quarto é a **cadência distribuída**: o trabalho deve ser realizado ao longo da sprint, com commits frequentes e progressivos, evitando a concentração de entregas no último dia.

---

# 2. Fluxo Gitflow

## 2.1 Visão geral

 O projeto AZ1 adota um fluxo baseado no Gitflow, com as branches permanentes `main`, `develop` e `hmg` e as branches temporárias `feature/*`, `release/*` e `hotfix/*` exigidas pelo enunciado oficial. As branches `docs/*` e `fix/*` são especializações adotadas pela equipe para documentação e correções comuns.

 A branch `hmg` é a etapa de homologação entre `develop` e `main`: ela recebe o conteúdo integrado da sprint, serve de ambiente de verificação final e só então é promovida para `main`. Nenhuma promoção para `main` ocorre sem passar por ela.

- fluxo regular: `feature/*`, `docs/*` e `fix/*` → `develop` → `hmg` → `main`;
- correção urgente: `hotfix/*` parte de `main` e retorna por MRs separados para `main` e `develop`.

 **Evolução deste acordo.** Na Sprint 1, esta seção registrava que a `hmg` não existia entre as branches inspecionadas e, por isso, não integrava o fluxo documentado. A constatação era correta no momento da escrita, em 14/08/2026, mas envelheceu no mesmo dia: a branch foi criada logo em seguida e o MR !24 promoveu `hmg` para `main` às 20h27 daquele dia, tornando-se o caminho efetivo da entrega da Sprint 1. O texto foi corrigido na Sprint 2 para descrever o fluxo oficial do módulo, que é também o fluxo que a equipe de fato utilizou. O registro anterior fica preservado aqui, conforme a convenção de evolução sem apagamento definida na Seção 1.2 do `GestaoProjeto.md`.

## 2.2 Estrutura de branches


| Branch | Origem | Finalidade | Destino do merge | Permanência |
|---|---|---|---|---|
| `main` | Não se aplica | Versões estáveis e entregáveis | Não se aplica | Permanente |
| `develop` | `main` | Integração contínua do trabalho da sprint | `hmg`, por MR | Permanente |
| `hmg` | `develop` | Homologação da versão candidata antes da promoção | `main`, por MR | Permanente |
| `feature/<descricao>` | `develop` | Nova funcionalidade ou artefato | `develop`, por MR | Temporária |
| `docs/<descricao>` | `develop` | Documentação | `develop`, por MR | Temporária |
| `fix/<descricao>` | `develop` | Correção de bug | `develop`, por MR | Temporária |
| `hotfix/<descricao>` | `main` | Correção urgente em produção | `main` e `develop`, por MR | Temporária |
| `release/<versao>` | `develop` | Estabilização da versão candidata | `main` e `develop`, por MRs separados quando houver ajustes de estabilização | Temporária |

 A `hmg` e a `release/*` cumprem papéis distintos e não se substituem. A `hmg` é permanente e concentra a homologação de cada ciclo: é por ela que todo conteúdo passa antes de chegar à `main`. A `release/*` é temporária e existe para estabilizar e etiquetar uma versão específica quando houver ajustes que não devam voltar diretamente para `develop`. Até o momento, a equipe promoveu para `main` exclusivamente pela `hmg`; a `release/*` permanece definida conforme o enunciado do módulo, sem uso registrado no histórico do repositório.

## 2.3 Fluxo entre branches

```text
feature/* ─┐
docs/* ────┼──> develop ──> hmg ──> main
fix/* ─────┘

              develop ──> release/* ──> main          (estabilização de versão)
                              └────────> develop      (ajustes da release)

main ──> hotfix/* ──> main
                 └──> develop
```

No fluxo regular, o trabalho de cada integrante é integrado a `develop` por Merge Request. Ao final do ciclo, o conteúdo consolidado em `develop` é promovido para `hmg`, onde a equipe realiza a homologação da entrega, e só então segue de `hmg` para `main` por um novo Merge Request. Esse é o caminho oficial do módulo e o utilizado pela equipe nas promoções realizadas até aqui.

A branch `release/*` é criada a partir de `develop` para estabilizar e etiquetar uma versão quando houver ajustes de estabilização que precisem retornar a `develop`. Um `hotfix/*` parte de `main` e retorna tanto para `main` quanto para `develop`, evitando que a correção se perca na próxima versão.

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
- Letras minúsculas, sem acentos e sem espaços, usando hífen como separador;
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
| Critérios de aprovação | Pelo menos um comentário de revisão real, já que aprovação sem comentário não conta |
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
3. Designar o reviewer antes de solicitar o merge, lembrando que o autor não revisa o próprio MR;
4. Aguardar a revisão com pelo menos um comentário registrado no MR e realizar os ajustes solicitados;
5. Após aprovação, realizar o merge pelo GitLab, sendo a estratégia adotada o **merge commit**, para preservar o histórico completo;
6. Excluir a branch de trabalho imediatamente após o merge.

As promoções para `main` seguem o mesmo controle e ocorrem em duas etapas. Primeiro, abre-se um Merge Request de `develop` para `hmg`, onde a entrega consolidada da sprint é homologada. Depois da verificação, abre-se um segundo Merge Request de `hmg` para `main`. Cada uma dessas integrações exige revisão e aprovação próprias, e a abertura do MR de promoção para `main` é revezada entre os integrantes conforme o Contrato de Convivência. Quando a versão exigir ajustes de estabilização que não devam voltar diretamente para `develop`, utiliza-se uma branch `release/*`, que retorna a `develop` por Merge Request separado.

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
git tag -a v1.0.0 -m "Release v1.0.0 da Sprint 1"
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

 Commits e pushes diretos para `main`, `hmg` e `develop` são proibidos. A integração deve ocorrer por Merge Request, com **no mínimo uma aprovação** de revisor diferente do autor e com os critérios da Seção 4.1 atendidos. Somente integrantes autorizados pelo grupo podem concluir o merge; o autor pode realizá-lo apenas depois da aprovação registrada pelo revisor. A rotação de responsáveis pelas promoções para `main` está definida no Contrato de Convivência.

 As três branches permanentes são configuradas como protegidas no GitLab, o que impede o push direto e condiciona toda alteração à abertura de Merge Request. Nenhum commit direto em branch protegida foi observado no histórico do repositório ao longo das Sprints 1 e 2, conforme registrado na Seção 4.6 do `GestaoProjeto.md`.

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

 Toda branch de trabalho, todo commit autoral e todo Merge Request do projeto AZ1 devem estar associados a uma issue do GitLab. O vínculo é estabelecido de três formas: o nome da branch descreve a issue desenvolvida; cada commit autoral referencia a issue com `#N`; e o MR contém `Closes #N` na descrição, encerrando a issue automaticamente quando o merge é realizado. Commits de merge gerados pela plataforma são rastreados pelo MR correspondente e não precisam repetir o padrão de mensagem autoral.

## 5.2 Convenção de commits

 Os commits seguem o padrão Conventional Commits, padronizado em português. O formato adotado é:

    <tipo>(<escopo opcional>): <descrição curta em português> (#N)


**Regras:**
- Descrição no infinitivo: `adicionar` está correto, `adicionei` não;
- Máximo de 72 caracteres na primeira linha;
- Um commit corresponde a uma intenção, sem misturar tipos diferentes;
- Referência à issue obrigatória com `#N`;
- Commits distribuídos ao longo da sprint, já que concentrar no último dia é anti-padrão penalizado pelo dashboard.

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

    atualização documentação          (sem tipo e sem #N)
    docs: atualizei o brainstorming    (verbo no passado)
    feat: nova feature (#15)           (descrição genérica)


## 5.3 Evidências de aplicação

| Evidência | Link | O que demonstra |
|---|---|---|
| Issue | [Issue #16](https://git.inteli.edu.br/graduacao/2026-2a/t17/g01/-/issues/16) | Task refinada com DoR, DoD, labels, milestone e assignee |
| Branch | [docs/brainstorming-features](https://git.inteli.edu.br/graduacao/2026-2a/t17/g01/-/tree/docs/brainstorming-features) | Nomenclatura padronizada e origem em `develop` |
| Merge Request | [MR !11](https://git.inteli.edu.br/graduacao/2026-2a/t17/g01/-/merge_requests/11) | Vínculo com a issue, reviewer designado e revisão real |
| Histórico de commits | [Commits da branch](https://git.inteli.edu.br/graduacao/2026-2a/t17/g01/-/commits/docs/brainstorming-features) | Commits semânticos em português com `#N` distribuídos ao longo da sprint |

 Os links acima são evidências declaradas pela equipe. O histórico local confirma a existência de branches de trabalho com prefixos padronizados, commits autorais vinculados a issues e merges em `develop`. O conteúdo completo da issue e do Merge Request depende de acesso ao GitLab e, portanto, não pôde ser validado apenas com os arquivos locais. Não foram encontradas evidências locais de uso de `release/*` ou `hotfix/*`; as Seções 6.2 e 6.3 são exemplos de aplicação futura, não registros de execução.

### Conformidade dos commits na Sprint 2

 A equipe conferiu o histórico da sprint contra as regras da Seção 5.2, considerando apenas os commits autorais, conforme a exceção definida na Seção 5.1. O resultado por regra:

| Regra da Seção 5.2 | Situação |
|---|---|
| Referência à issue com `#N` | Atendida sem exceção |
| Tipo Conventional Commits válido | Atendida sem exceção |
| Descrição no infinitivo | Não atendida em parte relevante dos commits |
| Primeira linha com até 72 caracteres | Não atendida em alguns commits |

 A referência à issue, apontada como não conforme na avaliação da Sprint 1, foi integralmente corrigida e manteve-se assim ao longo de toda a sprint. É a regra que sustenta a rastreabilidade entre commit e task, e por isso a mais relevante das quatro.

 Permanecem duas não conformidades declaradas, ambas de forma e sem efeito sobre a rastreabilidade: o uso do presente do indicativo no lugar do infinitivo, forma que a própria Seção 5.2 apresenta como inválida, e a extrapolação do limite de 72 caracteres. A equipe optou por manter as regras como estão e registrar o desvio, em vez de flexibilizar a convenção para acomodar a prática. O histórico já integrado não é reescrito, e a correção vale para os commits das próximas sprints, apoiada no hook da Seção 6.5, que recusa a mensagem antes de o commit ser criado. A ação correspondente está registrada na Seção 4.2.4 do `GestaoProjeto.md`.

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
git tag -a v1.0.0 -m "Release v1.0.0 da Sprint 1"
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

## 6.4 Promoção da entrega da sprint por `hmg`

**Contexto real:** este é o único exemplo desta seção que registra execução, e não aplicação futura. A entrega da Sprint 1 foi promovida para `main` por este caminho, no MR !24, mergeado em 14/08/2026.

 A promoção ocorre em duas etapas, cada uma com Merge Request e aprovação próprias. Primeiro, o conteúdo consolidado em `develop` é levado para homologação:

```bash
git checkout develop && git pull origin develop
git checkout hmg && git pull origin hmg
git merge develop
git push origin hmg
```

 Na prática, esse merge é realizado pela interface do GitLab, por um Merge Request de `develop` para `hmg`, de modo que a revisão fique registrada. Com a entrega homologada em `hmg`, abre-se o segundo Merge Request, de `hmg` para `main`, cuja abertura é revezada entre os integrantes conforme o Contrato de Convivência. Depois da integração em `main`, cria-se a tag da versão:

```bash
git checkout main && git pull origin main
git tag -a v0.2.0 -m "Release v0.2.0 da Sprint 2"
git push origin v0.2.0
```

 As branches `develop` e `hmg` são permanentes e não são excluídas ao final do ciclo; apenas as branches de trabalho o são, conforme a Seção 4.3.

## 6.5 Verificação automática da mensagem de commit

**Contexto:** a aferição registrada na Seção 5.3 mostrou que a referência à issue atingiu 100% de conformidade na Sprint 2, enquanto a descrição no infinitivo ficou em 39,3%. A diferença é que a primeira regra passou a ser lembrada e a segunda continuou dependendo de atenção manual a cada mensagem. O hook abaixo transfere essa verificação para o próprio `git commit`.

 O arquivo é criado em `.git/hooks/commit-msg`, que é local a cada cópia do repositório e não é versionado, de modo que cada integrante o instala em sua máquina:

```bash
cat > .git/hooks/commit-msg <<'HOOK'
#!/usr/bin/env bash
msg=$(head -n1 "$1")
# merges gerados pela plataforma são exceção, conforme a Seção 5.1
grep -qE '^Merge ' <<< "$msg" && exit 0

tipos='feat|fix|docs|style|refactor|test|chore|perf|ci|build|revert'
erro=0
grep -qE "^($tipos)(\([^)]+\))?: " <<< "$msg" || { echo "✗ tipo Conventional Commits ausente ou inválido"; erro=1; }
grep -qE '#[0-9]+' <<< "$msg" || { echo "✗ falta referência à issue (#N)"; erro=1; }
[ ${#msg} -le 72 ] || { echo "✗ primeira linha com ${#msg} caracteres (máximo 72)"; erro=1; }
verbo=$(sed -E "s/^($tipos)(\([^)]+\))?: *//" <<< "$msg" | awk '{print $1}')
grep -qE '(ar|er|ir)$' <<< "$verbo" || { echo "✗ descrição deve começar no infinitivo (recebido: '$verbo')"; erro=1; }

[ $erro -eq 0 ] || { echo; echo "Mensagem recusada. Formato: <tipo>(<escopo>): <descrição no infinitivo> (#N)"; exit 1; }
HOOK
chmod +x .git/hooks/commit-msg
```

 O hook recusa o commit antes que ele seja criado, o que permite corrigir a mensagem sem reescrever histórico. Ele não substitui a revisão por pares nem o dashboard do módulo: verifica apenas a forma da mensagem, não a pertinência do commit.

---

# 7. Checklist de Conformidade

- [ ] A issue tem DoR, DoD, labels, milestone e assignee preenchidos e está em backlog antes de ir para doing.
- [ ] A branch foi criada a partir de `develop` (ou de `main`, no caso de hotfix).
- [ ] A promoção para `main` passou por `hmg`, com Merge Request e aprovação em cada etapa.
- [ ] O nome da branch segue a convenção: `<prefixo>/<descricao-em-kebab-case>`.
- [ ] Os commits seguem Conventional Commits em português com `#N` e estão distribuídos ao longo da sprint.
- [ ] O hook local de `commit-msg` da Seção 6.5 está instalado na cópia de trabalho.
- [ ] O MR aponta para a branch correta e contém `Closes #N`, `## O que foi feito` e `## Como testar`.
- [ ] O reviewer foi designado antes do merge e registrou pelo menos um comentário real.
- [ ] Labels e milestone estão preenchidos no MR.
- [ ] O merge seguiu a estratégia definida (merge commit).
- [ ] A branch temporária foi excluída após o merge.
- [ ] O card no Kanban foi movido para closed após o merge.
