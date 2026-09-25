# Testes do comparativo de famílias de classificador.
#
# Não se testa aqui QUAL modelo vence — isso muda com o dataset e é exatamente
# o que o relatório existe para descobrir. Testa-se o que precisa ser verdade
# para que a comparação signifique alguma coisa:
#
#   1. Todo candidato precisa de `predict_proba`. A regra de rejeição compara
#      confiança contra limiar, e cobertura e aceitação indevida são definidas
#      sobre ela. Um candidato sem probabilidade não estoura — ele some das
#      duas métricas, e o relatório sai plausível e errado.
#   2. Trocar o estimador não pode trocar o texto. Se o pré-processamento
#      mudasse junto, a tabela mediria duas coisas somadas.
#   3. O veredito precisa ranquear pelo PONTO DE OPERAÇÃO, e não pelo F1 bruto.

from __future__ import annotations

import dataclasses
import unittest
from unittest import mock

from sklearn.linear_model import LogisticRegression
from sklearn.naive_bayes import MultinomialNB

import pln.comparativo_modelos as comparativo
from pln.classificador import CONFIG_PRE_PADRAO, construir_classificador
from pln.comparativo_modelos import (
    Candidato,
    Combinacao,
    Medicao,
    Pareado,
    _leitura,
    _tabela_de_hiperparametros,
    _tabela_de_textos,
    _tabela_por_intencao,
    candidatos,
    comparar_notas,
    confirmar_no_retido,
    espaco_de_busca,
    melhor_por_familia,
    todos_os_pares,
    variantes_de_hiperparametro,
)
from pln.metricas import ResultadoRNF03, distancia_do_requisito
from pln.preprocessamento import ETAPAS, ConfigPreprocessamento, Tokenizacao
from pln.vetorizacao import ConfigVetorizacao, ModoVetorizacao


def _resultado(f1: float, cobertura: float, aceitacao: float, limiar: float = 0.5) -> ResultadoRNF03:
    return ResultadoRNF03(
        limiar=limiar,
        f1_macro=f1,
        cobertura=cobertura,
        aceitacao_indevida=aceitacao,
        conhecidos=180,
        fora_do_catalogo=20,
    )


def _medicao(
    nome: str,
    f1_bruto: float,
    ponto: ResultadoRNF03,
    aprovado: bool = False,
    por_intencao: dict[str, float] | None = None,
) -> Medicao:
    return Medicao(
        candidato=Candidato(nome, MultinomialNB(), "porque sim"),
        combinacao=None,
        sem_rejeicao=_resultado(f1_bruto, 1.0, 1.0, limiar=0.0),
        melhor_ponto=ponto,
        tem_ponto_aprovado=aprovado,
        segundos=0.1,
        f1_por_intencao=por_intencao or {"orientar_tap": f1_bruto, "fora_do_catalogo": f1_bruto},
    )


# Quatro permutações distintas das etapas: servem só para distinguir, no teste,
# qual texto cada família recebeu.
ORDENS = [
    tuple(ETAPAS[i:] + ETAPAS[:i]) for i in range(4)
]


class TesteCandidatos(unittest.TestCase):
    def test_todos_produzem_probabilidade(self) -> None:
        for candidato in candidatos():
            with self.subTest(candidato.nome):
                self.assertTrue(
                    hasattr(candidato.estimador, "predict_proba"),
                    f"{candidato.nome} não expõe predict_proba. Sem probabilidade não há "
                    f"limiar, e sem limiar cobertura e aceitação indevida não existem.",
                )

    def test_a_referencia_vem_primeiro(self) -> None:
        # A ordem é o que faz cada linha da tabela ser lida como diferença em
        # relação ao que está em produção — e o que está em produção mudou na
        # Sprint 3. Rotular o modelo antigo de "referência" faria o relatório
        # comparar contra algo que ninguém mais roda.
        # Compara a FAMÍLIA, e não o rótulo: "LinearSVC calibrado" é texto para
        # humano, `CalibratedClassifierCV` é o que o pipeline monta. A versão
        # anterior deste teste comparava os dois e só passava por coincidência,
        # enquanto o nome do candidato calhava de ser igual ao da classe.
        from pln.classificador import construir_classificador

        em_producao = type(construir_classificador().named_steps["classificador"])
        self.assertIsInstance(
            candidatos()[0].estimador, em_producao,
            f"o primeiro candidato é {type(candidatos()[0].estimador).__name__}, mas a "
            f"produção roda {em_producao.__name__}. A tabela leria cada linha como "
            f"diferença contra algo que ninguém executa.",
        )

    def test_nomes_nao_se_repetem(self) -> None:
        nomes = [c.nome for c in candidatos()]
        self.assertEqual(len(nomes), len(set(nomes)))


class TesteTrocaSomenteOEstimador(unittest.TestCase):
    def test_preprocessamento_e_vetorizacao_nao_mudam(self) -> None:

        padrao = construir_classificador()
        alternativo = construir_classificador(estimador=LogisticRegression())

        self.assertEqual(
            padrao.named_steps["preprocessamento"].config,
            alternativo.named_steps["preprocessamento"].config,
        )
        self.assertEqual(padrao.named_steps["preprocessamento"].config, CONFIG_PRE_PADRAO)
        self.assertIsInstance(alternativo.named_steps["classificador"], LogisticRegression)

    def test_sem_estimador_vem_o_modelo_do_produto(self) -> None:
        """E o produto deixou de ser Naive Bayes.

        Este teste já afirmou `MultinomialNB`. A busca de três estágios mostrou
        que ele falhava nos três limites do RNF03 no conjunto retido, e a
        regressão logística os atende — a troca é o resultado dessa medição, e
        não preferência.
        """
        from sklearn.calibration import CalibratedClassifierCV

        self.assertIsInstance(
            construir_classificador().named_steps["classificador"], CalibratedClassifierCV
        )


class TesteDistanciaDoRequisito(unittest.TestCase):
    def test_resultado_aprovado_tem_distancia_zero(self) -> None:
        self.assertEqual(distancia_do_requisito(_resultado(0.90, 0.95, 0.10)), 0.0)

    def test_folga_alem_do_limite_nao_compensa_violacao_em_outra_metrica(self) -> None:
        """Os três limites são cumulativos: não existe crédito entre eles.

        Um F1 altíssimo não paga uma cobertura baixa — a Seção 6.3 exige os
        três simultaneamente.
        """
        so_cobertura_ruim = distancia_do_requisito(_resultado(1.00, 0.50, 0.00))

        self.assertGreater(so_cobertura_ruim, 0.0)


class TesteLeitura(unittest.TestCase):
    def test_ranqueia_pelo_ponto_de_operacao_e_nao_pelo_f1_bruto(self) -> None:
        """A distinção que o primeiro veredito deste módulo errava.

        `f1_bruto` ignora as duas métricas que o RNF03 exige junto. Um modelo
        pode ter F1 sem rejeição maior e, no ponto em que de fato operaria,
        servir menos gente e aceitar mais pedido fora do catálogo.
        """
        referencia = _medicao("MultinomialNB", 0.67, _resultado(0.57, 0.52, 0.15))
        f1_alto_ponto_ruim = _medicao("F1 alto", 0.80, _resultado(0.55, 0.40, 0.30))
        ponto_bom = _medicao("Ponto bom", 0.74, _resultado(0.71, 0.74, 0.10))

        texto = "\n".join(_leitura([referencia, f1_alto_ponto_ruim, ponto_bom]))

        self.assertIn("Ponto bom", texto)
        self.assertNotIn("**`F1 alto`", texto)

    def test_referencia_vencendo_nao_propoe_troca(self) -> None:
        referencia = _medicao("MultinomialNB", 0.67, _resultado(0.70, 0.85, 0.10))
        pior = _medicao("Outro", 0.80, _resultado(0.40, 0.30, 0.40))

        texto = "\n".join(_leitura([referencia, pior]))

        self.assertIn("A referência continua sendo a melhor", texto)

    def test_candidato_aprovado_e_anunciado_como_tal(self) -> None:
        referencia = _medicao("MultinomialNB", 0.67, _resultado(0.57, 0.52, 0.15))
        aprovado = _medicao("Aprovado", 0.90, _resultado(0.88, 0.93, 0.10), aprovado=True)

        texto = "\n".join(_leitura([referencia, aprovado]))

        self.assertIn("atende aos três limites do RNF03", texto)

    def test_o_custo_da_troca_aparece_sempre_que_ha_troca(self) -> None:
        """A ressalva da régua não pode sumir do relatório.

        Trocar o produto sem trocar a régua da varredura faz o
        pré-processamento ter sido escolhido sob um modelo que não roda mais.
        Quem lê só a tabela não tem como saber disso.
        """
        referencia = _medicao("MultinomialNB", 0.67, _resultado(0.57, 0.52, 0.15))
        melhor = _medicao("Melhor", 0.74, _resultado(0.71, 0.74, 0.10))

        texto = "\n".join(_leitura([referencia, melhor]))

        self.assertIn("Seção 3.3.2", texto)
        self.assertIn("experimento.py", texto)


class TesteTabelaPorIntencao(unittest.TestCase):
    """A abertura por classe, que é o que torna o veredito inspecionável.

    O agregado diz QUANTO uma família ganha. Só esta tabela diz ONDE — e a
    diferença decide, porque `fora_do_catalogo` sustenta sozinha a aceitação
    indevida do RNF03: ganhar na média perdendo nessa classe piora o requisito.
    """

    def _duas(self) -> list[Medicao]:
        referencia = _medicao(
            "MultinomialNB", 0.67, _resultado(0.57, 0.52, 0.15),
            por_intencao={"fora_do_catalogo": 0.663, "orientar_tap": 0.850},
        )
        desafiante = _medicao(
            "LinearSVC", 0.74, _resultado(0.71, 0.74, 0.10),
            por_intencao={"fora_do_catalogo": 0.813, "orientar_tap": 0.825},
        )
        return [referencia, desafiante]

    def test_marca_a_melhor_de_cada_linha(self) -> None:
        texto = "\n".join(_tabela_por_intencao(self._duas()))

        self.assertIn("**0.813**", texto)   # LinearSVC vence fora_do_catalogo
        self.assertIn("**0.850**", texto)   # MultinomialNB vence orientar_tap

    def test_nomeia_a_vencedora_por_intencao(self) -> None:
        linhas = _tabela_por_intencao(self._duas())

        fora = next(linha for linha in linhas if "`fora_do_catalogo`" in linha)
        tap = next(linha for linha in linhas if "`orientar_tap`" in linha)

        self.assertTrue(fora.rstrip().endswith("| LinearSVC |"))
        self.assertTrue(tap.rstrip().endswith("| MultinomialNB |"))

    def test_placar_conta_as_vitorias(self) -> None:
        texto = "\n".join(_tabela_por_intencao(self._duas()))

        self.assertIn("LinearSVC em 1", texto)
        self.assertIn("MultinomialNB em 1", texto)

    def test_uma_coluna_por_familia(self) -> None:
        cabecalho = _tabela_por_intencao(self._duas())[0]

        self.assertIn("| MultinomialNB |", cabecalho)
        self.assertIn("| LinearSVC |", cabecalho)


def _combinacao(nome: str, tokenizacao: Tokenizacao) -> Combinacao:
    return Combinacao(
        candidato=Candidato(nome, MultinomialNB(), "porque sim"),
        config_pre=ConfigPreprocessamento(tokenizacao=tokenizacao),
        config_vet=ConfigVetorizacao(ModoVetorizacao.BOW, n_max=1),
    )


class TesteBuscaConjunta(unittest.TestCase):
    """O classificador passou a ser EIXO de busca, e não constante.

    Medir todas as famílias sobre a configuração de texto que o
    `MultinomialNB` escolheu dá vantagem a ele: o pré-processamento não é
    neutro entre famílias. Estes testes travam o formato do espaço e a regra de
    escolha, não os valores — que mudam com o dataset.
    """

    @staticmethod
    def _mesmos_textos(configs: list[ConfigPreprocessamento]) -> dict:
        return {c.nome: configs for c in candidatos()}

    def test_espaco_e_o_produto_das_tres_dimensoes(self) -> None:
        configs = [ConfigPreprocessamento(), ConfigPreprocessamento(minusculas=True)]

        espaco = espaco_de_busca(self._mesmos_textos(configs))

        # famílias x textos x vetorizações
        self.assertEqual(len(espaco), len(candidatos()) * len(configs) * 4)

    def test_toda_familia_aparece_no_espaco(self) -> None:
        espaco = espaco_de_busca(self._mesmos_textos([ConfigPreprocessamento()]))

        nomes = {c.candidato.nome for c in espaco}

        self.assertEqual(nomes, {c.nome for c in candidatos()})

    def test_cada_familia_recebe_os_textos_dela(self) -> None:
        """A correção central desta rodada, e a regressão que a desfaria.

        Antes, todas as famílias liam o ranking do `MultinomialNB`. Uma família
        cujo texto ideal estivesse na posição 800 desse ranking nunca o veria —
        e a comparação favorecia quem produziu o ranking.
        """
        familias = [c.nome for c in candidatos()]
        proprio = {
            nome: [ConfigPreprocessamento(ordem=ORDENS[i])]
            for i, nome in enumerate(familias)
        }

        espaco = espaco_de_busca(proprio)

        for nome in familias:
            ordens = {c.config_pre.ordem for c in espaco if c.candidato.nome == nome}
            self.assertEqual(
                ordens, {proprio[nome][0].ordem},
                f"{nome} recebeu texto que não era o dela",
            )

    def test_familia_sem_ranking_proprio_falha_alto(self) -> None:
        """Herdar em silêncio é pior que quebrar: a assimetria voltaria invisível."""
        parcial = {candidatos()[0].nome: [ConfigPreprocessamento()]}

        with self.assertRaises(KeyError):
            espaco_de_busca(parcial)

    def test_toda_familia_declara_regua_propria(self) -> None:
        reguas = [c.regua for c in candidatos()]

        self.assertEqual(
            len(set(reguas)), len(reguas),
            "duas famílias compartilhando régua leriam o mesmo ranking",
        )

    def test_as_quatro_familias_do_parecer(self) -> None:
        nomes = {c.nome for c in candidatos()}

        self.assertEqual(len(nomes), 4)
        for esperada in ("LogisticRegression", "MultinomialNB"):
            self.assertIn(esperada, nomes)
        self.assertTrue(any("LinearSVC" in n for n in nomes))
        self.assertTrue(any("SGD" in n for n in nomes))

    def test_melhor_por_familia_escolhe_pela_distancia_ao_requisito(self) -> None:
        """E não pelo F1 bruto — a mesma régua que ordena a tabela agregada."""
        ruim = _medicao("MultinomialNB", 0.90, _resultado(0.88, 0.40, 0.30))
        bom = _medicao("MultinomialNB", 0.70, _resultado(0.70, 0.92, 0.10))

        escolhida = melhor_por_familia([ruim, bom])

        self.assertEqual(len(escolhida), 1)
        self.assertAlmostEqual(escolhida[0].melhor_ponto.cobertura, 0.92)

    def test_devolve_uma_medicao_por_familia_na_ordem_dos_candidatos(self) -> None:
        medicoes = [
            _medicao("LinearSVC calibrado", 0.80, _resultado(0.80, 0.90, 0.10)),
            _medicao("MultinomialNB", 0.70, _resultado(0.70, 0.80, 0.12)),
        ]

        escolhidas = melhor_por_familia(medicoes)

        # A ordem de `candidatos()` manda, e a referência (o modelo em
        # produção) vem primeiro nela.
        esperada = [c.nome for c in candidatos()
                    if c.nome in {"LinearSVC calibrado", "MultinomialNB"}]
        self.assertEqual([m.candidato.nome for m in escolhidas], esperada)


class TesteTabelaDeTextos(unittest.TestCase):
    def test_escapa_o_pipe_da_descricao(self) -> None:
        """`bow n=1 | [tok:regex] ...` tem `|`, que separa célula em markdown.

        Sem escapar, a linha inteira se parte em colunas fantasmas e a tabela
        renderiza errada — falha silenciosa que só aparece ao ler o relatório.
        """
        medicao = _medicao("MultinomialNB", 0.70, _resultado(0.70, 0.80, 0.12))
        com_texto = dataclasses.replace(
            medicao, combinacao=_combinacao("MultinomialNB", Tokenizacao.REGEX)
        )

        linha = next(
            linha for linha in _tabela_de_textos([com_texto]) if "MultinomialNB" in linha
        )

        self.assertNotIn(" | [tok:", linha)
        self.assertIn("\\| [tok:", linha)

    def test_diz_quando_as_familias_preferem_textos_diferentes(self) -> None:
        a = dataclasses.replace(
            _medicao("MultinomialNB", 0.70, _resultado(0.70, 0.80, 0.12)),
            combinacao=_combinacao("MultinomialNB", Tokenizacao.REGEX),
        )
        b = dataclasses.replace(
            _medicao("LinearSVC", 0.80, _resultado(0.80, 0.90, 0.10)),
            combinacao=_combinacao("LinearSVC", Tokenizacao.LINGUISTICO),
        )

        texto = "\n".join(_tabela_de_textos([a, b]))

        self.assertIn("2 textos diferentes", texto)

    def test_diz_quando_todas_preferem_o_mesmo(self) -> None:
        a = dataclasses.replace(
            _medicao("MultinomialNB", 0.70, _resultado(0.70, 0.80, 0.12)),
            combinacao=_combinacao("MultinomialNB", Tokenizacao.REGEX),
        )
        b = dataclasses.replace(
            _medicao("LinearSVC", 0.80, _resultado(0.80, 0.90, 0.10)),
            combinacao=_combinacao("LinearSVC", Tokenizacao.REGEX),
        )

        texto = "\n".join(_tabela_de_textos([a, b]))

        self.assertIn("MESMO texto", texto)


class TesteVariantesDeHiperparametro(unittest.TestCase):
    """O terceiro estágio, que faltava.

    Até ele existir, a comparação media todas as famílias em configuração
    PADRÃO — e `ajuste_fino.py` só sabe buscar `alpha` e `fit_prior`, que são
    do Naive Bayes. O pipeline estava completo para ele e incompleto para os
    demais, o que é a mesma classe de viés que a busca conjunta corrigiu no
    eixo do texto.
    """

    def _com_grade(self, grade) -> Medicao:
        candidato = Candidato("X", MultinomialNB(), "porque", grade=grade)
        combinacao = Combinacao(
            candidato=candidato,
            config_pre=ConfigPreprocessamento(),
            config_vet=ConfigVetorizacao(ModoVetorizacao.BOW, n_max=1),
        )
        base = _medicao("X", 0.70, _resultado(0.70, 0.80, 0.12))
        return dataclasses.replace(base, combinacao=combinacao)

    def test_produto_cartesiano_da_grade(self) -> None:
        medicao = self._com_grade((("alpha", (0.1, 1.0)), ("fit_prior", (True, False))))

        variantes = variantes_de_hiperparametro(medicao)

        self.assertEqual(len(variantes), 4)
        self.assertEqual(
            {v.descrever_parametros() for v in variantes},
            {"alpha=0.1, fit_prior=True", "alpha=0.1, fit_prior=False",
             "alpha=1.0, fit_prior=True", "alpha=1.0, fit_prior=False"},
        )

    def test_familia_sem_grade_nao_gera_variante(self) -> None:
        self.assertEqual(variantes_de_hiperparametro(self._com_grade(())), [])

    def test_variante_preserva_o_texto_da_familia(self) -> None:
        """A grade roda sobre o MELHOR texto, não sobre um texto qualquer."""
        medicao = self._com_grade((("alpha", (0.1,)),))

        variante = variantes_de_hiperparametro(medicao)[0]

        self.assertEqual(variante.config_pre, medicao.combinacao.config_pre)
        self.assertEqual(variante.config_vet, medicao.combinacao.config_vet)

    def test_todo_candidato_real_declara_grade(self) -> None:
        for c in candidatos():
            with self.subTest(c.nome):
                self.assertTrue(
                    c.grade,
                    f"{c.nome} entrou sem grade de hiperparâmetro e seria comparado "
                    f"em configuração padrão contra famílias ajustadas.",
                )


class TesteTabelaDeHiperparametros(unittest.TestCase):
    def test_mostra_as_duas_linhas_quando_a_grade_venceu(self) -> None:
        """Sem as duas linhas o relatório pareceria contraditório.

        A escolha é pela menor distância até o RNF03, não pelo maior F1, então
        uma família ajustada pode exibir F1 MENOR. Mostrar padrão e ajustado
        lado a lado é o que torna isso verificável em vez de misterioso.
        """
        combinacao = Combinacao(
            candidato=Candidato("X", MultinomialNB(), "porque"),
            config_pre=ConfigPreprocessamento(),
            config_vet=ConfigVetorizacao(ModoVetorizacao.BOW, n_max=1),
            parametros=(("alpha", 2.0),),
        )
        padrao = _medicao("X", 0.70, _resultado(0.7794, 0.872, 0.129))
        ajustada = dataclasses.replace(
            _medicao("X", 0.70, _resultado(0.7680, 0.894, 0.148)), combinacao=combinacao
        )

        texto = "\n".join(_tabela_de_hiperparametros([padrao], [ajustada]))

        self.assertIn("0.7794", texto)   # a linha do padrão não some
        self.assertIn("0.7680", texto)   # nem a da ajustada
        self.assertIn("alpha=2.0", texto)
        self.assertIn("1 de 1", texto)

    def test_diz_quando_o_padrao_ja_era_o_melhor(self) -> None:
        padrao = _medicao("X", 0.70, _resultado(0.80, 0.92, 0.10))

        texto = "\n".join(_tabela_de_hiperparametros([padrao], [padrao]))

        self.assertIn("a grade não superou", texto)
        self.assertIn("0 de 1", texto)


class TestePareado(unittest.TestCase):
    """O teste que este módulo JÁ ERROU, e que por isso precisa de trava.

    Com 10 dobras, a comparação entre os dois primeiros devolveu t = 1,502 e
    foi lida como empate; com 10 dobras x 5 repetições, os mesmos dois modelos
    dão t = 3,527 e a diferença é real. A leitura errada autoriza trocar o
    modelo do produto pelo pior dos dois por critério de engenharia.
    """

    @staticmethod
    def _pareado(dif: list[float]) -> Pareado:
        base = [0.80] * len(dif)
        return Pareado("A", "B", base, [x + d for x, d in zip(base, dif, strict=True)])

    def test_diferenca_consistente_e_significativa(self) -> None:
        p = self._pareado([0.015 + (0.001 if i % 2 else -0.001) for i in range(50)])

        self.assertTrue(p.significativo)
        self.assertGreater(p.intervalo_95[0], 0)

    def test_diferenca_que_troca_de_sinal_nao_e_significativa(self) -> None:
        p = self._pareado([0.05 if i % 2 else -0.05 for i in range(50)])

        self.assertFalse(p.significativo)

    def test_intervalo_contem_a_media(self) -> None:
        p = self._pareado([0.01, 0.02, 0.03, 0.00, 0.02] * 10)
        baixo, alto = p.intervalo_95
        media = sum(p.diferencas) / len(p.diferencas)

        self.assertLess(baixo, media)
        self.assertGreater(alto, media)

    def test_a_mesma_diferenca_separa_com_50_e_nao_com_10(self) -> None:
        """Reproduz o erro que este módulo cometeu, com os números reais.

        `LinearSVC` contra `LogisticRegression` mediu diferença média +0,0154
        com desvio 0,0310 — dispersão DUAS VEZES maior que o efeito. Com 10
        medições isso dá t = 1,50 e parece empate; com 50, dá t = 3,53 e a
        diferença é real.

        A sequência abaixo alterna +0,046 e −0,016 justamente para reproduzir
        essa razão entre efeito e dispersão. Se alguém reduzir as repetições,
        este teste falha antes de o relatório voltar a declarar empate falso.
        """
        dif = [0.046 if i % 2 else -0.016 for i in range(50)]

        self.assertFalse(
            self._pareado(dif[:10]).significativo,
            "com 10 medições esta diferença não deveria ser detectável",
        )
        self.assertTrue(
            self._pareado(dif).significativo,
            "com 50 medições a mesma diferença precisa aparecer",
        )


class TesteExtracaoDoPareado(unittest.TestCase):
    """Medir uma vez por família e derivar os pares tem de dar o mesmo número.

    A refatoração existe por custo: com 4 famílias são 6 pares, e re-treinar
    por par custaria o triplo. Se a extração mudasse a conta, o ganho de tempo
    viria acompanhado de um resultado diferente — e ninguém perceberia, porque
    o número continuaria plausível.
    """

    def test_comparar_notas_reproduz_o_pareado_direto(self) -> None:
        a = [0.80 + 0.01 * (i % 3) for i in range(50)]
        b = [0.82 + 0.01 * (i % 4) for i in range(50)]

        derivado = comparar_notas("A", a, "B", b)
        direto = Pareado("A", "B", a, b)

        self.assertAlmostEqual(derivado.t, direto.t, places=10)
        self.assertEqual(derivado.intervalo_95, direto.intervalo_95)

    def test_todos_os_pares_cobre_a_combinacao_completa(self) -> None:
        notas = {nome: [0.8 + i * 0.01] * 50 for i, nome in enumerate("ABCD")}

        pares = todos_os_pares(notas)

        self.assertEqual(len(pares), 6)  # C(4,2)
        self.assertEqual(
            {(p.nome_a, p.nome_b) for p in pares},
            {("A", "B"), ("A", "C"), ("A", "D"), ("B", "C"), ("B", "D"), ("C", "D")},
        )

    def test_series_de_tamanhos_diferentes_nao_sao_pareaveis(self) -> None:
        """O teste pressupõe que a i-ésima nota das duas veio da MESMA partição."""
        with self.assertRaises(ValueError):
            comparar_notas("A", [0.8] * 10, "B", [0.8] * 20)


class TesteConfirmacaoNoRetido(unittest.TestCase):
    """O retido só vale enquanto não participar de escolha nenhuma.

    Basta chamar `curva_do_limiar` sobre ele para o número melhorar e deixar de
    significar generalização. É a falha mais fácil de cometer e a mais difícil
    de notar depois, porque o resultado fica melhor.
    """

    def setUp(self) -> None:
        self.dev_x = [f"pergunta de desenvolvimento {i}" for i in range(40)]
        self.dev_y = [f"intencao_{i % 4}" for i in range(40)]
        self.ret_x = [f"pergunta retida {i}" for i in range(20)]
        self.ret_y = [f"intencao_{i % 4}" for i in range(20)]

        combinacao = Combinacao(
            candidato=Candidato("X", MultinomialNB(), "porque"),
            config_pre=ConfigPreprocessamento(),
            config_vet=ConfigVetorizacao(ModoVetorizacao.BOW, n_max=1),
        )
        self.medicao = dataclasses.replace(
            _medicao("X", 0.70, _resultado(0.70, 0.80, 0.12)), combinacao=combinacao
        )

    def test_o_limiar_e_calibrado_so_no_desenvolvimento(self) -> None:
        vistos = []
        real = comparativo.curva_do_limiar

        def espiao(reais, previstos, confiancas, *args, **kwargs):
            vistos.append(list(reais))
            return real(reais, previstos, confiancas, *args, **kwargs)

        with mock.patch.object(comparativo, "curva_do_limiar", espiao):
            confirmar_no_retido(
                self.medicao, self.dev_x, self.dev_y, self.ret_x, self.ret_y, k=2
            )

        self.assertTrue(vistos, "a curva do limiar nem chegou a ser calculada")
        for rotulos in vistos:
            self.assertEqual(
                len(rotulos), len(self.dev_y),
                "curva_do_limiar recebeu um conjunto do tamanho do retido: "
                "calibrar nele queima o retido.",
            )

    def test_devolve_o_limiar_usado_junto_com_o_resultado(self) -> None:
        # Sem o limiar ao lado, o relatório não teria como mostrar que ele veio
        # congelado do desenvolvimento.
        resultado = confirmar_no_retido(
            self.medicao, self.dev_x, self.dev_y, self.ret_x, self.ret_y, k=2
        )

        self.assertIsNotNone(resultado)
        _, limiar = resultado
        self.assertGreaterEqual(limiar, 0.0)
        self.assertLessEqual(limiar, 1.0)

    def test_sem_combinacao_nao_ha_o_que_confirmar(self) -> None:
        sem = _medicao("X", 0.70, _resultado(0.70, 0.80, 0.12))

        self.assertIsNone(
            confirmar_no_retido(sem, self.dev_x, self.dev_y, self.ret_x, self.ret_y)
        )


if __name__ == "__main__":
    unittest.main()
