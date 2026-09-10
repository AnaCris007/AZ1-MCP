# Testes de reprodutibilidade das métricas de PLN.
#
# O F1-macro publicado em `resultados/` só é reproduzível se as versões das
# bibliotecas que o produzem estiverem fixadas. Enquanto `requirements.txt`
# usava pisos (`scikit-learn>=1.4`), a documentação declarava versões exatas
# que nenhum arquivo garantia — e duas delas já haviam derivado silenciosamente
# do que a tabela afirmava. Um rebuild podia mudar o número medido sem que
# nenhum teste acusasse.
#
# Estes testes fecham essa porta: as três fontes (os dois arquivos de
# dependência e a tabela da Seção 3.3.7) precisam concordar, sempre.

from __future__ import annotations

import re
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent

# As bibliotecas que determinam a métrica. Não é a lista completa de
# dependências do projeto: `fastapi` ou `boto3` não mudam um F1, e fixá-las
# custaria atualizações de segurança sem nada em troca.
PACOTES_DA_METRICA = ("scikit-learn", "nltk", "spacy", "numpy", "joblib")


def _versoes_do_requirements() -> dict[str, str]:
    texto = (RAIZ / "requirements.txt").read_text(encoding="utf-8")
    return dict(re.findall(r"^([A-Za-z0-9_.-]+)==([0-9][^\s#]*)", texto, re.MULTILINE))


def _versoes_do_pyproject() -> dict[str, str]:
    texto = (RAIZ / "pyproject.toml").read_text(encoding="utf-8")
    return dict(re.findall(r'"([A-Za-z0-9_.-]+)==([0-9][^"]*)"', texto))


def _versoes_da_documentacao() -> dict[str, str]:
    texto = (RAIZ / "docs" / "Projeto.md").read_text(encoding="utf-8")
    # Linhas da tabela da Seção 3.3.7: | `pacote` | versão | papel |
    return dict(re.findall(r"^\|\s*`([a-z-]+)`\s*\|\s*([0-9][0-9.]*)\s*\|", texto, re.MULTILINE))


class TesteVersoesFixadas(unittest.TestCase):
    def test_requirements_fixa_os_pacotes_da_metrica(self):
        fixadas = _versoes_do_requirements()
        for pacote in PACOTES_DA_METRICA:
            self.assertIn(
                pacote, fixadas,
                f"{pacote} precisa estar fixado com == em requirements.txt. Com piso >=, "
                f"um rebuild muda o F1-macro publicado em resultados/ e nada acusa.",
            )

    def test_pyproject_fixa_os_pacotes_da_metrica(self):
        fixadas = _versoes_do_pyproject()
        for pacote in PACOTES_DA_METRICA:
            self.assertIn(
                pacote, fixadas,
                f"{pacote} precisa estar fixado com == em pyproject.toml.",
            )

    def test_requirements_e_pyproject_concordam(self):
        req, pyp = _versoes_do_requirements(), _versoes_do_pyproject()
        for pacote in PACOTES_DA_METRICA:
            self.assertEqual(
                req[pacote], pyp[pacote],
                f"{pacote} está em versões diferentes nos dois arquivos de dependência: "
                f"requirements.txt diz {req[pacote]}, pyproject.toml diz {pyp[pacote]}.",
            )

    def test_documentacao_declara_as_versoes_realmente_fixadas(self):
        # Este é o teste que teria pego a deriva: a tabela dizia spacy 3.8.15 e
        # joblib 1.5.3 enquanto o ambiente rodava 3.8.16 e 1.6.0.
        req, doc = _versoes_do_requirements(), _versoes_da_documentacao()
        for pacote in PACOTES_DA_METRICA:
            self.assertIn(
                pacote, doc,
                f"{pacote} não aparece na tabela de bibliotecas da Seção 3.3.7.",
            )
            self.assertEqual(
                doc[pacote], req[pacote],
                f"a Seção 3.3.7 declara {pacote} {doc[pacote]}, mas requirements.txt fixa "
                f"{req[pacote]}. Regere os relatórios de resultados/ antes de editar a tabela.",
            )


class TesteAmbienteInstaladoBateComOsPins(unittest.TestCase):
    # Diferente dos anteriores: aqueles comparam arquivos entre si, este
    # compara o que está fixado com o que de fato foi importado. É o que
    # detecta um ambiente montado fora do requirements.
    def test_versoes_instaladas_sao_as_fixadas(self):
        from importlib.metadata import PackageNotFoundError, version

        fixadas = _versoes_do_requirements()
        for pacote in PACOTES_DA_METRICA:
            try:
                instalada = version(pacote)
            except PackageNotFoundError:
                self.skipTest(f"{pacote} não está instalado neste ambiente")
            self.assertEqual(
                instalada, fixadas[pacote],
                f"o ambiente tem {pacote} {instalada}, mas requirements.txt fixa "
                f"{fixadas[pacote]}. As métricas em resultados/ foram medidas com a versão "
                f"fixada; reinstale com `pip install -r requirements.txt`.",
            )


# Os módulos que compõem o pipeline de PLN propriamente dito. A Seção 3.3.9
# conta só estes; o README conta a suíte inteira, que inclui os testes de API
# e de serviços. Os dois números são diferentes de propósito.
MODULOS_DO_PIPELINE = (
    "test_ajuste_fino.py",
    "test_bancada.py",
    "test_classificador.py",
    "test_experimento.py",
    "test_preprocessamento.py",
    "test_reprodutibilidade.py",
    "test_vetorizacao.py",
)


def _contar_testes(arquivos) -> int:
    padrao = re.compile(r"^\s+(?:async )?def test", re.MULTILINE)
    return sum(len(padrao.findall(a.read_text(encoding="utf-8"))) for a in arquivos)


class TesteContagensDocumentadas(unittest.TestCase):
    # README e documentação afirmavam 106, 145 e 100 testes ao mesmo tempo. Dois
    # desses números estavam certos para escopos diferentes e um estava obsoleto,
    # o que é pior que estar tudo errado: não dá para saber qual acreditar sem
    # contar à mão. Estes testes contam.
    def test_readme_declara_o_total_da_suite(self):
        total = _contar_testes(sorted((RAIZ / "tests").glob("test_*.py")))
        readme = (RAIZ / "README.md").read_text(encoding="utf-8")
        self.assertIn(
            f"# {total} testes", readme,
            f"a suíte tem {total} testes, mas o README declara outro número. "
            f"Atualize as duas ocorrências em README.md.",
        )
        self.assertIn(
            f"# os {total} testes, dentro da imagem", readme,
            f"a suíte tem {total} testes, mas o README declara outro número no bloco Docker.",
        )

    def test_documentacao_declara_os_testes_do_pipeline(self):
        pipeline = _contar_testes(RAIZ / "tests" / nome for nome in MODULOS_DO_PIPELINE)
        doc = (RAIZ / "docs" / "Projeto.md").read_text(encoding="utf-8")
        self.assertIn(
            f"O pipeline tem **{pipeline} testes automatizados**", doc,
            f"os módulos do pipeline de PLN somam {pipeline} testes, mas a Seção 3.3.9 "
            f"declara outro número.",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
