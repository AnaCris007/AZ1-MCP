# Testes da partição entre desenvolvimento e teste retido.
#
# A propriedade que importa aqui não é "o código roda", é "a afirmação é
# verdadeira". O relatório vai dizer que o teste retido nunca participou do
# treino, da escolha do pré-processamento, do ajuste ou da calibração. Se a
# partição tiver uma fresta, essa frase vira uma mentira publicada.
#
# Duas frestas são plausíveis e nenhuma delas dá erro:
#
#   1. O MESMO TEXTO nos dois arquivos, escrito com acento diferente ou espaço
#      a mais. Comparação literal não pega.
#   2. Exemplos MIGRANDO de partição quando o pool cresce. É o que aconteceria
#      com `shuffle` semeado, e é invisível: cada execução isolada parece
#      correta.

from __future__ import annotations

import unittest

from pln.particao import (
    FRACAO_TESTE_PADRAO,
    duplicatas,
    e_do_teste,
    normalizar,
    separar,
)


def _pool(quantos: int, intencao: str = "orientar_tap") -> list[tuple[str, str]]:
    return [(f"pergunta número {i} sobre o projeto", intencao) for i in range(quantos)]


class TesteNormalizar(unittest.TestCase):
    def test_acento_maiuscula_e_pontuacao_nao_distinguem_dois_textos(self) -> None:
        self.assertEqual(
            normalizar("Qual é a SITUAÇÃO do projeto?"),
            normalizar("qual e a situacao do projeto"),
        )

    def test_espaco_repetido_nao_distingue(self) -> None:
        self.assertEqual(normalizar("o  que   está pendente"), normalizar("o que está pendente"))


class TesteSeparar(unittest.TestCase):
    def test_nenhum_exemplo_aparece_nas_duas_particoes(self) -> None:
        desenvolvimento, teste = separar(_pool(500))

        chaves_dev = {normalizar(texto) for texto, _ in desenvolvimento}
        chaves_teste = {normalizar(texto) for texto, _ in teste}

        self.assertEqual(chaves_dev & chaves_teste, set())

    def test_nada_se_perde(self) -> None:
        linhas = _pool(500)
        desenvolvimento, teste = separar(linhas)

        self.assertEqual(len(desenvolvimento) + len(teste), len(linhas))

    def test_proporcao_fica_proxima_da_pedida(self) -> None:
        # Aproximada, e não exata: a atribuição é por hash do texto, então a
        # contagem tem ruído binomial. A tolerância é larga de propósito —
        # apertá-la faria o teste falhar por sorteio, e não por defeito.
        _, teste = separar(_pool(2000), fracao_teste=0.20)

        self.assertAlmostEqual(len(teste) / 2000, 0.20, delta=0.03)

    def test_e_deterministico(self) -> None:
        self.assertEqual(separar(_pool(200)), separar(_pool(200)))

    def test_semente_diferente_produz_particao_diferente(self) -> None:
        _, com_42 = separar(_pool(200), semente=42)
        _, com_7 = separar(_pool(200), semente=7)

        self.assertNotEqual(
            {texto for texto, _ in com_42}, {texto for texto, _ in com_7}
        )

    def test_crescer_o_pool_nao_move_quem_ja_estava(self) -> None:
        """A propriedade que justifica hash em vez de embaralhamento.

        Com `shuffle` semeado, acrescentar exemplos recalcula o sorteio inteiro
        e frases migram de partição. O modelo da rodada anterior foi ajustado
        sobre elas: o conjunto retido vaza sem ninguém ter feito nada errado, e
        nenhuma execução isolada parece incorreta.
        """
        antes_dev, antes_teste = separar(_pool(200))

        ampliado = _pool(200) + [(f"frase nova {i}", "orientar_tap") for i in range(300)]
        depois_dev, depois_teste = separar(ampliado)

        self.assertTrue(set(antes_dev).issubset(set(depois_dev)))
        self.assertTrue(set(antes_teste).issubset(set(depois_teste)))

    def test_fracao_invalida_e_recusada(self) -> None:
        for fracao in (0.0, 1.0, -0.1, 1.5):
            with self.subTest(fracao=fracao), self.assertRaises(ValueError):
                separar(_pool(10), fracao_teste=fracao)


class TesteDuplicatas(unittest.TestCase):
    def test_encontra_repeticao_que_so_difere_em_acento(self) -> None:
        linhas = [
            ("Qual é a situação?", "consultar_projeto_sintetico"),
            ("qual e a situacao", "consultar_projeto_sintetico"),
        ]

        self.assertEqual(len(duplicatas(linhas)), 1)

    def test_pool_sem_repeticao_nao_acusa(self) -> None:
        self.assertEqual(duplicatas(_pool(50)), [])


class TesteArquivosGerados(unittest.TestCase):
    """O contrato entre os arquivos, verificado sobre os que estão no disco."""

    def test_desenvolvimento_e_teste_nao_se_sobrepoem(self) -> None:
        from pln.caminhos import DATASET_PADRAO, DATASET_TESTE
        from pln.particao import carregar

        if not DATASET_TESTE.exists():
            self.skipTest("teste retido ainda não gerado (rode `python -m pln.particao`)")

        dev = {normalizar(t) for t, _ in carregar(DATASET_PADRAO)}
        retido = {normalizar(t) for t, _ in carregar(DATASET_TESTE)}

        self.assertEqual(
            dev & retido, set(),
            "há exemplos nos dois arquivos. Qualquer métrica publicada sobre o "
            "teste retido passa a ser medida sobre dados de treino.",
        )

    def test_todo_exemplo_do_teste_seria_sorteado_para_o_teste(self) -> None:
        """Os arquivos correspondem à regra que diz tê-los produzido.

        Pega o caso em que alguém edita um dos CSVs à mão em vez de reexecutar
        a partição — o arquivo fica plausível e deixa de ser reproduzível.
        """
        from pln.caminhos import DATASET_TESTE
        from pln.particao import carregar

        if not DATASET_TESTE.exists():
            self.skipTest("teste retido ainda não gerado")

        fora_do_lugar = [
            texto for texto, _ in carregar(DATASET_TESTE)
            if not e_do_teste(texto, FRACAO_TESTE_PADRAO)
        ]

        self.assertEqual(fora_do_lugar[:3], [])


if __name__ == "__main__":
    unittest.main()
