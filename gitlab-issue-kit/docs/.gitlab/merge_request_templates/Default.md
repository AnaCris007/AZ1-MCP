<!--
Template de merge request.

Mantenha a estrutura "Closes #N / O que foi feito / Como testar / Checklist" —
alguns baremas validam pelos nomes exatos das seções.
-->

Closes #<!-- número da issue que este MR resolve -->

## O que foi feito

<!-- Bullets curtos e objetivos. Foque no "o quê" e no "porquê" —
     o "como" o reviewer vê no diff. -->

-
-

## Como testar

<!-- Passo-a-passo para o reviewer reproduzir. Inclua o resultado esperado. -->

1.
2.
3. **Resultado esperado:**

## Checklist

- [ ] Testes unitários escritos e passando localmente
- [ ] Sem warnings ou erros no linter
- [ ] Documentação atualizada (se aplicável)
- [ ] Variáveis de ambiente novas adicionadas ao `.env.example` (se aplicável)
- [ ] Migrations executadas e testadas (se aplicável)
- [ ] Branch parte de `develop` (ou `main` para `hotfix/`)
- [ ] Code review solicitado a pelo menos 1 membro do time

<!--
ANTES DE ABRIR:
- Título DESCRITIVO com 3+ palavras (sem "WIP:" ou "Draft:").
- Substituir "Closes #" pelo número real da issue.
- Aplicar a mesma label de TIPO da issue: FEATURE | BUG FIX | DOCUMENTATION
- Definir a mesma milestone da issue.
- Atribuir reviewer ANTES de marcar como pronto.
- Reviewer deve deixar pelo menos 1 comentário substantivo.
-->
