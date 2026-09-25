# =============================================================================
# AZ1 — atalhos de operação
# =============================================================================
# Um Makefile aqui não é para compilar nada: é para que os comandos longos do
# Docker tenham um nome só, igual para todo mundo. A alternativa é cada pessoa
# guardar sua própria linha de compose no histórico do shell — e é assim que
# alguém acaba subindo produção com o override de desenvolvimento junto.
#
#   make help          lista os alvos
#   make up            sobe a pilha de desenvolvimento
#   make prod-up       sobe a pilha de produção
#
# Requer GNU Make. No Windows, use o Git Bash com make instalado, o WSL, ou
# simplesmente copie o comando que cada alvo executa — todos são uma linha só.
# =============================================================================

SHELL := /bin/sh

COMPOSE      := docker compose
COMPOSE_PROD := docker compose -f docker-compose.yml -f docker-compose.prod.yml

# Metadados de build. Ficam gravados como labels OCI na imagem, e é o que
# permite descobrir de qual commit saiu um contêiner em produção.
VERSION    ?= 0.1.0
VCS_REF    := $(shell git rev-parse --short HEAD 2>/dev/null || echo unknown)
BUILD_DATE := $(shell date -u +%Y-%m-%dT%H:%M:%SZ)

export AZ1_VERSION    := $(VERSION)
export AZ1_VCS_REF    := $(VCS_REF)
export AZ1_BUILD_DATE := $(BUILD_DATE)

.DEFAULT_GOAL := help
.PHONY: help build up down restart logs logs-worker logs-rabbit rabbitmq-ui ps sh \
	    drive-abrir restart-worker \
	    test lint train experiment bancada metricas \
	    particionar metricas-teste comparativo \
	    prod-build prod-up prod-down prod-logs bake release clean nuke scan size

help:  ## Lista os alvos disponíveis
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
	| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

# --- Desenvolvimento ---------------------------------------------------------

build:  ## Constrói as imagens de desenvolvimento
	$(COMPOSE) build

up:  ## Sobe a pilha de desenvolvimento (frontend, api, minio, rabbitmq, worker)
	$(COMPOSE) up -d --build
	@echo "frontend  http://localhost:5173"
	@echo "api       http://localhost:8010/docs"
	@echo "minio     http://localhost:9001  (minioadmin / minioadmin)"
	@echo "rabbitmq  http://localhost:15672  (az1 / az1)"

down:  ## Derruba a pilha, preservando os volumes
	$(COMPOSE) down --remove-orphans

restart:  ## Reinicia a API
	$(COMPOSE) restart api

logs:  ## Acompanha os logs de todos os serviços
	$(COMPOSE) logs -f --tail=100

logs-worker:  ## Acompanha os logs do worker de varredura (consumidor)
	$(COMPOSE) logs -f --tail=100 worker

logs-rabbit:  ## Acompanha os logs do RabbitMQ
	$(COMPOSE) logs -f --tail=100 rabbitmq

rabbitmq-ui:  ## Abre o painel de management do RabbitMQ no navegador (az1 / az1)
	@echo "RabbitMQ management: http://localhost:15672  (az1 / az1)"
	@python3 -c "import webbrowser; webbrowser.open('http://localhost:15672')" 2>/dev/null || true

ps:  ## Estado dos contêineres, com a saúde de cada um
	$(COMPOSE) ps

sh:  ## Abre um shell no contêiner da API
	$(COMPOSE) exec api /bin/bash

drive-abrir:  ## Abre o canal do Drive NO HOST e grava .google_token.json (pré-requisito da indexação real)
	@# Roda no HOST, não no contêiner: o fluxo OAuth de "Desktop app" precisa abrir
	@# o navegador para o consentimento e receber o callback numa porta local. O
	@# arquivo .google_token.json gerado aqui é o que o worker monta (aponte
	@# GOOGLE_TOKEN_FILE=./.google_token.json no .env e faça `make restart-worker`
	@# ou `make up`). Abra o canal contra o MESMO banco que o worker lê (ver .env).
	python -m services.drive_channel_service abrir

restart-worker:  ## Reinicia só o worker (após apontar GOOGLE_TOKEN_FILE no .env)
	$(COMPOSE) restart worker

# --- Qualidade ---------------------------------------------------------------

test:  ## Roda a suíte de testes dentro do contêiner
	$(COMPOSE) --profile ci run --rm tests

lint:  ## Roda o ruff no código Python
	$(COMPOSE) --profile ci run --rm --entrypoint ruff tests check src tests

# --- Pipeline de PLN ---------------------------------------------------------

train:  ## Retreina o classificador e grava em ./resultados
	$(COMPOSE) --profile ml run --rm trainer

# REGUA escolhe o instrumento de medida da varredura. Cada família precisa da
# dela: herdar o ranking de outra favorece quem o produziu. Ver Seção 3.3.7.
#   make experiment                      -> multinomialnb (padrão, ~20 min)
#   make experiment REGUA=linearsvc      -> ~15 min
#   make experiment REGUA=logisticregression -> ~2h30
REGUA ?= multinomialnb

experiment:  ## Varre pré-processamento e vetorização (use REGUA=<familia>)
	$(COMPOSE) --profile ml run --rm trainer python -m pln.experimento --regua $(REGUA)

bancada:  ## Mede latência, tempo de treino e pico de memória (RNF01 e RNF10)
	$(COMPOSE) --profile ml run --rm trainer python -m pln.bancada

metricas:  ## Mede F1, cobertura e aceitação indevida, e a curva do limiar (RNF03)
	$(COMPOSE) --profile ml run --rm trainer python -m pln.metricas

particionar:  ## Separa o pool em desenvolvimento e teste retido
	$(COMPOSE) --profile ml run --rm trainer python -m pln.particao

metricas-teste:  ## Mede o RNF03 UMA VEZ no teste retido, com o limiar do desenvolvimento
	$(COMPOSE) --profile ml run --rm trainer python -m pln.metricas --teste

comparativo:  ## Compara 4 famílias, cada uma no melhor texto dela, e confirma no retido
	$(COMPOSE) --profile ml run --rm trainer python -m pln.comparativo_modelos --confirmar-no-retido

# --- Produção ----------------------------------------------------------------

prod-build:  ## Constrói as imagens de produção com os metadados de versão
	$(COMPOSE_PROD) build

prod-up:  ## Sobe a pilha de produção em segundo plano
	$(COMPOSE_PROD) up -d --build

prod-down:  ## Derruba a pilha de produção
	$(COMPOSE_PROD) down --remove-orphans

prod-logs:  ## Acompanha os logs de produção
	$(COMPOSE_PROD) logs -f --tail=100

# --- Build avançado ----------------------------------------------------------

bake:  ## Constrói api e frontend em paralelo, com cache compartilhado
	docker buildx bake --set '*.args.VERSION=$(VERSION)' \
	                   --set '*.args.VCS_REF=$(VCS_REF)' \
	                   --set '*.args.BUILD_DATE=$(BUILD_DATE)'

release:  ## Constrói para amd64 e arm64 (exige um builder com QEMU)
	docker buildx bake release TAG=$(VERSION) VERSION=$(VERSION) VCS_REF=$(VCS_REF)

# --- Diagnóstico e limpeza ---------------------------------------------------

size:  ## Mostra o tamanho das imagens do projeto
	@docker images --filter "reference=az1/*" \
	    --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}"

scan:  ## Procura vulnerabilidades conhecidas nas imagens
	docker scout cves az1/api:$(VERSION) || \
	    echo "docker scout indisponivel: use trivy image az1/api:$(VERSION)"

clean:  ## Remove contêineres e imagens do projeto, preservando os dados
	$(COMPOSE) down --remove-orphans --rmi local

nuke:  ## Remove TAMBÉM os volumes: os áudios do MinIO são perdidos
	$(COMPOSE) down --remove-orphans --rmi local --volumes
