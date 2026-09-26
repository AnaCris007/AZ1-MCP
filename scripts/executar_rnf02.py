#!/usr/bin/env python3
"""Executa e documenta a matriz de autenticação do RNF02.

As chaves e os JWTs são sintéticos, existem somente na memória e nunca são
gravados nos artefatos. Dependências de negócio são substituídas por sentinelas
para demonstrar que uma credencial rejeitada não alcança a regra de negócio.
"""

from __future__ import annotations

import csv
import io
import json
import logging
import sys
import time
import wave
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

from az1_api import dependencies
from az1_api.dependencies import get_token_verifier, get_usuario_resolver, require_authenticated_user
from az1_api.main import app
from services.auth_service import (
    REQUIRED_AUDIENCE,
    AuthKeyMode,
    AuthMode,
    SupabaseAuthSettings,
    SupabaseTokenVerifier,
)
from services.usuario_service import DomainUser


UNAUTHORIZED_BODY = {
    "error": "unauthorized",
    "message": "Token de autenticação ausente ou inválido.",
}
CONVERSA_ID = "11111111-1111-4111-8111-111111111111"


class RegraDeNegocioAlcancada(RuntimeError):
    pass


class SentinelaNegocio:
    """Falha deliberadamente na primeira chamada de negócio e registra-a."""

    def __init__(self, nome: str, chamadas: list[str]) -> None:
        self.nome = nome
        self.chamadas = chamadas

    def __getattr__(self, atributo: str):
        def chamar(*_args, **_kwargs):
            self.chamadas.append(f"{self.nome}.{atributo}")
            raise RegraDeNegocioAlcancada(f"sentinela:{self.nome}.{atributo}")

        return chamar

    def __call__(self, *_args, **_kwargs):
        self.chamadas.append(f"{self.nome}.__call__")
        raise RegraDeNegocioAlcancada(f"sentinela:{self.nome}.__call__")


class ResolvedorEspiao:
    def __init__(self) -> None:
        self.chamadas: list[dict[str, str]] = []

    def resolve(self, *, auth_user_id: str, email: str, name: str) -> DomainUser:
        self.chamadas.append({"auth_user_id": auth_user_id, "email": email, "name": name})
        return DomainUser(id=9002, perfil="pmo")


class Capturador(logging.Handler):
    def __init__(self) -> None:
        super().__init__(logging.WARNING)
        self.mensagens: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.mensagens.append(self.format(record))


@dataclass(frozen=True)
class Operacao:
    metodo: str
    molde: str
    caminho: str
    operation_id: str


def _wav_minimo() -> bytes:
    saida = io.BytesIO()
    with wave.open(saida, "wb") as arquivo:
        arquivo.setnchannels(1)
        arquivo.setsampwidth(2)
        arquivo.setframerate(8000)
        arquivo.writeframes(b"\x00\x00" * 80)
    return saida.getvalue()


def _operacoes_protegidas() -> list[Operacao]:
    documento = app.openapi()
    protegidas: list[Operacao] = []
    substituicoes = {
        "audio_id": "audio-rnf02",
        "pendencia_id": "1",
        "evento_id": "1",
        "conversa_id": CONVERSA_ID,
        "assinante_id": "22222222-2222-4222-8222-222222222222",
    }
    for molde, item in documento["paths"].items():
        for metodo, descricao in item.items():
            if not isinstance(descricao, dict) or not descricao.get("security"):
                continue
            caminho = molde
            for campo, valor in substituicoes.items():
                caminho = caminho.replace("{" + campo + "}", valor)
            protegidas.append(
                Operacao(metodo.upper(), molde, caminho, descricao.get("operationId", ""))
            )
    return sorted(protegidas, key=lambda item: (item.caminho, item.metodo))


def _corpo(operacao: Operacao) -> tuple[dict[str, Any], dict[str, Any]]:
    json_body: dict[str, Any] | None = None
    files: dict[str, Any] | None = None
    if operacao.molde == "/api/v1/audio":
        files = {"audio": ("rnf02.wav", _wav_minimo(), "audio/wav")}
    elif operacao.molde == "/api/v1/chat":
        json_body = {"message": "Consulta sintética RNF02.", "conversation_id": CONVERSA_ID}
    elif operacao.molde == "/api/v1/rag/search":
        json_body = {"query": "status SYN-01", "n_resultados": 5}
    elif operacao.molde == "/api/v1/tasks/{pendencia_id}":
        json_body = {"done": True}
    elif operacao.molde == "/api/v1/calendar/events":
        json_body = {
            "titulo": "Evento RNF02",
            "data": "2026-09-25",
            "hora": "09:00",
            "descricao": "Sintético",
        }
    elif operacao.molde == "/api/v1/conversas/avaliacoes":
        json_body = {"conversa_id": CONVERSA_ID, "ordem": 2, "polaridade": "positiva"}
    elif operacao.molde == "/api/v1/text-to-speech":
        json_body = {"text": "Teste RNF02", "voice": "Kore", "format": "wav"}
    elif operacao.molde == "/api/v1/alertas/assinantes":
        json_body = {"projeto_id": "SYN-01", "url": "https://example.com/rnf02"}
    kwargs: dict[str, Any] = {}
    if json_body is not None:
        kwargs["json"] = json_body
    if files is not None:
        kwargs["files"] = files
    return kwargs, {"tipo": "multipart" if files else "json" if json_body is not None else "sem_corpo"}


def _dependencias_de_negocio(chamadas: list[str]) -> dict[Any, Any]:
    ignorar = {require_authenticated_user, get_token_verifier, get_usuario_resolver}
    # O FastAPI atual preserva, em algumas rotas incluídas, uma árvore parcial
    # em ``APIRoute.dependant``. Começamos portanto pelo catálogo explícito de
    # factories da borda e somamos o que a árvore expõe. Factories de webhook
    # não são usadas pelas operações protegidas e ficam fora da substituição.
    encontradas: set[Any] = {
        valor
        for nome, valor in vars(dependencies).items()
        if nome.startswith("get_")
        and callable(valor)
        and valor not in ignorar
        and "webhook" not in nome
        and nome not in {"get_publicador"}
    }

    def visitar(dependant) -> None:
        for filha in dependant.dependencies:
            chamada = filha.call
            if getattr(chamada, "__module__", "") == dependencies.__name__ and chamada not in ignorar:
                encontradas.add(chamada)
            visitar(filha)

    for rota in app.routes:
        if isinstance(rota, APIRoute):
            visitar(rota.dependant)

    return {
        chamada: (lambda alvo=chamada: SentinelaNegocio(alvo.__name__, chamadas))
        for chamada in encontradas
    }


def _tokens(settings: SupabaseAuthSettings, chave: bytes, outra_chave: bytes) -> dict[str, str | None]:
    agora = int(time.time())
    base = {
        "aud": REQUIRED_AUDIENCE,
        "iss": settings.issuer,
        "sub": "11111111-1111-4111-8111-111111111111",
        "email": "participante.rnf02@example.com",
        "app_metadata": {"provider": "azure"},
        "user_metadata": {"full_name": "Participante RNF02"},
    }

    def assinar(**mudancas: Any) -> str:
        claims = {**base, "exp": agora + 3600, **mudancas}
        return jwt.encode(claims, chave, algorithm="ES256")

    return {
        "valido": assinar(),
        "ausente": None,
        "malformado": "rnf02-token-malformado-nao-jwt",
        "expirado": assinar(exp=agora - 60),
        "assinatura_invalida": jwt.encode({**base, "exp": agora + 3600}, outra_chave, algorithm="ES256"),
        "audiencia_incorreta": assinar(aud="publico-incorreto"),
    }


def _requisitar(client: TestClient, operacao: Operacao, token: str | None):
    kwargs, resumo_corpo = _corpo(operacao)
    if token is not None:
        kwargs["headers"] = {"Authorization": f"Bearer {token}"}
    return client.request(operacao.metodo, operacao.caminho, **kwargs), resumo_corpo


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit("uso: executar_rnf02.py DIRETORIO_SAIDA")
    saida = Path(sys.argv[1])
    saida.mkdir(parents=True, exist_ok=True)

    chave_privada_obj = ec.generate_private_key(ec.SECP256R1())
    outra_privada_obj = ec.generate_private_key(ec.SECP256R1())
    chave_privada = chave_privada_obj.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )
    outra_privada = outra_privada_obj.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )
    chave_publica = chave_privada_obj.public_key().public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
    )
    settings = SupabaseAuthSettings(
        project_url="https://rnf02-sintetico.supabase.co",
        mode=AuthMode.ENABLED,
        key_mode=AuthKeyMode.JWKS,
    )
    tokens = _tokens(settings, chave_privada, outra_privada)
    operacoes = _operacoes_protegidas()
    chamadas_negocio: list[str] = []
    resolvedor = ResolvedorEspiao()
    capturador = Capturador()
    logger_auth = logging.getLogger("az1_api.dependencies")
    logger_api = logging.getLogger("az1_api.main")
    logger_auth.addHandler(capturador)
    nivel_anterior = logger_auth.level
    api_desabilitado_anterior = logger_api.disabled
    logger_auth.setLevel(logging.WARNING)
    # As sentinelas geram 500 deliberado depois da autenticação válida. O
    # traceback não acrescenta evidência e tornaria a execução desnecessariamente
    # ruidosa; as causas de autenticação continuam capturadas acima.
    logger_api.disabled = True

    app.dependency_overrides.update(_dependencias_de_negocio(chamadas_negocio))
    app.dependency_overrides[get_token_verifier] = lambda: SupabaseTokenVerifier(
        settings, key_resolver=lambda _token: chave_publica
    )
    app.dependency_overrides[get_usuario_resolver] = lambda: resolvedor
    tentativas: list[dict[str, Any]] = []
    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            for operacao in operacoes:
                antes_identidade = len(resolvedor.chamadas)
                antes_negocio = len(chamadas_negocio)
                resposta, corpo = _requisitar(client, operacao, tokens["valido"])
                identidade_resolvida = len(resolvedor.chamadas) == antes_identidade + 1
                tentativas.append(
                    {
                        "metodo": operacao.metodo,
                        "endpoint": operacao.molde,
                        "condicao": "valido",
                        "authorization": "Bearer <redacted>",
                        "corpo": corpo["tipo"],
                        "status": resposta.status_code,
                        "identidade_resolvida": identidade_resolvida,
                        "regra_negocio_alcancada": len(chamadas_negocio) > antes_negocio,
                        "resultado": "PASSOU" if resposta.status_code != 401 and identidade_resolvida else "FALHOU",
                    }
                )

            for operacao in operacoes:
                for condicao in ("ausente", "malformado", "expirado", "assinatura_invalida", "audiencia_incorreta"):
                    antes_identidade = len(resolvedor.chamadas)
                    antes_negocio = len(chamadas_negocio)
                    resposta, corpo = _requisitar(client, operacao, tokens[condicao])
                    passou = (
                        resposta.status_code == 401
                        and resposta.json() == UNAUTHORIZED_BODY
                        and resposta.headers.get("www-authenticate") == "Bearer"
                        and len(resolvedor.chamadas) == antes_identidade
                        and len(chamadas_negocio) == antes_negocio
                    )
                    tentativas.append(
                        {
                            "metodo": operacao.metodo,
                            "endpoint": operacao.molde,
                            "condicao": condicao,
                            "authorization": "<absent>" if condicao == "ausente" else "Bearer <redacted>",
                            "corpo": corpo["tipo"],
                            "status": resposta.status_code,
                            "identidade_resolvida": len(resolvedor.chamadas) > antes_identidade,
                            "regra_negocio_alcancada": len(chamadas_negocio) > antes_negocio,
                            "resultado": "PASSOU" if passou else "FALHOU",
                        }
                    )
    finally:
        app.dependency_overrides.clear()
        logger_auth.removeHandler(capturador)
        logger_auth.setLevel(nivel_anterior)
        logger_api.disabled = api_desabilitado_anterior

    valores_sensiveis = [valor for valor in tokens.values() if valor]
    log_completo = "\n".join(capturador.mensagens)
    vazou_segredo = any(valor in log_completo for valor in valores_sensiveis)
    falhas = [item for item in tentativas if item["resultado"] != "PASSOU"]
    validas = [item for item in tentativas if item["condicao"] == "valido"]
    invalidas = [item for item in tentativas if item["condicao"] != "valido"]
    aprovado = not falhas and not vazou_segredo and len(operacoes) > 0

    inventario = [
        {"metodo": op.metodo, "endpoint": op.molde, "operation_id": op.operation_id}
        for op in operacoes
    ]
    (saida / "inventario_endpoints.json").write_text(
        json.dumps(inventario, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (saida / "configuracao_sso.json").write_text(
        json.dumps(
            {
                "modo": "enabled",
                "provedor": "azure",
                "modo_chave": "jwks",
                "algoritmo": "ES256",
                "issuer": settings.issuer,
                "audience": REQUIRED_AUDIENCE,
                "material_criptografico": "efemero_em_memoria_nao_persistido",
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    with (saida / "tentativas.csv").open("w", newline="", encoding="utf-8") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=list(tentativas[0]))
        escritor.writeheader()
        escritor.writerows(tentativas)
    (saida / "logs_sanitizados.txt").write_text(log_completo + "\n", encoding="utf-8")

    resultado = {
        "rnf": "RNF02",
        "resultado": "APROVADO" if aprovado else "REPROVADO",
        "endpoints_protegidos": len(operacoes),
        "tentativas_totais": len(tentativas),
        "credencial_valida": {"passou": sum(x["resultado"] == "PASSOU" for x in validas), "total": len(validas)},
        "credenciais_invalidas": {"passou": sum(x["resultado"] == "PASSOU" for x in invalidas), "total": len(invalidas)},
        "falhas": len(falhas),
        "segredo_em_log": vazou_segredo,
        "criterio": "100% válidas aceitas; 100% inválidas bloqueadas antes do negócio; nenhum segredo em log",
    }
    (saida / "resultado.json").write_text(
        json.dumps(resultado, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    relatorio = f"""# Execução RNF02 — autenticação

**Resultado: {resultado['resultado']}**

- Endpoints protegidos inventariados pelo OpenAPI: {len(operacoes)}
- Credenciais válidas aceitas: {resultado['credencial_valida']['passou']}/{len(validas)}
- Condições inválidas bloqueadas com 401 genérico: {resultado['credenciais_invalidas']['passou']}/{len(invalidas)}
- Tentativas que alcançaram regra de negócio após credencial inválida: {sum(x['regra_negocio_alcancada'] for x in invalidas)}
- Tokens ou chaves encontrados nos logs: {'sim' if vazou_segredo else 'não'}
- Total de tentativas: {len(tentativas)}

## Método

Foi gerado em memória um par ES256 efêmero e tokens sintéticos para as condições
válida, ausente, malformada, expirada, assinatura inválida e audiência incorreta.
Cada operação protegida declarada no OpenAPI recebeu as seis tentativas. Uma
sentinela substituiu cada dependência de negócio: nas negativas, qualquer chamada
à sentinela reprovaria o caso. Nas válidas, erros funcionais posteriores à
autenticação não contam como falha de autenticação, conforme o planejamento.

Nenhum JWT ou chave foi persistido. `tentativas.csv` redige o cabeçalho e
`logs_sanitizados.txt` contém apenas causas operacionais sem credenciais.
"""
    (saida / "relatorio.md").write_text(relatorio, encoding="utf-8")
    print(json.dumps(resultado, ensure_ascii=False))
    return 0 if aprovado else 1


if __name__ == "__main__":
    raise SystemExit(main())
