# =============================================================================
# test_classificador.py — Testes do classificador de intenções
# =============================================================================
#     python -m unittest discover tests -v
#
# A garantia central deste arquivo é a de `TesteConfiguracaoViajaComOModelo`: o
# pré-processamento é uma etapa do pipeline, então o objeto salvo em disco
# carrega a própria configuração. Sem isso, treinar com um pré-processamento e
# prever com outro é um erro possível — e é o mais difícil de diagnosticar em
# PLN, porque não levanta exceção nenhuma: o modelo simplesmente erra mais.
# =============================================================================

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from sklearn.base import clone

from az1.pln.classificador import (
    CONFIG_PRE_PADRAO,
    PreprocessadorDeTexto,
    avaliar_com_validacao_cruzada,
    carregar_dataset,
    carregar_modelo,
    construir_classificador,
    listar_palavras_de_maior_peso_por_intencao,
    prever_intencao,
    salvar_modelo,
)
from az1.pln.preprocessamento import ConfigPreprocessamento, ModoStopwords, preprocessar

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

    def test_max_iter_alto_o_bastante_para_convergir(self):
        # Com o padrão 100 o otimizador não converge em matrizes esparsas de
        # texto, e o sklearn avisa — o que significa "parou antes de terminar".
        self.assertGreaterEqual(construir_classificador().named_steps["classificador"].max_iter, 1000)


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
        f1, relatorio, matriz, classes = avaliar_com_validacao_cruzada(TEXTOS, ROTULOS, construir_classificador(), k=3)
        self.assertGreaterEqual(f1, 0.0)
        self.assertLessEqual(f1, 1.0)
        self.assertIn("precision", relatorio)
        self.assertEqual(classes, sorted(set(ROTULOS)))
        self.assertEqual(len(matriz), len(classes))

    def test_matriz_de_confusao_soma_o_total_de_exemplos(self):
        _, _, matriz, _ = avaliar_com_validacao_cruzada(TEXTOS, ROTULOS, construir_classificador(), k=3)
        self.assertEqual(sum(sum(linha) for linha in matriz), len(TEXTOS))


class TesteDatasetPadrao(unittest.TestCase):
    def test_config_padrao_veio_do_experimento(self):
        # Trava contra alguém trocar o padrão sem passar pelo experimento:
        # se este teste falhar, a documentação em docs/PipelinePLN.md e os
        # comparativos em resultados/ precisam ser atualizados junto.
        self.assertEqual(CONFIG_PRE_PADRAO.etapas_ativas_na_ordem(), ())

    def test_dataset_de_exemplo_carrega(self):
        from az1.pln.classificador import DATASET_PADRAO

        textos, rotulos = carregar_dataset(DATASET_PADRAO)
        self.assertEqual(len(textos), len(rotulos))
        self.assertGreater(len(textos), 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
