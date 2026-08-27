# Testes do módulo de vetorização.

from __future__ import annotations

import unittest

from sklearn.feature_extraction.text import CountVectorizer, TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB

from pln.vetorizacao import (
    JANELAS_NGRAMA,
    ConfigVetorizacao,
    ModoVetorizacao,
    construir_pipeline_de_medicao,
    construir_vetorizador,
    todas_as_vetorizacoes,
)

TFIDF_UNIGRAMA = ConfigVetorizacao(ModoVetorizacao.TFIDF, n_max=1)

CORPUS = ["prazo venceu ?", "prazo venceu ?", "registra o marco ."]


class TesteEspacoDeVetorizacao(unittest.TestCase):
    def test_cada_modo_entra_uma_vez_por_janela(self):
        self.assertEqual(len(todas_as_vetorizacoes()), 2 * len(JANELAS_NGRAMA))

    def test_sem_duplicatas(self):
        opcoes = todas_as_vetorizacoes()
        self.assertEqual(len(set(opcoes)), len(opcoes), "há vetorizações duplicadas")

    def test_todo_modo_aparece(self):
        modos = {v.modo for v in todas_as_vetorizacoes()}
        self.assertEqual(modos, set(ModoVetorizacao))

    def test_tfidf_unigrama_esta_no_espaco(self):
        self.assertIn(TFIDF_UNIGRAMA, todas_as_vetorizacoes())

    def test_descricao_curta(self):
        self.assertEqual(ConfigVetorizacao(ModoVetorizacao.BOW, 1).descrever(), "bow n=1")
        self.assertEqual(ConfigVetorizacao(ModoVetorizacao.TFIDF, 2).descrever(), "tfidf n=1-2")


class TesteNaoRetokeniza(unittest.TestCase):
    # Com os padrões do sklearn ligados, as etapas `minusculas` e
    # `remover_pontuacao` e a escolha de tokenizador deixam de ter efeito, e o
    # experimento passa a medir errado sem falhar.

    def test_padroes_do_sklearn_estao_desligados(self):
        v = construir_vetorizador(TFIDF_UNIGRAMA)
        self.assertFalse(v.lowercase, "lowercase ligado anularia a etapa `minusculas`")
        self.assertIs(v.tokenizer, str.split, "tokenizer próprio anularia a escolha de tokenização")
        self.assertIsNone(v.token_pattern, "token_pattern ativo descartaria pontuação")

    def test_pontuacao_sobrevive_como_token(self):
        v = construir_vetorizador(TFIDF_UNIGRAMA)
        v.fit(CORPUS)
        self.assertIn("?", v.vocabulary_)

    def test_maiuscula_e_minuscula_ficam_distintas(self):
        v = construir_vetorizador(TFIDF_UNIGRAMA)
        v.fit(["Prazo prazo"])
        self.assertIn("Prazo", v.vocabulary_)
        self.assertIn("prazo", v.vocabulary_)

    def test_token_de_uma_letra_nao_e_descartado(self):
        # O token_pattern padrão exige duas letras e descartaria "o", "e", "a".
        v = construir_vetorizador(TFIDF_UNIGRAMA)
        v.fit(["o marco e o prazo"])
        self.assertIn("o", v.vocabulary_)


class TesteModosEJanelas(unittest.TestCase):
    def test_bow_e_tfidf_usam_classes_diferentes(self):
        self.assertIsInstance(construir_vetorizador(ConfigVetorizacao(ModoVetorizacao.BOW, 1)), CountVectorizer)
        self.assertIsInstance(construir_vetorizador(ConfigVetorizacao(ModoVetorizacao.TFIDF, 1)), TfidfVectorizer)

    def test_bow_conta_e_tfidf_pondera(self):
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
        p = construir_pipeline_de_medicao(TFIDF_UNIGRAMA)
        self.assertEqual(list(p.named_steps), ["vetorizador", "classificador"])

    def test_pipeline_treina_e_prediz(self):
        p = construir_pipeline_de_medicao(TFIDF_UNIGRAMA)
        p.fit(CORPUS, ["consulta", "consulta", "transacao"])
        self.assertEqual(len(p.predict(["prazo venceu ?"])), 1)

    def test_classificador_e_deterministico(self):
        rotulos = ["consulta", "consulta", "transacao"]
        a = construir_pipeline_de_medicao(TFIDF_UNIGRAMA).fit(CORPUS, rotulos).predict(CORPUS)
        b = construir_pipeline_de_medicao(TFIDF_UNIGRAMA).fit(CORPUS, rotulos).predict(CORPUS)
        self.assertListEqual(list(a), list(b))


class TesteReguaUnica(unittest.TestCase):
    # A régua já mudou conforme a vetorização, o que tornava a comparação entre
    # elas confundida: o classificador variava junto com a representação. Estes
    # testes quebram se alguém acrescentar uma vetorização que a régua não atenda.

    def test_a_regua_e_a_mesma_em_todo_o_espaco_de_busca(self):
        classificadores = [
            construir_pipeline_de_medicao(v).named_steps["classificador"]
            for v in todas_as_vetorizacoes()
        ]
        for c in classificadores:
            self.assertIsInstance(c, MultinomialNB)
        primeiro = classificadores[0].get_params()
        for c in classificadores[1:]:
            self.assertEqual(c.get_params(), primeiro)

    def test_toda_vetorizacao_do_espaco_alimenta_a_regua(self):
        # Entrada negativa faria o `MultinomialNB` recusar a matriz.
        rotulos = ["a", "a", "b"]
        for v in todas_as_vetorizacoes():
            with self.subTest(vetorizacao=v.descrever()):
                p = construir_pipeline_de_medicao(v).fit(CORPUS, rotulos)
                self.assertEqual(len(p.predict(CORPUS)), len(CORPUS))


if __name__ == "__main__":
    unittest.main(verbosity=2)
