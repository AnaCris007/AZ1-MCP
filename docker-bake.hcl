// =============================================================================
// AZ1 — buildx bake
// =============================================================================
// O compose sabe construir imagens, mas constrói uma por vez, para a
// arquitetura da máquina local, com cache que morre com o runner do CI. Isto
// aqui resolve as três coisas:
//
//   docker buildx bake                    # api + frontend, em paralelo
//   docker buildx bake api                # só a API
//   docker buildx bake release            # multiarquitetura (amd64 + arm64)
//   docker buildx bake --push release     # constrói e publica
//   docker buildx bake --print            # mostra o plano, sem construir
//
// Multiarquitetura importa neste projeto porque a equipe desenvolve em Mac M1
// (arm64) e a instância de deploy é x86 (amd64) — ou, se for Graviton, o
// contrário. Sem isso, a imagem construída no notebook simplesmente não roda no
// servidor, e a descoberta acontece no meio do deploy.
//
// Para construir para outra arquitetura é preciso um builder com QEMU:
//   docker buildx create --name az1 --driver docker-container --use
//
// Detalhe que costuma confundir: o bake lê o docker-compose.yml TAMBÉM, e funde
// as duas definições. Por isso `docker buildx bake --print` mostra em cada alvo
// a tag deste arquivo e a do campo `image:` do compose. Não é duplicação
// acidental — é o que mantém os dois arquivos coerentes sem repetir valores.
// =============================================================================

// --- Parâmetros --------------------------------------------------------------
// Sobrescreva no ambiente: TAG=v0.2.0 docker buildx bake

variable "REGISTRY" {
  default = "" // vazio = imagens locais; ex.: "registry.gitlab.com/inteli-t17/g01/"
}

variable "TAG" {
  default = "dev"
}

variable "VERSION" {
  default = "0.1.0"
}

variable "VCS_REF" {
  default = "unknown"
}

variable "BUILD_DATE" {
  default = "unknown"
}

// Login com Microsoft via Supabase Auth (RNF02). Públicas por natureza — vão
// para dentro do bundle do frontend de qualquer jeito — mas sem valor fixo
// como VITE_API_BASE_URL: cada deploy aponta para o seu próprio projeto.
variable "SUPABASE_URL" {
  default = ""
}

variable "SUPABASE_ANON_KEY" {
  default = ""
}

// --- Grupos ------------------------------------------------------------------

group "default" {
  targets = ["api", "frontend"]
}

group "release" {
  targets = ["api-release", "frontend-release"]
}

// --- Alvo comum --------------------------------------------------------------
// Herança evita repetir contexto e argumentos em cada alvo — e evita o bug
// clássico de acrescentar um LABEL em uma imagem e esquecer da outra.

target "_common" {
  context = "."
  args = {
    VERSION    = VERSION
    VCS_REF    = VCS_REF
    BUILD_DATE = BUILD_DATE
  }
  // Cache local entre builds. Em CI, troque por cache de registro:
  //   cache-from = ["type=registry,ref=${REGISTRY}az1/cache"]
  //   cache-to   = ["type=registry,ref=${REGISTRY}az1/cache,mode=max"]
  // "mode=max" guarda também as camadas intermediárias, o que faz diferença
  // real num build multi-estágio como este: sem ele, o cache só cobre a imagem
  // final e o estágio de dependências é refeito a cada pipeline.
  cache-from = ["type=local,src=.docker-cache"]
  cache-to   = ["type=local,dest=.docker-cache,mode=max"]
}

// --- API ---------------------------------------------------------------------

target "api" {
  inherits   = ["_common"]
  dockerfile = "docker/api/Dockerfile"
  target     = "runtime"
  tags = [
    "${REGISTRY}az1/api:${TAG}",
    "${REGISTRY}az1/api:${VERSION}",
  ]
}

target "api-release" {
  inherits  = ["api"]
  platforms = ["linux/amd64", "linux/arm64"]
}

// Imagem de treino/experimentação. Não entra no grupo default: é construída sob
// demanda, porque carrega o modelo do spaCy e as dependências de teste.
target "trainer" {
  inherits   = ["_common"]
  dockerfile = "docker/api/Dockerfile"
  target     = "trainer"
  tags       = ["${REGISTRY}az1/trainer:${TAG}"]
}

// --- Frontend ----------------------------------------------------------------

target "frontend" {
  inherits   = ["_common"]
  dockerfile = "docker/frontend/Dockerfile"
  target     = "runtime"
  args = {
    // Vazio: o bundle chama /api na própria origem e o nginx encaminha.
    VITE_API_BASE_URL = ""
    VITE_SUPABASE_URL       = SUPABASE_URL
    VITE_SUPABASE_ANON_KEY  = SUPABASE_ANON_KEY
  }
  tags = [
    "${REGISTRY}az1/frontend:${TAG}",
    "${REGISTRY}az1/frontend:${VERSION}",
  ]
}

target "frontend-release" {
  inherits  = ["frontend"]
  platforms = ["linux/amd64", "linux/arm64"]
}
