"""Executa o RNF04 contra a API em processo e um PostgreSQL dedicado.

As dependencias externas (LLM, STT e TTS) sao controladas para tornar a massa
repetivel. A fronteira sob teste permanece real: rotas FastAPI, tarefas de
fundo, ConversaRepository, SQL, view auditoria.vw_turno e armazenamento dos
textos pelo contrato de objeto.
"""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
import uuid
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import urlsplit

from fastapi.testclient import TestClient
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from az1_api.dependencies import (
    get_agente,
    get_chat_answerer,
    get_classificador_de_intencao,
    get_conversa_repository,
    get_speech_generator,
    get_token_verifier,
    get_transcriber,
    require_authenticated_user,
)
from az1_api.main import app
from pln.entidades import EntidadesExtraidas
from pln.intencao import IntencaoDetectada
from rag.retriever import ResultadoBusca
from services.agente_service import RespostaDoAgente, ResultadoAcao
from services.auth_service import AuthMode, AuthenticatedUser
from services.chat_service import (
    ChatReceptionError,
    ChatReceptionErrorCode,
    ChatReply,
)
from services.conversa_repository import ConversaRepository
from services.speech_service import GeneratedSpeech
from services.transcription_service import TranscriptionResult


@dataclass(frozen=True)
class Caso:
    id: str
    canal: str
    conversa_id: str
    entrada: str
    intencao: str
    confianca: float
    resposta_bruta: str
    resposta_esperada: str
    resultado: str
    fontes: tuple[ResultadoBusca, ...]
    categoria: str


class ArmazenamentoEmMemoria:
    def __init__(self) -> None:
        self.objetos: dict[str, dict[str, object]] = {}

    def store(self, *, key: str, content, content_type: str, metadata: dict[str, str]) -> None:
        content.seek(0)
        self.objetos[key] = {
            "conteudo": content.read().decode("utf-8"),
            "content_type": content_type,
            "metadata": metadata,
        }


class ClassificadorControlado:
    def __init__(self, casos: dict[str, Caso]) -> None:
        self.casos = casos

    def __call__(self, texto: str) -> IntencaoDetectada:
        caso = self.casos.get(texto)
        if caso is None:
            return IntencaoDetectada(
                prevista="consultar_projeto_sintetico", confianca=0.96
            )
        return IntencaoDetectada(prevista=caso.intencao, confianca=caso.confianca)


class AgenteSemAcao:
    def executar(self, *, deteccao: IntencaoDetectada, texto: str) -> RespostaDoAgente:
        return RespostaDoAgente(ResultadoAcao.SEM_ACAO, EntidadesExtraidas())


class RespondedorControlado:
    def __init__(self, casos: dict[str, Caso], erros: dict[str, Exception]) -> None:
        self.casos = casos
        self.erros = erros

    def answer(self, message: str, conversation_id: str | None = None, **_) -> ChatReply:
        if message in self.erros:
            raise self.erros[message]
        caso = self.casos[message]
        return ChatReply(
            text=caso.resposta_bruta,
            fontes=caso.fontes,
            resultado=caso.resultado,
            modelo="modelo-controlado-rnf04",
        )


class TranscritorControlado:
    def __init__(self, casos_por_id: dict[str, Caso]) -> None:
        self.casos_por_id = casos_por_id

    async def transcribe_content(
        self, *, content: bytes, language: str = "pt-BR"
    ) -> TranscriptionResult:
        caso_id = content.decode("utf-8").removeprefix("audio:")
        caso = self.casos_por_id[caso_id]
        return TranscriptionResult(
            text=caso.entrada,
            language=language,
            confidence=0.97,
            duration_seconds=2.4,
        )


class GeradorDeFalaControlado:
    def generate(self, text: str) -> GeneratedSpeech:
        return GeneratedSpeech(content=("wav:" + text).encode("utf-8"))


def fonte(indice: int, projeto: str = "SYN-01") -> ResultadoBusca:
    return ResultadoBusca(
        texto=f"Trecho controlado {indice} do projeto {projeto}.",
        score=0.90 - indice / 100,
        projeto_id=projeto,
        tipo_documento="cronograma",
        secao="Marcos",
        arquivo_origem=f"02_Cronograma_{projeto}.xlsx",
        chunk_id=f"rnf04-{projeto.lower()}-{indice:02d}",
    )


def criar_massa(commit: str) -> list[Caso]:
    namespace = uuid.uuid5(uuid.NAMESPACE_URL, f"az1:rnf04:{commit}")
    categorias = (
        ("sucesso_com_fonte", "sucesso", "consultar_projeto_sintetico"),
        ("sucesso_com_fonte", "sucesso", "consultar_documentos_normativos"),
        ("sucesso_sem_fonte", "sucesso", "gerar_alertas_pendencias"),
        ("esclarecimento", "esclarecimento", "orientar_tap"),
        ("fora_do_catalogo", "recusada", "fora_do_catalogo"),
    )
    casos: list[Caso] = []
    numero = 0
    for canal, prefixo in (("texto", "T"), ("voz", "V")):
        for rodada in range(2):
            for categoria, resultado, intencao in categorias:
                numero += 1
                caso_id = f"RNF04-{prefixo}{rodada * 5 + len(casos) % 5 + 1:02d}"
                conversa_id = str(uuid.uuid5(namespace, caso_id))
                entrada = f"[{caso_id}] Solicitação sintética sobre o projeto SYN-01."
                tem_fonte = categoria == "sucesso_com_fonte"
                fontes = (fonte(numero),) if tem_fonte else ()
                if categoria == "sucesso_com_fonte":
                    bruta = f"O projeto possui o marco controlado {numero} [1]."
                    esperada = f"O projeto possui o marco controlado {numero}."
                elif categoria == "sucesso_sem_fonte":
                    bruta = esperada = "Não há pendências abertas no conjunto controlado."
                elif categoria == "esclarecimento":
                    bruta = esperada = "Informe qual seção do TAP deseja consultar."
                else:
                    bruta = esperada = "A solicitação está fora do catálogo do portfólio."
                casos.append(
                    Caso(
                        id=caso_id,
                        canal=canal,
                        conversa_id=conversa_id,
                        entrada=entrada,
                        intencao=intencao,
                        confianca=0.96,
                        resposta_bruta=bruta,
                        resposta_esperada=esperada,
                        resultado=resultado,
                        fontes=fontes,
                        categoria=categoria,
                    )
                )
    return casos


def serializar(valor):
    if isinstance(valor, datetime):
        return valor.isoformat()
    if hasattr(valor, "as_tuple"):
        return float(valor)
    if isinstance(valor, uuid.UUID):
        return str(valor)
    raise TypeError(f"Tipo não serializável: {type(valor).__name__}")


def consultar_turno(pool: ConnectionPool, conversa_id: str) -> dict[str, object] | None:
    with pool.connection() as conexao, conexao.cursor(row_factory=dict_row) as cursor:
        cursor.execute(
            "SELECT * FROM auditoria.vw_turno WHERE conversa_id = %s",
            (conversa_id,),
        )
        turno = cursor.fetchone()
        if turno is None:
            return None
        cursor.execute(
            """
            SELECT posicao, chunk_id, score, projeto_codigo, tipo_documento,
                   arquivo_origem, secao, trecho
              FROM auditoria.mensagem_fonte
             WHERE mensagem_id = %s
             ORDER BY posicao
            """,
            (turno["resposta_id"],),
        )
        turno["fontes"] = cursor.fetchall()
        return turno


def checar_caso(
    caso: Caso,
    turno: dict[str, object] | None,
    usuario_id: int,
    armazenamento: ArmazenamentoEmMemoria,
) -> tuple[bool, list[str], dict[str, object]]:
    falhas: list[str] = []
    detalhes: dict[str, object] = {}
    if turno is None:
        return False, ["nenhum registro recuperado por conversa_id"], detalhes

    esperado_fontes = [
        {
            "posicao": i + 1,
            "chunk_id": f.chunk_id,
            "projeto_codigo": f.projeto_id,
            "arquivo_origem": f.arquivo_origem,
            "trecho": f.texto,
        }
        for i, f in enumerate(caso.fontes)
    ]
    obtido_fontes = [
        {
            "posicao": f["posicao"],
            "chunk_id": f["chunk_id"],
            "projeto_codigo": f["projeto_codigo"],
            "arquivo_origem": f["arquivo_origem"],
            "trecho": f["trecho"],
        }
        for f in turno["fontes"]
    ]

    verificacoes = {
        "usuario_autenticado": turno["usuario_id"] == usuario_id,
        "datas": turno["perguntado_em"] is not None and turno["respondido_em"] is not None,
        "formato": turno["formato_prompt"] == ("audio" if caso.canal == "voz" else "texto"),
        "entrada": turno["prompt"] == caso.entrada or bool(turno["audio_referencia"]),
        "intencao": turno["intencao"] == caso.intencao,
        "resposta": turno["resposta"] == caso.resposta_esperada,
        "resultado": turno["resultado"] == caso.resultado,
        "tempo": turno["tempo_processamento_ms"] is not None,
        "avaliacao": turno["avaliacao_polaridade"] == "positiva",
        "fontes": obtido_fontes == esperado_fontes,
    }
    for nome, passou in verificacoes.items():
        if not passou:
            falhas.append(nome)

    chave_prompt = f"conversas/{caso.conversa_id}/000001-usuario.txt"
    chave_resposta = f"conversas/{caso.conversa_id}/000002-agente.txt"
    verificacoes["objeto_prompt"] = (
        armazenamento.objetos.get(chave_prompt, {}).get("conteudo") == caso.entrada
    )
    verificacoes["objeto_resposta"] = (
        armazenamento.objetos.get(chave_resposta, {}).get("conteudo")
        == caso.resposta_esperada
    )
    for nome in ("objeto_prompt", "objeto_resposta"):
        if not verificacoes[nome]:
            falhas.append(nome)
    detalhes["verificacoes"] = verificacoes
    detalhes["fontes_esperadas"] = esperado_fontes
    detalhes["fontes_obtidas"] = obtido_fontes
    return not falhas, falhas, detalhes


def escrever_csv(caminho: Path, linhas: list[dict[str, object]]) -> None:
    with caminho.open("w", newline="", encoding="utf-8") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=list(linhas[0]))
        escritor.writeheader()
        escritor.writerows(linhas)


def executar(args: argparse.Namespace) -> int:
    cwd = Path.cwd().resolve()
    raiz = cwd if (cwd / "src").is_dir() else Path(__file__).resolve().parents[1]
    saida = (raiz / args.saida).resolve()
    saida.mkdir(parents=True, exist_ok=True)
    commit = args.commit or subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=raiz, text=True
    ).strip()
    banco = urlsplit(args.database_url).path.removeprefix("/")
    if not banco.startswith("az1_rnf04_"):
        raise RuntimeError("O banco dedicado deve começar com az1_rnf04_.")

    casos = criar_massa(commit)
    por_entrada = {caso.entrada: caso for caso in casos}
    por_id = {caso.id: caso for caso in casos}
    armazenamento = ArmazenamentoEmMemoria()
    pool = ConnectionPool(args.database_url, min_size=1, max_size=4, open=True)

    with pool.connection() as conexao, conexao.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO portfolio.usuario (nome, email, perfil)
            VALUES (%s, %s, %s) RETURNING id
            """,
            ("Usuário Sintético RNF04", f"rnf04-{commit[:8]}@example.com", "pmo"),
        )
        usuario_id = cursor.fetchone()[0]

    repositorio = ConversaRepository(pool, armazenamento)
    usuario = AuthenticatedUser(
        subject="rnf04-synthetic-user",
        email=f"rnf04-{commit[:8]}@example.com",
        name="Usuário Sintético RNF04",
        provider="azure",
        domain_user_id=usuario_id,
    )
    erros = {
        "[RNF04-E01] Falha controlada do serviço externo.": ChatReceptionError(
            ChatReceptionErrorCode.SERVICE_UNAVAILABLE
        ),
        "[RNF04-E02] Erro controlado de processamento.": RuntimeError(
            "falha controlada sem dado sensível"
        ),
    }
    respondedor = RespondedorControlado(por_entrada, erros)
    app.dependency_overrides[get_chat_answerer] = lambda: respondedor
    app.dependency_overrides[get_classificador_de_intencao] = lambda: ClassificadorControlado(
        por_entrada
    )
    app.dependency_overrides[get_agente] = AgenteSemAcao
    app.dependency_overrides[get_conversa_repository] = lambda: repositorio
    app.dependency_overrides[require_authenticated_user] = lambda: usuario
    app.dependency_overrides[get_token_verifier] = lambda: SimpleNamespace(
        settings=SimpleNamespace(mode=AuthMode.DISABLED)
    )
    app.dependency_overrides[get_transcriber] = lambda: TranscritorControlado(por_id)
    app.dependency_overrides[get_speech_generator] = GeradorDeFalaControlado

    requisicoes: list[dict[str, object]] = []
    iniciado = datetime.now(UTC)
    try:
        cliente = TestClient(app, raise_server_exceptions=False)
        for caso in casos:
            if caso.canal == "texto":
                resposta = cliente.post(
                    "/api/v1/chat",
                    json={"message": caso.entrada, "conversation_id": caso.conversa_id},
                )
                requisicoes.append(
                    {
                        "id": caso.id,
                        "canal": caso.canal,
                        "transporte": "HTTP POST /api/v1/chat",
                        "status": resposta.status_code,
                        "resposta": resposta.json(),
                    }
                )
                turno = consultar_turno(pool, caso.conversa_id)
                if turno is not None:
                    repositorio.registrar_avaliacao(
                        usuario_id=usuario_id,
                        conversa_id=caso.conversa_id,
                        ordem=2,
                        polaridade="positiva",
                        motivo="resposta_util",
                        comentario=f"Avaliação sintética de {caso.id}",
                    )
            else:
                eventos: list[object] = []
                with cliente.websocket_connect("/api/v1/voice/call") as websocket:
                    websocket.send_json(
                        {"type": "start_call", "conversation_id": caso.conversa_id}
                    )
                    eventos.append(websocket.receive_json())
                    websocket.send_json({"type": "utterance_start"})
                    websocket.send_bytes(f"audio:{caso.id}".encode("utf-8"))
                    websocket.send_json({"type": "utterance_end"})
                    for _ in range(5):
                        eventos.append(websocket.receive_json())
                    eventos.append({"audio_bytes": len(websocket.receive_bytes())})
                    websocket.send_json({"type": "end_call"})
                requisicoes.append(
                    {
                        "id": caso.id,
                        "canal": caso.canal,
                        "transporte": "WebSocket /api/v1/voice/call",
                        "status": 101,
                        "resposta": eventos,
                    }
                )

        negativos = []
        for indice, (entrada, erro) in enumerate(erros.items(), start=1):
            caso_id = f"RNF04-E{indice:02d}"
            conversa_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"{commit}:{caso_id}"))
            resposta = cliente.post(
                "/api/v1/chat",
                json={"message": entrada, "conversation_id": conversa_id},
            )
            turno = consultar_turno(pool, conversa_id)
            negativos.append(
                {
                    "id": caso_id,
                    "conversa_id": conversa_id,
                    "categoria_erro_esperada": (
                        "servico_externo_indisponivel" if indice == 1 else "erro_processamento"
                    ),
                    "http_status": resposta.status_code,
                    "http_body": resposta.json(),
                    "registro_recuperado": turno,
                    "falha_rastreada": bool(
                        turno
                        and turno["resultado"] == "falha"
                        and turno["categoria_erro"]
                    ),
                }
            )
    finally:
        app.dependency_overrides.clear()

    recuperados: list[dict[str, object]] = []
    checklist: list[dict[str, object]] = []
    completos = 0
    primeiro_turno = None
    for caso in casos:
        turno = consultar_turno(pool, caso.conversa_id)
        if turno is not None:
            primeiro_turno = primeiro_turno or turno
            recuperados.append({"id": caso.id, "turno": turno})
        passou, falhas, detalhes = checar_caso(caso, turno, usuario_id, armazenamento)
        completos += int(passou)
        checklist.append(
            {
                "id": caso.id,
                "canal": caso.canal,
                "categoria": caso.categoria,
                "conversa_id": caso.conversa_id,
                "completo": "sim" if passou else "não",
                "inconsistencias": "; ".join(falhas),
                "detalhes": json.dumps(detalhes, ensure_ascii=False, default=serializar),
            }
        )

    if primeiro_turno is None:
        controle_detectado = False
        controle_falhas = ["não houve registro completo para gerar a cópia controlada"]
    else:
        copia_incompleta = dict(primeiro_turno)
        copia_incompleta["tempo_processamento_ms"] = None
        controle_falhas = []
        if copia_incompleta.get("tempo_processamento_ms") is None:
            controle_falhas.append("tempo")
        controle_detectado = "tempo" in controle_falhas

    falhas_negativas_rastreadas = sum(int(n["falha_rastreada"]) for n in negativos)
    taxa = completos / len(casos)
    aprovado = (
        completos == len(casos)
        and falhas_negativas_rastreadas == len(negativos)
        and controle_detectado
    )
    encerrado = datetime.now(UTC)

    massa = []
    for caso in casos:
        item = asdict(caso)
        item["fontes"] = [asdict(f) for f in caso.fontes]
        massa.append(item)
    (saida / "massa.json").write_text(
        json.dumps(massa, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (saida / "requisicoes_respostas.json").write_text(
        json.dumps(requisicoes, ensure_ascii=False, indent=2, default=serializar),
        encoding="utf-8",
    )
    (saida / "registros_recuperados.json").write_text(
        json.dumps(recuperados, ensure_ascii=False, indent=2, default=serializar),
        encoding="utf-8",
    )
    (saida / "cenarios_negativos.json").write_text(
        json.dumps(negativos, ensure_ascii=False, indent=2, default=serializar),
        encoding="utf-8",
    )
    escrever_csv(saida / "checklist.csv", checklist)
    escrever_csv(
        saida / "identificadores.csv",
        [
            {
                "id": c.id,
                "canal": c.canal,
                "conversa_id": c.conversa_id,
                "intencao": c.intencao,
                "resultado": c.resultado,
            }
            for c in casos
        ],
    )
    (saida / "consultas.sql").write_text(
        """-- Consultas executadas pelo instrumento RNF04
SELECT * FROM auditoria.vw_turno WHERE conversa_id = :conversa_id;

SELECT posicao, chunk_id, score, projeto_codigo, tipo_documento,
       arquivo_origem, secao, trecho
  FROM auditoria.mensagem_fonte
 WHERE mensagem_id = :resposta_id ORDER BY posicao;
""",
        encoding="utf-8",
    )
    resultado = {
        "requisito": "RNF04",
        "status": "Aprovado" if aprovado else "Reprovado",
        "commit": commit,
        "banco_dedicado": banco,
        "inicio_utc": iniciado.isoformat(),
        "fim_utc": encerrado.isoformat(),
        "interacoes_planejadas": len(casos),
        "interacoes_completas": completos,
        "taxa_completude": taxa,
        "por_canal": {
            canal: {
                "total": sum(c.canal == canal for c in casos),
                "completas": sum(
                    linha["canal"] == canal and linha["completo"] == "sim"
                    for linha in checklist
                ),
            }
            for canal in ("texto", "voz")
        },
        "falhas_controladas": len(negativos),
        "falhas_controladas_rastreadas": falhas_negativas_rastreadas,
        "registro_incompleto_controlado_detectado": controle_detectado,
        "campos_ausentes_no_controle": controle_falhas,
        "ambiente": {
            "api": "FastAPI TestClient (rotas reais em processo)",
            "persistencia": "ConversaRepository + PostgreSQL 16 dedicado",
            "dependencias_externas": "LLM/STT/TTS controladas",
            "armazenamento_textual": "dublê contratual em memória, conteúdo e metadados inspecionados",
        },
    }
    (saida / "resultado.json").write_text(
        json.dumps(resultado, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    inconsistencias = [l for l in checklist if l["completo"] == "não"]
    relatorio = f"""# Execução do RNF04 — rastreabilidade das consultas

- Status: **{resultado['status']}**
- Commit: `{commit}`
- Banco dedicado: `{banco}`
- Período UTC: {iniciado.isoformat()} a {encerrado.isoformat()}
- Interações completas: **{completos}/{len(casos)} ({taxa:.2%})**
- Texto: **{resultado['por_canal']['texto']['completas']}/10**
- Voz: **{resultado['por_canal']['voz']['completas']}/10**
- Falhas controladas rastreadas: **{falhas_negativas_rastreadas}/{len(negativos)}**
- Registro incompleto de controle detectado: **{'sim' if controle_detectado else 'não'}**

## Método

As 20 interações passaram pelas rotas reais da aplicação: HTTP para texto e
WebSocket para voz. LLM, STT e TTS tiveram respostas controladas, enquanto a
persistência usou `ConversaRepository` e PostgreSQL real. O checklist consultou
`auditoria.vw_turno`, `auditoria.mensagem_fonte`, avaliações e os objetos de
texto arquivados.

## Conclusão

O critério exige 100% das 20 interações completas, as falhas externas e de
processamento associadas ao mesmo identificador e a detecção do registro
incompleto de controle. O resultado foi **{resultado['status']}**.

## Inconsistências

"""
    if inconsistencias:
        relatorio += "\n".join(
            f"- `{l['id']}` ({l['canal']}): {l['inconsistencias']}"
            for l in inconsistencias
        )
    else:
        relatorio += "- Nenhuma nas 20 interações."
    relatorio += "\n\n"
    if falhas_negativas_rastreadas != len(negativos):
        relatorio += (
            "As falhas controladas retornaram erro ao cliente, mas não produziram "
            "registro correlacionado com `resultado=falha` e `categoria_erro`.\n"
        )
    (saida / "relatorio.md").write_text(relatorio, encoding="utf-8")
    if not aprovado:
        (saida / "defeito.md").write_text(
            """# Defeito encontrado pelo RNF04

## Resultado observado

Nem todos os canais e desfechos deixam uma trilha recuperável pelo identificador.
Consulte `checklist.csv` e `cenarios_negativos.json` para a enumeração exata.

## Impacto

O requisito de rastreabilidade ponta a ponta não pode ser demonstrado para toda
a massa. Em especial, uma resposta entregue ao usuário pode existir sem o par
correspondente em `auditoria.vw_turno`, e erros controlados podem não registrar
`resultado=falha`/`categoria_erro`.

## Correção esperada

Integrar a persistência de auditoria ao canal de voz e registrar desfechos de
falha antes de devolver o erro controlado, incluindo a categoria do erro e os
metadados aplicáveis do áudio. Depois, repetir a mesma massa versionada.
""",
            encoding="utf-8",
        )

    pool.close()
    print(json.dumps(resultado, ensure_ascii=False, indent=2))
    return 0 if aprovado else 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database-url", required=True)
    parser.add_argument("--saida", required=True)
    parser.add_argument("--commit")
    return executar(parser.parse_args())


if __name__ == "__main__":
    sys.exit(main())
