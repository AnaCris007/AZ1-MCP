"""Executa CT-RNF06-P/N pela API e preserva as evidencias brutas.

Uso:
    python scripts/executar_rnf06.py \
        --base-url http://127.0.0.1:8010 \
        --audios assets/data/audios \
        --saida resultados/testes-rnf/<commit>/rnf06

O script envia os arquivos originais ao mesmo contrato HTTP consumido pelo
frontend. Ele nao carrega o .env e nunca grava credenciais nas evidencias.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import mimetypes
import re
import subprocess
import sys
import unicodedata
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

import httpx

REFERENCIAS = {
    ("L01", "F01"): "O projeto SYN-01 alcançou sessenta e oito por cento de avanço físico neste mês.",
    ("L01", "F02"): "O marco de energização da subestação foi reprogramado para quinze de outubro.",
    ("L01", "F03"): "O principal risco da obra é o atraso na entrega dos equipamentos de sinalização.",
    ("L02", "F01"): "A equipe concluiu a inspeção da via permanente entre as estações Central e Norte.",
    ("L02", "F02"): "O cronograma prevê o início dos testes do material rodante na próxima quinzena.",
    ("L02", "F03"): "A pendência de licenciamento ambiental continua sob responsabilidade da gerência técnica.",
    ("L03", "F01"): "O Termo de Abertura do Projeto precisa informar objetivo, escopo, prazo e patrocinador.",
    ("L03", "F02"): "O mapa de benefícios relaciona a redução do tempo de viagem à modernização da linha.",
    ("L03", "F03"): "A ventilação do túnel permanece em estado crítico devido à falha do fornecedor.",
    ("L04", "F01"): "O avanço previsto era setenta e cinco por cento, mas o avanço realizado chegou a sessenta e nove por cento.",
    ("L04", "F02"): "A entrega do sistema de portas de plataforma depende da aprovação do projeto executivo.",
    ("L04", "F03"): "O relatório mensal registrou dois riscos altos e três pendências vencidas.",
    ("L05", "F01"): "O comitê aprovou a mudança de escopo para incluir a reforma da estação.",
    ("L05", "F02"): "A instalação dos equipamentos de telecomunicações deve terminar até trinta de novembro.",
    ("L05", "F03"): "A fonte do indicador é o boletim de medição validado pela fiscalização do contrato.",
}

PADRAO_ARQUIVO = re.compile(r"^(L\d{2})_(F\d{2})_(LIMPO|RUIDO)$")
META_WER = 0.15


@dataclass(frozen=True)
class DistanciaPalavras:
    substituicoes: int
    exclusoes: int
    insercoes: int
    palavras_referencia: int

    @property
    def erros(self) -> int:
        return self.substituicoes + self.exclusoes + self.insercoes

    @property
    def wer(self) -> float:
        return self.erros / self.palavras_referencia if self.palavras_referencia else 0.0


def normalizar_nome(texto: str) -> str:
    sem_acentos = "".join(
        caractere
        for caractere in unicodedata.normalize("NFKD", texto)
        if not unicodedata.combining(caractere)
    )
    return sem_acentos.upper()


def identificar_audio(caminho: Path) -> tuple[str, str, str]:
    correspondencia = PADRAO_ARQUIVO.fullmatch(normalizar_nome(caminho.stem))
    if not correspondencia:
        raise ValueError(f"nome de audio fora do padrao: {caminho.name}")
    locutor, frase, condicao = correspondencia.groups()
    return locutor, frase, "limpa" if condicao == "LIMPO" else "ruido"


def normalizar_texto(texto: str) -> list[str]:
    texto = unicodedata.normalize("NFKC", texto).casefold()
    texto = re.sub(r"[^\w]+", " ", texto, flags=re.UNICODE)
    return texto.split()


def distancia_palavras(referencia: str, hipotese: str) -> DistanciaPalavras:
    ref = normalizar_texto(referencia)
    hip = normalizar_texto(hipotese)
    # Cada celula guarda (custo, S, D, I). Em empate, a ordem abaixo prioriza
    # correspondencia/substituicao, depois exclusao e por fim insercao.
    tabela: list[list[tuple[int, int, int, int]]] = [
        [(0, 0, 0, 0) for _ in range(len(hip) + 1)] for _ in range(len(ref) + 1)
    ]
    for i in range(1, len(ref) + 1):
        tabela[i][0] = (i, 0, i, 0)
    for j in range(1, len(hip) + 1):
        tabela[0][j] = (j, 0, 0, j)

    for i in range(1, len(ref) + 1):
        for j in range(1, len(hip) + 1):
            if ref[i - 1] == hip[j - 1]:
                tabela[i][j] = tabela[i - 1][j - 1]
                continue
            diagonal = tabela[i - 1][j - 1]
            acima = tabela[i - 1][j]
            esquerda = tabela[i][j - 1]
            candidatos = [
                (diagonal[0] + 1, diagonal[1] + 1, diagonal[2], diagonal[3]),
                (acima[0] + 1, acima[1], acima[2] + 1, acima[3]),
                (esquerda[0] + 1, esquerda[1], esquerda[2], esquerda[3] + 1),
            ]
            tabela[i][j] = min(candidatos, key=lambda item: item[0])

    _, substituicoes, exclusoes, insercoes = tabela[-1][-1]
    return DistanciaPalavras(substituicoes, exclusoes, insercoes, len(ref))


def sha256(caminho: Path) -> str:
    resumo = hashlib.sha256()
    with caminho.open("rb") as arquivo:
        for bloco in iter(lambda: arquivo.read(1024 * 1024), b""):
            resumo.update(bloco)
    return resumo.hexdigest()


def commit_atual(raiz: Path) -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=raiz, text=True
    ).strip()


def executar(args: argparse.Namespace) -> int:
    raiz = Path(__file__).resolve().parents[1]
    pasta_audios = (raiz / args.audios).resolve()
    pasta_saida = (raiz / args.saida).resolve()
    pasta_saida.mkdir(parents=True, exist_ok=True)

    audios = sorted(pasta_audios.glob("*.m4a"), key=lambda p: normalizar_nome(p.name))
    if len(audios) != 30:
        raise RuntimeError(f"esperados 30 audios .m4a; encontrados {len(audios)}")

    identificados: list[tuple[Path, str, str, str]] = []
    vistos: set[tuple[str, str, str]] = set()
    for caminho in audios:
        locutor, frase, condicao = identificar_audio(caminho)
        chave = (locutor, frase, condicao)
        if chave in vistos:
            raise RuntimeError(f"audio duplicado para {chave}: {caminho.name}")
        if (locutor, frase) not in REFERENCIAS:
            raise RuntimeError(f"referencia ausente para {locutor}/{frase}")
        vistos.add(chave)
        identificados.append((caminho, locutor, frase, condicao))

    esperado = {
        (locutor, frase, condicao)
        for locutor, frase in REFERENCIAS
        for condicao in ("limpa", "ruido")
    }
    if vistos != esperado:
        faltantes = sorted(esperado - vistos)
        raise RuntimeError(f"combinacoes de audio ausentes: {faltantes}")

    iniciado = datetime.now(UTC)
    registros: list[dict[str, object]] = []
    cabecalhos = {"Authorization": f"Bearer {args.token}"} if args.token else {}

    with httpx.Client(base_url=args.base_url, headers=cabecalhos, timeout=90.0) as cliente:
        saude = cliente.get("/health")
        saude.raise_for_status()
        for indice, (caminho, locutor, frase, condicao) in enumerate(identificados, start=1):
            referencia = REFERENCIAS[(locutor, frase)]
            registro: dict[str, object] = {
                "id": f"RNF06_{indice:03d}",
                "arquivo": caminho.name,
                "locutor": locutor,
                "frase": frase,
                "condicao": condicao,
                "sha256": sha256(caminho),
                "bytes": caminho.stat().st_size,
                "referencia": referencia,
                "status": "Erro",
                "audio_id": "",
                "transcricao": "",
                "idioma": "",
                "confianca": None,
                "duracao_s": None,
                "substituicoes": None,
                "exclusoes": None,
                "insercoes": None,
                "palavras_referencia": len(normalizar_texto(referencia)),
                "wer": None,
                "erro": "",
            }
            try:
                tipo = mimetypes.guess_type(caminho.name)[0] or "audio/mp4"
                with caminho.open("rb") as arquivo:
                    upload = cliente.post(
                        "/api/v1/audio",
                        files={"audio": (caminho.name, arquivo, tipo)},
                    )
                if upload.status_code != 201:
                    registro["erro"] = f"upload HTTP {upload.status_code}: {upload.text[:500]}"
                    registros.append(registro)
                    print(f"[{indice:02d}/30] {caminho.name}: erro no upload", flush=True)
                    continue
                audio_id = upload.json()["id"]
                registro["audio_id"] = audio_id

                resposta = cliente.post(
                    f"/api/v1/audio/{audio_id}/transcribe",
                    params={"language": "pt-BR"},
                )
                if resposta.status_code != 200:
                    registro["erro"] = (
                        f"transcricao HTTP {resposta.status_code}: {resposta.text[:500]}"
                    )
                    registros.append(registro)
                    print(f"[{indice:02d}/30] {caminho.name}: erro na transcricao", flush=True)
                    continue

                corpo = resposta.json()
                transcricao = str(corpo.get("text") or "")
                distancia = distancia_palavras(referencia, transcricao)
                registro.update(
                    {
                        "status": "Executado",
                        "transcricao": transcricao,
                        "idioma": corpo.get("language") or "",
                        "confianca": corpo.get("confidence"),
                        "duracao_s": corpo.get("duration_seconds"),
                        "substituicoes": distancia.substituicoes,
                        "exclusoes": distancia.exclusoes,
                        "insercoes": distancia.insercoes,
                        "wer": distancia.wer,
                    }
                )
                print(
                    f"[{indice:02d}/30] {caminho.name}: WER {distancia.wer:.1%}",
                    flush=True,
                )
            except (httpx.HTTPError, KeyError, ValueError, TypeError) as erro:
                registro["erro"] = f"{type(erro).__name__}: {erro}"
                print(f"[{indice:02d}/30] {caminho.name}: {registro['erro']}", flush=True)
            registros.append(registro)

    executados = [r for r in registros if r["status"] == "Executado"]
    totais = DistanciaPalavras(
        substituicoes=sum(int(r["substituicoes"]) for r in executados),
        exclusoes=sum(int(r["exclusoes"]) for r in executados),
        insercoes=sum(int(r["insercoes"]) for r in executados),
        palavras_referencia=sum(int(r["palavras_referencia"]) for r in executados),
    )
    por_condicao: dict[str, DistanciaPalavras] = {}
    for condicao in ("limpa", "ruido"):
        grupo = [r for r in executados if r["condicao"] == condicao]
        por_condicao[condicao] = DistanciaPalavras(
            substituicoes=sum(int(r["substituicoes"]) for r in grupo),
            exclusoes=sum(int(r["exclusoes"]) for r in grupo),
            insercoes=sum(int(r["insercoes"]) for r in grupo),
            palavras_referencia=sum(int(r["palavras_referencia"]) for r in grupo),
        )

    finalizado = datetime.now(UTC)
    resumo = {
        "caso": "CT-RNF06-P/N",
        "commit": commit_atual(raiz),
        "base_url": args.base_url,
        "iniciado_em_utc": iniciado.isoformat(),
        "finalizado_em_utc": finalizado.isoformat(),
        "modelo": "Deepgram nova-3",
        "idioma": "pt-BR",
        "normalizacao": "Unicode NFKC, minusculas, pontuacao removida e espacos normalizados",
        "meta_wer": META_WER,
        "audios_previstos": 30,
        "audios_executados": len(executados),
        "audios_com_erro": len(registros) - len(executados),
        "totais": asdict(totais) | {"erros": totais.erros, "wer": totais.wer},
        "por_condicao": {
            chave: asdict(valor) | {"erros": valor.erros, "wer": valor.wer}
            for chave, valor in por_condicao.items()
        },
        "resultado": (
            "Aprovado"
            if len(executados) == 30 and totais.wer <= META_WER
            else "Reprovado" if len(executados) == 30 else "Bloqueado"
        ),
    }

    campos = list(registros[0])
    with (pasta_saida / "transcricoes.csv").open("w", encoding="utf-8", newline="") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=campos)
        escritor.writeheader()
        escritor.writerows(registros)
    (pasta_saida / "resultado.json").write_text(
        json.dumps({"resumo": resumo, "registros": registros}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    linhas = [
        "# Execucao do RNF06",
        "",
        f"- Estado: **{resumo['resultado']}**",
        f"- Audios executados: {len(executados)}/30",
        f"- WER geral: **{totais.wer:.2%}** (meta: <= {META_WER:.0%})",
        f"- WER fala limpa: **{por_condicao['limpa'].wer:.2%}**",
        f"- WER com ruido: **{por_condicao['ruido'].wer:.2%}**",
        "",
        "O WER foi calculado sobre a soma de substituicoes, exclusoes e insercoes do corpus,",
        "dividida pelo total de palavras das referencias. Resultados com falha de transporte",
        "ou transcricao nao entram no denominador e impedem a aprovacao do caso.",
    ]
    (pasta_saida / "relatorio.md").write_text("\n".join(linhas) + "\n", encoding="utf-8")

    print(json.dumps(resumo, ensure_ascii=False, indent=2))
    return 0 if resumo["resultado"] == "Aprovado" else 1


def parser() -> argparse.ArgumentParser:
    analisador = argparse.ArgumentParser(description="Executa os 30 audios do RNF06 pela API.")
    analisador.add_argument("--base-url", default="http://127.0.0.1:8010")
    analisador.add_argument("--audios", type=Path, default=Path("assets/data/audios"))
    analisador.add_argument("--saida", type=Path, required=True)
    analisador.add_argument("--token", default="")
    return analisador


if __name__ == "__main__":
    try:
        raise SystemExit(executar(parser().parse_args()))
    except Exception as erro:  # noqa: BLE001 - falha do instrumento deve encerrar a campanha
        print(f"Falha do instrumento RNF06: {type(erro).__name__}: {erro}", file=sys.stderr)
        raise SystemExit(2)
