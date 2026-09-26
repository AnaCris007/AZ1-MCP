# Contrato das rotas de portfólio.
#
# As chaves testadas aqui não são escolha de estilo: são exatamente as que
# `TasksView.jsx` e `CalendarView.jsx` leem. Renomear qualquer uma faz a
# interface voltar silenciosamente para os dados de exemplo, porque o
# componente trata qualquer resposta inesperada como "backend indisponível".
# Por isso os nomes estão fixados campo a campo.

from __future__ import annotations

import unittest
from datetime import date, time

from fastapi.testclient import TestClient
from psycopg import OperationalError
from psycopg.errors import UndefinedTable

from az1_api.dependencies import (
    get_evento_local_repository,
    get_portfolio_repository,
    require_authenticated_user,
)
from az1_api.main import app
from routes.portfolio import formatar_dia, formatar_dia_da_semana, montar_agenda
from services.auth_service import AuthenticatedUser
from services.database_service import BancoNaoConfigurado
from services.evento_local_repository import EventoLocal
from services.portfolio_repository import Pendencia, SituacaoInvalida, SituacaoProjeto


def _evento_local(id=1, titulo="Dentista", data=date(2026, 11, 30), hora=None, descricao="") -> EventoLocal:
    return EventoLocal(id=id, titulo=titulo, data=data, hora=hora, descricao=descricao)


_USUARIO = AuthenticatedUser(
    subject="s", email="e@x", name="n", provider="azure", domain_user_id=1
)
_USUARIO_SEM_IDENTIDADE = AuthenticatedUser(
    subject="s", email="e@x", name="n", provider="disabled", domain_user_id=None
)


def _projeto(codigo="SYN-01", termino=date(2026, 11, 30)) -> SituacaoProjeto:
    return SituacaoProjeto(
        id=1, codigo=codigo, nome="Modernização da Ventilação",
        fase="Execução", status="Atrasado",
        data_inicio=date(2026, 2, 15), data_termino_prevista=termino,
        percentual_previsto=82.0, percentual_avanco=64.0, desvio_pp=-18.0,
        lider="Rafael Antunes", lider_email="rafael@metro.example",
        pendencias_abertas=4, artefatos=5,
    )


def _pendencia(
    pid=1, criticidade="Crítico", situacao="aberta", prazo=None, titulo="Atraso na entrega"
) -> Pendencia:
    return Pendencia(
        id=pid, projeto_codigo="SYN-01", projeto_nome="Modernização da Ventilação",
        codigo="R01", tipo="risco", titulo=titulo,
        descricao="Fornecedor pode postergar entregas",
        criticidade=criticidade, responsavel="Gerência de Engenharia",
        prazo=prazo, situacao=situacao,
    )


class _RepositorioFalso:
    def __init__(self, projetos=(), pendencias=(), atualizada="nao-definido"):
        self._projetos = tuple(projetos)
        self._pendencias = tuple(pendencias)
        self._atualizada = atualizada
        self.escritas: list[tuple[int, str]] = []

    def situacao_dos_projetos(self):
        return self._projetos

    def pendencias(self):
        return self._pendencias

    def alterar_situacao(self, *, pendencia_id: int, situacao: str):
        self.escritas.append((pendencia_id, situacao))
        if self._atualizada == "nao-definido":
            return _pendencia(pid=pendencia_id, situacao=situacao)
        if isinstance(self._atualizada, Exception):
            raise self._atualizada
        return self._atualizada


class _RepositorioDeEventosLocaisFalso:
    def __init__(self, eventos=(), criado="nao-definido", erro_ao_listar=None):
        self._eventos = tuple(eventos)
        self._criado = criado
        self._erro_ao_listar = erro_ao_listar
        self.chamadas_listar: list[int] = []
        self.criados: list[dict] = []
        self.apagados: list[tuple[int, int]] = []

    def listar(self, usuario_id):
        self.chamadas_listar.append(usuario_id)
        if self._erro_ao_listar is not None:
            raise self._erro_ao_listar
        return self._eventos

    def criar(self, *, usuario_id, titulo, data, hora, descricao):
        self.criados.append({"usuario_id": usuario_id, "titulo": titulo, "data": data, "hora": hora, "descricao": descricao})
        if self._criado == "nao-definido":
            return _evento_local(id=99, titulo=titulo, data=data, hora=hora, descricao=descricao)
        return self._criado

    def apagar(self, *, usuario_id, evento_id):
        self.apagados.append((usuario_id, evento_id))
        return usuario_id == 1 and evento_id == 7


class _BaseDePortfolio(unittest.TestCase):
    def setUp(self):
        self.repositorio = _RepositorioFalso()
        self.repositorio_eventos_locais = _RepositorioDeEventosLocaisFalso()
        app.dependency_overrides[require_authenticated_user] = lambda: _USUARIO
        app.dependency_overrides[get_portfolio_repository] = lambda: self.repositorio
        app.dependency_overrides[get_evento_local_repository] = lambda: self.repositorio_eventos_locais
        self.client = TestClient(app, raise_server_exceptions=False)
        self.addCleanup(app.dependency_overrides.clear)


class TesteTasks(_BaseDePortfolio):
    def test_as_chaves_sao_as_que_o_frontend_le(self):
        self.repositorio = _RepositorioFalso(pendencias=[_pendencia()])
        app.dependency_overrides[get_portfolio_repository] = lambda: self.repositorio

        corpo = self.client.get("/api/v1/tasks").json()

        self.assertEqual(
            set(corpo[0]),
            {"id", "title", "project", "priority", "dueDate", "description", "done"},
        )

    def test_projeto_traz_codigo_e_nome(self):
        # Só o nome não identifica: dois projetos podem ter títulos parecidos, e
        # o código é o que aparece nas citações do chat.
        self.repositorio = _RepositorioFalso(pendencias=[_pendencia()])
        app.dependency_overrides[get_portfolio_repository] = lambda: self.repositorio

        corpo = self.client.get("/api/v1/tasks").json()
        self.assertTrue(corpo[0]["project"].startswith("SYN-01 —"))

    def test_criticidade_colapsa_em_tres_prioridades(self):
        casos = {"Crítico": "alta", "Alto": "alta", "Moderado": "media", "Baixo": "baixa"}
        for criticidade, esperada in casos.items():
            with self.subTest(criticidade=criticidade):
                self.repositorio = _RepositorioFalso(
                    pendencias=[_pendencia(criticidade=criticidade)]
                )
                app.dependency_overrides[get_portfolio_repository] = lambda: self.repositorio
                corpo = self.client.get("/api/v1/tasks").json()
                self.assertEqual(corpo[0]["priority"], esperada)

    def test_criticidade_desconhecida_nao_derruba_a_rota(self):
        # `criticidade` é TEXT sem CHECK no banco: um valor novo não pode virar
        # KeyError e derrubar a listagem inteira.
        self.repositorio = _RepositorioFalso(pendencias=[_pendencia(criticidade="Urgentíssimo")])
        app.dependency_overrides[get_portfolio_repository] = lambda: self.repositorio

        resposta = self.client.get("/api/v1/tasks")
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta.json()[0]["priority"], "media")

    def test_prazo_ausente_vira_string_vazia_e_nao_nulo(self):
        # `prazo` é NULL em todas as 18 linhas da base atual. O frontend espera
        # string; `null` quebraria a formatação da data.
        self.repositorio = _RepositorioFalso(pendencias=[_pendencia(prazo=None)])
        app.dependency_overrides[get_portfolio_repository] = lambda: self.repositorio

        self.assertEqual(self.client.get("/api/v1/tasks").json()[0]["dueDate"], "")

    def test_resolvida_vira_done(self):
        self.repositorio = _RepositorioFalso(pendencias=[_pendencia(situacao="resolvida")])
        app.dependency_overrides[get_portfolio_repository] = lambda: self.repositorio
        self.assertTrue(self.client.get("/api/v1/tasks").json()[0]["done"])


class TestePatchDeTask(_BaseDePortfolio):
    def test_done_true_grava_resolvida(self):
        self.client.patch("/api/v1/tasks/7", json={"done": True})
        self.assertEqual(self.repositorio.escritas, [(7, "resolvida")])

    def test_done_false_grava_aberta(self):
        self.client.patch("/api/v1/tasks/7", json={"done": False})
        self.assertEqual(self.repositorio.escritas, [(7, "aberta")])

    def test_campos_de_texto_nao_chegam_ao_banco(self):
        # O modal de edição envia título, descrição e projeto inteiros. Nenhum
        # pode ser gravado: esse texto está vetorizado em `vecs.documentos_metro`
        # e editá-lo faria a linha e o trecho citado pelo chat discordarem.
        self.client.patch(
            "/api/v1/tasks/7",
            json={"done": True, "title": "outro título", "description": "outra", "project": "SYN-09"},
        )
        self.assertEqual(self.repositorio.escritas, [(7, "resolvida")])

    def test_situacao_explicita_vence_o_booleano(self):
        # Saída para quem precisa dos quatro estados do CHECK.
        self.client.patch("/api/v1/tasks/7", json={"done": True, "situacao": "em_tratamento"})
        self.assertEqual(self.repositorio.escritas, [(7, "em_tratamento")])

    def test_sem_done_nem_situacao_e_422(self):
        self.assertEqual(self.client.patch("/api/v1/tasks/7", json={}).status_code, 422)

    def test_situacao_fora_do_dominio_e_422(self):
        self.repositorio = _RepositorioFalso(atualizada=SituacaoInvalida("fora"))
        app.dependency_overrides[get_portfolio_repository] = lambda: self.repositorio
        resposta = self.client.patch("/api/v1/tasks/7", json={"situacao": "inventada"})
        self.assertEqual(resposta.status_code, 422)

    def test_pendencia_inexistente_e_404(self):
        # Não 200 silencioso: quem marcou uma tarefa precisa saber que ela não
        # foi marcada.
        self.repositorio = _RepositorioFalso(atualizada=None)
        app.dependency_overrides[get_portfolio_repository] = lambda: self.repositorio
        self.assertEqual(
            self.client.patch("/api/v1/tasks/999", json={"done": True}).status_code, 404
        )

    def test_devolve_a_linha_relida_e_nao_o_que_foi_enviado(self):
        # A interface deve exibir o que o banco aceitou. `em_tratamento`
        # desmarcada volta como `aberta`, e o cliente precisa enxergar isso.
        self.repositorio = _RepositorioFalso(atualizada=_pendencia(pid=7, situacao="aberta"))
        app.dependency_overrides[get_portfolio_repository] = lambda: self.repositorio
        corpo = self.client.patch("/api/v1/tasks/7", json={"done": True}).json()
        self.assertFalse(corpo["done"])


class TesteCalendario(_BaseDePortfolio):
    def test_a_forma_aninhada_e_a_que_o_componente_consome(self):
        self.repositorio = _RepositorioFalso(projetos=[_projeto()])
        app.dependency_overrides[get_portfolio_repository] = lambda: self.repositorio

        corpo = self.client.get("/api/v1/calendar/events").json()
        dia = corpo["days"][0]
        self.assertEqual(set(dia), {"date", "weekday", "events", "iso"})
        self.assertEqual(
            set(dia["events"][0]),
            {"id", "title", "type", "project", "time", "description", "responsible", "status"},
        )
        self.assertEqual(dia["iso"], "2026-11-30")

    def test_marco_e_prazo_continuam_sem_hora_fabricada(self):
        # Não há tabela de compromissos para eles no modelo: inventar "09:00"
        # para preencher a coluna seria fabricar dado. Só eventos próprios
        # carregam hora real — ver test_evento_local_aparece_na_agenda_com_hora_real.
        self.repositorio = _RepositorioFalso(projetos=[_projeto()])
        app.dependency_overrides[get_portfolio_repository] = lambda: self.repositorio
        corpo = self.client.get("/api/v1/calendar/events").json()
        self.assertEqual(corpo["days"][0]["events"][0]["time"], "")

    def test_rota_degrada_quando_tabela_de_eventos_locais_nao_existe(self):
        # Migração de banco e deploy de código são passos separados neste
        # projeto: uma instalação que ainda não rodou 07_evento_local.sql não
        # pode derrubar a Agenda inteira com 500 por causa disso.
        self.repositorio = _RepositorioFalso(projetos=[_projeto()])
        app.dependency_overrides[get_portfolio_repository] = lambda: self.repositorio
        self.repositorio_eventos_locais = _RepositorioDeEventosLocaisFalso(
            erro_ao_listar=UndefinedTable('relation "portfolio.evento_local" does not exist')
        )
        app.dependency_overrides[get_evento_local_repository] = lambda: self.repositorio_eventos_locais

        resposta = self.client.get("/api/v1/calendar/events")
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta.json()["days"][0]["events"][0]["type"], "marco")

    def test_falha_de_banco_ao_listar_eventos_locais_devolve_503(self):
        self.repositorio_eventos_locais = _RepositorioDeEventosLocaisFalso(
            erro_ao_listar=OperationalError("conexão indisponível")
        )
        app.dependency_overrides[get_evento_local_repository] = lambda: self.repositorio_eventos_locais

        resposta = self.client.get("/api/v1/calendar/events")

        self.assertEqual(resposta.status_code, 503)
        self.assertEqual(resposta.json()["error"], "agenda_indisponivel")

    def test_erro_de_programacao_ao_listar_eventos_locais_nao_e_mascarado(self):
        self.repositorio_eventos_locais = _RepositorioDeEventosLocaisFalso(
            erro_ao_listar=RuntimeError("erro inesperado")
        )
        app.dependency_overrides[get_evento_local_repository] = lambda: self.repositorio_eventos_locais

        resposta = self.client.get("/api/v1/calendar/events")

        self.assertEqual(resposta.status_code, 500)
        self.assertEqual(resposta.json()["error"], "internal_error")

    def test_evento_local_aparece_na_agenda_com_hora_real(self):
        self.repositorio_eventos_locais = _RepositorioDeEventosLocaisFalso(
            eventos=[_evento_local(data=date(2026, 12, 5), hora=time(9, 0))]
        )
        app.dependency_overrides[get_evento_local_repository] = lambda: self.repositorio_eventos_locais

        corpo = self.client.get("/api/v1/calendar/events").json()
        evento = corpo["days"][0]["events"][0]
        self.assertEqual(evento["type"], "evento")
        self.assertEqual(evento["time"], "09:00")
        self.assertEqual(self.repositorio_eventos_locais.chamadas_listar, [1])

    def test_evento_local_sem_hora_nao_fabrica_horario(self):
        self.repositorio_eventos_locais = _RepositorioDeEventosLocaisFalso(
            eventos=[_evento_local(data=date(2026, 12, 5), hora=None)]
        )
        app.dependency_overrides[get_evento_local_repository] = lambda: self.repositorio_eventos_locais

        corpo = self.client.get("/api/v1/calendar/events").json()
        self.assertEqual(corpo["days"][0]["events"][0]["time"], "")

    def test_evento_local_e_marco_no_mesmo_dia_ficam_juntos(self):
        dias = montar_agenda(
            [_projeto("SYN-01", termino=date(2026, 11, 30))],
            [],
            [_evento_local(data=date(2026, 11, 30))],
        )
        self.assertEqual(len(dias), 1)
        self.assertEqual(len(dias[0].events), 2)

    def test_sem_identidade_agenda_responde_200_sem_eventos_proprios(self):
        # AZ1_AUTH_MODE=disabled, ou ResolveOrCreateUsuario falhou: sem
        # domain_user_id não há "meus eventos", mas a Agenda não pode quebrar
        # por causa disso.
        app.dependency_overrides[require_authenticated_user] = lambda: _USUARIO_SEM_IDENTIDADE
        self.repositorio = _RepositorioFalso(projetos=[_projeto()])
        app.dependency_overrides[get_portfolio_repository] = lambda: self.repositorio

        resposta = self.client.get("/api/v1/calendar/events")
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta.json()["days"][0]["events"][0]["type"], "marco")
        self.assertEqual(self.repositorio_eventos_locais.chamadas_listar, [])

    def test_montar_agenda_continua_aceitando_dois_argumentos(self):
        # Compatibilidade posicional: eventos_locais é o terceiro parâmetro,
        # opcional, e chamadas existentes não devem precisar mudar.
        self.assertEqual(montar_agenda([], []), [])

    def test_data_e_unica_por_dia(self):
        # `key={day.date}` no React: data repetida duplica chave e o componente
        # passa a renderizar errado sem erro.
        dias = montar_agenda(
            [_projeto("SYN-01"), _projeto("SYN-02")],
            [_pendencia(pid=1, prazo=date(2026, 11, 30))],
        )
        datas = [d.date for d in dias]
        self.assertEqual(len(datas), len(set(datas)))
        self.assertEqual(len(dias[0].events), 3)

    def test_pendencia_resolvida_nao_ocupa_a_agenda(self):
        dias = montar_agenda([], [_pendencia(prazo=date(2026, 5, 1), situacao="resolvida")])
        self.assertEqual(dias, [])

    def test_dias_saem_em_ordem_cronologica(self):
        dias = montar_agenda(
            [_projeto("SYN-A", date(2026, 12, 1)), _projeto("SYN-B", date(2026, 3, 1))], []
        )
        self.assertEqual([d.date for d in dias], ["1 de março", "1 de dezembro"])


class TesteEventoLocal(_BaseDePortfolio):
    def test_cria_evento_e_devolve_a_forma_esperada(self):
        resposta = self.client.post(
            "/api/v1/calendar/events",
            json={"titulo": "Dentista", "data": "2026-12-05", "hora": "09:00", "descricao": "Checkup"},
        )
        self.assertEqual(resposta.status_code, 201)
        self.assertEqual(
            set(resposta.json()), {"id", "title", "date", "time", "description"}
        )
        self.assertEqual(self.repositorio_eventos_locais.criados[0]["usuario_id"], 1)

    def test_sem_titulo_e_422(self):
        resposta = self.client.post(
            "/api/v1/calendar/events", json={"titulo": "  ", "data": "2026-12-05"}
        )
        self.assertEqual(resposta.status_code, 422)

    def test_data_invalida_e_422(self):
        resposta = self.client.post(
            "/api/v1/calendar/events", json={"titulo": "Dentista", "data": "05/12/2026"}
        )
        self.assertEqual(resposta.status_code, 422)

    def test_hora_invalida_e_422(self):
        resposta = self.client.post(
            "/api/v1/calendar/events",
            json={"titulo": "Dentista", "data": "2026-12-05", "hora": "9h"},
        )
        self.assertEqual(resposta.status_code, 422)

    def test_sem_identidade_e_422(self):
        app.dependency_overrides[require_authenticated_user] = lambda: _USUARIO_SEM_IDENTIDADE
        resposta = self.client.post(
            "/api/v1/calendar/events", json={"titulo": "Dentista", "data": "2026-12-05"}
        )
        self.assertEqual(resposta.status_code, 422)

    def test_apaga_evento_proprio_e_devolve_204(self):
        resposta = self.client.delete("/api/v1/calendar/events/7")
        self.assertEqual(resposta.status_code, 204)
        self.assertEqual(self.repositorio_eventos_locais.apagados, [(1, 7)])

    def test_apagar_evento_inexistente_ou_de_outra_pessoa_e_404(self):
        resposta = self.client.delete("/api/v1/calendar/events/999")
        self.assertEqual(resposta.status_code, 404)


class TesteFormatacaoDeData(unittest.TestCase):
    # Formatar com `locale` daria nomes diferentes no Windows de desenvolvimento
    # e na imagem Alpine do contêiner — e falharia como texto errado, não como
    # exceção.
    def test_mes_em_portugues(self):
        self.assertEqual(formatar_dia(date(2026, 3, 30)), "30 de março")

    def test_dia_da_semana_em_portugues(self):
        self.assertEqual(formatar_dia_da_semana(date(2026, 11, 30)), "segunda-feira")

    def test_cobre_os_doze_meses_e_os_sete_dias(self):
        meses = {formatar_dia(date(2026, m, 1)).split(" de ")[1] for m in range(1, 13)}
        self.assertEqual(len(meses), 12)
        dias = {formatar_dia_da_semana(date(2026, 6, d)) for d in range(1, 8)}
        self.assertEqual(len(dias), 7)


class TesteSemBanco(unittest.TestCase):
    def test_responde_503_e_nao_lista_vazia(self):
        # Aqui o banco é a razão do endpoint, não acessório: devolver 200 com
        # lista vazia seria a mesma mentira que os dados de exemplo.
        def sem_banco():
            raise BancoNaoConfigurado("SUPABASE_DB_URL não configurada.")

        app.dependency_overrides[require_authenticated_user] = lambda: _USUARIO
        app.dependency_overrides[get_portfolio_repository] = sem_banco
        self.addCleanup(app.dependency_overrides.clear)

        cliente = TestClient(app, raise_server_exceptions=False)
        self.assertEqual(cliente.get("/api/v1/tasks").status_code, 503)


if __name__ == "__main__":
    unittest.main(verbosity=2)
