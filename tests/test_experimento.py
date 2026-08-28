# Testes da varredura: cobertura do espaço de busca e critério de recomendação.
#     python -m unittest discover tests -v

from __future__ import annotations

import itertools
import math
import unittest

from pln.experimento import (
    Resultado,
    empatadas_com_a_melhor,
    escolher_recomendada,
    permutacoes_de_ordem_a_testar,
    todas_as_configuracoes_de_preprocessamento,
)
from pln.preprocessamento import (
    ETAPAS,
    ConfigPreprocessamento,
    ModoMorfologia,
    ModoStopwords,
    Tokenizacao,
)
from pln.vetorizacao import ConfigVetorizacao, ModoVetorizacao

BOW = ConfigVetorizacao(ModoVetorizacao.BOW, n_max=1)
BOW_BI = ConfigVetorizacao(ModoVetorizacao.BOW, n_max=2)
TEXTO_CRU = ConfigPreprocessamento(tokenizacao=Tokenizacao.SPLIT)


def resultado(f1, desvio=0.05, config=TEXTO_CRU, vet=BOW, ordem_padrao=True):
    return Resultado(config, vet, f1, desvio, 100.0, 1, ordem_padrao)


class TesteEspacoDeBusca(unittest.TestCase):
    def test_cobre_o_produto_cartesiano_completo(self):
        geradas = todas_as_configuracoes_de_preprocessamento()
        esperadas = {
            ConfigPreprocessamento(m, a, p, n, sw, mo, tk)
            for m, a, p, n in itertools.product([False, True], repeat=4)
            for sw, mo, tk in itertools.product(ModoStopwords, ModoMorfologia, Tokenizacao)
        }
        self.assertEqual(set(geradas), esperadas)
        self.assertEqual(len(geradas), len(esperadas), "há configurações duplicadas")

    def test_permuta_todas_as_etapas_ativas(self):
        for base in todas_as_configuracoes_de_preprocessamento():
            ativas = base.etapas_ativas_na_ordem()
            ordens = permutacoes_de_ordem_a_testar(base)
            self.assertEqual(len(ordens), math.factorial(len(ativas)))
            self.assertEqual(len({o[: len(ativas)] for o in ordens}), math.factorial(len(ativas)))

    def test_toda_ordem_gerada_e_valida(self):
        # Ordem sem todas as etapas é rejeitada por `ConfigPreprocessamento`.
        for base in todas_as_configuracoes_de_preprocessamento():
            for ordem in permutacoes_de_ordem_a_testar(base):
                self.assertEqual(set(ordem), set(ETAPAS))

    def test_a_primeira_permutacao_e_a_ordem_padrao(self):
        # `e_a_ordem_padrao` depende disso: o representante de cada corpus
        # deduplicado é o primeiro inserido.
        for base in todas_as_configuracoes_de_preprocessamento():
            ativas = base.etapas_ativas_na_ordem()
            padrao = ativas + tuple(e for e in ETAPAS if e not in ativas)
            self.assertEqual(permutacoes_de_ordem_a_testar(base)[0], padrao)


class TesteRecomendacao(unittest.TestCase):
    def test_empate_e_um_desvio_padrao_da_melhor(self):
        resultados = [resultado(0.80, desvio=0.05), resultado(0.76), resultado(0.74)]
        self.assertEqual(len(empatadas_com_a_melhor(resultados)), 2)

    def test_prefere_menos_etapas_mesmo_com_f1_menor(self):
        com_etapas = ConfigPreprocessamento(minusculas=True, remover_acentos=True)
        escolhida = escolher_recomendada([resultado(0.80, config=com_etapas), resultado(0.78)])
        self.assertEqual(escolhida.config.etapas_ativas_na_ordem(), ())

    def test_prefere_janela_menor_entre_empatadas(self):
        self.assertEqual(escolher_recomendada([resultado(0.80, vet=BOW_BI), resultado(0.78)]).vetorizacao.n_max, 1)

    def test_prefere_a_ordem_padrao_ao_f1_mais_alto(self):
        # Entre ordens do mesmo conjunto de etapas, a diferença de F1 é menor
        # que o desvio entre dobras, então escolher por ela seria escolher ruído.
        etapas = ("minusculas", "remover_acentos")
        inativas = tuple(e for e in ETAPAS if e not in etapas)
        base = ConfigPreprocessamento(minusculas=True, remover_acentos=True)
        invertida = base.copiar_com_outra_ordem(etapas[::-1] + inativas)

        escolhida = escolher_recomendada([
            resultado(0.8010, config=invertida, ordem_padrao=False),
            resultado(0.8000, config=base, ordem_padrao=True),
        ])
        self.assertTrue(escolhida.e_a_ordem_padrao)
        self.assertAlmostEqual(escolhida.f1_medio, 0.8000)

    def test_f1_ainda_desempata_quando_o_resto_e_igual(self):
        escolhida = escolher_recomendada([resultado(0.78), resultado(0.80)])
        self.assertAlmostEqual(escolhida.f1_medio, 0.80)


if __name__ == "__main__":
    unittest.main(verbosity=2)
