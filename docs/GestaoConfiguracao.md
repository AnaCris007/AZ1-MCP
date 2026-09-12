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

<details>
<summary><strong>7. Coerência entre Política e Prática</strong></summary>

- [7.1 O que foi inspecionado, e com que alcance](#71-o-que-foi-inspecionado-e-com-que-alcance)
- [7.2 Quadro de aderência](#72-quadro-de-aderência)
- [7.3 Leitura do quadro](#73-leitura-do-quadro)

</details>

- [8. Checklist de Conformidade](#8-checklist-de-conformidade)


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

 A branch `hmg` é a etapa de homologação entre `develop` e `main`: ela recebe o conteúdo integrado da sprint, serve de ambiente de verificação final e só então é promovida para `main`. Toda promoção regular para `main` passa por ela; hotfix é a exceção urgente documentada, com retorno a develop e sincronização posterior de hmg.

- fluxo regular: `feature/*`, `docs/*` e `fix/*` → `develop` → `hmg` → `main`;
- correção urgente: `hotfix/*` parte de `main` e retorna por MRs separados para `main` e `develop`.

 **Evolução deste acordo.** Na Sprint 1, esta seção registrava que a `hmg` não existia entre as branches inspecionadas e, por isso, não integrava o fluxo documentado. A constatação era correta no momento da escrita, em 14/08/2026, mas envelheceu no mesmo dia: a branch foi criada logo em seguida e o MR !24 promoveu `hmg` para `main` às 20h27 daquele dia, tornando-se o caminho efetivo da entrega da Sprint 1. O texto foi corrigido na Sprint 2 para descrever o fluxo oficial do módulo, que é também o fluxo que a equipe de fato utilizou. O registro anterior fica preservado aqui, conforme a convenção de evolução sem apagamento definida na Seção 1.2 do `GestaoProjeto.md`.

## 2.2 Estrutura de branches


| Branch | Finalidade | Origem | Destino do merge | Quando criar | Aprovação exigida | Quando excluir | Exemplo |
|---|---|---|---|---|---|---|---|
| `main` | Versões estáveis e entregáveis | Não se aplica | Não se aplica | Existe desde a criação do repositório | Toda entrada exige MR aprovado por revisor | Nunca: é permanente | `main` |
| `develop` | Integração contínua do trabalho da sprint | `main` | `hmg`, por MR | Existe desde o início do módulo | Toda entrada exige MR aprovado por revisor | Nunca: é permanente | `develop` |
| `hmg` | Homologação da versão candidata antes da promoção | `develop` | `main`, por MR | Existe desde 14/08/2026 | Toda entrada exige MR aprovado por revisor | Nunca: é permanente | `hmg` |
| `feature/<descricao>` ou `feat/<descricao>` | Nova funcionalidade ou artefato executável | `develop` | `develop`, por MR | Ao iniciar uma task de funcionalidade com o DoR atendido | Um revisor diferente do autor | Imediatamente após o merge | `feat/construir-api-de-audio` |
| `docs/<descricao>` | Documentação, sem alteração de comportamento | `develop` | `develop`, por MR | Ao iniciar uma task de documentação com o DoR atendido | Um revisor diferente do autor | Imediatamente após o merge | `docs/modelo-logico-relacional` |
| `fix/<descricao>` | Correção de defeito já integrado à `develop` | `develop` | `develop`, por MR | Ao identificar o defeito e refinar a issue correspondente | Um revisor diferente do autor | Imediatamente após o merge | `fix/diagramas` |
| `hotfix/<descricao>` | Correção urgente sobre versão já promovida | `main` | `main` e `develop`, por MRs separados | Somente quando a falha estiver em `main` e não puder aguardar o ciclo regular | Um revisor diferente do autor, em cada um dos dois MRs | Após os dois merges concluídos | `hotfix/corrigir-falha-classificador` |
| `release/<versao>` | Estabilização e etiquetagem da versão candidata | `develop` | `hmg` e, havendo ajustes, `develop`, por MRs separados | Quando a versão exigir ajustes de estabilização que não devam voltar diretamente para `develop` | Um revisor diferente do autor, em cada MR | Após a criação da tag em `main` | `release/v1.0.0` |

**Estado observado no repositório.** Os tipos com uso registrado no histórico são: `main`, `develop`, `hmg` e as temporárias `feature/`, `feat/`, `docs/` e `fix/`. **Não há registro de uso de `release/*` nem de `hotfix/*`**: os exemplos dessas duas linhas descrevem a política e não constituem evidência de execução, conforme a Seção 5.3. Registra-se também que **o repositório não possui nenhuma tag**, portanto a etiquetagem prevista nas Seções 4.4 e 6.4 não está demonstrada no corte. Ausência de tag atual não prova que uma tag nunca tenha existido.

 A `hmg` e a `release/*` cumprem papéis distintos e não se substituem. A `hmg` é permanente e concentra a homologação de cada ciclo: é por ela que o conteúdo de promoção regular passa antes de chegar à `main`, com a exceção urgente de hotfix descrita acima. A `release/*` é temporária e existe para estabilizar e etiquetar uma versão específica quando houver ajustes que não devam voltar diretamente para `develop`. Até o momento, a equipe promoveu para `main` exclusivamente pela `hmg`; a `release/*` permanece definida conforme o enunciado do módulo, sem uso registrado no histórico do repositório.

## 2.3 Fluxo entre branches

```text
feature/* ─┐
docs/* ────┼──> develop ──> hmg ──> main
fix/* ─────┘

              develop ──> release/* ──> hmg ──> main          (estabilização de versão)
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

**Sobre o número da issue no nome da branch.** Uma convenção difundida inclui o número da issue no próprio nome, no formato `tipo/numero-descricao`, como em `feat/123-recebimento-audio`. **A equipe não adota esse formato**, e a escolha é deliberada: o vínculo com a issue já é estabelecido em dois pontos obrigatórios (a referência `#N` em cada commit autoral e o `Closes #N` na descrição do Merge Request), de modo que acrescentá-lo ao nome da branch seria uma terceira repetição do mesmo dado. O que se perde é a legibilidade do vínculo na listagem de branches; o que se ganha é um nome que descreve o trabalho, e não um número que exige consulta para significar algo. A convenção adotada é a única válida no projeto, e a aferição da Seção 7 mostra conformidade do prefixo, mas também uma exceção de maiúscula na descrição na Sprint 2.

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
git pull --ff-only origin develop
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
| Branch de destino correta | Branches de trabalho apontam para `develop`; releases seguem para `hmg` e depois `main`; hotfixes retornam para `main` e `develop` |
| Quantidade mínima de revisores | Um revisor, diferente do autor |
| Critérios de aprovação | Aprovação por par e comentário técnico, conforme política do grupo. Na auditoria de participação, aprovação registrada também é revisão efetiva; a conformidade com a exigência local de comentário é verificada separadamente |
| Tratamento de conflitos | O autor resolve os conflitos antes de solicitar a revisão |
| Evidências obrigatórias | `Closes #N` na descrição, seções `## O que foi feito` e `## Como testar`, labels e milestone preenchidos |

O modelo de MR também possui suporte automatizado: [`setup_mr_template.py`](../gitlab-issue-kit/scripts/setup_mr_template.py) lê a convenção de [`config.yml`](../gitlab-issue-kit/scripts/config.yml) e gera `.gitlab/merge_request_templates/Default.md` na raiz. O modo `--dry-run` mostra o resultado sem gravar; `--apply-remote` também aplica o texto à configuração do GitLab. A presença do script é um entregável do processo, enquanto sua execução e publicação são etapas distintas. O [guia do kit](../gitlab-issue-kit/docs/README.md) documenta o procedimento.

**Conteúdo mínimo da descrição:** a seção “O que foi feito” explica o problema, o resultado e os arquivos afetados. “Como testar” informa comandos, ambiente, SHA e resultado esperado, com links para a evidência obtida. O vínculo de fechamento usa o número real da issue, após conferir que o MR entrega todo o seu escopo; uma contribuição parcial deve referenciar a issue sem declarar sua conclusão.

O checklist do MR deve conferir revisão independente, aprovação, resolução das discussões, testes aplicáveis, documentação, labels e milestone. Esses itens são critérios para aceite, não evidência de que este artefato já foi aprovado.

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
git status --short
git switch develop
git pull --ff-only origin develop
git branch --merged origin/develop
# Somente após conferir merge, trabalho adicional e autorização:
git branch -d docs/brainstorming-features
git push origin --delete docs/brainstorming-features
```

## 4.4 Releases e hotfixes

**Release:**

```bash
git checkout develop && git pull --ff-only origin develop
git checkout -b release/v1.0.0
# realizar e validar os ajustes de estabilização
git add <arquivos-alterados>
git commit -m "chore: preparar release v1.0.0 (#N)"
git push -u origin release/v1.0.0
```

 Após a estabilização, abrir um Merge Request de `release/*` para `hmg`, seguido de `hmg` para `main`. Se a release contiver ajustes que ainda não estejam em `develop`, abrir também um Merge Request de retorno para `develop`. Depois da integração em `main`, criar a tag e excluir a branch de release:

```bash
git checkout main && git pull --ff-only origin main
git tag -a v1.0.0 -m "Release v1.0.0 da Sprint 1"
git push origin v1.0.0
git push origin --delete release/v1.0.0
```

**Hotfix:**

```bash
git checkout main && git pull --ff-only origin main
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

 A política exige proteção das três branches permanentes. A proteção deve ser conferida nas configurações do projeto; a topologia do Git não substitui essa configuração. Nenhum commit direto em branch protegida foi observado no histórico do repositório ao longo das Sprints 1 e 2, conforme registrado na Seção 4.6 do `GestaoProjeto.md`.

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

 Toda branch de trabalho, todo commit autoral e todo Merge Request do projeto AZ1 devem estar associados a uma issue do GitLab. O vínculo é estabelecido de três formas: o nome da branch descreve a issue desenvolvida; cada commit autoral referencia a issue com `#N`; e o MR contém `Closes #N` na descrição, permitindo fechamento automático conforme destino e configuração; o estado deve ser conferido após o merge. Commits de merge gerados pela plataforma são rastreados pelo MR correspondente e não precisam repetir o padrão de mensagem autoral.

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
| Branch | [docs/brainstorming-features](https://git.inteli.edu.br/graduacao/2026-2a/t17/g01/-/tree/8affbbeb2767dba6eb0f52d11fa21d961802a231) | Nomenclatura padronizada e origem em `develop` |
| Merge Request | [MR !11](https://git.inteli.edu.br/graduacao/2026-2a/t17/g01/-/merge_requests/11) | Vínculo com a issue, reviewer designado e revisão real |
| Aderência da política à prática | [Seção 7.2 deste documento](#72-quadro-de-aderência) | Confronto item a item entre o que a política define e o que o repositório registra |
| Histórico de commits | [Commits da branch](https://git.inteli.edu.br/graduacao/2026-2a/t17/g01/-/commits/8affbbeb2767dba6eb0f52d11fa21d961802a231) | Commits semânticos em português com `#N` distribuídos ao longo da sprint |

 Os links acima são evidências declaradas pela equipe. O histórico local confirma a existência de branches de trabalho com prefixos padronizados, commits autorais vinculados a issues e merges em `develop`. O conteúdo completo da issue e do Merge Request depende de acesso ao GitLab e, portanto, não pôde ser validado apenas com os arquivos locais. Não foram encontradas evidências locais de uso de `release/*` ou `hotfix/*`; as Seções 6.2 e 6.3 são exemplos de aplicação futura, não registros de execução.

### Conformidade dos commits na Sprint 2

 A equipe conferiu o histórico da sprint contra as regras da Seção 5.2, considerando apenas os commits autorais, conforme a exceção definida na Seção 5.1.

**Método da aferição.** Foram considerados os **94 commits autorais únicos**, identificados por SHA, com data de autoria entre 15/08/2026 e 28/08/2026, alcançáveis a partir de qualquer referência local. Commits de merge foram excluídos, pela exceção da Seção 5.1, e commits que aparecem em mais de uma branch foram contados uma única vez. A apuração pode ser reproduzida sobre o próprio repositório, e o percentual de cada regra é a razão entre os commits conformes e esses 94.

| Regra da Seção 5.2 | Conformes | Percentual | Situação |
|---|---:|---:|---|
| Referência à issue com `#N` | 94 de 94 | **100,0%** | Atendida sem exceção |
| Tipo Conventional Commits válido | 94 de 94 | **100,0%** | Atendida sem exceção |
| Primeira linha com até 72 caracteres | 78 de 94 | 83,0% | Não atendida em 16 commits |
| Descrição no infinitivo | 34 de 94 | 36,2% | Não atendida em 60 commits |

 A referência à issue, apontada como não conforme na avaliação da Sprint 1, foi integralmente corrigida e manteve-se assim ao longo de toda a sprint. É a regra que sustenta a rastreabilidade entre commit e task, e por isso a mais relevante das quatro.

 Permanecem duas não conformidades declaradas, ambas de forma e sem efeito sobre a rastreabilidade. A primeira é o uso do presente do indicativo no lugar do infinitivo, forma que a própria Seção 5.2 apresenta como inválida: mensagens como `docs: adiciona diagrama conceitual #116` e `fix: conserta documentação de tecnologias #152` são as recorrentes. A segunda é a extrapolação do limite de 72 caracteres, concentrada em mensagens que descrevem várias alterações de uma vez, como a que registra a implementação do endpoint de áudio com validação de duração, formato e assinatura.

 A equipe optou por manter as regras como estão e registrar o desvio, em vez de flexibilizar a convenção para acomodar a prática. O histórico já integrado não é reescrito, e a correção vale para os commits das próximas sprints, apoiada no hook da Seção 6.5, que recusa a mensagem antes de o commit ser criado. A ação correspondente está registrada na Seção 4.2.4 do `GestaoProjeto.md`, e a criação do hook é a task T37 do planejamento da Sprint 3.

**Distribuição ao longo da sprint.** A quinta regra da Seção 5.2 (commits distribuídos ao longo do ciclo) é a única que não se afere por mensagem, e sim por data. Sobre os mesmos 94 commits:

| Dia | Commits | Participação |
|---|---:|---:|
| 20/08 | 1 | 1,1% |
| 21/08 | 4 | 4,3% |
| 22/08 | 1 | 1,1% |
| 23/08 | 2 | 2,1% |
| 24/08 | 8 | 8,5% |
| 25/08 | 23 | 24,5% |
| 26/08 | 13 | 13,8% |
| **27/08** | **39** | **41,5%** |
| 28/08 | 3 | 3,2% |

 A regra **não é atendida**: um único dia concentra 41,5% dos commits, e os três dias de maior volume somam 79,8%. O dado sustenta o ponto fraco registrado na Seção 4.2.3 do `GestaoProjeto.md` e o critério de 40% fixado como meta para a Sprint 3.

**Distribuição por integrante.** A autoria, em contrapartida, está equilibrada, o que confirma que o problema é de cadência e não de divisão de trabalho:

| Integrante | Commits autorais | Participação |
|---|---:|---:|
| Matheus Ferreira da Silva | 16 | 17,0% |
| Karol Barbosa Rocha | 15 | 16,0% |
| Rui Facó | 14 | 14,9% |
| Felipe Simão | 14 | 14,9% |
| Paulo Henrique Bueno Fernandes | 13 | 13,8% |
| Ana Cristina Jardim | 13 | 13,8% |
| Tobias Viana | 9 | 9,6% |

 A diferença entre o integrante com mais e o com menos commits é de sete registros, e todos os sete contribuíram em volume comparável. Commits são uma medida grosseira de esforço (uma seção longa de documentação pode caber em um commit, e um ajuste pequeno de código pode render três), de modo que a leitura correta desta tabela é a ausência de concentração, e não a equivalência de carga.

---

# 6. Exemplos Práticos

## 6.1 Desenvolvimento de uma feature de documentação

**Contexto:** implementar a seção de brainstorming de features no `Projeto.md` (issue #16, Sprint 1).

```bash
git checkout develop && git pull --ff-only origin develop
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
git checkout develop && git pull --ff-only origin develop
git checkout -b release/v1.0.0
# realizar e validar os ajustes de estabilização
git add <arquivos-alterados>
git commit -m "chore: preparar release v1.0.0 (#N)"
git push -u origin release/v1.0.0
```

 Abrir um Merge Request da release para `hmg`, seguido de `hmg` para `main` e, se houver ajustes de estabilização ainda ausentes de `develop`, outro Merge Request de retorno para `develop`. Por fim, criar a tag em `main`:

```bash
git checkout main && git pull --ff-only origin main
git tag -a v1.0.0 -m "Release v1.0.0 da Sprint 1"
git push origin v1.0.0
git push origin --delete release/v1.0.0
```

## 6.3 Correção por hotfix

**Contexto ilustrativo:** corrigir uma falha crítica no classificador de intenções após integração em `main`. A issue `#34` é usada apenas para demonstrar a convenção e não é apresentada como evidência de hotfix executado.

```bash
git checkout main && git pull --ff-only origin main
git checkout -b hotfix/corrigir-falha-classificador
git push -u origin hotfix/corrigir-falha-classificador

git commit -m "fix(pln): corrigir falha na classificacao de intencao (#34)"
git commit -m "test(pln): adicionar caso de teste para falha corrigida (#34)"
git push -u origin hotfix/corrigir-falha-classificador
```

 Abrir um Merge Request para `main`. Após o merge, abrir outro Merge Request de sincronização para `develop` e excluir a branch.

## 6.4 Promoção da entrega da sprint por `hmg`

**Contexto real:** a integração abaixo está registrada no Git; os comandos de tag são ilustrativos, não evidência de execução. A entrega da Sprint 1 foi promovida para `main` por este caminho, no MR !24, mergeado em 14/08/2026.

 A promoção ocorre em duas etapas, cada uma com Merge Request e aprovação próprias. Primeiro, o conteúdo consolidado em `develop` é levado para homologação:

```bash
git fetch origin
git log --oneline origin/hmg..origin/develop
# No GitLab: abrir MR develop -> hmg, revisar e aprovar.
# Após homologação: abrir MR hmg -> main, revisar e aprovar.
```

 Na prática, esse merge é realizado pela interface do GitLab, por um Merge Request de `develop` para `hmg`, de modo que a revisão fique registrada. Com a entrega homologada em `hmg`, abre-se o segundo Merge Request, de `hmg` para `main`, cuja abertura é revezada entre os integrantes conforme o Contrato de Convivência. Depois da integração em `main`, cria-se a tag da versão:

```bash
git checkout main && git pull --ff-only origin main
git tag -a v0.2.0 -m "Release v0.2.0 da Sprint 2"
git push origin v0.2.0
```

 As branches `develop` e `hmg` são permanentes e não são excluídas ao final do ciclo; apenas as branches de trabalho o são, conforme a Seção 4.3.

## 6.5 Verificação automática da mensagem de commit

**Contexto:** a aferição registrada na Seção 5.3 mostrou que a referência à issue atingiu 100% de conformidade na Sprint 2, enquanto a descrição no infinitivo ficou em 36,2%. A causa dessa diferença não foi medida. O hook abaixo faz uma verificação heurística no `git commit`; o sufixo ar/er/ir não certifica que a palavra é verbo no infinitivo, nem comprova instalação coletiva.

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

# 7. Coerência entre Política e Prática

## 7.1 O que foi inspecionado, e com que alcance

 Esta seção confronta cada política deste documento com o que o repositório e o GitLab efetivamente registram. O histórico Git foi usado como fonte primária para branches, commits e merges; a consulta à plataforma complementou a inspeção com aprovações, revisores e estado dos Merge Requests. A conferência final da Sprint 2, validada no feedback do artefato, está registrada na Seção 4.2.4 do `GestaoProjeto.md`.

 A distinção importa e é aplicada rigorosamente na tabela abaixo: **ausência de informação local não é descumprimento comprovado**. Onde a prática não pôde ser observada, a linha diz exatamente isso.

 Uma ressalva adicional vale para a linha de exclusão de branches: as referências remotas conhecidas localmente refletem a última sincronização com o servidor, e não necessariamente o estado deste instante. O número deve ser reconferido no GitLab antes de servir de base para ação.

## 7.2 Quadro de aderência

| Item | Política documentada | Prática observada | Desvio | Ação para a Sprint 3 |
|---|---|---|---|---|
| Nomenclatura de branches | `<prefixo>/<descricao-em-kebab-case>`, com prefixo da lista da Seção 3.1 | As 25 branches distintas da sprint usam prefixo válido: `docs`, `feat`, `feature` e `fix`: e descrição em kebab-case. Uma delas, `docs/diario-de-construcao-prototipo-B`, termina com letra maiúscula | **Desvio pontual**: 24 de 25 em conformidade integral | Manter a convenção; conferir o nome na abertura do MR, quando ainda é barato renomear |
| Origem das branches | Branches de trabalho partem de `develop` | Verificado nos 26 merges: em todos, o ponto de bifurcação entre a branch e o destino pertence à `develop` | Nenhum | Manter |
| Destino dos Merge Requests | Branches de trabalho apontam para `develop` | Os 26 MRs da sprint apontam para `develop` | Nenhum | Manter |
| Proteção de branches permanentes | Sem commit direto em `main`, `hmg` e `develop` | Nenhum commit direto observado no histórico das três branches | Nenhum | Manter |
| Vínculo entre commit e issue | Todo commit autoral referencia `#N` | 94 de 94 commits autorais referenciam a issue | Nenhum | Manter |
| Tipo Conventional Commits | Tipo válido em toda mensagem autoral | 94 de 94 commits usam tipo válido | Nenhum | Manter |
| Descrição no infinitivo | Verbo no infinitivo após o tipo | 34 de 94, ou 36,2% | **Desvio comprovado** | Instalar o hook da Seção 6.5, task T37 |
| Limite de 72 caracteres | Primeira linha com até 72 caracteres | 78 de 94, ou 83,0% | **Desvio comprovado** | Mesmo hook, que também verifica o comprimento |
| Cadência dos commits | Commits distribuídos ao longo da sprint | Um único dia concentra 41,5% dos commits | **Desvio comprovado** | Primeira ação da Seção 4.2.4 do `GestaoProjeto.md`, com critério de 40% por dia |
| Vínculo entre MR e issue | `Closes #N` na descrição do MR | Os 26 MRs têm ao menos uma issue referenciada nos commits da branch. A presença específica de `Closes #N` no corpo de cada MR não foi incluída na aferição final | **Não verificável integralmente** | Incluir a verificação do campo `Closes` na conferência final de cada sprint |
| Revisão por par com comentário real | Ao menos um comentário técnico independente | A participação dos sete integrantes em revisões na Sprint 2 foi confirmada no feedback do artefato; a Seção 4.2.4 registra a distribuição | Participação confirmada no retorno da avaliação | Manter o vínculo de cada revisão à aprovação e ao comentário no MR; designação isolada não substitui revisão |
| Autor não conclui o próprio merge sem aprovação | O autor só realiza o merge depois da aprovação registrada | A consulta final ao GitLab confirmou a existência de revisão registrada por integrante diferente do autor antes das integrações examinadas | Nenhum | Manter |
| Estratégia de merge | Merge commit, para preservar o histórico | Os 26 MRs geraram commit de merge, sem indício de *squash* ou *rebase* | Nenhum | Manter |
| Exclusão da branch após o merge | Branch temporária excluída imediatamente após o merge | Os 26 MRs partiram de 25 branches distintas, das quais **7 foram excluídas e 18 continuam existindo** nas referências remotas conhecidas localmente | **Desvio comprovado** | Excluir as branches já mescladas e marcar a opção de exclusão da branch de origem na abertura de cada MR |
| Sincronização com a base antes do MR | Merge explícito de `develop` na branch de trabalho | Prática observada em várias branches, com commits de merge de `develop` para a branch de trabalho | Nenhum | Manter |
| Ausência de reescrita de histórico | Sem `push --force` e sem `reset --hard` em branch compartilhada | Nenhum indício de reescrita no histórico das branches inspecionadas | Nenhum | Manter |
| Promoção por `hmg` | `develop` para `hmg` para `main`, com MR e aprovação em cada etapa | Executada na Sprint 2: a integração de `develop` em `hmg` foi seguida pela promoção de `hmg` para `main`, concluída às 18h13 (BRT) de 28/08 pelo commit `6f70532` | Nenhum | Manter o fluxo e repeti-lo antes de cada Sprint Review |
| Etiquetagem da versão | Tag anotada criada em `main` após a promoção | **Nenhuma tag existe no repositório** | **Desvio comprovado** | Criar a tag da Sprint 2 junto da promoção, e incluir a etapa no checklist da Seção 8 |
| Uso de `release/*` | Branch de estabilização quando houver ajustes que não devam voltar a `develop` | Sem uso registrado | Nenhum: a política prevê o uso condicionado, e a condição não ocorreu | Manter a política; os exemplos permanecem ilustrativos |
| Uso de `hotfix/*` | Correção urgente a partir de `main` | Sem uso registrado | Nenhum, pela mesma razão | Manter a política |
| Esteira de verificação | Etapas de lint, testes, build, registro, deploy e verificação, conforme a Seção 3.7.6 do `Projeto.md` | No retrato de S2, CI ainda era planejamento; em S3, os arquivos de configuração foram versionados | Desvio registrado no retrato histórico, não estado atual | Ação histórica T36; em S3, conferir execução da configuração já versionada |

## 7.3 Leitura do quadro

 O quadro registra a avaliação da Sprint 2 e suas ações para o ciclo seguinte. A promoção por hmg e a participação dos revisores, confirmadas no feedback, permanecem registradas. Os avanços posteriores de configuração são descritos abaixo, sem substituir o histórico.

 Os seis desvios comprovados se organizam em quatro grupos, e o agrupamento sugere tratamentos distintos. O primeiro é **forma da mensagem de commit**, com dois itens que têm a mesma causa e a mesma solução: são conhecidos, dependem de atenção manual e o hook da Seção 6.5 pode reduzir parte dos desvios formais. O segundo é **cadência**, um item que não se resolve por ferramenta e depende de mudança de comportamento, razão pela qual está tratado como ação verificável, com critério numérico. O terceiro é **encerramento de ciclo**, com dois itens (branches não excluídas e tag ausente) que compartilham a característica de serem etapas finais que podem ser esquecidas quando a entrega já parece pronta. A promoção por `hmg`, anteriormente classificada de forma incorreta como não executada, foi confirmada no histórico e não integra esse grupo. Para os desvios restantes, a providência mais eficaz é o checklist da Seção 8.

 A avaliação histórica da Sprint 2 registrava uma esteira ainda não implementada. Na Sprint 3, os arquivos de CI passaram a existir; os arquivos `.gitlab-ci.yml` e `gitlab-issue-kit/.gitlab-ci.yml` registram build, testes e qualidade. A execução de cada pipeline deve ser conferida no MR.

 Além do vínculo `Closes #N`, a cobertura de revisão exige registros primários de aprovações e comentários. A participação dos sete integrantes na Sprint 2 foi confirmada no feedback; no acompanhamento das próximas sprints, cada revisão deve continuar vinculada à aprovação ou ao comentário correspondente.

---

# 8. Checklist de Conformidade

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

**No encerramento de cada sprint**, além dos itens acima por Merge Request:

- [ ] Todas as branches de trabalho já mescladas foram excluídas do remoto.
- [ ] O Merge Request de `develop` para `hmg` foi aberto, revisado e mesclado.
- [ ] O Merge Request de `hmg` para `main` foi aberto por quem está na rotação, revisado e mesclado.
- [ ] A tag anotada da versão foi criada em `main` e enviada ao remoto.
- [ ] O histórico de lançamentos do `README.md` registra a versão e a data da entrega.
- [ ] A aferição de conformidade dos commits da sprint foi atualizada na Seção 5.3.
- [ ] O quadro de aderência da Seção 7.2 foi reconferido contra o repositório na data da entrega.
