# =============================================================================
# test_vetorizacao.py — Testes do módulo de vetorização
# =============================================================================
#     python -m unittest discover tests -v
#
# O teste mais importante deste arquivo é o que garante que o vetorizador NÃO
# retokeniza. Se os padrões do scikit-learn voltarem a valer, três decisões do
# experimento — minúsculas, remoção de pontuação e escolha de tokenizador —
# deixam de ter efeito silenciosamente, e o experimento passa a medir errado
# sem falhar em lugar nenhum.
# =============================================================================

from __future__ import annotations

import unittest

from sklearn.feature_extraction.text import CountVectorizer, TfidfVectorizer

from az1.pln.vetorizacao import (
    JANELAS_NGRAMA,
    VETORIZACAO_REFERENCIA,
    ConfigVetorizacao,
    ModoVetorizacao,
    construir_pipeline_de_medicao,
    construir_vetorizador,
    todas_as_vetorizacoes,
)

CORPUS = ["prazo venceu ?", "prazo venceu ?", "registra o marco ."]


class TesteEspacoDeVetorizacao(unittest.TestCase):
    def test_sao_quatro_opcoes(self):
        opcoes = todas_as_vetorizacoes()
        self.assertEqual(len(opcoes), len(ModoVetorizacao) * len(JANELAS_NGRAMA))
        self.assertEqual(len(set(opcoes)), len(opcoes), "há vetorizações duplicadas")

    def test_referencia_esta_no_espaco(self):
        # A régua da Fase 1 precisa ser uma das opções da Fase 2 — senão a
        # comparação entre as fases não fecha.
        self.assertIn(VETORIZACAO_REFERENCIA, todas_as_vetorizacoes())

    def test_descricao_curta(self):
        self.assertEqual(ConfigVetorizacao(ModoVetorizacao.BOW, 1).descrever(), "bow n=1")
        self.assertEqual(ConfigVetorizacao(ModoVetorizacao.TFIDF, 2).descrever(), "tfidf n=1-2")


class TesteNaoRetokeniza(unittest.TestCase):
    # A garantia central: o vetorizador respeita a tokenização já feita.

    def test_padroes_do_sklearn_estao_desligados(self):
        v = construir_vetorizador(VETORIZACAO_REFERENCIA)
        self.assertFalse(v.lowercase, "lowercase ligado anularia a etapa `minusculas`")
        self.assertIs(v.tokenizer, str.split, "tokenizer próprio anularia a escolha de tokenização")
        self.assertIsNone(v.token_pattern, "token_pattern ativo descartaria pontuação")

    def test_pontuacao_sobrevive_como_token(self):
        # "?" é evidência: separa pergunta (consulta/alerta) de ordem
        # (transação). Com o token_pattern padrão do sklearn ele seria
        # descartado em silêncio.
        v = construir_vetorizador(VETORIZACAO_REFERENCIA)
        v.fit(CORPUS)
        self.assertIn("?", v.vocabulary_)

    def test_maiuscula_e_minuscula_ficam_distintas(self):
        v = construir_vetorizador(VETORIZACAO_REFERENCIA)
        v.fit(["Prazo prazo"])
        self.assertIn("Prazo", v.vocabulary_)
        self.assertIn("prazo", v.vocabulary_)

    def test_token_de_uma_letra_nao_e_descartado(self):
        # O token_pattern padrão exige duas letras (\w\w+) e comeria "o", "e", "a".
        v = construir_vetorizador(VETORIZACAO_REFERENCIA)
        v.fit(["o marco e o prazo"])
        self.assertIn("o", v.vocabulary_)


class TesteModosEJanelas(unittest.TestCase):
    def test_bow_e_tfidf_usam_classes_diferentes(self):
        self.assertIsInstance(construir_vetorizador(ConfigVetorizacao(ModoVetorizacao.BOW, 1)), CountVectorizer)
        self.assertIsInstance(construir_vetorizador(ConfigVetorizacao(ModoVetorizacao.TFIDF, 1)), TfidfVectorizer)

    def test_bow_conta_e_tfidf_pondera(self):
        # Bag of words devolve inteiros; tf-idf devolve pesos normalizados.
        bow = construir_vetorizador(ConfigVetorizacao(ModoVetorizacao.BOW, 1)).fit_transform(CORPUS)
        tfidf = construir_vetorizador(ConfigVetorizacao(ModoVetorizacao.TFIDF, 1)).fit_transform(CORPUS)
        self.assertTrue((bow.data == bow.data.astype(int)).all())
        self.assertTrue((tfidf.data <= 1.0).all(), "tf-idf normalizado deveria ficar em [0, 1]")

    def test_bigrama_aumenta_o_vocabulario(self):
        so_uni = construir_vetorizador(ConfigVetorizacao(ModoVetorizacao.BOW, 1)).fit(CORPUS)
        com_bi = construir_vetorizador(ConfigVetorizacao(ModoVetorizacao.BOW, 2)).fit(CORPUS)
        self.assertGreater(len(com_bi.vocabulary_), len(so_uni.vocabulary_))
        self.assertIn("prazo venceu", com_bi.vocabulary_)


class TestePipeline(unittest.TestCase):
    def test_pipeline_tem_vetorizador_e_classificador(self):
        p = construir_pipeline_de_medicao(VETORIZACAO_REFERENCIA)
        self.assertEqual(list(p.named_steps), ["vetorizador", "classificador"])

    def test_pipeline_treina_e_prediz(self):
        p = construir_pipeline_de_medicao(VETORIZACAO_REFERENCIA)
        p.fit(CORPUS, ["consulta", "consulta", "transacao"])
        self.assertEqual(len(p.predict(["prazo venceu ?"])), 1)

    def test_classificador_e_deterministico(self):
        # Requisito da régua: mesma entrada, mesma saída, sempre.
        rotulos = ["consulta", "consulta", "transacao"]
        a = construir_pipeline_de_medicao(VETORIZACAO_REFERENCIA).fit(CORPUS, rotulos).predict(CORPUS)
        b = construir_pipeline_de_medicao(VETORIZACAO_REFERENCIA).fit(CORPUS, rotulos).predict(CORPUS)
        self.assertListEqual(list(a), list(b))


if __name__ == "__main__":
    unittest.main(verbosity=2)
