# Execução dos testes de integração — commit `6a757e2`

Registro da execução das suítes da Seção 6.4 do `docs/Projeto.md`.
Data da execução: 21/09/2026. Ambiente: Python 3.12, Linux, sem Docker ativo.

## Comando

```bash
python -m unittest discover -s tests -p "test_integracao_*.py" -v
```

## Resultado consolidado

| Métrica | Valor |
|---|---|
| Testes executados | 155 |
| Aprovados | 115 |
| Pulados por infraestrutura ausente | 40 |
| Falhas | 0 |
| Erros | 0 |
| Tempo | ~11,5 s |

**Pular não é aprovar.** Os 40 pulados dependem de MinIO e PostgreSQL de teste,
que não estavam no ar nesta execução. Cada um declara no próprio motivo o que
falta e como subir. A contagem de aprovados vale apenas para as fronteiras que
foram efetivamente atravessadas.

## Por suíte

| Suíte | Casos | Executados | Pulados | Fronteira real atravessada |
|---|---|---|---|---|
| `test_integracao_audio_minio` | TI-01 a TI-05, TI-62 | 7 | 7 | MinIO (ausente nesta execução) |
| `test_integracao_transcricao` | TI-06 a TI-10 | 5 | 0 | Deepgram, por fita real |
| `test_integracao_sintese_fala` | TI-11 a TI-15 | 6 | 0 | Gemini TTS, por fita real |
| `test_integracao_analise_pln` | TI-16 a TI-19 | 4 | 0 | Deepgram + `.joblib` do disco |
| `test_integracao_chat` | TI-20 a TI-23 | 6 | 0 | Gemini chat, por fita real |
| `test_integracao_persistencia` | TI-24 a TI-29, TI-53, TI-54, TI-65 | 15 | 14 | PostgreSQL (ausente nesta execução) |
| `test_integracao_frontend_backend` | TI-30 a TI-34 | 8 | 0 | contrato HTTP e arquivos de configuração |
| `test_integracao_rag` | TI-55 a TI-58 | 13 | 1 | parsers e chunker reais; `vecs` sob opt-in |
| `test_integracao_seguranca` | TI-63, TI-64 | 9 | 0 | pilha de autenticação real |
| `test_integracao_vhs_provedores` | TI-59 a TI-61 | 10 | 0 | fitas reais dos dois SDKs, sem rede |
| `test_integracao_vhs` | TI-47 a TI-52 | 10 | 0 | servidor HTTP sintético (Sprint 4) |
| `test_integracao_contrato_webhook` | TI-35 a TI-40, TI-41/TI-42 de lote | 8 | 0 | dublê em memória (Sprint 4) |
| `test_integracao_contrato_mensageria` | TI-41 a TI-46 | 7 | 0 | intermediário em memória |
| `test_integracao_webhook` | TI-35 a TI-42 | 19 | 0 | adaptador Microsoft Graph (Sprint 4) |
| `test_integracao_webhook_drive` | TI-35 a TI-42 | 10 | 0 | adaptador Google Drive (Sprint 4) |
| `test_integracao_webhook_postgres` | TI-35 a TI-42 | 18 | 18 | PostgreSQL (ausente nesta execução) |

## Arquivos

- `descoberta-integracao.log` — saída verbosa da descoberta completa.
- `<suíte>.log` — saída verbosa de cada suíte isolada.
- `vhs-replay-offline.log` — replay das seis fitas com a rede bloqueada,
  em processo separado (`scripts/gravar_fitas_vhs.py --conferir`), com
  `play_count` e origem de cada gravação.

## Para incluir as suítes puladas

```bash
docker compose up -d minio minio-init postgres
export TEST_AUDIO_STORAGE_ENDPOINT_URL=http://127.0.0.1:9000
export TEST_DATABASE_URL=postgresql://az1:az1@127.0.0.1:5432/az1_teste
psql "$TEST_DATABASE_URL" -f src/database/01_create_database.sql
psql "$TEST_DATABASE_URL" -f src/database/02_initial_data.sql
psql "$TEST_DATABASE_URL" -f src/database/03_rls_policies.sql
python -m unittest discover -s tests -p "test_integracao_*.py" -v
```

TI-55 gasta chamadas reais de embedding e exige opt-in adicional:
`export TEST_RAG_DB_URL=$TEST_DATABASE_URL`.
