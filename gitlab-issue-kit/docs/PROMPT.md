# Prompt de contexto — gitlab-issue-kit

Cole o bloco abaixo no início de uma sessão nova do Claude Code, junto com os
artefatos da sprint. Ele explica o kit, a divisão de trabalho e o contrato do CSV.

---

## 📋 Prompt (copiar daqui pra baixo)

Estou usando o **gitlab-issue-kit**, um kit de automação que cria issues no GitLab
em lote a partir de um CSV. Ele vive em `C:\Users\Inteli\Documents\gitlab-issue-kit\`
(WSL: `/mnt/c/Users/Inteli/Documents/gitlab-issue-kit/`), **fora de qualquer repo**,
porque é reaproveitado entre projetos.

### Divisão de trabalho — siga sem perguntar

1. **Eu mando os artefatos** (docs de planejamento, escopo da sprint, backlog bruto).
2. **Você gera o CSV.** Esse é o seu trabalho, não o meu. Salve como
   `backlog_<sprint>.csv` e me avise quando terminar.
3. **Eu rodo o script.** Nunca você. Ações que escrevem em sistema externo são minhas.
   Também não rode `git add` nem `git commit` — sugira a mensagem, eu executo.

Você **não edita os `.py`**. Todo comportamento específico de projeto (labels, cores,
tamanhos, prioridades, template da descrição) mora no `scripts/config.yml`. Se algo precisa
mudar, muda o YAML.

### Como o script funciona

```
config.yml  ─┐
             ├─→ create_issues.py ─→ API v4 do GitLab ─→ outputs/issues_created.json
backlog.csv ─┘
```

- `gitlab_kit.py` — núcleo compartilhado: carrega o `scripts/config.yml`, lê as credenciais
  (`GITLAB_URL`, `GITLAB_TOKEN`, `GITLAB_PROJECT_ID` do `.env`) e envolve o cliente HTTP.
- `setup_labels.py` — roda **uma vez por projeto**, cria o catálogo de labels. Idempotente.
- `create_issues.py` — roda **a cada sprint**, lê o CSV e cria as issues.

Ordem de execução (minha, não sua):

```bash
python scripts/setup_labels.py --dry-run && python scripts/setup_labels.py     # 1x por projeto
python scripts/create_issues.py --csv csv/backlog_sprint5.csv --dry-run    # valida sem rede
python scripts/create_issues.py --csv csv/backlog_sprint5.csv              # cria de verdade
```

O `--dry-run` **não faz nenhuma chamada de rede** — nem GET. Valida o CSV inteiro
sem token configurado.

Fluxo interno do `create_issues.py`, na ordem:

1. Carrega `scripts/config.yml` e as credenciais (dispensadas em dry-run).
2. Lê o CSV (`utf-8-sig`) e ignora linhas com `title` vazio.
3. **Valida o lote inteiro antes de criar qualquer coisa.** Se houver erro, aborta
   com **zero** issues criadas — evita o pior cenário, metade do backlog no board e
   o resto travado num CSV mal formado.
4. Por issue: garante as labels → resolve a milestone pelo nome (cria se não existir)
   → monta a descrição pelo template → `POST /issues`.
5. Falha em uma linha **não** interrompe o resto; o resumo final lista o que falhou.
6. Salva `outputs/issues_created.json` com iid, URL, labels e milestone de cada issue.

### Contrato do CSV — é isso que você precisa acertar

Cabeçalho exato:

```
title,description,objective,dependencies,tasks,dor,dod,labels,size,milestone,priority,kind
```

| Coluna | Obrigatória | Formato |
|---|---|---|
| `title` | ✅ | texto — **sempre no infinitivo** |
| `description` | ✅ | texto corrido — vira o **Contexto** da issue |
| `objective` | ✅ | uma frase: o porquê da tarefa |
| `dependencies` | ❌ | itens separados por `;` — `#12;#15` ou `Nenhuma` |
| `tasks` | ✅ | itens separados por `;` → viram checkboxes |
| `dor` | ✅ | itens separados por `;` → viram checkboxes |
| `dod` | ✅ | itens separados por `;` → viram checkboxes |
| `labels` | ✅ | separadas por `,` → **campo entre aspas duplas** |
| `size` | ✅ | `PP` \| `P` \| `M` \| `G` |
| `milestone` | ✅ | nome exato, ex.: `Sprint 5` |
| `priority` | ❌ | `Alta` \| `Média` \| `Baixa` |
| `kind` | ❌ | `FEATURE` \| `BUG FIX` \| `DOCUMENTATION` |

Separadores: `;` **dentro** de listas (tasks/dor/dod/dependencies), `,` entre labels.

### O que o script já faz sozinho — não duplique no CSV

- **Label de tamanho:** derivada de `size` (`M` → `SIZE_M`). Nunca escreva `SIZE_*`
  na coluna `labels`.
- **Label de prioridade:** só `Alta`/`high` geram `PRIORIDADE ALTA`. Média e baixa
  **não recebem label** — mas ainda assim preencha a coluna.
- **Label de tipo de trabalho:** vem de `kind`; se vazio, é inferida da label de
  camada (`DOCS`/`RESEARCH` → `DOCUMENTATION`, o resto → `FEATURE`). Só preencha
  `kind` explicitamente quando a inferência erraria — tipicamente `BUG FIX`.
- **Formatação da descrição:** o template do `scripts/config.yml` monta as seções
  (Objetivo / Contexto / Dependências / Tasks / DoR / DoD). Mande **texto puro** nas
  colunas — sem markdown de seção, sem `- [ ]`, sem `\n`.
- **Labels e milestone faltando:** criadas sob demanda, com a cor do catálogo.

Na coluna `labels`, portanto, entra **só a camada**:
`BACKEND`, `FRONTEND`, `DATABASE`, `DOCS`, `INFRA`, `TEST`, `RESEARCH`, `DEVOPS`.

### Validação — o que aborta e o que só avisa

**Aborta o lote inteiro:**
- coluna obrigatória faltando no cabeçalho
- `size` fora de `PP`/`P`/`M`/`G`
- `kind` preenchido com valor fora de `FEATURE`/`BUG FIX`/`DOCUMENTATION`
- `description.template` do config com placeholder inválido

**Só avisa (a issue é criada):** título duplicado, sem tasks, sem milestone.

### Regras de conteúdo do projeto G03

- Título **no infinitivo**, 100% das issues.
- Toda issue precisa de label de **camada** + **tamanho** + **tipo de trabalho**
  (tipo faltando foi o erro mais crítico da Sprint 3).
- **Mínimo 8 issues por membro** — grupo de 7 → **56+ issues** por sprint. Confira a
  contagem total no fim e me diga o número.
- **Misture tamanhos**: prefira quebrar `G` em `M`/`P`. `PP` = até 15min, `P` = 30min,
  `M` = 30–60min, `G` = 60–120min.
- **DoR e DoD específicos**, nunca genéricos — nada de "código pronto".
- **Dependências nomeadas** (issue ou entregável concreto), não só "Nenhuma" por padrão.

### Armadilhas

- Todo campo que contenha `,` **precisa** de aspas duplas — inclusive `labels` com
  mais de uma label. É o erro nº 1.
- O kit **só cria**, nunca edita nem apaga. Rodar o mesmo CSV duas vezes gera issues
  duplicadas — por isso o `--dry-run` primeiro é obrigatório.
- Há 0,4s de pausa entre escritas por causa do rate-limit: 60 issues ≈ 1 minuto.
- Exit code `0` = tudo passou, `1` = alguma falha.

Antes de gerar o CSV, leia `scripts/config.yml` para conferir o catálogo de labels e os
tamanhos vigentes — eles mudam de projeto para projeto. Use `csv/backlog_exemplo.csv`
como referência de formatação.
