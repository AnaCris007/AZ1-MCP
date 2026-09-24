# Testes do contrato da fronteira do PLN.
#
# O que se trava aqui não são valores medidos, e sim a UNICIDADE da regra. Ela
# existia em quatro versões que não concordavam: `metricas.py` a definia e só a
# aplicava offline, `agente_service` tinha um `0.70` fixo, `alertas.yaml` tinha
# outro, e `analysis_service` não aplicava nenhuma. Nada disso quebrava teste,
# porque cada cópia estava correta sozinha — o defeito era a relação entre elas.
#
# Por isso dois dos testes abaixo olham para o CÓDIGO-FONTE em vez de para o
# comportamento. Um limiar recém-copiado passa em qualquer teste de
# comportamento no dia em que é escrito; o que ele quebra é o dia em que alguém
# ajusta o original e não sabe da cópia.

from __future__ import annotations

import ast
import unittest
from pathlib import Path

import numpy as np

from pln import metricas
from pln.intencao import (
    INTENCAO_FORA_DO_CATALOGO,
    LIMIAR_PADRAO,
    DetectarIntencao,
    IntencaoDetectada,
    aplicar_limiar,
    aplicar_limiar_em_lote,
)
from services import agente_service, alerta_service


def _modelo_falso(intencao: str, confianca: float):
    """Um objeto com a superfície que `prever_intencao` consome, e nada mais."""

    class _Classificador:
        classes_ = np.array([intencao, "outra_intencao"])

    class _Modelo:
        named_steps = {"classificador": _Classificador()}

        def predict_proba(self, textos):
            return np.array([[confianca, 1.0 - confianca]])

    return _Modelo()


def _constantes_de_modulo(modulo) -> set[str]:
    arvore = ast.parse(Path(modulo.__file__).read_text(encoding="utf-8"))
    return {
        alvo.id
        for no in arvore.body
        if isinstance(no, ast.Assign)
        for alvo in no.targets
        if isinstance(alvo, ast.Name)
    }


class TesteAplicarLimiar(unittest.TestCase):
    def test_abaixo_do_limiar_vira_fora_do_catalogo(self) -> None:
        self.assertEqual(aplicar_limiar("orientar_tap", 0.4, 0.5), INTENCAO_FORA_DO_CATALOGO)

    def test_no_limiar_nao_rejeita(self) -> None:
        # A comparação é `<`, e não `<=`. A curva de `metricas.py` varre o
        # limiar em passos de 0,05 e o ponto de operação sai dela: inverter
        # isto desloca a curva inteira em um passo.
        self.assertEqual(aplicar_limiar("orientar_tap", 0.5, 0.5), "orientar_tap")

    def test_em_lote_exige_listas_do_mesmo_tamanho(self) -> None:
        with self.assertRaises(ValueError):
            aplicar_limiar_em_lote(["a", "b"], [0.9], 0.5)


class TesteIntencaoDetectada(unittest.TestCase):
    def test_confianca_suficiente_preserva_a_previsao(self) -> None:
        deteccao = IntencaoDetectada(prevista="orientar_tap", confianca=0.9, limiar=0.7)

        self.assertFalse(deteccao.rejeitada)
        self.assertEqual(deteccao.intencao, "orientar_tap")

    def test_rejeitada_separa_a_previsao_crua_da_decisao(self) -> None:
        """As duas leituras são o motivo de esta classe existir.

        `prevista` responde "o que o modelo achou" e vai para a trilha;
        `intencao` responde "o que o sistema faz com isso". Colapsá-las
        transformaria toda dúvida do classificador em recusa, e com a cobertura
        medida hoje isso recusaria cerca de metade das perguntas legítimas.
        """
        deteccao = IntencaoDetectada(prevista="orientar_tap", confianca=0.3, limiar=0.7)

        self.assertTrue(deteccao.rejeitada)
        self.assertEqual(deteccao.prevista, "orientar_tap")
        self.assertEqual(deteccao.intencao, INTENCAO_FORA_DO_CATALOGO)

    def test_limiar_padrao_quando_nao_informado(self) -> None:
        self.assertEqual(IntencaoDetectada(prevista="x", confianca=0.9).limiar, LIMIAR_PADRAO)


class TesteDetectarIntencao(unittest.TestCase):
    def test_devolve_argmax_e_confianca_do_modelo(self) -> None:
        detector = DetectarIntencao(_modelo_falso("gerar_alertas_pendencias", 0.82))

        deteccao = detector("o que precisa da minha atenção?")

        self.assertEqual(deteccao.prevista, "gerar_alertas_pendencias")
        self.assertAlmostEqual(deteccao.confianca, 0.82)
        self.assertFalse(deteccao.rejeitada)

    def test_limiar_do_detector_chega_a_deteccao(self) -> None:
        detector = DetectarIntencao(_modelo_falso("orientar_tap", 0.82), limiar=0.9)

        self.assertTrue(detector("x").rejeitada)


class TesteRegraUnica(unittest.TestCase):
    def test_metricas_usa_a_mesma_funcao_do_servico(self) -> None:
        """Medição e execução compartilham o objeto, não a intenção de serem iguais.

        Enquanto `metricas.py` tinha a própria cópia, o relatório do RNF03
        descrevia uma regra que o serviço não aplicava.
        """
        self.assertIs(metricas.aplicar_limiar_em_lote, aplicar_limiar_em_lote)
        self.assertIs(metricas.INTENCAO_FORA_DO_CATALOGO, INTENCAO_FORA_DO_CATALOGO)

    def test_agente_nao_declara_limiar_proprio(self) -> None:
        declaradas = _constantes_de_modulo(agente_service)

        self.assertEqual(
            [nome for nome in declaradas if "LIMIAR" in nome], [],
            "agente_service voltou a declarar limiar próprio. Ele recebe a "
            "decisão pronta em IntencaoDetectada.rejeitada.",
        )

    def test_despacho_de_alerta_nao_declara_limiar_proprio(self) -> None:
        declaradas = _constantes_de_modulo(alerta_service)

        self.assertEqual(
            [nome for nome in declaradas if "LIMIAR" in nome], [],
            "alerta_service voltou a declarar limiar próprio. O YAML decide "
            "QUAIS intenções são de risco; se a classificação é confiável quem "
            "decide é pln.intencao.",
        )


if __name__ == "__main__":
    unittest.main()
