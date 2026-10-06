"""Todo pacote de `src/` precisa estar declarado no `pyproject.toml`.

POR QUE ESTE TESTE EXISTE
-------------------------
A lista de `[tool.hatch.build.targets.wheel]` é explícita, e nada no projeto
falha quando um pacote novo fica de fora dela. Em desenvolvimento e na suíte de
testes o `src/` está no caminho de importação, então o módulo é encontrado
assim mesmo; dentro da imagem, onde a aplicação roda a partir do que foi
INSTALADO no venv, ele simplesmente não existe.

O sintoma é um `ModuleNotFoundError` na subida do contêiner, depois de um build
inteiramente verde: o build não importa a aplicação, então nada acusa. Foi
exatamente assim que `src/mcp_servidor` chegou a um deploy e o derrubou.
"""

from __future__ import annotations

import pathlib
import tomllib
import unittest

RAIZ = pathlib.Path(__file__).resolve().parent.parent


class Empacotamento(unittest.TestCase):
    def test_todo_pacote_de_src_esta_declarado_no_pyproject(self) -> None:
        config = tomllib.loads((RAIZ / "pyproject.toml").read_text(encoding="utf-8"))
        declarados = set(config["tool"]["hatch"]["build"]["targets"]["wheel"]["packages"])

        # Sem exigir `__init__.py`: `src/config` guarda só YAML e é empacotado
        # assim mesmo, porque a aplicação lê esses arquivos em tempo de execução.
        # `frontend` é projeto Node e não entra na roda Python.
        ignorar = {"frontend", "__pycache__"}
        no_disco = {f"src/{p.name}" for p in (RAIZ / "src").iterdir() if p.is_dir() and p.name not in ignorar}

        self.assertEqual(
            no_disco - declarados,
            set(),
            "Pacote em src/ fora da lista do pyproject.toml. Ele funciona nos testes, "
            "porque src/ está no caminho de importação, e some dentro da imagem.",
        )
        self.assertEqual(declarados - no_disco, set(), "pyproject.toml declara pacote que não existe em src/.")


if __name__ == "__main__":
    unittest.main()
