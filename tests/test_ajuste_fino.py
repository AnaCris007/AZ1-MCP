# =============================================================================
# test_ajuste_fino.py — Testes da busca de hiperparâmetros do modelo final
# =============================================================================
#     python -m unittest discover tests -v
#
# A garantia central deste arquivo é a de `TesteComparacaoPorFamilia`. O espaço
# de busca tem duas regiões DISJUNTAS — `gaussiano` só existe com vetorização
# densa, as outras três variantes só com esparsa — e uma comparação pareada
# ingênua exige grupos completos que nunca vão existir. Quando isso aconteceu, o
# efeito não foi um erro: as tabelas simplesmente SUMIRAM do relatório. Os
# testes abaixo falham se voltarem a sumir.
# =============================================================================

from __future__ import annotations

import unittest

from pln.ajuste_fino import (
    EIXOS_ANALISADOS,
    GRADE_ALPHA,
    GRADE_VAR_SMOOTHING,
    Candidato,
    ResultadoDoAjuste,
    comparar_eixo,
    config_da_linha,
    escapar_para_tabela,
    escolher_mais_simples,
    gerar_bloco_de_configuracao,
    grade_de_prior,
    grade_de_suavizacao,
    melhor_por_familia,
    montar_candidatos,
    rotular,
    separar_por_familia,
)
from pln.classificador import (
    ALPHA_PADRAO,
    CONFIG_PRE_PADRAO,
    CONFIG_VET_PADRAO,
    FIT_PRIOR_PADRAO,
    VARIANTE_PADRAO,
    VarianteNB,
)
from pln.preprocessamento import ConfigPreprocessamento, ModoMorfologia, ModoStopwords, Tokenizacao
from pln.vetorizacao import ConfigVetorizacao, ModoVetorizacao

TEXTO_CRU = ConfigPreprocessamento(tokenizacao=Tokenizacao.SPLIT)
BOW = ConfigVetorizacao(ModoVetorizacao.BOW, n_max=1)
TFIDF = ConfigVetorizacao(ModoVetorizacao.TFIDF, n_max=1)
EMBEDDING = ConfigVetorizacao(ModoVetorizacao.EMBEDDING, n_max=1)


def resultado(variante, suavizacao, fit_prior, f1, config_vet=BOW, config_pre=TEXTO_CRU, desvio=0.0):
    return ResultadoDoAjuste(Candidato(config_pre, config_vet, variante, suavizacao, fit_prior), f1, desvio)


class TesteEspacoDeBusca(unittest.TestCase):
    def test_nao_gera_combinacao_impossivel(self):
        # Toda a razão de `variantes_compativeis` existir: `gaussiano` com uma
        # matriz esparsa de contagem, ou `multinomial` com vetores negativos,
        # não são configurações ruins — são erro de execução.
        for candidato in montar_candidatos([TEXTO_CRU]):
            denso = candidato.config_vet.produz_vetores_densos()
            gaussiano = candidato.variante is VarianteNB.GAUSSIANO
            self.assertEqual(denso, gaussiano, f"combinação impossível: {candidato.descrever()}")

    def test_cada_variante_recebe_a_sua_grade(self):
        self.assertEqual(grade_de_suavizacao(VarianteNB.GAUSSIANO), GRADE_VAR_SMOOTHING)
        self.assertEqual(grade_de_suavizacao(VarianteNB.MULTINOMIAL), GRADE_ALPHA)

    def test_as_grades_vivem_em_escalas_diferentes(self):
        # O ponto não é que os conjuntos sejam disjuntos — `0.1` está nos dois, e
        # tudo bem. O ponto é a ESCALA: `alpha` orbita o padrão 1,0 do
        # scikit-learn, e `var_smoothing` orbita o padrão 1e-9. Varrer a
        # gaussiana com a grade de alpha testaria seis valores destrutivos, todos
        # oito ordens de grandeza acima do razoável.
        self.assertGreaterEqual(min(GRADE_ALPHA), 1e-3)
        self.assertLessEqual(min(GRADE_VAR_SMOOTHING), 1e-9)
        self.assertLess(min(GRADE_VAR_SMOOTHING), min(GRADE_ALPHA) / 1e6)

    def test_gaussiano_nao_varre_fit_prior(self):
        # GaussianNB não tem `fit_prior`. Varrer os dois valores geraria duas
        # linhas idênticas com nomes diferentes.
        self.assertEqual(len(grade_de_prior(VarianteNB.GAUSSIANO)), 1)
        self.assertEqual(len(grade_de_prior(VarianteNB.BERNOULLI)), 2)


class TesteComparacaoPorFamilia(unittest.TestCase):
    def setUp(self):
        self.resultados = [
            resultado(v, s, p, 0.9, config_vet=vet)
            for v in (VarianteNB.MULTINOMIAL, VarianteNB.COMPLEMENT, VarianteNB.BERNOULLI)
            for s in (0.1, 1.0)
            for p in (True, False)
            for vet in (BOW, TFIDF)
        ] + [
            resultado(VarianteNB.GAUSSIANO, s, True, 0.8, config_vet=EMBEDDING)
            for s in (1e-9, 1e-3)
        ]

    def test_separa_as_duas_regioes(self):
        familias = dict(separar_por_familia(self.resultados))
        self.assertEqual(set(familias), {"esparsa", "densa"})
        self.assertEqual(len(familias["densa"]), 2)
        self.assertEqual(len(familias["esparsa"]), 24)

    def test_comparar_no_espaco_inteiro_nao_produz_nada(self):
        # Documenta o defeito original: nenhuma combinação tem as quatro
        # variantes, porque não pode ter. Comparar sem separar devolve lista
        # vazia — e uma lista vazia vira uma tabela ausente, não um erro.
        self.assertEqual(comparar_eixo(self.resultados, "variante"), [])

    def test_comparar_dentro_da_familia_produz_a_tabela(self):
        esparsos = dict(separar_por_familia(self.resultados))["esparsa"]
        linhas = comparar_eixo(esparsos, "variante")
        self.assertEqual({rotulo for rotulo, _, _ in linhas},
                         {"multinomial", "complement", "bernoulli"})

    def test_todo_eixo_analisado_rende_tabela_em_alguma_familia(self):
        # Se um eixo parar de render tabela em qualquer região, ele sumiu do
        # relatório — que foi exatamente o defeito.
        for eixo in EIXOS_ANALISADOS:
            with self.subTest(eixo=eixo):
                rendeu = any(
                    comparar_eixo(grupo, eixo)
                    for _, grupo in separar_por_familia(self.resultados)
                )
                self.assertTrue(rendeu, f"o eixo `{eixo}` não produz tabela em nenhuma família")

    def test_eixo_constante_nao_rende_tabela(self):
        densos = dict(separar_por_familia(self.resultados))["densa"]
        self.assertEqual(comparar_eixo(densos, "variante"), [])

    def test_melhor_de_cada_familia(self):
        melhores = dict(melhor_por_familia(self.resultados))
        self.assertAlmostEqual(melhores["esparsa"].f1_medio, 0.9)
        self.assertAlmostEqual(melhores["densa"].f1_medio, 0.8)


class TesteRotulos(unittest.TestCase):
    def test_config_de_vetorizacao_sai_legivel(self):
        # O `str()` cru de um dataclass é ilegível numa tabela.
        self.assertEqual(rotular(BOW), "bow n=1")
        self.assertNotIn("ConfigVetorizacao", rotular(BOW))

    def test_enum_sai_pelo_valor(self):
        self.assertEqual(rotular(VarianteNB.COMPLEMENT), "complement")

    def test_booleano_sai_como_texto(self):
        self.assertEqual(rotular(True), "True")


class TesteDesempate(unittest.TestCase):
    def test_escolhe_a_mais_simples_entre_as_empatadas(self):
        # Empate é "dentro de um desvio padrão da melhor". Entre empatadas, a
        # esparsa ganha da densa: não depende de baixar um modelo de 40 MB.
        resultados = [
            resultado(VarianteNB.GAUSSIANO, 1e-9, True, 1.00, config_vet=EMBEDDING, desvio=0.05),
            resultado(VarianteNB.MULTINOMIAL, 1.0, True, 0.99, desvio=0.05),
        ]
        self.assertFalse(escolher_mais_simples(resultados).candidato.config_vet.produz_vetores_densos())

    def test_prefere_menos_etapas_de_preprocessamento(self):
        muitas = ConfigPreprocessamento(
            minusculas=True, remover_acentos=True, remover_pontuacao=True,
            tokenizacao=Tokenizacao.SPLIT,
        )
        resultados = [
            resultado(VarianteNB.MULTINOMIAL, 1.0, True, 1.00, config_pre=muitas, desvio=0.05),
            resultado(VarianteNB.MULTINOMIAL, 1.0, True, 0.99, config_pre=TEXTO_CRU, desvio=0.05),
        ]
        escolhido = escolher_mais_simples(resultados).candidato
        self.assertEqual(escolhido.config_pre.etapas_ativas_na_ordem(), ())

    def test_nao_escolhe_fora_do_empate(self):
        resultados = [
            resultado(VarianteNB.MULTINOMIAL, 1.0, True, 0.99, config_pre=TEXTO_CRU, desvio=0.0),
            resultado(VarianteNB.MULTINOMIAL, 1.0, True, 0.10, config_pre=TEXTO_CRU, desvio=0.0),
        ]
        self.assertAlmostEqual(escolher_mais_simples(resultados).f1_medio, 0.99)


class TesteBlocoDeConfiguracao(unittest.TestCase):
    # O relatório termina com um bloco rotulado "valores para classificador.py".
    # Se ele não for Python válido, o rótulo é mentira — e era: o `repr()` de um
    # dataclass com enums imprime `<ModoStopwords.MANTER: 'manter'>`, que não
    # compila, além de listar todos os campos no valor padrão.

    def bloco(self, candidato):
        linhas = gerar_bloco_de_configuracao(candidato)
        self.assertEqual(linhas[0], "```python")
        self.assertEqual(linhas[-1], "```")
        return "\n".join(linhas[1:-1])

    def test_o_bloco_e_python_valido_e_executavel(self):
        # Executa o bloco com os mesmos nomes que `classificador.py` tem em
        # escopo. Se não compilar ou faltar um import, quebra aqui.
        codigo = self.bloco(Candidato(TEXTO_CRU, BOW, VarianteNB.MULTINOMIAL, 1.0, True))
        escopo = {
            "ConfigPreprocessamento": ConfigPreprocessamento,
            "ConfigVetorizacao": ConfigVetorizacao,
            "ModoVetorizacao": ModoVetorizacao,
            "ModoStopwords": ModoStopwords,
            "ModoMorfologia": ModoMorfologia,
            "Tokenizacao": Tokenizacao,
            "VarianteNB": VarianteNB,
        }
        exec(codigo, escopo)  # noqa: S102 — é exatamente o que se quer verificar
        self.assertEqual(escopo["CONFIG_PRE_PADRAO"], TEXTO_CRU)
        self.assertEqual(escopo["CONFIG_VET_PADRAO"], BOW)
        self.assertIs(escopo["VARIANTE_PADRAO"], VarianteNB.MULTINOMIAL)

    def test_nao_usa_repr_de_dataclass(self):
        codigo = self.bloco(Candidato(TEXTO_CRU, BOW, VarianteNB.MULTINOMIAL, 1.0, True))
        self.assertNotIn("<", codigo, "o bloco tem repr de enum, que não compila")

    def test_omite_campos_no_valor_padrao(self):
        # Um construtor com os sete campos explícitos é ilegível e esconde qual
        # deles foi de fato uma escolha.
        codigo = self.bloco(Candidato(TEXTO_CRU, BOW, VarianteNB.MULTINOMIAL, 1.0, True))
        self.assertNotIn("minusculas=False", codigo)
        self.assertNotIn("ordem=", codigo)

    def test_registra_a_tokenizacao_mesmo_no_padrao(self):
        # A tokenização é a exceção: entra sempre, porque é decisão registrada.
        codigo = self.bloco(Candidato(TEXTO_CRU, BOW, VarianteNB.MULTINOMIAL, 1.0, True))
        self.assertIn("tokenizacao=Tokenizacao.SPLIT", codigo)

    def test_gaussiano_nao_emite_fit_prior(self):
        # GaussianNB não tem `fit_prior`; colar a linha daria TypeError.
        codigo = self.bloco(Candidato(TEXTO_CRU, EMBEDDING, VarianteNB.GAUSSIANO, 1e-9, True))
        self.assertNotIn("FIT_PRIOR_PADRAO", codigo)

    def test_o_bloco_reproduz_os_padroes_em_vigor(self):
        # Fecha o ciclo: o que o relatório manda colar é o que está colado.
        # Se alguém editar `classificador.py` à mão sem rodar o ajuste fino, ou
        # mudar o formato do bloco, este teste acusa.
        atual = Candidato(
            CONFIG_PRE_PADRAO, CONFIG_VET_PADRAO, VARIANTE_PADRAO, ALPHA_PADRAO, FIT_PRIOR_PADRAO
        )
        codigo = self.bloco(atual)
        self.assertIn(f"VarianteNB.{VARIANTE_PADRAO.name}", codigo)
        self.assertIn(f"ALPHA_PADRAO      = {ALPHA_PADRAO!r}", codigo)


class TesteEscapeDeTabela(unittest.TestCase):
    def test_barra_vertical_e_escapada(self):
        # `descrever()` usa `|` como separador, e `|` delimita coluna em markdown.
        # Sem escapar, uma configuração vira três colunas e a tabela desalinha.
        descricao = Candidato(TEXTO_CRU, BOW, VarianteNB.MULTINOMIAL, 1.0, True).descrever()
        self.assertIn("|", descricao)
        self.assertNotIn("|", escapar_para_tabela(descricao).replace("\\|", ""))


class TesteLeituraDoRelatorio(unittest.TestCase):
    def test_reconstroi_a_configuracao_a_partir_do_csv(self):
        # O CSV do experimento grava cada campo em coluna própria justamente
        # para permitir a volta sem interpretar a string de descrição.
        linha = {
            "minusculas": "True", "remover_acentos": "False",
            "remover_pontuacao": "True", "remover_numeros": "False",
            "stopwords": "preservar_negacoes", "morfologia": "stemming",
            "tokenizacao": "regex",
        }
        config = config_da_linha(linha)
        self.assertTrue(config.minusculas)
        self.assertFalse(config.remover_acentos)
        self.assertIs(config.stopwords, ModoStopwords.PRESERVAR_NEGACOES)
        self.assertIs(config.morfologia, ModoMorfologia.STEMMING)
        self.assertIs(config.tokenizacao, Tokenizacao.REGEX)


if __name__ == "__main__":
    unittest.main(verbosity=2)
