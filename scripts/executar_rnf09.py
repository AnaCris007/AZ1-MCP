#!/usr/bin/env python3
"""Executa CT-RNF09-P/N em uma base PostgreSQL dedicada."""

from __future__ import annotations

import csv
import io
import json
import logging
import sys
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

import psycopg
from fastapi.testclient import TestClient
from psycopg_pool import ConnectionPool
from sqlalchemy import create_engine

from az1_api.dependencies import get_listador_auditoria, require_authenticated_user
from az1_api.main import app
from routes.chat import registrar_turno_em_segundo_plano
from services.auditoria_service import ListarConsultas
from services.auth_service import AuthenticatedUser
from services.conversa_repository import ConversaRepository, TurnoDoChat


REFERENCIA = datetime(2026, 9, 25, 15, 0, tzinfo=timezone.utc)
MARCA_SENHA = "SENHA-FICTICIA-RNF09-NAO-REAL"
MARCA_TOKEN = "TOKEN-FICTICIO-RNF09-NAO-REAL"


@dataclass
class Controle:
    id: str
    descricao: str
    esperado: str
    observado: str
    resultado: str


class ArmazenamentoEmMemoria:
    def __init__(self) -> None:
        self.objetos: dict[str, bytes] = {}

    def store(self, *, key: str, content, content_type: str, metadata: dict) -> None:
        content.seek(0)
        self.objetos[key] = content.read()


class RepositorioFalho:
    def __init__(self) -> None:
        self.tentativas = 0

    def registrar_turno(self, _turno) -> None:
        self.tentativas += 1
        raise ConnectionError("persistência de auditoria indisponível [sintético]")


class Capturador(logging.Handler):
    def __init__(self) -> None:
        super().__init__(logging.WARNING)
        self.linhas: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.linhas.append(self.format(record))


def adicionar(controles: list[Controle], id_: str, descricao: str, esperado: str, observado: str, passou: bool) -> None:
    controles.append(Controle(id_, descricao, esperado, observado, "PASSOU" if passou else "FALHOU"))


def executar_sql_comum(dsn: str, claims: str, sql: str, parametros=(), *, fetch=False):
    with psycopg.connect(dsn) as conexao:
        conexao.execute("SET ROLE az1_app")
        conexao.execute("SELECT set_config('request.jwt.claims', %s, true)", (claims,))
        cursor = conexao.execute(sql, parametros)
        return cursor.fetchall() if fetch else cursor.rowcount


def tentativa_bloqueada(dsn: str, claims: str, sql: str, parametros=()) -> tuple[bool, str]:
    try:
        executar_sql_comum(dsn, claims, sql, parametros)
    except (psycopg.errors.InsufficientPrivilege, psycopg.errors.CheckViolation) as erro:
        return True, type(erro).__name__
    except psycopg.Error as erro:
        return True, type(erro).__name__
    return False, "operação permitida"


def main() -> int:
    if len(sys.argv) != 3:
        raise SystemExit("uso: executar_rnf09.py DSN DIRETORIO_SAIDA")
    dsn, diretorio = sys.argv[1], Path(sys.argv[2])
    diretorio.mkdir(parents=True, exist_ok=True)
    controles: list[Controle] = []

    admin_sub = uuid.UUID("90000000-0000-4000-8000-000000000001")
    comum_sub = uuid.UUID("90000000-0000-4000-8000-000000000002")
    conversas = {
        89: uuid.UUID("89000000-0000-4000-8000-000000000089"),
        90: uuid.UUID("90000000-0000-4000-8000-000000000090"),
        91: uuid.UUID("91000000-0000-4000-8000-000000000091"),
    }

    with psycopg.connect(dsn) as conexao:
        admin_id = conexao.execute(
            "INSERT INTO portfolio.usuario (nome,email,perfil,auth_user_id) VALUES (%s,%s,%s,%s) RETURNING id",
            ("Administrador RNF09", "admin.rnf09@example.com", "pmo", admin_sub),
        ).fetchone()[0]
        comum_id = conexao.execute(
            "INSERT INTO portfolio.usuario (nome,email,perfil,auth_user_id) VALUES (%s,%s,%s,%s) RETURNING id",
            ("Usuário Comum RNF09", "comum.rnf09@example.com", "lider_projeto", comum_sub),
        ).fetchone()[0]
        ids_mensagem: dict[int, int] = {}
        for dias, conversa_id in conversas.items():
            instante = REFERENCIA - timedelta(days=dias)
            conexao.execute(
                "INSERT INTO auditoria.conversa (id,usuario_id,titulo,criada_em,atualizada_em) VALUES (%s,%s,%s,%s,%s)",
                (conversa_id, admin_id, f"RNF09 {dias} dias", instante, instante),
            )
            ids_mensagem[dias] = conexao.execute(
                "INSERT INTO auditoria.mensagem (conversa_id,ordem,papel,formato,conteudo,criada_em) "
                "VALUES (%s,1,'usuario','texto',%s,%s) RETURNING id",
                (conversa_id, f"Registro sintético de {dias} dias", instante),
            ).fetchone()[0]

    # Retenção e consulta administrativa direta.
    with psycopg.connect(dsn) as conexao:
        linhas = conexao.execute(
            "SELECT c.id, extract(day from (%s::timestamptz-c.criada_em))::int AS idade, m.conteudo "
            "FROM auditoria.conversa c JOIN auditoria.mensagem m ON m.conversa_id=c.id "
            "WHERE c.id = ANY(%s) ORDER BY idade",
            (REFERENCIA, list(conversas.values())),
        ).fetchall()
        idades = {linha[1] for linha in linhas}
        elegiveis = conexao.execute(
            "SELECT count(*) FROM auditoria.conversa WHERE id = ANY(%s) AND criada_em < %s::timestamptz - interval '90 days'",
            (list(conversas.values()), REFERENCIA),
        ).fetchone()[0]
    adicionar(controles, "RET-89", "Registro de 89 dias preservado", "Disponível e íntegro", str(89 in idades), 89 in idades)
    adicionar(controles, "RET-90", "Registro de 90 dias preservado", "Disponível e íntegro", str(90 in idades), 90 in idades)
    adicionar(controles, "RET-91", "Registro de 91 dias elegível para expurgo", "Elegível, remoção não obrigatória", f"elegíveis={elegiveis}", elegiveis == 1)

    lifecycle = json.loads((Path("/app/infra/minio/lifecycle.json")).read_text(encoding="utf-8"))
    regra_conversas = next((r for r in lifecycle["Rules"] if r["Filter"]["Prefix"] == "conversas/"), None)
    dias_lifecycle = regra_conversas["Expiration"]["Days"] if regra_conversas else None
    adicionar(controles, "RET-S3", "Cópia da trilha no objeto respeita retenção mínima", ">= 90 dias", f"{dias_lifecycle} dias", bool(dias_lifecycle and dias_lifecycle >= 90))

    # Superfície administrativa: a implementação atual não recebe perfil na rota.
    engine = create_engine(dsn)
    app.dependency_overrides[get_listador_auditoria] = lambda: ListarConsultas(engine)
    try:
        app.dependency_overrides[require_authenticated_user] = lambda: AuthenticatedUser(
            subject=str(admin_sub), email="admin.rnf09@example.com", name="Admin", provider="azure", domain_user_id=admin_id
        )
        with TestClient(app, raise_server_exceptions=False) as cliente:
            resposta_admin = cliente.get("/api/v1/auditoria/consultas?limit=100")
        adicionar(controles, "ACESSO-ADMIN", "Consulta pela identidade administrativa", "HTTP 200 com registros", f"HTTP {resposta_admin.status_code}", resposta_admin.status_code == 200 and len(resposta_admin.json().get("consultas", [])) >= 3)

        app.dependency_overrides[require_authenticated_user] = lambda: AuthenticatedUser(
            subject=str(comum_sub), email="comum.rnf09@example.com", name="Comum", provider="azure", domain_user_id=comum_id
        )
        with TestClient(app, raise_server_exceptions=False) as cliente:
            resposta_comum = cliente.get("/api/v1/auditoria/consultas?limit=100")
        comum_negado = resposta_comum.status_code in (403, 404)
        adicionar(controles, "ACESSO-COMUM", "Consulta da rota administrativa pela identidade comum", "Acesso negado", f"HTTP {resposta_comum.status_code}; registros={len(resposta_comum.json().get('consultas', [])) if resposta_comum.status_code == 200 else 0}", comum_negado)
    finally:
        app.dependency_overrides.clear()
        engine.dispose()

    claims_comum = json.dumps({"sub": str(comum_sub), "role": "authenticated"})
    alheias = executar_sql_comum(
        dsn, claims_comum,
        "SELECT id FROM auditoria.mensagem WHERE conversa_id = ANY(%s)",
        (list(conversas.values()),), fetch=True,
    )
    adicionar(controles, "RLS-ISOLAMENTO", "Identidade comum lê registros de outra identidade diretamente", "Nenhuma linha", f"linhas={len(alheias)}", len(alheias) == 0)

    # Imutabilidade pelo papel da aplicação.
    bloqueou, detalhe = tentativa_bloqueada(dsn, claims_comum, "UPDATE auditoria.mensagem SET conteudo='adulterado' WHERE id=%s", (ids_mensagem[89],))
    adicionar(controles, "IMUT-MSG-UPD", "Alteração de mensagem", "Bloqueada", detalhe, bloqueou)
    bloqueou, detalhe = tentativa_bloqueada(dsn, claims_comum, "DELETE FROM auditoria.mensagem WHERE id=%s", (ids_mensagem[89],))
    adicionar(controles, "IMUT-MSG-DEL", "Exclusão de mensagem", "Bloqueada", detalhe, bloqueou)
    bloqueou, detalhe = tentativa_bloqueada(dsn, claims_comum, "DELETE FROM auditoria.conversa WHERE id=%s", (conversas[89],))
    adicionar(controles, "IMUT-CONV-DEL", "Exclusão de conversa", "Bloqueada", detalhe, bloqueou)

    # Cria uma conversa própria da identidade comum para distinguir RLS de GRANT.
    conversa_comum = uuid.UUID("92000000-0000-4000-8000-000000000092")
    with psycopg.connect(dsn) as conexao:
        conexao.execute("INSERT INTO auditoria.conversa (id,usuario_id,titulo) VALUES (%s,%s,%s)", (conversa_comum, comum_id, "Original"))
        mensagem_comum = conexao.execute(
            "INSERT INTO auditoria.mensagem (conversa_id,ordem,papel,formato,conteudo) VALUES (%s,1,'usuario','texto','Feedback') RETURNING id",
            (conversa_comum,),
        ).fetchone()[0]
    bloqueou, detalhe = tentativa_bloqueada(dsn, claims_comum, "UPDATE auditoria.conversa SET titulo='Alterado' WHERE id=%s", (conversa_comum,))
    adicionar(controles, "IMUT-CONV-TITULO", "Renomeação de conversa auditável", "Bloqueada conforme plano RNF09", detalhe, bloqueou)
    bloqueou, detalhe = tentativa_bloqueada(dsn, claims_comum, "UPDATE auditoria.conversa SET arquivada_em=now() WHERE id=%s", (conversa_comum,))
    adicionar(controles, "IMUT-CONV-ARQ", "Arquivamento de conversa auditável", "Bloqueado conforme plano RNF09", detalhe, bloqueou)

    try:
        executar_sql_comum(
            dsn, claims_comum,
            "INSERT INTO auditoria.avaliacao (usuario_id,mensagem_id,polaridade) VALUES (%s,%s,'positiva')",
            (comum_id, mensagem_comum),
        )
        executar_sql_comum(
            dsn, claims_comum,
            "UPDATE auditoria.avaliacao SET polaridade='negativa' WHERE usuario_id=%s AND mensagem_id=%s",
            (comum_id, mensagem_comum),
        )
        with psycopg.connect(dsn) as conexao:
            polaridade = conexao.execute(
                "SELECT polaridade FROM auditoria.avaliacao WHERE usuario_id=%s AND mensagem_id=%s",
                (comum_id, mensagem_comum),
            ).fetchone()[0]
        feedback_ok, feedback_obs = polaridade == "negativa", f"polaridade={polaridade}"
    except psycopg.Error as erro:
        feedback_ok, feedback_obs = False, type(erro).__name__
    adicionar(controles, "FEEDBACK", "Atualização controlada de feedback", "Permitida somente nas colunas autorizadas", feedback_obs, feedback_ok)

    # Privacidade pelo caminho real do repositório de conversas.
    armazenamento = ArmazenamentoEmMemoria()
    pool = ConnectionPool(dsn, min_size=1, max_size=2, open=True)
    try:
        repositorio = ConversaRepository(pool=pool, armazenamento=armazenamento)
        conversa_segredo = str(uuid.UUID("93000000-0000-4000-8000-000000000093"))
        repositorio.registrar_turno(
            TurnoDoChat(
                conversa_id=conversa_segredo,
                usuario_id=comum_id,
                prompt=f"entrada com {MARCA_SENHA} e {MARCA_TOKEN}",
                resposta="Resposta sintética sem eco de credencial.",
                resultado="sucesso",
                modelo="modelo-sintetico-rnf09",
                tempo_processamento_ms=10,
            )
        )
    finally:
        pool.close()
    with psycopg.connect(dsn) as conexao:
        ocorrencias_mensagem = conexao.execute(
            "SELECT count(*) FROM auditoria.mensagem WHERE conteudo LIKE %s OR conteudo LIKE %s",
            (f"%{MARCA_SENHA}%", f"%{MARCA_TOKEN}%"),
        ).fetchone()[0]
        # O campo livre é ensaiado como a própria aplicação (dono do schema),
        # pois é assim que a API se conecta hoje. Comentário SQL não sanitiza.
        conexao.execute(
            "INSERT INTO auditoria.evento_plataforma (usuario_id,tipo,origem,detalhe) VALUES (%s,'erro_aplicacao','api',%s::jsonb)",
            (comum_id, json.dumps({"erro": MARCA_TOKEN})),
        )
        ocorrencias_evento = conexao.execute(
            "SELECT count(*) FROM auditoria.evento_plataforma WHERE detalhe::text LIKE %s",
            (f"%{MARCA_TOKEN}%",),
        ).fetchone()[0]
    sem_segredos = ocorrencias_mensagem == 0 and ocorrencias_evento == 0
    adicionar(controles, "PRIVACIDADE", "Senhas/tokens fictícios não persistem na auditoria", "Zero ocorrências em mensagem e evento_plataforma.detalhe", f"mensagem={ocorrencias_mensagem}; evento={ocorrencias_evento}", sem_segredos)

    # Contingência: falha controlada, captura de registro técnico e contagem de tentativas.
    falho = RepositorioFalho()
    capturador = Capturador()
    logger_chat = logging.getLogger("routes.chat")
    logger_chat.addHandler(capturador)
    nivel = logger_chat.level
    logger_chat.setLevel(logging.WARNING)
    turno_falho = TurnoDoChat(
        conversa_id=str(uuid.UUID("94000000-0000-4000-8000-000000000094")),
        usuario_id=comum_id,
        prompt="Interação sintética durante indisponibilidade.",
        resposta="Resposta concluída.",
        resultado="sucesso",
        modelo="modelo-sintetico-rnf09",
        tempo_processamento_ms=10,
    )
    try:
        registrar_turno_em_segundo_plano(falho, turno_falho)
    finally:
        logger_chat.removeHandler(capturador)
        logger_chat.setLevel(nivel)
    log_contingencia = "\n".join(capturador.linhas)
    registro_tecnico = "Falha ao gravar a trilha" in log_contingencia
    nova_tentativa = falho.tentativas > 1
    buffer_observavel = False
    alerta_observavel = False
    contingencia_ok = registro_tecnico and (buffer_observavel or nova_tentativa) and alerta_observavel
    adicionar(
        controles, "CONTINGENCIA", "Falha da persistência não perde o evento silenciosamente",
        "Registro/buffer, alerta e nova tentativa observáveis",
        f"registro_tecnico={registro_tecnico}; buffer={buffer_observavel}; alerta={alerta_observavel}; tentativas={falho.tentativas}",
        contingencia_ok,
    )
    (diretorio / "log_contingencia_sanitizado.txt").write_text(log_contingencia + "\n", encoding="utf-8")

    with (diretorio / "controles.csv").open("w", newline="", encoding="utf-8") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=list(asdict(controles[0])))
        escritor.writeheader()
        escritor.writerows(asdict(c) for c in controles)

    falhas = [c for c in controles if c.resultado == "FALHOU"]
    resultado = {
        "rnf": "RNF09",
        "resultado": "APROVADO" if not falhas else "REPROVADO",
        "commit": "0a61b353829dee491537bb2863facbe589d48cc8",
        "instante_referencia": REFERENCIA.isoformat(),
        "base_dedicada": "az1_rnf09_0a61b353_20260925",
        "controles": len(controles),
        "aprovados": len(controles) - len(falhas),
        "reprovados": len(falhas),
        "falhas": [{"id": c.id, "observado": c.observado} for c in falhas],
        "dados": "exclusivamente sintéticos",
    }
    (diretorio / "resultado.json").write_text(json.dumps(resultado, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (diretorio / "massa.json").write_text(
        json.dumps(
            {
                "identidades": {"administrativa": "admin-rnf09", "comum": "comum-rnf09"},
                "idades_dias": [89, 90, 91],
                "marcadores_credencial": ["SENHA-FICTICIA-<redacted>", "TOKEN-FICTICIO-<redacted>"],
            },
            ensure_ascii=False,
            indent=2,
        ) + "\n",
        encoding="utf-8",
    )
    linhas_falha = "\n".join(f"- `{c.id}` — {c.descricao}: {c.observado}" for c in falhas) or "- Nenhuma."
    relatorio = f"""# Execução RNF09 — auditabilidade das interações

**Resultado: {resultado['resultado']}**

- Controles executados: {len(controles)}
- Aprovados: {resultado['aprovados']}
- Reprovados: {resultado['reprovados']}
- Base: PostgreSQL real, dedicada e inicializada pelos scripts versionados
- Dados: exclusivamente sintéticos

## Falhas

{linhas_falha}

## Interpretação

O RNF09 exige aprovação de todos os controles. Assim, qualquer falha torna o
resultado global reprovado. Permissões existentes no SQL foram julgadas pelo
texto do requisito e pelo procedimento da Seção 6.3.4, não tratadas como
aprovação automática.
"""
    (diretorio / "relatorio.md").write_text(relatorio, encoding="utf-8")
    print(json.dumps(resultado, ensure_ascii=False))
    return 0 if not falhas else 1


if __name__ == "__main__":
    raise SystemExit(main())
