# Testes do classificador de intenções.
#
# A garantia central é a de `TesteConfiguracaoViajaComOModelo`: o modelo salvo
# carrega o próprio pré-processamento. Sem isso, treinar com uma configuração e
# prever com outra é possível, e não levanta exceção: o modelo só erra mais.

from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from sklearn.base import clone
from sklearn.naive_bayes import MultinomialNB

from pln.caminhos import DATASET_PADRAO
from pln.classificador import (
    CONFIG_PRE_PADRAO,
    CONFIG_VET_PADRAO,
    PreprocessadorDeTexto,
    avaliar_classificador,
    carregar_dataset,
    carregar_modelo,
    construir_classificador,
    listar_palavras_de_maior_peso_por_intencao,
    prever_intencao,
    salvar_modelo,
)
from pln.preprocessamento import ConfigPreprocessamento, ModoStopwords, Tokenizacao, preprocessar
from pln.vetorizacao import (
    ModoVetorizacao,
    construir_pipeline_de_medicao,
    todas_as_vetorizacoes,
)

RAIZ = Path(__file__).resolve().parent.parent

# SEIS por classe, e não três. O modelo do produto é `LinearSVC` embrulhado em
# `CalibratedClassifierCV(cv=3)`, que treina três modelos internos e por isso
# exige pelo menos três exemplos de cada classe DENTRO de cada dobra de treino.
# Com três por classe, uma validação cruzada de três dobras deixa dois no treino
# e o calibrador recusa — não é limitação do teste, é do modelo, e vale
# registrar: um dataset com classe rara demais não treina.
TEXTOS = [
    "Qual o status do projeto?", "Qual o avanço da obra?", "Quantos documentos existem?",
    "Qual o percentual concluído?", "Como está o cronograma?", "Qual a situação do lote?",
    "Registra o novo marco.", "Cria um projeto novo.", "Atualiza o percentual.",
    "Grava a data de entrega.", "Inclui o responsável.", "Lança o avanço do mês.",
    "Tem pendência vencida?", "Algum prazo vence hoje?", "Quais riscos estão sem mitigação?",
    "Há entrega atrasada?", "Algum marco furou o prazo?", "Quais problemas estão abertos?",
]
ROTULOS = ["consulta"] * 6 + ["transacao"] * 6 + ["alerta"] * 6


class TestePreprocessadorDeTexto(unittest.TestCase):
    def test_fit_devolve_self(self):
        # Contrato do scikit-learn — sem isso o Pipeline não encadeia.
        p = PreprocessadorDeTexto()
        self.assertIs(p.fit(TEXTOS), p)

    def test_transform_aplica_a_config(self):
        config = ConfigPreprocessamento(minusculas=True, stopwords=ModoStopwords.REMOVER_TUDO)
        p = PreprocessadorDeTexto(config)
        self.assertEqual(p.transform(["O Prazo do projeto"]), [preprocessar("O Prazo do projeto", config)])

    def test_sobrevive_ao_clone(self):
        # A validação cruzada clona o estimador a cada dobra. Se a config não
        # for guardada intacta em __init__, o clone perde a configuração e cada
        # dobra treinaria com um pré-processamento diferente.
        config = ConfigPreprocessamento(minusculas=True, remover_acentos=True)
        copia = clone(PreprocessadorDeTexto(config))
        self.assertEqual(copia.config, config)


class TesteConstrucao(unittest.TestCase):
    def test_pipeline_tem_as_tres_etapas_na_ordem(self):
        modelo = construir_classificador()
        self.assertEqual(list(modelo.named_steps), ["preprocessamento", "vetorizador", "classificador"])

    def test_treina_a_partir_de_texto_bruto(self):
        # O pipeline recebe frases, não vetores — é o que impede a divergência
        # entre o pré-processamento do treino e o da previsão.
        modelo = construir_classificador().fit(TEXTOS, ROTULOS)
        self.assertEqual(len(modelo.predict(["Qual o status?"])), 1)

    def test_padroes_do_modelo_vieram_do_ajuste_fino(self):
        # Trava contra alguém trocar os hiperparâmetros sem passar por
        # `ajuste_fino.py`. Os valores abaixo são a recomendação de
        # resultados/ajuste_fino.md. Se este teste falhar, aquele relatório e
        # docs/PipelinePLN.md precisam ser atualizados junto.
        #
        # O que este teste NÃO garante: que sejam os melhores possíveis. Eles
        # venceram um empate de 2010 configurações em 3000 — ver a ressalva de
        # saturação no cabeçalho deste módulo.
        from pln.classificador import ALPHA_PADRAO, FIT_PRIOR_PADRAO

        self.assertEqual(ALPHA_PADRAO, 1.0)
        self.assertIs(FIT_PRIOR_PADRAO, True)

    def test_regularizacao_e_convergencia_configuradas(self):
        # Este teste já foi de `max_iter`, virou `alpha` quando o produto passou
        # a Naive Bayes, e volta a ser dos dois com a regressão logística. O que
        # ele guarda não muda: os parâmetros que impedem o modelo de falhar em
        # silêncio.
        #
        # `C` finito mantém a regularização ligada; sem ela, 5.096 colunas sobre
        # 881 exemplos decoram o corpus. `max_iter` alto evita o aviso de não
        # convergência do `lbfgs`, que sobre contagem bruta é lento — e um
        # modelo que não convergiu treina, prevê e erra sem levantar exceção.
        final = construir_classificador().named_steps["classificador"]

        # O `C` mora no `LinearSVC` que o calibrador embrulha, e não no
        # calibrador. Ler `final.C` devolveria AttributeError — é o custo de
        # explicabilidade e de introspecção que a calibração cobra.
        self.assertGreater(final.estimator.C, 0)
        self.assertEqual(final.method, "sigmoid")
        self.assertGreaterEqual(final.cv, 2)


class TestePrevisao(unittest.TestCase):
    def setUp(self):
        self.modelo = construir_classificador().fit(TEXTOS, ROTULOS)

    def test_prever_devolve_rotulo_e_confianca(self):
        intencao, confianca = prever_intencao(self.modelo, "Registra o marco novo.")
        self.assertIn(intencao, set(ROTULOS))
        self.assertGreaterEqual(confianca, 0.0)
        self.assertLessEqual(confianca, 1.0)

    def test_confianca_e_a_maior_probabilidade(self):
        _, confianca = prever_intencao(self.modelo, "Qual o status?")
        self.assertAlmostEqual(confianca, max(self.modelo.predict_proba(["Qual o status?"])[0]))

    def test_probabilidades_somam_um(self):
        # É o que torna a confiança comparável entre classes — e, portanto,
        # utilizável como limiar para o agente dizer que não entendeu.
        self.assertAlmostEqual(sum(self.modelo.predict_proba(["Qual o status?"])[0]), 1.0, places=6)


class TesteExplicacao(unittest.TestCase):
    def test_devolve_termos_para_cada_classe(self):
        modelo = construir_classificador().fit(TEXTOS, ROTULOS)
        explicacao = listar_palavras_de_maior_peso_por_intencao(modelo, quantas=3)
        self.assertEqual(set(explicacao), set(ROTULOS))
        for classe, termos in explicacao.items():
            with self.subTest(classe=classe):
                self.assertEqual(len(termos), 3)
                self.assertTrue(all(isinstance(t, str) for t, _ in termos))

    def test_termos_vem_ordenados_por_peso(self):
        modelo = construir_classificador().fit(TEXTOS, ROTULOS)
        for termos in listar_palavras_de_maior_peso_por_intencao(modelo).values():
            pesos = [peso for _, peso in termos]
            self.assertEqual(pesos, sorted(pesos, reverse=True))


class TesteConfiguracaoViajaComOModelo(unittest.TestCase):
    # A garantia central: o modelo salvo carrega o próprio pré-processamento.

    def test_ida_e_volta_pelo_disco_preserva_as_previsoes(self):
        modelo = construir_classificador().fit(TEXTOS, ROTULOS)
        with tempfile.TemporaryDirectory() as tmp:
            caminho = Path(tmp) / "modelo.joblib"
            salvar_modelo(modelo, caminho)
            recarregado = carregar_modelo(caminho)
        self.assertListEqual(list(recarregado.predict(TEXTOS)), list(modelo.predict(TEXTOS)))

    def test_modelo_salvo_carrega_a_config_de_preprocessamento(self):
        config = ConfigPreprocessamento(minusculas=True, remover_acentos=True)
        modelo = construir_classificador(config_pre=config).fit(TEXTOS, ROTULOS)
        with tempfile.TemporaryDirectory() as tmp:
            caminho = Path(tmp) / "modelo.joblib"
            salvar_modelo(modelo, caminho)
            recarregado = carregar_modelo(caminho)
        self.assertEqual(recarregado.named_steps["preprocessamento"].config, config)


class TesteAvaliacao(unittest.TestCase):
    def test_avaliar_devolve_f1_relatorio_matriz_e_classes(self):
        f1, relatorio, matriz, classes = avaliar_classificador(TEXTOS, ROTULOS, construir_classificador(), k=3)
        self.assertGreaterEqual(f1, 0.0)
        self.assertLessEqual(f1, 1.0)
        self.assertIn("precision", relatorio)
        self.assertEqual(classes, sorted(set(ROTULOS)))
        self.assertEqual(len(matriz), len(classes))

    def test_matriz_de_confusao_soma_o_total_de_exemplos(self):
        _, _, matriz, _ = avaliar_classificador(TEXTOS, ROTULOS, construir_classificador(), k=3)
        self.assertEqual(sum(sum(linha) for linha in matriz), len(TEXTOS))


class TesteDatasetPadrao(unittest.TestCase):
    def test_config_padrao_e_a_vencedora_da_busca_de_tres_estagios(self):
        # Trava contra alguém trocar o padrão sem passar pela busca. Os valores
        # abaixo saíram de `resultados/comparativo_modelos.md`, da linha da
        # regressão logística: `bow n=1-2` com `[tok:regex] remover_numeros >
        # stemming`. Se este teste falhar, o comparativo e a Seção 3.3 do
        # Projeto.md precisam ser atualizados junto.
        #
        # Repare que este NÃO é o rank #1 do experimento: aquele ranking é
        # produzido sob `MultinomialNB`, e cada família tem o seu melhor texto.
        # É justamente o que a busca conjunta existe para mostrar.
        self.assertEqual(
            CONFIG_PRE_PADRAO.etapas_ativas_na_ordem(),
            ("minusculas", "remover_acentos", "remover_numeros"),
        )
        self.assertIs(CONFIG_PRE_PADRAO.tokenizacao, Tokenizacao.REGEX)
        self.assertIs(CONFIG_VET_PADRAO.modo, ModoVetorizacao.BOW)
        self.assertEqual(CONFIG_VET_PADRAO.n_max, 2)

    def test_dataset_de_exemplo_carrega(self):
        textos, rotulos = carregar_dataset(DATASET_PADRAO)
        self.assertEqual(len(textos), len(rotulos))
        self.assertGreater(len(textos), 0)


class TesteClassificadorDoProdutoEAReguaDoExperimento(unittest.TestCase):
    """Produto e régua DEIXARAM de ser o mesmo modelo, e isso é decisão.

    Até a Sprint 3 havia aqui um teste afirmando o contrário: produto e régua
    tinham de ser da mesma classe, porque o pré-processamento é escolhido
    medindo com a régua. O argumento era válido enquanto ninguém tinha medido
    outras famílias sobre o texto delas próprias.

    Medido, o `MultinomialNB` ficou em sexto de sete e falhava nos três limites
    do RNF03 no conjunto retido. Manter a invariante custaria o requisito.

    Estes testes travam o que sobrou: a divergência é INTENCIONAL e a régua
    continua sendo o Naive Bayes, cuja velocidade é o que torna a varredura de
    milhares de execuções praticável.
    """

    def test_produto_e_regua_sao_familias_diferentes(self):
        do_produto = construir_classificador().named_steps["classificador"]
        da_regua = construir_pipeline_de_medicao(CONFIG_VET_PADRAO).named_steps["classificador"]

        self.assertIsNot(
            type(do_produto), type(da_regua),
            "produto e régua voltaram a ser a mesma família. Se a volta é "
            "deliberada, o cabeçalho de classificador.py e a Seção 3.3.7 "
            "precisam voltar junto.",
        )

    def test_a_regua_continua_sendo_naive_bayes(self):
        # A varredura de `experimento.py` são milhares de execuções, e é a
        # velocidade do Naive Bayes que as torna praticáveis. Trocar a régua por
        # uma família com otimização iterativa mediria o mesmo espaço em horas.
        da_regua = construir_pipeline_de_medicao(CONFIG_VET_PADRAO).named_steps["classificador"]

        self.assertIsInstance(da_regua, MultinomialNB)

    def test_o_produto_produz_probabilidade(self):
        # A regra de rejeição de `pln.intencao` é um limiar sobre confiança.
        # Uma família sem `predict_proba` quebraria cobertura e aceitação
        # indevida — as duas métricas do RNF03 definidas sobre a rejeição.
        self.assertTrue(
            hasattr(construir_classificador().named_steps["classificador"], "predict_proba")
        )

    def test_treina_com_toda_vetorizacao_do_espaco(self):
        for config_vet in todas_as_vetorizacoes():
            with self.subTest(vetorizacao=config_vet.descrever()):
                modelo = construir_classificador(config_vet=config_vet)
                modelo.fit(TEXTOS, ROTULOS)
                self.assertEqual(len(modelo.predict(["Qual o status?"])), 1)


class TesteModeloSalvoCarregaDeFora(unittest.TestCase):
    # `python -m pln.classificador` carrega o módulo como `__main__`. Chamando
    # `main()` desse contexto, o pickle grava `PreprocessadorDeTexto` com o
    # caminho `__main__` e o modelo só carrega de dentro do próprio CLI.

    def test_treina_pelo_cli_e_carrega_por_import(self):
        with tempfile.TemporaryDirectory() as pasta:
            destino = Path(pasta) / "modelo.joblib"
            treino = subprocess.run(
                [sys.executable, "-m", "pln.classificador", "--k", "2", "--salvar", str(destino)],
                capture_output=True, text=True, cwd=RAIZ,
            )
            self.assertEqual(treino.returncode, 0, treino.stderr)

            leitura = subprocess.run(
                [sys.executable, "-c",
                 "from pln.classificador import carregar_modelo, prever_intencao;"
                 f"m = carregar_modelo(__import__('pathlib').Path({str(destino)!r}));"
                 "print(prever_intencao(m, 'Tem algum prazo vencido?')[0])"],
                capture_output=True, text=True, cwd=RAIZ,
            )
            self.assertEqual(
                leitura.returncode, 0,
                "o modelo salvo pelo CLI não carrega de um processo que o importa:\n"
                + leitura.stderr,
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
