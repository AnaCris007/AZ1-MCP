# O que a API faz quando não há banco configurado.
#
# Este módulo existe por causa de uma falha de pipeline concreta: sem
# `SUPABASE_DB_URL`, `obter_engine()` levantava durante a RESOLUÇÃO das
# dependências do FastAPI, antes de o corpo da rota rodar. O efeito era que
# `POST /chat` e `POST /audio/{id}/analyze` respondiam 500 — não por falha do
# chat nem da análise, mas porque a gravação da trilha e o despacho de alertas,
# ambos acessórios, penduram-se neles.
#
# A distinção que os testes abaixo prendem:
#
#   - onde o banco é ACESSÓRIO (efeito colateral de outra rota), a dependência
#     degrada para um objeto nulo e a rota continua respondendo;
#   - onde o banco é a RAZÃO do endpoint (alertas, auditoria), a dependência
#     levanta `BancoNaoConfigurado`, que vira 503 — indisponibilidade, e não o
#     500 genérico que diria "defeito de programação".
#
# Nenhum desses caminhos é exercitado no desenvolvimento local, onde o `.env`
# existe. Só a CI passa por eles, que foi exatamente onde a falha apareceu.

from __future__ import annotations

import os
import unittest
from unittest import mock

from az1_api import dependencies as dep
from database.conexao import BancoNaoConfigurado, obter_engine
from services.alerta_service import DespachoDesligado
from services.auditoria_service import GravacaoDesligada

# Os provedores e o engine são `lru_cache`: sem limpar, um teste enxergaria o
# objeto que outro construiu com o ambiente anterior.
_COM_CACHE = (
    obter_engine,
    dep.get_gravador_auditoria,
    dep.get_alerta_dispatcher,
    dep.get_listador_auditoria,
    dep.get_alerta_registrador,
    dep.get_alerta_desativador,
    dep.get_alerta_listador,
)


class _SemBanco(unittest.TestCase):
    def setUp(self):
        ambiente = {k: v for k, v in os.environ.items() if k != "SUPABASE_DB_URL"}
        patch = mock.patch.dict(os.environ, ambiente, clear=True)
        patch.start()
        self.addCleanup(patch.stop)
        self._limpar_caches()
        self.addCleanup(self._limpar_caches)

    @staticmethod
    def _limpar_caches():
        for funcao in _COM_CACHE:
            funcao.cache_clear()


class TesteDependenciasAcessoriasDegradam(_SemBanco):
    def test_gravador_de_auditoria_vira_objeto_nulo(self):
        self.assertIsInstance(dep.get_gravador_auditoria(), GravacaoDesligada)

    def test_gravar_sem_banco_nao_levanta(self):
        # É o que mantém `POST /chat` respondendo: a trilha se perde, a conversa
        # não.
        dep.get_gravador_auditoria().gravar(
            mensagem="oi", resposta="olá", conversation_id="c", duracao_ms=1
        )

    def test_despachante_de_alertas_vira_objeto_nulo(self):
        self.assertIsInstance(dep.get_alerta_dispatcher(), DespachoDesligado)

    def test_despachar_sem_banco_nao_levanta(self):
        dep.get_alerta_dispatcher().despachar(
            intencao="orientar_tap",
            confianca_pln=0.9,
            audio_id="aud_1",
            transcricao="t",
            projeto_id=None,
        )

    def test_avisa_uma_vez_e_nao_a_cada_chamada(self):
        # Em desenvolvimento sem banco, um aviso por requisição encheria o log a
        # ponto de esconder o que importa.
        gravador = dep.get_gravador_auditoria()
        with self.assertLogs("services.auditoria_service", level="WARNING") as capturado:
            gravador.gravar(mensagem="a", resposta="b", conversation_id="c", duracao_ms=1)
            gravador.gravar(mensagem="a", resposta="b", conversation_id="c", duracao_ms=1)
            gravador.gravar(mensagem="a", resposta="b", conversation_id="c", duracao_ms=1)

        self.assertEqual(len(capturado.output), 1)
        self.assertIn("SUPABASE_DB_URL", capturado.output[0])


class TesteDependenciasEssenciaisLevantam(_SemBanco):
    # Aqui o banco não é acessório: um endpoint de auditoria que responde 200 sem
    # banco estaria mentindo sobre a trilha, e um de alertas aceitaria um
    # assinante que nunca seria gravado.
    def test_listador_de_auditoria(self):
        with self.assertRaises(BancoNaoConfigurado):
            dep.get_listador_auditoria()

    def test_provedores_de_alerta(self):
        for provedor in (
            dep.get_alerta_registrador,
            dep.get_alerta_desativador,
            dep.get_alerta_listador,
        ):
            with self.subTest(provedor=provedor.__name__), self.assertRaises(BancoNaoConfigurado):
                provedor()

    def test_a_mensagem_diz_onde_conseguir_a_url(self):
        with self.assertRaises(BancoNaoConfigurado) as capturado:
            obter_engine()
        self.assertIn("SUPABASE_DB_URL", str(capturado.exception))
        self.assertIn("Connection string", str(capturado.exception))


if __name__ == "__main__":
    unittest.main(verbosity=2)
