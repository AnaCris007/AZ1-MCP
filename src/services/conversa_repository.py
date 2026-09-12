# Persistência de conversas: o texto no S3, a linha de rastreio no banco.
#
# POR QUE OS DOIS, E NÃO UM SÓ
# ----------------------------
# A decisão do time foi guardar os prompts num bucket. Ela é atendida aqui, mas
# sem abrir mão da linha em `auditoria.mensagem`, por três motivos concretos:
#
#   1. O RNF04 foi escrito nomeando as tabelas: "`conversa.id` e `mensagem.id`
#      identificam a conversa e cada turno". Só-S3 deixaria a implementação fora
#      de passo com o texto do próprio requisito.
#   2. "Quais conversas caíram em `fora_do_catalogo` esta semana?" é uma linha de
#      SQL sobre `idx_mensagem_intencao`, e uma varredura de bucket inteiro do
#      outro lado.
#   3. `auditoria.mensagem.conteudo` é NOT NULL. O schema não admite a linha sem
#      o texto — então a duplicação não é escolha minha, é o modelo que o time
#      aprovou.
#
# O que o S3 acrescenta, já que a coluna existe: uma cópia FORA do banco. A
# imutabilidade do RNF09 o schema já dá de graça (`REVOKE UPDATE, DELETE ON
# auditoria.mensagem`), mas ela não sobrevive a um projeto Supabase recriado —
# e recriar projeto é coisa que acontece em conta gratuita. A retenção de 90
# dias fica no ciclo de vida do bucket, em `infra/minio/lifecycle.json`.
#
# POR QUE NÃO EXISTE COLUNA APONTANDO PARA O OBJETO
# -------------------------------------------------
# `audio_referencia` guarda a chave do áudio porque ela nasce fora: o upload
# devolve "aud_<hex>" e não há como recalculá-la. A chave do turno nós geramos,
# a partir de `(conversa_id, ordem)` — que a tabela já mantém UNIQUE. Derivar
# em vez de gravar evita uma coluna redundante e, com ela, o estado em que
# coluna e objeto discordam.
#
# O preço é que mudar `chave_do_turno` órfã todos os objetos antigos. Por isso
# o formato está numa função só, com um teste que o fixa: quem mexer vai ver o
# teste vermelho antes de ver o estrago.
#
# ORDEM DAS ESCRITAS
# ------------------
# O S3 é escrito DENTRO da transação, depois dos INSERTs e antes do commit.
# Assim as duas falhas possíveis caem do lado seguro:
#
#   - S3 falha  → a transação reverte, e não fica linha apontando para objeto
#                 que não existe.
#   - banco falha depois do S3 → sobra um objeto órfão, que é inofensivo: o
#                 conteúdo foi preservado, que é o que a auditoria quer.

from __future__ import annotations

import io
import logging
import uuid
from dataclasses import dataclass
from typing import Any, BinaryIO, Protocol

from psycopg_pool import ConnectionPool

logger = logging.getLogger(__name__)

# Prefixo próprio, e deliberadamente diferente de `incoming/`: a regra de ciclo
# de vida daquele expira em 7 dias, e o RNF09 exige no mínimo 90.
PREFIXO_CONVERSAS = "conversas/"

PAPEL_USUARIO = "usuario"
PAPEL_AGENTE = "agente"

# Os domínios abaixo replicam os CHECK de `auditoria.mensagem`. Validar aqui não
# substitui a restrição do banco — ela continua sendo a autoridade; o que isto
# dá é uma mensagem de erro que diz qual valor está errado, em vez de um
# `CheckViolation` genérico depois de metade da transação já ter rodado.
#
# O risco de duplicar é divergir. `tests/test_conversa_repository.py` lê o DDL e
# compara com estas constantes, de modo que a divergência reprove a suíte.
INTENCOES_VALIDAS = frozenset(
    {
        "consultar_documentos_normativos",
        "consultar_projeto_sintetico",
        "orientar_mapa_beneficios",
        "orientar_tap",
        "orientar_entregas_cronograma",
        "orientar_avanco_mensal",
        "orientar_riscos_problemas",
        "analisar_completude_coerencia",
        "gerar_alertas_pendencias",
        "fora_do_catalogo",
    }
)
RESULTADOS_VALIDOS = frozenset({"sucesso", "esclarecimento", "recusada", "falha"})
FORMATOS_VALIDOS = frozenset({"texto", "audio"})

# `conversa.titulo` é o rótulo da barra lateral, derivado da primeira mensagem.
TAMANHO_MAXIMO_TITULO = 80

TIPO_DE_CONTEUDO = "text/plain; charset=utf-8"


class Armazenamento(Protocol):
    """O contrato que `S3ObjectStorage` já cumpre."""

    def store(
        self,
        *,
        key: str,
        content: BinaryIO,
        content_type: str,
        metadata: dict[str, str],
    ) -> None: ...


@dataclass(frozen=True)
class FonteDaResposta:
    """Um chunk que fundamentou a resposta, copiado no momento em que ela saiu.

    Os metadados são cópia, e não junção: `mensagem_fonte` precisa continuar
    legível depois de o documento ser reindexado — reindexar troca o `chunk_id`,
    porque ele é o md5 do conteúdo.
    """

    chunk_id: str
    arquivo_origem: str
    posicao: int
    score: float | None = None
    projeto_codigo: str | None = None
    tipo_documento: str | None = None
    secao: str | None = None
    trecho: str | None = None


def conversa_uuid(valor: str | None) -> str | None:
    """O identificador normalizado, ou None se ele não serve como chave.

    `auditoria.conversa.id` é UUID. O frontend gera `crypto.randomUUID()`, mas o
    Swagger, os testes e qualquer outro cliente mandam o que quiserem — e um
    valor malformado só falharia lá dentro da tarefa de fundo, com
    `InvalidTextRepresentation`, depois da resposta já ter sido enviada.

    Recusar aqui, e devolvendo None em vez de levantar, é deliberado: a trilha é
    efeito colateral de `POST /chat`. Um identificador ruim não pode custar a
    resposta ao usuário — no máximo custa o registro dela.
    """
    if not valor:
        return None
    try:
        return str(uuid.UUID(valor))
    except ValueError:
        return None


@dataclass(frozen=True)
class TurnoDoChat:
    """Um par pergunta-resposta, que vira duas linhas irmãs em `mensagem`."""

    conversa_id: str
    usuario_id: int
    prompt: str
    resposta: str
    resultado: str

    # Saída do pipeline de PLN. Vai na linha do USUÁRIO — o CHECK
    # `mensagem_papel_coerente` recusa intenção na linha do agente.
    intencao: str | None = None
    confianca_intencao: float | None = None

    # Vão na linha do AGENTE, pelo mesmo CHECK.
    modelo: str | None = None
    tempo_processamento_ms: int | None = None

    formato: str = "texto"
    fontes: tuple[FonteDaResposta, ...] = ()


@dataclass(frozen=True)
class TurnoGravado:
    ordem_prompt: int
    ordem_resposta: int
    mensagem_usuario_id: int
    mensagem_agente_id: int
    chave_prompt: str
    chave_resposta: str


def chave_do_turno(conversa_id: str, ordem: int, papel: str) -> str:
    """A chave do objeto no bucket.

    ESTE FORMATO É CONTRATO. Nenhuma coluna guarda a chave: ela é recalculada a
    partir da linha sempre que alguém precisa do objeto. Mudar o formato torna
    inalcançável tudo o que já foi gravado.

    `ordem` vai com seis dígitos para que a listagem do prefixo saia na ordem da
    conversa — S3 ordena chaves como texto, e sem o zero à esquerda o turno 10
    apareceria antes do 9.
    """
    return f"{PREFIXO_CONVERSAS}{conversa_id}/{ordem:06d}-{papel}.txt"


def titulo_a_partir_do_prompt(prompt: str) -> str:
    limpo = " ".join(prompt.split())
    if len(limpo) <= TAMANHO_MAXIMO_TITULO:
        return limpo
    return limpo[: TAMANHO_MAXIMO_TITULO - 1].rstrip() + "…"


_SQL_GARANTIR_CONVERSA = """
INSERT INTO auditoria.conversa (id, usuario_id, titulo)
VALUES (%s, %s, %s)
ON CONFLICT (id) DO NOTHING
"""

# `FOR UPDATE` serializa os turnos de UMA conversa. Sem ele, dois turnos
# simultâneos leriam o mesmo `max(ordem)` e o segundo bateria no
# `UNIQUE (conversa_id, ordem)` — falha correta, porém desnecessária.
_SQL_TRAVAR_CONVERSA = """
SELECT usuario_id FROM auditoria.conversa WHERE id = %s FOR UPDATE
"""

_SQL_PROXIMA_ORDEM = """
SELECT coalesce(max(ordem), 0) FROM auditoria.mensagem WHERE conversa_id = %s
"""

_SQL_INSERIR_MENSAGEM = """
INSERT INTO auditoria.mensagem (
    conversa_id, ordem, papel, formato, conteudo,
    intencao, confianca_intencao,
    resultado, modelo, tempo_processamento_ms
) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
RETURNING id
"""

_SQL_INSERIR_FONTE = """
INSERT INTO auditoria.mensagem_fonte (
    mensagem_id, posicao, chunk_id, score,
    projeto_codigo, tipo_documento, arquivo_origem, secao, trecho
) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
"""


class ConversaNaoGravada(RuntimeError):
    """Turno recusado antes de tocar o banco, por dado incoerente."""


@dataclass(frozen=True)
class ConversaResumida:
    id: str
    titulo: str
    atualizada_em: str


@dataclass(frozen=True)
class MensagemRegistrada:
    ordem: int
    papel: str
    conteudo: str


_SQL_LISTAR_CONVERSAS = """
SELECT id, coalesce(titulo, '(sem título)'), atualizada_em
  FROM auditoria.conversa
 WHERE usuario_id = %s AND arquivada_em IS NULL
 ORDER BY atualizada_em DESC
 LIMIT %s
"""

# O `usuario_id` entra no WHERE, e não só a conversa: enquanto a RLS não estiver
# em vigor (a aplicação conecta como dono), é este filtro que impede alguém de
# ler a conversa de outra pessoa passando o UUID dela.
_SQL_MENSAGENS_DA_CONVERSA = """
SELECT m.ordem, m.papel, m.conteudo
  FROM auditoria.mensagem m
  JOIN auditoria.conversa c ON c.id = m.conversa_id
 WHERE m.conversa_id = %s AND c.usuario_id = %s
 ORDER BY m.ordem
"""


class PersistenciaDesligada:
    """Ocupa o lugar de `ConversaRepository` quando não há banco configurado.

    Gravar a trilha é efeito colateral de `POST /chat`, não a razão de a rota
    existir. Sem este objeto nulo, `get_connection_pool()` levanta durante a
    RESOLUÇÃO das dependências do FastAPI e a conversa inteira vira 500 — a
    ausência de banco derrubaria o produto em vez de apenas deixar de auditá-lo.

    Foi exatamente essa a falha de pipeline que
    `tests/test_dependencias_sem_banco.py` passou a vigiar. O aviso sai UMA vez,
    e não a cada requisição.
    """

    def __init__(self, motivo: str) -> None:
        self._motivo = motivo
        self._avisou = False

    def registrar_turno(self, turno: TurnoDoChat) -> None:
        self._avisar()

    def listar_conversas(self, usuario_id: int, limite: int = 50) -> tuple:
        self._avisar()
        return ()

    def mensagens_da_conversa(self, conversa_id: str, usuario_id: int) -> tuple:
        self._avisar()
        return ()

    def registrar_avaliacao(self, **_: object) -> bool:
        self._avisar()
        return False

    def _avisar(self) -> None:
        if not self._avisou:
            logger.warning("Persistência de conversas desligada: %s", self._motivo)
            self._avisou = True


# `auditoria.avaliacao` tem CHECK em polaridade e motivo. Mesma regra de sempre:
# duplicar os domínios aqui dá erro legível antes da transação, e um teste que lê
# o DDL impede que as listas se afastem.
POLARIDADES_VALIDAS = frozenset({"positiva", "negativa"})
MOTIVOS_VALIDOS = frozenset(
    {
        "resposta_incorreta",
        "fonte_irrelevante",
        "resposta_incompleta",
        "nao_entendeu_pergunta",
        "demorou_demais",
        "resposta_util",
        "outro",
    }
)

# A avaliação recai sobre a mensagem, e não sobre a conversa: o CHECK
# `avaliacao_alvo_unico` aceita um ou outro, e por mensagem é o que permite
# saber QUAL resposta foi ruim — que é o sinal útil para melhorar o modelo.
#
# `mensagem_id` é resolvido a partir de (conversa_id, ordem), que a tabela
# mantém UNIQUE. O cliente não conhece o id: ele é gerado por IDENTITY numa
# tarefa de fundo, depois de a resposta já ter saído.
_SQL_AVALIAR = """
INSERT INTO auditoria.avaliacao (usuario_id, mensagem_id, polaridade, motivo, comentario)
SELECT %s, m.id, %s, %s, %s
  FROM auditoria.mensagem m
  JOIN auditoria.conversa c ON c.id = m.conversa_id
 WHERE m.conversa_id = %s AND m.ordem = %s AND c.usuario_id = %s
RETURNING id
"""


class ConversaRepository:
    def __init__(self, pool: ConnectionPool, armazenamento: Armazenamento) -> None:
        self._pool = pool
        self._armazenamento = armazenamento

    def listar_conversas(self, usuario_id: int, limite: int = 50) -> tuple[ConversaResumida, ...]:
        """As conversas da pessoa, da mais recente para a mais antiga.

        Arquivadas ficam de fora: `arquivada_em` é exclusão lógica — o RNF09
        exige reter 90 dias, então "apagar conversa" na interface é ocultar, não
        remover.
        """
        with self._pool.connection() as conexao, conexao.cursor() as cursor:
            cursor.execute(_SQL_LISTAR_CONVERSAS, (usuario_id, limite))
            return tuple(
                ConversaResumida(id=str(i), titulo=tit, atualizada_em=at.isoformat())
                for i, tit, at in cursor.fetchall()
            )

    def mensagens_da_conversa(
        self, conversa_id: str, usuario_id: int
    ) -> tuple[MensagemRegistrada, ...]:
        """Os turnos de uma conversa, se ela for da pessoa que pediu."""
        with self._pool.connection() as conexao, conexao.cursor() as cursor:
            cursor.execute(_SQL_MENSAGENS_DA_CONVERSA, (conversa_id, usuario_id))
            return tuple(
                MensagemRegistrada(ordem=o, papel=p, conteudo=c)
                for o, p, c in cursor.fetchall()
            )


    def registrar_avaliacao(
        self,
        *,
        usuario_id: int,
        conversa_id: str,
        ordem: int,
        polaridade: str,
        motivo: str | None = None,
        comentario: str | None = None,
    ) -> bool:
        """Registra o juízo sobre uma resposta. False se o alvo não existe.

        O INSERT é um `INSERT ... SELECT` com o filtro de dono embutido: uma
        mensagem de outra pessoa simplesmente não produz linha, e o método
        devolve False — sem consulta prévia e sem janela entre verificar e
        gravar.
        """
        if polaridade not in POLARIDADES_VALIDAS:
            raise ConversaNaoGravada(
                f"polaridade {polaridade!r} fora do domínio: {sorted(POLARIDADES_VALIDAS)}."
            )
        if motivo is not None and motivo not in MOTIVOS_VALIDOS:
            raise ConversaNaoGravada(
                f"motivo {motivo!r} fora do domínio: {sorted(MOTIVOS_VALIDOS)}."
            )

        with self._pool.connection() as conexao, conexao.cursor() as cursor:
            cursor.execute(
                _SQL_AVALIAR,
                (usuario_id, polaridade, motivo, comentario, conversa_id, ordem, usuario_id),
            )
            return cursor.fetchone() is not None

    def registrar_turno(self, turno: TurnoDoChat) -> TurnoGravado:
        _validar(turno)

        with self._pool.connection() as conexao:
            with conexao.cursor() as cursor:
                cursor.execute(
                    _SQL_GARANTIR_CONVERSA,
                    (
                        turno.conversa_id,
                        turno.usuario_id,
                        titulo_a_partir_do_prompt(turno.prompt),
                    ),
                )
                cursor.execute(_SQL_TRAVAR_CONVERSA, (turno.conversa_id,))
                cursor.execute(_SQL_PROXIMA_ORDEM, (turno.conversa_id,))
                ultima = cursor.fetchone()[0]

                ordem_prompt = ultima + 1
                ordem_resposta = ultima + 2

                cursor.execute(
                    _SQL_INSERIR_MENSAGEM,
                    (
                        turno.conversa_id,
                        ordem_prompt,
                        PAPEL_USUARIO,
                        turno.formato,
                        turno.prompt,
                        turno.intencao,
                        turno.confianca_intencao,
                        # As quatro colunas do agente são anuladas pelo CHECK
                        # `mensagem_papel_coerente` quando o papel é 'usuario'.
                        None,
                        None,
                        None,
                    ),
                )
                id_usuario = cursor.fetchone()[0]

                cursor.execute(
                    _SQL_INSERIR_MENSAGEM,
                    (
                        turno.conversa_id,
                        ordem_resposta,
                        PAPEL_AGENTE,
                        turno.formato,
                        turno.resposta,
                        # Idem, do outro lado: intenção e confiança pertencem ao
                        # prompt, não à resposta.
                        None,
                        None,
                        turno.resultado,
                        turno.modelo,
                        turno.tempo_processamento_ms,
                    ),
                )
                id_agente = cursor.fetchone()[0]

                for fonte in turno.fontes:
                    cursor.execute(
                        _SQL_INSERIR_FONTE,
                        (
                            id_agente,
                            fonte.posicao,
                            fonte.chunk_id,
                            fonte.score,
                            fonte.projeto_codigo,
                            fonte.tipo_documento,
                            fonte.arquivo_origem,
                            fonte.secao,
                            fonte.trecho,
                        ),
                    )

            # Ainda dentro da transação, de propósito — ver o cabeçalho.
            chave_prompt = self._arquivar(
                turno.conversa_id, ordem_prompt, PAPEL_USUARIO, turno.prompt, id_usuario
            )
            chave_resposta = self._arquivar(
                turno.conversa_id, ordem_resposta, PAPEL_AGENTE, turno.resposta, id_agente
            )

        return TurnoGravado(
            ordem_prompt=ordem_prompt,
            ordem_resposta=ordem_resposta,
            mensagem_usuario_id=id_usuario,
            mensagem_agente_id=id_agente,
            chave_prompt=chave_prompt,
            chave_resposta=chave_resposta,
        )

    def _arquivar(
        self, conversa_id: str, ordem: int, papel: str, texto: str, mensagem_id: int
    ) -> str:
        chave = chave_do_turno(conversa_id, ordem, papel)
        self._armazenamento.store(
            key=chave,
            content=io.BytesIO(texto.encode("utf-8")),
            content_type=TIPO_DE_CONTEUDO,
            # Só identificadores e números: metadado de objeto S3 viaja em
            # cabeçalho HTTP, e acento no cabeçalho quebra a assinatura em
            # algumas implementações. O texto vai no corpo, onde UTF-8 é seguro.
            metadata={
                "conversa-id": conversa_id,
                "mensagem-id": str(mensagem_id),
                "ordem": str(ordem),
                "papel": papel,
            },
        )
        return chave


def _validar(turno: TurnoDoChat) -> None:
    if not turno.prompt.strip():
        raise ConversaNaoGravada("O prompt não pode ser vazio: `conteudo` é NOT NULL.")
    if not turno.resposta.strip():
        raise ConversaNaoGravada("A resposta não pode ser vazia: `conteudo` é NOT NULL.")
    if turno.resultado not in RESULTADOS_VALIDOS:
        raise ConversaNaoGravada(
            f"resultado {turno.resultado!r} fora do domínio de auditoria.mensagem: "
            f"{sorted(RESULTADOS_VALIDOS)}."
        )
    if turno.intencao is not None and turno.intencao not in INTENCOES_VALIDAS:
        raise ConversaNaoGravada(
            f"intencao {turno.intencao!r} fora do catálogo da Seção 3.1. O domínio do "
            f"banco e o de pln/classificador.py precisam continuar iguais."
        )
    if turno.formato not in FORMATOS_VALIDOS:
        raise ConversaNaoGravada(
            f"formato {turno.formato!r} fora do domínio: {sorted(FORMATOS_VALIDOS)}."
        )
    if turno.confianca_intencao is not None and not 0 <= turno.confianca_intencao <= 1:
        raise ConversaNaoGravada(
            f"confianca_intencao {turno.confianca_intencao} fora de [0, 1]."
        )
    if turno.tempo_processamento_ms is not None and turno.tempo_processamento_ms < 0:
        raise ConversaNaoGravada("tempo_processamento_ms não pode ser negativo.")

    for fonte in turno.fontes:
        # Uma fonte sem chunk_id passa no NOT NULL como string vazia e só
        # aparece como problema meses depois, quando alguém tentar voltar da
        # afirmação para o trecho. O RNF12 morre em silêncio assim.
        if not fonte.chunk_id:
            raise ConversaNaoGravada(
                "fonte sem chunk_id: a trilha precisa apontar para um chunk da coleção."
            )
        if not fonte.arquivo_origem:
            raise ConversaNaoGravada(
                "fonte sem arquivo_origem: mensagem_fonte.arquivo_origem é NOT NULL."
            )
        if fonte.posicao < 1:
            raise ConversaNaoGravada(
                f"posicao {fonte.posicao} inválida: mensagem_fonte exige posicao > 0."
            )

    posicoes = [f.posicao for f in turno.fontes]
    if len(set(posicoes)) != len(posicoes):
        raise ConversaNaoGravada(
            "duas fontes com a mesma posição: mensagem_fonte tem UNIQUE (mensagem_id, posicao)."
        )
    chunks = [f.chunk_id for f in turno.fontes]
    if len(set(chunks)) != len(chunks):
        raise ConversaNaoGravada(
            "o mesmo chunk citado duas vezes: mensagem_fonte tem UNIQUE (mensagem_id, chunk_id)."
        )


def fontes_da_busca(resultados: Any) -> tuple[FonteDaResposta, ...]:
    """Converte a saída de `rag.retriever.buscar` em fontes graváveis.

    A posição é o índice da lista, que já vem ordenada por relevância — é o que
    `mensagem_fonte.posicao` documenta ("1 = mais próximo").

    `trecho` recebe o texto do chunk no momento da resposta, e não uma junção
    feita depois: reindexar um documento troca o `chunk_id` (ele é o md5 do
    conteúdo), então a junção deixaria de encontrar a fonte justamente na
    auditoria, que é quando ela precisa continuar legível.
    """
    return tuple(
        FonteDaResposta(
            chunk_id=r.chunk_id,
            arquivo_origem=r.arquivo_origem,
            posicao=i,
            score=r.score,
            projeto_codigo=r.projeto_id,
            tipo_documento=r.tipo_documento,
            secao=r.secao,
            trecho=r.texto,
        )
        for i, r in enumerate(resultados, start=1)
    )
