#!/bin/sh
# =============================================================================
# Entrypoint da API — o que precisa acontecer antes do uvicorn existir
# =============================================================================
# Três responsabilidades, nesta ordem:
#   1. Resolver segredos entregues como arquivo (convenção *_FILE).
#   2. Verificar o artefato do modelo antes de aceitar tráfego.
#   3. Ceder o PID 1 ao processo do servidor, com `exec`.
#
# O `exec` da última linha não é estilo. Sem ele, o shell continua como PID 1 e
# o uvicorn vira filho: o SIGTERM do `docker stop` chega ao shell, que o ignora,
# e o contêiner só morre no SIGKILL dez segundos depois — requisições em voo
# cortadas no meio, a cada deploy.
#
# `set -eu`: aborta em erro e em variável não definida. Falhar aqui, na
# inicialização, é barato; falhar na primeira requisição do usuário não é.
# =============================================================================
set -eu

log() { printf '[entrypoint] %s\n' "$*" >&2; }

# --- 1. Segredos como arquivo ------------------------------------------------
# Docker secrets e a maioria dos gerenciadores (Vault, AWS Secrets Manager via
# sidecar, Kubernetes) entregam segredo como arquivo montado, não como variável.
# A variável de ambiente é visível em `docker inspect`, no `/proc/<pid>/environ`
# de qualquer processo do contêiner e nos logs de quem imprime o ambiente.
#
# A convenção abaixo aceita as duas formas: se GEMINI_API_KEY_FILE existir, o
# conteúdo do arquivo vira GEMINI_API_KEY. O código da aplicação continua lendo
# só a variável e não precisa saber de nada disso.
for nome in DEEPGRAM_API_KEY GEMINI_API_KEY AUDIO_STORAGE_ACCESS_KEY AUDIO_STORAGE_SECRET_KEY; do
    eval "arquivo=\${${nome}_FILE:-}"
    [ -n "$arquivo" ] || continue

    if [ ! -r "$arquivo" ]; then
        log "ERRO: ${nome}_FILE aponta para '$arquivo', que não existe ou não é legível."
        exit 1
    fi

    # A substituição de comando já descarta as quebras de linha finais — o que
    # importa aqui, porque todo editor acrescenta uma ao salvar o arquivo do
    # segredo, e uma chave de API com "\n" no fim falha na autenticação com uma
    # mensagem que não diz nada sobre isso.
    valor=$(cat "$arquivo")
    export "$nome=$valor"
    log "segredo $nome carregado de $arquivo"
done
unset nome arquivo valor 2>/dev/null || true

# --- 2. Credencial de exemplo em produção ------------------------------------
# A trava do docker-compose.prod.yml (${VAR:?...}) só dispara com a variável
# AUSENTE. Como AUDIO_STORAGE_SECRET_KEY vem preenchida no .env.example, um
# .env copiado do exemplo passa por ela levando "minioadmin" para o servidor —
# a falha exata que a trava existia para impedir.
#
# Esta verificação fecha esse caminho. Fica atrás de uma variável porque em
# desenvolvimento a credencial de exemplo é justamente o que se quer: só o
# docker-compose.prod.yml liga o modo estrito.
if [ "${AZ1_REFUSE_DEFAULT_CREDENTIALS:-0}" = "1" ]; then
    case "${AUDIO_STORAGE_SECRET_KEY:-}" in
        "" | minioadmin | minio123 | password | changeme)
            log "ERRO: AUDIO_STORAGE_SECRET_KEY está com uma credencial de exemplo."
            log "      Em produção isso deixaria o armazenamento de áudio aberto a"
            log "      qualquer um que conheça o padrão do MinIO."
            log "      Defina um segredo real no .env (mínimo 8 caracteres) e suba de novo."
            exit 1
            ;;
    esac
    log "credenciais de armazenamento: verificadas (não são as de exemplo)"
fi

# --- 3. Artefato do modelo ---------------------------------------------------
# O .joblib é assado na imagem pelo estágio `trainer`. Se um bind mount de
# desenvolvimento sobrepuser /app/resultados com uma pasta vazia do host, o
# arquivo some — e o erro só apareceria no primeiro POST /audio/{id}/analyze,
# como 500 genérico. Avisar aqui transforma isso num erro legível na subida.
MODELO="${AZ1_MODEL_PATH:-/app/resultados/classificador.joblib}"
if [ -f "$MODELO" ]; then
    log "modelo de intenções: $MODELO"
else
    log "AVISO: modelo não encontrado em $MODELO."
    log "       /api/v1/audio/{id}/analyze vai falhar até que exista."
    log "       Gere com: docker compose --profile ml run --rm trainer"
fi

# --- 4. Diagnóstico e entrega do PID 1 ---------------------------------------
log "storage de áudio: ${AUDIO_STORAGE_ENDPOINT_URL:-<não definido>} (bucket ${AUDIO_STORAGE_BUCKET:-az1-audio})"
log "iniciando: $*"

exec "$@"
