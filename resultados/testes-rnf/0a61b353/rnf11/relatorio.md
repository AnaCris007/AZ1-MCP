# Execução RNF11 — explicabilidade das sugestões de preenchimento

**Resultado: BLOQUEADO**

- Casos: `CT-RNF11-P` e `CT-RNF11-N`
- Commit: `0a61b353829dee491537bb2863facbe589d48cc8`
- Positivas executadas: 0 de 20
- Negativas executadas: 0 de 10
- Métrica de aprovação: não calculável

## Motivo

O RNF11 mede as sugestões produzidas pelo RF04. O fluxo necessário para gerar
essas sugestões não existe na versão avaliada. O inventário de implementação do
próprio projeto registra o RF04 como **não implementado**, e
`src/services/agente_service.py` encaminha as intenções de orientação para
`SEM_ACAO` porque a leitura e a sugestão de campos ainda não foram construídas.

O contrato HTTP também não representa uma sugestão por campo nem contém uma
justificativa própria: `ChatResponse` expõe apenas `reply` e `fontes`. Portanto,
uma resposta textual eventual do RAG não pode ser contabilizada como execução
do RF04/RNF11.

Na inspeção do PostgreSQL em execução, as tabelas de entrada indispensáveis
também estavam vazias:

- `portfolio.artefato`: 0 registros;
- `portfolio.campo_artefato`: 0 registros.

## Por que não é “Reprovado”

Nenhuma das 30 solicitações planejadas pôde chegar ao objeto que o requisito
mede: uma sugestão de preenchimento associada a um campo. Conforme a taxonomia
do planejamento, ausência de fluxo, instrumento ou massa obrigatória é
**bloqueio de execução**, não falha observada do critério de 85%.

## O que falta para executar

1. Implementar o RF04: localizar artefato e campos pendentes e gerar uma
   sugestão individual por campo, sem alterar a fonte original.
2. Expor para cada sugestão pelo menos: campo, texto sugerido, referência
   recuperável e justificativa curta.
3. Carregar massa sintética de artefatos e campos pendentes/completos.
4. Versionar 20 solicitações positivas e 10 negativas, com fontes sintéticas e
   gabaritos que definam previamente o que sustenta cada sugestão.
5. Coletar os julgamentos independentes de duas pessoas; usar uma terceira
   somente nas divergências.

As solicitações, fontes e gabaritos podem ser sintéticos. Os julgamentos humanos
não devem ser inventados. Depois desses itens, a aprovação exige pelo menos
17/20 positivas válidas e 10/10 negativas com abstenção ou limitação segura.
