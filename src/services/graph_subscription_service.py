"""Criação, renovação e remoção da assinatura de notificações do Microsoft Graph.

Executável:

    python -m services.graph_subscription_service abrir
    python -m services.graph_subscription_service renovar
    python -m services.graph_subscription_service listar
    python -m services.graph_subscription_service fechar

A assinatura é a origem observada: enquanto ela existe, o Graph chama a nossa
rota a cada mudança no recurso. Vale no máximo 42.300 minutos (pouco menos de 30
dias) para `driveItem`, e a URL de notificação não pode ser alterada depois de
criada — reiniciar o túnel, que troca a URL, exige criar uma assinatura nova.

Simétrico a `services.drive_channel_service`, de propósito: mesmos comandos,
mesmo arquivo de configuração, mesma tabela. O que muda é o fluxo de autorização
(código de dispositivo aqui, laço de retorno local lá) e o formato da chamada.

NÃO EXERCITADO CONTRA UM TENANT REAL. O grupo não conseguiu provisionar um tenant
do Entra ID (ver Seção 5.1.1 do Projeto.md), então este script foi escrito a
partir da documentação do provedor e verificado apenas nas partes que não
dependem da rede. O receptor que ele configura, esse sim, é coberto pelos oito
casos da suíte de contrato.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import psycopg
from dotenv import load_dotenv

from services.webhook_http import ErroDeOperacao, ErroHTTP
from services.webhook_http import pedir as _pedir

GRAPH = "https://graph.microsoft.com/v1.0"

# `Files.Read.All` é o menor escopo que permite assinar o recurso e, depois,
# baixar o conteúdo para vetorizar. `offline_access` é o que faz o provedor
# devolver o refresh token — sem ele a autorização morre em uma hora.
ESCOPO = "https://graph.microsoft.com/Files.Read.All offline_access"

load_dotenv()

PROVEDOR = "microsoft_graph"
CREDENCIAIS = Path(".microsoft_token.json")

# O teto documentado para `driveItem` é 42.300 minutos. Vinte e nove dias ficam
# confortavelmente abaixo e sobrevivem a diferenças de relógio.
VALIDADE = timedelta(days=29)


@dataclass(frozen=True)
class Config:
    client_id: str
    tenant: str
    recurso: str
    client_state: str
    url_publica: str
    dsn: str

    @classmethod
    def from_environment(cls) -> Config:
        faltando = [
            nome
            for nome in ("MS_CLIENT_ID", "MS_WEBHOOK_CLIENT_STATE", "WEBHOOK_PUBLIC_URL")
            if not os.environ.get(nome)
        ]
        if faltando:
            raise ErroDeOperacao(
                f"Variáveis ausentes no .env: {', '.join(faltando)}.\n"
                "Consulte a Seção 5.1.6 do Projeto.md, Manual de operação — Microsoft Graph, Parte 2."
            )

        url = os.environ["WEBHOOK_PUBLIC_URL"].rstrip("/")
        if not url.startswith("https://"):
            # O Graph recusa assinatura com endereço que não seja HTTPS, e a
            # mensagem de erro dele não deixa isso claro.
            raise ErroDeOperacao(f"WEBHOOK_PUBLIC_URL precisa começar com https://, e está como {url!r}")

        return cls(
            client_id=os.environ["MS_CLIENT_ID"],
            tenant=os.environ.get("MS_TENANT", "consumers"),
            recurso=os.environ.get("MS_RECURSO", "/me/drive/root"),
            client_state=os.environ["MS_WEBHOOK_CLIENT_STATE"],
            url_publica=url,
            dsn=os.environ.get("DATABASE_URL", "postgresql://az1:az1@localhost:5432/az1"),
        )

    @property
    def notification_url(self) -> str:
        return f"{self.url_publica}/api/v1/webhooks/microsoft"

    def autoridade(self, caminho: str) -> str:
        return f"https://login.microsoftonline.com/{self.tenant}/oauth2/v2.0/{caminho}"


# ---------------------------------------------------------------------------
# OAuth: fluxo de código de dispositivo
# ---------------------------------------------------------------------------
# Escolhido em vez do laço de retorno local porque dispensa client secret e
# dispensa registrar URI de redirecionamento — dois passos a menos no portal do
# Azure, e duas coisas a menos para errar. Exige que "Allow public client flows"
# esteja habilitado no registro da aplicação.


def _autorizar(config: Config) -> dict[str, Any]:
    inicio = _pedir(
        config.autoridade("devicecode"),
        metodo="POST",
        formulario=True,
        dados={"client_id": config.client_id, "scope": ESCOPO},
    )

    print()
    print(inicio.get("message", f"Acesse {inicio['verification_uri']} e informe o código {inicio['user_code']}"))
    print()

    intervalo = int(inicio.get("interval", 5))
    limite = time.monotonic() + int(inicio.get("expires_in", 900))

    while time.monotonic() < limite:
        time.sleep(intervalo)
        try:
            return _pedir(
                config.autoridade("token"),
                metodo="POST",
                formulario=True,
                dados={
                    "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
                    "client_id": config.client_id,
                    "device_code": inicio["device_code"],
                },
            )
        except ErroHTTP as exc:
            if exc.codigo == "authorization_pending":
                continue
            if exc.codigo == "slow_down":
                # O provedor pede para reduzir o ritmo; insistir no mesmo passo
                # faz ele recusar de vez.
                intervalo += 5
                continue
            if exc.codigo == "authorization_declined":
                raise ErroDeOperacao("Autorização recusada no navegador.") from exc
            if exc.codigo == "expired_token":
                raise ErroDeOperacao("O código expirou. Rode o comando de novo.") from exc
            raise

    raise ErroDeOperacao("A autorização não foi concluída a tempo.")


def _renovar_token(config: Config, refresh_token: str) -> dict[str, Any]:
    return _pedir(
        config.autoridade("token"),
        metodo="POST",
        formulario=True,
        dados={
            "grant_type": "refresh_token",
            "client_id": config.client_id,
            "refresh_token": refresh_token,
            "scope": ESCOPO,
        },
    )


def obter_token(config: Config) -> str:
    """Devolve um access token válido, reaproveitando o refresh token gravado."""
    if CREDENCIAIS.exists():
        guardado = json.loads(CREDENCIAIS.read_text())
        try:
            novo = _renovar_token(config, guardado["refresh_token"])
            CREDENCIAIS.write_text(json.dumps(novo, indent=2))
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


def _gravar(config: Config, assinatura_id: str, expira_em: datetime) -> None:
    with psycopg.connect(config.dsn) as conexao:
        conexao.execute(
            """
            INSERT INTO integracao.conexao
                (provedor, conta, recurso, client_state, subscription_id, expira_em, ativa)
            VALUES (%s, %s, %s, %s, %s, %s, TRUE)
            ON CONFLICT (provedor, conta, recurso) DO UPDATE
               SET client_state = EXCLUDED.client_state,
                   subscription_id = EXCLUDED.subscription_id,
                   expira_em = EXCLUDED.expira_em,
                   ativa = TRUE
            """,
            (PROVEDOR, "padrao", config.recurso, config.client_state, assinatura_id, expira_em),
        )


def abrir(config: Config) -> None:
    token = obter_token(config)
    expira_em = datetime.now(UTC) + VALIDADE

    print(f"Criando assinatura para {config.recurso}")
    print(f"  notificationUrl: {config.notification_url}")
    print("\nO Graph vai chamar essa URL agora, com ?validationToken=, e exigir")
    print("resposta em até dez segundos. Se o túnel ou a API estiverem fora, falha aqui.\n")

    resposta = _pedir(
        f"{GRAPH}/subscriptions",
        metodo="POST",
        token=token,
        dados={
            "changeType": "updated",
            "notificationUrl": config.notification_url,
            "resource": config.recurso,
            "expirationDateTime": expira_em.isoformat().replace("+00:00", "Z"),
            "clientState": config.client_state,
            # Identificador nosso, devolvido em cada notificação. Útil para
            # correlacionar log da aplicação com log do provedor.
            "clientId": str(uuid.uuid4()),
        },
    )

    assinatura_id = resposta["id"]
    _gravar(config, assinatura_id, expira_em)

    print(f"Assinatura criada.\n  id:        {assinatura_id}")
    print(f"  expira em: {expira_em.isoformat()}")
    print("\nSuba um arquivo no recurso observado para ver a primeira notificação.")


def renovar(config: Config) -> None:
    token = obter_token(config)

    with psycopg.connect(config.dsn) as conexao:
        linhas = conexao.execute(
            "SELECT subscription_id FROM integracao.conexao WHERE provedor = %s AND ativa",
            (PROVEDOR,),
        ).fetchall()

    if not linhas:
        print("Nenhuma assinatura ativa. Use `abrir`.")
        return

    expira_em = datetime.now(UTC) + VALIDADE

    for (assinatura_id,) in linhas:
        _pedir(
            f"{GRAPH}/subscriptions/{assinatura_id}",
            metodo="PATCH",
            token=token,
            dados={"expirationDateTime": expira_em.isoformat().replace("+00:00", "Z")},
        )
        with psycopg.connect(config.dsn) as conexao:
            conexao.execute(
                "UPDATE integracao.conexao SET expira_em = %s WHERE provedor = %s AND subscription_id = %s",
                (expira_em, PROVEDOR, assinatura_id),
            )
        print(f"Assinatura {assinatura_id} renovada até {expira_em.isoformat()}.")


def fechar(config: Config) -> None:
    token = obter_token(config)

    with psycopg.connect(config.dsn) as conexao:
        linhas = conexao.execute(
            "SELECT subscription_id FROM integracao.conexao WHERE provedor = %s AND ativa",
            (PROVEDOR,),
        ).fetchall()

        if not linhas:
            print("Nenhuma assinatura ativa.")
            return

        for (assinatura_id,) in linhas:
            # A desativação local vem primeiro e é a que importa para a segurança:
            # a partir dela o verificador já recusa qualquer entrega com 401,
            # mesmo que a remoção do lado do provedor falhe.
            conexao.execute(
                "UPDATE integracao.conexao SET ativa = FALSE WHERE provedor = %s AND subscription_id = %s",
                (PROVEDOR, assinatura_id),
            )
            try:
                _pedir(f"{GRAPH}/subscriptions/{assinatura_id}", metodo="DELETE", token=token)
                print(f"Assinatura {assinatura_id} removida no Graph e desativada localmente.")
            except ErroHTTP as exc:
                # Assinatura já expirada devolve erro, e isso não é problema: o
                # efeito pretendido — parar de receber — já aconteceu.
                print(f"Assinatura {assinatura_id} desativada localmente. O Graph recusou a remoção: {exc.status}")


def listar(config: Config) -> None:
    with psycopg.connect(config.dsn) as conexao:
        linhas = conexao.execute(
            """
            SELECT subscription_id, recurso, expira_em, ativa, delta_pendente
              FROM integracao.conexao WHERE provedor = %s ORDER BY criada_em DESC
            """,
            (PROVEDOR,),
        ).fetchall()

    if not linhas:
        print("Nenhuma assinatura registrada.")
        return

    for assinatura_id, recurso, expira_em, ativa, pendente in linhas:
        estado = "ativa" if ativa else "inativa"
        vencida = " (VENCIDA)" if expira_em and expira_em < datetime.now(UTC) else ""
        print(f"{assinatura_id}  {estado}{vencida}  recurso={recurso}  expira={expira_em}  varredura={pendente}")


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
