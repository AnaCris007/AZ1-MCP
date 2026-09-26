# Testes da trava que impede a evidência do inventário de cair dentro do
# repositório.
#
# O relatório de `scripts/inventariar_indice_rag.py` carrega a forma da base
# vetorial do parceiro. Os identificadores saem como hash, mas as CONTAGENS não:
# quantos chunks, quantos documentos, quantos sem metadado. Versionar isso por
# acidente publica no histórico do Git um retrato que não se apaga com um
# `git rm` — e o histórico deste repositório é lido por quem não participou da
# sprint.
#
# A task pedia que uma pessoa rodasse o comando à mão e conferisse o código de
# saída 1. Isso vale uma vez, no dia do MR. Estes testes valem em toda execução
# do CI, e não dependem de banco.

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
MODULO = RAIZ / "scripts" / "inventariar_indice_rag.py"


def _carregar():
    """Importa o executor pelo caminho.

    `scripts/` não é pacote — não tem `__init__.py` e não está no `src` do
    projeto —, então `import` comum não o alcança. Carregar por spec é o que
    permite testar o script sem transformá-lo em módulo instalável só por causa
    do teste.
    """
    spec = importlib.util.spec_from_file_location("inventariar_indice_rag", MODULO)
    modulo = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = modulo
    spec.loader.exec_module(modulo)
    return modulo


inventario = _carregar()


class TesteCaminhoDeSaida(unittest.TestCase):
    def test_caminho_dentro_do_repositorio_e_recusado(self) -> None:
        with self.assertRaises(inventario.InventarioError) as contexto:
            inventario._caminho_de_saida(RAIZ / "inventario-rag.json")

        self.assertIn("dentro do repositório", str(contexto.exception))

    def test_subpasta_do_repositorio_tambem_e_recusada(self) -> None:
        # O caso perigoso não é a raiz, é `docs/evidencias/` — uma pasta que já
        # existe, já é versionada, e onde a evidência "pareceria" pertencer.
        with self.assertRaises(inventario.InventarioError):
            inventario._caminho_de_saida(RAIZ / "docs" / "evidencias" / "inventario.json")

    def test_a_propria_raiz_e_recusada(self) -> None:
        with self.assertRaises(inventario.InventarioError):
            inventario._caminho_de_saida(RAIZ)

    def test_caminho_externo_e_aceito(self) -> None:
        externo = RAIZ.parent / "inventario-rag.json"

        resolvido = inventario._caminho_de_saida(externo)

        self.assertEqual(resolvido, externo.resolve())

    def test_irmao_com_nome_parecido_nao_e_confundido_com_o_repositorio(self) -> None:
        # A comparação é por componente de caminho, não por prefixo de texto.
        # `g01-evidencias` ao lado de `g01` está FORA, e recusá-lo seria um falso
        # positivo que empurraria a pessoa a desligar a trava.
        vizinho = RAIZ.parent / f"{RAIZ.name}-evidencias" / "inventario.json"

        resolvido = inventario._caminho_de_saida(vizinho)

        self.assertEqual(resolvido, vizinho.resolve())

    def test_caminho_relativo_e_resolvido_antes_de_decidir(self) -> None:
        # `--saida ../fora.json` a partir da raiz cai fora do repositório, e
        # decidir pelo texto do argumento, sem resolver, erraria o veredito.
        resolvido = inventario._caminho_de_saida(Path("..") / "fora.json")

        self.assertEqual(resolvido, (Path.cwd() / ".." / "fora.json").resolve())


class TesteOrdemDasVerificacoes(unittest.TestCase):
    def test_a_recusa_acontece_antes_de_tocar_o_banco(self) -> None:
        """A trava é a primeira coisa que `main` avalia.

        Se ela rodasse depois da consulta, uma execução recusada ainda teria
        aberto conexão e lido a base — e o custo de errar o caminho passaria a
        incluir um acesso ao banco do parceiro.
        """
        chamou_banco = False

        def _executar_espiao(*_args, **_kwargs):
            nonlocal chamou_banco
            chamou_banco = True
            return {}

        original_executar = inventario._executar
        original_argumentos = inventario._argumentos
        inventario._executar = _executar_espiao
        inventario._argumentos = lambda: type(
            "Args", (), {"saida": RAIZ / "inventario-rag.json"}
        )()
        try:
            codigo = inventario.main()
        finally:
            inventario._executar = original_executar
            inventario._argumentos = original_argumentos

        self.assertEqual(codigo, 1)
        self.assertFalse(chamou_banco)


class TesteConsultaDoInventario(unittest.TestCase):
    """Acoplamento com o SQL, que vive fora do Python e muda sem avisar."""

    def setUp(self) -> None:
        self.sql = inventario.ARQUIVO_SQL.read_text(encoding="utf-8")

    def test_o_arquivo_sql_existe_no_caminho_que_o_script_espera(self) -> None:
        self.assertTrue(inventario.ARQUIVO_SQL.is_file())

    def test_os_padroes_com_barra_invertida_usam_prefixo_e(self) -> None:
        """Sem o `E`, a barra invertida deixa de ser escape e o padrão morre.

        Com `standard_conforming_strings` ligado — padrão desde o PostgreSQL 9.1
        —, `'\\\\.'` entrega ao regex uma barra literal seguida de qualquer
        caractere. O detector de e-mail passou a exigir uma barra antes do TLD e
        só podia devolver zero, o que foi relatado como "nenhum e-mail
        encontrado". Um achado de segurança vazio parecendo um achado limpo.
        """
        barra = chr(92)
        for linha in self.sql.split("\n"):
            if barra not in linha or linha.lstrip().startswith("--"):
                continue
            with self.subTest(linha=linha.strip()):
                self.assertIn(
                    "E'",
                    linha,
                    "literal com barra invertida sem prefixo E: o regex recebe a "
                    "barra como caractere e o padrão deixa de casar",
                )

    def test_a_consulta_nao_escreve(self) -> None:
        # O executor abre transação READ ONLY, mas o SQL é lido de um arquivo:
        # a trava do servidor protege o banco, e esta protege a intenção.
        proibidos = ("insert ", "update ", "delete ", "drop ", "alter ", "truncate ")
        corpo = " ".join(
            linha for linha in self.sql.lower().split("\n")
            if not linha.lstrip().startswith("--")
        )
        for comando in proibidos:
            with self.subTest(comando=comando.strip()):
                self.assertNotIn(comando, corpo)


if __name__ == "__main__":
    unittest.main()
