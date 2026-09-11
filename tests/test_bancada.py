# Testes da bancada de medição.
#
# Uma bancada que mede errado é pior que não ter bancada: ela produz um número
# com aparência de evidência. O que precisa de teste aqui não é o valor medido,
# que muda a cada máquina, e sim a aritmética que o produz — o percentil e a
# replicação estratificada — mais as invariantes que impedem uso indevido.

from __future__ import annotations

import unittest

from pln.bancada import (
    FATORES_DE_ESCALA,
    PERCENTIS,
    ResumoDeLatencia,
    medir_latencia,
    percentil,
    replicar,
)


class TestePercentil(unittest.TestCase):
    # O método é o do posto mais próximo, escolhido para que o valor devolvido
    # seja sempre um valor observado. `statistics.quantiles` interpolaria e
    # devolveria um número que nenhuma execução mediu — indefensável como
    # evidência contra um limite contratual.
    def test_devolve_sempre_um_valor_observado(self):
        amostras = [1.0, 2.5, 3.75, 4.0, 10.0]
        for q in (1, 25, 50, 80, 95, 100):
            self.assertIn(percentil(amostras, q), amostras)

    def test_p100_e_o_maximo(self):
        self.assertEqual(percentil([1.0, 2.0, 3.0, 4.0], 100), 4.0)

    def test_p50_de_dez_amostras_e_a_quinta(self):
        amostras = [float(n) for n in range(1, 11)]
        self.assertEqual(percentil(amostras, 50), 5.0)

    def test_percentil_baixo_nao_sai_do_intervalo(self):
        # Teto de 1% de 10 amostras é o posto 1: sem o `max(1, ...)` um posto 0
        # devolveria a última amostra por indexação negativa, silenciosamente.
        amostras = [float(n) for n in range(1, 11)]
        self.assertEqual(percentil(amostras, 1), 1.0)

    def test_amostra_unica(self):
        self.assertEqual(percentil([7.0], 95), 7.0)

    def test_lista_vazia_levanta(self):
        with self.assertRaises(ValueError):
            percentil([], 50)

    def test_e_monotonico(self):
        amostras = sorted(float(n) for n in (5, 1, 9, 3, 7, 2, 8))
        valores = [percentil(amostras, q) for q in (10, 25, 50, 75, 90, 100)]
        self.assertEqual(valores, sorted(valores))


class TesteReplicacao(unittest.TestCase):
    TEXTOS = ["a", "b", "c", "d"]
    ROTULOS = ["x", "x", "y", "y"]

    def test_fator_um_devolve_copia_e_nao_o_original(self):
        textos, rotulos = replicar(self.TEXTOS, self.ROTULOS, 1)
        self.assertEqual(textos, self.TEXTOS)
        self.assertIsNot(textos, self.TEXTOS)
        self.assertIsNot(rotulos, self.ROTULOS)

    def test_multiplica_o_numero_de_exemplos(self):
        for fator in FATORES_DE_ESCALA:
            textos, rotulos = replicar(self.TEXTOS, self.ROTULOS, fator)
            self.assertEqual(len(textos), len(self.TEXTOS) * fator)
            self.assertEqual(len(rotulos), len(textos))

    def test_preserva_o_balanceamento_entre_classes(self):
        # É o que "estratificada" significa. Se a replicação desbalanceasse, a
        # curva de escala mediria duas coisas ao mesmo tempo.
        for fator in FATORES_DE_ESCALA:
            _, rotulos = replicar(self.TEXTOS, self.ROTULOS, fator)
            self.assertEqual(rotulos.count("x"), rotulos.count("y"))
            self.assertEqual(rotulos.count("x"), 2 * fator)

    def test_texto_e_rotulo_continuam_pareados(self):
        textos, rotulos = replicar(self.TEXTOS, self.ROTULOS, 3)
        esperado = dict(zip(self.TEXTOS, self.ROTULOS, strict=True))
        for texto, rotulo in zip(textos, rotulos, strict=True):
            self.assertEqual(rotulo, esperado[texto])

    def test_fator_invalido_levanta(self):
        for fator in (0, -1):
            with self.assertRaises(ValueError):
                replicar(self.TEXTOS, self.ROTULOS, fator)


class TesteMedicaoDeLatencia(unittest.TestCase):
    def test_mede_exatamente_as_repeticoes_pedidas(self):
        chamadas = []
        resumo = medir_latencia(chamadas.append, ["a", "b"], repeticoes=10, aquecimento=3)
        self.assertIsInstance(resumo, ResumoDeLatencia)
        self.assertEqual(resumo.amostras, 10)
        # As de aquecimento rodam, mas não entram na estatística.
        self.assertEqual(len(chamadas), 13)

    def test_reporta_todos_os_percentis_exigidos(self):
        resumo = medir_latencia(lambda _: None, ["a"], repeticoes=20, aquecimento=1)
        self.assertEqual(sorted(resumo.percentis_ms), sorted(PERCENTIS))

    def test_percentis_sao_nao_decrescentes(self):
        resumo = medir_latencia(lambda _: None, ["a"], repeticoes=50, aquecimento=1)
        valores = [resumo.percentis_ms[q] for q in sorted(PERCENTIS)]
        self.assertEqual(valores, sorted(valores))

    def test_percorre_as_entradas_ciclicamente(self):
        # Sem o rodízio, a medição repetiria a mesma frase e o cache por texto
        # de `preprocessamento` devolveria tudo pronto — a latência medida seria
        # a do cache, não a do pipeline.
        vistos = []
        medir_latencia(vistos.append, ["a", "b", "c"], repeticoes=6, aquecimento=0)
        self.assertEqual(vistos, ["a", "b", "c", "a", "b", "c"])

    def test_sem_entradas_levanta(self):
        with self.assertRaises(ValueError):
            medir_latencia(lambda _: None, [], repeticoes=5, aquecimento=0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
