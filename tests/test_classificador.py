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

TEXTOS = [
    "Qual o status do projeto?", "Qual o avanço da obra?", "Quantos documentos existem?",
    "Registra o novo marco.", "Cria um projeto novo.", "Atualiza o percentual.",
    "Tem pendência vencida?", "Algum prazo vence hoje?", "Quais riscos estão sem mitigação?",
]
ROTULOS = ["consulta"] * 3 + ["transacao"] * 3 + ["alerta"] * 3


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

    def test_suavizacao_ligada(self):
        # Substituiu o antigo teste de `max_iter`, que era da regressão
        # logística e deixou de existir com a troca para Naive Bayes. O análogo
        # é o `alpha`: com 0 a suavização desliga e volta o problema que ela
        # existe para resolver — um termo nunca visto numa classe tem
        # probabilidade zero, e um único zero zera o produto inteiro, então uma
        # palavra desconhecida basta para eliminar uma intenção inteira.
        self.assertGreater(construir_classificador().named_steps["classificador"].alpha, 0)


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
    def test_config_padrao_e_a_primeira_colocada_do_experimento(self):
        # Trava contra alguém trocar o padrão sem passar pelo experimento. Os
        # valores abaixo são o rank #1 de resultados/comparativo_preprocessamento.md
        # — `bow n=1` com `[tok:split] (texto cru)`, nenhuma etapa ligada.
        # Se este teste falhar, o comparativo e docs/PipelinePLN.md precisam ser
        # atualizados junto.
        #
        # O que este teste NÃO garante: que essa seja a melhor forma de preparar
        # o texto. Ela venceu um empate de 2261 configurações, todas em F1
        # 1,0000, por ser a mais simples — ver a ressalva em classificador.py.
        self.assertEqual(
            CONFIG_PRE_PADRAO.etapas_ativas_na_ordem(), ("remover_numeros", "morfologia")
        )
        self.assertIs(CONFIG_PRE_PADRAO.tokenizacao, Tokenizacao.REGEX)
        self.assertIs(CONFIG_VET_PADRAO.modo, ModoVetorizacao.BOW)
        self.assertEqual(CONFIG_VET_PADRAO.n_max, 1)

    def test_dataset_de_exemplo_carrega(self):
        textos, rotulos = carregar_dataset(DATASET_PADRAO)
        self.assertEqual(len(textos), len(rotulos))
        self.assertGreater(len(textos), 0)


class TesteClassificadorDoProdutoEAReguaDoExperimento(unittest.TestCase):
    # O pré-processamento padrão foi escolhido medindo com a régua do
    # experimento, então trocar o classificador aqui faria essa escolha valer
    # para um modelo que não é o que roda.

    def test_produto_usa_a_mesma_classe_da_regua(self):
        do_produto = construir_classificador().named_steps["classificador"]
        da_regua = construir_pipeline_de_medicao(CONFIG_VET_PADRAO).named_steps["classificador"]
        self.assertIs(type(do_produto), type(da_regua))

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
