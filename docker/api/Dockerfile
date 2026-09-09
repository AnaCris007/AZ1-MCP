# syntax=docker/dockerfile:1.7
# =============================================================================
# AZ1 — imagem da API (FastAPI + pipeline de PLN)
# =============================================================================
# Build multi-estágio com quatro alvos, cada um com uma razão de existir:
#
#   base    → variáveis de ambiente e caminho do virtualenv, herdado por todos
#   builder → compila e instala dependências; carrega apt e pip (não vai a prod)
#   trainer → treina o classificador; alvo do serviço `trainer` do compose
#   dev     → recarga automática e dependências de teste, para desenvolvimento
#   runtime → o que sobe em produção: venv + modelo + dados do NLTK, nada mais
#
# O ganho do multi-estágio aqui é concreto: `builder` baixa compiladores e o
# cache do pip, `trainer` roda validação cruzada e escreve artefatos. Nada
# disso aparece em `runtime`, que recebe apenas os diretórios prontos via
# `COPY --from`. A superfície de ataque da imagem final não inclui um
# compilador, e o tamanho não inclui o cache de build.
#
# POR QUE DEBIAN SLIM E NÃO ALPINE
# --------------------------------
# A recomendação usual é Alpine pelo tamanho. Aqui ela custaria caro: numpy,
# scikit-learn, spaCy e PyAV publicam wheels manylinux (glibc), e não musllinux
# para todas as versões. No Alpine o pip cai no código-fonte e a build passa a
# compilar C/C++/Fortran por dezenas de minutos — para uma imagem que, ao final,
# não fica menor, porque o peso está nas bibliotecas científicas e não na base.
#
# BuildKit é obrigatório (padrão no Docker 23+): a diretiva `syntax` acima e os
# `--mount=type=cache` abaixo dependem dele.
# =============================================================================

ARG PYTHON_VERSION=3.12

# -----------------------------------------------------------------------------
# base — contrato de ambiente comum a todos os estágios
# -----------------------------------------------------------------------------
FROM python:${PYTHON_VERSION}-slim-bookworm AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONFAULTHANDLER=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_ROOT_USER_ACTION=ignore \
    VIRTUAL_ENV=/app/.venv \
    PATH=/app/.venv/bin:$PATH \
    NLTK_DATA=/opt/nltk_data

# O WORKDIR não é só conveniência: `pln/caminhos.py` localiza a raiz do projeto
# procurando `pyproject.toml` a partir do pacote instalado, subindo a árvore.
# Com o venv em /app/.venv e o pyproject em /app, a busca termina em /app e
# `resultados/` resolve para /app/resultados — independentemente do diretório de
# onde o processo foi iniciado.
WORKDIR /app

# -----------------------------------------------------------------------------
# builder — dependências e instalação do pacote
# -----------------------------------------------------------------------------
FROM base AS builder

# `docker-clean` apaga os .deb baixados ao fim de cada apt-get, o que anularia o
# cache montado abaixo. Removê-lo é o que torna o cache do apt efetivo entre
# builds; `sharing=locked` evita duas builds concorrentes corrompendo o cache.
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt/lists,sharing=locked \
    rm -f /etc/apt/apt.conf.d/docker-clean \
    && apt-get update \
    && apt-get install -y --no-install-recommends build-essential

RUN python -m venv "$VIRTUAL_ENV"

# As dependências entram numa camada própria, antes do código. É a única razão
# de extrair a lista do pyproject em vez de rodar `pip install .` direto: assim
# a camada pesada (~700 MB de wheels científicos) só é refeita quando as
# dependências mudam, e não a cada edição de um .py.
COPY pyproject.toml ./
RUN python -c "import tomllib, pathlib; \
print('\n'.join(tomllib.loads(pathlib.Path('pyproject.toml').read_text())['project']['dependencies']))" \
    > /tmp/requirements.txt \
    && cat /tmp/requirements.txt

RUN --mount=type=cache,target=/root/.cache/pip,sharing=locked \
    pip install --requirement /tmp/requirements.txt

# Corpora do NLTK. O pipeline padrão usa o stemmer RSLP; `stopwords` entra
# porque as configurações alternativas de pré-processamento dependem dela e o
# custo são poucos MB. Sem isso, a primeira requisição falharia com LookupError
# — e falharia em produção, não aqui.
RUN python -m nltk.downloader -d "$NLTK_DATA" stopwords rslp

COPY ruff.toml ./
COPY src ./src

# Normaliza permissões vindas do checkout. O NTFS não tem bit de execução, então
# o Docker copia todo arquivo de um clone em Windows como 0755 — e o ruff, com a
# regra EXE selecionada neste projeto, acusa EXE002 ("executável sem shebang")
# em cada um dos .py. Seriam 44 erros que não existem no CI em Linux.
#
# "a-x,a+X": tira o bit de execução dos arquivos e o devolve aos diretórios (o X
# maiúsculo só se aplica a diretórios e ao que já era executável).
RUN chmod -R a-x,a+X src

RUN --mount=type=cache,target=/root/.cache/pip,sharing=locked \
    pip install --no-deps .

# -----------------------------------------------------------------------------
# trainer — produz resultados/classificador.joblib
# -----------------------------------------------------------------------------
# O modelo é treinado DENTRO da build, e não copiado do repositório. A diferença
# importa: o artefato da imagem passa a ser reprodutível a partir do dataset
# versionado, e não depende de alguém ter lembrado de rodar o treino e commitar
# o .joblib. São ~400 exemplos e um MultinomialNB — segundos de build.
#
# Este estágio também é o alvo do serviço `trainer` do compose, usado para
# reexecutar experimento/ajuste_fino gravando em ./resultados no host.
FROM builder AS trainer

# Modelo estatístico do spaCy: necessário para lematização e tokenização
# linguística, usadas pelas varreduras de `experimento.py`. Fica fora do runtime
# de propósito — a configuração vencedora usa stemming do NLTK, não o spaCy.
ARG WITH_SPACY_MODEL=1
RUN --mount=type=cache,target=/root/.cache/pip,sharing=locked \
    if [ "$WITH_SPACY_MODEL" = "1" ]; then python -m spacy download pt_core_news_sm; fi

COPY tests ./tests
RUN chmod -R a-x,a+X tests

RUN python -m pln.classificador \
    && test -f /app/resultados/classificador.joblib

CMD ["python", "-m", "pln.classificador"]

# -----------------------------------------------------------------------------
# dev — desenvolvimento com recarga automática
# -----------------------------------------------------------------------------
# Instalação editável: o .pth aponta para /app/src, que o compose sobrepõe com
# bind mount do host. Editar um arquivo no editor reinicia o uvicorn, sem build.
FROM trainer AS dev

RUN --mount=type=cache,target=/root/.cache/pip,sharing=locked \
    pip install --editable ".[dev]"

# O mesmo entrypoint da produção, de propósito. Ele é ainda mais útil aqui: em
# desenvolvimento, /app/resultados vem por bind mount do host e pode chegar
# vazio numa cópia recém-clonada. O aviso na subida transforma isso numa linha
# de log clara, em vez de um 500 na primeira análise de áudio.
COPY docker/api/entrypoint.sh /usr/local/bin/az1-entrypoint
RUN chmod 0755 /usr/local/bin/az1-entrypoint

EXPOSE 8000
ENTRYPOINT ["/usr/local/bin/az1-entrypoint"]
CMD ["uvicorn", "az1_api.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload", \
     "--reload-dir", "/app/src"]

# -----------------------------------------------------------------------------
# runtime — imagem de produção
# -----------------------------------------------------------------------------
FROM base AS runtime

# libgomp1: OpenMP, exigido pelo scikit-learn em tempo de execução. Não vem no
# python:slim e a falta só aparece no import, com a aplicação já subindo.
# Instalado sem `build-essential` — compilador nenhum chega à imagem final.
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt/lists,sharing=locked \
    rm -f /etc/apt/apt.conf.d/docker-clean \
    && apt-get update \
    && apt-get install -y --no-install-recommends libgomp1

# Usuário sem privilégios, com UID alto e fixo. Fixar o UID é o que permite
# casar permissões de volumes montados; `--no-log-init` evita que o adduser
# aloque um arquivo de log esparso gigante para UIDs altos.
RUN groupadd --gid 10001 az1 \
    && useradd --uid 10001 --gid 10001 --no-log-init --create-home --shell /usr/sbin/nologin az1

COPY --from=builder --chown=10001:10001 /app/.venv /app/.venv
COPY --from=builder /opt/nltk_data /opt/nltk_data
COPY --from=trainer --chown=10001:10001 /app/resultados /app/resultados
COPY --chown=10001:10001 pyproject.toml /app/pyproject.toml
COPY docker/api/entrypoint.sh /usr/local/bin/az1-entrypoint

RUN chmod 0755 /usr/local/bin/az1-entrypoint

# Metadados OCI. Não são decoração: `docker inspect` numa imagem em produção
# responde de qual commit ela saiu, que é a primeira pergunta de qualquer
# investigação de incidente.
ARG VERSION=0.1.0
ARG VCS_REF=unknown
ARG BUILD_DATE=unknown
LABEL org.opencontainers.image.title="az1-api" \
      org.opencontainers.image.description="API do AZ1 — recepção de áudio, transcrição, classificação de intenções e chat" \
      org.opencontainers.image.source="https://git.inteli.edu.br/graduacao/2026-2a/t17/g01" \
      org.opencontainers.image.licenses="CC-BY-4.0" \
      org.opencontainers.image.version="${VERSION}" \
      org.opencontainers.image.revision="${VCS_REF}" \
      org.opencontainers.image.created="${BUILD_DATE}"

USER 10001:10001
EXPOSE 8000

# Sonda em Python puro: a imagem não tem curl nem wget, e acrescentar um pacote
# só para o healthcheck aumentaria a superfície da imagem de produção.
# `start-period` cobre a subida do uvicorn; falhas antes dele não contam.
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD ["python", "-c", "import sys, urllib.request; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=4).status == 200 else 1)"]

ENTRYPOINT ["/usr/local/bin/az1-entrypoint"]
CMD ["uvicorn", "az1_api.main:app", "--host", "0.0.0.0", "--port", "8000"]
