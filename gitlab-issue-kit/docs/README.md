# gitlab-issue-kit

Cria issues no GitLab em lote, a partir de um CSV. Você descreve o backlog em
uma planilha, roda um comando, e os cards aparecem no board — com descrição
formatada, labels, tamanho, prioridade e milestone.

Portátil: copie a pasta para qualquer projeto, ajuste o `scripts/config.yml` e use.

---

## Estrutura

Copie a pasta inteira para onde precisar.

```
gitlab-issue-kit/
├── scripts/                    # tudo que executa
│   ├── create_issues.py        # CLI principal — cria as issues a partir do CSV
│   ├── setup_labels.py         # CLI — cria as labels do catálogo no projeto novo
│   ├── setup_mr_template.py    # CLI — gera o template de merge request
│   ├── relabel.py              # CLI — adiciona/remove labels em issues existentes
│   ├── gitlab_kit.py           # núcleo compartilhado (config, credenciais, HTTP)
│   └── config.yml              # ⬅ TODO comportamento de projeto mora aqui
├── csv/                        # os backlogs
│   ├── backlog_exemplo.csv     # CSV de exemplo, válido e pronto para rodar
│   └── backlog_<sprint>.csv    # um por sprint
├── docs/                       # documentação e templates de referência
│   ├── README.md
│   ├── PROMPT.md
│   └── .gitlab/                # templates de issue e MR (ver seção abaixo)
│       ├── issue_templates/Default.md
│       └── merge_request_templates/Default.md
└── outputs/                    # relatórios gerados pelas execuções
    └── issues_created.json
```

Rode sempre a partir da raiz do kit: `python scripts/create_issues.py ...`.

**`config.yml` mora em `scripts/` de propósito.** O `gitlab_kit.py` resolve o
config como `Path(__file__).parent / "config.yml"` — se o YAML sair de perto
dele, todo comando passa a exigir `--config` explícito.

O `.gitlab/` aqui é **material de referência do kit**. Para valer no seu
projeto, esses arquivos precisam estar em `.gitlab/` na **raiz do repositório** —
o GitLab só reconhece templates nesses caminhos exatos. O
`setup_mr_template.py` faz esse trabalho: detecta a raiz do repo pelo `.git` e
escreve o template lá.

`create_issues.py` e `setup_labels.py` são genéricos. Ao levar o kit para um
projeto novo, **edite só o `scripts/config.yml`**.

---

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env      # preencha GITLAB_URL, GITLAB_TOKEN, GITLAB_PROJECT_ID
```

O token é um Personal Access Token com escopo `api`
(GitLab → Preferences → Access Tokens). O `GITLAB_PROJECT_ID` é o número que
aparece em Settings → General do projeto.

Python 3.10+.

---

## Uso

```bash
# 1. Uma vez por projeto: cria as labels do catálogo
python scripts/setup_labels.py --dry-run
python scripts/setup_labels.py

# 2. A cada sprint: valida o CSV sem tocar no GitLab
python scripts/create_issues.py --csv csv/backlog_sprint1.csv --dry-run

# 3. Cria de verdade
python scripts/create_issues.py --csv csv/backlog_sprint1.csv
```

`--dry-run` não faz **nenhuma** chamada de rede — dá para validar o CSV antes
mesmo de ter um token configurado.

Ao final, um relatório com iid + URL de cada issue criada vai para
`outputs/issues_created.json` (use `--output-dir` para mudar).

---

## Formato do CSV

Cabeçalho:

```
title,description,objective,dependencies,tasks,dor,dod,labels,size,milestone,priority,kind
```

| Coluna | Obrigatório | Formato | Exemplo |
|---|---|---|---|
| `title` | ✅ | texto | `Implementar endpoint de autenticação` |
| `description` | ✅ | texto — vira o **Contexto** | `O app precisa de um endpoint...` |
| `objective` | ✅ | texto | `Permitir login seguro` |
| `dependencies` | ❌ | itens separados por `;` | `Nenhuma` ou `#12;#15` |
| `tasks` | ✅ | itens separados por `;` | `Criar rota;Validar payload` |
| `dor` | ✅ | itens separados por `;` | `Modelo definido;.env pronto` |
| `dod` | ✅ | itens separados por `;` | `Testes passando;Review ok` |
| `labels` | ✅ | separados por `,` (aspas no CSV) | `"BACKEND,TEST"` |
| `size` | ✅ | `PP` `P` `M` `G` | `M` |
| `milestone` | ✅ | nome exato da milestone | `Sprint 01` |
| `priority` | ❌ | `Alta` `Média` `Baixa` | `Alta` |
| `kind` | ❌ | `FEATURE` `BUG FIX` `DOCUMENTATION` | `BUG FIX` |

Veja `csv/backlog_exemplo.csv` para um CSV completo e válido.

**Cuidado com vírgulas:** qualquer campo que contenha `,` precisa estar entre
aspas duplas — inclusive a coluna `labels` quando tem mais de uma label.

---

## O que o script faz sozinho

1. **Valida o lote inteiro antes de criar qualquer coisa** — size inválido ou
   kind fora da lista aborta a execução com zero issues criadas. Títulos
   duplicados, tasks vazias e milestone ausente viram avisos.
2. **Resolve a milestone** pelo nome — e cria se não existir
   (`api.create_missing_milestone` no config).
3. **Cria as labels faltantes** sob demanda, com a cor do catálogo.
4. **Monta a descrição** a partir do template do `scripts/config.yml`, com as listas
   de tasks/DoR/DoD viradas em checkboxes markdown.
5. **Aplica labels automáticas** além das que vieram do CSV:
   - tamanho: `SIZE_PP` / `SIZE_P` / `SIZE_M` / `SIZE_G`
   - prioridade: só as configuradas em `priority_labels` (por padrão, apenas
     `Alta` → `PRIORIDADE ALTA`; média e baixa não recebem label)
   - tipo de trabalho: `FEATURE` / `BUG FIX` / `DOCUMENTATION`, do campo `kind`
     ou inferido da label de camada
6. **Salva o relatório JSON** com iid, URL, labels e milestone de cada issue.

---

## Templates de issue e merge request

Para as issues criadas **à mão**, direto na interface do GitLab — o script cobre
só as que vêm do CSV.

Copie a pasta `.gitlab/` para a **raiz do repositório** e faça commit:

```bash
cp -r gitlab-issue-kit/.gitlab .          # a partir da raiz do repo
git add .gitlab && git commit -m "chore: adicionar templates de issue e MR"
```

O GitLab lê esses arquivos do branch padrão. Só funciona nesses caminhos exatos:

| Arquivo | Efeito |
|---|---|
| `.gitlab/issue_templates/Default.md` | aplicado automaticamente ao abrir uma issue nova |
| `.gitlab/merge_request_templates/Default.md` | aplicado automaticamente ao abrir um MR novo |

O nome `Default.md` é o que faz o GitLab **pré-preencher** o campo sem o usuário
precisar escolher nada no dropdown. Renomeando (ex.: `Bug.md`), o template passa
a ser opcional e some do preenchimento automático — dá para ter vários: o
`Default.md` como padrão e outros como alternativa.

**Mantenha o template de issue em sincronia com o `scripts/config.yml`.** O
`.gitlab/issue_templates/Default.md` é a versão manual do que o
`description.template` gera automaticamente — a ideia é que issue criada pelo
script e issue criada à mão fiquem indistinguíveis no board. Se você mexer nas
seções de um, mexa no outro. O mesmo vale para a lista de labels no rodapé do
template: ela precisa refletir o catálogo `labels:` do `scripts/config.yml`.

---

## Adaptando para um projeto novo

Tudo no `scripts/config.yml`, que é comentado seção por seção:

| Quero mudar... | Edite |
|---|---|
| Quais labels existem e suas cores | `labels:` |
| Tamanhos aceitos e o que cada um significa | `sizes:` |
| Prefixo da label de tamanho (`SIZE_` → `size::`) | `size_label_prefix:` |
| Quais prioridades geram label | `priority_labels:` |
| Tipos de trabalho aceitos e a inferência automática | `kind:` |
| O formato do corpo da issue | `description.template:` |
| Separadores do CSV | `csv:` |
| Velocidade / timeout / criação de milestone | `api:` |

O `description.template` aceita os placeholders `{title}`, `{objective}`,
`{context}`, `{dependencies}`, `{tasks}`, `{dor}`, `{dod}`, `{size}`,
`{size_description}`, `{milestone}`, `{priority}` e `{kind}`. Chaves literais
`{ }` precisam ser duplicadas: `{{ }}`.

Dá para manter vários configs e escolher na hora:

```bash
python scripts/create_issues.py --csv csv/backlog.csv --config scripts/configs/cliente-x.yml
```

---

## Notas

- O kit não edita nem apaga issues — só cria. Rodar duas vezes o mesmo CSV
  gera issues duplicadas; use `--dry-run` antes.
- Falhas são isoladas por issue: um erro em uma linha não interrompe o resto,
  e o resumo final lista tudo que falhou.
- Há uma pausa de 0.4s entre chamadas de escrita para não bater no rate-limit
  do GitLab. Um backlog de 60 issues leva ~1 minuto.
- O exit code é `0` se tudo passou e `1` se houve qualquer falha — dá para
  encadear em CI.
