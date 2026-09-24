# Testes das métricas do RNF03.
#
# O que precisa de teste aqui não são os valores medidos, que mudam com o
# dataset, e sim as DEFINIÇÕES — porque duas delas são contraintuitivas e errar
# uma produz um número plausível, que ninguém questiona, e errado.
#
# A mais traiçoeira é a cobertura: ela conta exemplos NÃO REJEITADOS, e não
# exemplos classificados corretamente. Um exemplo de `orientar_tap` previsto
# como `orientar_avanco_mensal` entra na cobertura. Quem mede acerto é o F1.

from __future__ import annotations

import unittest

# A regra de rejeição mudou de casa para `pln.intencao`, porque o serviço
# precisa aplicá-la em produção e não pode depender do módulo de medição. Os
# testes dela continuam aqui: a rejeição é uma das DEFINIÇÕES que este arquivo
# existe para travar, e é sobre ela que cobertura e aceitação indevida são
# construídas. `test_intencao.py` trava o outro lado — que é a MESMA função.
from pln.intencao import (
    INTENCAO_FORA_DO_CATALOGO,
    aplicar_limiar,
    aplicar_limiar_em_lote,
)
from pln.metricas import (
    LIMIARES_PADRAO,
    META_ACEITACAO_INDEVIDA,
    META_COBERTURA,
    META_F1_MACRO,
    avaliar_rnf03,
    curva_do_limiar,
    escolher_limiar,
    limiar_menos_distante,
    subamostrar,
)

FORA = INTENCAO_FORA_DO_CATALOGO


class TesteAplicarLimiar(unittest.TestCase):
    def test_confianca_abaixo_do_limiar_rejeita(self):
        self.assertEqual(aplicar_limiar("orientar_tap", 0.4, 0.5), FORA)

    def test_confianca_acima_do_limiar_mantem(self):
        self.assertEqual(aplicar_limiar("orientar_tap", 0.6, 0.5), "orientar_tap")

    def test_confianca_igual_ao_limiar_nao_rejeita(self):
        # A comparação é `<`, e não `<=`: o limiar é o piso do que se aceita.
        # Trocar um pelo outro desloca a curva inteira em um degrau.
        self.assertEqual(aplicar_limiar("orientar_tap", 0.5, 0.5), "orientar_tap")

    def test_limiar_zero_nunca_rejeita(self):
        # É o comportamento de produção hoje: nenhum limiar aplicado.
        self.assertEqual(aplicar_limiar("orientar_tap", 0.0, 0.0), "orientar_tap")

    def test_em_lote_preserva_a_ordem(self):
        rotulos = ["a", "b", "c"]
        saida = aplicar_limiar_em_lote(rotulos, [0.9, 0.1, 0.9], 0.5)
        self.assertEqual(saida, ["a", FORA, "c"])

    def test_em_lote_exige_mesmo_tamanho(self):
        with self.assertRaises(ValueError):
            aplicar_limiar_em_lote(["a", "b"], [0.9], 0.5)


class TesteDefinicaoDeCobertura(unittest.TestCase):
    # Quatro conhecidos, nenhum fora do catálogo.
    REAIS = ["a", "b", "c", "d"]

    def test_conhecido_previsto_errado_ainda_conta_como_coberto(self):
        # Esta é a definição literal da Seção 6.3: `conhecidos não rejeitados`.
        # Todos os quatro erraram de classe, mas nenhum foi rejeitado.
        previstos = ["b", "a", "d", "c"]
        r = avaliar_rnf03(self.REAIS, previstos, [0.9] * 4, limiar=0.5)
        self.assertEqual(r.cobertura, 1.0)

    def test_conhecido_rejeitado_nao_conta(self):
        r = avaliar_rnf03(self.REAIS, list(self.REAIS), [0.9, 0.9, 0.1, 0.1], limiar=0.5)
        self.assertEqual(r.cobertura, 0.5)

    def test_conhecido_previsto_como_fora_do_catalogo_nao_conta(self):
        # Rejeição pelo limiar e previsão direta de `fora_do_catalogo` têm o
        # mesmo efeito sobre a cobertura: o exemplo não foi atendido.
        previstos = [FORA, "b", "c", "d"]
        r = avaliar_rnf03(self.REAIS, previstos, [0.9] * 4, limiar=0.5)
        self.assertEqual(r.cobertura, 0.75)

    def test_conta_apenas_os_conhecidos(self):
        reais = ["a", "b", FORA, FORA]
        r = avaliar_rnf03(reais, ["a", "b", FORA, FORA], [0.9] * 4, limiar=0.5)
        self.assertEqual(r.conhecidos, 2)
        self.assertEqual(r.fora_do_catalogo, 2)


class TesteDefinicaoDeAceitacaoIndevida(unittest.TestCase):
    REAIS = [FORA] * 4

    def test_fora_do_catalogo_aceito_como_conhecida_conta(self):
        r = avaliar_rnf03(self.REAIS, ["a", "b", FORA, FORA], [0.9] * 4, limiar=0.5)
        self.assertEqual(r.aceitacao_indevida, 0.5)

    def test_rejeicao_pelo_limiar_evita_a_aceitacao_indevida(self):
        # Mesmos rótulos previstos do teste anterior, mas com confiança baixa:
        # o limiar salva os dois que seriam aceitos indevidamente.
        r = avaliar_rnf03(self.REAIS, ["a", "b", FORA, FORA], [0.1] * 4, limiar=0.5)
        self.assertEqual(r.aceitacao_indevida, 0.0)

    def test_tudo_aceito_indevidamente(self):
        r = avaliar_rnf03(self.REAIS, ["a", "b", "c", "d"], [0.9] * 4, limiar=0.5)
        self.assertEqual(r.aceitacao_indevida, 1.0)


class TesteAvaliacao(unittest.TestCase):
    def test_sem_exemplos_levanta(self):
        with self.assertRaises(ValueError):
            avaliar_rnf03([], [], [], limiar=0.5)

    def test_aprovado_exige_os_tres_limites(self):
        # Um conjunto que passa em F1 e cobertura mas falha em aceitação
        # indevida precisa reprovar: a Seção 6.3 diz que os limites são
        # cumulativos.
        reais = ["a"] * 9 + [FORA]
        previstos = ["a"] * 9 + ["a"]
        r = avaliar_rnf03(reais, previstos, [0.9] * 10, limiar=0.5)
        self.assertEqual(r.cobertura, 1.0)
        self.assertEqual(r.aceitacao_indevida, 1.0)
        self.assertFalse(r.aprovado)

    def test_aprovado_quando_os_tres_passam(self):
        reais = ["a", "b", FORA]
        previstos = ["a", "b", FORA]
        r = avaliar_rnf03(reais, previstos, [0.9, 0.9, 0.9], limiar=0.5)
        self.assertGreaterEqual(r.f1_macro, META_F1_MACRO)
        self.assertGreaterEqual(r.cobertura, META_COBERTURA)
        self.assertLessEqual(r.aceitacao_indevida, META_ACEITACAO_INDEVIDA)
        self.assertTrue(r.aprovado)


class TesteCurvaDoLimiar(unittest.TestCase):
    REAIS = ["a", "b", "c", FORA, FORA]
    PREVISTOS = ["a", "b", "a", "a", FORA]
    CONFIANCAS = [0.9, 0.7, 0.5, 0.3, 0.8]

    def curva(self):
        return curva_do_limiar(self.REAIS, self.PREVISTOS, self.CONFIANCAS)

    def test_cobre_todos_os_limiares_pedidos(self):
        self.assertEqual([r.limiar for r in self.curva()], list(LIMIARES_PADRAO))

    def test_cobertura_nunca_sobe_quando_o_limiar_sobe(self):
        # Subir o limiar só pode rejeitar mais. Se esta invariante quebrar, a
        # comparação é entre grandezas diferentes.
        coberturas = [r.cobertura for r in self.curva()]
        self.assertEqual(coberturas, sorted(coberturas, reverse=True))

    def test_aceitacao_indevida_nunca_sobe_quando_o_limiar_sobe(self):
        aceitacoes = [r.aceitacao_indevida for r in self.curva()]
        self.assertEqual(aceitacoes, sorted(aceitacoes, reverse=True))

    def test_limiar_maximo_rejeita_tudo(self):
        extremo = self.curva()[-1]
        self.assertEqual(extremo.limiar, 1.0)
        self.assertEqual(extremo.cobertura, 0.0)
        self.assertEqual(extremo.aceitacao_indevida, 0.0)


class TesteEscolhaDoLimiar(unittest.TestCase):
    def test_devolve_none_quando_nenhum_limiar_atende(self):
        # O caso real do dataset atual. `None` é resposta, não falha: nenhum
        # ponto de corte concilia cobertura e aceitação indevida.
        reais = ["a"] * 9 + [FORA]
        curva = curva_do_limiar(reais, ["a"] * 10, [0.99] * 10)
        self.assertIsNone(escolher_limiar(curva))

    def test_escolhe_o_de_maior_f1_entre_os_aprovados(self):
        reais = ["a", "b", FORA]
        curva = curva_do_limiar(reais, ["a", "b", FORA], [0.9, 0.9, 0.9])
        escolhido = escolher_limiar(curva)
        self.assertIsNotNone(escolhido)
        aprovados = [r for r in curva if r.aprovado]
        self.assertEqual(escolhido.f1_macro, max(r.f1_macro for r in aprovados))

    def test_menos_distante_sempre_devolve_algo(self):
        reais = ["a"] * 9 + [FORA]
        curva = curva_do_limiar(reais, ["a"] * 10, [0.99] * 10)
        self.assertIn(limiar_menos_distante(curva), curva)


class TesteSubamostragem(unittest.TestCase):
    TEXTOS = [f"t{i}" for i in range(40)]
    ROTULOS = ["a"] * 20 + ["b"] * 20

    def test_fracao_total_devolve_copia(self):
        textos, _ = subamostrar(self.TEXTOS, self.ROTULOS, 1.0)
        self.assertEqual(textos, self.TEXTOS)
        self.assertIsNot(textos, self.TEXTOS)

    def test_preserva_o_balanceamento(self):
        for fracao in (0.25, 0.5, 0.75):
            _, rotulos = subamostrar(self.TEXTOS, self.ROTULOS, fracao)
            self.assertEqual(rotulos.count("a"), rotulos.count("b"))

    def test_mantem_texto_e_rotulo_pareados(self):
        esperado = dict(zip(self.TEXTOS, self.ROTULOS, strict=True))
        textos, rotulos = subamostrar(self.TEXTOS, self.ROTULOS, 0.5)
        for texto, rotulo in zip(textos, rotulos, strict=True):
            self.assertEqual(rotulo, esperado[texto])

    def test_e_deterministica(self):
        primeira = subamostrar(self.TEXTOS, self.ROTULOS, 0.5)
        segunda = subamostrar(self.TEXTOS, self.ROTULOS, 0.5)
        self.assertEqual(primeira, segunda)

    def test_garante_o_minimo_para_a_validacao_cruzada(self):
        # Fração minúscula ainda precisa deixar 2 por classe, senão o
        # `StratifiedKFold` levanta em vez de medir.
        _, rotulos = subamostrar(self.TEXTOS, self.ROTULOS, 0.01)
        self.assertGreaterEqual(rotulos.count("a"), 2)
        self.assertGreaterEqual(rotulos.count("b"), 2)

    def test_fracao_invalida_levanta(self):
        for fracao in (0, -0.5, 1.5):
            with self.assertRaises(ValueError):
                subamostrar(self.TEXTOS, self.ROTULOS, fracao)


if __name__ == "__main__":
    unittest.main(verbosity=2)
