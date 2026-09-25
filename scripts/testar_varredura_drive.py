#!/usr/bin/env python3
"""Smoke-test da varredura do Drive, SEM túnel e SEM RabbitMQ.

Prova, contra o Drive REAL, as duas peças novas isoladas do resto: autenticação +
`changes.list` + download (o cliente), e opcionalmente o pipeline de indexação.

Uso:
    # 1) só listar o que mudou desde um ponto e mostrar o que baixaria:
    python scripts/testar_varredura_drive.py

    # 2) baixar E indexar de verdade no pgvector (exige GEMINI_API_KEY):
    python scripts/testar_varredura_drive.py --indexar

Pré-requisitos no .env:
    GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET  — credencial OAuth "Desktop app"
    GOOGLE_WEBHOOK_CHANNEL_TOKEN            — qualquer segredo (só p/ montar Config)
    WEBHOOK_PUBLIC_URL                      — pode ser https://example.com aqui
                                             (não abrimos canal, só satisfaz o Config)
    SUPABASE_DB_URL                         — para --indexar gravar no pgvector
    GEMINI_API_KEY                          — para --indexar vetorizar

Na primeira execução o navegador abre para autorizar (grava .google_token.json).
Depois, edite/adicione um arquivo .docx ou .xlsx no Drive e rode de novo.
"""

from __future__ import annotations

import sys
from pathlib import Path

_SRC = Path(__file__).parent.parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from dotenv import load_dotenv  # noqa: E402

load_dotenv()

from services.drive_channel_service import DRIVE, Config, obter_token  # noqa: E402
from services.drive_download_service import DriveClient  # noqa: E402
from services.webhook_http import pedir as _pedir  # noqa: E402


def main() -> int:
    indexar = "--indexar" in sys.argv

    config = Config.from_environment()
    token = obter_token(config)  # abre o navegador na 1ª vez; grava .google_token.json
    cliente = DriveClient(config, token)

    # Ponto de partida do feed. Aqui pegamos um token "de agora"; num sistema real
    # ele viria de integracao.conexao.delta_token. Então: rode uma vez para fixar
    # o ponto, edite um arquivo no Drive, e rode de novo para ver a mudança.
    inicio = _pedir(f"{DRIVE}/changes/startPageToken", token=token)["startPageToken"]
    print(f"Ponto de partida do feed (startPageToken): {inicio}")

    marcador = Path(".drive_smoketest_token")
    if marcador.exists():
        anterior = marcador.read_text().strip()
        print(f"Usando o ponto salvo da execução anterior: {anterior}\n")
        ponto = anterior
    else:
        marcador.write_text(inicio)
        print(
            "\nPrimeira execução: ponto salvo em .drive_smoketest_token.\n"
            "Agora edite ou adicione um .docx/.xlsx no Drive e rode este script de novo.\n"
        )
        return 0

    mudancas, novo_token = cliente.listar_mudancas(ponto)
    print(f"{len(mudancas)} mudança(s) desde o último ponto:\n")

    for m in mudancas:
        arq = m.get("file") or {}
        estado = "REMOVIDO" if m.get("removed") or arq.get("trashed") else "ativo"
        print(f"  - {arq.get('name', m.get('fileId'))}  [{arq.get('mimeType','?')}]  ({estado})")

    if indexar:
        print("\n--indexar: baixando e reindexando no pgvector...\n")
        from mensageria.varredura_indexacao import VarreduraComIndexacao
        from services.database_service import PostgresSettings, abrir_pool

        pool = abrir_pool(PostgresSettings.from_environment())

        # Reusa a lógica real de processar cada mudança (download + extrair +
        # vetorizar + indexar), sem precisar da fila.
        varredura = VarreduraComIndexacao(pool, drive_factory=lambda: cliente)
        indexados = sum(varredura._processar_mudanca(cliente, m) for m in mudancas)
        print(f"\n{indexados} arquivo(s) indexado(s) no pgvector.")

    if novo_token:
        marcador.write_text(novo_token)
        print(f"\nPonto de retomada avançado para: {novo_token}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
