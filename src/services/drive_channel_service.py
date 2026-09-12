"""Abertura, renovação e fechamento do canal de notificações do Google Drive.

Executável:

    python -m services.drive_channel_service abrir
    python -m services.drive_channel_service renovar
    python -m services.drive_channel_service fechar
    python -m services.drive_channel_service listar

O canal é a origem observada: enquanto ele existe, o Drive chama a nossa rota a
cada mudança no acervo da conta. Ele vale no máximo sete dias (`changes.watch`),
e a URL de notificação não pode ser alterada depois de criado — então reiniciar o
túnel, que troca a URL, exige abrir um canal novo.

Usa apenas a biblioteca padrão para falar OAuth e HTTP. É deliberado: as
bibliotecas oficiais do Google resolveriam isto em menos linhas, mas trariam uma
árvore de dependências grande para uma ferramenta operacional que roda algumas
vezes por semana, fora do caminho de execução da API.
"""

from __future__ import annotations

import argparse
import json
import os
import secrets
import sys
import urllib.parse
import uuid
import webbrowser
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any

import psycopg
from dotenv import load_dotenv

from services.webhook_http import ErroDeOperacao, ErroHTTP
from services.webhook_http import pedir as _pedir
from services.webhook_registry_service import PostgresSettings

AUTORIZACAO = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN = "https://oauth2.googleapis.com/token"
DRIVE = "https://www.googleapis.com/drive/v3"

# `drive.readonly` é o menor escopo que permite ler o feed de mudanças e, depois,
# baixar o conteúdo para vetorizar. `drive.metadata.readonly` bastaria para o
# webhook, mas não para a etapa seguinte, e trocar o escopo obriga o usuário a
# consentir de novo — então já se pede o que a Sprint 5 vai precisar.
ESCOPO = "https://www.googleapis.com/auth/drive.readonly"

load_dotenv()

PROVEDOR = "google_drive"
CREDENCIAIS = Path(".google_token.json")

# Sete dias é o teto do `changes.watch`. Um minuto a menos porque o Google recusa
# valores no limite exato quando o relógio local está ligeiramente adiantado.
VALIDADE = timedelta(days=7) - timedelta(minutes=1)


@dataclass(frozen=True)
class Config:
    client_id: str
    client_secret: str
    channel_token: str
    url_publica: str
    dsn: str

    @classmethod
    def from_environment(cls) -> Config:
        faltando = [
            nome
            for nome in (
                "GOOGLE_CLIENT_ID",
                "GOOGLE_CLIENT_SECRET",
                "GOOGLE_WEBHOOK_CHANNEL_TOKEN",
                "WEBHOOK_PUBLIC_URL",
            )
            if not os.environ.get(nome)
        ]
        if faltando:
            raise ErroDeOperacao(f"Variáveis ausentes no .env: {', '.join(faltando)}")

        url = os.environ["WEBHOOK_PUBLIC_URL"].rstrip("/")
        if not url.startswith("https://"):
            # O Google recusa canal com endereço que não seja HTTPS, e a mensagem
            # de erro dele não diz isso com clareza.
            raise ErroDeOperacao(f"WEBHOOK_PUBLIC_URL precisa começar com https://, e está como {url!r}")

        return cls(
            client_id=os.environ["GOOGLE_CLIENT_ID"],
            client_secret=os.environ["GOOGLE_CLIENT_SECRET"],
            channel_token=os.environ["GOOGLE_WEBHOOK_CHANNEL_TOKEN"],
            url_publica=url,
            dsn=PostgresSettings.from_environment().dsn,
        )


# ---------------------------------------------------------------------------
# OAuth: fluxo de loopback para aplicativo de desktop
# ---------------------------------------------------------------------------


class _Captura(BaseHTTPRequestHandler):
    codigo: str | None = None
    estado: str | None = None

    def do_GET(self) -> None:  # noqa: N802 — nome exigido por BaseHTTPRequestHandler
        parametros = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        _Captura.codigo = parametros.get("code", [None])[0]
        _Captura.estado = parametros.get("state", [None])[0]

        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(b"<h1>Autorizado.</h1><p>Pode fechar esta aba.</p>")

    def log_message(self, *args: Any) -> None:
        """Silencia o log do servidor, que polui a saída do comando."""


def _autorizar(config: Config) -> dict[str, Any]:
    servidor = HTTPServer(("127.0.0.1", 0), _Captura)
    porta = servidor.server_address[1]
    redirect_uri = f"http://127.0.0.1:{porta}"

    # `state` protege contra uma resposta forjada chegar ao servidor local.
    estado = secrets.token_urlsafe(16)
    parametros = {
        "client_id": config.client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": ESCOPO,
        # Sem estes dois o Google devolve só o access_token, que vale uma hora, e
        # não o refresh_token — e aí o canal não sobrevive a um reinício.
        "access_type": "offline",
        "prompt": "consent",
        "state": estado,
    }
    url = f"{AUTORIZACAO}?{urllib.parse.urlencode(parametros)}"

    print("Abrindo o navegador para autorizar. Se não abrir, use este endereço:\n")
    print(f"  {url}\n")
    webbrowser.open(url)

    servidor.handle_request()
    servidor.server_close()

    if not _Captura.codigo:
        raise ErroDeOperacao("O navegador não devolveu o código de autorização.")
    if _Captura.estado != estado:
        raise ErroDeOperacao("O `state` devolvido não confere. Autorização descartada.")

    return _pedir(
        TOKEN,
        metodo="POST",
        formulario=True,
        dados={
            "code": _Captura.codigo,
            "client_id": config.client_id,
            "client_secret": config.client_secret,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
        },
    )


def _renovar(config: Config, refresh_token: str) -> dict[str, Any]:
    return _pedir(
        TOKEN,
        metodo="POST",
        formulario=True,
        dados={
            "refresh_token": refresh_token,
            "client_id": config.client_id,
            "client_secret": config.client_secret,
            "grant_type": "refresh_token",
        },
    )


def obter_token(config: Config) -> str:
    """Devolve um access token válido, reaproveitando o refresh token gravado."""
    if CREDENCIAIS.exists():
        guardado = json.loads(CREDENCIAIS.read_text())
        try:
            novo = _renovar(config, guardado["refresh_token"])
            # A resposta do refresh não repete o refresh_token; preserva-se o antigo.
            guardado["access_token"] = novo["access_token"]
            CREDENCIAIS.write_text(json.dumps(guardado, indent=2))
            return novo["access_token"]
        except (ErroHTTP, ErroDeOperacao, KeyError):
            print("Refresh token inválido ou revogado. Autorizando de novo.\n", file=sys.stderr)

    credenciais = _autorizar(config)
    CREDENCIAIS.write_text(json.dumps(credenciais, indent=2))
    CREDENCIAIS.chmod(0o600)
    return credenciais["access_token"]


# ---------------------------------------------------------------------------
# Comandos
# ---------------------------------------------------------------------------


def abrir(config: Config, *, retomar_de: str | None = None) -> None:
    token = obter_token(config)

    # O ponto de partida do feed. Guardado junto com o canal para que a varredura
    # da Sprint 5 saiba de onde continuar em vez de reprocessar o acervo inteiro.
    # Numa renovação o ponto anterior é reaproveitado: pedir um novo descartaria
    # silenciosamente o que mudou entre o fechamento e a abertura.
    inicio = retomar_de or _pedir(f"{DRIVE}/changes/startPageToken", token=token)["startPageToken"]

    canal_id = str(uuid.uuid4())
    expira_em = datetime.now(UTC) + VALIDADE

    # Grava a origem ANTES de pedir o canal ao Google, e não depois. A
    # documentação do Drive registra que o `sync` de abertura pode chegar antes
    # mesmo de a resposta deste POST voltar para nós; se a linha só existisse
    # depois da resposta, essa entrega encontraria `VerificadorCanalAtivo` sem
    # nada para confrontar e seria recusada com 401 — um canal genuinamente
    # recém-criado sendo rejeitado pelo próprio receptor que o criou. `canal_id`
    # já é conhecido neste ponto porque o UUID é gerado por nós, não pelo Google;
    # só `recurso_id` (que o Google atribui) fica pendente até a resposta.
    with psycopg.connect(config.dsn) as conexao:
        reservada = conexao.execute(
            """
            INSERT INTO integracao.conexao
                (provedor, conta, recurso, client_state, subscription_id, recurso_id,
                 expira_em, delta_token, ativa)
            VALUES (%s, %s, %s, %s, %s, NULL, %s, %s, TRUE)
            ON CONFLICT (provedor, conta, recurso) DO UPDATE
               SET client_state = EXCLUDED.client_state,
                   subscription_id = EXCLUDED.subscription_id,
                   recurso_id = NULL,
                   expira_em = EXCLUDED.expira_em,
                   delta_token = EXCLUDED.delta_token,
                   ativa = TRUE
             WHERE NOT integracao.conexao.ativa
            RETURNING id
            """,
            (PROVEDOR, "padrao", "changes", config.channel_token, canal_id, expira_em, inicio),
        ).fetchone()
        if reservada is None:
            raise ErroDeOperacao("Já existe um canal ativo. Use renovar ou fechar antes de abrir.")

    try:
        resposta = _pedir(
            f"{DRIVE}/changes/watch?pageToken={inicio}",
            metodo="POST",
            token=token,
            dados={
                "id": canal_id,
                "type": "web_hook",
                "address": f"{config.url_publica}/api/v1/webhooks/google",
                "token": config.channel_token,
                # O Google espera milissegundos desde a época, como texto.
                "expiration": str(int(expira_em.timestamp() * 1000)),
            },
        )
    except ErroDeOperacao:
        # O canal nunca chegou a existir do lado do Google: desfaz a linha
        # especulativa, em vez de deixar uma origem "ativa" fantasma que nunca
        # vai receber nada e nunca vai ser corretamente encerrada por `fechar`.
        with psycopg.connect(config.dsn) as conexao:
            conexao.execute(
                "UPDATE integracao.conexao SET ativa = FALSE WHERE provedor = %s AND subscription_id = %s",
                (PROVEDOR, canal_id),
            )
        raise

    with psycopg.connect(config.dsn) as conexao:
        conexao.execute(
            "UPDATE integracao.conexao SET recurso_id = %s WHERE provedor = %s AND subscription_id = %s",
            (resposta.get("resourceId"), PROVEDOR, canal_id),
        )

    print(f"Canal aberto.\n  id:        {canal_id}")
    print(f"  recurso:   {resposta.get('resourceId')}")
    print(f"  expira em: {expira_em.isoformat()}")
    print(f"  endereço:  {config.url_publica}/api/v1/webhooks/google")
    print("\nO Drive vai mandar agora uma notificação `sync`, que é registrada e ignorada.")


def renovar(config: Config) -> None:
    """Substitui o canal atual por um novo, preservando o ponto de retomada.

    O Drive não permite estender um canal nem alterar seu endereço, então renovar
    é necessariamente encerrar e abrir outro. O que se preserva é o `delta_token`:
    sem ele, a varredura seguinte começaria do presente e as mudanças ocorridas
    entre o fechamento e a abertura nunca seriam vistas.

    Feito para rodar sem ninguém olhando, semanalmente. Isso exige que a tela de
    consentimento OAuth esteja publicada — em modo *Testing* o Google revoga o
    refresh token a cada sete dias, e aí o comando para para pedir autorização no
    navegador. Ver a Seção 5.1.6 do Projeto.md, Manual de operação — Google Drive, Manutenção.
    """
    with psycopg.connect(config.dsn) as conexao:
        linha = conexao.execute(
            "SELECT delta_token FROM integracao.conexao WHERE provedor = %s AND ativa",
            (PROVEDOR,),
        ).fetchone()

    retomar_de = linha[0] if linha else None
    if retomar_de:
        print(f"Preservando o ponto de retomada do feed: {retomar_de}")

    fechar(config)
    abrir(config, retomar_de=retomar_de)


def fechar(config: Config) -> None:
    token = obter_token(config)

    with psycopg.connect(config.dsn) as conexao:
        linhas = conexao.execute(
            "SELECT subscription_id, recurso_id FROM integracao.conexao WHERE provedor = %s AND ativa",
            (PROVEDOR,),
        ).fetchall()

        if not linhas:
            print("Nenhum canal ativo.")
            return

        for canal_id, recurso_id in linhas:
            # A desativação local vem primeiro e é a que importa para a segurança:
            # a partir dela o verificador já recusa qualquer entrega com 401,
            # mesmo que o encerramento do lado do Google falhe.
            conexao.execute(
                "UPDATE integracao.conexao SET ativa = FALSE WHERE provedor = %s AND subscription_id = %s",
                (PROVEDOR, canal_id),
            )

            if not recurso_id:
                print(f"Canal {canal_id} desativado localmente (sem resourceId; vai expirar sozinho).")
                continue

            try:
                _pedir(
                    f"{DRIVE}/channels/stop",
                    metodo="POST",
                    token=token,
                    dados={"id": canal_id, "resourceId": recurso_id},
                )
                print(f"Canal {canal_id} encerrado no Google e desativado localmente.")
            except ErroDeOperacao as exc:
                # Canal já expirado devolve erro, e isso não é problema: o efeito
                # pretendido — parar de receber — já aconteceu.
                print(f"Canal {canal_id} desativado localmente. O Google recusou o encerramento: {exc}")


def listar(config: Config) -> None:
    with psycopg.connect(config.dsn) as conexao:
        linhas = conexao.execute(
            """
            SELECT subscription_id, expira_em, ativa, delta_pendente
              FROM integracao.conexao WHERE provedor = %s ORDER BY criada_em DESC
            """,
            (PROVEDOR,),
        ).fetchall()

    if not linhas:
        print("Nenhum canal registrado.")
        return

    for canal_id, expira_em, ativa, pendente in linhas:
        estado = "ativo" if ativa else "inativo"
        vencido = " (VENCIDO)" if expira_em and expira_em < datetime.now(UTC) else ""
        print(f"{canal_id}  {estado}{vencido}  expira={expira_em}  varredura_pendente={pendente}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("comando", choices=("abrir", "renovar", "fechar", "listar"))
    argumentos = parser.parse_args()

    try:
        config = Config.from_environment()
        {"abrir": abrir, "renovar": renovar, "fechar": fechar, "listar": listar}[argumentos.comando](config)
    except ErroDeOperacao as exc:
        print(f"\nErro: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
