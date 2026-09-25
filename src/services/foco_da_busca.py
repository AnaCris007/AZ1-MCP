# O que a classificação diz à busca — e por que ela não manda no prompt.
#
# Até aqui a intenção era calculada antes da LLM e morria ali: decidia se o
# Agente agia e nada mais. Quando ele não agia, a pergunta ia para o RAG
# exatamente como se nenhuma classificação existisse.
#
# Este módulo é a ponte, e ele é deliberadamente estreito.
#
# POR QUE FILTRAR A BUSCA, E NÃO INSTRUIR O MODELO
# ------------------------------------------------
# Havia duas formas de a intenção "chegar à LLM". Escrever no prompt "a
# intenção é X" é a literal, e é a pior: com F1-macro de 0,87, cerca de uma em
# oito classificações está errada, e uma afirmação errada dentro do prompt
# compete com a pergunta do usuário pela atenção do modelo — que não tem como
# saber qual das duas confiar.
#
# Filtrar a recuperação é verificável e degrada bem. Se a intenção estiver
# certa, o modelo recebe trechos do documento certo. Se estiver errada, o
# filtro devolve pouco ou nada relevante, e o `recuar_para_busca_ampla` abaixo
# repete a busca sem filtro. O erro custa uma busca vetorial, não uma resposta
# equivocada.
#
# O MAPA É PARCIAL DE PROPÓSITO
# -----------------------------
# Quatro das dez intenções nomeiam um tipo de documento; as demais não, e
# forçá-las a um tipo seria inventar correspondência. `consultar_projeto_
# sintetico` e `analisar_completude_coerencia` atravessam todos os documentos
# de um projeto; `consultar_documentos_normativos` busca fora do projeto;
# `gerar_alertas_pendencias` é servida pelo Agente e nem chega aqui.
#
# Sem entrada no mapa, o foco fica vazio e a busca é a de sempre. Nenhuma
# pergunta piora por não haver regra para ela.

from __future__ import annotations

from dataclasses import dataclass

from pln.intencao import IntencaoDetectada

# Intenção -> tipo de documento, na taxonomia de `rag/parsers.py`
# (`_TIPO_POR_PREFIXO`). As quatro correspondências são diretas: o usuário que
# pergunta sobre riscos quer o documento de riscos.
#
# Manter sincronizado com `_TIPO_POR_PREFIXO`: um tipo escrito errado aqui não
# levanta erro, só devolve busca vazia — e `tests/test_foco_da_busca.py`
# compara as duas listas justamente por isso.
TIPO_DOCUMENTO_POR_INTENCAO: dict[str, str] = {
    "orientar_tap": "termo_abertura",
    "orientar_entregas_cronograma": "cronograma",
    "orientar_mapa_beneficios": "mapa_beneficios",
    "orientar_riscos_problemas": "riscos_problemas",
}


@dataclass(frozen=True)
class FocoDaBusca:
    """Filtros que a classificação sugere à recuperação.

    Dado simples, e não `IntencaoDetectada`: `gemini_service` não deveria
    precisar importar `pln` para responder uma pergunta. O que ele recebe são
    dois filtros opcionais, e o que fazer com eles é decisão dele.
    """

    tipo_documento: str | None = None
    projeto_codigo: str | None = None

    @property
    def vazio(self) -> bool:
        return self.tipo_documento is None and self.projeto_codigo is None


SEM_FOCO = FocoDaBusca()


def focar_busca(deteccao: IntencaoDetectada | None, entidades=None) -> FocoDaBusca:
    """O foco que esta classificação sugere, ou nenhum.

    Uma detecção REJEITADA não foca nada: abaixo do limiar o rótulo é palpite,
    e estreitar a busca com base num palpite é a forma mais direta de o
    classificador piorar uma resposta que funcionaria sem ele.

    O código do projeto vem de `entidades`, extraído por REGRA e não por
    modelo — `SYN-\\d{2}` casa ou não casa. Por isso ele entra mesmo quando a
    intenção não tem tipo de documento associado: a confiabilidade dele não
    depende do F1 do classificador.
    """
    codigo = getattr(entidades, "projeto_codigo", None)

    if deteccao is None or deteccao.rejeitada:
        return FocoDaBusca(projeto_codigo=codigo)

    return FocoDaBusca(
        tipo_documento=TIPO_DOCUMENTO_POR_INTENCAO.get(deteccao.prevista),
        projeto_codigo=codigo,
    )
