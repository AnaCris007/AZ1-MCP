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

from pln.caminhos import DATASET_PADRAO
from pln.classificador import (
    CONFIG_PRE_PADRAO,
    CONFIG_VET_PADRAO,
    PreprocessadorDeTexto,
    VarianteNB,
    avaliar_classificador,
    carregar_dataset,
    carregar_modelo,
    construir_classificador,
    listar_palavras_de_maior_peso_por_intencao,
    prever_intencao,
    salvar_modelo,
    variantes_compativeis,
)
from pln.preprocessamento import ConfigPreprocessamento, ModoStopwords, Tokenizacao, preprocessar
from pln.vetorizacao import ConfigVetorizacao, ModoVetorizacao

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
        from pln.classificador import ALPHA_PADRAO, FIT_PRIOR_PADRAO, VARIANTE_PADRAO

        self.assertIs(VARIANTE_PADRAO, VarianteNB.MULTINOMIAL)
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
        self.assertEqual(CONFIG_PRE_PADRAO.etapas_ativas_na_ordem(), ())
        self.assertIs(CONFIG_PRE_PADRAO.tokenizacao, Tokenizacao.SPLIT)
        self.assertIs(CONFIG_VET_PADRAO.modo, ModoVetorizacao.BOW)
        self.assertEqual(CONFIG_VET_PADRAO.n_max, 1)

    def test_dataset_de_exemplo_carrega(self):
        textos, rotulos = carregar_dataset(DATASET_PADRAO)
        self.assertEqual(len(textos), len(rotulos))
        self.assertGreater(len(textos), 0)


class TesteCompatibilidadeDeVariante(unittest.TestCase):
    # A escolha da variante de Naive Bayes NÃO é livre: ela é determinada pela
    # vetorização. Multinomial e Complement estimam P(termo|classe) somando
    # colunas, e soma negativa não é probabilidade de nada; vetores de embedding
    # têm coordenadas negativas por construção. Gaussiano é o caminho inverso:
    # lê coordenada contínua e não sabe o que fazer com matriz esparsa.
    #
    # Sem a checagem, a combinação errada morre lá no fundo do scikit-learn com
    # `ValueError: Negative values in data`, que não menciona nem embeddings nem
    # Naive Bayes e manda quem lê procurar no lugar errado.

    EMBEDDING = ConfigVetorizacao(ModoVetorizacao.EMBEDDING, n_max=1)
    BOW = ConfigVetorizacao(ModoVetorizacao.BOW, n_max=1)

    def test_denso_so_aceita_gaussiano(self):
        self.assertEqual(variantes_compativeis(self.EMBEDDING), (VarianteNB.GAUSSIANO,))

    def test_esparso_nao_aceita_gaussiano(self):
        self.assertNotIn(VarianteNB.GAUSSIANO, variantes_compativeis(self.BOW))

    def test_toda_variante_serve_a_alguma_familia(self):
        # Uma variante que não fosse compatível com nada seria inalcançável — e
        # continuaria aparecendo em `--variante` na linha de comando.
        cobertas = set(variantes_compativeis(self.BOW)) | set(variantes_compativeis(self.EMBEDDING))
        self.assertEqual(cobertas, set(VarianteNB))

    def test_combinacao_invalida_e_recusada_com_mensagem_util(self):
        with self.assertRaises(ValueError) as caso:
            construir_classificador(config_vet=self.EMBEDDING, variante=VarianteNB.MULTINOMIAL)
        mensagem = str(caso.exception)
        self.assertIn("multinomial", mensagem)
        self.assertIn("gaussiano", mensagem, "a mensagem não diz qual variante usar")

    def test_combinacao_valida_treina(self):
        modelo = construir_classificador(
            config_vet=self.EMBEDDING, variante=VarianteNB.GAUSSIANO, alpha=1e-9
        )
        self.assertEqual(len(modelo.fit(TEXTOS, ROTULOS).predict(["Qual o status?"])), 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
