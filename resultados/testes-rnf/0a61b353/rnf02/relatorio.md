# Execução RNF02 — autenticação

**Resultado: APROVADO**

- Endpoints protegidos inventariados pelo OpenAPI: 19
- Credenciais válidas aceitas: 19/19
- Condições inválidas bloqueadas com 401 genérico: 95/95
- Tentativas que alcançaram regra de negócio após credencial inválida: 0
- Tokens ou chaves encontrados nos logs: não
- Total de tentativas: 114

## Método

Foi gerado em memória um par ES256 efêmero e tokens sintéticos para as condições
válida, ausente, malformada, expirada, assinatura inválida e audiência incorreta.
Cada operação protegida declarada no OpenAPI recebeu as seis tentativas. Uma
sentinela substituiu cada dependência de negócio: nas negativas, qualquer chamada
à sentinela reprovaria o caso. Nas válidas, erros funcionais posteriores à
autenticação não contam como falha de autenticação, conforme o planejamento.

Nenhum JWT ou chave foi persistido. `tentativas.csv` redige o cabeçalho e
`logs_sanitizados.txt` contém apenas causas operacionais sem credenciais.
