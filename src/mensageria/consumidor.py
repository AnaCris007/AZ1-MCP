"""Worker consumidor: lê `varredura.pendente` e faz a varredura de cada origem.

É um processo autônomo, iniciado por `python -m mensageria.consumidor`. Conecta
ao RabbitMQ com reconexão e backoff (tanto na abertura, via
`connection_attempts`/`retry_delay` do pika, quanto num laço externo que reabre
se a conexão cair depois de estabelecida — um broker reiniciado não derruba o
worker de vez).

Para cada mensagem:
  • desserializa o envelope;
  • chama `VarreduraDeConexao.varrer`;
  • `basic_ack` em caso de sucesso.

Tratamento de falha, alinhado ao TI-42/TI-43:
  • exceção no processamento  → `basic_nack(requeue=True)`: a mensagem VOLTA à
    fila para nova tentativa (erro transitório, ex.: blip do banco). O laço não é
    infinito — a fila é declarada com `x-delivery-limit`, e o broker dead-letter-a
    sozinho ao ultrapassar o limite;
  • payload indesserializável → `basic_nack(requeue=False)` DIRETO, sem laço: não
    adianta reentregar algo que nunca vai ser lido — vai para a fila morta;
  • versão de envelope desconhecida → loga e `basic_nack(requeue=False)`.

`pika` é importado dentro dos métodos, pela mesma razão do publicador: manter o
módulo importável (e as constantes de topologia) mesmo onde o broker não existe.
"""

from __future__ import annotations

import logging
import os
import time
from typing import Any

from dotenv import load_dotenv

from mensageria.config import MensageriaSettings
from mensageria.envelope import EnvelopeInvalido, desserializar
from mensageria.publicador import declarar_topologia
from mensageria.varredura import VarreduraDeConexao
from services.webhook_service import VERSAO_ENVELOPE

logger = logging.getLogger(__name__)

# Espera entre tentativas de reabrir a conexão no laço externo, quando o broker
# cai depois de já ter subido. Curto o bastante para retomar rápido, longo o
# bastante para não martelar um broker que está reiniciando.
_ESPERA_RECONEXAO_SEGUNDOS = 5.0


class ConsumidorVarredura:
    """Consome a fila de varredura, marcando cada origem como varrida."""

    def __init__(self, settings: MensageriaSettings, varredura: Any) -> None:
        # `varredura` é qualquer objeto com `varrer(evento)` — o stub
        # `VarreduraDeConexao` (só estado) ou `VarreduraComIndexacao` (baixa e
        # reindexa). O consumidor não distingue: chama `varrer` e trata a falha.
        self._settings = settings
        self._varredura = varredura

    def _tratar(self, canal: Any, metodo: Any, corpo: bytes) -> None:
        try:
            evento = desserializar(corpo)
        except EnvelopeInvalido:
            # Irrecuperável: reentregar não ajuda. Vai direto para a fila morta.
            logger.warning(
                "Payload indesserializável na fila %s; enviando para a fila morta.",
                self._settings.fila,
                exc_info=True,
            )
            canal.basic_nack(delivery_tag=metodo.delivery_tag, requeue=False)
            return

        if evento.versao != VERSAO_ENVELOPE:
            # Versão que este worker não sabe interpretar. Não é lixo, mas também
            # não é seguro processar — vai para a fila morta, com o motivo no log.
            logger.warning(
                "Versão de envelope desconhecida (%s; esperado %s); enviando para a fila morta.",
                evento.versao,
                VERSAO_ENVELOPE,
            )
            canal.basic_nack(delivery_tag=metodo.delivery_tag, requeue=False)
            return

        try:
            self._varredura.varrer(evento)
        except Exception:
            # Falha de PROCESSAMENTO (transitória por natureza): devolve à fila
            # para nova tentativa (requeue=True). O laço de reentrega não é
            # infinito — a fila é declarada com `x-delivery-limit` (ver
            # `declarar_topologia`), e o broker dead-letter-a a mensagem sozinho
            # ao ultrapassar o limite. É a diferença entre este caso e o payload
            # indesserializável acima: aquele nunca vai ser lido, então vai
            # direto para a morta; este pode ser um erro passageiro do banco.
            logger.warning(
                "Falha ao varrer correlacao=%s; devolvendo à fila para nova tentativa.",
                evento.correlacao,
            )
            canal.basic_nack(delivery_tag=metodo.delivery_tag, requeue=True)
            return

        canal.basic_ack(delivery_tag=metodo.delivery_tag)

    def _consumir_uma_vez(self) -> None:
        """Abre a conexão e consome até ela cair. Levanta se a conexão falhar."""
        import pika

        parametros = pika.URLParameters(self._settings.url)
        parametros.connection_attempts = max(parametros.connection_attempts, 3)
        parametros.retry_delay = max(parametros.retry_delay, 2)

        conexao = pika.BlockingConnection(parametros)
        try:
            canal = conexao.channel()
            declarar_topologia(canal, self._settings)
            # Uma mensagem por vez: o worker só recebe a próxima depois de
            # confirmar a atual, para não acumular trabalho não confirmado.
            canal.basic_qos(prefetch_count=1)

            def _callback(ch: Any, metodo: Any, _propriedades: Any, corpo: bytes) -> None:
                self._tratar(ch, metodo, corpo)

            canal.basic_consume(queue=self._settings.fila, on_message_callback=_callback)
            logger.info("Consumidor pronto na fila %s.", self._settings.fila)
            canal.start_consuming()
        finally:
            try:
                if conexao.is_open:
                    conexao.close()
            except Exception:
                logger.debug("Falha ao fechar a conexão do consumidor; ignorando.", exc_info=True)

    def rodar(self) -> None:
        """Laço externo de reconexão: se a conexão cair, reabre após backoff."""
        import pika

        while True:
            try:
                self._consumir_uma_vez()
            except pika.exceptions.AMQPError:
                logger.warning(
                    "Conexão com o broker perdida; reabrindo em %.0fs.",
                    _ESPERA_RECONEXAO_SEGUNDOS,
                    exc_info=True,
                )
                time.sleep(_ESPERA_RECONEXAO_SEGUNDOS)
            except KeyboardInterrupt:
                logger.info("Consumidor interrompido; encerrando.")
                return


def _abrir_pool(papel: str | None) -> Any:
    """Monta o pool do worker no mesmo padrão de `dependencies.get_webhook_connection_pool`.

    Com `papel="az1_webhook"` (varredura só de estado), a migração 06 já autoriza
    `UPDATE (delta_pendente) ON integracao.conexao` — sem migração nova. Com
    `papel=None` (varredura com indexação), usa o papel do próprio DSN, que precisa
    poder `UPDATE (delta_token)` e escrever na coleção vetorial `vecs`.
    """
    from services.database_service import PostgresSettings, abrir_pool

    dsn = os.environ.get("DATABASE_URL", "").strip()
    if not dsn:
        dsn = PostgresSettings.from_environment().dsn
    return abrir_pool(PostgresSettings(dsn=dsn, papel=papel))


def _indexacao_disponivel() -> bool:
    """Diz se dá para fazer a varredura REAL (baixar do Drive + vetorizar).

    Exige as três peças: credenciais OAuth do Drive no `.env`, o token gravado por
    `drive_channel_service abrir`, e a chave do Gemini para os embeddings. Faltando
    qualquer uma, o worker degrada para a varredura só de estado — mesma filosofia
    do resto do projeto (degradar em vez de derrubar).
    """
    from pathlib import Path

    tem_oauth = bool(os.environ.get("GOOGLE_CLIENT_ID") and os.environ.get("GOOGLE_CLIENT_SECRET"))
    tem_token = Path(".google_token.json").exists()
    tem_gemini = bool(os.environ.get("GEMINI_API_KEY"))
    return tem_oauth and tem_token and tem_gemini


def _montar_varredura() -> tuple[Any, Any]:
    """Escolhe a varredura e o pool coerente com ela. Retorna (varredura, pool)."""
    if _indexacao_disponivel():
        from mensageria.varredura_indexacao import VarreduraComIndexacao

        pasta_raiz = os.environ.get("DRIVE_PASTA_PMO_ID", "").strip() or None
        if pasta_raiz:
            logger.info(
                "Credenciais do Drive e do Gemini presentes: varredura COM indexação, "
                "escopada à pasta do PMO (DRIVE_PASTA_PMO_ID=%s).",
                pasta_raiz,
            )
        else:
            logger.warning(
                "Varredura COM indexação SEM escopo: DRIVE_PASTA_PMO_ID não definida. O "
                "changes.list monitora o Drive INTEIRO, então TODO .docx/.xlsx alterado "
                "na conta será indexado. Defina DRIVE_PASTA_PMO_ID para limitar ao PMO."
            )
        pool = _abrir_pool(papel=None)  # papel do DSN: precisa de delta_token + vecs
        return VarreduraComIndexacao(pool, pasta_raiz=pasta_raiz), pool

    logger.info(
        "Varredura só de estado (sem indexação): faltam credenciais do Drive e/ou GEMINI_API_KEY, "
        "ou .google_token.json. O worker fecha delta_pendente sem baixar arquivos."
    )
    pool = _abrir_pool(papel="az1_webhook")
    return VarreduraDeConexao(pool), pool


def main() -> None:
    # Lê o `.env` como os outros entrypoints (`az1_api.main`,
    # `drive_channel_service`), para o worker não exigir um `source .env` manual.
    load_dotenv()
    logging.basicConfig(
        level=os.environ.get("LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    settings = MensageriaSettings.from_environment()
    if settings is None:
        raise SystemExit(
            "RABBITMQ_URL não configurada. O worker de varredura não tem barramento "
            "para consumir; defina RABBITMQ_URL (ex.: amqp://az1:az1@rabbitmq:5672/)."
        )

    varredura, _pool = _montar_varredura()
    consumidor = ConsumidorVarredura(settings, varredura)
    consumidor.rodar()


if __name__ == "__main__":
    main()
