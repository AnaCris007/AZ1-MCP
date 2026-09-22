"""A fita: grava e reproduz interações HTTP reais dos SDKs.

Este é o ponto de entrada do módulo. Ele amarra as quatro peças anteriores —
modo, chave, sanitização e manifesto — em torno de um `vcr.VCR` configurado
conforme o item 3 da Seção 6.4.3, e resolve o que o VCR.py sozinho não resolve:

- **validade** — a biblioteca não tem TTL; quem barra o registro vencido é o
  manifesto, antes de a fita abrir;
- **ausência de rede em replay** — o bloqueio é armado ao redor do contexto, de
  modo que a promessa vire asserção;
- **atualização revisável** — o modo `atualizar` grava um candidato ao lado da
  versão vigente, em vez de sobrescrevê-la, porque o plano pede revisão do diff
  sanitizado antes da troca.

Sobre a correspondência: `match_on` inclui o corpo, como o item 3 determina.
Isso é o que faz duas mensagens de chat diferentes não casarem com a mesma
gravação mesmo quando a URL é idêntica — no google-genai, a mensagem viaja no
corpo, e sem o `body` no critério uma fita responderia por qualquer pergunta.
"""

from __future__ import annotations

import importlib.metadata as metadata
from collections.abc import Callable, Iterator, Sequence
from contextlib import contextmanager, nullcontext
from datetime import datetime
from pathlib import Path

import vcr

from tests.vhs.chave import ChaveVhs
from tests.vhs.erros import ErroVhs, RegistroAusente, RegistroCorrompido, RegistroVencido
from tests.vhs.manifesto import (
    ORIGEM_REAL,
    VALIDADE_PADRAO_DIAS,
    Manifesto,
    agora_utc,
)
from tests.vhs.modos import Modo
from tests.vhs.rede import rede_bloqueada
from tests.vhs.sanitizacao import sanitizar_requisicao, sanitizar_resposta, segredos_do_ambiente, varrer_segredos

# Item 3 da Seção 6.4.3, na ordem em que o plano escreveu.
CRITERIO_DE_CORRESPONDENCIA = ("method", "scheme", "host", "port", "path", "query", "body")

SUFIXO_CANDIDATO = ".candidato.yaml"


def versao_de_pacote(nome: str) -> str:
    """Versão instalada de um pacote, para o campo `versao_sdk` do manifesto."""
    try:
        return metadata.version(nome)
    except metadata.PackageNotFoundError:
        return "ausente"


class Vhs:
    """Gravador e reprodutor de interações externas de uma suíte.

    Uma instância fixa o modo e a raiz das gravações; cada chamada de `fita`
    abre uma gravação específica, identificada pela chave.
    """

    def __init__(
        self,
        *,
        raiz: Path,
        modo: Modo,
        versao_sdk: str = "desconhecida",
        agora: Callable[[], datetime] = agora_utc,
        segredos: Sequence[str] | None = None,
        bloquear_rede: bool = True,
    ) -> None:
        self.raiz = Path(raiz)
        self.modo = modo
        self.versao_sdk = versao_sdk
        self.bloquear_rede = bloquear_rede
        # `None` significa "descubra do ambiente"; uma sequência vazia explícita
        # desliga a redação por valor, útil no teste que verifica a redação.
        self.segredos = tuple(segredos_do_ambiente() if segredos is None else segredos)
        self.manifesto = Manifesto.carregar(self.raiz, agora=agora)

    # -- configuração do VCR.py ---------------------------------------------

    def _configuracao(self, record_mode: str) -> vcr.VCR:
        return vcr.VCR(
            record_mode=record_mode,
            match_on=list(CRITERIO_DE_CORRESPONDENCIA),
            before_record_request=sanitizar_requisicao(self.segredos),
            before_record_response=sanitizar_resposta(self.segredos),
            # Sem isto, uma resposta comprimida fica ilegível no arquivo, e a
            # varredura de segredos de TI-50 não teria o que varrer.
            decode_compressed_response=True,
        )

    # -- uso ----------------------------------------------------------------

    @contextmanager
    def fita(
        self,
        chave: ChaveVhs,
        *,
        validade_dias: int | None = VALIDADE_PADRAO_DIAS,
        origem: str = ORIGEM_REAL,
        temporario: bool = False,
        versao_sdk: str | None = None,
    ) -> Iterator[object | None]:
        """Abre a gravação da chave conforme o modo, e devolve a fita do VCR.py.

        Em `desligado` devolve `None`: não há fita, a chamada vai ao serviço
        real. Nos demais modos devolve o objeto `Cassette`, cujo `play_count`
        conta as reproduções servidas — medida de replay, não de rede.
        """
        arquivo = self.raiz / chave.caminho_relativo

        if self.modo is Modo.DESLIGADO:
            yield None
            return

        if self.modo is Modo.REPRODUZIR:
            # Validar ANTES de abrir: ausência, corrupção e vencimento precisam
            # falhar sem que nada toque a rede (TI-47 e TI-49).
            self.manifesto.validar(chave)
            guarda = rede_bloqueada() if self.bloquear_rede else nullcontext()
            with guarda, self._configuracao("none").use_cassette(str(arquivo)) as fita:
                yield fita
            return

        if self.modo is Modo.ATUALIZAR:
            # O candidato mora ao lado da versão vigente, que fica intacta para
            # o diff. A troca é explícita, em `promover_candidato`.
            candidato = arquivo.with_suffix(SUFIXO_CANDIDATO)
            candidato.parent.mkdir(parents=True, exist_ok=True)
            self.manifesto.consumir_chamada_real()
            with self._configuracao("all").use_cassette(str(candidato)) as fita:
                yield fita
            return

        # Modo.GRAVAR — `once`: reproduz o que existe, grava o que falta.
        regravar = self._precisa_regravar(chave, arquivo)
        if regravar:
            # O débito é feito antes da chamada, e não depois: o teto do item 10
            # existe para interromper a campanha, o que só funciona se ele for
            # conferido enquanto ainda dá para não chamar.
            self.manifesto.consumir_chamada_real()

        arquivo.parent.mkdir(parents=True, exist_ok=True)
        try:
            with self._configuracao("once").use_cassette(str(arquivo)) as fita:
                yield fita
        finally:
            # `finally`, e não código solto após o `with`: gravar a resposta de
            # erro de um provedor é caso previsto — TI-07 captura a recusa a uma
            # chave deliberadamente errada —, e o adaptador traduz esse 401 em
            # exceção. Sem o `finally`, a exceção sobe, o VCR.py persiste o
            # arquivo no seu próprio `__exit__` e o manifesto fica sem a linha:
            # a fita existiria em disco e o replay a trataria como ausente.
            if regravar and arquivo.exists():
                self.manifesto.registrar(
                    chave,
                    versao_sdk=versao_sdk or self.versao_sdk,
                    origem=origem,
                    validade_dias=validade_dias,
                    temporario=temporario,
                )

    def _precisa_regravar(self, chave: ChaveVhs, arquivo: Path) -> bool:
        """Decide, em modo `gravar`, entre reaproveitar e capturar de novo.

        Um registro íntegro e dentro do prazo é reaproveitado. Ausente, vencido
        ou corrompido, o arquivo é descartado e a interação é capturada outra
        vez — é a metade "em gravação autorizada" de TI-47. Descartar é
        necessário porque o modo `once` do VCR.py reproduziria o arquivo velho
        em vez de substituí-lo.
        """
        if not arquivo.exists():
            return True

        try:
            self.manifesto.validar(chave)
        except (RegistroAusente, RegistroVencido, RegistroCorrompido):
            arquivo.unlink(missing_ok=True)
            return True

        return False

    # -- manutenção ---------------------------------------------------------

    def promover_candidato(
        self,
        chave: ChaveVhs,
        *,
        validade_dias: int | None = VALIDADE_PADRAO_DIAS,
        origem: str = ORIGEM_REAL,
        temporario: bool = False,
        versao_sdk: str | None = None,
    ) -> None:
        """Substitui a versão vigente pelo candidato, depois da revisão do diff."""
        arquivo = self.raiz / chave.caminho_relativo
        candidato = arquivo.with_suffix(SUFIXO_CANDIDATO)
        if not candidato.exists():
            raise ErroVhs(f"não há candidato para {chave.descricao()}; grave em modo atualizar antes de promover")

        candidato.replace(arquivo)
        self.manifesto.registrar(
            chave,
            versao_sdk=versao_sdk or self.versao_sdk,
            origem=origem,
            validade_dias=validade_dias,
            temporario=temporario,
        )

    def varredura_de_segredos(self) -> list[str]:
        """Achados de segredo nas gravações, para a evidência de TI-50."""
        return varrer_segredos(self.raiz, self.segredos)
