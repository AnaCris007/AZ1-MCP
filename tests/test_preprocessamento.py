# Testes das etapas, modos, tokenização e ordem do pré-processamento.
#
# Cada etapa é testada isolada, ligada sozinha e com as demais desligadas: se um
# desses testes quebrar quando outra etapa mudar, houve acoplamento indevido.

from __future__ import annotations

import unittest

from pln.preprocessamento import (
    ETAPAS,
    NEGACOES,
    ConfigPreprocessamento,
    ModoMorfologia,
    ModoStopwords,
    Tokenizacao,
    lematizar,
    preprocessar,
    reduzir_palavra_ao_radical,
    tokenizar,
)


class TesteEtapasIsoladas(unittest.TestCase):
    def test_nenhuma_etapa_preserva_o_texto(self):
        texto = "Qual é o STATUS do RF01, hoje?"
        self.assertEqual(preprocessar(texto, ConfigPreprocessamento()), texto)

    def test_minusculas(self):
        config = ConfigPreprocessamento(minusculas=True)
        self.assertEqual(preprocessar("Prazo VENCIDO", config), "prazo vencido")

    def test_remover_acentos(self):
        config = ConfigPreprocessamento(remover_acentos=True)
        self.assertEqual(preprocessar("situação não está órgão", config), "situacao nao esta orgao")

    def test_remover_pontuacao_vira_espaco(self):
        # Vira espaço, não vazio: senão "prazo,marco" colaria num token só.
        config = ConfigPreprocessamento(remover_pontuacao=True)
        self.assertEqual(preprocessar("prazo,marco?", config), "prazo marco")

    def test_remover_numeros(self):
        config = ConfigPreprocessamento(remover_numeros=True)
        self.assertEqual(preprocessar("contrato 4521 do lote 3", config), "contrato do lote")

    def test_radical_e_deterministico(self):
        self.assertEqual(reduzir_palavra_ao_radical("prazos"), reduzir_palavra_ao_radical("prazos"))


class TesteMorfologia(unittest.TestCase):

    FLEXOES = "vencendo vencidos vencer"

    def test_stemming_converge_formas_verbais(self):
        config = ConfigPreprocessamento(morfologia=ModoMorfologia.STEMMING)
        radicais = set(preprocessar(self.FLEXOES, config).split())
        self.assertEqual(len(radicais), 1, f"esperava um radical único, veio {radicais}")

    def test_lematizacao_normaliza_flexoes_em_frase(self):
        config = ConfigPreprocessamento(morfologia=ModoMorfologia.LEMATIZACAO)
        self.assertEqual(preprocessar("Os documentos venceram ontem", config), "o documento vencer ontem")

    def test_lematizacao_devolve_palavra_real_e_stemming_nao(self):
        self.assertEqual(lematizar("vencendo"), "vencer")
        self.assertNotEqual(reduzir_palavra_ao_radical("vencendo"), "vencer")

    def test_lematizacao_depende_do_contexto(self):
        # O lema depende do contexto, então lematizar token solto dá resultado
        # diferente de lematizar a frase. Etapas que destroem a estrutura antes
        # da lematização pioram os lemas, e é por isso que a ordem importa aqui.
        solto = lematizar("vencidos")
        em_frase = lematizar("Os prazos estão vencidos.")
        self.assertNotIn(solto, em_frase.split())

    def test_nenhuma_nao_altera_o_texto(self):
        config = ConfigPreprocessamento(morfologia=ModoMorfologia.NENHUMA)
        self.assertEqual(preprocessar(self.FLEXOES, config), self.FLEXOES)

    def test_os_tres_modos_produzem_saidas_distintas(self):
        saidas = {
            preprocessar(self.FLEXOES, ConfigPreprocessamento(morfologia=modo))
            for modo in ModoMorfologia
        }
        self.assertEqual(len(saidas), 3, f"modos colidiram: {saidas}")

    def test_morfologia_e_exclusiva_por_construcao(self):
        # São valores de um mesmo campo, não duas flags independentes.
        config = ConfigPreprocessamento(morfologia=ModoMorfologia.STEMMING)
        self.assertIs(config.morfologia, ModoMorfologia.STEMMING)
        self.assertEqual(config.etapas_ativas_na_ordem().count("morfologia"), 1)


class TesteTokenizacao(unittest.TestCase):

    FRASE = "O contrato R$1.500,00 do Sr. Silva venceu, sem aditivo!"

    def test_split_nao_separa_pontuacao_grudada(self):
        self.assertIn("venceu,", tokenizar(self.FRASE, Tokenizacao.SPLIT))

    def test_regex_separa_pontuacao(self):
        tokens = tokenizar(self.FRASE, Tokenizacao.REGEX)
        self.assertIn("venceu", tokens)
        self.assertIn(",", tokens)

    def test_linguistico_preserva_numero_e_abreviatura(self):
        # No tokenizador de idioma, "1.500,00" é um número e "Sr." é abreviatura.
        tokens = tokenizar(self.FRASE, Tokenizacao.LINGUISTICO)
        self.assertIn("1.500,00", tokens)
        self.assertIn("Sr.", tokens)

    def test_regex_fragmenta_o_que_o_linguistico_mantem(self):
        regex = tokenizar(self.FRASE, Tokenizacao.REGEX)
        linguistico = tokenizar(self.FRASE, Tokenizacao.LINGUISTICO)
        self.assertGreater(len(regex), len(linguistico))

    def test_as_tres_estrategias_diferem(self):
        contagens = {len(tokenizar(self.FRASE, modo)) for modo in Tokenizacao}
        self.assertEqual(len(contagens), 3, f"tokenizadores colidiram: {contagens}")

    def test_tokenizacao_altera_o_resultado_do_preprocessamento(self):
        saidas = {
            preprocessar(self.FRASE, ConfigPreprocessamento(tokenizacao=modo))
            for modo in Tokenizacao
        }
        self.assertGreater(len(saidas), 1)


class TesteModosDeStopwords(unittest.TestCase):
    # A lista do NLTK inclui as negações. Removê-las faz "não atualizou o status"
    # e "atualizou o status" virarem a mesma frase.

    FRASE = "o projeto não tem documento e o prazo está vencido"

    def test_manter_nao_remove_nada(self):
        config = ConfigPreprocessamento(stopwords=ModoStopwords.MANTER)
        self.assertEqual(preprocessar(self.FRASE, config), self.FRASE)

    def test_remover_tudo_apaga_a_negacao(self):
        config = ConfigPreprocessamento(stopwords=ModoStopwords.REMOVER_TUDO)
        self.assertNotIn("não", preprocessar(self.FRASE, config).split())

    def test_preservar_negacoes_mantem_a_negacao(self):
        config = ConfigPreprocessamento(stopwords=ModoStopwords.PRESERVAR_NEGACOES)
        self.assertIn("não", preprocessar(self.FRASE, config).split())

    def test_os_tres_modos_produzem_saidas_distintas(self):
        saidas = {
            preprocessar(self.FRASE, ConfigPreprocessamento(stopwords=modo)) for modo in ModoStopwords
        }
        self.assertEqual(len(saidas), 3, f"modos colidiram: {saidas}")

    def test_preservar_negacoes_cobre_as_principais(self):
        config = ConfigPreprocessamento(stopwords=ModoStopwords.PRESERVAR_NEGACOES)
        for palavra in ("não", "nem", "sem", "nunca"):
            with self.subTest(palavra=palavra):
                self.assertIn(palavra, preprocessar(f"o projeto {palavra} tem prazo", config).split())

    def test_negacao_sobrevive_tambem_sem_acento(self):
        # Com remover_acentos antes, "não" vira "nao": sem normalizar a lista
        # junto, a proteção da negação deixa de valer.
        config = ConfigPreprocessamento(
            remover_acentos=True, stopwords=ModoStopwords.PRESERVAR_NEGACOES
        )
        self.assertIn("nao", preprocessar("o projeto não tem prazo", config).split())

    def test_todas_as_negacoes_declaradas_sao_preservadas(self):
        config = ConfigPreprocessamento(stopwords=ModoStopwords.PRESERVAR_NEGACOES)
        for palavra in NEGACOES:
            with self.subTest(palavra=palavra):
                self.assertIn(palavra, preprocessar(f"o {palavra} projeto", config).split())


class TesteOrdem(unittest.TestCase):

    def test_ordem_padrao_e_a_declarada_em_etapas(self):
        self.assertEqual(ConfigPreprocessamento().ordem, ETAPAS)

    def test_etapas_ativas_respeitam_a_ordem_configurada(self):
        config = ConfigPreprocessamento(minusculas=True, morfologia=ModoMorfologia.STEMMING)
        self.assertEqual(config.etapas_ativas_na_ordem(), ("minusculas", "morfologia"))

        invertida = config.copiar_com_outra_ordem(
            ("morfologia", "minusculas")
            + tuple(e for e in ETAPAS if e not in ("morfologia", "minusculas"))
        )
        self.assertEqual(invertida.etapas_ativas_na_ordem(), ("morfologia", "minusculas"))

    def test_ordem_altera_o_resultado(self):
        # A lista de stopwords não contém "o,", então a etapa só filtra o que a
        # remoção de pontuação já separou.
        etapas = ("remover_pontuacao", "stopwords")
        resto = tuple(e for e in ETAPAS if e not in etapas)
        base = ConfigPreprocessamento(
            remover_pontuacao=True, stopwords=ModoStopwords.REMOVER_TUDO
        )
        frase = "o, projeto e, o prazo"

        limpa_antes = preprocessar(frase, base.copiar_com_outra_ordem(etapas + resto))
        filtra_antes = preprocessar(frase, base.copiar_com_outra_ordem(etapas[::-1] + resto))

        self.assertNotEqual(limpa_antes, filtra_antes)
        self.assertNotIn("o", limpa_antes.split())
        self.assertIn("o", filtra_antes.split())

    def test_ordem_invalida_e_rejeitada(self):
        with self.assertRaises(ValueError):
            ConfigPreprocessamento(ordem=("minusculas", "morfologia"))
        with self.assertRaises(ValueError):
            ConfigPreprocessamento(ordem=ETAPAS + ("inexistente",))


class TesteInvariantes(unittest.TestCase):
    def test_sem_espaco_duplicado_com_tudo_ligado(self):
        config = ConfigPreprocessamento(
            minusculas=True, remover_acentos=True, remover_pontuacao=True,
            remover_numeros=True, stopwords=ModoStopwords.PRESERVAR_NEGACOES,
            morfologia=ModoMorfologia.LEMATIZACAO,
        )
        resultado = preprocessar("Não recebi os documentos do RF01, e os prazos estão vencendo!", config)
        self.assertNotIn("  ", resultado)
        self.assertEqual(resultado, resultado.strip())

    def test_funcao_e_deterministica(self):
        config = ConfigPreprocessamento(
            minusculas=True, stopwords=ModoStopwords.REMOVER_TUDO, morfologia=ModoMorfologia.STEMMING
        )
        texto = "Quais prazos vencem nesta semana?"
        self.assertEqual(preprocessar(texto, config), preprocessar(texto, config))

    def test_config_e_hasheavel(self):
        # O experimento usa a config como chave de dicionário.
        self.assertIsInstance(hash(ConfigPreprocessamento(minusculas=True)), int)

    def test_descricao_mostra_ordem_e_modo(self):
        config = ConfigPreprocessamento(
            minusculas=True, stopwords=ModoStopwords.PRESERVAR_NEGACOES
        )
        self.assertEqual(config.descrever(), "[tok:split] minusculas > sw:preservar_negacoes")
        self.assertEqual(ConfigPreprocessamento().descrever(), "[tok:split] (texto cru)")


if __name__ == "__main__":
    unittest.main(verbosity=2)
