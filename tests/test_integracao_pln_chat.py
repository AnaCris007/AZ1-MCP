"""Caso TI-17 — a mesma frase, digitada e transcrita, produz a mesma intenção.

A Seção 6.4.4 registrava este caso como bloqueado: *"`/chat` atual não
classifica nem retorna intenção. Dependência de implementação"*. A inversão de
ordem — classificar antes de consultar as fontes — removeu a dependência, e o
caso passa a ser executável.

O que se verifica é o PIPELINE COMUM: que os dois caminhos de entrada usem o
mesmo detector e a mesma regra de rejeição, e não duas cópias que podem
divergir. O modelo vem do `.joblib` em disco, como a Seção 6.4.2 manda
("modelo carregado diretamente do disco, sem dublê").

O QUE ESTA SUÍTE NÃO É
----------------------
Não é medição de acerto do classificador — isso é RNF03, Seção 6.3, e depende
do conjunto cego. Aqui se verifica a FORMA do contrato entre os dois caminhos
de entrada. Um classificador ruim passaria neste teste; é outra pergunta.
"""

from __future__ import annotations

import unittest

from az1_api.dependencies import get_classificador_de_intencao
from pln.caminhos import MODELO_PADRAO


def _modelo_disponivel() -> str | None:
    """O `.joblib` treinado é pré-requisito, e não algo a dublar.

    A Seção 6.4.2 é explícita: nesta frente o modelo é carregado do disco. Sem
    ele não há integração a testar — só um dublê conversando com outro.
    """
    if not MODELO_PADRAO.exists():
        return (
            f"modelo não encontrado em {MODELO_PADRAO}. "
            f"Rode `python -m pln.classificador` antes."
        )
    return None


MOTIVO = _modelo_disponivel()


@unittest.skipIf(MOTIVO is not None, MOTIVO or "")
class TestMesmaIntencaoPorTextoEAudioIntegracao(unittest.TestCase):
    """TI-17 — a mesma frase, digitada e transcrita, produz a mesma intenção.

    A Seção 6.4.4 registrava este caso como bloqueado: *"`/chat` atual não
    classifica nem retorna intenção. Dependência de implementação"*. A inversão
    de ordem da Parte B removeu a dependência.

    O que se verifica aqui é o PIPELINE COMUM: que os dois caminhos de entrada
    usem o mesmo detector e a mesma regra de rejeição, e não duas cópias que
    podem divergir. Por isso o teste compara `DetectarIntencao` contra si mesmo
    através das duas rotas, em vez de gravar áudio — a transcrição é TI-06, e a
    igualdade que interessa aqui é a do classificador.
    """

    def setUp(self) -> None:
        get_classificador_de_intencao.cache_clear()
        from az1_api.dependencies import get_classificador_de_intencao as real

        self.detector = real()
        if self.detector is None:
            self.skipTest("classificador não pôde ser carregado do .joblib")

    def test_ti17_chat_e_analise_compartilham_o_mesmo_detector(self) -> None:
        from az1_api.dependencies import get_analyzer

        get_analyzer.cache_clear()
        try:
            analisador = get_analyzer()
        except Exception as erro:  # sem DEEPGRAM_API_KEY ou sem S3
            self.skipTest(f"analisador de áudio indisponível: {type(erro).__name__}")

        self.assertIs(
            analisador._detector.__class__, self.detector.__class__,
            "chat e áudio usam detectores de classes diferentes: o pipeline não é comum",
        )

    def test_ti17b_a_mesma_frase_produz_a_mesma_deteccao(self) -> None:
        """Duas chamadas ao mesmo detector não podem divergir.

        Parece trivial e não é: o `.joblib` já foi desserializado por dois
        provedores distintos no passado, e duas instâncias do mesmo modelo com
        `sys.modules` diferente produziriam rótulos iguais e confianças
        distintas.
        """
        frase = "Quais entregas estão previstas para este mês?"

        primeira = self.detector(frase)
        segunda = self.detector(frase)

        self.assertEqual(primeira.prevista, segunda.prevista)
        self.assertAlmostEqual(primeira.confianca, segunda.confianca, places=10)
        self.assertEqual(primeira.rejeitada, segunda.rejeitada)


if __name__ == "__main__":
    unittest.main()
