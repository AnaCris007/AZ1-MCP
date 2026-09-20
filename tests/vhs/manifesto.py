"""Manifesto das gravações: integridade, validade e orçamento da campanha.

O item 6 da Seção 6.4.3 lista o que cada registro precisa declarar — hash,
provedor, modelo, versão do SDK, versão do contrato, instante da gravação,
política de validade e a marca `real`/`simulado`. O item 7 acrescenta a razão
de o manifesto existir como código próprio, e não como configuração do VCR.py:
**a biblioteca não tem TTL de negócio**. Ela sabe dizer se um pedido casa com o
que está gravado; não sabe dizer que aquela gravação envelheceu.

Três consequências práticas, todas exercitadas pela suíte:

- Em `reproduzir`, registro vencido ou corrompido falha **sem rede**. A
  expiração não autoriza chamada externa silenciosa em CI (item 7).
- O relógio é injetável. Testar a fronteira da validade não pode exigir esperar
  dias, nem mexer no relógio da máquina.
- A campanha tem teto de chamadas reais, fixado antes de gravar (item 10), e o
  encerramento apaga os registros temporários (item 6).

A marca `origem` é o que impede a confusão que o plano rejeita explicitamente:
um timeout produzido por mock não pode ser arquivado como se fosse interação
capturada do provedor. Ele entra como `simulado`, e o relatório distingue.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

from tests.vhs.chave import ChaveVhs
from tests.vhs.erros import (
    CampanhaEncerrada,
    LimiteDeChamadasReais,
    RegistroAusente,
    RegistroCorrompido,
    RegistroVencido,
)

NOME_DO_MANIFESTO = "manifesto.json"
VALIDADE_PADRAO_DIAS = 30
LIMITE_PADRAO_DE_CHAMADAS_REAIS = 50

ORIGEM_REAL = "real"
ORIGEM_SIMULADA = "simulado"
ORIGENS = (ORIGEM_REAL, ORIGEM_SIMULADA)


def agora_utc() -> datetime:
    return datetime.now(UTC)


def _sha256(arquivo: Path) -> str:
    return hashlib.sha256(arquivo.read_bytes()).hexdigest()


@dataclass(frozen=True)
class Registro:
    """Uma linha do manifesto, descrevendo uma gravação em disco."""

    sha256: str
    provedor: str
    modelo: str
    cenario: str
    versao_contrato: str
    versao_sdk: str
    gravado_em: str
    validade_dias: int | None
    origem: str
    temporario: bool

    @property
    def instante(self) -> datetime:
        return datetime.fromisoformat(self.gravado_em)

    def vencido_em(self, momento: datetime) -> bool:
        if self.validade_dias is None:
            return False
        return momento > self.instante + timedelta(days=self.validade_dias)


@dataclass
class Campanha:
    """Janela de gravação com contrato congelado e teto de chamadas reais."""

    inicio: str
    encerramento: str | None = None
    limite_chamadas_reais: int = LIMITE_PADRAO_DE_CHAMADAS_REAIS
    chamadas_reais: int = 0


class Manifesto:
    """Estado versionado ao lado das fitas, em `manifesto.json`."""

    def __init__(
        self,
        *,
        raiz: Path,
        registros: dict[str, Registro] | None = None,
        campanha: Campanha | None = None,
        agora: Callable[[], datetime] = agora_utc,
    ) -> None:
        self.raiz = raiz
        self.agora = agora
        self.registros = registros or {}
        self.campanha = campanha or Campanha(inicio=agora().isoformat())

    # -- persistência -------------------------------------------------------

    @classmethod
    def carregar(cls, raiz: Path, *, agora: Callable[[], datetime] = agora_utc) -> Manifesto:
        arquivo = raiz / NOME_DO_MANIFESTO
        if not arquivo.exists():
            return cls(raiz=raiz, agora=agora)

        bruto = json.loads(arquivo.read_text(encoding="utf-8"))
        registros = {caminho: Registro(**dados) for caminho, dados in bruto.get("registros", {}).items()}
        return cls(
            raiz=raiz,
            registros=registros,
            campanha=Campanha(**bruto["campanha"]),
            agora=agora,
        )

    def salvar(self) -> None:
        self.raiz.mkdir(parents=True, exist_ok=True)
        conteudo = {
            "campanha": asdict(self.campanha),
            "registros": {caminho: asdict(registro) for caminho, registro in sorted(self.registros.items())},
        }
        (self.raiz / NOME_DO_MANIFESTO).write_text(
            json.dumps(conteudo, indent=2, ensure_ascii=False, sort_keys=False) + "\n",
            encoding="utf-8",
        )

    # -- registros ----------------------------------------------------------

    def registrar(
        self,
        chave: ChaveVhs,
        *,
        versao_sdk: str,
        origem: str = ORIGEM_REAL,
        validade_dias: int | None = VALIDADE_PADRAO_DIAS,
        temporario: bool = False,
    ) -> Registro:
        """Anota a gravação recém-persistida, com o hash do arquivo em disco."""
        if origem not in ORIGENS:
            raise ValueError(f"origem deve ser uma de {ORIGENS}, veio {origem!r}")

        arquivo = self.raiz / chave.caminho_relativo
        if not arquivo.exists():
            raise RegistroAusente(f"nada para registrar em {chave.caminho_relativo}: o arquivo não foi gravado")

        registro = Registro(
            sha256=_sha256(arquivo),
            provedor=chave.provedor,
            modelo=chave.modelo,
            cenario=chave.cenario,
            versao_contrato=chave.versao_contrato,
            versao_sdk=versao_sdk,
            gravado_em=self.agora().isoformat(),
            validade_dias=validade_dias,
            origem=origem,
            temporario=temporario,
        )
        self.registros[chave.caminho_relativo.as_posix()] = registro
        self.salvar()
        return registro

    def validar(self, chave: ChaveVhs) -> Registro:
        """Devolve o registro da chave, ou levanta dizendo exatamente o que há.

        A ordem das três verificações é a que separa as causas: primeiro a
        existência, depois a integridade, por último o prazo. Um arquivo
        corrompido não deve ser reportado como vencido, e um vencido não deve
        ser reportado como ausente — TI-49 exige distinguir.
        """
        relativo = chave.caminho_relativo.as_posix()
        registro = self.registros.get(relativo)
        arquivo = self.raiz / chave.caminho_relativo

        if registro is None:
            raise RegistroAusente(f"sem registro no manifesto para {chave.descricao()}")
        if not arquivo.exists():
            raise RegistroAusente(f"manifesto aponta {relativo}, e o arquivo não está em disco")
        if _sha256(arquivo) != registro.sha256:
            raise RegistroCorrompido(f"conteúdo de {relativo} não confere com o hash do manifesto")
        if registro.vencido_em(self.agora()):
            raise RegistroVencido(
                f"{relativo} venceu: gravado em {registro.gravado_em}, validade de {registro.validade_dias} dias"
            )

        return registro

    def remover(self, chave: ChaveVhs) -> None:
        """Apaga a gravação e sua linha, usado ao descartar uma massa."""
        self.registros.pop(chave.caminho_relativo.as_posix(), None)
        (self.raiz / chave.caminho_relativo).unlink(missing_ok=True)
        self.salvar()

    # -- campanha -----------------------------------------------------------

    def abrir_campanha(self, *, limite_chamadas_reais: int = LIMITE_PADRAO_DE_CHAMADAS_REAIS) -> None:
        self.campanha = Campanha(inicio=self.agora().isoformat(), limite_chamadas_reais=limite_chamadas_reais)
        self.salvar()

    def consumir_chamada_real(self) -> int:
        """Debita uma chamada externa do orçamento e devolve o total gasto."""
        if self.campanha.encerramento is not None:
            raise CampanhaEncerrada(
                f"campanha encerrada em {self.campanha.encerramento}; abra outra para gravar de novo"
            )
        if self.campanha.chamadas_reais >= self.campanha.limite_chamadas_reais:
            raise LimiteDeChamadasReais(
                f"limite de {self.campanha.limite_chamadas_reais} chamadas reais atingido nesta campanha"
            )

        self.campanha.chamadas_reais += 1
        self.salvar()
        return self.campanha.chamadas_reais

    def encerrar_campanha(self, *, remover_temporarios: bool = True) -> list[str]:
        """Fecha a janela e apaga o que não foi selecionado para regressão."""
        self.campanha.encerramento = self.agora().isoformat()

        removidos: list[str] = []
        if remover_temporarios:
            for relativo, registro in list(self.registros.items()):
                if registro.temporario:
                    (self.raiz / relativo).unlink(missing_ok=True)
                    del self.registros[relativo]
                    removidos.append(relativo)

        self.salvar()
        return removidos
