from __future__ import annotations

import hashlib
import hmac
import json
import logging
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum, auto
from functools import lru_cache
from pathlib import Path

import httpx
import sqlalchemy
import yaml
from sqlalchemy import text

logger = logging.getLogger(__name__)

# src/services/alerta_service.py -> src/config/alertas.yaml
_ARQUIVO_CONFIG = Path(__file__).resolve().parent.parent / "config" / "alertas.yaml"

_TIMEOUT_HTTP = 5.0
_VERSAO_EVENTO = "1"


class AlertaServiceErrorCode(Enum):
    ASSINANTE_NAO_ENCONTRADO = auto()


class AlertaServiceError(Exception):
    def __init__(self, code: AlertaServiceErrorCode) -> None:
        self.code = code
        super().__init__(code.name)


@dataclass(frozen=True)
class AssinanteCriado:
    id: str
    projeto_id: str
    url: str
    secret: str


@dataclass(frozen=True)
class AssinantePublico:
    id: str
    projeto_id: str
    url: str
    ativa: bool
    criado_em: str


class ConfiguracaoAlertas:
    def __init__(self, intencoes_de_risco: list[str], limiar_confianca: float) -> None:
        self.intencoes_de_risco = intencoes_de_risco
        self.limiar_confianca = limiar_confianca

    @classmethod
    @lru_cache(maxsize=1)
    def carregar(cls) -> ConfiguracaoAlertas:
        dados = yaml.safe_load(_ARQUIVO_CONFIG.read_text(encoding="utf-8")) or {}
        return cls(
            intencoes_de_risco=list(dados.get("intencoes_de_risco", [])),
            limiar_confianca=float(dados.get("limiar_confianca", 0.0)),
        )


def _agora_iso() -> str:
    return datetime.now(UTC).isoformat()


class RegistrarAssinante:
    def __init__(self, engine: sqlalchemy.Engine) -> None:
        self._engine = engine

    def registrar(self, *, projeto_id: str, url: str) -> AssinanteCriado:
        secret = secrets.token_hex(32)
        secret_hash = hashlib.sha256(secret.encode()).hexdigest()
        with self._engine.connect() as conn:
            row = conn.execute(
                text(
                    "INSERT INTO alerta.assinante (projeto_id, url, secret_hash) "
                    "VALUES (:projeto_id, :url, :secret_hash) "
                    "RETURNING id, projeto_id, url"
                ),
                {"projeto_id": projeto_id, "url": url, "secret_hash": secret_hash},
            ).one()
            conn.commit()
        return AssinanteCriado(
            id=str(row.id),
            projeto_id=row.projeto_id,
            url=row.url,
            secret=secret,
        )


class DesativarAssinante:
    def __init__(self, engine: sqlalchemy.Engine) -> None:
        self._engine = engine

    def desativar(self, *, assinante_id: str) -> None:
        with self._engine.connect() as conn:
            result = conn.execute(
                text("UPDATE alerta.assinante SET ativa = FALSE WHERE id = :id"),
                {"id": assinante_id},
            )
            conn.commit()
        if result.rowcount == 0:
            raise AlertaServiceError(AlertaServiceErrorCode.ASSINANTE_NAO_ENCONTRADO)


class ListarAssinantes:
    def __init__(self, engine: sqlalchemy.Engine) -> None:
        self._engine = engine

    def listar(self) -> list[AssinantePublico]:
        with self._engine.connect() as conn:
            rows = conn.execute(
                text(
                    "SELECT id, projeto_id, url, ativa, criado_em "
                    "FROM alerta.assinante ORDER BY criado_em DESC"
                )
            ).all()
        return [
            AssinantePublico(
                id=str(r.id),
                projeto_id=r.projeto_id,
                url=r.url,
                ativa=r.ativa,
                criado_em=r.criado_em.isoformat(),
            )
            for r in rows
        ]


class DespachoDesligado:
    """Substitui `DispatcherAlerta` quando não há banco configurado.

    Mesmo raciocínio de `GravacaoDesligada`, em `auditoria_service.py`: o
    despacho de alertas pendura-se em `POST /audio/{id}/analyze` como efeito
    colateral, e sem banco a análise inteira respondia 500.
    """

    def __init__(self, motivo: str) -> None:
        self._motivo = motivo
        self._avisou = False

    def despachar(self, **_: object) -> None:
        if not self._avisou:
            logger.warning("Despacho de alertas desligado: %s", self._motivo)
            self._avisou = True


class DispatcherAlerta:
    def __init__(self, engine: sqlalchemy.Engine, configuracao: ConfiguracaoAlertas) -> None:
        self._engine = engine
        self._configuracao = configuracao

    def _deve_disparar(self, intencao: str, confianca_pln: float) -> bool:
        return (
            intencao in self._configuracao.intencoes_de_risco
            and confianca_pln >= self._configuracao.limiar_confianca
        )

    def despachar(
        self,
        *,
        intencao: str,
        confianca_pln: float,
        audio_id: str,
        transcricao: str,
        projeto_id: str | None,
    ) -> None:
        if not self._deve_disparar(intencao, confianca_pln):
            return

        assinantes = self._assinantes_ativos(projeto_id)
        if not assinantes:
            return

        payload = {
            "evento": "risco_detectado",
            "versao": _VERSAO_EVENTO,
            "timestamp": _agora_iso(),
            "audio_id": audio_id,
            "risco": {
                "intencao": intencao,
                "confianca": confianca_pln,
                "transcricao": transcricao,
            },
        }
        corpo = json.dumps(payload, ensure_ascii=False)

        with httpx.Client(timeout=_TIMEOUT_HTTP) as client:
            for assinante_id, url, secret_hash in assinantes:
                historico_id = self._registrar_historico(assinante_id, audio_id, payload)
                self._enviar(client, url, corpo, secret_hash, historico_id)

    def _assinantes_ativos(self, projeto_id: str | None) -> list[tuple[str, str, str]]:
        if projeto_id is None:
            consulta = text(
                "SELECT id, url, secret_hash FROM alerta.assinante WHERE ativa = TRUE"
            )
            params: dict[str, object] = {}
        else:
            consulta = text(
                "SELECT id, url, secret_hash FROM alerta.assinante "
                "WHERE ativa = TRUE AND projeto_id = :projeto_id"
            )
            params = {"projeto_id": projeto_id}
        with self._engine.connect() as conn:
            rows = conn.execute(consulta, params).all()
        return [(str(r.id), r.url, r.secret_hash) for r in rows]

    def _registrar_historico(self, assinante_id: str, audio_id: str, payload: dict) -> str:
        with self._engine.connect() as conn:
            row = conn.execute(
                text(
                    "INSERT INTO alerta.historico "
                    "(assinante_id, audio_id, payload, situacao) "
                    "VALUES (:assinante_id, :audio_id, CAST(:payload AS JSONB), 'pendente') "
                    "RETURNING id"
                ),
                {
                    "assinante_id": assinante_id,
                    "audio_id": audio_id,
                    "payload": json.dumps(payload, ensure_ascii=False),
                },
            ).one()
            conn.commit()
        return str(row.id)

    def _enviar(
        self,
        client: httpx.Client,
        url: str,
        corpo: str,
        secret_hash: str,
        historico_id: str,
    ) -> None:
        # Nota: a chave do HMAC é SHA256(secret), não o secret em texto plano, pois
        # nunca armazenamos o plaintext. Assinantes devem verificar com:
        #   HMAC-SHA256(sha256(secret).hexdigest(), body)
        # Isso difere do padrão GitHub/Stripe — documentar no contrato da API.
        assinatura = hmac.new(
            secret_hash.encode(), corpo.encode(), hashlib.sha256
        ).hexdigest()
        situacao = "falhou"
        status_code: int | None = None
        try:
            resposta = client.post(
                url,
                content=corpo,
                headers={
                    "Content-Type": "application/json",
                    "X-Alerta-Signature": assinatura,
                },
            )
            status_code = resposta.status_code
            if resposta.is_success:
                situacao = "enviado"
        except httpx.HTTPError as exc:
            logger.warning("Falha ao enviar alerta para %s: %s", url, exc)
        finally:
            self._atualizar_historico(historico_id, situacao, status_code)

    def _atualizar_historico(
        self, historico_id: str, situacao: str, status_code: int | None
    ) -> None:
        with self._engine.connect() as conn:
            conn.execute(
                text(
                    "UPDATE alerta.historico "
                    "SET situacao = :situacao, status_code = :status_code "
                    "WHERE id = :id"
                ),
                {"situacao": situacao, "status_code": status_code, "id": historico_id},
            )
            conn.commit()
