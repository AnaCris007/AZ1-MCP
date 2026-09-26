#!/usr/bin/env python3
"""Executa CT-RNF07-P/N e preserva evidencias incrementais.

A janela oficial descrita em docs/Projeto.md e de quatro horas. Este executor
aceita uma janela reduzida, mas a registra como desvio de escopo e nunca a
apresenta como equivalente a campanha oficial.
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from unittest import mock
from zoneinfo import ZoneInfo


FUSO = ZoneInfo("America/Sao_Paulo")
RAIZ = Path(__file__).resolve().parents[1]
SAIDA_PADRAO = RAIZ / "resultados/testes-rnf/0a61b353/rnf07"
CAMPANHA = "0a61b353"
JANELA_OFICIAL_MINUTOS = 240
INTERVALO_OFICIAL_SEGUNDOS = 60
LIMITE_SEGUNDOS = 2.0


def agora() -> datetime:
    return datetime.now(FUSO)


def gravar_json(caminho: Path, dados: Any) -> None:
    temporario = caminho.with_suffix(caminho.suffix + ".tmp")
    temporario.write_text(
        json.dumps(dados, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporario.replace(caminho)


def commit_atual() -> str:
    resultado = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=RAIZ,
        capture_output=True,
        text=True,
        check=False,
    )
    return resultado.stdout.strip() or "nao_identificado"


def sondar(url: str, timeout: float = LIMITE_SEGUNDOS) -> dict[str, Any]:
    inicio_local = agora()
    inicio_mono = time.monotonic()
    status: int | None = None
    corpo = ""
    erro = ""
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resposta:  # noqa: S310 - URL local informada pelo executor
            status = resposta.status
            corpo = resposta.read(4096).decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        status = exc.code
        corpo = exc.read(4096).decode("utf-8", errors="replace")
        erro = f"HTTPError: {exc.reason}"
    except Exception as exc:  # noqa: BLE001 - a indisponibilidade e o dado medido
        erro = f"{type(exc).__name__}: {exc}"
    duracao = time.monotonic() - inicio_mono
    fim_local = agora()
    return {
        "inicio": inicio_local.isoformat(),
        "fim": fim_local.isoformat(),
        "duracao_segundos": round(duracao, 6),
        "status_http": status,
        "corpo": corpo,
        "erro": erro,
        "sucesso": status == 200 and duracao <= LIMITE_SEGUNDOS,
    }


def gravar_verificacoes(caminho: Path, verificacoes: list[dict[str, Any]]) -> None:
    campos = [
        "numero",
        "inicio",
        "fim",
        "duracao_segundos",
        "status_http",
        "corpo",
        "erro",
        "sucesso",
        "elegivel",
        "justificativa_exclusao",
        "ready_status_auxiliar",
        "ready_duracao_segundos_auxiliar",
    ]
    temporario = caminho.with_suffix(".csv.tmp")
    with temporario.open("w", encoding="utf-8", newline="") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=campos)
        escritor.writeheader()
        escritor.writerows(verificacoes)
    temporario.replace(caminho)


@contextmanager
def capturar_logs():
    registros: list[str] = []

    class Capturador(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            registros.append(self.format(record))

    handler = Capturador(logging.WARNING)
    raiz = logging.getLogger()
    raiz.addHandler(handler)
    try:
        yield registros
    finally:
        raiz.removeHandler(handler)


def executar_cenarios_controlados() -> dict[str, Any]:
    """Exercita falha de banco em memoria, sem tocar o banco configurado."""
    sys.path.insert(0, str(RAIZ / "src"))
    from fastapi.testclient import TestClient

    from az1_api.dependencies import get_connection_pool
    from az1_api.main import app

    pool_saudavel = mock.MagicMock()
    cursor = pool_saudavel.connection.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value
    cursor.fetchone.return_value = (1,)
    pool_falho = mock.MagicMock()
    pool_falho.connection.side_effect = OSError("conexao recusada no cenario controlado RNF07")

    eventos: list[dict[str, Any]] = []
    with TestClient(app, raise_server_exceptions=False) as cliente:
        app.dependency_overrides[get_connection_pool] = lambda: pool_saudavel
        antes = cliente.get("/health/ready")
        eventos.append({"etapa": "banco_antes", "endpoint": "/health/ready", "status": antes.status_code, "corpo": antes.json()})

        app.dependency_overrides[get_connection_pool] = lambda: pool_falho
        with capturar_logs() as logs_falha:
            falha_ready = cliente.get("/health/ready")
            falha_health = cliente.get("/health")
        eventos.append({"etapa": "banco_indisponivel", "endpoint": "/health/ready", "status": falha_ready.status_code, "corpo": falha_ready.json()})
        eventos.append({"etapa": "banco_indisponivel", "endpoint": "/health", "status": falha_health.status_code, "corpo": falha_health.json()})

        app.dependency_overrides[get_connection_pool] = lambda: pool_saudavel
        depois = cliente.get("/health/ready")
        eventos.append({"etapa": "banco_recuperado", "endpoint": "/health/ready", "status": depois.status_code, "corpo": depois.json()})
    app.dependency_overrides.clear()

    banco = {
        "metodo": "substituicao controlada do pool no processo de teste; banco externo nao foi interrompido",
        "antes_200": antes.status_code == 200,
        "falha_ready_503": falha_ready.status_code == 503,
        "health_oficial_na_falha_503": falha_health.status_code == 503,
        "health_oficial_observado": falha_health.status_code,
        "recuperacao_200": depois.status_code == 200,
        "registro_tecnico_observado": bool(logs_falha),
        "registros_capturados": logs_falha,
        "alerta_observado": False,
        "resultado_contrato_planejado": all(
            [
                antes.status_code == 200,
                falha_health.status_code == 503,
                depois.status_code == 200,
                bool(logs_falha),
                False,
            ]
        ),
    }
    aplicacao = {
        "executavel": False,
        "motivo": (
            "A versao avaliada nao expoe estado interno de saude nem mecanismo controlado "
            "que torne GET /health 503 mantendo o servidor HTTP acessivel."
        ),
        "resultado_contrato_planejado": False,
    }
    return {
        "executado_em": agora().isoformat(),
        "aplicacao_internamente_nao_saudavel": aplicacao,
        "banco_indisponivel": banco,
        "eventos": eventos,
        "observacao": (
            "GET /health e uma verificacao rasa nesta versao; /health/ready detectou a falha "
            "do banco, mas esse endpoint auxiliar nao substitui o contrato oficial planejado."
        ),
    }


def montar_resultado(
    *,
    inicio: datetime,
    fim: datetime,
    args: argparse.Namespace,
    verificacoes: list[dict[str, Any]],
    controlados: dict[str, Any],
) -> dict[str, Any]:
    elegiveis = [linha for linha in verificacoes if linha["elegivel"]]
    sucessos = sum(1 for linha in elegiveis if linha["sucesso"])
    disponibilidade = (100.0 * sucessos / len(elegiveis)) if elegiveis else 0.0
    positivo_aprovado = bool(elegiveis) and disponibilidade >= 99.0
    negativo_aprovado = bool(
        controlados["aplicacao_internamente_nao_saudavel"]["resultado_contrato_planejado"]
        and controlados["banco_indisponivel"]["resultado_contrato_planejado"]
    )
    concluido = len(verificacoes) == args.samples
    return {
        "requisito": "RNF07",
        "campanha": CAMPANHA,
        "status_execucao": "CONCLUIDA" if concluido else "INTERROMPIDA",
        "resultado_global": "APROVADO" if concluido and positivo_aprovado and negativo_aprovado else "REPROVADO",
        "inicio": inicio.isoformat(),
        "fim": fim.isoformat(),
        "janela_planejada_minutos": JANELA_OFICIAL_MINUTOS,
        "janela_executada_minutos": args.duration_minutes,
        "evidencia_reduzida": args.duration_minutes < JANELA_OFICIAL_MINUTOS,
        "intervalo_segundos": args.interval_seconds,
        "amostras_planejadas_nesta_execucao": args.samples,
        "verificacoes_realizadas": len(verificacoes),
        "verificacoes_elegiveis": len(elegiveis),
        "verificacoes_bem_sucedidas": sucessos,
        "disponibilidade_percentual": round(disponibilidade, 4),
        "ct_rnf07_p": "APROVADO" if positivo_aprovado else "REPROVADO",
        "ct_rnf07_n": "APROVADO" if negativo_aprovado else "REPROVADO",
        "criterio": ">=99% de GET /health HTTP 200 em ate 2 s; falhas controladas devem gerar 503, registro, alerta e recuperar para 200",
        "ressalva": (
            "A janela reduzida de uma hora nao comprova o criterio oficial de quatro horas "
            "e limita a conclusao a esta execucao academica."
            if args.duration_minutes < JANELA_OFICIAL_MINUTOS
            else "Nenhuma reducao da janela oficial."
        ),
    }


def gravar_relatorio(saida: Path, resultado: dict[str, Any], controlados: dict[str, Any]) -> None:
    banco = controlados["banco_indisponivel"]
    aplicacao = controlados["aplicacao_internamente_nao_saudavel"]
    texto = f"""# Execucao do RNF07 — disponibilidade da solucao

## Resultado

**{resultado['resultado_global']}** na versao e no ambiente avaliados.

- CT-RNF07-P: **{resultado['ct_rnf07_p']}** — {resultado['verificacoes_bem_sucedidas']}/{resultado['verificacoes_elegiveis']} verificacoes elegiveis bem-sucedidas ({resultado['disponibilidade_percentual']:.4f}%).
- CT-RNF07-N: **{resultado['ct_rnf07_n']}**.
- Janela executada: {resultado['janela_executada_minutos']} minutos, ante 240 minutos do plano original.
- Intervalo: {resultado['intervalo_segundos']} segundos; amostras realizadas: {resultado['verificacoes_realizadas']}.

## Desvio de escopo

Esta rodada foi deliberadamente reduzida de quatro horas para uma hora por restricao de tempo. Ela preserva o intervalo de uma verificacao por minuto, mas nao e equivalente as 240 verificacoes do criterio oficial. Nao foram preenchidas artificialmente amostras ausentes.

## Cenarios controlados

A indisponibilidade do banco foi simulada pela substituicao do pool somente dentro do processo de teste, sem interromper ou alterar o banco externo configurado. `/health/ready` retornou 503 durante a falha e 200 depois da recuperacao. O endpoint contratual `/health`, entretanto, retornou HTTP {banco['health_oficial_observado']} durante a falha do banco. Registro tecnico observado: {str(banco['registro_tecnico_observado']).lower()}; alerta observado: {str(banco['alerta_observado']).lower()}.

O cenario de aplicacao internamente nao saudavel nao foi executavel: {aplicacao['motivo']} Esse impedimento conta como nao atendimento do caso negativo, e nao como aprovacao presumida.

## Conclusao

{resultado['ressalva']} O resultado global exige simultaneamente a disponibilidade natural e o comportamento previsto para as falhas controladas.

## Evidencias

- `verificacoes.csv`: cada chamada, duracao, status, corpo e elegibilidade.
- `cenarios_controlados.json`: eventos e observacoes dos testes negativos.
- `ambiente.json`: versao, configuracao e horarios.
- `resultado.json`: calculo consolidado e veredito.
- `monitor.log`: progresso do executor.
"""
    (saida / "relatorio.md").write_text(texto, encoding="utf-8")


def executar(args: argparse.Namespace) -> int:
    saida = args.output_dir.resolve()
    saida.mkdir(parents=True, exist_ok=True)
    inicio = agora()
    fim_previsto = inicio + timedelta(minutes=args.duration_minutes)
    ambiente = {
        "requisito": "RNF07",
        "campanha": CAMPANHA,
        "commit": commit_atual(),
        "base_url": args.base_url,
        "endpoint_oficial": "/health",
        "endpoint_auxiliar": "/health/ready",
        "fuso_horario": str(FUSO),
        "inicio": inicio.isoformat(),
        "fim_previsto": fim_previsto.isoformat(),
        "janela_planejada_minutos": JANELA_OFICIAL_MINUTOS,
        "janela_executada_minutos": args.duration_minutes,
        "intervalo_planejado_segundos": INTERVALO_OFICIAL_SEGUNDOS,
        "intervalo_executado_segundos": args.interval_seconds,
        "amostras": args.samples,
        "limite_por_verificacao_segundos": LIMITE_SEGUNDOS,
        "manutencoes_previamente_comunicadas": [],
        "evidencia_reduzida": args.duration_minutes < JANELA_OFICIAL_MINUTOS,
    }
    gravar_json(saida / "ambiente.json", ambiente)
    controlados = executar_cenarios_controlados()
    gravar_json(saida / "cenarios_controlados.json", controlados)

    verificacoes: list[dict[str, Any]] = []
    inicio_mono = time.monotonic()
    print(f"RNF07 iniciado em {inicio.isoformat()}; termino previsto {fim_previsto.isoformat()}", flush=True)
    try:
        for numero in range(1, args.samples + 1):
            alvo = inicio_mono + (numero - 1) * args.interval_seconds
            espera = alvo - time.monotonic()
            if espera > 0:
                time.sleep(espera)
            principal = sondar(f"{args.base_url.rstrip('/')}/health")
            auxiliar = sondar(f"{args.base_url.rstrip('/')}/health/ready")
            linha = {
                "numero": numero,
                **principal,
                "elegivel": True,
                "justificativa_exclusao": "",
                "ready_status_auxiliar": auxiliar["status_http"],
                "ready_duracao_segundos_auxiliar": auxiliar["duracao_segundos"],
            }
            verificacoes.append(linha)
            gravar_verificacoes(saida / "verificacoes.csv", verificacoes)
            andamento = {
                "status_execucao": "EM_ANDAMENTO",
                "inicio": inicio.isoformat(),
                "fim_previsto": fim_previsto.isoformat(),
                "verificacoes_realizadas": len(verificacoes),
                "amostras_planejadas": args.samples,
                "ultima_verificacao": linha,
            }
            gravar_json(saida / "resultado.json", andamento)
            print(
                f"[{numero:02d}/{args.samples:02d}] /health={principal['status_http']} "
                f"{principal['duracao_segundos']:.4f}s sucesso={principal['sucesso']} "
                f"/health/ready={auxiliar['status_http']}",
                flush=True,
            )
        restante = inicio_mono + args.duration_minutes * 60 - time.monotonic()
        if restante > 0:
            time.sleep(restante)
    except KeyboardInterrupt:
        print("Execucao interrompida", flush=True)

    fim = agora()
    resultado = montar_resultado(
        inicio=inicio,
        fim=fim,
        args=args,
        verificacoes=verificacoes,
        controlados=controlados,
    )
    gravar_json(saida / "resultado.json", resultado)
    gravar_relatorio(saida, resultado, controlados)
    ambiente["fim_real"] = fim.isoformat()
    gravar_json(saida / "ambiente.json", ambiente)
    processo_path = saida / "processo.json"
    if processo_path.exists():
        processo = json.loads(processo_path.read_text(encoding="utf-8"))
        processo.update(
            {
                "status": "CONCLUIDO" if resultado["status_execucao"] == "CONCLUIDA" else "INTERROMPIDO",
                "fim_real": fim.isoformat(),
                "resultado_global": resultado["resultado_global"],
            }
        )
        gravar_json(processo_path, processo)
    print(f"RNF07 concluido: {resultado['resultado_global']}", flush=True)
    return 0 if resultado["status_execucao"] == "CONCLUIDA" else 1


def iniciar_destacado(args: argparse.Namespace) -> int:
    saida = args.output_dir.resolve()
    saida.mkdir(parents=True, exist_ok=True)
    log = (saida / "monitor.log").open("a", encoding="utf-8")
    comando = [
        sys.executable,
        str(Path(__file__).resolve()),
        "--run",
        "--base-url",
        args.base_url,
        "--duration-minutes",
        str(args.duration_minutes),
        "--interval-seconds",
        str(args.interval_seconds),
        "--samples",
        str(args.samples),
        "--output-dir",
        str(saida),
    ]
    processo = subprocess.Popen(  # noqa: S603 - argumentos internos, sem shell
        comando,
        cwd=RAIZ,
        stdout=log,
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )
    log.close()
    inicio = agora()
    dados = {
        "pid": processo.pid,
        "status": "INICIADO",
        "inicio": inicio.isoformat(),
        "fim_previsto": (inicio + timedelta(minutes=args.duration_minutes)).isoformat(),
        "comando": comando,
    }
    gravar_json(saida / "processo.json", dados)
    print(json.dumps(dados, ensure_ascii=False))
    return 0


def analisar_argumentos() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", action="store_true", help="executa no processo atual")
    parser.add_argument("--base-url", default="http://127.0.0.1:8010")
    parser.add_argument("--duration-minutes", type=float, default=60.0)
    parser.add_argument("--interval-seconds", type=float, default=60.0)
    parser.add_argument("--samples", type=int)
    parser.add_argument("--output-dir", type=Path, default=SAIDA_PADRAO)
    args = parser.parse_args()
    if args.duration_minutes <= 0 or args.interval_seconds <= 0:
        parser.error("duracao e intervalo devem ser positivos")
    if args.samples is None:
        args.samples = max(1, int(args.duration_minutes * 60 / args.interval_seconds))
    if args.samples <= 0:
        parser.error("samples deve ser positivo")
    return args


if __name__ == "__main__":
    argumentos = analisar_argumentos()
    raise SystemExit(executar(argumentos) if argumentos.run else iniciar_destacado(argumentos))
