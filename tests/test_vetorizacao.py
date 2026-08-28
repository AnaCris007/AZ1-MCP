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
from sklearn.naive_bayes import GaussianNB, MultinomialNB

from pln.vetorizacao import (
    JANELAS_NGRAMA,
    MODELO_DE_VETORES,
    ConfigVetorizacao,
    ModoVetorizacao,
    carregar_vetores,
    construir_pipeline_de_medicao,
    construir_vetorizador,
    todas_as_vetorizacoes,
)

# TF-IDF com unigrama: a escolha convencional da área, usada aqui como fixture
# por não favorecer nenhuma estratégia de tokenização em particular.
#
# Já foi uma constante de `vetorizacao.py` chamada VETORIZACAO_REFERENCIA, que
# existia para servir de régua na busca em duas fases. A busca em duas fases foi
# removida; a constante perdeu a razão de existir no código de produção e passou
# a morar aqui, onde ainda tem uma.
TFIDF_UNIGRAMA = ConfigVetorizacao(ModoVetorizacao.TFIDF, n_max=1)
EMBEDDING = ConfigVetorizacao(ModoVetorizacao.EMBEDDING, n_max=1)

CORPUS = ["prazo venceu ?", "prazo venceu ?", "registra o marco ."]


class TesteEspacoDeVetorizacao(unittest.TestCase):
    def test_esparsas_variam_a_janela_a_densa_nao(self):
        # As duas esparsas entram uma vez por janela de n-grama; a densa não tem
        # janela onde um bigrama caberia, e entra UMA vez. Gerá-la duas vezes
        # produziria duas linhas idênticas no ranking, dando a impressão de duas
        # medições independentes.
        opcoes = todas_as_vetorizacoes()
        esparsas = [v for v in opcoes if not v.produz_vetores_densos()]
        densas = [v for v in opcoes if v.produz_vetores_densos()]
        self.assertEqual(len(esparsas), 2 * len(JANELAS_NGRAMA))
        self.assertEqual(len(densas), 1)

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
    # A garantia central: o vetorizador respeita a tokenização já feita.

    def test_padroes_do_sklearn_estao_desligados(self):
        v = construir_vetorizador(TFIDF_UNIGRAMA)
        self.assertFalse(v.lowercase, "lowercase ligado anularia a etapa `minusculas`")
        self.assertIs(v.tokenizer, str.split, "tokenizer próprio anularia a escolha de tokenização")
        self.assertIsNone(v.token_pattern, "token_pattern ativo descartaria pontuação")

    def test_pontuacao_sobrevive_como_token(self):
        # "?" é evidência: separa pergunta (consulta/alerta) de ordem
        # (transação). Com o token_pattern padrão do sklearn ele seria
        # descartado em silêncio.
        v = construir_vetorizador(TFIDF_UNIGRAMA)
        v.fit(CORPUS)
        self.assertIn("?", v.vocabulary_)

    def test_maiuscula_e_minuscula_ficam_distintas(self):
        v = construir_vetorizador(TFIDF_UNIGRAMA)
        v.fit(["Prazo prazo"])
        self.assertIn("Prazo", v.vocabulary_)
        self.assertIn("prazo", v.vocabulary_)

    def test_token_de_uma_letra_nao_e_descartado(self):
        # O token_pattern padrão exige duas letras (\w\w+) e comeria "o", "e", "a".
        v = construir_vetorizador(TFIDF_UNIGRAMA)
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
        p = construir_pipeline_de_medicao(TFIDF_UNIGRAMA)
        self.assertEqual(list(p.named_steps), ["vetorizador", "classificador"])

    def test_pipeline_treina_e_prediz(self):
        p = construir_pipeline_de_medicao(TFIDF_UNIGRAMA)
        p.fit(CORPUS, ["consulta", "consulta", "transacao"])
        self.assertEqual(len(p.predict(["prazo venceu ?"])), 1)

    def test_classificador_e_deterministico(self):
        # Requisito da régua: mesma entrada, mesma saída, sempre.
        rotulos = ["consulta", "consulta", "transacao"]
        a = construir_pipeline_de_medicao(TFIDF_UNIGRAMA).fit(CORPUS, rotulos).predict(CORPUS)
        b = construir_pipeline_de_medicao(TFIDF_UNIGRAMA).fit(CORPUS, rotulos).predict(CORPUS)
        self.assertListEqual(list(a), list(b))


class TesteVetorizacaoDensa(unittest.TestCase):
    # A vetorização densa carrega o modelo do spaCy. Se ele não estiver baixado,
    # o teste diz o que fazer em vez de falhar com um erro de carregamento.
    def setUp(self):
        try:
            carregar_vetores(MODELO_DE_VETORES)
        except RuntimeError as erro:
            self.skipTest(str(erro))

    def test_produz_matriz_densa_de_largura_fixa(self):
        # A largura não depende do corpus: são sempre as mesmas dimensões do
        # modelo, venham 3 documentos ou 3000. É o oposto de uma esparsa.
        v = construir_vetorizador(EMBEDDING)
        curto = v.fit_transform(CORPUS)
        longo = v.fit_transform([*CORPUS, "obra risco prazo cronograma marco"])
        self.assertEqual(curto.shape[1], longo.shape[1])
        self.assertEqual(curto.shape[0], len(CORPUS))

    def test_tem_valores_negativos(self):
        # É por isso que Multinomial e Complement não servem para esta família —
        # ver `variantes_compativeis` em classificador.py. Se este teste passar a
        # falhar, a incompatibilidade deixou de existir e a regra pode mudar.
        matriz = construir_vetorizador(EMBEDDING).fit_transform(CORPUS)
        self.assertTrue((matriz < 0).any())

    def test_respeita_a_tokenizacao_recebida(self):
        # O MESMO teste que `TesteNaoRetokeniza` faz para as esparsas, na versão
        # densa. O caminho fácil seria `nlp(texto).vector`, que retokeniza com as
        # regras do spaCy e jogaria fora a tokenização escolhida pelo
        # pré-processamento — fazendo as três estratégias darem resultado idêntico.
        v = construir_vetorizador(EMBEDDING)
        com_pontuacao_grudada = v.fit_transform(["prazo venceu?"])
        separado = v.fit_transform(["prazo venceu ?"])
        self.assertFalse(
            (com_pontuacao_grudada == separado).all(),
            "o vetorizador denso retokenizou: a tokenização do pré-processamento foi ignorada",
        )

    def test_documento_sem_token_conhecido_vira_vetor_nulo(self):
        matriz = construir_vetorizador(EMBEDDING).fit_transform(["xkcdqq zzzwww"])
        self.assertTrue((matriz == 0).all())

    def test_pipeline_de_medicao_usa_gaussiano(self):
        # A régua muda com a família da vetorização, porque tem que mudar: não
        # existe Naive Bayes que trate contagem esparsa e coordenada densa com a
        # mesma suposição.
        denso = construir_pipeline_de_medicao(EMBEDDING).named_steps["classificador"]
        esparso = construir_pipeline_de_medicao(TFIDF_UNIGRAMA).named_steps["classificador"]
        self.assertIsInstance(denso, GaussianNB)
        self.assertIsInstance(esparso, MultinomialNB)

    def test_pipeline_denso_treina_e_prediz(self):
        rotulos = ["a", "a", "b"]
        p = construir_pipeline_de_medicao(EMBEDDING).fit(CORPUS, rotulos)
        self.assertEqual(len(p.predict(CORPUS)), len(CORPUS))


if __name__ == "__main__":
    unittest.main(verbosity=2)
