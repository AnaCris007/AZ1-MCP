# Execução dos testes não funcionais

Este diretório preserva as evidências técnicas da campanha dos RNFs. O
planejamento e os critérios oficiais permanecem na Seção 6.3 de
`docs/Projeto.md`; esta pasta registra o que foi efetivamente executado, sem
converter bloqueios ou reprovações em aprovações.

## Versões avaliadas

- Campanha principal: commit `0a61b353829dee491537bb2863facbe589d48cc8`.
- RNF06: commit `6b3eb96b9e0d1c6269156808468d56450d96deae`, anterior à
  campanha principal. O resultado não é apresentado como evidência da versão
  posterior.
- RNF08: sessões externas documentadas diretamente na Seção 6.9 de
  `docs/Projeto.md`.

## Resultado consolidado

| Requisito | Casos | Resultado | Evidência principal |
|---|---|---|---|
| RNF01 | CT-RNF01-P/N | Reprovado | `0a61b353/rnf01/relatorio.md` |
| RNF02 | CT-RNF02-P/N | Aprovado | `0a61b353/rnf02/relatorio.md` |
| RNF03 | CT-RNF03-P/N | Reprovado | `0a61b353/rnf03/relatorio.md` |
| RNF04 | CT-RNF04-P/N | Reprovado | `0a61b353/rnf04/relatorio.md` |
| RNF05 | CT-RNF05-P/N | Aprovado | `0a61b353/rnf05/relatorio.md` |
| RNF06 | CT-RNF06-P/N | Aprovado no commit `6b3eb96` | `6b3eb96/rnf06/relatorio.md` |
| RNF07 | CT-RNF07-P/N | Reprovado | `0a61b353/rnf07/relatorio.md` |
| RNF08 | CT-RNF08-P/N | Aprovado | Seção 6.9 de `docs/Projeto.md` |
| RNF09 | CT-RNF09-P/N | Reprovado | `0a61b353/rnf09/relatorio.md` |
| RNF10 | CT-RNF10-C-P/N e CT-RNF10-M-P/N | Aprovado | `0a61b353/rnf10/relatorio.md` |
| RNF11 | CT-RNF11-P/N | Bloqueado | `0a61b353/rnf11/relatorio.md` |
| RNF12 | CT-RNF12-P/N | Reprovado | `0a61b353/rnf12/relatorio.md` |

Resultado agregado: cinco requisitos aprovados, seis reprovados e um
bloqueado. A aprovação do RNF06 pertence à versão indicada na tabela.

## Scripts e reprodução

| RNF | Executor principal | Dependências ou observações |
|---|---|---|
| RNF01 | `scripts/executar_rnf01.py` | Usa `scripts/rnf01_servidor.py` e uma API controlada |
| RNF02 | `scripts/executar_rnf02.py` | FastAPI TestClient e chaves ES256 efêmeras |
| RNF03 | `scripts/executar_rnf03.py` | CSV cego, modelo congelado e scikit-learn |
| RNF04 | `scripts/executar_rnf04.py` | PostgreSQL dedicado, HTTP e WebSocket |
| RNF05 | `scripts/executar_rnf05.py` | Cliente Python, cliente React/Vitest e servidor controlado |
| RNF06 | `scripts/executar_rnf06.py` | API/Deepgram e áudios reais mantidos fora do Git |
| RNF07 | `scripts/executar_rnf07.py` | Monitor HTTP em segundo plano e cenários controlados em processo |
| RNF08 | roteiro da Seção 6.9 | Sessões externas; não possui executor automatizado |
| RNF09 | `scripts/executar_rnf09.py` | PostgreSQL dedicado e FastAPI TestClient |
| RNF10 | `scripts/executar_rnf10_carga.py` e `scripts/executar_rnf10_memoria.py` | Servidores e trabalhadores auxiliares do mesmo diretório |
| RNF11 | não aplicável nesta versão | Bloqueado pela ausência do fluxo de sugestões do RF04 |
| RNF12 | `scripts/executar_rnf12.py` | Massa gerada por `scripts/gerar_massa_rnf12.mjs`; índice RAG e configuração do ambiente |

Cada executor mantém o resultado bruto em JSON/CSV e um relatório legível em
Markdown. Os comandos que usam banco devem receber uma base exclusiva de teste;
endereços, tokens e credenciais não são evidências e não devem ser versionados.

## Política das evidências

- Arquivos `resultado.json`, matrizes CSV, logs sanitizados e relatórios são
  preservados porque permitem auditar os cálculos e os problemas encontrados.
- Gravações de voz dos participantes não são versionadas. O RNF06 preserva as
  referências, transcrições, contagens de erro e resultados derivados.
- Modelos temporários do RNF10 não são versionados; o manifesto e as medições
  permitem reproduzi-los pelos scripts.
- Planilhas e pré-visualizações em `outputs/` são produtos de trabalho
  ignorados. A evidência final necessária foi resumida em formatos textuais na
  campanha.
