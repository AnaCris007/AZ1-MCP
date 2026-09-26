# O `: Agente` do diagrama de sequência (docs/Projeto.md §3.9): recebe a
# intenção já classificada e decide a ação do sistema.
#
# Cobre só as intenções que já têm uma ação existente para reaproveitar:
#   - gerar_alertas_pendencias  -> lista as pendências (do projeto, se identificado)
#   - consultar_projeto_sintetico -> situação estruturada do(s) projeto(s)
#   - fora_do_catalogo          -> recusa e orienta (RF02, caso crítico 1)
#
# As demais intenções do catálogo ficam de fora de propósito:
# `consultar_documentos_normativos` já é servida pelo RAG do chat; os
# `orientar_*` e `analisar_completude_coerencia` dependem de ler e sugerir
# preenchimento de campos de artefato, funcionalidade que docs/Projeto.md
# (linha "RF04 | Não implementado") registra como não implementada em nenhum
# lugar do sistema — não é este componente que resolve isso.
#
# O LIMIAR NÃO MORA MAIS AQUI. Este componente recebe uma `IntencaoDetectada`
# com a regra de rejeição já aplicada por `pln.intencao` — a mesma função que
# `pln.metricas` usa para medir o RNF03. Antes havia um `0.70` fixo neste
# arquivo e outro em `config/alertas.yaml`, e nenhum dos dois era o que o
# relatório media.
#
# O que este componente ainda decide é o que fazer com as DUAS leituras que a
# detecção carrega: confiança insuficiente deixa o RAG responder, enquanto
# `fora_do_catalogo` previsto COM confiança é recusa. São situações diferentes
# e só uma delas é o caso crítico 1.

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum, auto

from pln.entidades import EntidadesExtraidas, extrair_entidades
from pln.intencao import INTENCAO_FORA_DO_CATALOGO, IntencaoDetectada
from services.portfolio_repository import Pendencia, PortfolioRepository, SituacaoProjeto

logger = logging.getLogger(__name__)

INTENCOES_COM_ACAO = frozenset({"gerar_alertas_pendencias", "consultar_projeto_sintetico"})


class ResultadoAcao(Enum):
    PENDENCIAS = auto()
    PROJETO = auto()
    RECUSADA_FORA_DO_CATALOGO = auto()
    SEM_ACAO = auto()


@dataclass(frozen=True)
class RespostaDoAgente:
    resultado: ResultadoAcao
    entidades: EntidadesExtraidas
    pendencias: tuple[Pendencia, ...] = field(default_factory=tuple)
    projetos: tuple[SituacaoProjeto, ...] = field(default_factory=tuple)


_SEM_ACAO_SEM_ENTIDADE = RespostaDoAgente(ResultadoAcao.SEM_ACAO, EntidadesExtraidas())


class ExecutarIntencao:
    def __init__(self, portfolio: PortfolioRepository) -> None:
        self._portfolio = portfolio

    def executar(self, *, deteccao: IntencaoDetectada, texto: str) -> RespostaDoAgente:
        entidades = extrair_entidades(texto)

        # Confiança insuficiente NÃO é recusa: é ausência de opinião. O RAG
        # responde, como respondia antes de este componente existir.
        if deteccao.rejeitada:
            return RespostaDoAgente(ResultadoAcao.SEM_ACAO, entidades)

        # `prevista`, e não `intencao`: o que autoriza a recusa é o modelo ter
        # dito `fora_do_catalogo`, não a regra tê-lo produzido por descarte.
        # Passado o guarda acima os dois coincidem, e escrever `prevista` é o
        # que mantém a distinção legível se a ordem mudar.
        if deteccao.prevista == INTENCAO_FORA_DO_CATALOGO:
            return RespostaDoAgente(ResultadoAcao.RECUSADA_FORA_DO_CATALOGO, entidades)

        if deteccao.prevista not in INTENCOES_COM_ACAO:
            return RespostaDoAgente(ResultadoAcao.SEM_ACAO, entidades)

        if deteccao.prevista == "gerar_alertas_pendencias":
            return RespostaDoAgente(
                ResultadoAcao.PENDENCIAS, entidades, pendencias=self._pendencias(entidades)
            )

        return RespostaDoAgente(
            ResultadoAcao.PROJETO, entidades, projetos=self._projetos(entidades)
        )

    def _pendencias(self, entidades: EntidadesExtraidas) -> tuple[Pendencia, ...]:
        pendencias = self._portfolio.pendencias()
        if entidades.projeto_codigo is None:
            return pendencias
        return tuple(p for p in pendencias if p.projeto_codigo == entidades.projeto_codigo)

    def _projetos(self, entidades: EntidadesExtraidas) -> tuple[SituacaoProjeto, ...]:
        projetos = self._portfolio.situacao_dos_projetos()
        if entidades.projeto_codigo is None:
            return projetos
        return tuple(p for p in projetos if p.codigo == entidades.projeto_codigo)


class AgenteDesligado:
    """Substitui `ExecutarIntencao` quando não há banco configurado.

    Mesmo raciocínio de `DespachoDesligado`, em `alerta_service.py`: as ações
    que dependem de portfólio ficam indisponíveis, mas a recusa por
    fora-do-catálogo não depende de banco nenhum e continua funcionando.
    """

    def __init__(self, motivo: str) -> None:
        self._motivo = motivo
        self._avisou = False

    def executar(self, *, deteccao: IntencaoDetectada, texto: str) -> RespostaDoAgente:
        entidades = extrair_entidades(texto)
        if deteccao.rejeitada:
            return RespostaDoAgente(ResultadoAcao.SEM_ACAO, entidades)
        if deteccao.prevista == INTENCAO_FORA_DO_CATALOGO:
            return RespostaDoAgente(ResultadoAcao.RECUSADA_FORA_DO_CATALOGO, entidades)
        if not self._avisou:
            logger.warning("Agente desligado: %s", self._motivo)
            self._avisou = True
        return RespostaDoAgente(ResultadoAcao.SEM_ACAO, entidades)
