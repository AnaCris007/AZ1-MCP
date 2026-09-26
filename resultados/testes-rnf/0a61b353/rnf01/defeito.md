# RNF01-D01 — ausência de timeout controlado abaixo de 60 segundos

## Resultado observado

Nas cinco requisições cuja dependência externa permaneceu ocupada por 65
segundos, a aplicação não devolveu resposta nem erro controlado dentro do teto.
O observador HTTP encerrou cada tentativa após aproximadamente 61 segundos.

## Impacto

Uma dependência lenta pode manter a consulta aberta além do máximo declarado
pelo RNF01. O usuário não recebe um desfecho controlado e recursos do servidor
continuam ocupados até a dependência terminar.

## Correção esperada

Aplicar um timeout total no caminho de geração/consulta externa abaixo de 60
segundos e convertê-lo em erro HTTP controlado. Depois da correção, repetir as
100 tentativas negativas; reduzir apenas o timeout do cliente não corrige o
defeito da aplicação.

