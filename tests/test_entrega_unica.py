# =============================================================================
# test_entrega_unica.py — O arquivo único não pode divergir dos módulos
# =============================================================================
#     python -m unittest discover tests -v
#
# `entregas/pln_completo.py` é uma cópia gerada de `src/pln/`. Cópia que ninguém
# confere envelhece: a versão anterior deste arquivo tinha 1769 linhas escritas
# à mão e já divergia da fonte — referenciava um módulo inexistente e carregava
# o nome errado do dataset, os mesmos defeitos que estavam nos módulos, porque
# consertar em um lugar nunca consertava no outro.
#
# O teste abaixo é o que torna essa divergência impossível de passar despercebida:
# ele regenera o arquivo em memória e compara com o que está em disco. Editar a
# entrega à mão, ou mexer num módulo sem regenerar, quebra a suíte.
# =============================================================================

from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
GERADOR = RAIZ / "scripts" / "gerar_pln_completo.py"
ENTREGA = RAIZ / "entregas" / "pln_completo.py"


class TesteEntregaUnica(unittest.TestCase):
    def test_arquivo_unico_esta_atualizado(self):
        # Roda o gerador em modo `--conferir`, que não escreve nada e sai com 1
        # se o conteúdo em disco for diferente do que ele produziria agora.
        processo = subprocess.run(
            [sys.executable, str(GERADOR), "--conferir"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(
            processo.returncode,
            0,
            "entregas/pln_completo.py está desatualizado em relação a src/pln/.\n"
            "Rode: python scripts/gerar_pln_completo.py\n\n"
            f"{processo.stdout}{processo.stderr}",
        )

    def test_entrega_roda_sem_o_pacote_instalado(self):
        # A razão de existir do arquivo único é rodar sozinho. Este teste tira
        # `src/` do caminho de import e confirma que ele ainda sobe — se alguém
        # deixar um `from pln...` escapar para dentro dele, quebra aqui.
        ambiente_limpo = {"PYTHONPATH": "", "PATH": "/usr/bin:/bin"}
        processo = subprocess.run(
            [sys.executable, str(ENTREGA), "--help"],
            capture_output=True,
            text=True,
            env=ambiente_limpo,
            cwd=RAIZ,
        )
        self.assertEqual(processo.returncode, 0, processo.stderr)
        for subcomando in ("treinar", "prever", "experimento", "ajuste"):
            self.assertIn(subcomando, processo.stdout, f"o subcomando `{subcomando}` sumiu da entrega")

    def test_todo_modulo_do_pacote_esta_na_entrega(self):
        # A entrega se apresenta como "o pipeline inteiro em um arquivo". Se
        # alguém criar um módulo novo em src/pln/ e esquecer de acrescentá-lo a
        # `MODULOS` no gerador, a promessa deixa de ser verdade em silêncio — foi
        # o que aconteceu com `ajuste_fino.py`.
        import re

        modulos_no_pacote = {
            caminho.stem
            for caminho in (RAIZ / "src" / "pln").glob("*.py")
            if caminho.stem != "__init__"
        }
        gerador = GERADOR.read_text(encoding="utf-8")
        bloco = gerador[gerador.index("MODULOS:"):gerador.index("COM_CLI:")]
        declarados = set(re.findall(r'\("(\w+)",', bloco))
        self.assertEqual(
            modulos_no_pacote - declarados,
            set(),
            "módulo em src/pln/ que não entra na entrega — acrescente a `MODULOS` no gerador",
        )

    def test_cabecalho_avisa_que_e_gerado(self):
        # O aviso é a única defesa contra alguém abrir o arquivo, achar bonito e
        # começar a editar.
        cabecalho = ENTREGA.read_text(encoding="utf-8")[:1500]
        self.assertIn("ARQUIVO GERADO", cabecalho)
        self.assertIn("scripts/gerar_pln_completo.py", cabecalho)


if __name__ == "__main__":
    unittest.main(verbosity=2)
