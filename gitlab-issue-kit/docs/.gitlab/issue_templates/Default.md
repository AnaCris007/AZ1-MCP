<!--
Template de issue criada à mão. Espelha exatamente o corpo que o
create_issues.py gera a partir do CSV (config.yml → description.template).

Se você mudar o template do config.yml, mude este arquivo junto — a ideia é que
issue criada pelo script e issue criada à mão fiquem indistinguíveis no board.

Mantenha os cabeçalhos em **negrito inline**, não em `##`: alguns baremas
validam pelo nome exato da seção.
-->

**Objetivo da tarefa:** <!-- 1–2 linhas, verbo no infinitivo: "Implementar X", "Documentar Y". -->

**Contexto:** <!-- Por que estamos fazendo isso? Qual problema ou decisão motiva esta tarefa? -->

**Dependências:**
<!-- Issues ou componentes que precisam estar prontos antes desta.
     Nomeie a issue (#42), não escreva só "Nenhuma" por preguiça. -->
- Nenhuma

**Tasks:**
<!-- Subtarefas para concluir. Prefira granularidade fina — se passar de 120 min, quebre a issue. -->
- [ ]
- [ ]
- [ ]

**DoR (Definition of Ready):**
<!-- Específico desta issue, não genérico. O que precisa existir para começar? -->
- [ ] Design / requisitos aprovados
- [ ] Dependências mapeadas
- [ ] Contrato de API definido (se aplicável)
- [ ] Ambiente de desenvolvimento configurado

**DoD (Definition of Done):**
<!-- Específico desta issue. Como sabemos que acabou? -->
- [ ] Implementado
- [ ] Testes unitários passando
- [ ] MR aprovado por 1 revisor
- [ ] Documentação atualizada (se aplicável)

<!--
ANTES DE CRIAR — checklist de labels (precisa bater com o config.yml do kit):
- Título no INFINITIVO ("Implementar", "Documentar", "Corrigir").
- 1 label de CAMADA: BACKEND | FRONTEND | DATABASE | DOCS | INFRA | TEST | RESEARCH | DEVOPS
- 1 label de TIPO: FEATURE | BUG FIX | DOCUMENTATION
- 1 label de TAMANHO: SIZE_PP (≤15 min) | SIZE_P (≤30 min) | SIZE_M (30–60 min) | SIZE_G (60–120 min)
- Se prioridade alta, aplicar PRIORIDADE ALTA (média e baixa não recebem label).
- Atribuir 1 responsável (assignee).
- Definir a milestone da sprint.
-->
