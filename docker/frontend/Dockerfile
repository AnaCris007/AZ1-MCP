# syntax=docker/dockerfile:1.7
# =============================================================================
# AZ1 — imagem do frontend (React + Vite, servido por nginx)
# =============================================================================
# O React não roda no servidor: `vite build` produz HTML, CSS e JS estáticos. A
# consequência para o Docker é que Node é dependência de BUILD, não de runtime.
# Publicar a imagem com Node dentro seria embarcar ~400 MB de runtime, um
# gerenciador de pacotes e o node_modules inteiro numa imagem que só precisa
# entregar arquivos por HTTP — e cada um desses pacotes é uma CVE a acompanhar.
#
# Daí os estágios: `build` tem Node e node_modules; `runtime` é nginx + a pasta
# dist. O resultado final fica na casa das dezenas de MB.
#
# O contexto de build é a RAIZ do repositório, não src/frontend: a imagem
# precisa também de docker/frontend/default.conf.template. Por isso os COPY
# abaixo trazem o prefixo src/frontend/.
# =============================================================================

ARG NODE_VERSION=22
ARG NGINX_VERSION=1.27

# -----------------------------------------------------------------------------
# deps — node_modules em camada própria
# -----------------------------------------------------------------------------
FROM node:${NODE_VERSION}-alpine AS deps
WORKDIR /app

# Só os manifestos, antes do código-fonte: enquanto as dependências não mudarem,
# esta camada vem do cache e `npm ci` não roda. Copiar o projeto inteiro aqui
# invalidaria a instalação a cada componente editado.
#
# `npm ci` e não `npm install`: instala exatamente o que está no lockfile e
# falha se package.json e package-lock.json divergirem. `npm install` resolveria
# versões novas silenciosamente, e a imagem deixaria de ser reproduzível.
COPY src/frontend/package.json src/frontend/package-lock.json ./
RUN --mount=type=cache,target=/root/.npm,sharing=locked \
    npm ci --no-audit --no-fund

# -----------------------------------------------------------------------------
# dev — servidor de desenvolvimento do Vite (HMR)
# -----------------------------------------------------------------------------
# Alvo usado pelo docker-compose.override.yml. O código vem por bind mount, não
# por COPY: é o que faz o hot reload funcionar.
FROM deps AS dev
ENV NODE_ENV=development
EXPOSE 5173
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "5173"]

# -----------------------------------------------------------------------------
# build — bundle de produção
# -----------------------------------------------------------------------------
FROM deps AS build

COPY src/frontend/ ./

# Variáveis VITE_* são substituídas em tempo de build e ficam gravadas no
# bundle. Não há como configurá-las depois, no contêiner: o que vai a runtime
# são arquivos estáticos já compilados.
#
# O padrão vazio é deliberado. Com ele o cliente chama /api/... na própria
# origem e quem encaminha para a API é o nginx deste mesmo contêiner. Isso
# elimina CORS do problema — o navegador vê uma origem só — e mantém a API fora
# da internet, acessível apenas pela rede interna do compose.
ARG VITE_API_BASE_URL=""
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}

RUN npm run build && test -f dist/index.html

# -----------------------------------------------------------------------------
# runtime — nginx sem privilégios
# -----------------------------------------------------------------------------
# `nginx-unprivileged` em vez do nginx oficial: o oficial sobe o processo mestre
# como root para poder abrir a porta 80 (<1024 exige CAP_NET_BIND_SERVICE).
# Esta variante escuta em 8080 e roda inteira como UID 101, o que permite
# `cap_drop: ALL` e `no-new-privileges` no compose sem que nada quebre.
FROM nginxinc/nginx-unprivileged:${NGINX_VERSION}-alpine AS runtime

# O template é processado por envsubst no entrypoint da imagem base e vira
# /etc/nginx/conf.d/default.conf na subida. É o que permite trocar o endereço da
# API sem reconstruir a imagem — a mesma imagem serve dev, homologação e prod.
COPY docker/frontend/default.conf.template /etc/nginx/templates/default.conf.template
COPY docker/frontend/security-headers.conf /etc/nginx/security-headers.conf
COPY --from=build /app/dist /usr/share/nginx/html

ENV NGINX_PORT=8080 \
    API_UPSTREAM=http://api:8000

ARG VERSION=0.1.0
ARG VCS_REF=unknown
ARG BUILD_DATE=unknown
LABEL org.opencontainers.image.title="az1-frontend" \
      org.opencontainers.image.description="Interface conversacional do AZ1, servida por nginx" \
      org.opencontainers.image.source="https://git.inteli.edu.br/graduacao/2026-2a/t17/g01" \
      org.opencontainers.image.licenses="CC-BY-4.0" \
      org.opencontainers.image.version="${VERSION}" \
      org.opencontainers.image.revision="${VCS_REF}" \
      org.opencontainers.image.created="${BUILD_DATE}"

USER 101
EXPOSE 8080

# /healthz é servido pelo próprio nginx e não toca a API: o healthcheck responde
# "o servidor de estáticos está de pé", que é o que este contêiner promete.
# Misturar a saúde da API aqui faria o orquestrador reiniciar o frontend por
# causa de um problema que não é dele.
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD ["/bin/sh", "-c", "wget -qO- http://127.0.0.1:${NGINX_PORT}/healthz || exit 1"]
