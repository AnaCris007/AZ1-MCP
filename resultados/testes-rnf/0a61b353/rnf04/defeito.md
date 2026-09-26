# Defeito encontrado pelo RNF04

## Resultado observado

Nem todos os canais e desfechos deixam uma trilha recuperável pelo identificador.
Consulte `checklist.csv` e `cenarios_negativos.json` para a enumeração exata.

## Impacto

O requisito de rastreabilidade ponta a ponta não pode ser demonstrado para toda
a massa. Em especial, uma resposta entregue ao usuário pode existir sem o par
correspondente em `auditoria.vw_turno`, e erros controlados podem não registrar
`resultado=falha`/`categoria_erro`.

## Correção esperada

Integrar a persistência de auditoria ao canal de voz e registrar desfechos de
falha antes de devolver o erro controlado, incluindo a categoria do erro e os
metadados aplicáveis do áudio. Depois, repetir a mesma massa versionada.
