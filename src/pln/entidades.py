# Extração de entidades por regras, não por modelo.
#
# O catálogo de intenções (docs/Projeto.md §3.1) prevê entidades além da
# intenção, mas o dataset de treino só rotula `texto,intencao` — sem anotação
# de entidade, um extrator estatístico não tem como ser treinado nem validado.
#
# O que É seguro extrair por regra é o código do projeto: segue um padrão fixo
# (`portfolio.projeto.codigo`, ver `database/02_initial_data.sql`) e não exige
# entender a frase. Nomes em linguagem natural ("a ventilação", "Linha 6") não
# são extraídos aqui: sem dado de treino anotado, uma regra ad hoc erraria
# silenciosamente, e cada erro silencioso é uma consulta respondida sobre o
# projeto errado.

from __future__ import annotations

import re
from dataclasses import dataclass

_PADRAO_CODIGO_PROJETO = re.compile(r"\bSYN-\d{2}\b", re.IGNORECASE)


@dataclass(frozen=True)
class EntidadesExtraidas:
    projeto_codigo: str | None = None


def extrair_entidades(texto: str) -> EntidadesExtraidas:
    encontrado = _PADRAO_CODIGO_PROJETO.search(texto)
    return EntidadesExtraidas(projeto_codigo=encontrado.group(0).upper() if encontrado else None)
