# O contrato da fronteira do PLN: o que o resto do sistema recebe quando pede
# uma classificação.
#
# Existe porque a regra de rejeição estava escrita em quatro lugares que não
# concordavam — `metricas.py` a definia e só a aplicava offline,
# `agente_service` tinha um `0.70` fixo, `alertas.yaml` tinha outro, e
# `analysis_service` não aplicava nenhuma. Medir uma regra e executar outra é a
# forma mais barata de um relatório aprovado descrever um sistema que não existe.
#
# Este módulo fica em `pln/`, e não em `services/`, porque o limiar é
# propriedade da CALIBRAÇÃO do modelo — mesma família de `CONFIG_PRE_PADRAO` e
# `ALPHA_PADRAO` em `classificador.py`: valor medido, colado no código e
# guardado por teste. Mantê-lo aqui deixa `services/` livre de decisão de
# modelagem.

from __future__ import annotations

from dataclasses import dataclass

from pln.classificador import prever_intencao

INTENCAO_FORA_DO_CATALOGO = "fora_do_catalogo"

# Calibrado por `python -m pln.metricas`, SOMENTE sobre dados de
# desenvolvimento. Trocar o dataset o invalida, pelo mesmo motivo que invalida
# as constantes de `classificador.py`.
#
# POR QUE 0,20, E NÃO O 0,00 QUE A FERRAMENTA REPORTA
# ---------------------------------------------------
# Sob o `LinearSVC` calibrado, TODO limiar entre 0,00 e 0,20 produz exatamente
# as mesmas três métricas — porque a menor confiança observada no
# desenvolvimento é 0,2080, e abaixo dela não há o que rejeitar. O `0,00` que
# `escolher_limiar` devolve é o primeiro de um empate, não uma decisão de nunca
# rejeitar.
#
# Adotar o TOPO da faixa empatada custa zero em métrica medida e mantém a regra
# viva: se dados futuros produzirem confiança abaixo de 0,20 — e produzirão, o
# corpus é sintético e a linguagem real é mais variada —, com 0,00 nada seria
# rejeitado nunca, em silêncio.
#
# Neste ponto os TRÊS limites do RNF03 são atendidos no conjunto retido:
# F1 0,8735, cobertura 96,0%, aceitação indevida 8,2%.
#
# `resultados/metricas_rnf03.md` traz a curva inteira. Subir daqui troca
# cobertura por aceitação indevida, nunca melhora as duas.
LIMIAR_PADRAO = 0.20


# A regra de rejeição. Abaixo do limiar, a previsão vira `fora_do_catalogo`.
#
# É função de módulo, e não método de `IntencaoDetectada`, porque `metricas.py`
# precisa aplicá-la a listas inteiras de previsões vindas da validação cruzada,
# onde não há modelo carregado nem texto original — só rótulo e confiança.
def aplicar_limiar(rotulo: str, confianca: float, limiar: float) -> str:
    if confianca < limiar:
        return INTENCAO_FORA_DO_CATALOGO
    return rotulo


def aplicar_limiar_em_lote(
    rotulos: list[str], confiancas: list[float], limiar: float
) -> list[str]:
    return [
        aplicar_limiar(rotulo, confianca, limiar)
        for rotulo, confianca in zip(rotulos, confiancas, strict=True)
    ]


# Carrega as DUAS leituras da mesma classificação, e é esse o ponto.
#
# `prevista` é o argmax cru: o que o modelo achou. `intencao` é o que sobra
# depois da regra. Quem precisa da diferença é o Agente — "o modelo disse
# `fora_do_catalogo` com confiança" leva à recusa prevista no RF02, enquanto "o
# modelo não teve confiança em nada" leva a deixar o RAG responder.
#
# Colapsar as duas na mesma string transformaria toda dúvida do classificador
# numa recusa. Com a cobertura medida hoje (51,9% no limiar 0,70), isso
# recusaria cerca de metade das perguntas legítimas — o RNF03 seria cumprido ao
# pé da letra às custas do produto.
@dataclass(frozen=True)
class IntencaoDetectada:
    prevista: str
    confianca: float
    limiar: float = LIMIAR_PADRAO

    @property
    def rejeitada(self) -> bool:
        return self.confianca < self.limiar

    @property
    def intencao(self) -> str:
        return aplicar_limiar(self.prevista, self.confianca, self.limiar)


# O modelo é injetado, e não carregado aqui: quem sabe de onde vem o `.joblib`
# é `az1_api/dependencies.py`, que já o mantém desserializado uma vez só por
# processo.
class DetectarIntencao:
    def __init__(self, modelo, limiar: float = LIMIAR_PADRAO) -> None:
        self._modelo = modelo
        self._limiar = limiar

    def __call__(self, texto: str) -> IntencaoDetectada:
        prevista, confianca = prever_intencao(self._modelo, texto)
        return IntencaoDetectada(
            prevista=prevista, confianca=confianca, limiar=self._limiar
        )
