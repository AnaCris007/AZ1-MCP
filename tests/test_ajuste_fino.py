# Testes da busca de hiperparâmetros do modelo.
#
# A garantia central é a de `TesteComparacaoPareada`: toda tabela do relatório
# precisa sair. Com regiões disjuntas no espaço de busca, nenhum grupo pareado
# fica completo e as tabelas somem sem erro.

from __future__ import annotations

import unittest

from pln.ajuste_fino import (
    EIXOS_ANALISADOS,
    GRADE_ALPHA,
    Candidato,
    ResultadoDoAjuste,
    comparar_eixo,
    config_da_linha,
    escapar_para_tabela,
    escolher_mais_simples,
    gerar_bloco_de_configuracao,
    montar_candidatos,
    rotular,
)
from pln.classificador import (
    ALPHA_PADRAO,
    CONFIG_PRE_PADRAO,
    CONFIG_VET_PADRAO,
    FIT_PRIOR_PADRAO,
)
from pln.preprocessamento import ConfigPreprocessamento, ModoMorfologia, ModoStopwords, Tokenizacao
from pln.vetorizacao import ConfigVetorizacao, ModoVetorizacao

TEXTO_CRU = ConfigPreprocessamento(tokenizacao=Tokenizacao.SPLIT)
BOW = ConfigVetorizacao(ModoVetorizacao.BOW, n_max=1)
TFIDF = ConfigVetorizacao(ModoVetorizacao.TFIDF, n_max=1)


def resultado(suavizacao, fit_prior, f1, config_vet=BOW, config_pre=TEXTO_CRU, desvio=0.0):
    return ResultadoDoAjuste(Candidato(config_pre, config_vet, suavizacao, fit_prior), f1, desvio)


class TesteEspacoDeBusca(unittest.TestCase):
    def test_cobre_o_produto_cartesiano_completo(self):
        # O classificador não é eixo: é sempre `MultinomialNB`, o mesmo da régua
        # do experimento. Sobram vetorização, suavização e priori.
        candidatos = montar_candidatos([TEXTO_CRU])
        self.assertEqual(len({c.config_vet for c in candidatos}), 4)
        self.assertEqual({c.suavizacao for c in candidatos}, set(GRADE_ALPHA))
        self.assertEqual({c.fit_prior for c in candidatos}, {True, False})
        self.assertEqual(len(candidatos), 4 * len(GRADE_ALPHA) * 2)

    def test_o_classificador_nao_e_eixo_de_busca(self):
        self.assertNotIn("variante", EIXOS_ANALISADOS)
        self.assertFalse(hasattr(Candidato(TEXTO_CRU, BOW, 1.0, True), "variante"))


class TesteComparacaoPareada(unittest.TestCase):
    def setUp(self):
        self.resultados = [
            resultado(s, p, 0.9, config_vet=vet)
            for s in (0.1, 1.0)
            for p in (True, False)
            for vet in (BOW, TFIDF)
        ]

    def test_comparar_no_espaco_inteiro_produz_a_tabela(self):
        # Com regiões disjuntas esta chamada devolvia lista vazia, e lista vazia
        # vira tabela ausente no relatório, não erro.
        linhas = comparar_eixo(self.resultados, "suavizacao")
        self.assertEqual({rotulo for rotulo, _, _ in linhas}, {"0.1", "1.0"})

    def test_todo_eixo_analisado_rende_tabela(self):
        for eixo in EIXOS_ANALISADOS:
            with self.subTest(eixo=eixo):
                self.assertTrue(comparar_eixo(self.resultados, eixo),
                                f"o eixo `{eixo}` não produz tabela")

    def test_eixo_constante_nao_rende_tabela(self):
        constantes = [r for r in self.resultados if r.candidato.suavizacao == 1.0]
        self.assertEqual(comparar_eixo(constantes, "suavizacao"), [])


class TesteRotulos(unittest.TestCase):
    def test_config_de_vetorizacao_sai_legivel(self):
        # O `str()` cru de um dataclass é ilegível numa tabela.
        self.assertEqual(rotular(BOW), "bow n=1")
        self.assertNotIn("ConfigVetorizacao", rotular(BOW))

    def test_enum_sai_pelo_valor(self):
        self.assertEqual(rotular(ModoVetorizacao.TFIDF), "tfidf")

    def test_booleano_sai_como_texto(self):
        self.assertEqual(rotular(True), "True")


class TesteDesempate(unittest.TestCase):
    def test_escolhe_a_mais_simples_entre_as_empatadas(self):
        # Empate é "dentro de um desvio padrão da melhor".
        bigrama = ConfigVetorizacao(ModoVetorizacao.BOW, n_max=2)
        resultados = [
            resultado(1.0, True, 1.00, config_vet=bigrama, desvio=0.05),
            resultado(1.0, True, 0.99, config_vet=BOW, desvio=0.05),
        ]
        self.assertEqual(escolher_mais_simples(resultados).candidato.config_vet.n_max, 1)

    def test_prefere_menos_etapas_de_preprocessamento(self):
        muitas = ConfigPreprocessamento(
            minusculas=True, remover_acentos=True, remover_pontuacao=True,
            tokenizacao=Tokenizacao.SPLIT,
        )
        resultados = [
            resultado(1.0, True, 1.00, config_pre=muitas, desvio=0.05),
            resultado(1.0, True, 0.99, config_pre=TEXTO_CRU, desvio=0.05),
        ]
        escolhido = escolher_mais_simples(resultados).candidato
        self.assertEqual(escolhido.config_pre.etapas_ativas_na_ordem(), ())

    def test_nao_escolhe_fora_do_empate(self):
        resultados = [
            resultado(1.0, True, 0.99, config_pre=TEXTO_CRU, desvio=0.0),
            resultado(1.0, True, 0.10, config_pre=TEXTO_CRU, desvio=0.0),
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
        codigo = self.bloco(Candidato(TEXTO_CRU, BOW, 1.0, True))
        escopo = {
            "ConfigPreprocessamento": ConfigPreprocessamento,
            "ConfigVetorizacao": ConfigVetorizacao,
            "ModoVetorizacao": ModoVetorizacao,
            "ModoStopwords": ModoStopwords,
            "ModoMorfologia": ModoMorfologia,
            "Tokenizacao": Tokenizacao,
        }
        exec(codigo, escopo)  # noqa: S102 — é exatamente o que se quer verificar
        self.assertEqual(escopo["CONFIG_PRE_PADRAO"], TEXTO_CRU)
        self.assertEqual(escopo["CONFIG_VET_PADRAO"], BOW)

    def test_nao_usa_repr_de_dataclass(self):
        codigo = self.bloco(Candidato(TEXTO_CRU, BOW, 1.0, True))
        self.assertNotIn("<", codigo, "o bloco tem repr de enum, que não compila")

    def test_omite_campos_no_valor_padrao(self):
        # Um construtor com os sete campos explícitos é ilegível e esconde qual
        # deles foi de fato uma escolha.
        codigo = self.bloco(Candidato(TEXTO_CRU, BOW, 1.0, True))
        self.assertNotIn("minusculas=False", codigo)
        self.assertNotIn("ordem=", codigo)

    def test_registra_a_tokenizacao_mesmo_no_padrao(self):
        # A tokenização é a exceção: entra sempre, porque é decisão registrada.
        codigo = self.bloco(Candidato(TEXTO_CRU, BOW, 1.0, True))
        self.assertIn("tokenizacao=Tokenizacao.SPLIT", codigo)

    def test_emite_os_dois_parametros_do_modelo(self):
        codigo = self.bloco(Candidato(TEXTO_CRU, BOW, 1.0, True))
        self.assertIn("ALPHA_PADRAO", codigo)
        self.assertIn("FIT_PRIOR_PADRAO", codigo)
        self.assertNotIn("VARIANTE_PADRAO", codigo)

    def test_o_bloco_reproduz_os_padroes_em_vigor(self):
        # Fecha o ciclo: o que o relatório manda colar é o que está colado.
        # Se alguém editar `classificador.py` à mão sem rodar o ajuste fino, ou
        # mudar o formato do bloco, este teste acusa.
        atual = Candidato(CONFIG_PRE_PADRAO, CONFIG_VET_PADRAO, ALPHA_PADRAO, FIT_PRIOR_PADRAO)
        codigo = self.bloco(atual)
        self.assertIn(f"FIT_PRIOR_PADRAO  = {FIT_PRIOR_PADRAO!r}", codigo)
        self.assertIn(f"ALPHA_PADRAO      = {ALPHA_PADRAO!r}", codigo)


class TesteEscapeDeTabela(unittest.TestCase):
    def test_barra_vertical_e_escapada(self):
        # `descrever()` usa `|` como separador, e `|` delimita coluna em markdown.
        # Sem escapar, uma configuração vira três colunas e a tabela desalinha.
        descricao = Candidato(TEXTO_CRU, BOW, 1.0, True).descrever()
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
