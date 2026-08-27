<p align='center'>
  <a href='https://www.inteli.edu.br/'>
    <img src='../assets/inteli.png' alt='Inteli, Instituto de Tecnologia e Liderança' width='300'>
  </a>
</p>

---

## Projeto: AZ1

## Sumário

<details>
<summary><strong>1. Entendimento de Negócio</strong></summary>

- [1.1 Problema](#11-problema)
- [1.2 Contexto da Indústria do Parceiro](#12-contexto-da-indústria-do-parceiro)
- [1.3 Visão do Produto](#13-visão-do-produto)
- [1.4 Objetivo do Produto](#14-objetivo-do-produto)
- [1.5 Personas e Jornada do Usuário](#15-personas-e-jornada-do-usuário)
- [1.6 Fluxo do Negócio](#16-fluxo-do-negócio)
- [1.7 Brainstorming de Features](#17-brainstorming-de-features)
- [1.8 Canvas do MVP](#18-canvas-do-mvp)
- [1.9 Matriz de Risco do Projeto](#19-matriz-de-risco-do-projeto)

</details>
<details>
<summary><strong>2. Especificação de Requisitos de Software</strong></summary>

- [2.1 Business Drivers](#21-business-drivers)
- [2.2 Requisitos Funcionais](#22-requisitos-funcionais)
- [2.3 Requisitos Não Funcionais](#23-requisitos-não-funcionais)
- [2.4 Visão Inicial da Solução Técnica](#24-visão-inicial-da-solução-técnica)
- [2.5 Tecnologias e Ferramentas](#25-tecnologias-e-ferramentas)
- [2.6 Rastreabilidade Consolidada](#26-rastreabilidade-consolidada)

</details>

<details>
<summary><strong>3. Definição Técnica e Arquitetural da Solução</strong></summary>

- [3.1 Catálogo de Intenções e Contrato de Classificação](#31-catálogo-de-intenções-e-contrato-de-classificação)
- [3.2 API de Speech to Text e Text to Speech](#32-api-de-speech-to-text-e-text-to-speech)
- [3.3 Algoritmo de NLP e Implementação](#33-algoritmo-de-nlp-e-implementação)
- [3.4 API para Recebimento de Áudios](#34-api-para-recebimento-de-áudios)
- [3.5 Pilha de Tecnologias](#35-pilha-de-tecnologias)
- [3.6 Modelagem Conceitual e Lógica dos Dados](#36-modelagem-conceitual-e-lógica-dos-dados)
- [3.7 Processo de Deploy em Nuvem](#37-processo-de-deploy-em-nuvem)
- [3.8 Projeto Técnico e Arquitetural](#38-projeto-técnico-e-arquitetural)
- [3.9 Estratégia de Entrega para as Sprints 3, 4 e 5](#39-estratégia-de-entrega-para-as-sprints-3-4-e-5)

</details>

<details>
<summary><strong>4. Prototipação Exploratória — Design e UX</strong></summary>

- [4.1 Questão de Projeto](#41-questão-de-projeto)
- [4.2 Alternativas Divergentes](#42-alternativas-divergentes)
- [4.3 Formatos de Prototipação](#43-formatos-de-prototipação)
- [4.4 Construção dos Protótipos](#44-construção-dos-protótipos)
- [4.5 Diário de Construção dos Dois Protótipos](#45-diário-de-construção-dos-dois-protótipos)
- [4.6 Execução dos Protótipos](#46-execução-dos-protótipos)
- [4.7 Comparação entre as Alternativas](#47-comparação-entre-as-alternativas)
- [4.8 Limites dos Protótipos](#48-limites-dos-protótipos)
- [4.9 Inventário de Decisões em Aberto](#49-inventário-de-decisões-em-aberto)
- [4.10 Repertório de Situações](#410-repertório-de-situações)
- [4.11 Registros Visuais](#411-registros-visuais)

</details>

</details>

- [5. Registro de Decisões](#5-registro-de-decisões)
- [6. Fontes](#6-fontes)

---

# 1. Entendimento de Negócio

## 1.1 Problema

 O Metrô de São Paulo gerencia empreendimentos de elevada complexidade técnica, financeira e administrativa. Esses projetos podem durar entre oito e dez anos, envolver investimentos bilionários, mais de uma centena de contratos e produzir dezenas de milhares de documentos. Nesse cenário, o PMO Corporativo é responsável pela governança da estratégia, dos portfólios, dos programas e dos projetos da companhia, acompanhando cronogramas, marcos, riscos, problemas, indicadores, benefícios e mudanças.

 Atualmente, o Metrô já possui processos, ferramentas e práticas estabelecidas para a gestão e o armazenamento desses documentos e informações. Portanto, o desafio não está na ausência de uma estrutura de gestão documental, mas na necessidade de tornar a interação com esse grande volume de conteúdo mais simples, ágil e acessível.

 Mesmo com os documentos organizados, a localização de uma informação específica pode exigir que o profissional navegue por diferentes arquivos, listas, relatórios ou sistemas, aplique filtros e analise manualmente os resultados. Além disso, o registro de novas informações e documentos depende do acesso às ferramentas utilizadas e do preenchimento correto dos campos necessários. Essas atividades podem demandar tempo e aumentar a carga operacional das equipes, principalmente diante da quantidade e da complexidade dos projetos administrados.

 Dessa forma, o desafio consiste em oferecer uma maneira mais rápida e intuitiva de consultar e adicionar informações à estrutura de gestão já existente. Por meio de uma interação em linguagem natural, tanto por texto quanto por áudio, o usuário poderá solicitar dados sobre determinado projeto, localizar documentos, verificar riscos, marcos e pendências ou registrar novas informações sem precisar navegar manualmente por diferentes interfaces. As inclusões realizadas com o auxílio do agente, entretanto, deverão passar por validações, respeitar os campos obrigatórios e as permissões de cada usuário, além de manter a rastreabilidade das alterações.

 A dificuldade de acessar e registrar informações com agilidade pode atrasar análises, aumentar o esforço necessário para elaborar relatórios e limitar a capacidade do PMO de identificar riscos, pendências e desvios de maneira preventiva. No setor metroferroviário, em que os empreendimentos envolvem recursos públicos e afetam diretamente a mobilidade da população, a rapidez, a integridade e a confiabilidade dessas informações são fundamentais para apoiar decisões e acompanhar a entrega dos benefícios planejados.

 Portanto, o problema central que o projeto busca resolver é a necessidade de tornar mais ágil, simples e intuitiva a consulta e a adição de informações na estrutura de gestão documental já utilizada pelo Metrô. O objetivo não é substituir os processos, as ferramentas ou os profissionais responsáveis, mas reduzir o esforço manual necessário para localizar, interpretar e registrar informações relacionadas aos empreendimentos.

 Como resposta a esse desafio, o projeto considera o desenvolvimento de um agente de Inteligência Artificial capaz de compreender solicitações em linguagem natural e, por meio de integrações com o ambiente Microsoft homologado do Metrô, consultar ou registrar informações autorizadas. A solução deverá preservar os processos existentes, as regras de negócio, as permissões de acesso, a segurança e a rastreabilidade, funcionando como uma nova camada de interação com o ambiente já administrado pelo Metrô e apoiando, sem substituir, a análise e a tomada de decisão dos profissionais responsáveis.

### Matriz SWOT

 Para aprofundar a compreensão do problema e do contexto em que a solução será inserida, foi elaborada uma Matriz SWOT, ferramenta de análise estratégica que organiza os fatores internos (forças e fraquezas) e externos (oportunidades e ameaças) que influenciam o negócio. A imagem 1 apresenta a matriz elaborada para o Metrô de São Paulo, com foco na atuação do PMO Corporativo e na gestão de informações de seus empreendimentos, e os quadrantes são analisados em detalhe na sequência.

<div align="center">
<sub>Imagem 01 - Matriz SWOT </sub><br>
  <img src="../assets/negócios/swot.png" width="100%" alt="matriz swot"><br>
  <sup>Fonte: Material produzido pelos autores, 2026.</sup>
</div>

 A Matriz SWOT foi elaborada para analisar o contexto interno e externo do Metrô de São Paulo, com foco na atuação do PMO Corporativo e na gestão de informações relacionadas aos seus empreendimentos. As forças e fraquezas representam características internas da organização, enquanto as oportunidades e ameaças correspondem a fatores externos que podem influenciar suas atividades.

 Entre as principais forças do Metrô, destacam-se sua ampla experiência na gestão de empreendimentos de grande porte, a presença de profissionais especializados e a existência de processos consolidados de governança e gestão documental. A organização também conta com um PMO Corporativo estruturado, responsável por apoiar o acompanhamento da estratégia, dos portfólios, dos programas, dos projetos e dos indicadores. Esses elementos favorecem o controle das iniciativas e o alinhamento dos empreendimentos aos objetivos estratégicos da companhia.

 Em relação às fraquezas, a própria dimensão e complexidade das operações representam desafios internos. Os empreendimentos podem envolver longos períodos de execução, investimentos elevados, numerosos contratos e a produção de milhares de documentos. Embora o Metrô já possua ferramentas e processos para administrar essas informações, o grande volume de conteúdo pode tornar a localização, a consulta e a consolidação dos dados mais demoradas, aumentando o esforço operacional, a dependência de ações manuais de consolidação e verificação da qualidade das informações e o risco de inconsistências nos dados, o que dificulta a obtenção rápida de uma visão integrada dos projetos.

 No ambiente externo, a evolução contínua da Inteligência Artificial, do Processamento de Linguagem Natural e das tecnologias de integração de dados representa uma oportunidade relevante para o Metrô. A organização já possui iniciativas relacionadas à IA, incluindo o uso de agentes, o que demonstra abertura institucional e experiência inicial com essas tecnologias. A oportunidade, portanto, não está simplesmente em iniciar sua adoção, mas em ampliar e especializar suas aplicações de acordo com as necessidades do PMO Corporativo. Nesse contexto, essas tecnologias podem ser utilizadas para tornar a consulta às informações mais intuitiva, apoiar a identificação de prazos e pendências, comparar dados dos empreendimentos e propor conteúdos para campos que deverão ser avaliados pelos profissionais responsáveis. Essa evolução pode reduzir o esforço operacional e fortalecer a capacidade de acompanhamento e análise dos projetos, desde que seja integrada aos processos, às permissões e às regras de segurança já estabelecidos pelo Metrô.

 Entretanto, o Metrô também está exposto a ameaças externas que podem afetar a continuidade e os resultados de seus empreendimentos. Entre elas estão restrições orçamentárias, mudanças regulatórias, dependência de fornecedores, riscos relacionados à segurança da informação, atrasos em grandes obras e possíveis mudanças ou substituições na plataforma de gestão de portfólio, o que exige que novas soluções sejam flexíveis e desacopladas das ferramentas atuais. Por prestar um serviço público essencial e administrar empreendimentos financiados com recursos públicos, eventuais falhas, atrasos ou problemas de segurança podem produzir impactos financeiros, institucionais e sociais relevantes.

 A análise demonstra que o Metrô possui uma base organizacional sólida para aproveitar as oportunidades proporcionadas pela transformação digital. Sua experiência, seus profissionais especializados, seus processos consolidados e seu PMO estruturado oferecem condições favoráveis para a incorporação gradual de novas tecnologias. Ao mesmo tempo, qualquer iniciativa deve considerar a complexidade interna da organização e as ameaças existentes no ambiente externo.

Nesse contexto, o projeto pode aproveitar as forças já existentes no Metrô para facilitar o acesso e o registro de informações, sem substituir os processos e mecanismos atuais de gestão. A implementação de uma nova camada de interação deve ocorrer de forma segura, integrada e alinhada às regras da organização, contribuindo para reduzir o esforço operacional e melhorar o apoio à tomada de decisão.

---

## 1.2 Contexto da Indústria do Parceiro

### Visão geral do setor

 O setor metroferroviário compreende o transporte público de passageiros sobre trilhos em ambientes urbanos e metropolitanos — metrôs, trens metropolitanos, monotrilhos e veículos leves sobre trilhos (VLTs). É um modal estruturante da mobilidade urbana, marcado pela alta capacidade, pela previsibilidade e pelo menor impacto ambiental por passageiro transportado. No Brasil, segundo o Balanço do Setor Metroferroviário 2024 da ANPTrilhos, a malha soma cerca de 1.137,5 km e transportou 2,57 bilhões de passageiros em 2024 (média de aproximadamente 8,6 milhões por dia), distribuídos por cerca de 49 linhas em 21 sistemas de 73 municípios — um crescimento de 3,6% em relação a 2023.

 Além do papel na mobilidade, o setor gera benefícios econômicos e ambientais expressivos: a ANPTrilhos estima, para 2024, uma economia de R$ 11,7 bilhões com a redução de congestionamentos e a emissão evitada de 2,4 milhões de toneladas de poluentes. Trata-se de uma indústria intensiva em capital, sustentada por obras de infraestrutura de longo prazo — empreendimentos plurianuais e bilionários —, que exigem forte governança de projetos e articulação entre o poder público, os operadores e a iniciativa privada.

### Tendências e desafios

 Entre as principais tendências, destaca-se a ampliação da participação privada por meio de concessões e parcerias público-privadas (PPPs) — das 16 empresas operadoras do país, 9 já são privadas —, modelo apontado pela ANPTrilhos como instrumento essencial para viabilizar a expansão da malha, a exemplo da concessão do Trem Intercidades São Paulo–Campinas, firmada em 2024. Somam-se a isso a modernização tecnológica, com sistemas de sinalização CBTC e operação automatizada (sem condutor), a adoção de monotrilhos e VLTs e a digitalização da experiência do usuário, com bilhetagem eletrônica e pagamento por aproximação e QR Code.

 Do lado dos desafios, a própria ANPTrilhos aponta a necessidade de mais incentivos regulatórios e de maior priorização de investimentos para sustentar a expansão e a modernização do setor. A esses fatores somam-se o financiamento de obras de grande porte com recursos públicos, a recuperação da demanda após a pandemia (ainda pressionada pelo teletrabalho), a complexidade de coordenar múltiplos operadores em uma mesma rede, o envelhecimento de ativos nas linhas mais antigas e a gestão de empreendimentos longos — com milhares de contratos e documentos —, que demanda controle rigoroso de prazos, custos e riscos.

### Posicionamento do parceiro no mercado

 A Companhia do Metropolitano de São Paulo (Metrô/SP), fundada em 1968, é uma sociedade de economia mista controlada pelo Governo do Estado de São Paulo e vinculada à Secretaria dos Transportes Metropolitanos. Seu papel vai além da operação: a companhia é responsável pelo planejamento, projeto, construção e operação do sistema metroviário da Região Metropolitana de São Paulo, atuando como principal articuladora da expansão da rede sobre trilhos da capital.

 Em termos de participação, o Metrô opera diretamente as Linhas 1-Azul, 2-Verde, 3-Vermelha e 15-Prata (além da 17-Ouro), que juntas transportaram mais de 821 milhões de passageiros em 2025, dentro de um sistema metroviário de cerca de 116 km e mais de 100 estações. Historicamente a espinha dorsal do transporte de alta capacidade da cidade, o Metrô hoje divide a operação da rede com concessionárias privadas — como a Linha 4-Amarela (primeira PPP metroviária do país, operada pela ViaQuatro) e as Linhas 5-Lilás, 8 e 9 (ViaMobilidade) —, mantendo, porém, o papel central de planejador e executor dos grandes empreendimentos de expansão do sistema.

---

## 1.3 Visão do Produto

### Descrição geral

 O produto consiste em um agente inteligente de apoio à gestão do portfólio de projetos, desenvolvido para auxiliar os profissionais do Metrô de São Paulo no acompanhamento dos empreendimentos administrados pelo PMO Corporativo. Sua finalidade é facilitar a consulta, a interpretação e o acompanhamento das informações dos projetos, proporcionando uma interação mais simples e intuitiva por meio de linguagem natural.
 No MVP, o agente utilizará um pipeline de Processamento de Linguagem Natural desenvolvido e avaliado pela equipe. Esse pipeline será responsável por interpretar as solicitações dos usuários, identificar suas intenções e classificá-las de acordo com os tipos de interação definidos, como consultas, transações ou alertas. As intenções serão controladas por um catálogo aceitável de interações sobre os projetos da empresa: solicitações genéricas ou sem relação com o contexto do portfólio deverão ser detectadas, e o usuário será orientado sobre as interações possíveis, evitando respostas fora do escopo do agente.
  Por meio de uma interface conversacional, o profissional poderá fazer perguntas relacionadas aos projetos, incluindo dúvidas sobre documentos, prazos, marcos, riscos, pendências, avanço e situação dos empreendimentos, além de dúvidas sobre conceitos e normativos relativos à gestão de portfólio, programas e projetos. O agente consultará as fontes integradas e apresentará respostas estruturadas com base nas informações disponíveis. Também poderá comparar projetos, apoiar análises relacionadas ao acompanhamento do portfólio e à aderência aos normativos aplicáveis e gerar prévias de relatórios de status e de apresentações para a diretoria a partir dos dados disponíveis.
 A interação com o agente ocorrerá primariamente por linguagem natural escrita, e a solicitação por voz também integra o escopo do produto: por meio da conversão de áudio em texto, as mensagens faladas serão encaminhadas ao mesmo pipeline de PLN, permitindo que o profissional interaja com o agente da forma que lhe for mais conveniente.
  Além de responder às solicitações, o agente poderá oferecer apoio proativo aos profissionais. A partir dos dados disponíveis, poderá identificar e comunicar situações que mereçam atenção, como a proximidade ou o vencimento de prazos, a ausência de documentos esperados, a existência de campos incompletos e outras pendências relacionadas aos projetos. Esses alertas terão caráter informativo e servirão como apoio ao acompanhamento realizado pelo PMO.
  O agente também poderá apoiar a entrada de dados. Ao identificar uma solicitação de transação, como o registro de uma nova informação ou a criação de um projeto, o agente analisará os dados disponíveis e apresentará, na própria conversa, uma sugestão estruturada de preenchimento dos campos correspondentes. No MVP, entretanto, essas propostas terão caráter exclusivamente sugestivo: o agente não preencherá, alterará ou salvará informações em nenhuma base, cabendo ao profissional avaliar a sugestão e, se desejar, efetuar o registro por meio das ferramentas oficiais. Dessa forma, a categoria de transação é contemplada na identificação de intenções e no apoio ao preenchimento, preservando integralmente a responsabilidade humana sobre as informações registradas.
  Para desenvolver e validar o MVP de maneira segura, serão utilizados dados sintéticos que representem situações e informações do contexto do PMO. Portanto, o produto não será integrado ao portfólio real do Metrô nesta etapa, não utilizará dados corporativos sensíveis e não será implantado em ambiente de produção. A integração com os sistemas reais poderá ser considerada como uma evolução posterior do projeto.
 A solução deverá considerar o ecossistema tecnológico da Microsoft, especialmente ferramentas como o Microsoft Copilot Studio e a Power Platform, que atuarão como camada de orquestração e integração do agente, assegurando aderência ao ambiente homologado pelo Metrô e a possibilidade de sustentação e evolução da solução pela própria equipe interna.
 O produto funcionará como uma camada inteligente de consulta, orientação e apoio ao acompanhamento dos projetos. Ele não substituirá os sistemas corporativos, os processos de governança nem a avaliação dos profissionais do Metrô. Seu papel será auxiliar o profissional a encontrar, compreender e analisar informações, preservando as regras de acesso, a confidencialidade e a rastreabilidade das interações.

### O que o produto FAZ (escopo)

| #   | Funcionalidade                             | Descrição                                                                                                                                                                                       |
| --- | ------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | Interação em linguagem natural por texto   | Recebe solicitações escritas em linguagem natural por meio de uma interface conversacional.                                                                                                     |
| 2   | Interação por voz                          | Aceita solicitações faladas, convertendo o áudio em texto e encaminhando-o ao mesmo pipeline de processamento.                                                                                  |
| 3   | Interpretação e classificação de intenções | Interpreta as solicitações por meio de um pipeline de PLN desenvolvido pela equipe, identifica a intenção do usuário e a classifica como consulta, transação ou alerta.                         |
| 4   | Controle do catálogo de intenções          | Detecta solicitações genéricas ou fora do contexto do portfólio e orienta o usuário sobre o catálogo de interações aceitáveis, recusando interações fora de escopo.                             |
| 5   | Consulta a informações dos projetos        | Responde a dúvidas sobre documentos, prazos, marcos, riscos, pendências, avanço e situação dos projetos, utilizando dados sintéticos.                                                           |
| 6   | Esclarecimento de conceitos e normativos   | Responde a dúvidas sobre conceitos e normativos relativos à gestão de portfólio, programas e projetos.                                                                                          |
| 7   | Apoio à análise dos projetos              | Apresenta dados estruturados de um projeto para apoiar a análise humana de status, prazos, riscos e aderência a normativos.                                                                      |
| 8   | Estruturação de respostas                 | Organiza a resposta e suas referências em formato que possa subsidiar relatórios produzidos pelos profissionais; a geração de prévias completas permanece como evolução futura.                 |
| 9   | Respostas estruturadas com referências     | Apresenta respostas claras e estruturadas, indicando as fontes ou referências utilizadas quando disponíveis, e informa quando não existem dados suficientes para uma resposta confiável.        |
| 10  | Alertas e apoio proativo                   | Alerta sobre prazos próximos ou vencidos, sinaliza documentos esperados ausentes, identifica campos incompletos e demais pendências, e oferece ajuda proativa conforme o contexto identificado. |
| 11  | Sugestões de preenchimento                 | Identifica solicitações de transação e apresenta, no chat, sugestões estruturadas de preenchimento de campos e registros, permitindo que o profissional as avalie antes de qualquer registro.   |
| 12  | Segurança e governança das interações      | Respeita as permissões de cada perfil, a confidencialidade das informações e a rastreabilidade das interações.                                                                                  |

### O que o produto NÃO FAZ (fora de escopo)

| #   | Item fora do escopo                                                                                                        | Justificativa                                                                                                                                                                  |
| --- | -------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| 1   | Utilizar dados reais ou sensíveis do Metrô                                                                                 | Restrição de confidencialidade do parceiro: nenhum dado sensível pode ser processado fora de ambientes homologados; o MVP é validado exclusivamente sobre dados sintéticos.    |
| 2   | Integrar-se ao portfólio real ou ser implantado em produção                                                                | O TAPI delimita a integração com o portfólio real como evolução posterior ("Ir Além"); o MVP é uma prova de conceito em ambiente controlado.                                   |
| 3   | Preencher, alterar, salvar ou excluir informações automaticamente em qualquer base ou sistema                              | Decisão de projeto para preservar a responsabilidade humana: as transações geram apenas sugestões no chat, e o registro é efetuado pelo profissional nas ferramentas oficiais. |
| 4   | Executar automaticamente as sugestões apresentadas                                                                         | O profissional deve avaliar e decidir sobre cada sugestão, mantendo-se como responsável final pelas informações registradas.                                                   |
| 5   | Tomar decisões técnicas, administrativas ou estratégicas, ou aprovar documentos, riscos, prazos e ações de governança      | O agente tem caráter de apoio: decisões e aprovações permanecem sob responsabilidade dos profissionais e dos processos de governança do Metrô.                                 |
| 6   | Substituir os sistemas, processos ou profissionais do Metrô                                                                | O produto é uma camada adicional de interação sobre a estrutura existente, e não um substituto dela.                                                                           |
| 7   | Permitir acesso a informações incompatíveis com as permissões do usuário                                                   | Exigência de confidencialidade e controle de acesso por perfil definida pelo parceiro.                                                                                         |
| 8   | Responder a solicitações fora do catálogo de intenções                                                                     | O TAPI determina que interações genéricas ou sem contexto sejam detectadas, orientadas e descartadas.                                                                          |
| 9   | Garantir respostas conclusivas com dados ausentes, incompletos ou desatualizados, ou prever com certeza resultados futuros | Limitação inerente à natureza da solução: as respostas dependem da qualidade dos dados disponíveis, e o agente sinaliza incertezas em vez de ocultá-las.                       |
| 10  | Contemplar todos os documentos, processos e possibilidades do ambiente corporativo                                         | Delimitação necessária de escopo para um MVP acadêmico com prazo definido; a cobertura completa é evolução futura.                                                             |

#### Delimitação do MVP

  O MVP será destinado à validação do pipeline de PLN e das principais formas de interação do agente em um ambiente controlado, utilizando dados sintéticos. O foco estará na capacidade de compreender solicitações por texto e por voz, responder a consultas, apoiar comparações, emitir alertas e sugerir o preenchimento de campos, sempre mantendo o profissional como responsável pela avaliação, pelo registro das informações e pela decisão final.
 Em síntese: no MVP, o agente consulta, interpreta, compara, responde, alerta e sugere preenchimentos utilizando dados sintéticos. O profissional analisa, registra e decide. A integração com o portfólio real, o preenchimento automático de qualquer base, o uso de dados sensíveis e a implantação em produção ficam fora do escopo.

## 1.4 Objetivo do Produto

 O objetivo geral do produto é reduzir o esforço manual necessário para consultar, interpretar e registrar informações dos projetos administrados pelo PMO Corporativo do Metrô de São Paulo, por meio de um agente de Inteligência Artificial capaz de compreender solicitações em linguagem natural, escrita e por voz, e de responder com informações estruturadas, alertas e sugestões de preenchimento, preservando os processos, as permissões e a rastreabilidade já estabelecidos pela companhia.

 Esse objetivo foi formulado a partir da conclusão central da análise do problema: o desafio do Metrô não está na ausência de uma estrutura de gestão, mas no custo operacional de interagir com ela. Por essa razão, o objetivo não propõe a substituição de sistemas, processos ou profissionais, e sim a redução do atrito entre o profissional e a informação, atuando exatamente sobre os pontos em que a análise identificou esforço manual: a localização de informações dispersas em diferentes arquivos, listas e sistemas, a consolidação de análises e o registro de novos dados. O objetivo geral desdobra-se nas seguintes metas específicas, alinhadas ao problema identificado e às necessidades do negócio:

- **Agilizar o acesso à informação:** permitir que o profissional obtenha dados sobre documentos, prazos, marcos, riscos, pendências e avanço dos projetos por meio de uma única interface conversacional. O atendimento será verificado pelo RNF01: pelo menos 80% das consultas textuais deverão produzir resposta em até 15 segundos;
- **Compreender corretamente as solicitações dos usuários:** desenvolver e avaliar um pipeline de Processamento de Linguagem Natural capaz de identificar as intenções dos usuários e classificá-las como consultas, transações sugestivas ou alertas. O atendimento será verificado pelo RNF03, que estabelece precisão mínima de 85% na classificação das intenções;
- **Apoiar a análise dos projetos:** oferecer respostas estruturadas sobre os projetos do portfólio, com fonte e data da informação. O atendimento será verificado pelos critérios de aceitação dos RF02 e RF03 e pelo RNF08, segundo o qual pelo menos 80% dos participantes dos testes deverão compreender a resposta sem auxílio externo;
- **Fortalecer o acompanhamento preventivo do portfólio:** identificar e comunicar proativamente prazos próximos ou vencidos, documentos ausentes, campos incompletos e demais pendências. O atendimento será verificado pelos critérios de aceitação do RF05 e pelo conjunto de casos de teste de alertas definido na seção 2.1;
- **Apoiar a qualidade da entrada de dados:** apresentar sugestões estruturadas para campos pendentes, sem alterar a fonte original. O atendimento será verificado pelos critérios de aceitação do RF04 e pelo RNF11, que exige referências válidas e justificativa compreensível em pelo menos 85% das sugestões;
- **Garantir conformidade com as restrições do parceiro:** validar a solução exclusivamente com dados sintéticos e simular permissões de acesso por perfil. O atendimento será verificado pelo RNF02 e pela presença de todos os elementos de auditoria definidos no RNF04;
- **Assegurar aderência e sustentabilidade tecnológica:** manter o núcleo do agente desacoplado das aplicações clientes e exposto por interfaces padronizadas. O atendimento será verificado pelo RNF05, mediante o consumo das funcionalidades principais por pelo menos duas aplicações clientes sem duplicação das regras de negócio.

 Para evidenciar o alinhamento entre as metas, o problema identificado e as necessidades do negócio, a tabela a seguir apresenta a rastreabilidade de cada meta em relação ao aspecto do problema que a origina e ao benefício esperado pelo parceiro que ela atende, conforme registrado no TAPI:

<div align="center">
<sub>Tabela 1.4 — Rastreabilidade entre metas, problema e benefícios esperados pelo parceiro</sub>
</div>

| Meta                                               | Origem no problema                                                             | Benefício esperado pelo parceiro                                           |
| -------------------------------------------------- | ------------------------------------------------------------------------------ | -------------------------------------------------------------------------- |
| Agilizar o acesso à informação                     | Navegação manual por diferentes arquivos, listas, relatórios e sistemas        | Eficiência; Transparência                                                  |
| Compreender as solicitações dos usuários           | Viabilizador técnico da interação em linguagem natural (núcleo do MVP)         | Precisão                                                                   |
| Apoiar a análise dos projetos                      | Consolidação manual de documentos e análises                                   | Capacidade analítica e suporte à decisão; Relatórios automatizados         |
| Fortalecer o acompanhamento preventivo             | Limitação da capacidade do PMO de identificar riscos e desvios preventivamente | Proatividade                                                               |
| Apoiar a qualidade da entrada de dados             | Registro de informações trabalhoso e suscetível a erros e inconsistências      | Precisão                                                                   |
| Garantir conformidade com as restrições            | Exigências de confidencialidade, permissões por perfil e rastreabilidade       | Confidencialidade; Rastreabilidade                                         |
| Assegurar aderência e sustentabilidade tecnológica | Premissa de possível troca da plataforma de portfólio                          | Interoperabilidade e integração; Sustentação e autonomia da equipe interna |

<div align="center">
<sup>Fonte: Material produzido pelos autores, 2026.</sup>
</div>

 Em conjunto, essas metas respondem diretamente ao problema central identificado: tornar mais ágil, simples e intuitiva a interação com a estrutura de gestão de portfólio já existente. Ao permitir que a informação seja consultada, analisada e sugerida por meio de linguagem natural, o produto atua sobre o esforço manual que hoje consome o tempo das equipes, gerando eficiência, precisão e apoio à tomada de decisão, ao mesmo tempo em que preserva as permissões, a confidencialidade e a rastreabilidade exigidas pela companhia. Alcançar esse objetivo significa, portanto, entregar ao PMO Corporativo não um substituto de seus sistemas, processos ou profissionais, mas uma camada de interação que amplia a capacidade da estrutura já existente, liberando as equipes para as atividades analíticas e estratégicas que efetivamente dependem do julgamento humano.

## 1.5 Personas e Jornada do Usuário

### Persona 1: Robson Oliveira — Diretor

<div align="center">
<sub>Imagem 1.5 - Persona 1: Robson Oliveira — Diretor</sub><br>
  <img src="../assets/design/Persona-diretor.png" width="100%" alt="Persona 1: Robson Oliveira — Diretor"><br>
  <sup>Fonte: Material produzido pelos autores, 2026.</sup>
</div>

### Caracterização

Robson Oliveira é diretor e acompanha projetos estratégicos do Metrô, tendo como uma de suas principais responsabilidades tomar decisões relacionadas ao andamento e aos resultados das iniciativas sob sua gestão. Para isso, precisa ter uma visão ampla dos projetos, acompanhando informações como status, indicadores, riscos, prazos e marcos.

Sua rotina envolve lidar com informações provenientes de diferentes projetos, documentos e sistemas. Nesse contexto, o acesso rápido e confiável aos dados é importante para que consiga compreender a situação dos projetos e identificar possíveis impactos para a organização.

### Dores

Uma das principais dificuldades de Robson é encontrar informações distribuídas entre diferentes documentos e sistemas. A necessidade de consultar diferentes fontes pode tornar a busca por informações atualizadas mais demorada, principalmente quando é necessário obter uma visão geral do portfólio.

Outra dificuldade está na comparação entre projetos. Sem uma forma centralizada de consultar e relacionar as informações, pode ser mais difícil identificar semelhanças, diferenças, riscos e situações que mereçam atenção.

### Interesses no Sistema

Robson tem interesse em consultar rapidamente o status e os indicadores dos projetos, obtendo uma visão geral do andamento das iniciativas. Também busca acompanhar riscos, prazos e marcos, de forma a identificar possíveis impactos para a organização com antecedência.

Além disso, tem interesse em comparar diferentes projetos do portfólio, utilizando essas informações como apoio para suas decisões estratégicas. Por ocupar uma posição de nível executivo, seu foco está menos nos detalhes operacionais de cada projeto e mais em uma visão consolidada e confiável que oriente suas decisões.

### Expectativas em relação à solução

Robson espera conseguir consultar as informações dos projetos de maneira simples e rápida, sem precisar realizar buscas manuais em diferentes documentos e sistemas. Também espera que as informações apresentadas sejam organizadas e contextualizadas de acordo com o projeto consultado.

A possibilidade de realizar consultas utilizando linguagem natural, por texto ou voz, facilita a interação com a solução e permite que o usuário formule perguntas de acordo com a necessidade do momento.

### Relação da persona com o produto

A persona de Robson representa o **Diretor**, que utiliza o agente para obter uma visão estratégica e consolidada do portfólio de projetos. Seu papel é acompanhar o desempenho geral das iniciativas, identificar riscos, avanços e possíveis impactos para a organização, utilizando essas informações como apoio à tomada de decisões. O Diretor utiliza a solução principalmente para **obter uma visão estratégica do conjunto de projetos e apoiar decisões de nível executivo**.

### Jornada do Usuário 1.5.1 — [Robson Oliveira - Diretor]

<div align="center">
<sub>Imagem 1.5.1 - Jornada do Usuário — Robson Oliveira - Diretor</sub><br>
  <img src="../assets/design/Jornada-diretor.png" width="100%" alt="Jornada do Usuário — Robson Oliveira, Diretor"><br>
  <sup>Fonte: Material produzido pelos autores, 2026.</sup>
</div>

### Cenário

Robson precisa acompanhar o andamento de projetos estratégicos do Metrô, mas as informações estão espalhadas entre diferentes documentos e sistemas, dificultando uma visão rápida e confiável para suas decisões.

### Necessidade

A jornada de Robson começa com a identificação da necessidade de se atualizar sobre um ou mais projetos, geralmente motivada por reuniões de diretoria, cobranças de stakeholders ou pela própria rotina de acompanhamento. Nesse momento, sua principal dificuldade é lidar com informações espalhadas entre documentos e sistemas, o que representa uma oportunidade para a solução centralizar essas informações em um único ponto de consulta.

### Consulta

Em seguida, Robson formula uma pergunta em linguagem natural, por texto ou voz, sobre o projeto de seu interesse. Nessa etapa, a principal dor está na demora para acessar informações atualizadas dos projetos, o que a solução busca resolver ao permitir consultas rápidas e diretas por meio do agente.

### Análise

Com a resposta em mãos, Robson avalia as informações recebidas, como status, riscos e prazos dos projetos. Nessa etapa, sua principal necessidade é compreender as informações de forma clara e organizada, facilitando a identificação de pontos que possam exigir sua atenção ou influenciar suas decisões.

### Comparação

Quando necessário, Robson compara diferentes projetos do portfólio para identificar riscos e prioridades. Essa etapa representa o ponto de maior satisfação na jornada, já que a possibilidade de comparação direta entre projetos supera uma das principais dores relatadas por Robson: a dificuldade em comparar projetos e visualizar o portfólio como um todo.

### Decisão

Por fim, com base nos dados consolidados, Robson toma sua decisão estratégica, geralmente no contexto de uma reunião de diretoria ou na definição de próximos passos. Ao contar com dados confiáveis e atualizados, a insegurança de decidir com base em informações incompletas é reduzida, tornando o processo mais ágil e permitindo que Robson utilize o agente como apoio, mantendo a decisão sob sua responsabilidade.

### Experiência do cliente ao longo da jornada

A experiência de Robson evolui de forma crescente ao longo da jornada: parte de um sentimento mais neutro/insatisfeito nas etapas iniciais, quando ainda lida com a dispersão das informações, e cresce progressivamente até atingir o pico de satisfação nas etapas de Comparação e Decisão, momento em que consegue consolidar as informações e tomar decisões estratégicas com mais confiança e agilidade.

---

### Persona 2: Maria Eduarda Santos — Analista de PMO

<div align="center">
<sub>Imagem 1.5.2 - Persona 2: Maria Eduarda Santos — Analista de PMO</sub><br>
  <img src="../assets/design/Persona-pmo.png" width="100%" alt="Persona 2: Maria Eduarda Santos — Analista de PMO"><br>
  <sup>Fonte: Material produzido pelos autores, 2026.</sup>
</div>

### Caracterização

Maria Eduarda Santos é analista do PMO Corporativo do Metrô e atua diretamente na gestão do portfólio de projetos, sendo responsável por manter os dados atualizados, cobrar os responsáveis por pendências de preenchimento e consolidar informações para relatórios e apresentações destinadas à diretoria. Diferentemente de uma visão puramente estratégica, seu trabalho está concentrado na operação diária da governança do portfólio, servindo como elo entre os líderes de projeto e os níveis mais altos da organização.

Sua rotina envolve acompanhar o cumprimento dos prazos mensais de atualização de status, verificar a qualidade dos dados registrados pelas equipes de projeto e apoiar a elaboração de relatórios consolidados. Nesse contexto, ter acesso rápido a informações atualizadas e confiáveis é essencial para que consiga cumprir suas próprias entregas sem depender inteiramente da boa vontade e da disponibilidade dos responsáveis por cada projeto.

### Dores

Uma das principais dificuldades de Maria Eduarda é a necessidade de cobrar manualmente, um a um, os responsáveis por atualizações pendentes, especialmente próximo ao prazo mensal de registro de status. Essa cobrança repetitiva consome tempo que poderia ser dedicado a atividades de maior valor analítico.

Outra dificuldade está na consolidação de dados espalhados entre diferentes sistemas e documentos, como listas do SharePoint, planilhas de Excel e arquivos de Word, processo necessário para a elaboração de relatórios de status e apresentações mensais. A ausência de um mecanismo proativo que sinalize riscos, marcos e pendências antes que se tornem problemas também obriga Maria Eduarda a atuar de forma reativa, identificando falhas apenas quando já se tornaram visíveis.

### Interesses no Sistema

Maria Eduarda tem interesse em consultar e comparar projetos do portfólio sem precisar navegar manualmente pelas listas do SharePoint, obtendo respostas rápidas e organizadas conforme sua necessidade do momento.

Além disso, busca receber alertas proativos sobre marcos, riscos e pendências de preenchimento, de modo a agir antes do prazo, em vez de depender inteiramente da própria iniciativa para lembrar cada responsável. Também tem interesse em contar com apoio na elaboração de relatórios de status e de apresentações mensais para a diretoria, a partir de templates já utilizados pela equipe, e em receber sugestões de conteúdo para campos pendentes, mantendo o controle final sobre o que é efetivamente registrado.

### Expectativas em relação à solução

Maria Eduarda espera que a solução reduza o esforço manual envolvido na cobrança de atualizações e na consolidação de dados, permitindo que ela dedique mais tempo à análise da qualidade das informações e menos à busca e à repetição de tarefas operacionais.

A possibilidade de interagir por linguagem natural, por texto ou voz, aliada a alertas proativos e sugestões de preenchimento, é vista como um fator que aumenta sua produtividade e reduz o risco de pendências passarem despercebidas até próximo do prazo.

### Relação da persona com o produto

A persona de Maria Eduarda representa o **Analista de PMO**, responsável pela operação diária da governança do portfólio. Ela utiliza o agente tanto para **consultar e comparar o andamento dos projetos** quanto para **cobrar, apoiar o preenchimento e consolidar informações** que alimentam os relatórios e as apresentações destinadas à diretoria. O Analista de PMO utiliza a solução principalmente para **reduzir o esforço manual de acompanhamento e cobrança, ganhando tempo para atividades de maior valor analítico dentro do portfólio**.

### Jornada do Usuário 1.5.2 — Maria Eduarda Santos - Analista de PMO

<div align="center">
<sub>Imagem 1.5.2.1 - Jornada do Usuário — Maria Eduarda Santos - Analista de PMO</sub><br>
  <img src="../assets/design/Jornada-pmo.png" width="100%" alt="Jornada do Usuário — Maria Eduarda Santos, Analista de PMO"><br>
  <sup>Fonte: Material produzido pelos autores, 2026.</sup>
</div>

### Cenário

Maria Eduarda precisa manter os dados dos projetos atualizados e cobrar os responsáveis antes dos prazos mensais, mas hoje isso depende de acompanhamento manual e de navegação por diferentes sistemas e documentos, consumindo tempo que faltaria à análise e à consolidação das informações.

### Identificação

A jornada de Maria Eduarda começa com a identificação de quais projetos estão com pendência de atualização, geralmente próximo ao prazo mensal de registro de status, fixado até o dia 10 de cada mês. Nessa etapa, sua principal dificuldade está na falta de alertas automáticos que sinalizem pendências antes do prazo, o que representa uma oportunidade para a solução notificar proativamente Maria Eduarda sobre o que precisa ser atualizado.

### Cobrança

Em seguida, Maria Eduarda cobra manualmente cada responsável pelo preenchimento das informações pendentes, geralmente por e-mail ou mensagem. Nessa etapa, a principal dor está na cobrança repetitiva, feita um a um, o que a solução busca resolver ao automatizar lembretes e cobranças por meio do agente.

### Preenchimento

Com os responsáveis notificados, Maria Eduarda acompanha o preenchimento dos campos pendentes nas listas do SharePoint e nos documentos de projeto, muitas vezes precisando orientar os responsáveis sobre o que e como preencher. Nessa etapa, sua principal dificuldade é a ausência de apoio para preencher campos de forma padronizada, o que a solução busca resolver ao sugerir conteúdo para os campos pendentes a partir da interação com o usuário responsável.

### Consolidação

Na sequência, Maria Eduarda consolida os dados atualizados em relatórios de status e apresentações mensais para a diretoria. Sua principal dificuldade é o tempo gasto reunindo informações espalhadas entre diferentes sistemas e documentos. Nessa etapa, a solução pode consolidar automaticamente os dados com rastreabilidade de fonte, reduzindo o esforço manual de montagem dos relatórios.

### Entrega

Por fim, Maria Eduarda entrega o material consolidado ao PMO e à diretoria, respondendo a questionamentos sobre o andamento do portfólio. Essa etapa representa o ponto de maior satisfação na jornada, pois, ao contar com dados atualizados e rastreáveis, reduz-se o risco de entregar informação desatualizada ou incompleta, tornando a entrega mais segura e ágil.

### Experiência do cliente ao longo da jornada

A experiência de Maria Eduarda evolui de forma crescente ao longo da jornada: parte de um sentimento mais neutro/insatisfeito nas etapas iniciais, quando ainda lida com a falta de alertas e a cobrança manual e repetitiva, e cresce progressivamente até atingir o pico de satisfação na etapa de Entrega, momento em que consegue reportar o andamento do portfólio com mais confiança, agilidade e rastreabilidade.

---

### Persona 3: Rafael Antunes — Líder de Projeto

<div align="center">
<sub>Imagem 1.5.3 - Persona 3: Rafael Antunes — Líder de Projeto</sub><br>
  <img src="../assets/design/Persona-lider.png" width="100%" alt="Persona 3: Rafael Antunes — Líder de Projeto"><br>
  <sup>Fonte: Material produzido pelos autores, 2026.</sup>
</div>

### Caracterização

Rafael Antunes é líder de um empreendimento específico do Metrô e responde pela sua condução no dia a dia, sendo responsável por acompanhar o cronograma, os marcos, os contratos, os riscos e as entregas do projeto sob sua gestão. Diferentemente de uma visão ampla de portfólio, seu foco está na profundidade de um único empreendimento, do qual é a principal fonte de informações.

Sua rotina envolve manter as informações do projeto atualizadas nos sistemas do PMO, responder a demandas da diretoria e do próprio PMO e fazer a ponte entre as equipes de execução — como obra e fornecedores — e a governança da companhia. Nesse contexto, registrar e localizar rapidamente as informações do empreendimento é essencial para acompanhar o andamento e responder com agilidade às demandas.

### Dores

Uma das principais dificuldades de Rafael é o tempo gasto atualizando manualmente status, marcos e riscos em diferentes listas e sistemas. Essa atividade operacional, somada ao retrabalho necessário para consolidar as informações do projeto em relatórios e apresentações, reduz o tempo disponível para a gestão do empreendimento.

Além disso, Rafael lida frequentemente com cobranças do PMO por atualizações pendentes e com a dificuldade de localizar documentos e contratos específicos do seu projeto em meio ao grande volume de informações.

### Interesses no Sistema

Rafael tem interesse em registrar e atualizar status, marcos, riscos e pendências do seu projeto por meio de linguagem natural, por texto ou voz, contando com validação dos campos e rastreabilidade das alterações. Também busca consultar rapidamente documentos, contratos e o histórico do empreendimento sob sua responsabilidade.

Ademais, tem interesse em gerar o status do projeto com menos esforço e em não perder prazos de atualização, mantendo as informações sempre consistentes e disponíveis para o PMO e a diretoria.

### Expectativas em relação à solução

Rafael espera conseguir registrar e consultar as informações do seu empreendimento de maneira simples e rápida, sem precisar navegar manualmente por diversos sistemas e documentos. Também espera que o preenchimento das informações seja apoiado pela solução, com sugestões de conteúdo que ele possa validar, respeitando as permissões de acesso e os campos obrigatórios.

A possibilidade de interagir por linguagem natural, aliada à manutenção da rastreabilidade das alterações, é vista como um fator que reduz o esforço operacional e aumenta a confiabilidade das informações registradas.

### Relação da persona com o produto

A persona de Rafael representa o **Líder de Projeto**, responsável por um empreendimento específico do Metrô. Ele utiliza o agente tanto para **registrar e manter atualizadas as informações do seu projeto** quanto para consultá-las rapidamente, sendo a principal fonte dos dados que alimentam a governança do PMO e as decisões da diretoria. O Líder de Projeto utiliza a solução principalmente para **reduzir o esforço operacional de registro e consulta das informações do seu empreendimento, dedicando mais tempo à gestão e à entrega do projeto**.

### Jornada do Usuário 1.5.3 — Rafael Antunes - Líder de Projeto

<div align="center">
<sub>Imagem 1.5.3.1 - Jornada do Usuário — Rafael Antunes - Líder de Projeto</sub><br>
  <img src="../assets/design/Jornada-lider.png" width="100%" alt="Jornada do Usuário — Rafael Antunes, Líder de Projeto"><br>
  <sup>Fonte: Material produzido pelos autores, 2026.</sup>
</div>

### Cenário

Rafael precisa manter as informações do seu empreendimento sempre atualizadas e responder a demandas do PMO e da diretoria, mas registrar e localizar esses dados exige navegar por diferentes sistemas e documentos, consumindo tempo que faltaria à gestão do projeto.

### Acompanhamento

A jornada de Rafael começa com o acompanhamento contínuo do andamento do seu empreendimento, momento em que identifica o que precisa ser registrado ou atualizado, como um avanço, um atraso, um novo risco ou uma pendência. Nessa etapa, sua principal dificuldade está nas informações do projeto dispersas entre documentos e sistemas, o que representa uma oportunidade para a solução oferecer alertas proativos sobre prazos e pendências do próprio projeto.

### Consulta

Em seguida, Rafael consulta rapidamente documentos, contratos, riscos e o status atual do seu projeto, formulando perguntas em linguagem natural, por texto ou voz. Nessa etapa, a principal dor está na necessidade de navegar por várias listas, pastas e sistemas para localizar a informação, o que a solução busca resolver ao oferecer uma consulta unificada e contextualizada do empreendimento.

### Registro

Com as informações em mãos, Rafael registra ou atualiza o status, os marcos, os riscos e as pendências do projeto em linguagem natural. Nessa etapa, sua principal dor é o preenchimento manual e demorado em diversos campos e sistemas, além do retrabalho envolvido. A solução atua nesse ponto ao oferecer um registro assistido, com sugestão de campos, validação, respeito às permissões e rastreabilidade das alterações.

### Consolidação

Na sequência, Rafael consolida as informações do projeto para gerar relatórios e apresentações de status. Sua principal dificuldade é montar o relatório manualmente, reunindo dados espalhados em diferentes fontes. Nessa etapa, a solução pode gerar prévias de relatório a partir dos dados já atualizados e rastreáveis, reduzindo o esforço de consolidação.

### Reporte

Por fim, Rafael reporta o andamento do projeto ao PMO e à diretoria, respondendo a questionamentos sobre o empreendimento. Essa etapa representa o ponto de maior satisfação da jornada, pois, ao contar com dados confiáveis, atualizados e rastreáveis, reduz-se o risco de reportar informações desatualizadas ou inconsistentes, tornando o reporte mais seguro e ágil.

### Experiência do cliente ao longo da jornada

A experiência de Rafael evolui de forma crescente ao longo da jornada: parte de um sentimento mais neutro/insatisfeito nas etapas iniciais, quando ainda lida com a dispersão das informações e o esforço manual de registro, e cresce progressivamente até atingir o pico de satisfação na etapa de Reporte, momento em que consegue reportar o andamento do projeto com mais confiança, agilidade e rastreabilidade.

---

## 1.6 Fluxo do Negócio

### Cadeia de valor

<div align="center">
<sub>Figura 1.6.1 — Cadeia de valor relacionada à gestão do portfólio de projetos</sub><br>
  <img src="../assets/negócios/cadeia-de-valor.svg" width="100%" alt="Cadeia de valor da gestão do portfólio de projetos, com processos primários, processos de apoio e ponto de atuação do AZ1"><br>
  <sup>Fonte: material produzido pelos autores (2026).</sup>
</div>

A cadeia de valor separa os processos primários, que produzem diretamente informação para o acompanhamento e a tomada de decisão, dos processos de apoio que sustentam sua execução. O fluxo primário começa no planejamento e no cadastro dos empreendimentos, passa pela execução e pela atualização das informações, segue para a consulta e a identificação de pendências, alcança a consolidação e a análise do portfólio e termina no reporte e no apoio à decisão. A governança e os normativos do PMO, a gestão documental e o controle de acesso, a infraestrutura tecnológica e os dados, além da auditoria, da segurança e da rastreabilidade, apoiam todas essas etapas.

O AZ1 atua na etapa de consulta e acompanhamento: interpreta solicitações em linguagem natural, recupera dados autorizados, sinaliza pendências e sugere conteúdo para campos. No MVP, o agente não substitui o cadastro oficial nem grava alterações nas fontes corporativas; o profissional continua responsável por avaliar a sugestão e registrar a informação. Assim, o valor entregue é a redução do esforço de acesso e consolidação sem retirar dos profissionais e dos sistemas oficiais a responsabilidade pela governança dos dados.

### Fluxo do Business Process Model and Notation (BPMN)

 Esta seção modela, em notação BPMN, o fluxo de consulta e registro de informações do portfólio de projetos do Metrô de São Paulo em dois momentos: o processo como ocorre atualmente (AS-IS) e o processo com a solução proposta incorporada (TO-BE). É a comparação entre os dois diagramas que evidencia a contribuição do produto — não pela substituição das atividades ou dos responsáveis, que permanecem os mesmos, mas pela redução do atrito na interação com a informação, preservando os processos, as permissões e a rastreabilidade já estabelecidos pela companhia.

O primeiro diagrama representa o fluxo atual. Suas atividades e decisões são:

1. o usuário identifica uma necessidade de informação ou de ação sobre o portfólio;
2. acessa o agente de inteligência artificial disponível no Microsoft Studio;
3. consulta os dados dos projetos que serão planejados;
4. seleciona blocos de texto predefinidos ou envia uma mensagem de texto;
5. o agente filtra os dados de acordo com a pergunta e consulta o catálogo de portfólios;
6. a plataforma exibe as informações localizadas, e o usuário aguarda a resposta;
7. no gateway **“Conseguiu a resposta?”**, o caminho **Sim** permite que o usuário acesse a informação e encerre o fluxo; no caminho **Não**, o usuário retorna à formulação da consulta e repete o ciclo.

<div align="center">
  <sub>FIGURA 1.6.1 - Fluxo de gestão de portfólio de projetos (AS-IS)</sub><br>
  <img src="../assets/negócios/diagrama_as_is.svg" width="100%" alt="Diagrama BPMN do fluxo de gestão de portfólio de projetos no estado atual"><br>
  <sup>Fonte: material produzido pelos autores (2026).</sup>
</div>

O segundo diagrama representa o mesmo fluxo com a solução incorporada. Suas atividades e decisões são:

1. o usuário identifica uma necessidade de informação ou de apoio a uma ação sobre o portfólio e envia um comando em linguagem natural;
2. no gateway **“Tipo de entrada?”**, o caminho **Áudio** aciona a transcrição; o caminho **Texto** segue diretamente ao pré-processamento;
3. a interface pré-processa e normaliza o texto, compreende a solicitação e classifica sua intenção;
4. no gateway **“Compreendeu a intenção do usuário?”**, o caminho **Sim** prossegue para o tipo de intenção; o caminho **Não** leva ao envio de uma pergunta de esclarecimento;
5. no gateway **“Usuário respondeu?”**, o caminho **Sim** retorna à compreensão da intenção; o caminho **Não** encerra a sessão;
6. no gateway **“Tipo de intenção”**, uma consulta aciona a filtragem e a apresentação dos dados, enquanto um pedido de apoio ao preenchimento gera somente uma sugestão para avaliação humana;
7. a plataforma apresenta a resposta ou a sugestão, e a sessão é encerrada sem alteração automática das fontes de dados.


<div align="center">
  <sub>FIGURA 1.6.2 - Fluxo de gestão de portfólio de projetos (TO-BE)</sub><br>
  <img src="../assets/negócios/diagrama_to_be.svg" width="100%" alt="Diagrama BPMN do fluxo de gestão de portfólio de projetos com o agente de IA incorporado"><br>
  <sup>Fonte: material produzido pelos autores (2026).</sup>
</div>

**Nota de escopo:** no diagrama original, o caminho denominado “Inserção de Informação” representa, para o MVP, apenas a geração de uma sugestão de preenchimento. Nenhuma informação é gravada nas fontes oficiais. A execução efetiva de transações permanece registrada como evolução futura na seção 1.7.

**Principais diferenças entre os fluxos:**

| Aspecto | AS-IS | TO-BE |
| --- | --- | --- |
| Forma de entrada | Blocos de texto predefinidos ou mensagem escrita | Linguagem natural, por texto ou áudio |
| Interpretação da demanda | Filtragem direta a partir da pergunta | Pré-processamento, normalização e classificação da intenção |
| Demanda não compreendida | Usuário retorna ao início e reformula por conta própria | Agente devolve perguntas de esclarecimento antes de encerrar |
| Operações suportadas | Consulta de informação | Consulta de informação e sugestão de preenchimento, sem gravação automática |
| Encerramento | Depende de o usuário obter a resposta por tentativa e erro | Sessão encerrada explicitamente, com resposta ou por ausência de retorno |

 A leitura conjunta dos dois diagramas mostra que o ganho não está em acrescentar etapas ao processo, e sim em deslocar para o agente o esforço que hoje recai sobre o usuário: interpretar a demanda, reformular a pergunta quando o resultado não satisfaz e navegar pela estrutura até localizar a informação. As atividades de negócio e a decisão final permanecem sob responsabilidade dos profissionais do Metrô, conforme delimitado na seção 1.3.

---

## 1.7 Brainstorming de Features

 O brainstorming de features é uma técnica de levantamento de ideias na qual as funcionalidades possíveis para um produto são registradas de forma ampla, antes de qualquer filtro de escopo, para em seguida serem avaliadas e priorizadas. Essa prática permite que o grupo visualize o universo completo de possibilidades da solução, das capacidades essenciais ao MVP até os desejos de longo prazo do parceiro, e tome decisões de sequenciamento fundamentadas, em vez de definir o escopo de maneira implícita ou arbitrária. Nesta seção, são apresentados o registro das ideias levantadas, os critérios adotados para a priorização e a classificação de cada feature quanto ao seu planejamento no projeto.

 A partir da análise do TAPI (Termo de Abertura de Projeto Inteli), das discussões internas do grupo e dos desejos manifestados pelo parceiro, foi realizado um brainstorming de funcionalidades para o agente de IA. Nessa etapa, todas as ideias foram registradas, incluindo aquelas que extrapolam o escopo do MVP, como as funcionalidades que dependem da integração com o portfólio real do Metrô ou de aprovações de compliance da companhia. O objetivo desse registro é duplo: sequenciar o desenvolvimento das features viáveis dentro do módulo e preservar, para o parceiro, as ideias que podem orientar evoluções futuras da solução, ainda que não sejam satisfeitas nesta etapa.

Cada feature foi avaliada em dois critérios. A importância expressa o valor para o problema e para os benefícios esperados pelo parceiro; a viabilidade representa a capacidade de entrega dentro do módulo, considerando esforço técnico, dependências externas e restrições de confidencialidade. Para tornar a priorização reproduzível, adotou-se a escala Baixa = 1, Média = 2 e Alta = 3; níveis intermediários correspondem à média dos níveis adjacentes. O score é a soma de importância e viabilidade, variando de 2 a 6. Empates são resolvidos, nesta ordem, pela maior importância e pela precedência técnica. Por isso, as funcionalidades do pipeline de Processamento de Linguagem Natural antecedem as que dependem dele. A coluna de planejamento registra o recorte do projeto, mas não altera o score.

[PENDENTE — confirmar, para cada feature, se sua origem foi o TAPI, o parceiro ou uma discussão interna da equipe e acrescentar essa informação à tabela; o repositório registra apenas as fontes gerais do brainstorming.]

<div align="center">
<sub>Tabela 1.7 — Brainstorming e priorização de features</sub>
</div>

| Prioridade | Feature                                                                           | Importância | Viabilidade | Score | Planejamento                                  |
| :--------: | --------------------------------------------------------------------------------- | :---------: | :---------: | :---: | --------------------------------------------- |
| 1 | Consulta em linguagem natural por voz e texto | Alta | Alta | 6,0 | MVP |
| 2 | Identificação e classificação de intenções | Alta | Alta | 6,0 | MVP |
| 3 | Detecção de solicitações fora do catálogo de intenções | Alta | Alta | 6,0 | MVP |
| 4 | Consulta a informações estruturadas dos projetos (prazos, marcos, riscos, avanço) | Alta | Alta | 6,0 | MVP |
| 5 | Respostas estruturadas | Alta | Alta | 6,0 | MVP |
| 6 | Aviso de dados insuficientes para resposta confiável | Alta | Alta | 6,0 | MVP |
| 7 | Localização e consulta de documentos dos projetos | Alta | Média | 5,0 | MVP |
| 8 | Indicação das fontes | Alta | Média | 5,0 | MVP |
| 9 | Alertas de prazos e documentos faltantes | Alta | Média | 5,0 | MVP |
| 10 | Identificação de campos incompletos | Alta | Média | 5,0 | MVP |
| 11 | Sugestão de conteúdo para campos | Alta | Média | 5,0 | MVP |
| 12 | Esclarecimento de dúvidas sobre conceitos e normativos de gestão de portfólio | Média/Alta | Média | 4,5 | MVP |
| 13 | Sugestões proativas de consultas e perguntas sugeridas | Média | Média | 4,0 | MVP |
| 14 | Registro de feedback do usuário sobre as respostas | Média | Média | 4,0 | MVP |
| 15 | Controle de acesso por perfil | Alta | Média/Baixa | 4,5 | Simulação no MVP |
| 16 | Rastreabilidade das interações | Alta | Média | 5,0 | Simulação no MVP |
| 17 | Análises comparativas entre projetos | Alta | Média/Baixa | 4,5 | Evolução futura |
| 18 | Prévia de relatório de status | Média/Alta | Média | 4,5 | Evolução futura |
| 19 | Fluxo guiado de criação de projetos (sugestões por etapas) | Média | Baixa | 3,0 | Evolução futura |
| 20 | Painel de alertas e pendências | Média | Média | 4,0 | Evolução futura |
| 21 | Notificações automáticas | Média | Baixa | 3,0 | Evolução futura |
| 22 | Integração com o portfólio real do Metrô (SharePoint, Listas, Power BI) | Alta | Baixa | 4,0 | Registro para o futuro (Ir Além) |
| 23 | Execução efetiva de transações com confirmação do usuário | Alta | Baixa | 4,0 | Registro para o futuro (Ir Além) |
| 24 | Prévia de apresentação mensal para a diretoria | Média | Baixa | 3,0 | Registro para o futuro (desejo do parceiro) |
| 25 | Prévia do relatório de fechamento do portfólio e dos projetos | Média | Baixa | 3,0 | Registro para o futuro (desejo do parceiro) |
| 26 | Identificação de conexões com estratégia e indicadores | Média | Baixa | 3,0 | Registro para o futuro (desejo do parceiro) |
| 27 | Consultas sobre faturas e pagamentos dos projetos | Média | Baixa | 3,0 | Registro para o futuro (desejo do parceiro) |
| 28 | Adoção de serviços de IA generativa homologados | Média | Baixa | 3,0 | Registro para o futuro (evolução tecnológica) |

<div align="center">
<sup>Fonte: Material produzido pelos autores, 2026.</sup>
</div>

 O MVP reúne as funcionalidades que serão efetivamente desenvolvidas e validadas ao longo do módulo, sobre a base de dados sintéticos, e representa a resposta mínima e completa ao problema identificado. As primeiras posições da priorização foram ocupadas pelas capacidades de interpretação em linguagem natural, de classificação de intenções e de controle do catálogo de interações, porque nenhuma outra funcionalidade do agente existe sem elas: o pipeline de Processamento de Linguagem Natural é o fundamento técnico sobre o qual toda a solução se apoia. A entrada por voz foi incluída nesse mesmo núcleo por ser um requisito central do módulo e por reutilizar integralmente o processamento de texto, uma vez que o áudio é convertido em texto antes de seguir para o pipeline. Na sequência, foram priorizadas as consultas, as respostas estruturadas e o aviso de dados insuficientes, que juntas entregam o valor mais imediato ao usuário: obter informação confiável de forma rápida. Por fim, os alertas, o apoio ao preenchimento de campos, o esclarecimento de dúvidas e o registro de feedback completam o escopo, agregando a dimensão proativa da solução e gerando insumos para a melhoria contínua do próprio pipeline. Essa ordenação também funciona como instrumento de gestão do risco de prazo registrado na matriz de riscos: caso o cronograma exija replanejamento, o corte de escopo ocorre das últimas para as primeiras posições, preservando sempre as funcionalidades das quais as demais dependem.

 A categoria de simulação no MVP foi criada para as funcionalidades que o parceiro considera indispensáveis, mas que só podem ser implementadas de forma plena na infraestrutura corporativa real do Metrô, à qual o grupo não terá acesso nesta etapa. É o caso do controle de acesso por perfil e da rastreabilidade das interações, exigências diretas das restrições de confidencialidade do TAPI. Em vez de simplesmente adiá-las, o grupo optou por demonstrar seus mecanismos sobre a base sintética, com perfis de permissão fictícios e registro das interações realizadas. Essa escolha permite validar o comportamento da solução diante dessas exigências e facilita a futura implantação no ambiente da companhia, já que a lógica estará construída e documentada.

 A evolução futura reúne as funcionalidades que agregariam valor ao produto, mas que dependem da maturidade consolidada do núcleo para serem bem executadas, razão pela qual não integram o compromisso inicial do MVP. As análises comparativas entre projetos e a prévia de relatório de status, embora presentes no escopo macro do TAPI, exigem uma base sintética com múltiplos projetos suficientemente ricos e um mecanismo de consulta já estável, condições que só se confirmam ao longo das sprints. Por isso, essa faixa funciona como um backlog complementar, alinhado à estratégia de aproveitamento da oportunidade de expansão registrada na matriz de riscos: ao final de cada sprint, o grupo avalia se há capacidade de incorporar algum desses itens, priorizando os de maior importância. As funcionalidades que não forem desenvolvidas não se perdem, pois serão registradas nas orientações de evolução entregues ao parceiro.

 O registro para o futuro, por fim, preserva os desejos do parceiro e as possibilidades de evolução que não serão satisfeitos nesta etapa, atendendo ao propósito do brainstorming de não descartar nenhuma ideia relevante. A integração com o portfólio real do Metrô e a execução efetiva de transações correspondem ao caminho de evolução que o próprio TAPI denomina "Ir Além", e dependem do acesso ao ambiente corporativo e de aprovações das áreas de TI e compliance da companhia, fatores fora do controle do grupo. As prévias de apresentações e relatórios de fechamento, as conexões com estratégia e indicadores e as consultas financeiras são desejos manifestados pelo parceiro que pressupõem essa integração para gerar valor efetivo. Já a adoção de serviços de IA generativa aguarda homologação pela companhia e está prevista nos entregáveis do projeto como estudo inicial. Vale destacar que a importância de várias dessas funcionalidades é alta, e sua posição na priorização decorre exclusivamente da viabilidade no contexto do módulo. O registro formal dessas ideias integra os entregáveis do projeto e oferece à equipe do Metrô um backlog priorizado para dar continuidade à solução após o encerramento do módulo.

## 1.8 Canvas do MVP

![Business Model Canvas](../assets/negócios/BMC.png)

### Visão geral

O Business Model Canvas (BMC) foi utilizado para estruturar os principais elementos relacionados à proposta de valor, aos usuários, aos recursos e às atividades necessárias para o desenvolvimento do agente de Inteligência Artificial voltado à gestão de projetos do Metrô de São Paulo. Diferentemente de um produto comercial tradicional, a solução proposta possui caráter interno e tem como principal objetivo gerar ganhos de eficiência operacional, facilitar o acesso às informações dos projetos e apoiar os diferentes perfis envolvidos na gestão e no acompanhamento do portfólio de projetos do Metrô. O Canvas considera o agente de IA como uma interface conversacional capaz de consultar informações organizacionais, auxiliar usuários durante atividades relacionadas à documentação dos projetos e facilitar o acesso ao conhecimento existente nos sistemas internos da organização.

### Parceiros-chave

Os parceiros-chave representam os atores necessários para o desenvolvimento, validação e evolução da solução.

**Escritório de Projetos do Metrô**

O Escritório de Projetos possui conhecimento sobre os processos, documentos e regras de gestão utilizados dentro da organização. Sua participação é fundamental para fornecer contexto de negócio, validar os comportamentos esperados do agente e verificar se as respostas e funcionalidades desenvolvidas estão alinhadas às necessidades reais dos usuários.

**Inteli / equipe acadêmica**

O Inteli participa do desenvolvimento do projeto por meio da equipe de estudantes e professores responsáveis pelo acompanhamento técnico e metodológico da solução.

### Atividades-chave

As atividades-chave correspondem às ações necessárias para construir, manter e melhorar continuamente o agente.

**Desenvolvimento e aprimoramento do agente de IA**

Implementar as funcionalidades do agente e realizar melhorias com base nos resultados obtidos durante testes e validações com os stakeholders.

**Integração com as fontes de informação do Metrô**

Permitir que o agente consulte as fontes de dados relevantes para responder às solicitações dos usuários e fornecer informações relacionadas aos projetos.

**Manutenção da base de conhecimento**

Garantir que documentos, informações e demais fontes utilizadas pelo agente estejam organizados e atualizados, reduzindo a possibilidade de respostas baseadas em informações desatualizadas ou inconsistentes.

**Interpretação das intenções dos usuários**

Estruturar os fluxos necessários para que o agente consiga compreender diferentes tipos de solicitação realizados em linguagem natural e identificar corretamente as ações ou informações esperadas pelo usuário.

**Monitoramento da qualidade das respostas**

Avaliar continuamente as respostas produzidas pelo agente, identificando erros, limitações e oportunidades de melhoria.

### Recursos-chave

Os recursos-chave representam os elementos necessários para que a solução consiga operar adequadamente.

**Estrutura e dados do SharePoint**

O SharePoint constitui uma das principais fontes de informação consideradas para a solução, concentrando documentos e dados relacionados à gestão dos projetos.

**Tecnologias de Processamento de Linguagem Natural**

Permitem que os usuários interajam com o sistema utilizando linguagem natural, sem a necessidade de conhecer estruturas específicas de consulta ou navegar manualmente pelas diferentes fontes de informação.

**Modelo de Inteligência Artificial**

O modelo de IA é responsável pela interpretação das solicitações, geração das respostas e apoio às interações realizadas pelo agente.

**Infraestrutura tecnológica da aplicação**

A solução depende da infraestrutura necessária para disponibilizar a interface desenvolvida pela equipe, executar o agente e realizar o processamento e a consulta das informações utilizadas durante as interações.

**Conhecimento sobre os processos de gestão de projetos**

Além da tecnologia, a solução depende do conhecimento das regras, documentos e processos utilizados pelo Metrô para que as respostas estejam alinhadas ao contexto real da organização.

### Propostas de valor

A principal proposta de valor da solução consiste em facilitar a interação dos usuários com as informações relacionadas aos projetos do Metrô.

**Acesso rápido às informações por linguagem natural**

O agente reduz a necessidade de navegação manual por diferentes documentos e estruturas de dados, permitindo que os usuários façam perguntas diretamente em linguagem natural.

**Redução do trabalho manual**

A solução busca diminuir o tempo empregado na busca, interpretação e consolidação manual de informações relacionadas aos projetos.

**Apoio ao acompanhamento e à tomada de decisão**

Ao facilitar o acesso às informações relevantes, o agente pode apoiar líderes, Escritório de Projetos e diretoria durante o acompanhamento dos projetos e a tomada de decisões.

**Maior qualidade e padronização das informações**

O agente pode auxiliar os usuários durante o preenchimento e consulta de documentos, contribuindo para uma maior consistência das informações registradas.

**Assistência no cumprimento da documentação de projetos**

A solução também busca auxiliar os responsáveis pelos projetos no acompanhamento e preenchimento dos documentos necessários ao longo de seu ciclo de vida.

### Relacionamento com os usuários

A relação entre o agente e seus usuários ocorre predominantemente por meio de autoatendimento assistido.

**Assistência personalizada**

As respostas e informações apresentadas podem variar de acordo com o perfil, a solicitação e o contexto do usuário.

**Interação sob demanda**

Os usuários podem consultar o agente sempre que necessitarem localizar informações, esclarecer dúvidas ou obter suporte relacionado aos processos de gestão.

**Uso recorrente**

Por estar relacionado às atividades de acompanhamento e atualização dos projetos, espera-se que o agente seja utilizado de maneira recorrente durante o ciclo de vida dos projetos.

### Segmentos de usuários

A solução atende diferentes perfis envolvidos na gestão de projetos do Metrô.

**Diretoria Executiva**

Necessita principalmente de informações consolidadas que permitam acompanhar a situação dos projetos e apoiar processos de tomada de decisão.

**Líderes de Projeto**

São responsáveis pelo acompanhamento e atualização dos projetos e podem utilizar o agente tanto para consultar informações quanto para receber assistência durante atividades relacionadas à documentação.

**Escritório de Projetos**

Possui uma visão mais ampla do portfólio e dos processos de gestão, utilizando a solução para acessar informações e acompanhar o cumprimento das práticas estabelecidas pela organização.

### Canais

O principal canal de interação previsto para o MVP é uma **interface própria desenvolvida pela equipe**, por meio da qual os usuários poderão se comunicar diretamente com o agente conversacional. Essa abordagem permite que as funcionalidades centrais da solução sejam desenvolvidas e validadas sem depender, durante o projeto, de uma implantação direta no ambiente corporativo da Microsoft utilizado pelo Metrô. Como possibilidade de evolução após a conclusão do MVP, a solução poderá ser integrada às ferramentas já utilizadas pela organização, de forma a aproximar o agente do fluxo de trabalho cotidiano dos usuários.

**Interface própria do agente**

Representa o canal efetivamente implementado durante o desenvolvimento do MVP e será responsável por disponibilizar a interação entre os usuários e o agente de IA.

**Microsoft Teams — integração futura**

O Microsoft Teams é considerado um possível canal futuro para disponibilização do agente dentro do ambiente corporativo do Metrô. Essa integração não faz parte da implementação atual e exigirá adequações técnicas e de infraestrutura para implantação no ambiente da organização.

**Microsoft Copilot Studio — integração futura**

O Microsoft Copilot Studio também é considerado como uma possibilidade de integração e disponibilização futura da solução dentro do ecossistema Microsoft. Sua utilização não faz parte do escopo de implementação do MVP, mas poderá ser indicada ao parceiro como uma alternativa para continuidade e integração da solução após a entrega do projeto.

**SharePoint / Microsoft 365**

O SharePoint possui papel relevante principalmente como fonte de informações e documentos utilizados pelo agente. Em uma implantação futura no ambiente do Metrô, a integração com o ecossistema Microsoft 365 poderá ampliar a disponibilidade e o acesso à solução.

### Estrutura de custos

Como a solução depende de infraestrutura tecnológica e de manutenção contínua, os principais custos considerados são:

* licenciamento de ferramentas e serviços de Inteligência Artificial;
* infraestrutura computacional e processamento;
* desenvolvimento e manutenção do agente;
* integração e manutenção das fontes de dados;
* atividades de governança, segurança e monitoramento da solução.

Em uma futura implantação dentro do ecossistema Microsoft do Metrô, também poderão existir custos associados ao licenciamento e à utilização de ferramentas necessárias para integrar o agente a serviços como Microsoft Teams, SharePoint, Microsoft 365 e Copilot Studio.

Os custos podem variar de acordo com a arquitetura adotada, o número de usuários, o volume de consultas e os serviços utilizados durante a operação.

### Retorno gerado

Por se tratar de uma solução interna desenvolvida para o Metrô de São Paulo, **não existe uma fonte de receita direta associada ao agente**.

O retorno esperado ocorre principalmente por meio de ganhos operacionais e redução de custos indiretos, incluindo:

* redução das horas dedicadas a atividades manuais;
* aumento da produtividade dos profissionais;
* redução de inconsistências nas informações dos projetos;
* melhoria do acompanhamento dos projetos;
* redução potencial de retrabalho e de riscos decorrentes de informações incompletas ou de difícil acesso.

Dessa forma, o valor econômico da solução está associado principalmente à eficiência obtida com a utilização do agente e à melhoria da qualidade dos processos de gestão.

---

## 1.9 Matriz de Risco do Projeto

A matriz de riscos é uma ferramenta amplamente utilizada na gestão de projetos para identificar e monitorar os riscos de um projeto. Nesse contexto, os riscos podem representar tanto ameaças, associadas a possíveis efeitos negativos sobre o projeto, quanto oportunidades, relacionadas a eventos que podem gerar impactos positivos.

No contexto deste projeto, foram identificados e analisados 12 riscos, sendo 9 ameaças e 3 oportunidades. Cada risco foi avaliado considerando dois fatores principais, probabilidade de ocorrência e impacto, os quais constituem os dois eixos da matriz de riscos apresentada a seguir. Para facilitar sua identificação, as ameaças foram representadas pela nomenclatura AMnº, enquanto as oportunidades foram identificadas como OPnº. Cada risco é detalhado individualmente nas subseções seguintes, e o conjunto é consolidado ao final em um quadro resumo acompanhado da representação visual da matriz.

### 1.9.1. Critério de severidade

Além da classificação por probabilidade e impacto, foi atribuída a cada risco uma pontuação de severidade, com o objetivo de representar numericamente a combinação desses dois fatores e facilitar a priorização dos riscos. A severidade é calculada por meio da seguinte expressão:

$$
S = 10 \times \frac{P \times I - 0{,}1}{4{,}4}
$$

Em que:

- **S** representa a severidade do risco, em uma escala de 0 a 10;
- **P** representa a probabilidade de ocorrência, expressa em formato decimal;
- **I** representa o impacto, convertido para uma escala numérica de 1 a 5.

Para a quantificação do impacto, foi adotada a seguinte escala:

| Impacto     | Valor |
| ----------- | :---: |
| Muito Baixo |   1   |
| Baixo       |   2   |
| Moderado    |   3   |
| Alto        |   4   |
| Muito Alto  |   5   |

A utilização dessa escala permite converter as classificações qualitativas de impacto em valores numéricos, possibilitando sua combinação com a probabilidade no cálculo da severidade.

A fórmula foi normalizada em relação às faixas efetivamente adotadas neste registro, nas quais a probabilidade varia de 10% a 90% e o impacto assume valores de 1 a 5. Dentro desses limites, a menor combinação possível, correspondente a uma probabilidade de 10% associada a impacto Muito Baixo, resulta em severidade 0, enquanto a maior combinação, correspondente a uma probabilidade de 90% associada a impacto Muito Alto, resulta em severidade 10. Dessa forma, quanto maior o valor de severidade, maior é a prioridade atribuída ao risco em relação aos demais riscos identificados.

As faixas de criticidade adotadas são apresentadas a seguir:

|  Severidade | Criticidade |
| ----------: | ----------- |
|   0,0 a 2,0 | Muito Baixa |
|  2,01 a 4,0 | Baixa       |
|  4,01 a 6,0 | Moderada    |
|  6,01 a 8,0 | Alta        |
| 8,01 a 10,0 | Muito Alta  |

### 1.9.2. Ameaças

#### AM1. Comunicação interna do grupo

- **Categoria:** Comunicação
- **Probabilidade:** 30%
- **Impacto:** Alto
- **Severidade:** 2,50 (Baixa)
- **Responsável nominal:** Tobias Viana
- **Status:** Em Monitoramento
- **Descrição:** Este risco se refere à possibilidade de falhas na comunicação interna entre os integrantes do grupo, como ruídos no repasse de informações, ausência de clareza sobre a responsabilidade de cada tarefa ou decisões técnicas tomadas sem o conhecimento de todos. A probabilidade foi estimada em 30%, valor considerado baixo, uma vez que o grupo formalizou ainda na primeira semana de desenvolvimento um documento de boas práticas de comunicação, que têm funcionado até o momento e que reduz de forma significativa a chance de ocorrências recorrentes. Ainda assim, a probabilidade não é nula, pois o projeto envolve a interação com um parceiro externo e entre os membros do grupo. O impacto foi classificado como Alto porque uma falha de comunicação não permaneceria restrita ao ambiente interno do grupo, podendo gerar retrabalho em componentes já desenvolvidos do pipeline de PLN, decisões técnicas desalinhadas entre os integrantes e o repasse de informações inconsistentes a equipe do Metrô, situações que atrapalham o desenvolvimento do projeto.
- **Mitigação:** Manter e revisar periodicamente o documento de boas práticas de comunicação, ajustando os acordos da equipe conforme os aprendizados ao longo das sprints.
- **Contingência:** Em caso de conflito ou desalinhamento, o responsável nominal deve realizar uma reunião com os membros envolvidos no conflito para resolver a situação antes que ela comprometa a sprint em andamento e sugerir formas de evitar conflitos futuros.

#### AM2. Baixa acurácia na identificação de intenções

- **Categoria:** Técnico
- **Probabilidade:** 30%
- **Impacto:** Muito Alto
- **Severidade:** 3,18 (Baixa)
- **Responsável nominal:** Ana Cristina, desenvolvedora técnica da pipeline
- **Status:** Aberto
- **Descrição:** Este risco se refere à possibilidade de o pipeline de PLN desenvolvido pela equipe não atingir um nível satisfatório de acurácia na classificação das intenções do usuário, confundindo solicitações de naturezas distintas, como consulta, transação e alerta, ou deixando de rejeitar interações genéricas e fora do contexto do portfólio. A probabilidade foi estimada em 30%, valor considerado baixo, porque a classificação opera sobre um catálogo fechado de intenções, definido e validado junto ao parceiro antes do desenvolvimento, e porque se trata de uma tarefa consolidada no campo do processamento de linguagem natural, com técnicas maduras e amplamente documentadas. O acompanhamento das métricas desde a primeira versão do pipeline também permite corrigir o rumo a cada iteração, o que reduz a chance de o problema ser percebido apenas ao final. Ainda assim, a probabilidade não é desprezível, pois a avaliação ocorre exclusivamente sobre dados sintéticos construídos pela própria equipe, a entrada por voz agrega ruído ao texto processado e o catálogo abrange o ciclo de vida completo do projeto dentro do portfólio, o que amplia a variedade de formulações que o modelo precisa distinguir. O impacto foi classificado como Muito Alto porque a identificação de intenções constitui o núcleo do MVP, de modo que uma acurácia insuficiente comprometeria todas as capacidades construídas sobre ela, incluindo o roteamento das solicitações, a geração de respostas estruturadas e o atendimento aos requisitos não funcionais de precisão acordados com o parceiro.
- **Mitigação:** Definir o catálogo de intenções aceitáveis logo nas primeiras sprints, tomando como base os exemplos de interação em linguagem natural apresentados pelo parceiro, e submeter esse catálogo à validação do Metrô antes do início do desenvolvimento. Em paralelo, estabelecer desde a primeira versão do pipeline um conjunto de métricas de avaliação, como acurácia, F1 por classe e matriz de confusão, acompanhadas a cada iteração para identificar precocemente as intenções com pior desempenho.
- **Contingência:** Caso a acurácia permaneça abaixo do patamar acordado, reduzir o escopo do catálogo para o subconjunto de intenções com melhor desempenho comprovado e introduzir um mecanismo de confirmação explícita da intenção junto ao usuário sempre que a confiança da classificação ficar abaixo de um limiar definido, de forma que a solicitação seja esclarecida antes de qualquer execução. As limitações observadas devem ser registradas na documentação do pipeline e incorporadas às orientações de evolução futura previstas nos entregáveis do projeto.

#### AM3. Atraso na liberação de acesso ao ambiente Microsoft pelo parceiro

- **Categoria:** Stakeholders
- **Probabilidade:** 70%
- **Impacto:** Moderado
- **Severidade:** 4,55 (Moderada)
- **Responsável nominal:** Rui Facó
- **Status:** Aberto
- **Descrição:** Este risco se refere à possibilidade de a equipe não obter acesso ao ambiente Microsoft do parceiro, composto por Copilot Studio e demais serviços da Power Platform, ou de esse acesso ser concedido tardiamente. A probabilidade foi estimada em 70%, valor considerado alto, porque a liberação depende da aprovação das áreas de TI e de compliance do Metrô e implica conceder credenciais de um ambiente corporativo a integrantes externos à companhia, situação que costuma exigir análise formal e etapas de autorização cujo prazo o grupo não controla nem consegue antecipar. As restrições de confidencialidade que orientam o projeto tornam esse tipo de concessão ainda mais criteriosa, o que reforça a expectativa de demora. O impacto foi classificado como Moderado porque a arquitetura da solução não depende do ecossistema Microsoft, já que o grupo tem liberdade para desenvolver o pipeline de PLN na tecnologia que considerar mais adequada. A consequência recai sobre o material de correspondência entre a solução construída e sua equivalente no ecossistema Microsoft, entregável solicitado pelo parceiro, que ficaria restrito a um mapeamento conceitual sem verificação prática na plataforma.
- **Mitigação:** Solicitar o acesso de forma antecipada e formal com apoio dos professores orientadores, registrando o pedido e acordando um prazo de retorno. Enquanto a liberação não ocorre, estruturar a correspondência entre as duas soluções a partir da documentação oficial do Copilot Studio e da Power Platform e avaliar o uso de um ambiente gratuito de desenvolvimento da própria Microsoft, que permite experimentação sem qualquer exposição de dados do parceiro.
- **Contingência:** Caso o acesso não seja concedido, elaborar o material de correspondência exclusivamente com base na documentação oficial e em experimentação realizada em ambiente próprio, explicitando na documentação que o mapeamento não foi verificado no ambiente do Metrô. Como complemento, submeter o material à revisão da equipe de TI e do PMO do parceiro, de modo que a validação conceitual seja obtida mesmo sem o acesso técnico.

#### AM4. Atraso no fornecimento de informações pelo Metrô

- **Categoria:** Dados e Stakeholders
- **Probabilidade:** 50%
- **Impacto:** Alto
- **Severidade:** 4,32 (Moderada)
- **Responsável nominal:** Karol Barbosa
- **Status:** Aberto
- **Descrição:** Este risco se refere à possibilidade de o Metrô demorar a fornecer as informações e os artefatos de referência necessários ao desenvolvimento da solução. Como o MVP é validado sobre dados sintéticos, o grupo depende do envio de arquivos de exemplo pelo parceiro, tais como termo de abertura de projeto, mapa de benefícios, relatório de status, cronograma e normativos de gestão, para que o conjunto sintético reproduza a estrutura, a terminologia e o nível de detalhe dos documentos realmente utilizados pelo parceiro. A probabilidade foi estimada em 50% porque, embora exista um canal formal de comunicação com o parceiro, o material precisa passar por anonimização ou adaptação antes de ser compartilhado, em razão das restrições de confidencialidade, o que representa esforço adicional para uma equipe que possui suas próprias prioridades operacionais. O impacto foi classificado como Alto porque a ausência desses exemplos obrigaria o grupo a construir o conjunto sintético a partir de suposições sobre o formato dos documentos, reduzindo a representatividade do dataset e, por consequência, a confiabilidade de toda a avaliação do pipeline de PLN.
- **Mitigação:** Encaminhar, logo na primeira sprint, uma solicitação objetiva com a relação exata dos artefatos desejados e a finalidade de cada um. Para reduzir o esforço do parceiro, a solicitação deve deixar claro que os arquivos podem ser fictícios ou anonimizados e que interessa ao grupo a estrutura dos documentos, e não o conteúdo real dos projetos. O acompanhamento do pedido deve ocorrer nos encontros periódicos com o parceiro, de modo que eventuais atrasos sejam percebidos com antecedência.
- **Contingência:** Caso os arquivos não sejam disponibilizados no prazo acordado, iniciar a construção do conjunto sintético a partir dos exemplos de interação em linguagem natural presentes no apêndice do TAPI e de modelos públicos de artefatos de gestão de projetos, mantendo o desenvolvimento em andamento. Quando o material oficial for recebido, o conjunto deve ser revisado e ajustado para incorporar a estrutura real dos documentos, e a limitação enfrentada precisa ser registrada na documentação do pipeline.

#### AM5. Não conclusão do projeto dentro do prazo

- **Categoria:** Cronograma
- **Probabilidade:** 10%
- **Impacto:** Muito Alto
- **Severidade:** 0,91 (Muito Baixa)
- **Responsável nominal:** Felipe Simão
- **Status:** Aberto
- **Descrição:** Este risco se refere à possibilidade de o grupo não concluir o escopo acordado do MVP até a data de encerramento do projeto, entregando uma solução incompleta ou sem o nível de maturidade necessário para demonstração ao parceiro. A probabilidade foi estimada em 10%, valor considerado muito baixo, uma vez que o projeto é conduzido dentro de uma estrutura formal de sprints, com cerimônias definidas, entregas incrementais avaliadas ao longo do módulo e acompanhamento contínuo dos professores orientadores. Esse formato obriga o grupo a produzir resultado demonstrável em cada ciclo e permite identificar desvios de ritmo enquanto ainda há tempo de correção, o que torna improvável um atraso capaz de comprometer a entrega final. A probabilidade não é nula porque o escopo abrange desde a construção do pipeline de PLN até a interação por voz e o material de correspondência com o ecossistema Microsoft, e parte do trabalho depende de insumos fornecidos pelo parceiro. O impacto foi classificado como Muito Alto porque a data de encerramento é definida pelo calendário acadêmico e não admite prorrogação, de modo que um atraso não pode ser compensado com tempo adicional e resultaria na entrega de uma solução parcial ao Metrô, comprometendo tanto a avaliação do módulo quanto o valor percebido pelo parceiro.
- **Mitigação:** Manter o escopo priorizado de forma explícita, distinguindo as funcionalidades essenciais ao MVP daquelas classificadas como desejáveis, e planejar cada sprint de modo que produza um incremento funcional demonstrável, e não apenas trabalho parcial acumulado. O ritmo de execução deve ser acompanhado durante as cerimônias, com comparação entre o previsto e o realizado a cada sprint, de forma que qualquer desvio seja tratado no ciclo seguinte. Sempre que possível, as funcionalidades que constituem o núcleo da solução devem ser concluídas antes das que representam diferenciais.
- **Contingência:** Caso o atraso se materialize, replanejar o escopo restante em conjunto com o Product Owner e os professores orientadores, concentrando o esforço da equipe no núcleo do MVP e reclassificando as funcionalidades desejáveis como evolução futura, devidamente registradas nas orientações de continuidade entregues ao parceiro. Em paralelo, redistribuir as tarefas entre os integrantes de modo a reforçar as frentes críticas para a entrega final.

#### AM6. Dados insuficientes ou inadequados para validação do agente

- **Categoria:** Dados
- **Probabilidade:** 70%
- **Impacto:** Alto
- **Severidade:** 6,14 (Alta)
- **Responsável nominal:** Matheus Ferreira, responsável pela avaliação do pipeline
- **Status:** Aberto
- **Descrição:** Este risco se refere à possibilidade de o conjunto de dados sintéticos construído pelo grupo não possuir volume, diversidade ou aderência suficientes para validar o agente de forma confiável. Diferentemente do risco associado ao atraso no fornecimento de insumos pelo parceiro, o problema aqui recai sobre a qualidade do próprio conjunto, ainda que ele seja produzido dentro do prazo. A probabilidade foi estimada em 70%, valor considerado alto, porque o dataset é elaborado pelos mesmos integrantes que desenvolvem o pipeline, o que favorece a criação de exemplos alinhados às soluções já implementadas e tende a produzir uma avaliação otimista. Além disso, a cobertura de situações críticas, como solicitações ambíguas, pedidos fora do contexto do portfólio que devem ser rejeitados e transcrições imperfeitas provenientes da entrada por voz, exige construção deliberada de casos e dificilmente ocorre de forma espontânea. O impacto foi classificado como Alto porque uma base de validação inadequada compromete a credibilidade das métricas apresentadas, podendo levar o grupo a concluir que o agente atende aos requisitos quando, na prática, apenas reproduz bem os poucos padrões que conhece, o que afeta diretamente a avaliação de desempenho prevista entre os entregáveis do projeto.
- **Mitigação:** Definir previamente os critérios de composição do conjunto de dados, estabelecendo cobertura mínima de exemplos por intenção e a inclusão obrigatória de casos ambíguos, fora de contexto e com ruído de transcrição. Como medida adicional, o conjunto reservado para teste deve ser elaborado por integrantes que não participaram da construção do conjunto de treinamento, de modo a reduzir a circularidade entre quem cria os dados e quem desenvolve o modelo. Sempre que possível, uma amostra do conjunto deve ser apresentada ao PMO do Metrô para confirmação de que as formulações refletem a linguagem efetivamente usada na gestão do portfólio.
- **Contingência:** Caso a avaliação evidencie que o conjunto é insuficiente, ampliar a base com novos casos concentrados nas classes de pior desempenho e nas situações de rejeição, repetindo a avaliação em seguida. Se não houver condição de ampliar o conjunto de forma adequada, delimitar formalmente o alcance das conclusões na documentação, explicitando sobre quais tipos de solicitação as métricas obtidas são válidas e quais aspectos permanecem sem verificação.

#### AM7. Indisponibilidade ou sobrecarga de um integrante da equipe

- **Categoria:** Equipe
- **Probabilidade:** 50%
- **Impacto:** Moderado
- **Severidade:** 3,18 (Baixa)
- **Responsável nominal:** Paulo Henrique
- **Status:** Em Monitoramento
- **Descrição:** Este risco se refere à possibilidade de um integrante ficar temporariamente indisponível ou sobrecarregado durante o projeto, seja por demandas simultâneas de outras disciplinas, seja por imprevistos pessoais ou de saúde. A probabilidade foi estimada em 50% porque a equipe conduz o projeto em paralelo às demais atividades acadêmicas, cujos períodos de avaliação se concentram em momentos específicos e afetam todos os integrantes ao mesmo tempo, o que torna a ocorrência plausível ao longo das sprints. O impacto foi classificado como Moderado porque o grupo consegue redistribuir tarefas entre os demais integrantes, de forma que a entrega não fica bloqueada, ainda que o ritmo de execução seja reduzido. O efeito se agrava quando a ausência atinge a pessoa responsável por uma frente técnica específica do pipeline, situação em que o conhecimento concentrado em um único integrante retarda a retomada do trabalho.
- **Mitigação:** Distribuir o conhecimento das frentes críticas entre mais de um integrante, evitando que qualquer componente da solução dependa exclusivamente de uma pessoa, e manter a documentação técnica atualizada a cada entrega, de modo que outro integrante consiga assumir a frente sem retrabalho. O planejamento das sprints deve considerar os períodos de maior carga acadêmica, distribuindo as tarefas mais exigentes fora desses intervalos.
- **Contingência:** Caso a indisponibilidade ocorra, redistribuir as tarefas do integrante afetado entre os demais na daily seguinte, priorizando as frentes essenciais ao MVP, de modo que nenhuma atividade fique parada à espera do próximo ciclo de planejamento. Se a ausência se prolongar por mais de uma sprint e comprometer o escopo acordado, o replanejamento deve ser conduzido na planning seguinte, em conjunto com o Product Owner, e comunicado aos professores orientadores.

#### AM8. Alucinação do modelo de linguagem

- **Categoria:** Técnico
- **Probabilidade:** 50%
- **Impacto:** Alto
- **Severidade:** 4,32 (Moderada)
- **Responsável nominal:** Ana Cristina Jardim
- **Status:** Aberto
- **Descrição:** Este risco se refere à possibilidade de o modelo de linguagem utilizado no pipeline de PLN gerar respostas que não estejam fundamentadas nas fontes consultadas, produzindo informações plausíveis mas incorretas sobre os projetos do portfólio — fenômeno conhecido como alucinação. A probabilidade foi estimada em 50% porque a geração de texto por modelos de linguagem de grande porte é suscetível a esse problema em domínios especializados, especialmente quando as fontes disponíveis não cobrem todos os cenários de consulta ou quando a pergunta é ambígua. O risco é especialmente relevante no contexto do MVP, cujas fontes são dados sintéticos com cobertura limitada. O impacto foi classificado como Alto porque uma resposta incorreta apresentada como confiável pode induzir o profissional a tomar uma decisão baseada em informação falsa, comprometendo tanto a credibilidade do agente quanto a qualidade da gestão do portfólio. Esse risco está diretamente relacionado ao RF03, que exige a indicação de fonte, e ao RNF11, que exige explicabilidade das sugestões.
- **Mitigação:** Adotar a abordagem de Retrieval-Augmented Generation (RAG), ancorando todas as respostas em trechos recuperados das fontes disponíveis antes da geração de texto. Exibir obrigatoriamente a fonte e o trecho de origem em cada resposta, de modo que o usuário possa verificar a informação. Construir casos de teste específicos para avaliar a taxa de respostas fundamentadas versus respostas sem suporte nas fontes.
- **Contingência:** Caso respostas sem fundamentação sejam identificadas nos testes, adicionar um mecanismo de filtragem que bloqueie a exibição de respostas cuja confiança de recuperação esteja abaixo de um limiar definido. Nesses casos, o agente deve informar ao usuário que não há dados suficientes para uma resposta confiável, conforme previsto no critério de aceitação do RF02.

#### AM9. Degradação da qualidade da transcrição em ambiente ruidoso

- **Categoria:** Técnico
- **Probabilidade:** 50%
- **Impacto:** Moderado
- **Severidade:** 3,18 (Baixa)
- **Responsável nominal:** Matheus Ferreira da Silva
- **Status:** Aberto
- **Descrição:** Este risco se refere à possibilidade de o serviço de conversão de áudio em texto (Speech-to-Text) produzir transcrições com taxa de erro de palavras acima do limite de 15% definido no RNF06, especialmente em cenários com ruído de fundo, sotaque regional, vocabulário técnico de gestão de projetos ou microfone de baixa qualidade. A probabilidade foi estimada em 50% porque, embora os serviços de STT disponíveis no mercado sejam maduros para português brasileiro em condições controladas, a qualidade degrada de forma relevante em ambientes corporativos com interferência de som ou quando o usuário utiliza terminologia específica do setor metroferroviário não contemplada no modelo base. O impacto foi classificado como Moderado porque uma transcrição imprecisa pode levar o pipeline a classificar incorretamente a intenção da solicitação ou a extrair entidades erradas, comprometendo a qualidade da resposta, mas sem causar dano irreversível — o usuário pode reformular a solicitação por texto se perceber o erro na transcrição exibida.
- **Mitigação:** Exibir a transcrição gerada ao usuário antes do processamento da solicitação, conforme definido no RF01, para que o profissional possa identificar e reportar erros antes de receber uma resposta incorreta. Avaliar o serviço de STT com um conjunto de áudios representativo do vocabulário do portfólio, incluindo termos técnicos de gestão de projetos e empreendimentos, medindo o WER contra transcrições de referência conforme o RNF06.
- **Contingência:** Caso a taxa de erro de palavras supere o limite em testes com o vocabulário do portfólio, avaliar a possibilidade de fine-tuning do modelo de STT com exemplos do domínio ou de substituição por outro serviço. Como alternativa imediata, oferecer ao usuário a opção de editar a transcrição antes da confirmação, reduzindo o impacto de transcrições imprecisas sem eliminar a funcionalidade de entrada por voz.

### 1.9.3. Oportunidades

#### OP1. Reutilização e evolução da solução

- **Categoria:** Arquitetura
- **Probabilidade:** 70%
- **Impacto:** Alto
- **Severidade:** 6,14 (Alta)
- **Responsável nominal:** Felipe Simão, responsável pela arquitetura da solução
- **Status:** Em Monitoramento
- **Descrição:** Esta oportunidade se refere ao ganho obtido ao desenvolver o núcleo do agente de forma desacoplada das camadas de interface, de orquestração e de acesso aos dados, de modo que o pipeline de PLN não dependa de nenhuma plataforma específica para funcionar. A probabilidade foi estimada em 70%, valor considerado alto, porque a concretização desse cenário depende essencialmente de decisões de projeto que estão sob o controle do grupo, ainda que exija disciplina para preservar as fronteiras entre as camadas ao longo de todas as sprints. O impacto foi classificado como Alto porque essa característica atende diretamente a uma premissa segundo a qual a plataforma de gestão de portfólio do Metrô pode ser modificada ou substituída no futuro por outras soluções, cabendo à solução de inteligência artificial permanecer funcional mesmo diante dessa troca. Um núcleo desacoplado também viabiliza a construção do material de correspondência com o ecossistema Microsoft, torna mais simples a evolução prevista para a integração com o portfólio real e reduz o custo de sustentação da solução pela equipe interna do parceiro.
- **Estratégia de aproveitamento:** Estabelecer desde o início do desenvolvimento uma separação explícita entre o núcleo de processamento de linguagem natural e as demais camadas da solução, expondo esse núcleo por meio de uma interface de comunicação bem definida e independente de tecnologia, de forma que qualquer plataforma de orquestração possa consumir suas funcionalidades sem alteração da lógica interna. As decisões de arquitetura que sustentam esse desacoplamento devem ser registradas na documentação técnica do projeto, incluindo a justificativa de cada escolha, e utilizadas como base tanto para o material de correspondência com o ecossistema Microsoft quanto para as orientações de evolução futura entregues ao Metrô.

#### OP2. Expansão do agente para novas funcionalidades de gestão de portfólio

- **Categoria:** Escopo
- **Probabilidade:** 50%
- **Impacto:** Moderado
- **Severidade:** 3,18 (Baixa)
- **Responsável nominal:** Paulo Henrique
- **Status:** Aberto
- **Descrição:** Esta oportunidade se refere à possibilidade de o agente incorporar, ao longo do projeto, funcionalidades de gestão de portfólio que não integram o recorte inicial do MVP, ampliando o valor entregue ao parceiro. O escopo macro descrito no TAPI reúne um conjunto extenso de capacidades, como o apoio ao preenchimento de dados de projeto, o esclarecimento de dúvidas sobre normativos, a geração de prévias de relatórios e apresentações e o alerta proativo de pendências, das quais o MVP contempla apenas uma parte. A probabilidade foi estimada em 50% porque a concretização desse cenário depende de o núcleo do pipeline atingir maturidade antes do previsto e de haver folga real de esforço nas sprints finais, condições plausíveis, mas não asseguradas. O impacto foi classificado como Moderado porque a incorporação de novas funcionalidades amplia o alcance da demonstração e aproxima a entrega da visão de produto desejada pelo Metrô, sem, contudo, alterar a natureza do resultado central do projeto, que permanece sendo o pipeline de processamento de linguagem natural validado sobre dados sintéticos.
- **Estratégia de aproveitamento:** Manter um backlog complementar com as funcionalidades do escopo macro que não integram o MVP, já priorizado segundo o valor percebido pelo parceiro e o esforço estimado pelo grupo, de modo que exista uma decisão previamente tomada sobre o que incorporar caso surja capacidade adicional de trabalho. Para viabilizar essa expansão sem retrabalho, o catálogo de intenções e a estrutura do pipeline devem ser projetados de forma extensível, permitindo a inclusão de novas intenções sem alteração da arquitetura. Ao final de cada sprint, o grupo deve avaliar se há condição de puxar um item desse backlog, e as funcionalidades que permanecerem fora do escopo precisam ser registradas nas orientações de evolução futura entregues ao Metrô.

#### OP3. Validação com dados e cenários mais próximos da realidade

- **Categoria:** Dados
- **Probabilidade:** 50%
- **Impacto:** Alto
- **Severidade:** 4,32 (Moderada)
- **Responsável nominal:** Matheus Ferreira, responsável pela avaliação do pipeline
- **Status:** Em Monitoramento
- **Descrição:** Esta oportunidade consiste na possibilidade de a base sintética utilizada na validação do MVP se tornar progressivamente mais representativa dos projetos do Metrô, incorporando a estrutura, a terminologia e as situações efetivamente encontradas na rotina do PMO. A probabilidade foi estimada em 50% porque a concretização desse cenário depende de dois fatores de peso semelhante, o envio de artefatos de exemplo pelo parceiro, que permitem calibrar o conjunto conforme os documentos reais, e o esforço contínuo do próprio grupo em enriquecer a base ao longo das sprints, ambos plausíveis, mas nenhum deles assegurado. O impacto foi classificado como Alto porque a representatividade do conjunto sintético determina diretamente a credibilidade das métricas obtidas na avaliação do pipeline de PLN, que constitui um dos entregáveis formais do projeto. Uma base mais próxima da realidade também qualifica a demonstração da solução ao parceiro, que passa a reconhecer nos exemplos apresentados o vocabulário e os cenários do seu próprio portfólio, o que fortalece a percepção de valor da entrega.
- **Estratégia de aproveitamento:** Ampliar de forma progressiva os cenários e exemplos presentes na base sintética, contemplando diferentes tipos de consulta, projetos, riscos, marcos e demais situações previstas no escopo do agente, e priorizar aquelas que correspondem às atividades mais frequentes na gestão do portfólio. Sempre que o parceiro disponibilizar artefatos de exemplo, esses materiais devem ser utilizados para ajustar a estrutura e a terminologia do conjunto já construído. A base deve ser versionada, de modo que as métricas obtidas em cada versão sejam comparáveis entre si e evidenciem o ganho de qualidade da avaliação ao longo do projeto, e uma amostra dos cenários deve ser apresentada ao PMO do Metrô para confirmação de aderência.

### 1.9.4. Representação visual

O quadro a seguir consolida os dez itens registrados, reunindo a avaliação atribuída a cada um, o responsável pelo acompanhamento e o status atual:

| ID  | Risco                                                                | Categoria            | Probabilidade | Impacto    | Severidade | Criticidade | Responsável          | Status           |
| --- | -------------------------------------------------------------------- | -------------------- | ------------: | ---------- | ---------: | ----------- | -------------------- | ---------------- |
| AM1 | Comunicação interna do grupo                                         | Comunicação          |           30% | Alto       |       2,50 | Baixa       | Tobias Viana         | Em Monitoramento |
| AM2 | Baixa acurácia na identificação de intenções                         | Técnico              |           30% | Muito Alto |       3,18 | Baixa       | Ana Cristina Jardim  | Aberto           |
| AM3 | Atraso na liberação de acesso ao ambiente Microsoft pelo parceiro    | Stakeholders         |           70% | Moderado   |       4,55 | Moderada    | Rui Facó             | Aberto           |
| AM4 | Atraso no fornecimento de informações pelo Metrô                     | Dados e Stakeholders |           50% | Alto       |       4,32 | Moderada    | Karol Barbosa Rocha  | Aberto           |
| AM5 | Não conclusão do projeto dentro do prazo                             | Cronograma           |           10% | Muito Alto |       0,91 | Muito Baixa | Felipe Simão         | Aberto           |
| AM6 | Dados insuficientes ou inadequados para validação do agente          | Dados                |           70% | Alto       |       6,14 | Alta        | Matheus Ferreira     | Aberto           |
| AM7 | Indisponibilidade ou sobrecarga de um integrante da equipe           | Equipe               |           50% | Moderado   |       3,18 | Baixa       | Paulo Henrique       | Em Monitoramento |
| AM8 | Alucinação do modelo de linguagem                                    | Técnico              |           50% | Alto       |       4,32 | Moderada    | Ana Cristina Jardim  | Aberto           |
| AM9 | Degradação da qualidade da transcrição em ambiente ruidoso           | Técnico              |           50% | Moderado   |       3,18 | Baixa       | Matheus Ferreira     | Aberto           |
| OP1 | Reutilização e evolução da solução                                   | Arquitetura          |           70% | Alto       |       6,14 | Alta        | Felipe Simão         | Em Monitoramento |
| OP2 | Expansão do agente para novas funcionalidades de gestão de portfólio | Escopo               |           50% | Moderado   |       3,18 | Baixa       | Paulo Henrique       | Aberto           |
| OP3 | Validação com dados e cenários mais próximos da realidade            | Dados                |           50% | Alto       |       4,32 | Moderada    | Matheus Ferreira     | Em Monitoramento |

A figura a seguir posiciona esses itens na matriz de probabilidade e impacto, com as ameaças representadas à esquerda e as oportunidades à direita:

<div align="center">
  <sub>FIGURA 1.9 - Matriz de probabilidade e impacto</sub><br>
  <img src="../assets/negócios/matriz-de-risco.png" width="100%" alt="Matriz de probabilidade e impacto do projeto"><br>
  <sup>Fonte: material produzido pelos autores (2026).</sup>
</div>

### 1.9.5. Análise dos itens mais críticos

A seleção dos itens mais críticos tomou como critério a severidade calculada, e não a leitura isolada da probabilidade ou do impacto. A escolha se deve ao fato de que a severidade é a única medida do registro que expressa os dois fatores simultaneamente em uma escala comum, o que permite comparar itens de naturezas muito distintas, como uma ameaça provável de consequência moderada e outra improvável de consequência severa, sob o mesmo parâmetro. Ordenar por probabilidade privilegiaria eventos frequentes ainda que inofensivos, enquanto ordenar por impacto destacaria cenários graves porém remotos, e nenhum dos dois recortes indicaria corretamente onde a equipe deve concentrar esforço.

O uso da severidade também torna a priorização verificável, uma vez que a regra de cálculo é explícita e qualquer leitor pode reproduzir o resultado a partir dos valores declarados para cada item, o que afasta a seleção arbitrária dos riscos que o grupo considera mais relevantes. Como a mesma regra se aplica a ameaças e a oportunidades, os dez itens compõem uma ordenação única, na qual uma oportunidade bem posicionada indica prioridade de aproveitamento, e não de correção. A partir desse critério, três itens se destacam dos demais:

| Item | Descrição resumida                                                | Severidade | Criticidade |
| ---- | ----------------------------------------------------------------- | ---------: | ----------- |
| AM6  | Dados insuficientes ou inadequados para validação do agente       |       6,14 | Alta        |
| OP1  | Reutilização e evolução da solução                                |       6,14 | Alta        |
| AM3  | Atraso na liberação de acesso ao ambiente Microsoft pelo parceiro |       4,55 | Moderada    |

A **AM6** ocupa o topo da priorização por combinar a maior probabilidade atribuída entre as ameaças com um impacto que atinge a própria evidência de qualidade do projeto. Como o agente é validado exclusivamente sobre dados sintéticos, o conjunto de validação é o único instrumento capaz de demonstrar que a solução funciona, de modo que sua inadequação não degrada apenas uma métrica isolada, mas retira a sustentação de todas as conclusões apresentadas ao parceiro. Trata se, além disso, de um risco cuja causa está inteiramente sob controle do grupo, o que torna o esforço preventivo especialmente eficaz.

A **OP1** alcança a mesma severidade da AM6, porém com sentido oposto, uma vez que a pontuação elevada em um risco positivo indica prioridade de aproveitamento, e não de correção. Sua posição se justifica porque o desacoplamento do núcleo do agente responde diretamente a uma premissa registrada pelo parceiro, segundo a qual a plataforma de gestão de portfólio pode ser substituída no futuro, e porque se trata de uma decisão de arquitetura tomada logo no início do desenvolvimento, cujo custo cresce de forma significativa caso o grupo opte por adiá-la.

A **AM3** completa a priorização por ser a ameaça de maior probabilidade cuja causa está fora do alcance do grupo, já que a liberação de acesso depende de aprovação das áreas de TI e de compliance do Metrô. Ainda que seu impacto seja moderado, por não comprometer a arquitetura da solução, a mitigação só produz efeito se iniciada com antecedência, o que a coloca entre os itens que exigem ação imediata mesmo sem figurar na faixa de criticidade mais elevada.

Observa-se que os dois itens de maior severidade decorrem de decisões internas do grupo, enquanto o terceiro depende de terceiros, o que orienta tratamentos distintos: nos dois primeiros, a prioridade recai sobre a disciplina de execução da equipe, e, no terceiro, sobre a antecipação da solicitação e a preparação de um caminho alternativo.

---

# 2. Especificação de Requisitos de Software (Sprint 1)

## 2.1 Business Drivers

### Contexto da aplicação

Conforme detalhado na seção 1.1, a gestão do portfólio do Metrô depende hoje de ações manuais para a obtenção de status, a consolidação de documentos e o acompanhamento de pendências. Do ponto de vista computacional, a aplicação de Processamento de Linguagem Natural transforma esse cenário ao substituir a navegação manual por listas e documentos por uma interação direta em linguagem natural, na qual o usuário formula sua solicitação por texto ou por voz e recebe uma resposta já estruturada, rastreável até sua fonte original e adequada ao seu nível de permissão.

Essa transformação depende de duas capacidades transversais, exigidas por ambos os fluxos descritos a seguir: um canal de entrada que processe texto e áudio de forma equivalente, exibindo a transcrição para conferência quando a entrada ocorrer por voz e um mecanismo de classificação capaz de reconhecer toda solicitação dentro de um catálogo de intenções definido com o parceiro, recusando pedidos fora do escopo do portfólio antes mesmo de consultar as fontes de dados.

### Fluxo de negócio 1: Consulta e análise comparativa de projetos

- **Situação atual (AS-IS):** conforme mapeado no fluxo de negócio (seção 1.6), a consulta e a comparação entre projetos hoje dependem de navegação manual pelas listas do SharePoint e de consolidação visual dos dados, processo sujeito a erros de interpretação e que se torna mais custoso quando envolve cruzar informações de portfólio com indicadores estratégicos.

- **Situação proposta (TO-BE):** o usuário formula sua solicitação diretamente em linguagem natural, como por exemplo: "qual o status do projeto X?" ou "compare os projetos X e Y em relação a prazo e riscos", e o sistema retorna os indicadores solicitados já filtrados conforme seu nível de permissão, acompanhados da fonte e da data de apuração de cada dado. Quando a solicitação for ambígua, o sistema solicita esclarecimento apenas sobre o dado faltante, preservando o que já foi informado.

- **Indicadores computacionais:**
  - **Precisão da classificação de intenção:** número de solicitações corretamente classificadas dividido pelo total de solicitações do conjunto de teste. O valor-alvo é de pelo menos 85%, conforme o RNF03.
  - **Taxa de acerto na extração de entidades:** número de entidades corretamente extraídas dividido pelo total de entidades presentes no conjunto de teste. [PENDENTE — confirmar com a equipe o valor-alvo para a extração de nome do projeto, período de referência e indicador solicitado.]
  - **Taxa de correspondência entre entidade e registro:** número de consultas em que a entidade extraída foi associada ao registro correto dividido pelo total de consultas do conjunto de teste. [PENDENTE — confirmar com a equipe o valor-alvo para a correspondência entre entidades extraídas e registros do portfólio.]

### Fluxo de negócio 2: Apoio proativo ao preenchimento e acompanhamento de pendências

- **Situação atual (AS-IS):** conforme mapeado no fluxo de negócio (seção 1.6), o acompanhamento de pendências depende hoje da cobrança manual do PMO junto a cada responsável antes do prazo mensal, sem qualquer apoio automatizado ao preenchimento de documentos como termo de abertura, cronograma e mapa de benefícios.

- **Situação proposta (TO-BE):** o sistema sugere textos para os campos pendentes a partir da interação com o usuário, mantendo o controle humano sobre o que é efetivamente registrado, e notifica proativamente o PMO sobre marcos, riscos e pendências conforme filtros configurados, sem repetir alertas já enviados.

- **Indicadores computacionais:**
  - **Taxa de acerto na extração de entidades:** número de entidades corretamente extraídas da fala ou do texto dividido pelo total de entidades presentes nas interações do conjunto de teste. [PENDENTE — confirmar com a equipe o valor-alvo para a extração do campo e do conteúdo sugerido.]
  - **Precisão na detecção de alertas:** número de marcos, riscos e pendências corretamente identificados como elegíveis dividido pelo total de alertas gerados. [PENDENTE — confirmar com a equipe o valor-alvo da precisão dos alertas e os filtros que comporão o conjunto de teste.]
  - **Taxa de erro de palavras (Word Error Rate — WER):** soma de substituições, inserções e exclusões dividida pelo total de palavras do áudio de referência. O valor-alvo é de no máximo 15%, equivalente à taxa mínima de 85% de palavras reconhecidas corretamente definida no RNF06.

---

## 2.2 Requisitos Funcionais

### Visão geral dos requisitos funcionais

| ID e título | User story | Critério de aceitação | Prioridade |
|---|---|---|---|
| RF01: Receber solicitações por áudio e texto e responder em texto | Como usuário do portfólio, quero enviar minhas solicitações por áudio ou texto e receber a resposta em formato textual, para consultar o portfólio de forma flexível conforme o contexto de uso. | Ao receber uma solicitação em áudio, o sistema deve convertê-la em texto e apresentar a transcrição ao usuário antes do processamento. Ao receber uma solicitação em texto, deve processá-la diretamente. Independentemente do formato da solicitação, a resposta do agente deve ser apresentada em texto na interface. | Alta |
| RF02: Consultar dados de projetos | Como PMO, quero consultar dados de um projeto, para obter informações sobre seu status e acompanhamento sem precisar consultar manualmente os documentos do portfólio. | Ao receber uma solicitação, o sistema deve identificar a que projeto e a que dado ela se refere, consultar as fontes disponíveis e retornar os dados solicitados. Quando a solicitação não permitir identificar o projeto ou o dado, o sistema deve solicitar o dado faltante antes de consultar as fontes. Quando a solicitação não corresponder a nenhuma consulta prevista sobre o portfólio, deve informar a limitação ao usuário sem consultar as fontes. | Alta |
| RF03: Apresentar a fonte da informação | Como diretor, quero saber de qual documento e de qual data veio cada resposta, para confiar na informação antes de tomar uma decisão. | Ao apresentar qualquer dado de negócio, o sistema deve exibir o documento de origem, a referência que permite localizá-lo no repositório e a data da sua última atualização, listando todas as fontes quando a resposta combinar mais de uma. | Alta |
| RF04: Sugerir o preenchimento de documentos | Como líder de projeto, quero receber sugestões de texto para os campos pendentes dos meus documentos, para preencher o portfólio mais rápido mantendo o controle sobre o que é efetivamente gravado. | Ao solicitar apoio no preenchimento de um documento, o sistema deve apresentar no chat uma sugestão de texto para cada campo pendente, permitindo a cópia individual das sugestões e sem alterar o documento de origem. | Média |
| RF05: Notificar proativamente o usuário de pendências | Como usuário do portfólio, quero ser notificado quando tiver pendências relacionadas aos projetos que acompanho, para tomar as providências necessárias dentro do prazo. | Ao identificar uma nova pendência relacionada a um projeto acompanhado pelo usuário, o sistema deve notificá-lo automaticamente, informando o projeto e a pendência, sem exigir uma solicitação prévia do usuário. | Média |
| RF06: Atualizar o cadastro de projetos a partir de instruções do usuário | Como líder de projeto, quero atualizar os dados de um projeto ditando ou escrevendo a alteração no chat, para manter o cadastro em dia sem abrir as planilhas e os documentos do portfólio. | Ao receber uma instrução de atualização, o sistema deve identificar o projeto e os campos afetados, apresentar ao usuário os valores que serão gravados e efetivar a alteração apenas após confirmação explícita, registrando o autor e a data da alteração. | Baixa |

### 2.2.1. Modelagem estática: classes e atributos do domínio

 A modelagem estática representa as entidades do domínio de gestão de portfólio do Metrô de São Paulo sobre as quais o agente atua. O modelo parte do Portfólio, que agrupa os projetos de um exercício, e desdobra cada projeto em três eixos: os artefatos que o documentam, as pendências que dele se originam e os usuários que o acompanham.

 O quarto eixo é a hierarquia de usuários. As três personas que aparecem nas histórias da seção anterior, o diretor do RF03, o PMO do RF02 e o líder de projeto do RF04 e do RF06, correspondem a três especializações da classe Usuário. Essa correspondência de um para um entre as personas das histórias e as classes do modelo é o que amarra a modelagem estática aos requisitos funcionais.

<div align="center">
  <sub>FIGURA 2.1: modelagem estática (classes e atributos do domínio)</sub><br>
  <img src="../assets/diagrama-de-classes.svg" width="100%" alt="Diagrama de classes do domínio de gestão de portfólio"><br>
  <sup>Fonte: material produzido pelos autores (2026).</sup>
</div>

**Descrição das classes:**

| Classe | Responsabilidade | RFs atendidos |
|---|---|---|
| Portfólio | Agrupa os projetos administrados pelo PMO Corporativo em um determinado exercício, delimitando tanto o conjunto percorrido na verificação periódica de pendências quanto o alcance de acesso dos perfis de âmbito consolidado | RF02, RF05 |
| Projeto | Representa o empreendimento acompanhado pelo PMO, concentrando os dados de identificação, situação e avanço consultados pelo agente | RF02, RF03, RF04, RF05, RF06 |
| Usuário | Superclasse que reúne os atributos comuns a todos os perfis e as relações que independem do papel exercido, como o acompanhamento de projetos e o recebimento de notificações | RF01, RF05 |
| Diretor | Especialização de Usuário com alcance de supervisão sobre o portfólio consolidado, perfil da história do RF03 | RF03 |
| PMO | Especialização de Usuário que administra o portfólio, com alcance sobre todos os projetos, perfil da história do RF02 | RF02 |
| LiderProjeto | Especialização de Usuário responsável por um subconjunto de projetos, único perfil com relação de responsabilidade formal e, por consequência, com permissão de alteração | RF04, RF06 |
| Pendência | Representa um item em aberto originado por um projeto, com prazo e situação, que fundamenta a notificação proativa | RF05 |
| Artefato | Representa o documento que integra a documentação do projeto, cujos metadados sustentam a indicação de fonte das respostas | RF03, RF04, RF05 |
| CampoArtefato | Representa um campo individual de um artefato, com o valor registrado e as marcações que identificam se ele está pendente de preenchimento | RF04, RF05 |

**Atributos por classe:**

| Classe | Atributo | Tipo | Finalidade no domínio |
|---|---|---|---|
| Portfólio | `id` | int | Identificador único do portfólio |
| Portfólio | `nome` | string | Denominação do portfólio |
| Portfólio | `anoExercicio` | int | Exercício ao qual o conjunto de projetos se refere |
| Projeto | `codigo` | string | Código institucional que identifica o empreendimento |
| Projeto | `nome` | string | Denominação do empreendimento |
| Projeto | `status` | string | Situação corrente do projeto, consultada no RF03 |
| Projeto | `dataInicio` | date | Data de início da execução |
| Projeto | `dataTerminoPrevista` | date | Data prevista de conclusão, base para a apuração de prazos |
| Projeto | `percentualAvanco` | float | Grau de execução física do projeto |
| Usuário | `id` | int | Identificador único do usuário |
| Usuário | `nome` | string | Nome do profissional |
| Usuário | `email` | string | Endereço corporativo utilizado no envio das notificações |
| Pendência | `id` | int | Identificador único da pendência |
| Pendência | `tipo` | string | Natureza da pendência, como prazo, documento ou aprovação |
| Pendência | `descricao` | string | Detalhamento do item em aberto |
| Pendência | `prazo` | date | Data limite para tratamento, base da notificação do RF05 |
| Pendência | `situacao` | string | Estado corrente da pendência |
| Artefato | `id` | int | Identificador único do artefato |
| Artefato | `tipo` | string | Natureza do documento, como ata, relatório ou contrato |
| Artefato | `referencia` | string | Localizador que permite recuperar o documento no repositório em que ele estiver hospedado, exibido como fonte da informação no RF03 |
| Artefato | `data` | datetime | Data da última atualização do documento, exibida junto à fonte no RF03 |
| Artefato | `versao` | string | Versão vigente do documento |
| CampoArtefato | `id` | int | Identificador único do campo |
| CampoArtefato | `nome` | string | Rótulo do campo dentro do artefato |
| CampoArtefato | `valor` | string | Conteúdo atualmente registrado no campo |
| CampoArtefato | `obrigatorio` | boolean | Indica se o preenchimento do campo é exigido |
| CampoArtefato | `preenchido` | boolean | Indica se o campo já possui conteúdo |

 A combinação dos atributos `obrigatorio` e `preenchido` da classe CampoArtefato é o que permite determinar quais campos de um artefato estão pendentes, insumo direto da sugestão de preenchimento prevista no RF04. Da mesma forma, os atributos `referencia` e `data` da classe Artefato são os que sustentam a exigência do RF03 de apresentar a origem e a data de cada informação devolvida pelo agente. Os dois recebem esses nomes para corresponder aos parâmetros homônimos que trafegam nas mensagens do cenário 1, de modo que o dado armazenado e o dado exibido sejam identificáveis como o mesmo ao longo das duas modelagens.

 As três especializações de Usuário não declaram atributos próprios. A diferença entre elas não é de dado armazenado, e sim de alcance de acesso, que é uma característica relacional e por isso está expressa nas associações descritas a seguir.

**Relacionamentos:**

| Origem | Relacionamento | Destino | Cardinalidade | Tipo |
|---|---|---|---|---|
| Portfólio | contém | Projeto | 1 para 1..* | Agregação |
| Projeto | compõe | Artefato | 1 para 0..* | Composição |
| Artefato | compõe | CampoArtefato | 1 para 1..* | Composição |
| Projeto | origina | Pendência | 1 para 0..* | Composição |
| Usuário | acompanha | Projeto | 0..* para 0..* | Associação |
| Pendência | notifica | Usuário | 0..* para 0..* | Associação |
| Diretor | supervisiona | Portfólio | 0..* para 1 | Associação |
| PMO | administra | Portfólio | 0..* para 1 | Associação |
| LiderProjeto | lidera | Projeto | 1 para 1..* | Associação |
| Diretor, PMO e LiderProjeto | especializa | Usuário | Não se aplica | Generalização |

 A distinção entre agregação e composição é intencional. O Portfólio agrega Projetos porque um projeto mantém identidade própria e pode ser reagrupado em outro exercício sem deixar de existir. Já o Artefato compõe o Projeto, o CampoArtefato compõe o Artefato e a Pendência é composta pelo Projeto, porque nenhum dos três faz sentido isoladamente: excluído o projeto, seus artefatos perdem o objeto que documentam e suas pendências perdem o objeto a que se referem.

 Os papéis do usuário são modelados por herança e não por um atributo de tipo. A razão é que cada perfil possui alcance de acesso distinto, e alcance de acesso é uma relação, não uma propriedade. É por isso que a distinção entre os três aparece nas associações e não em atributos: `Diretor` e `PMO` se ligam ao `Portfólio`, o que expressa alcance sobre o conjunto consolidado, enquanto `LiderProjeto` se liga diretamente a `Projeto`, o que restringe seu alcance aos empreendimentos sob sua responsabilidade. A granularidade da associação é a granularidade do acesso.

 A cardinalidade de `lidera`, de 1 para 1..*, reforça essa leitura. O `1` do lado do líder estabelece que cada projeto possui um único responsável, e é essa unicidade que delimita o conjunto ao qual o perfil tem acesso privilegiado e permissão de alteração, prevista no RF06.

 A associação `acompanha`, com cardinalidade de muitos para muitos entre Usuário e Projeto, é o que viabiliza a personalização da notificação prevista no RF05. Ela é deliberadamente distinta de `lidera`: acompanhar exprime interesse e define quem recebe notificação, ao passo que liderar exprime responsabilidade formal e define quem pode alterar. Um líder normalmente acompanha os projetos que lidera, mas as duas relações respondem a perguntas diferentes e por isso coexistem no modelo.

 A modelagem declara apenas classes e atributos, sem operações, por representar a estrutura de dados do domínio de portfólio. O comportamento do agente está representado na modelagem dinâmica desta seção e nos componentes da solução técnica descritos na seção 2.4.

### 2.2.2. Modelagem dinâmica: cenários e diagramas de sequência

 A modelagem dinâmica descreve como as classes declaradas na modelagem estática são percorridas durante a execução das solicitações previstas nos requisitos funcionais. Foram definidos três cenários. Os dois primeiros são iniciados pelo usuário em linguagem natural e compartilham a mesma cadeia de tratamento da entrada, enquanto o terceiro é iniciado pelo próprio sistema, sem interação conversacional.

| Cenário | Descrição | Iniciador | RFs cobertos |
|---|---|---|---|
| Cenário 1 | Consultar informações do projeto | Usuário | RF01, RF02, RF03 |
| Cenário 2 | Sugerir preenchimento de documento | Usuário | RF04 |
| Cenário 3 | Notificar pendências | Agendador (sistema) | RF05 |

 Os três cenários representam o fluxo principal de cada requisito, sem o tratamento de exceções, que fica previsto para a sprint seguinte. O RF06, de prioridade baixa e viabilidade ainda em avaliação, não recebeu cenário nesta sprint, conforme registrado na seção 2.2.3.

#### Linhas de vida adotadas

 Os três diagramas utilizam um conjunto comum de linhas de vida, de modo que a leitura de um cenário se aproveite do vocabulário do anterior. A tabela a seguir relaciona cada linha de vida ao seu papel e à sua correspondência na modelagem estática.

| Linha de vida | Papel nos cenários | Correspondência no modelo estático |
|---|---|---|
| Usuário | Ator que inicia a interação nos cenários 1 e 2 e recebe a notificação no cenário 3 | Classe `Usuário` e suas especializações |
| `: InterfaceDeChat` | Recebe solicitações por texto ou áudio e apresenta as respostas em formato textual | Componente de interface (seção 2.4) |
| `: ServicoDeVoz` | Converte áudio em texto na entrada (exclusivo do cenário 1) | Componente de serviços (seção 2.4) |
| `: PipelinePLN` | Conduz o tratamento da solicitação, extrai as entidades do texto e aciona os demais componentes | Componente de lógica de negócio (seção 2.4) |
| `: Intencao` | Detém o catálogo de intenções e classifica o texto contra ele, devolvendo a intenção reconhecida e os parâmetros que ela exige | Componente de lógica de negócio (seção 2.4) |
| `: Agente` | Orquestra a execução da intenção, consulta as fontes e compõe a resposta | Componente de lógica de negócio (seção 2.4) |
| `: FonteDeDados` | Encapsula o acesso às entidades persistidas do domínio | `Portfólio`, `Projeto`, `Artefato`, `CampoArtefato`, `Pendência`, `Usuário` |
| `: ServicoDeNotificacao` | Entrega a notificação ao usuário pelo canal corporativo (exclusivo do cenário 3) | Componente de serviços (seção 2.4) |
| `: Agendador` | Dispara a verificação periódica de pendências (exclusivo do cenário 3) | Componente de lógica de negócio (seção 2.4) |

 As linhas de vida de componente adotam a sintaxe UML de instância anônima, no formato `: Classe`, enquanto o Usuário é identificado pelo nome do papel, por ser um ator e não uma instância de componente.

**Nota:** apenas a linha de vida Usuário e a linha de vida `: FonteDeDados` possuem contrapartida direta na modelagem estática. As demais representam componentes da solução técnica, e não entidades do domínio. Isso vale inclusive para o `: Intencao`: intenção é conceito da camada de processamento de linguagem natural, que existiria de forma diferente se a interface não fosse conversacional, ao contrário de Projeto ou Artefato, que existem na gestão de portfólio independentemente da solução adotada. A separação entre os dois planos é deliberada e está detalhada na seção 2.4.

#### Convenções de notação adotadas

 Os três diagramas empregam três tipos de mensagem, distinguidos graficamente e aplicados de forma uniforme. A tabela a seguir registra a convenção, necessária para a leitura correta dos fluxos apresentados adiante.

| Tipo de mensagem | Traço | Ponta da seta | Rótulo | Quando é usada |
|---|---|---|---|---|
| Síncrona | Linha contínua | Cheia | Assinatura com parênteses | Chamada em que o remetente aguarda a conclusão, como `buscarDados(projeto, idUsuario)` |
| Assíncrona | Linha contínua | Vazada | Assinatura com parênteses | Envio em que o remetente não aguarda retorno, como `executarIntencao(intencao, entidades, idUsuario)` e a entrega da notificação no cenário 3 |
| Retorno | Linha tracejada | Vazada | Dados devolvidos, sem parênteses | Resposta a uma chamada anterior, como `camposPendentes, contextoDoProjeto` |

 A distinção importa para a leitura das mensagens dirigidas ao ator. Nos cenários 1 e 2, o que chega ao Usuário é sempre um retorno da solicitação que ele mesmo iniciou, representado por linha tracejada com os dados devolvidos. No cenário 3, em que o Usuário nunca formula uma solicitação, a notificação é um envio assíncrono genuíno e por isso aparece como linha contínua com ponta vazada.

 A passagem do `: PipelinePLN` ao `: Agente` é assíncrona nos cenários 1 e 2 porque o pipeline entrega a intenção reconhecida e não permanece bloqueado à espera do resultado. Quem devolve a resposta ao usuário é o `: Agente`, por meio da `: InterfaceDeChat`, e não o pipeline que originou a chamada. Já as consultas à `: FonteDeDados` são síncronas, porque o `: Agente` depende do dado retornado para compor a resposta.

#### Cenário 1: consultar informações do projeto

&emsp; O cenário representa o fluxo mais frequente do agente, no qual o usuário formula uma pergunta sobre um projeto e recebe a resposta acompanhada da indicação de origem. É o cenário de maior alcance, por percorrer a cadeia completa de consulta, do recebimento da solicitação em linguagem natural (RF01), passando pela consulta aos dados do projeto (RF02), até a devolução da resposta fundamentada com a indicação da fonte (RF03). O diagrama apresenta somente o fluxo principal; a recusa de pedidos fora do catálogo de intenções e o ciclo de esclarecimento diante de parâmetros faltantes, ambos previstos pelo RF02, não estão representados neste cenário.

<div align="center">
  <sub>FIGURA 2.2: diagrama de sequência do cenário 1 (consultar informações do projeto)</sub><br>
  <img src="../assets/1.svg" width="100%" alt="Diagrama de sequência do cenário de consulta de informações do projeto"><br>
  <sup>Fonte: material produzido pelos autores (2026).</sup>
</div>

**Fluxo do cenário:**

| # | Mensagem | Tipo | Origem | Destino | Requisito |
|---|---|---|---|---|---|
| 1 | `enviarAudio(audio)` | Síncrona | Usuário | `: InterfaceDeChat` | RF01 |
| 2 | `transcrever(audio)` | Síncrona | `: InterfaceDeChat` | `: ServicoDeVoz` | RF01 |
| 3 | `textoTranscrito` | Retorno | `: ServicoDeVoz` | `: InterfaceDeChat` | RF01 |
| 4 | `textoTranscrito` | Retorno | `: InterfaceDeChat` | Usuário | RF01 |
| 5 | `enviarSolicitacao(texto)` | Síncrona | Usuário | `: InterfaceDeChat` | RF01 |
| 6 | `processarSolicitacao(texto, idUsuario)` | Síncrona | `: InterfaceDeChat` | `: PipelinePLN` | RF02 |
| 7 | `classificarIntencao(texto)` | Síncrona | `: PipelinePLN` | `: Intencao` | RF02 |
| 8 | `intencaoIdentificada, parametrosObrigatorios` | Retorno | `: Intencao` | `: PipelinePLN` | RF02 |
| 9 | `extrairEntidades(texto, parametrosObrigatorios)` | Síncrona | `: PipelinePLN` | `: PipelinePLN` | RF02 |
| 10 | `log()` | Síncrona | `: PipelinePLN` | `: PipelinePLN` | Rastreabilidade |
| 11 | `executarIntencao(intencao, entidades, idUsuario)` | Assíncrona | `: PipelinePLN` | `: Agente` | RF02 |
| 12 | `buscarDados(projeto, idUsuario)` | Síncrona | `: Agente` | `: FonteDeDados` | RF02 |
| 13 | `dados, caminho` | Retorno | `: FonteDeDados` | `: Agente` | RF02, RF03 |
| 14 | `exibirResposta(resposta, referencia, data)` | Síncrona | `: Agente` | `: InterfaceDeChat` | RF03 |
| 15 | `resposta, referencia, data` | Retorno | `: InterfaceDeChat` | Usuário | RF01, RF03 |

**Fragmentos de interação:**

| Fragmento | Condição de guarda | Comportamento | Requisito |
|---|---|---|---|
| `alt` de entrada | `[canal de entrada em áudio]` | Passos 1 a 4: a solicitação chega em áudio, o `: ServicoDeVoz` a transcreve e a transcrição é devolvida ao usuário para conferência | RF01 |
| `alt` de entrada | `[canal de entrada em texto]` | Passo 5: a solicitação já chega em texto e segue direto para o tratamento | RF01 |

&emsp; O fragmento `alt` aplica-se somente à entrada, distinguindo as solicitações recebidas em áudio das recebidas em texto. Após a transcrição do áudio, ambas seguem pelo mesmo fluxo de processamento e resultam em uma resposta textual, independentemente do formato da solicitação original, conforme definido pelo RF01.

 O passo 4 devolve a transcrição ao próprio usuário antes de a solicitação seguir para o tratamento. Esse retorno atende à cláusula de conferência do RF01 e é o que permite ao usuário perceber um erro de transcrição antes de receber uma resposta construída sobre a interpretação errada.

 A classificação da intenção não é uma operação interna do `: PipelinePLN`, e sim uma chamada ao `: Intencao`, que detém o catálogo. A escolha segue o princípio de atribuir a responsabilidade a quem possui a informação necessária para cumpri-la: só quem conhece as intenções catalogadas consegue dizer a qual delas o texto corresponde. O retorno do passo 8 traz duas informações, a intenção reconhecida e os parâmetros que ela exige, e é o segundo deles que orienta a extração de entidades do passo 9.

&emsp; O passo 13 devolve, além dos dados do projeto, o caminho do artefato de origem. Esse retorno conjunto é o que permite ao passo 15 entregar conteúdo, referência e data em uma única exibição textual, atendendo ao RF03 sem uma consulta adicional às fontes.

#### Cenário 2: sugerir preenchimento de documento

 O cenário representa o apoio à documentação do portfólio, no qual o usuário solicita ajuda para preencher um artefato e recebe uma sugestão de texto para cada campo pendente. Reaproveita integralmente a cadeia de tratamento da entrada do cenário 1 (RF01 e RF02) e diverge a partir da execução da intenção, quando o agente passa a operar sobre os campos do artefato em vez dos dados de acompanhamento do projeto.

<div align="center">
  <sub>FIGURA 2.3: diagrama de sequência do cenário 2 (sugerir preenchimento de documento)</sub><br>
  <img src="../assets/sequencia-2.svg" width="100%" alt="Diagrama de sequência do cenário de sugestão de preenchimento de documento"><br>
  <sup>Fonte: material produzido pelos autores (2026).</sup>
</div>

**Fluxo do cenário:**

| # | Mensagem | Tipo | Origem | Destino | Requisito |
|---|---|---|---|---|---|
| 1 | `enviarSolicitacao(texto)` | Síncrona | Usuário | `: InterfaceDeChat` | RF04 |
| 2 | `processarSolicitacao(texto, idUsuario)` | Síncrona | `: InterfaceDeChat` | `: PipelinePLN` | RF04 |
| 3 | `classificarIntencao(texto)` | Síncrona | `: PipelinePLN` | `: Intencao` | RF04 |
| 4 | `intencaoIdentificada, parametrosObrigatorios` | Retorno | `: Intencao` | `: PipelinePLN` | RF04 |
| 5 | `extrairEntidades(texto, parametrosObrigatorios)` | Síncrona | `: PipelinePLN` | `: PipelinePLN` | RF04 |
| 6 | `executarIntencao(intencao, entidades, idUsuario)` | Assíncrona | `: PipelinePLN` | `: Agente` | RF04 |
| 7 | `obterCamposPendentes(artefato, projeto, idUsuario)` | Síncrona | `: Agente` | `: FonteDeDados` | RF04 |
| 8 | `camposPendentes, contextoDoProjeto` | Retorno | `: FonteDeDados` | `: Agente` | RF04 |
| 9 | `gerarSugestao(campo, contextoDoProjeto)` | Síncrona | `: Agente` | `: Agente` | RF04 |
| 10 | `enviarSugestoes(sugestoesPorCampo)` | Síncrona | `: Agente` | `: InterfaceDeChat` | RF04 |
| 11 | `sugestoes` | Retorno | `: InterfaceDeChat` | Usuário | RF04 |
| 12 | `informarArtefatoCompleto()` | Síncrona | `: Agente` | `: InterfaceDeChat` | RF04 |
| 13 | `artefatoCompleto` | Retorno | `: InterfaceDeChat` | Usuário | RF04 |

**Fragmentos de interação:**

| Fragmento | Condição de guarda | Comportamento | Requisito |
|---|---|---|---|
| `alt` | `[há campos pendentes]` | Passos 9 a 11: o `: Agente` gera as sugestões e a `: InterfaceDeChat` as devolve ao usuário | RF04 |
| `alt` | `[nenhum campo pendente]` | Passos 12 e 13: o `: Agente` emite `informarArtefatoCompleto()` e a `: InterfaceDeChat` devolve `artefatoCompleto`, sem gerar sugestões | RF04 |
| `loop` | `[para cada campo pendente]` | Passo 9: a sugestão é gerada campo a campo, o que garante a granularidade exigida pelo critério de aceitação do RF04 | RF04 |

 Os passos 1 a 6 reproduzem literalmente a cadeia de tratamento de entrada do cenário 1, incluindo a consulta ao catálogo de intenções e a extração de entidades orientada pelos parâmetros obrigatórios. Essa repetição é intencional e demonstra que o mesmo mecanismo de interpretação serve a requisitos distintos: o que muda é apenas a intenção reconhecida e, por consequência, a ação executada pelo `: Agente` a partir do passo 7.

 O `loop` envolve somente a geração da sugestão, e não o envio. A distinção importa: as sugestões são produzidas campo a campo, atendendo à granularidade exigida pelo RF04, mas entregues em uma única mensagem ao final, o que evita fragmentar a conversa em uma mensagem por campo.

 A mensagem `obterCamposPendentes` do passo 7 é a tradução direta da combinação dos atributos `obrigatorio` e `preenchido` da classe `CampoArtefato`, descrita na modelagem estática. É essa combinação que define o conjunto sobre o qual o fragmento `loop` itera.

 O `: Agente` devolve as sugestões ao usuário pela `: InterfaceDeChat` e não emite qualquer mensagem de escrita à `: FonteDeDados`. Essa ausência é deliberada e representa graficamente a restrição do RF04 de não alterar o documento de origem, mantendo com o usuário a decisão sobre o registro. O RF06 segue a mesma restrição no MVP e apresenta apenas uma proposta de atualização copiável.

#### Cenário 3: notificar pendências

 O cenário representa o único comportamento proativo da solução. Diferentemente dos anteriores, não é iniciado por uma solicitação em linguagem natural, mas por um agendador que dispara a verificação periódica do portfólio. O usuário aparece apenas ao final da sequência, como destinatário da notificação.

<div align="center">
  <sub>FIGURA 2.4: diagrama de sequência do cenário 3 (notificar pendências)</sub><br>
  <img src="../assets/sequencia-3.svg" width="100%" alt="Diagrama de sequência do cenário de notificação proativa de pendências"><br>
  <sup>Fonte: material produzido pelos autores (2026).</sup>
</div>

**Fluxo do cenário:**

| # | Mensagem | Tipo | Origem | Destino | Requisito |
|---|---|---|---|---|---|
| 1 | `executarVerificacaoPeriodica()` | Assíncrona | `: Agendador` | `: Agente` | RF05 |
| 2 | `consultarProjetos(prazos, campos, situacoes)` | Síncrona | `: Agente` | `: FonteDeDados` | RF05 |
| 3 | `projetos, artefatos` | Retorno | `: FonteDeDados` | `: Agente` | RF05 |
| 4 | `identificarPendencias(projetos)` | Síncrona | `: Agente` | `: Agente` | RF05 |
| 5 | `obterUsuariosQueAcompanham(projeto)` | Síncrona | `: Agente` | `: FonteDeDados` | RF05 |
| 6 | `usuariosDestino` | Retorno | `: FonteDeDados` | `: Agente` | RF05 |
| 7 | `enviarNotificacao(pendencia, usuariosDestino)` | Síncrona | `: Agente` | `: ServicoDeNotificacao` | RF05 |
| 8 | `notificar(projeto, pendencia)` | Assíncrona | `: ServicoDeNotificacao` | Usuário | RF05 |

**Fragmentos de interação:**

| Fragmento | Condição de guarda | Comportamento | Requisito |
|---|---|---|---|
| `opt` | `[há pendências identificadas]` | Quando a verificação não encontra pendências, a sequência se encerra sem notificação, o que evita comunicação desnecessária ao usuário | RF05 |
| `loop` | `[para cada pendência identificada]` | O destinatário é resolvido por pendência, de modo que cada usuário receba apenas o que se refere aos projetos que acompanha | RF05 |

 A mensagem `obterUsuariosQueAcompanham` do passo 5 percorre a associação `acompanha` entre `Usuário` e `Projeto`, de cardinalidade muitos para muitos. É esse relacionamento que dispensa uma configuração paralela de assinatura de notificações, conforme observado na modelagem estática.

 A ausência da `: InterfaceDeChat` e do `: PipelinePLN` entre as linhas de vida é o traço que distingue este cenário dos demais. Ela expressa graficamente o critério de aceitação do RF05, segundo o qual a notificação ocorre sem exigir uma solicitação prévia do usuário.

 É também o único cenário em que uma mensagem assíncrona chega ao ator. O disparo do `: Agendador` e a entrega pelo `: ServicoDeNotificacao` não bloqueiam o remetente à espera de resposta, ao contrário das consultas à `: FonteDeDados`, que são síncronas porque o `: Agente` depende do resultado para prosseguir. A notação evita a leitura equivocada de que a notificação seria o retorno de alguma solicitação do usuário, que neste cenário não existe.

### 2.2.3. Rastreabilidade entre requisitos, cenários e classes

 A rastreabilidade a seguir demonstra que cada requisito funcional está representado em ao menos um cenário e que cada cenário opera sobre classes efetivamente declaradas na modelagem estática. A verificação percorre os três eixos do artefato, ou seja, as histórias de usuário da seção 2.2, os diagramas de sequência e o diagrama de classes.

**Requisitos, cenários e classes:**

| RF | Persona da história | Cenário | Classes envolvidas | Atributos e relacionamentos determinantes | Mensagem que evidencia o atendimento |
|---|---|---|---|---|---|
| RF01: Receber solicitações por áudio e texto e responder em texto | Usuário do portfólio | Cenário 1 | `Usuário` | `id` | `enviarAudio(audio)`, `transcrever(audio)`, retorno `textoTranscrito` e apresentação da resposta em formato textual, independentemente do formato da solicitação |
| RF02: Consultar dados de projetos | PMO | Cenário 1 | `PMO`, `Portfólio`, `Projeto` | `codigo`, `status`, `percentualAvanco`, `dataTerminoPrevista`, relacionamento `administra` | `classificarIntencao(texto)`, `extrairEntidades(texto, parametrosObrigatorios)`, `executarIntencao(intencao, entidades, idUsuario)` e `buscarDados(projeto, idUsuario)` |
| RF03: Apresentar a fonte da informação | Diretor | Cenário 1 | `Diretor`, `Artefato`, `Projeto` | `referencia`, `data`, relacionamentos `compõe` e `supervisiona` | Retorno `dados, caminho`, chamada `exibirResposta(resposta, referencia, data)` e retorno textual `resposta, referencia, data` |
| RF04: Sugerir o preenchimento de documentos | Líder de projeto | Cenário 2 | `LiderProjeto`, `Artefato`, `CampoArtefato`, `Projeto` | `obrigatorio`, `preenchido`, `nome`, `valor`, relacionamentos `compõe` e `lidera` | `obterCamposPendentes(artefato, projeto, idUsuario)`, `gerarSugestao(campo, contextoDoProjeto)` e `enviarSugestoes(sugestoesPorCampo)` |
| RF05: Notificar proativamente o usuário de pendências | Usuário do portfólio | Cenário 3 | `Portfólio`, `Projeto`, `Artefato`, `CampoArtefato`, `Pendência`, `Usuário` | `prazo`, `situacao`, `preenchido`, `email`, relacionamentos `contém`, `origina`, `acompanha` e `notifica` | `consultarProjetos(prazos, campos, situacoes)`, `identificarPendencias(projetos)`, `obterUsuariosQueAcompanham(projeto)` e `enviarNotificacao(pendencia, usuariosDestino)` |
| RF06: Sugerir atualização do cadastro de projetos a partir de instruções do usuário | Líder de projeto | Variação do cenário 2 | `LiderProjeto`, `Projeto` | Relacionamento `lidera`, que delimita os projetos sobre os quais o líder pode receber sugestões | Mesmo fluxo sugestivo do cenário 2, sem escrita nas fontes |

 A coluna de persona evidencia a amarração direta entre as histórias de usuário e a modelagem estática. As três personas que aparecem nas histórias correspondem às três especializações de `Usuário`, de modo que cada requisito escrito na voz de um papel específico tem, no modelo, a classe correspondente entre as classes envolvidas.

**Cobertura das classes pelos cenários:**

| Classe | Cenário 1 | Cenário 2 | Cenário 3 | RFs atendidos |
|---|---|---|---|---|
| `Portfólio` | Sim | Não | Sim | RF02, RF05 |
| `Projeto` | Sim | Sim | Sim | RF02, RF03, RF04, RF05, RF06 |
| `Usuário` | Sim | Sim | Sim | RF01, RF05 |
| `Diretor` | Sim | Não | Não | RF03 |
| `PMO` | Sim | Não | Não | RF02 |
| `LiderProjeto` | Não | Sim | Não | RF04, RF06 |
| `Pendência` | Não | Não | Sim | RF05 |
| `Artefato` | Sim | Sim | Sim | RF03, RF04, RF05 |
| `CampoArtefato` | Não | Sim | Sim | RF04, RF05 |

 A verificação de cobertura confirma a coerência entre as três representações. Cinco dos seis requisitos funcionais aparecem em ao menos um cenário, e todas as nove classes do modelo estático são exercitadas por ao menos um cenário, o que indica que não há classe declarada sem uso previsto.

 A classe `Projeto` figura nos três cenários e concentra o maior número de requisitos, o que a confirma como entidade central do domínio, conforme antecipado na modelagem estática. Nas extremidades, `Pendência` se restringe ao cenário 3, por ser a entidade produzida pela verificação periódica, e `CampoArtefato` só aparece a partir do cenário 2, por ser a granularidade exigida exclusivamente pela sugestão de preenchimento.

 As especializações de `Usuário` distribuem-se conforme o perfil de cada história. `Diretor` e `PMO` aparecem no cenário 1 porque as histórias do RF02 e do RF03 são escritas nas suas vozes, e `LiderProjeto` aparece no cenário 2 pelo mesmo motivo em relação ao RF04. A superclasse `Usuário` figura nos três cenários por concentrar os atributos e as relações que independem de papel.

 As classes `Artefato` e `CampoArtefato` participam de mais de um cenário por cumprirem papéis distintos em cada um. No cenário 1, o `Artefato` fornece os metadados de origem exigidos pelo RF03. No cenário 2, a dupla sustenta a identificação dos campos pendentes exigida pelo RF04. No cenário 3, ambas são percorridas pelo critério `campos` da mensagem `consultarProjetos`, que permite classificar como pendência um artefato com campos obrigatórios ainda não preenchidos.

**Delimitações desta sprint:**

 Duas lacunas são registradas de forma explícita, por decisão do grupo e não por omissão.

O **RF06 não recebeu diagrama de sequência próprio** porque possui prioridade baixa e representa uma variação do apoio ao preenchimento modelado no cenário 2. No MVP, ele apenas identifica os campos mencionados e apresenta uma proposta copiável, sem gravar dados nas fontes. Uma eventual escrita com confirmação explícita pertence à evolução futura registrada na seção 1.7 e exigirá modelagem específica quando sua viabilidade for confirmada.

 Os **cenários representam apenas o fluxo principal**. A cláusula do RF02 que determina informar a limitação ao usuário quando a solicitação não corresponder a nenhuma consulta prevista não está representada graficamente, assim como não estão os tratamentos de falha de transcrição ou de indisponibilidade das fontes. A opção por diagramas de caminho feliz privilegia a legibilidade nesta primeira especificação, e os desvios entram na sprint seguinte.

 Registra-se ainda que a automensagem `log()` do cenário 1 não decorre de nenhum requisito funcional. Ela sustenta a rastreabilidade das interpretações feitas pelo agente, que é atributo de qualidade e será formalizada como requisito não funcional de auditabilidade na seção 2.3.


---

## 2.3 Requisitos Não Funcionais

### Visão geral dos requisitos não funcionais

Os valores-alvo ainda não acordados estão identificados como **a validar com o parceiro**. A validação deverá definir esses valores antes da homologação, sem alterar a métrica nem o procedimento de teste descritos.

| ID e título                                                | História de usuário                                                                                                                                               | Business Driver relacionado                               | Característica de qualidade        | Critério mensurável e verificável                                                                                                                                                                                                                                                           | Forma de validação ou teste                                                                                                                                     |
| ---------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------- | ---------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **RNF01 — Desempenho das consultas**                       | Como usuário do agente, quero receber rapidamente as respostas das minhas consultas para obter informações dos projetos sem comprometer minha tomada de decisão.  | Eficiência e agilidade no acesso às informações           | Desempenho                         | Pelo menos 80% das consultas textuais devem apresentar uma resposta em até 15 segundos, desconsiderando indisponibilidades dos serviços externos.                                                                                                                                           | Executar conjunto representativo de consultas e medir o tempo de resposta e taxa de sucesso.                                                                    |
| **RNF02 — Controle de acesso às informações**              | Como diretor, quero que o acesso às informações seja limitado de acordo com o perfil de cada usuário para preservar a confidencialidade dos projetos.              | Confidencialidade e segurança da informação               | Segurança e controle de acesso     | O sistema deve autenticar o usuário e validar suas permissões antes de responder às consultas. Nos testes de autorização, pelo menos 80% das tentativas de acesso a informações não permitidas devem ser bloqueadas em até 15 segundos.                                                     | Executar testes de autorização com diferentes perfis e verificar bloqueio de acessos não autorizados dentro do tempo limite.                                    |
| **RNF03 — Precisão na identificação de intenções**         | Como usuário do agente, quero que minhas perguntas sejam interpretadas corretamente para receber respostas coerentes com as informações solicitadas.              | Precisão e confiabilidade das consultas                   | Precisão e confiabilidade          | O componente de processamento de linguagem natural deve atingir precisão mínima de 85% na classificação das intenções em um conjunto de testes previamente validado pela equipe e pelo parceiro.                                                                                            | Avaliar o classificador em conjunto de teste rotulado, separado dos dados de treinamento.                                                                       |
| **RNF04 — Rastreabilidade das consultas**                  | Como responsável pela gestão dos projetos, quero que as consultas e respostas sejam registradas para permitir a auditoria das informações fornecidas pelo agente. | Rastreabilidade e transparência                           | Auditabilidade e rastreabilidade   | O sistema deve registrar o identificador do usuário, a data e hora, o canal utilizado, a intenção identificada, as fontes consultadas e o resultado da solicitação. Os registros devem ser protegidos contra alterações por usuários comuns.                                                | Verificar se todos os elementos obrigatórios estão presentes nos logs de auditoria e se são imutáveis.                                                          |
| **RNF05 — Interoperabilidade entre aplicações clientes**   | Como usuário, quero acessar o agente a partir de diferentes aplicações para consultar os projetos pelo ponto de acesso mais adequado à minha rotina.              | Interoperabilidade e acessibilidade                       | Flexibilidade e integração         | O núcleo do agente deve expor suas funcionalidades por meio de interfaces padronizadas, permitindo que pelo menos duas aplicações clientes distintas o consumam sem duplicação das regras de negócio.                                                                                       | Acionar as funcionalidades principais a partir de duas aplicações clientes distintas e verificar que o resultado é idêntico nas duas.                           |
| **RNF06 — Qualidade da transcrição de áudio**              | Como usuário, quero realizar consultas por voz e ter minha fala convertida corretamente em texto para interagir com o agente de maneira natural.                  | Acessibilidade, eficiência e uso de linguagem natural     | Acurácia em reconhecimento de fala | O componente de conversão de áudio em texto deve alcançar uma taxa mínima de 85% de palavras reconhecidas corretamente em um conjunto de áudios representativo do contexto do projeto.                                                                                                     | Testar com áudios do vocabulário de projetos e medir a taxa de erro de palavras (WER) contra transcrições de referência.                                        |
| **RNF07 — Disponibilidade da solução**                     | Como usuário, quero que o agente esteja disponível durante o período de trabalho para realizar consultas sempre que necessário.                                   | Continuidade operacional e eficiência                     | Confiabilidade e disponibilidade   | A solução deve apresentar disponibilidade mínima de 99% durante o horário de operação definido pelo parceiro, desconsiderando manutenções previamente comunicadas.                                                                                                                          | Monitorar uptime da aplicação e infraestrutura durante período de operação.                                                                                     |
| **RNF08 — Usabilidade das respostas**                      | Como usuário, quero receber respostas claras e organizadas para compreender rapidamente a situação dos projetos, independentemente do meu conhecimento técnico.   | Transparência e apoio à tomada de decisão                 | Usabilidade e compreensibilidade   | Em testes com representantes das personas, pelo menos 80% dos participantes devem compreender a resposta e identificar a informação solicitada sem auxílio externo.                                                                                                                         | Conduzir testes de usabilidade com representantes das personas e validar compreensão.                                                                           |
| **RNF09 — Auditabilidade das interações**  | Como responsável pela gestão e governança da solução, quero consultar registros das interações realizadas pelo agente para acompanhar seu funcionamento, investigar falhas e verificar a origem das respostas apresentadas. | Rastreabilidade e transparência | Auditabilidade | O sistema deve registrar eventos relevantes das interações realizadas com o agente, permitindo rastrear consultas, respostas, fontes utilizadas, solicitações de esclarecimento, notificações e falhas ocorridas durante o processamento. Os registros mínimos são: identificador único do evento, data e horário, tipo de interação, canal utilizado, requisito ou operação executada, resultado da operação, fonte consultada (quando aplicável), código ou categoria do erro (quando aplicável), identificador técnico do usuário (respeitando as regras de privacidade e acesso) e tempo de processamento. **PENDENTE DE VALIDAÇÃO DA EQUIPE:** definir o período de retenção dos registros de auditoria e os perfis autorizados a consultá-los. | (1) Dado que uma consulta seja processada, quando o processamento for finalizado, então o sistema deve registrar a data, o canal, a operação e as fontes utilizadas. (2) Dado que ocorra uma falha, quando o erro for tratado, então o sistema deve registrar a categoria do erro sem armazenar senhas, tokens ou dados sensíveis. (3) Dado que um usuário sem permissão tente acessar os registros, quando a solicitação for realizada, então o sistema deve negar o acesso. Forma de verificação: inspeção dos registros gerados, testes de acesso autorizado e não autorizado, verificação da ausência de dados sensíveis. |
| **RNF10 — Escalabilidade do agente**                       | Como administrador da solução, quero que o agente seja capaz de processar aumentos de volume de consultas e dados sem degradação significativa de desempenho.     | Continuidade operacional e sustentabilidade técnica       | Escalabilidade e performance       | O agente deve suportar aumento de até 10x no volume de consultas simultâneas mantendo a latência em até 20 segundos para 95% das requisições; o pipeline deve processar datasets sinteticamente maiores sem aumento proporcional de memória.                                                | Realizar testes de carga progressivos, aumentando gradualmente o volume de consultas e medir latência, throughput e uso de recursos.                            |
| **RNF11 — Explicabilidade das sugestões de preenchimento** | Como responsável por documentos, quero compreender as razões pelas quais o agente sugeriu determinados valores ou conteúdos.                                      | Transparência e confiabilidade dos dados sugeridos        | Explicabilidade e rastreabilidade  | Cada sugestão de preenchimento deve indicar explicitamente a fonte dos dados utilizados e o raciocínio por trás da sugestão; pelo menos 85% das sugestões devem ser acompanhadas de referências válidas e justificativa compreensível.                                                      | Verificar que todas as sugestões apresentadas incluem fontes identificáveis e justificativas claras; validar compreensão junto aos usuários.                    |

### Tabela de rastreabilidade entre requisitos não funcionais e funcionais

| RNF                                            | RF relacionado         | Relação de rastreabilidade                                                                                                |
| ---------------------------------------------- | ---------------------- | ------------------------------------------------------------------------------------------------------------------------- |
| RNF01 — Desempenho das consultas               | RF02                               | Qualifica o tempo de resposta das consultas de dados de projetos, sem alterar o comportamento especificado no requisito.                                                                                       |
| RNF02 — Controle de acesso às informações      | RF02, RF03, RF04, RF05, RF06       | Assegura que consultas, indicações de fonte, sugestões, notificações e alterações de cadastro respeitem o alcance de cada perfil, materializado nas associações `supervisiona`, `administra` e `lidera`.       |
| RNF03 — Precisão na identificação de intenções | RF02, RF04, RF06                   | Mede a qualidade da classificação executada pelo `: Intencao` nos cenários 1 e 2, que é o passo comum aos requisitos iniciados por linguagem natural.                                                          |
| RNF04 — Rastreabilidade das consultas          | RF01, RF02, RF03, RF04, RF05, RF06 | Mede o registro e a imutabilidade da auditoria de todas as interações, comportamento representado pela automensagem `log()` do cenário 1.                                                                      |
| RNF05 — Interoperabilidade entre aplicações clientes | RF01, RF02, RF04, RF05       | Assegura que as funcionalidades operem de maneira idêntica em qualquer aplicação que consuma o agente. Trata do ponto de acesso, enquanto o RF01 define as modalidades de entrada e estabelece a resposta em formato textual.                 |
| RNF06 — Qualidade da transcrição de áudio      | RF01                               | Qualifica a conversão de áudio em texto executada pelo `: ServicoDeVoz` no cenário 1, da qual dependem todas as solicitações formuladas por voz.                                                               |
| RNF07 — Disponibilidade da solução             | RF01, RF02, RF03, RF04, RF05, RF06 | Assegura que o agente esteja disponível durante o horário de operação, condição para a execução de qualquer requisito funcional.                                                                               |
| RNF08 — Usabilidade das respostas              | RF02, RF03                         | Mede a clareza e a compreensibilidade da resposta e da indicação de fonte devolvidas ao final do cenário 1.                                                                                                    |
| RNF09 — Auditabilidade das interações          | RF01, RF02, RF03, RF04, RF05 | Registra eventos de todas as interações com o agente, cobrindo consultas (RF01, RF02, RF03), sugestões de preenchimento (RF04) e notificações proativas (RF05), permitindo rastreabilidade e investigação de falhas. Complementa o RNF04, detalhando os atributos mínimos de cada evento registrado.                                                                              |
| RNF10 — Escalabilidade do agente               | RF02, RF04                         | Qualifica a capacidade de manter desempenho sob aumento de volume nos dois requisitos que percorrem o portfólio inteiro.                                                                                       |
| RNF11 — Explicabilidade das sugestões          | RF03, RF04                         | Mede a clareza e a rastreabilidade das fontes e justificativas das sugestões de preenchimento, estendendo ao RF04 a exigência de indicação de origem que o RF03 estabelece para as respostas de consulta.      |

### Relação dos requisitos não funcionais com os Business Drivers

Os requisitos não funcionais foram definidos a partir dos Business Drivers do projeto, considerando as características de qualidade necessárias para que o agente ofereça informações confiáveis, seguras e acessíveis aos usuários do Metrô de São Paulo.

Os requisitos de desempenho (RNF01) e disponibilidade (RNF07) contribuem para a **eficiência e agilidade no acesso às informações**, permitindo que os profissionais obtenham respostas rapidamente sem comprometer a tomada de decisão. O controle de acesso (RNF02) e a proteção de dados preservam a **confidencialidade e segurança da informação**, respeitando o perfil de cada usuário e as exigências legais aplicáveis. A rastreabilidade (RNF04) permite **transparência e auditoria** das consultas e respostas.

A precisão na identificação de intenções (RNF03) garante a **confiabilidade no acesso e tratamento das informações**, assegurando que solicitações em linguagem natural sejam interpretadas corretamente. A auditabilidade das interações (RNF09) complementa a rastreabilidade (RNF04), estabelecendo os atributos mínimos de cada evento registrado, de modo que seja possível investigar falhas, verificar a origem das respostas e controlar o acesso aos registros. A qualidade da transcrição de áudio (RNF06) e a interoperabilidade entre aplicações clientes (RNF05) oferecem **acessibilidade e flexibilidade**. A usabilidade (RNF08) e explicabilidade (RNF11) garantem que as respostas apoiem a **tomada de decisão** de forma clara. A escalabilidade (RNF10) contribui para a **continuidade operacional**, permitindo que o agente processe aumentos de volume sem degradação.

## 2.4 Visão Inicial da Solução Técnica

 A visão técnica apresentada nesta seção traduz, em um esboço preliminar de arquitetura, os fluxos de negócio descritos na seção 2.1 e os requisitos funcionais e não funcionais especificados nas seções 2.2 e 2.3. O diagrama a seguir representa a solução como um conjunto de blocos conectados, organizados em três camadas: interface humano-computador, lógica de negócio e acesso a dados e serviços.

 A divisão dos componentes de compreensão de linguagem segue o padrão adotado tanto por frameworks open-source de assistentes conversacionais, como o Rasa (RASA, 2024), quanto pela própria plataforma de bots da Microsoft (MICROSOFT, 2024), ecossistema já utilizado pelo parceiro por meio do Copilot Studio. Em ambos os casos, a compreensão da mensagem do usuário é dividida entre um componente de classificação de intenção, responsável por identificar o que o usuário deseja, e um componente de extração de parâmetros, responsável por capturar os dados específicos mencionados na solicitação, como o nome do projeto ou o período de referência.

### Diagrama de componentes (UML)

<div align="center">
<sub>Imagem 2.4.1 - Diagrama de componentes (UML) — Visão inicial da solução técnica</sub><br>
  <img src="../assets/diagrama_componentes.svg" width="100%" alt="Diagrama de componentes UML da solução, organizado em três camadas: interface, lógica de negócio e dados e serviços"><br>
  <sup>Fonte: Material produzido pelos autores, 2026.</sup>
</div>

<p align="center">
  Para melhor visualização do diagrama, acesse o arquivo no <a href="https://drive.google.com/file/d/154cjwt0ZTBpfKCDS-TIXnqn2YJdOKqlL/view?usp=sharing">Google Drive</a>.
</p>

### Descrição das camadas

| Camada | Componentes | Responsabilidade |
|---|---|---|
| **Interface (IHC)** | Chat UI - Texto e Voz | Recebe a solicitação do usuário nos dois canais previstos pelo RF01 e exibe a resposta estruturada ao final do processamento. |
| **Lógica de negócio** | API Gateway, Conversão de Áudio em Texto, Controle de Acesso, PLN — Compreensão (Intenção e Parâmetros), PLN — Transações e Ações, Gerador de Respostas e Explicabilidade, Auditoria e Feedback | O API Gateway centraliza a entrada das solicitações e as encaminha para a Conversão de Áudio em Texto quando a entrada ocorre por voz (RF01 e RNF06). Em seguida, o Controle de Acesso autentica o usuário e valida suas permissões (RNF02). O componente PLN — Compreensão identifica a intenção e extrai os parâmetros (RNF03), direcionando solicitações de preenchimento ao componente PLN — Transações e Ações (RF04 e RF06), alertas ao mesmo componente (RF05) e consultas ao Gerador de Respostas (RF02). O Gerador de Respostas monta a saída final e informa as fontes (RF03), além da justificativa quando aplicável (RNF11). Auditoria e Feedback registra os elementos definidos no RNF04 e captura a avaliação do usuário. |
| **Dados e serviços** | Repositório de Dados e Conhecimento, Logs de Auditoria | O Repositório de Dados e Conhecimento reúne os dados sintéticos estruturados do portfólio, o catálogo de intenções e a base de normativos empregados nas consultas (RF02), na indicação de fontes (RF03), nas sugestões (RF04 e RF06) e nos alertas (RF05). Os Logs de Auditoria armazenam separadamente os registros de interação e feedback protegidos contra alteração por usuários comuns (RNF04), pois possuem padrão de escrita e requisito de imutabilidade distintos dos dados operacionais. |

### Conexões entre componentes

| Origem → destino | Protocolo ou mecanismo | Dados e motivo da conexão |
|---|---|---|
| Chat UI → API Gateway | HTTPS/REST | Envia texto ou áudio por uma interface única, desacoplando a aplicação cliente da lógica interna. |
| API Gateway → Conversão de Áudio em Texto | Chamada de serviço por HTTPS/REST | Encaminha somente entradas de voz para transcrição, preservando um fluxo comum a partir do texto. |
| Conversão de Áudio em Texto → Controle de Acesso | Chamada interna | Entrega o texto transcrito ao mesmo controle aplicado às entradas digitadas. |
| API Gateway → Controle de Acesso | Chamada interna | Impede que solicitações em texto prossigam sem autenticação e autorização. |
| Controle de Acesso → PLN — Compreensão | Chamada interna | Encaminha apenas solicitações autorizadas para classificação de intenção e extração de parâmetros. |
| PLN — Compreensão → PLN — Transações e Ações | Chamada interna | Direciona intenções de sugestão e alerta para suas regras de negócio. |
| PLN — Compreensão → Gerador de Respostas | Chamada interna | Direciona consultas reconhecidas para composição da resposta. |
| PLN — Transações e Ações → Repositório de Dados | Consulta SQL e acesso ao repositório de documentos | Recupera campos e pendências sem alterar as fontes no MVP. |
| PLN — Transações e Ações → Gerador de Respostas | Chamada interna | Formata sugestões e alertas no mesmo padrão das consultas. |
| Gerador de Respostas → Repositório de Dados | Consulta SQL e recuperação de documentos | Obtém dados, metadados e referências necessários à resposta. |
| Gerador de Respostas → Chat UI | Resposta HTTPS/REST | Devolve conteúdo, fonte e data para exibição no canal de origem. |
| Gerador de Respostas → Auditoria e Feedback | Chamada interna | Registra a resposta apresentada e associa eventual feedback. |
| API Gateway → Auditoria e Feedback | Chamada interna | Registra usuário, data, hora, canal e solicitação desde a entrada. |
| PLN — Transações e Ações → Auditoria e Feedback | Chamada interna | Registra a intenção processada e o resultado sugestivo ou informativo. |
| Auditoria e Feedback → Logs de Auditoria | Persistência SQL | Mantém registros separados dos dados operacionais para facilitar controle de acesso e auditoria. |

---

## 2.5 Tecnologias e Ferramentas

### Linguagens e Tecnologias Utilizadas

O MVP será desenvolvido como uma aplicação independente da infraestrutura atualmente utilizada pelo Metrô, contemplando uma interface própria, uma camada de backend responsável pela lógica de negócio e componentes para processamento de linguagem natural, persistência de dados, consulta de documentos, controle de acesso, agendamento e notificações.

| Categoria | Escolha documentada | Alternativas registradas | Justificativa e relação com a arquitetura |
|---|---|---|---|
| Linguagem do backend e PLN | Python | [PENDENTE — registrar as alternativas comparadas pela equipe.] | Possui amplo ecossistema para PLN, inteligência artificial, APIs e processamento de dados. |
| Interface web | TypeScript, React e Next.js | [PENDENTE — registrar as alternativas comparadas pela equipe.] | Oferecem tipagem, componentização e estrutura para a aplicação cliente representada pela Chat UI. |
| API | FastAPI e APIs REST | [PENDENTE — registrar as alternativas comparadas pela equipe.] | Expõem o núcleo por contratos HTTP padronizados e mantêm as aplicações clientes desacopladas. |
| Persistência estruturada | PostgreSQL e SQL | [PENDENTE — registrar as alternativas comparadas pela equipe.] | Armazenam dados sintéticos do portfólio e registros de auditoria com consultas e controle transacional. |
| Documentos | Repositório de arquivos com metadados | Armazenamento corporativo Microsoft, previsto apenas para evolução futura | Mantém conteúdo e referências recuperáveis sem integrar o MVP às fontes reais do parceiro. |
| PLN e recuperação | Pipeline em Python, recuperação de informação e Retrieval-Augmented Generation (RAG) | Copilot Studio, considerado para integração futura | Permitem classificar intenções e recuperar contexto mantendo o núcleo independente do ambiente corporativo. |
| Voz | Serviço de conversão de áudio em texto e de texto em áudio | [PENDENTE — registrar os serviços avaliados e a escolha aprovada.] | Atende ao RF01 e ao RNF06 sem criar um pipeline de intenção separado para áudio. |
| Agendamento e notificações | Agendador de tarefas e serviço de notificações | [PENDENTE — registrar as alternativas comparadas pela equipe.] | Sustentam a verificação periódica e a comunicação proativa previstas no RF05. |
| Empacotamento | Docker | [PENDENTE — registrar as alternativas comparadas pela equipe.] | Padroniza o ambiente e reduz diferenças entre desenvolvimento e implantação. |
| Ecossistema corporativo futuro | Microsoft Copilot Studio e Power Platform | Aplicação independente adotada no MVP | Preserva aderência ao ambiente homologado sem exigir integração real nesta etapa. |

As tecnologias descritas a seguir compõem a base prevista para implementação da solução.

### Python

O **Python** será utilizado principalmente no desenvolvimento do backend, da lógica do agente e das funcionalidades relacionadas ao processamento de linguagem natural.

A linguagem será utilizada em atividades como:

* orquestração das solicitações;
* integração com serviços e APIs de inteligência artificial;
* classificação de intenções;
* extração de entidades;
* execução das regras de negócio;
* consulta às fontes de dados;
* análise de informações dos projetos;
* identificação de campos incompletos;
* geração de sugestões;
* geração de alertas;
* execução de tarefas periódicas;
* registro de interações e auditoria.

A escolha de Python está relacionada principalmente à sua ampla utilização no desenvolvimento de aplicações envolvendo inteligência artificial, processamento de linguagem natural e integração com modelos de linguagem.

### TypeScript

O **TypeScript** será utilizado principalmente no desenvolvimento da interface web da aplicação.

A linguagem adiciona tipagem estática ao JavaScript e contribui para maior organização, previsibilidade e manutenção do código da interface.

### SQL

O **SQL** será utilizado para definição, manipulação e consulta das informações estruturadas armazenadas no banco de dados relacional.

Entre essas informações estão dados de projetos, prazos, marcos, riscos, usuários, perfis, permissões, feedbacks e registros de auditoria.

### FastAPI

O **FastAPI** será utilizado como framework principal para construção do backend e das APIs da aplicação.

O backend será responsável por intermediar a comunicação entre a interface, o agente, as fontes de dados e os demais serviços da solução.

Entre suas principais responsabilidades estarão:

* disponibilização de endpoints;
* processamento das solicitações recebidas;
* aplicação das regras de negócio;
* controle de acesso;
* comunicação com o banco de dados;
* integração com serviços de inteligência artificial;
* consulta aos documentos;
* execução dos módulos de ação;
* registro de auditoria.

### React e Next.js

A interface da aplicação será desenvolvida utilizando **React**, com **Next.js** como framework web.

Essa camada será responsável pela interface conversacional do agente, permitindo que o usuário realize solicitações por texto ou voz e visualize:

* respostas do agente;
* informações estruturadas;
* fontes consultadas;
* datas de referência;
* sugestões;
* alertas;
* mensagens de insuficiência de dados;
* solicitações de feedback.

A interface será desenvolvida de forma independente dos canais atualmente utilizados pelo Metrô.

### PostgreSQL

O **PostgreSQL** será utilizado como banco de dados relacional principal do MVP.

O banco deverá armazenar informações estruturadas relacionadas a:

* projetos;
* prazos;
* marcos;
* riscos;
* avanço dos projetos;
* usuários;
* perfis e permissões;
* campos e artefatos dos projetos;
* feedbacks;
* metadados de documentos;
* registros de auditoria;
* informações utilizadas na geração de alertas.

Inicialmente, não é prevista a utilização de um segundo banco de dados não relacional, uma vez que os dados estruturados necessários ao MVP podem ser representados adequadamente por meio de um modelo relacional.

### Armazenamento e Consulta de Documentos

Os documentos utilizados pelo agente serão mantidos em um **repositório de arquivos independente**, acompanhado de seus respectivos metadados.

Esse repositório deverá conter documentos sintéticos que reproduzam a organização e os tipos de arquivos existentes no ambiente real do Metrô.

A estrutura permitirá validar funcionalidades como:

* localização de documentos;
* consulta ao conteúdo dos documentos;
* identificação de documentos ausentes;
* esclarecimento de dúvidas sobre normativos;
* indicação da fonte utilizada na resposta.

Dessa forma, o MVP poderá reproduzir os principais fluxos relacionados às informações atualmente armazenadas no SharePoint sem depender diretamente da infraestrutura corporativa.

### Inteligência Artificial e Processamento de Linguagem Natural

O agente utilizará uma **API de inteligência artificial disponibilizada no ecossistema Microsoft** para apoiar as funcionalidades de processamento de linguagem natural e geração de conteúdo.

Essa integração poderá ser utilizada em atividades como:

* interpretação das solicitações;
* identificação e classificação de intenções;
* detecção de solicitações fora do catálogo suportado;
* extração de entidades e parâmetros;
* geração de respostas em linguagem natural;
* geração de sugestões para preenchimento de campos;
* interpretação de documentos e normativos;
* apoio à identificação de informações relevantes nas fontes disponíveis.

A aplicação manterá sua própria camada de orquestração e regras de negócio, utilizando os modelos de linguagem como um dos componentes do processamento das solicitações.

### Recuperação de Informação e RAG

Para funcionalidades que envolvem documentos, normativos e outras fontes textuais, poderão ser utilizadas técnicas de **Retrieval-Augmented Generation (RAG)**.

Essa abordagem permite recuperar informações relevantes nas fontes disponíveis antes da geração da resposta pelo modelo de linguagem.

Sua utilização poderá apoiar funcionalidades como:

* consulta a documentos dos projetos;
* esclarecimento de dúvidas sobre normativos;
* identificação das fontes utilizadas;
* geração de respostas fundamentadas nas informações disponíveis;
* identificação de situações em que não existem dados suficientes para produzir uma resposta confiável.

### Serviço de Voz

O MVP permitirá que o usuário envie solicitações por voz.

Para isso, será utilizado um serviço de **Speech-to-Text (STT)** responsável pela conversão do áudio enviado pelo usuário em texto.

Após a transcrição, a solicitação seguirá o mesmo fluxo utilizado para as mensagens originalmente enviadas em texto.

O serviço de voz será responsável apenas pela conversão da entrada em áudio para texto. As respostas do agente serão apresentadas textualmente na interface.

### Agendamento de Tarefas

O sistema possuirá um mecanismo de **agendamento de tarefas periódicas** para execução automática de verificações que não dependem de uma solicitação direta do usuário.

Para o backend em Python, poderá ser utilizada uma ferramenta como o **APScheduler**.

Esse mecanismo poderá ser utilizado para:

* verificar prazos próximos;
* identificar documentos faltantes;
* identificar campos incompletos;
* analisar periodicamente situações dos projetos;
* iniciar a geração de alertas proativos.

Dessa forma, determinadas funcionalidades do agente poderão ser executadas de maneira automática e recorrente.

### Serviço de Notificações

O sistema contará com um mecanismo responsável pelo envio dos alertas e notificações identificados durante as verificações automáticas.

O serviço de notificações receberá as pendências encontradas pelo sistema, identificará os usuários relacionados ao projeto e encaminhará a informação pelo canal disponibilizado no MVP.

Esse mecanismo apoiará principalmente funcionalidades relacionadas a:

* alertas de prazo;
* documentos faltantes;
* campos incompletos;
* outras pendências identificadas automaticamente.

### Auditoria, Rastreabilidade e Feedback

As interações realizadas com o agente deverão ser registradas para permitir rastreabilidade das operações.

Os registros poderão incluir informações como:

* usuário responsável pela solicitação;
* data e horário;
* canal utilizado;
* intenção identificada;
* fontes consultadas;
* resultado da solicitação;
* alertas gerados;
* feedback fornecido pelo usuário.

Essas informações serão armazenadas de forma estruturada e utilizadas para auditoria e análise das interações realizadas com o sistema.

### APIs REST

A comunicação entre a interface, o backend e serviços externos será realizada principalmente por meio de **APIs REST**.

Essa abordagem permitirá separar as responsabilidades entre os diferentes componentes da aplicação e facilitar futuras integrações com outros sistemas.

### Docker

O **Docker** poderá ser utilizado para padronizar os ambientes de desenvolvimento e execução dos principais componentes da solução.

A conteinerização permitirá executar serviços como backend e banco de dados de maneira consistente entre os ambientes utilizados pela equipe.

### Integrações Futuras com o Ecossistema Microsoft

Embora o MVP seja desenvolvido fora da infraestrutura corporativa atualmente utilizada pelo Metrô, sua estrutura deverá possibilitar futuras integrações com os serviços adotados pela organização.

Entre as possíveis integrações futuras estão:

* SharePoint;
* Microsoft Teams;
* Copilot Studio;
* Power Automate;
* Microsoft Entra ID;
* demais serviços e APIs disponibilizados pelo ecossistema Microsoft.

Durante o MVP, dados, documentos, usuários e permissões sintéticos serão utilizados para representar as informações e fluxos necessários à validação da solução, sem expor dados corporativos reais do Metrô.

---

## 2.6 Rastreabilidade Consolidada

A tabela a seguir apresenta a rastreabilidade entre os principais elementos do artefato: business drivers, personas, jornadas, requisitos funcionais, requisitos não funcionais, diagramas e componentes. Ela permite verificar que não existem requisitos sem origem identificada, diagramas sem requisito relacionado nem componentes sem cobertura de requisito.

| Business Driver | Persona principal | Jornada relacionada | RF | RNF relacionado | Diagrama de classe (entidade central) | Diagrama de sequência | Componente arquitetural |
| --------------- | ----------------- | ------------------- | -- | --------------- | ------------------------------------- | --------------------- | ----------------------- |
| Eficiência e agilidade no acesso às informações | Robson (Diretor), Maria Eduarda (PMO), Rafael (Líder) | Jornadas 1.5.1, 1.5.2, 1.5.3 | RF01, RF02 | RNF01, RNF06, RNF07 | `Projeto`, `Portfólio`, `Usuário` | Cenário 1 | Chat UI, API Gateway, PLN — Compreensão, Gerador de Respostas |
| Precisão e confiabilidade das consultas | Robson (Diretor), Maria Eduarda (PMO) | Jornadas 1.5.1, 1.5.2 | RF02, RF03 | RNF03, RNF08, RNF11 | `Projeto`, `Artefato`, `Diretor`, `PMO` | Cenário 1 | PLN — Compreensão, Gerador de Respostas, Repositório de Dados |
| Confidencialidade e segurança da informação | Todos | Todas | RF02, RF03, RF04, RF05, RF06 | RNF02 | `Usuário`, `Diretor`, `PMO`, `LiderProjeto` | Cenários 1, 2, 3 | Controle de Acesso, API Gateway |
| Rastreabilidade e transparência | Todos | Todas | RF01, RF02, RF03, RF04, RF05 | RNF04, RNF09 | `Usuário` | Cenários 1, 2, 3 (automensagem `log()`) | Auditoria e Feedback, Logs de Auditoria |
| Proatividade e acompanhamento preventivo | Maria Eduarda (PMO), Rafael (Líder) | Jornadas 1.5.2, 1.5.3 | RF05 | RNF07 | `Pendência`, `Projeto`, `Usuário` | Cenário 3 | PLN — Transações e Ações, Serviço de Notificações, Agendador |
| Qualidade da entrada de dados | Rafael (Líder), Maria Eduarda (PMO) | Jornadas 1.5.2, 1.5.3 | RF04 | RNF11, RNF03 | `CampoArtefato`, `Artefato`, `LiderProjeto` | Cenário 2 | PLN — Transações e Ações, Gerador de Respostas, Repositório de Dados |
| Interoperabilidade e sustentabilidade tecnológica | Todos | Todas | RF01, RF02, RF04, RF05 | RNF05 | — | Cenários 1, 2, 3 | API Gateway (interface padronizada consumível por múltiplas aplicações clientes) |
| Acessibilidade e uso de linguagem natural | Todos | Todas | RF01 | RNF06 | `Usuário` | Cenário 1 (fragmento áudio) | Chat UI, Conversão de Áudio em Texto, API Gateway |

## 3. Definição Técnica e Arquitetural da Solução

### 3.1 Catálogo de Intenções e Contrato de Classificação

O catálogo de intenções define os tipos de solicitação que o agente deve reconhecer no MVP. A classificação ocorre após a entrada ser convertida para texto, quando aplicável, e antes da consulta às fontes ou do acionamento de qualquer processo. Solicitações que não correspondam às intenções catalogadas devem ser recusadas com uma orientação sobre as interações disponíveis.

| ID | Intenção técnica | Objetivo | Saída esperada | MVP |
|---|---|---|---|:---:|
| INT-01 | `consultar_documentos_normativos` | Consultar conceitos, regras, processos e informações dos documentos disponibilizados | Resposta fundamentada com indicação da fonte | Sim |
| INT-02 | `consultar_projeto_sintetico` | Consultar informações dos projetos do ambiente de demonstração | Dados estruturados do projeto sintético | Sim |
| INT-03 | `orientar_mapa_beneficios` | Apoiar o preenchimento do Mapa de Benefícios | Perguntas, campos pendentes e sugestões | Sim |
| INT-04 | `orientar_tap` | Apoiar o preenchimento do Termo de Abertura do Projeto | Orientações e sugestões para os campos do TAP | Sim |
| INT-05 | `orientar_entregas_cronograma` | Apoiar a definição de entregas, marcos, atividades, datas e dependências | Sugestões e validações do cronograma | Sim |
| INT-06 | `orientar_avanco_mensal` | Apoiar o preenchimento das informações de avanço do projeto | Dados necessários e sugestões de complementação | Sim |
| INT-07 | `orientar_riscos_problemas` | Apoiar a descrição e análise de riscos ou problemas | Sugestões de classificação, criticidade e plano de ação | Sim |
| INT-08 | `analisar_completude_coerencia` | Verificar se as informações fornecidas estão completas e coerentes | Diagnóstico de ausências, inconsistências e recomendações | Sim |
| INT-09 | `gerar_alertas_pendencias` | Identificar situações que precisam da atenção do usuário | Lista priorizada de alertas com justificativas | Sim, com dados de demonstração |
| INT-10 | `fora_do_catalogo` | Tratar solicitações que o protótipo não consegue executar | Explicação do limite e opções disponíveis | Sim |

#### Contrato de classificação

Para cada solicitação, o componente de compreensão deve devolver, no mínimo:

- a intenção identificada;
- as entidades extraídas;
- os parâmetros obrigatórios ausentes;
- a indicação de que a solicitação está fora do catálogo, quando aplicável.

O agente só deve prosseguir quando a intenção estiver suficientemente identificada e os parâmetros necessários estiverem disponíveis. Em caso de ambiguidade ou informação faltante, deve solicitar esclarecimento ao usuário.

#### Delimitação central

As intenções de orientação, análise e alerta produzem apenas respostas e sugestões no chat. No MVP, o agente consulta, interpreta, orienta e sugere conteúdos, mas não preenche documentos oficiais, não altera ou grava registros, não executa transações e não acessa o portfólio real do Metrô, as respostas dependem exclusivamente de documentos disponibilizados, dados sintéticos, informações fornecidas na conversa e artefatos anexados pelo usuário. Toda sugestão apresentada pelo agente deve ser revisada e confirmada pelo usuário, e o agente não deve apresentar sugestões como decisões oficiais, aprovações ou determinações de conformidade.

#### Regra de classificação durante fluxos guiados

O classificador de intenções não deve interpretar cada resposta fornecida durante um fluxo guiado como uma nova intenção. Por exemplo, se o agente pergunta "Qual é a data de término da entrega?" e o usuário responde "31 de dezembro de 2026", essa resposta não representa uma nova intenção: o gerenciador de diálogo deve tratá-la como o preenchimento da entidade `data_termino` do processo em andamento.

Uma nova classificação de intenção só deve ser executada quando o sistema detectar:

- a resposta não corresponder ao tipo ou ao formato esperado da entidade em preenchimento;
- mudança de assunto em relação ao processo em andamento;
- solicitação explícita do usuário para iniciar outro processo.

### 3.2 API de Speech to Text e Text to Speech

#### Serviço de Speech to Text

**Decisão:** utilizar o **Deepgram**, modelo `nova-3`, como serviço de conversão de áudio em texto.

O comparativo abaixo registra os critérios avaliados:

| Critério | Deepgram nova-3 | OpenAI Whisper API | Google Cloud STT | Azure Cognitive Speech |
| --- | --- | --- | --- | --- |
| Suporte ao português brasileiro | Sim, modelo dedicado | Sim | Sim | Sim |
| Qualidade em vocabulário técnico | Alta, aceita keyterms de domínio | Alta | Média | Média-alta |
| Custo por minuto de áudio | ~US$ 0,0043 | ~US$ 0,006 | ~US$ 0,016 | ~US$ 0,014 |
| Créditos gratuitos disponíveis | US$ 200 (conta nova) | US$ 5 (tier free) | US$ 300 (trial) | US$ 200 (trial) |
| Latência de resposta | Baixa (~1–2 s para áudios curtos) | Média (~3–5 s) | Baixa | Baixa |
| SDK Python oficial | Sim (`deepgram-sdk`) | Sim (`openai`) | Sim (`google-cloud-speech`) | Sim (`azure-cognitiveservices-speech`) |
| Facilidade de integração | Alta, cliente assíncrono nativo | Alta | Média, exige credencial GCP | Média, exige recurso Azure |

O Deepgram foi escolhido por combinar suporte explícito a termos de domínio via parâmetro `keyterm`, relevante para vocabulário do PMO como "empreendimento", "cronograma" e "marco", com latência baixa e créditos gratuitos que viabilizam os testes desta sprint sem custo. A escolha é provisória: a abstração `AudioFetcher` em `src/services/transcription_service.py` isola o cliente do restante do código, de modo que a troca por outro provedor exige alteração apenas na camada de serviço, sem impacto nas rotas ou nos esquemas de resposta. A decisão será reavaliada antes da entrega final com base nos resultados de WER medidos sobre áudios do vocabulário do portfólio, conforme exigido pelo RNF06.

#### Endpoint de transcrição

**Decisão:** expor a transcrição como um endpoint separado do recebimento do áudio, acionado por `audio_id`.

O áudio é armazenado primeiro via `POST /api/v1/audio` e transcrito sob demanda. Essa separação permite que o recebimento e a transcrição evoluam de forma independente e que o mesmo áudio seja retranscrito sem reenvio, caso o serviço externo falhe ou o idioma precise ser corrigido.

```http
POST /api/v1/audio/{audio_id}/transcribe
```

#### Parâmetros de entrada

| Parâmetro | Tipo | Obrigatório | Padrão | Descrição |
| --- | --- | --- | --- | --- |
| `audio_id` | string (rota) | Sim | | Identificador retornado pelo endpoint de recebimento |
| `language` | string (query) | Não | `pt-BR` | Código BCP-47 do idioma do áudio |

#### Autenticação

Nenhum cabeçalho de autenticação é exigido nesta versão. A autenticação com o Deepgram é feita internamente pela API, a partir da variável de ambiente `DEEPGRAM_API_KEY`.

#### Resposta de sucesso

**Código HTTP:** `200 OK`

| Campo | Tipo | Descrição |
| --- | --- | --- |
| `audio_id` | string | Identificador do áudio transcrito |
| `text` | string | Texto resultante da transcrição |
| `language` | string | Idioma utilizado na transcrição |
| `confidence` | float \| null | Grau de confiança médio reportado pelo serviço (0–1), ou `null` se não disponível |
| `duration_seconds` | float | Duração do áudio em segundos |

#### Respostas de erro

| Código | Condição |
| --- | --- |
| 404 | Áudio não encontrado no armazenamento (`audio_id` inexistente) |
| 502 | Falha na transcrição: serviço externo indisponível ou retornou erro |
| 422 | Parâmetro inválido (ex.: `language` com formato incorreto) |

#### Exemplos de requisição e resposta

```bash
curl -X POST \
  "http://localhost:8000/api/v1/audio/aud_067071317397468196a9b9c4cffa82c6/transcribe?language=pt-BR"
```

**Código HTTP:** `200 OK`

```json
{
  "audio_id": "aud_067071317397468196a9b9c4cffa82c6",
  "text": "Qual o status atual do empreendimento Linha 6 e quais são os marcos previstos para o próximo trimestre?",
  "language": "pt-BR",
  "confidence": 0.9516,
  "duration_seconds": 22.831
}
```

Áudio inexistente:

```bash
curl -X POST \
  "http://localhost:8000/api/v1/audio/aud_inexistente/transcribe"
```

**Código HTTP:** `404 Not Found`

```json
{
  "detail": "Áudio não encontrado: aud_inexistente"
}
```

Falha no serviço externo:

**Código HTTP:** `502 Bad Gateway`

```json
{
  "detail": "Falha na transcrição do áudio aud_067071317397468196a9b9c4cffa82c6"
}
```

#### Serviço de Text to Speech

A implementação do TTS não está no escopo desta sprint. O cliente de TTS exige que o serviço esteja escolhido e com credenciais de teste disponíveis antes de qualquer desenvolvimento, e essa avaliação ainda não foi concluída pelo grupo. Além disso, a integração ponta a ponta STT-PLN-TTS depende tanto do cliente de STT, já implementado, quanto do cliente de TTS, ainda pendente; iniciar a integração sem os dois clientes prontos resultaria em trabalho parcial que não pode ser validado.

O comparativo de provedores, a documentação dos endpoints e os exemplos de uso serão incluídos nesta seção na próxima sprint, após a escolha do serviço e os primeiros testes com o vocabulário do portfólio.

### 3.3 Algoritmo de NLP e Implementação

<!-- Exemplo do que incluir: algoritmo escolhido, finalidade, funcionamento, bibliotecas utilizadas e exemplo de implementação. -->

### 3.4 API para Recebimento de Áudios

Esta seção documenta a API interna responsável por receber os áudios enviados pelos usuários, estabelecendo o contrato de entrada do canal de voz da solução. As definições apresentadas determinam como o áudio entra no sistema, quais regras devem ser respeitadas antes do processamento e como o cliente deve tratar os resultados.

#### Endpoint e método HTTP

**Decisão:** utilizar o método `POST` no endpoint abaixo:

```http
POST /api/v1/audio
```

O método `POST` é adequado para o envio de um novo recurso ao sistema. O prefixo `/api/v1` permite versionar a API e facilita futuras evoluções sem quebrar integrações existentes.

#### Autenticação

**Decisão:** utilizar autenticação por Bearer Token.

```http
Authorization: Bearer <token>
```

Esse mecanismo restringe o acesso à API a usuários ou serviços autenticados e segue um padrão amplamente utilizado em APIs HTTP. O token será emitido pelo mecanismo de autenticação da solução. A definição do serviço emissor, entre autenticação própria ou integração com o Copilot Studio, será consolidada na Sprint 3, quando a camada de orquestração estiver especificada.

#### Formato da requisição

**Decisão:** utilizar `multipart/form-data`.

Esse formato é apropriado para o envio de arquivos binários e evita a conversão do áudio para Base64, que aumentaria desnecessariamente o tamanho da requisição.

#### Parâmetros de entrada

| Parâmetro | Tipo | Obrigatório | Formato esperado | Descrição |
| --- | --- | --- | --- | --- |
| `audio` | Arquivo binário | Sim | `audio/wav`, `audio/mpeg`, `audio/mp4`, `audio/x-m4a`, `audio/webm` | Arquivo de áudio enviado pelo usuário |

Nesta etapa, o endpoint precisa apenas receber o áudio. Outros parâmetros poderão ser adicionados futuramente caso o fluxo da aplicação exija.

A extensão e o MIME type declarados pelo cliente **não são utilizados como única fonte de verdade**: ambos podem ser inconsistentes com o conteúdo real do arquivo (um cliente pode renomear um arquivo ou enviar um MIME type incorreto). Por isso, a validação de formato deve inspecionar o conteúdo binário do arquivo (assinatura/header do arquivo), e não apenas os metadados informados na requisição.

#### Formatos de áudio suportados

Inicialmente, serão aceitos os seguintes formatos:

| Extensão | MIME types aceitos |
| --- | --- |
| `.wav` | `audio/wav`, `audio/x-wav` |
| `.mp3` | `audio/mpeg` |
| `.m4a` | `audio/mp4`, `audio/x-m4a` |
| `.webm` | `audio/webm` |

Diferentes clientes podem declarar variações de MIME type para o mesmo formato — em especial para `.m4a`, que pode chegar como `audio/mp4` ou `audio/x-m4a` dependendo do navegador ou dispositivo. Todas as variações listadas acima devem ser aceitas como válidas para a respectiva extensão. Esses formatos possuem ampla compatibilidade com navegadores, dispositivos móveis e serviços de Speech-to-Text, atendendo aos principais cenários de captura de áudio do sistema.

#### Tamanho máximo do arquivo

Cada arquivo será limitado a **10 MB**. Esse limite evita requisições excessivamente grandes, reduz o consumo desnecessário de memória e rede e oferece margem suficiente para áudios curtos utilizados em interações por voz.

#### Duração máxima

O áudio será limitado a **5 minutos**. A solução foi projetada para interações de voz e consultas, e não para o processamento de gravações extensas. O limite reduz o tempo de processamento e o uso de recursos.

Caso a duração do áudio ultrapasse esse limite, a API retorna `422 Unprocessable Entity` com o erro `audio_too_long`.

#### Exemplo de requisição

```bash
curl -X POST https://api.azum.com/api/v1/audio \\
  -H "Authorization: Bearer <token>" \\
  -F "audio=@consulta.wav"
```

O header `Content-Type: multipart/form-data` não é definido manualmente: a flag `-F` do curl já monta a requisição como multipart e adiciona o boundary correto automaticamente. Defini-lo à mão, sem o boundary, resultaria em uma requisição inválida.

#### Resposta de sucesso

**Código HTTP:** `201 Created`

```json
{
  "id": "aud_123456",
  "status": "received",
  "message": "Áudio recebido com sucesso."
}
```

O código `201` indica que o sistema recebeu e criou um novo recurso associado ao áudio enviado. Após passar por todas as validações, o áudio é armazenado em um bucket compatível com S3 usando o `id` gerado como chave do objeto — esse `id` é o que a próxima etapa do pipeline (Speech-to-Text) utiliza para recuperar o arquivo.

#### Respostas de erro

| Código HTTP | Situação |
| --- | --- |
| `400 Bad Request` | Requisição malformada (ex: corpo que não é `multipart/form-data` válido) |
| `401 Unauthorized` | Token ausente ou inválido |
| `413 Payload Too Large` | Arquivo maior que 10 MB |
| `415 Unsupported Media Type` | Formato de áudio não suportado (extensão/MIME type fora da lista aceita) |
| `422 Unprocessable Entity` | Arquivo ausente, vazio, corrompido, com duração acima do limite, ou em formato aceito porém inválido para processamento |
| `500 Internal Server Error` | Falha interna inesperada |

A distinção entre `415` e `422` é importante para o cliente tratar cada caso corretamente:

- **`415`**: o cliente enviou um arquivo em um formato que a API **não suporta** (extensão/MIME type fora da lista de formatos aceitos).
- **`422`**: o arquivo está em um formato **aceito**, mas não pode ser processado — por exemplo, está corrompido, vazio, ausente, ou ultrapassa a duração máxima permitida.

Sobre o arquivo ausente: como a implementação utiliza FastAPI, um parâmetro obrigatório declarado como `audio: UploadFile = File(...)` gera automaticamente um erro `422` quando o arquivo não é enviado. O contrato segue esse comportamento nativo do framework, em vez de tratá-lo manualmente para forçar um `400` — isso também é consistente com a semântica HTTP, já que a ausência de um campo obrigatório é um erro semântico (a requisição está bem formada, mas incompleta), não um erro de sintaxe. Dessa forma, `400` fica reservado para requisições estruturalmente inválidas (ex: corpo que não é multipart), e implementação e contrato permanecem alinhados. Esse `400` retorna o corpo padronizado com `error: "bad_request"`; já o `422` de arquivo ausente é a única resposta de erro que mantém o corpo nativo do FastAPI (`{"detail": [...]}`), pela razão explicada acima.

Todas as respostas de erro seguem o mesmo formato padronizado:

```json
{
  "error": "<código_do_erro>",
  "message": "<mensagem legível para o usuário>"
}
```

| Código de erro | Código HTTP | Situação |
| --- | --- | --- |
| `bad_request` | 400 | Requisição malformada (ex: corpo que não é multipart válido) |
| `unauthorized` | 401 | Token ausente ou inválido |
| `unsupported_format` | 415 | Formato de áudio não suportado |
| `file_too_large` | 413 | Arquivo maior que 10 MB |
| `audio_too_long` | 422 | Duração do áudio acima de 5 minutos |
| `invalid_audio` | 422 | Arquivo ausente, vazio ou corrompido |
| `internal_error` | 500 | Falha interna inesperada |

Exemplos de respostas de erro:

```json
{
  "error": "bad_request",
  "message": "Requisição malformada."
}
```

```json
{
  "error": "unsupported_format",
  "message": "Formato de áudio não suportado. Formatos aceitos: wav, mp3, m4a, webm."
}
```

```json
{
  "error": "file_too_large",
  "message": "O arquivo excede o tamanho máximo permitido de 10 MB."
}
```

```json
{
  "error": "audio_too_long",
  "message": "O áudio excede a duração máxima permitida de 5 minutos."
}
```

```json
{
  "error": "invalid_audio",
  "message": "Arquivo de áudio ausente, vazio ou corrompido."
}
```

```json
{
  "error": "unauthorized",
  "message": "Token de autenticação ausente ou inválido."
}
```

```json
{
  "error": "internal_error",
  "message": "Erro interno inesperado."
}
```

Os códigos HTTP e os códigos de erro padronizados facilitam o tratamento dos erros pelo frontend e tornam o comportamento da API previsível.

#### Requisitos adicionais

Consolidando as regras que o contrato da API precisa respeitar:

- **HTTPS obrigatório**: todas as requisições devem ser feitas via HTTPS, para proteger o áudio e o token de autenticação em trânsito.
- **Autenticação obrigatória**: toda requisição deve conter um Bearer Token válido.
- **Arquivo obrigatório**: o campo `audio` deve estar presente na requisição.
- **Arquivo não vazio**: o arquivo enviado não pode ter tamanho zero.
- **Tamanho máximo**: 10 MB por arquivo.
- **Duração máxima**: 5 minutos por áudio.
- **Formato validado pelo conteúdo real do arquivo**, não apenas pela extensão ou MIME type informado pelo cliente.
- **Formatos aceitos**: `.wav`, `.mp3`, `.m4a`, `.webm` (com as variações de MIME type aceitas listadas na seção de formatos suportados).

#### Fluxo de processamento

```text
Usuário
  ↓
POST /api/v1/audio
  ↓
Autenticação (Bearer Token)
  ↓
Validação do arquivo (presença e estrutura)
  ↓
Validação de formato, tamanho e duração

  ↙                          ↘
Áudio aceito              Áudio rejeitado
  ↓                          ↓
Encaminha para           Retorna 4xx com
Speech-to-Text           mensagem de erro
```

Com essas definições, o contrato da API estabelece como o áudio entra no sistema, quais regras devem ser respeitadas antes de seu processamento e como o cliente deve tratar tanto o caminho de sucesso quanto os casos de erro.

### 3.5 Pilha de Tecnologias

<!-- Exemplo do que incluir: linguagens, frameworks, bibliotecas, plataforma de execução e justificativa das escolhas. -->

### 3.6 Modelagem Conceitual e Lógica dos Dados

<!-- Exemplo do que incluir: entidades, relacionamentos, atributos principais e diagramas dos modelos de dados. -->

### 3.7 Processo de Deploy em Nuvem

#### 3.6.1 Arquitetura e Provedor Selecionado

O deploy do pipeline de Processamento de Linguagem Natural foi definido para o **Microsoft Azure**. No MVP, o núcleo permanece independente; Copilot Studio, Power Platform, Teams e SharePoint são integrações futuras com o ambiente corporativo do parceiro.

**Componentes principais:**

| Componente | Serviço Microsoft | Justificativa |
|-----------|------------------|--------------|
| Hospedagem do modelo | Azure App Service (tier gratuito) | HTTP API nativa, escalável, integrado com ecossistema Microsoft |
| Integração futura | Copilot Studio | Possível orquestração corporativa após o MVP independente |
| Persistência de dados | PostgreSQL | Mantém a tecnologia de banco definida para o MVP e pode ser hospedada em serviço compatível no Azure |
| Conversão de voz | Azure Cognitive Services (Speech-to-Text) | Free tier generoso: 5 horas/mês grátis |
| Integração de processos | Power Automate | Automações e orquestração de workflows |
| Ambiente completo | Microsoft 365 Developer Program | Tenant sandbox com 25 usuários, inclui Teams, SharePoint, Entra ID |

**Por que essa arquitetura:**
- **Alinhamento com parceiro** — Todo o ecossistema real de produção é Microsoft
- **Integração nativa** — Copilot Studio, Power Automate, Teams e SharePoint funcionam sem adaptadores customizados
- **Controle de custo acadêmico** — as camadas gratuitas poderão ser utilizadas quando disponíveis e compatíveis com a implantação escolhida
- **Reprodutibilidade** — os passos e parâmetros necessários serão registrados para repetição em ambiente autorizado

**Arquitetura em alto nível:**  

```
Usuário em Teams / Copilot Studio (Microsoft 365)
        ↓
  Copilot Studio (orquestração nativa)
        ├→ Power Automate (automações)
        ├→ Azure App Service (API do modelo NLP)
        │       ├→ Azure SQL Database / Cosmos DB (logs, histórico)
        │       └→ Application Insights (monitoramento)
        ├→ Azure Cognitive Services (STT/TTS)
        └→ SharePoint / OneDrive (documentos integrados)
```


#### 3.6.2 Serviços Gratuitos e Limites

**Azure Free Tier (sempre gratuito):**
- Azure App Service: 1 aplicação Web grátis (até 60 minutos de computação/dia)
- Azure Cognitive Services: 5.000 requisições/mês de Speech, 5.000 requisições/mês de Text
- Application Insights: 1 GB/mês de ingestão de logs

**Azure Free Tier (12 meses iniciais):**
- Azure SQL Database: 1 banco com até 5 GB grátis
- Azure Container Registry: 1 registro com 500 MB grátis

**Microsoft 365 Developer Program:**
- Tenant completo com 25 usuários
- Teams, SharePoint, OneDrive, Power Platform, Copilot Studio inclusos
- Válido enquanto ativo (renovável)

**Para projeto acadêmico sem time constraint:**
No projeto acadêmico, as camadas gratuitas serão usadas quando disponíveis e suficientes. A implantação real deverá considerar licenciamento e recursos corporativos.

#### 3.6.3 Etapas de Configuração e Implantação

**Passo 1 — Criar Ambientes Microsoft:**
1. Registrar-se em [Microsoft 365 Developer Program](https://developer.microsoft.com/en-us/microsoft-365/dev-program)
2. Criar tenant sandbox (instantâneo, pré-configurado)
3. Registrar-se em [Azure Portal](https://portal.azure.com) com a mesma conta
4. Ativar free tier credits (se aplicável)

**Passo 2 — Configurar Azure para Hospedagem do Modelo:**
1. Criar resource group `az1-nlp-dev`
2. Criar Azure App Service (`F1 Free` para publicação compatível ou `B1 Basic`, pago, quando os requisitos exigirem)
3. Configurar deployment via Git ou Docker (Azure Container Registry)
4. Criar ou conectar uma instância PostgreSQL para persistência

**Passo 3 — Preparar Modelo e API:**
1. Estruturar projeto Python em `src/nlp-deploy/`
2. Criar aplicação FastAPI com endpoint `/classify` que recebe `{"text": "..."}`
3. Exportar modelo treinado (TF-IDF + LogReg ou BERTimbau em ONNX) para diretório `model/`
4. Criar `requirements.txt` com dependências (flask, scikit-learn, joblib, ou onnxruntime)

**Passo 4 — Containerizar e Publicar:**
1. Criar `Dockerfile` baseado em `python:3.11-slim`
2. Testar localmente com `docker run`
3. Fazer build e push para Azure Container Registry
4. Atualizar App Service para usar imagem do ACR

**Passo 5 — Configurar Copilot Studio:**
1. Acessar [Copilot Studio](https://copilotstudio.microsoft.com) via M365 Dev tenant
2. Criar novo Copilot (agent)
3. Adicionar ação customizada que chama URL do Azure App Service
4. Configurar fluxo: receber texto → chamar API NLP → retornar intenção e confiança
5. Testar em preview dentro do Copilot Studio
6. Publicar para Teams

**Passo 6 — Integração com Power Automate (Opcional):**
1. Criar cloud flow acionado por evento (ex: novo documento no SharePoint)
2. Chamar ação customizada do Copilot Studio ou diretamente API do Azure App Service
3. Registrar resultado em lista do SharePoint ou tabela de SQL Database
4. Enviar notificação para usuário via Teams

#### 3.6.4 Exemplo de API (Flask)


```python
# src/nlp-deploy/app.py
from flask import Flask, request, jsonify
import joblib
import uuid
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

app = Flask(__name__)

# Carregar modelo
modelo = joblib.load("model/model.joblib")

# Conexão com banco (Azure SQL ou Postgres)
# Para dev local: sqlite:///local.db
# Para Azure SQL: mssql+pyodbc://user:pass@server.database.windows.net/db
DATABASE_URL = "sqlite:///./classifications.db"
engine = create_engine(DATABASE_URL)

@app.route("/health", methods=["GET"])
def health():
    return {"status": "healthy"}, 200

@app.route("/classify", methods=["POST"])
def classify():
    data = request.json
    texto = data.get("text", "")

    if not texto:
        return {"error": "text field required"}, 400

    # Classificação
    probs = modelo.predict_proba([texto])[0]
    idx = probs.argmax()
    intencao = modelo.classes_[idx]
    confianca = float(probs[idx])

    resultado = {
        "id": str(uuid.uuid4()),
        "text": texto,
        "intent": intencao,
        "confidence": round(confianca, 4),
        "timestamp": datetime.utcnow().isoformat()
    }

    # Gravar em banco (opcional)
    # db.insert_classification(resultado)

    return resultado, 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=False)
```

**Dockerfile correspondente:**

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY src/nlp-deploy/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/nlp-deploy/ .

EXPOSE 8000

CMD ["gunicorn", "--bind", "0.0.0.0:8000", "app:app"]
```

#### 3.6.5 Reprodutibilidade e Verificação

**Checklist de controle de custo:**
- [ ] Azure App Service em tier Free (1 instância)
- [ ] Azure SQL Database com free tier (primeiros 12 meses)
- [ ] Cognitive Services em free tier (limites respeitados)
- [ ] Elegibilidade e licenciamento do ambiente Microsoft confirmados
- [ ] Nenhum recurso em tier "Standard" ou "Premium" ativo

**Checklist de funcionalidade:**
- [ ] Azure App Service com status "Running"
- [ ] Endpoint `/health` retorna 200 OK
- [ ] Endpoint `/classify` processa requisições POST
- [ ] Copilot Studio consegue chamar API
- [ ] Resposta do agente aparece em Teams
- [ ] Logs aparecem em Application Insights
- [ ] Dados são gravados em banco (se integrado)

**Exemplo de requisição ponta a ponta:**

> A URL abaixo é ilustrativa e deverá ser substituída pela URL real após a execução do deploy.

```bash
curl -X POST https://az1-nlp-dev.azurewebsites.net/classify \
  -H "Content-Type: application/json" \
  -d '{"text": "Qual o prazo do marco de licenciamento ambiental da Linha 6?"}'
```

**Resposta esperada:**

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "text": "Qual o prazo do marco de licenciamento ambiental da Linha 6?",
  "intent": "consulta",
  "confidence": 0.8734,
  "timestamp": "2026-08-24T11:21:00.000000"
}
```

#### 3.6.6 Próximos Passos para Produção

Quando a solução for promovida para ambiente real do Metrô:

1. **Migrar banco de dados:** De Azure SQL (free 12m) para SQL Server corporativo ou similar
2. **Copilot Studio em produção:** Usar tenant corporativo em vez de sandbox M365 Dev
3. **Power Automate com SharePoint real:** Conectar a documentos e listas de verdade
4. **Entra ID:** Integrar autenticação corporativa do Metrô
5. **Compliance e segurança:** Implementar audit logs, DLP (Data Loss Prevention), conformidade com políticas corporativas

Toda a arquitetura permanece igual; apenas migram os recursos para ambientes gerenciados pelo Metrô.

#### 3.6.7 Observações Finais

Este deploy foi planejado como uma prova de conceito técnica alinhada ao ecossistema Microsoft do parceiro. A reprodutibilidade será confirmada após a execução dos passos e a inclusão das evidências. Uma futura promoção para produção exigirá ajustes de configuração, segurança, licenciamento e integração com o ambiente real do Metrô.

### 3.8 Projeto Técnico e Arquitetural

<!-- Exemplo do que incluir: diagramas UML de classes, componentes e sequência, acompanhados de explicações. -->

### 3.9 Estratégia de Entrega para as Sprints 3, 4 e 5

<!-- Exemplo do que incluir: como desenvolvimento, integração, testes e deploy serão distribuídos entre as próximas sprints. -->


## 4. Prototipação Exploratória — Design e UX

### 4.1 Questão de Projeto

**Como deve ocorrer a interação entre o usuário e o agente de IA para facilitar o acesso às informações relevantes dos projetos durante sua rotina de trabalho?**

Essa questão permanece em aberto porque, embora o agente tenha como objetivo facilitar o acesso às informações dos projetos, ainda não está definida a forma como essa interação deve acontecer no cotidiano do usuário. Diferentes formas de interação podem alterar quando e como as informações são apresentadas, o nível de iniciativa do agente e o controle do usuário sobre as consultas. A exploração das alternativas permitirá investigar as consequências dessas diferentes formas de interação antes de definir um comportamento para o sistema.

### 4.2 Alternativas Divergentes

Para investigar diferentes formas de interação entre o usuário e o agente de IA durante a rotina de trabalho, foram propostas duas alternativas que apresentam comportamentos distintos quanto à iniciativa do agente e à forma de acesso às informações dos projetos.

#### 4.2.1 Alternativa A: Interação Proativa e Contextual

Nesta alternativa, o agente acompanha o contexto das atividades realizadas pelo usuário durante sua rotina de trabalho e identifica informações e documentos do banco de dados que possam ser relevantes para a atividade em andamento. Ao encontrar conteúdos potencialmente úteis, o agente apresenta uma recomendação, permitindo que o usuário escolha se deseja ou não acessá-los.

A proposta busca explorar uma interação em que o agente possui maior iniciativa, oferecendo informações sem depender de uma consulta explícita. O usuário, entretanto, mantém o controle sobre a interação, podendo aceitar ou rejeitar as recomendações apresentadas.

Ao final do período de trabalho, as informações consideradas relevantes podem ser organizadas em um ambiente integrado ao Microsoft Teams, junto ao chatbot do agente, permitindo visualizar conteúdos priorizados, pendências identificadas e possíveis próximos passos.

#### 4.2.2 Alternativa B: Interação Sob Demanda

Nesta alternativa, o agente não apresenta recomendações durante as atividades do usuário. A interação ocorre somente quando o próprio usuário identifica uma necessidade e inicia uma consulta ao agente, informando o que deseja encontrar ou compreender sobre determinado projeto.

A partir da solicitação realizada, o agente consulta as informações disponíveis e apresenta os documentos e conteúdos relacionados à necessidade expressa pelo usuário. Dessa forma, a iniciativa da interação permanece com a pessoa, que determina quando utilizar o agente e quais informações deseja consultar.

Essa alternativa busca explorar uma experiência com menor nível de intervenção durante a rotina de trabalho, priorizando o controle do usuário sobre o momento e o contexto em que o agente é acionado.

#### Divergência entre as alternativas

As alternativas diferem principalmente em **quem inicia a interação**. Na Alternativa A, o agente identifica oportunidades de apoio e apresenta recomendações de forma proativa durante a atividade. Na Alternativa B, o agente permanece disponível, mas só realiza a busca e apresenta informações após uma solicitação explícita do usuário.

Essa diferença pode alterar aspectos relevantes da experiência, como o esforço necessário para encontrar informações, a frequência de interrupções, o nível de controle percebido pelo usuário e a capacidade do agente de antecipar necessidades. Neste momento, nenhuma das alternativas é considerada definitiva ou superior à outra; ambas serão exploradas por meio dos protótipos.

### 4.3 Formatos de Prototipação

Para explorar as duas alternativas propostas, foram escolhidos formatos de prototipação que permitem observar diferentes aspectos da interação entre o usuário e o agente de IA. Os protótipos serão construídos em paralelo e utilizados como instrumentos de investigação, sem representar versões finais da solução.

#### 4.3.1 Alternativa A: Vídeo e Encenação da Interação Proativa

A alternativa de interação proativa e contextual será explorada por meio de um **vídeo encenado**, representando um usuário durante sua rotina de trabalho enquanto o agente acompanha o contexto das atividades realizadas.

Ao longo da encenação, serão representados momentos em que o agente identifica documentos potencialmente relevantes e apresenta recomendações visuais ao usuário. O usuário poderá aceitar ou rejeitar essas recomendações, permitindo observar como a iniciativa do agente interfere no fluxo normal de trabalho.

O formato foi escolhido por permitir representar a experiência ao longo do tempo e investigar questões como **quando uma recomendação deveria aparecer, com que frequência o agente deveria intervir, como o usuário mantém controle sobre as sugestões e em quais situações uma recomendação pode deixar de ajudar e passar a interromper a atividade**.

O vídeo não busca representar uma interface final ou tecnicamente implementada, mas sim simular o comportamento e a relação entre usuário e agente em um cenário de uso.

#### 4.3.2 Alternativa B: Interface de Interação Sob Demanda

A alternativa de interação sob demanda será explorada por meio de uma **interface gráfica conversacional**, na qual o usuário inicia a interação com o agente sempre que identifica a necessidade de consultar alguma informação relacionada aos projetos.

Nesse formato, o usuário pode realizar perguntas em linguagem natural por **texto ou voz**. A partir da solicitação, o agente interpreta a consulta, busca as informações disponíveis nas fontes de dados do projeto e apresenta uma resposta em linguagem natural, podendo também indicar os documentos e fontes relacionados à informação apresentada.

Diferentemente da alternativa proativa, o agente não acompanha continuamente as atividades realizadas pelo usuário nem apresenta recomendações espontâneas. A interação depende de uma ação explícita do usuário, que determina quando o agente será acionado e qual informação deseja consultar.

Esse formato permite investigar **como o usuário formula suas necessidades em linguagem natural, quanto contexto precisa fornecer para obter uma resposta adequada e quais dificuldades podem surgir quando ele precisa identificar a necessidade e iniciar a interação com o agente**.

A prototipação por interface gráfica também permite representar e explorar situações como consultas ambíguas, perguntas por texto ou voz, necessidade de esclarecimento e apresentação das fontes utilizadas pelo agente.

#### Relação dos formatos com a questão de projeto

Os dois formatos permitem investigar a questão definida na [seção 4.1](#41-questão-de-projeto) a partir de formas distintas de interação entre o usuário e o agente. O vídeo encenado permite explorar uma experiência proativa e contextual, na qual o agente acompanha a rotina de trabalho e pode recomendar informações e documentos sem depender de uma solicitação inicial. Já a interface gráfica conversacional permite explorar uma experiência sob demanda, em que o usuário inicia a interação por texto ou voz e recebe respostas em linguagem natural a partir de suas solicitações.

A exploração dos dois formatos permite observar diferenças relacionadas à iniciativa do agente, ao nível de controle do usuário, à possibilidade de interrupções e ao esforço necessário para acessar informações. O objetivo não é determinar previamente qual alternativa é superior, mas compreender as consequências e limitações de cada forma de interação para orientar decisões futuras do projeto.

### 4.4 Construção dos Protótipos

Nesta seção serão apresentados os dois protótipos construídos a partir das alternativas definidas na [seção 4.2](#42-alternativas-divergentes), juntamente com os registros visuais de sua construção.

#### 4.4.1 Construção do Protótipo A: Interação Proativa e Contextual

##### Demonstração do Protótipo A

> **Inserir aqui a demonstração do vídeo referente à interação proativa e contextual.**

#### 4.4.2 Construção do Protótipo B: Interação Sob Demanda

##### Demonstração do Protótipo B

<div align="center">
<sub>Imagem 4.4.2 - Mockup da interface gráfica conversacional do agente — Interação Sob Demanda</sub><br>
  <img src="../assets/design/mockup-agente.png" width="100%" alt="Mockup da interface gráfica conversacional do agente para interação sob demanda"><br>
  <sup>Fonte: Material produzido pelos autores, 2026.</sup>
</div>


### 4.5 Diário de Construção dos Dois Protótipos

Esta seção registra, na ordem em que ocorreram, as decisões inesperadas, ambiguidades, dúvidas e limitações encontradas durante a construção de cada protótipo.

#### Protótipo A — Vídeo Encenado (Interação Proativa e Contextual)

> **Inserir aqui o diário de construção do Protótipo A.**

#### Protótipo B — Interface de Interação Sob Demanda

**20/08/2026 — Início da construção.** Decidimos partir da estrutura convencional de chatbot (sidebar de conversas, histórico de mensagens, campo de entrada), sem inovação de layout, para que a investigação ficasse concentrada no comportamento do agente e não na interface em si. A identidade visual usa a sinalização do Metrô (bolachas de linha, tipografia de placa, faixas de cor) apenas como camada de reconhecimento do contexto.

<div align="center">
<sub>Imagem 4.5.1 - Primeiro estado da interface: apenas interação por texto, ainda incompleta</sub><br>
  <img src="../assets/design/estado-1-somente-texto.png" width="100%" alt="Primeiro estado da interface do Protótipo B, com interação apenas por texto"><br>
  <sup>Fonte: Material produzido pelos autores, 2026.</sup>
</div>

**21/08/2026 — Decisão não prevista: duplicatas no SharePoint.** Ao montar a conversa de exemplo, foi preciso decidir o que o agente faz quando a busca retorna o mesmo documento em duas versões (uma recente e uma antiga em pasta "Antigos"). O grupo nunca tinha discutido isso. Para conseguir continuar, decidimos exibir as duas com um aviso amarelo de "versão possivelmente desatualizada" — mas a decisão real (ocultar a antiga? perguntar? mesclar?) permanece em aberto e foi registrada no [inventário da seção 4.9](#49-inventário-de-decisões-em-aberto).

**21/08/2026 — Ambiguidade: o que o agente responde a um pedido vago.** Ao simular o pedido "me manda o cronograma atualizado", não soubemos o que o sistema deveria fazer: escolher o mais provável? Listar todos? Perguntar? Improvisamos uma pergunta de desambiguação com botões de projeto. Ficou registrado como ambiguidade: o comportamento correto depende de conhecer a rotina real do PMO.

**22/08/2026 — Decisão não prevista: entrada por voz e transcrição incerta.** Ao adicionar a entrada por voz (exigência do contexto de PLN do módulo), a construção obrigou a decidir: (a) a transcrição aparece para o usuário ou fica oculta? (b) quando o reconhecimento tem baixa confiança em um termo (siglas internas como AMV, CCO), o agente busca assim mesmo ou confirma antes? Decidimos exibir a transcrição e confirmar antes de buscar — mas sem base em observação de usuários; foi o que o material exigiu para o protótipo funcionar. Ambas as decisões foram registradas no inventário da seção 4.9.

**24/08/2026 — Ambiguidade: o que a resposta por voz deveria falar.** O botão "ouvir resposta" existe na interface, mas não soubemos definir o que ele reproduz: o documento inteiro? Um resumo? Apenas "encontrei, veja na tela"? O protótipo não define — a reprodução é simulada. Registrado como lacuna do formato.

**O que o formato não permitiu representar:** a latência real do reconhecimento de voz; o comportamento do ASR com ruído de fundo (ambiente de estação); a conexão real com o SharePoint e o banco de dados (todas as respostas são fixas por palavra-chave, com um fallback de "não encontrei" para qualquer pedido fora do roteiro); e o Teams, citado na Alternativa A, que aqui não aparece.

<div align="center">
<sub>Imagem 4.5.2 - Estado intermediário: adição da entrada por voz, com microfone no campo de entrada e botões "ouvir resposta"</sub><br>
  <img src="../assets/design/estado-2-emoji.png" width="100%" alt="Estado intermediário da interface do Protótipo B, com entrada por voz e botões de ouvir resposta"><br>
  <sup>Fonte: Material produzido pelos autores, 2026.</sup>
</div>

<div align="center">
<sub>Imagem 4.5.3 - Estado intermediário: gravação de voz em andamento, com transcrição automática exibida e confirmação de termo com baixa confiança (AMV)</sub><br>
  <img src="../assets/design/estado-2-voz-emoji.png" width="100%" alt="Estado intermediário da interface do Protótipo B, com gravação de voz, transcrição automática e confirmação de termo com baixa confiança"><br>
  <sup>Fonte: Material produzido pelos autores, 2026.</sup>
</div>

<div align="center">
<sub>Imagem 4.5.4 - Estado final do Protótipo B: fluxo completo com bloqueio por permissão, entrada por voz com transcrição e reprodução da resposta em áudio</sub><br>
  <img src="../assets/design/prototipo-chatbot-metro.png" width="100%" alt="Estado final da interface conversacional do Protótipo B, com bloqueio por permissão, transcrição de voz e reprodução da resposta"><br>
  <sup>Fonte: Material produzido pelos autores, 2026.</sup>
</div>

### 4.6 Execução dos Protótipos

Esta seção registra como cada protótipo foi colocado em operação, incluindo situações difíceis, falhas, improvisos e lacunas encontradas durante a execução.

#### Protótipo A — Vídeo Encenado (Interação Proativa e Contextual)

> **Inserir aqui o registro de execução do Protótipo A.**

#### Protótipo B — Interface de Interação Sob Demanda

**Como foi rodado:** A sessão foi realizada em 25 de agosto de 2026, às 9h30, na biblioteca da faculdade, com duração aproximada de 30 minutos, com Roberto Filho, aluno de Engenharia de Software, fazendo o papel de analista de PMO do Metrô. O participante não acompanhou a construção da interface e recebeu apenas o contexto mínimo ("você é analista do PMO e precisa encontrar documentos e informações dos projetos"), sem tutorial ou demonstração prévia. A primeira parte da sessão foi de uso livre; na segunda, foram propostos pedidos fora do escopo coberto pelo protótipo. O registro foi feito por anotações durante a sessão e capturas de tela; não houve gravação de vídeo.

**O que aconteceu (não o que se esperava):**

| # | Pedido do participante | O que o protótipo fez | Falha / improviso / lacuna |
|---|------------------------|-----------------------|----------------------------|
| 1 | Uso livre inicial: localizar a conversa ativa, enviar mensagem de texto e iniciar gravação de áudio | O participante navegou sem nenhuma instrução, reconhecendo os elementos por semelhança com interfaces de chat que já utiliza | Nenhuma falha. Achado: o padrão convencional de interface elimina o custo de aprendizado — comportamento relevante para a comparação com a Alternativa A |
| 2 | Tentou gravar um áudio real e ouvir a resposta falada | A gravação, a transcrição e a reprodução são simuladas; a expectativa de funcionalidade real foi frustrada | **Improviso registrado:** foi preciso explicar verbalmente o que o sistema real faria. O protótipo não comunica seus próprios limites — a semelhança com produtos reais gera expectativa de funcionamento real |
| 3 | "quantas ocorrências teve na L2 em julho?" | Caiu no fallback "não encontrei documentos correspondentes", com o aviso de lacuna exibido na tela | **Lacuna confirmada:** pedido de dado estruturado, não de documento. O protótipo só define comportamento para busca de arquivos. Corresponde à decisão nº 5 do [inventário (seção 4.9)](#49-inventário-de-decisões-em-aberto), levantada na construção e confirmada na execução |

**Falhas encontradas:** O protótipo falhou diante de um pedido legítimo de informação (consulta a dado estruturado do banco, e não a um documento), caindo no fallback genérico. Além disso, falhou em comunicar sua própria natureza simulada: o participante esperava enviar e ouvir áudio de verdade.

**Improvisos registrados:** Em ambas as falhas foi necessário intervir verbalmente — explicar que a decisão sobre consultas ao banco está em aberto e que o fluxo de voz é simulado. Cada intervenção verbal indica um comportamento que o sistema real precisará definir.

<div align="center">
<sub>Imagem 4.6.1 - Fallback exibido durante a execução, diante do pedido de dado estruturado ("quantas ocorrências teve na L2 em julho?")</sub><br>
  <img src="../assets/design/execucao-fallback-dado-estruturado.png" width="100%" alt="Captura da interface exibindo o fallback de documento não encontrado durante o teste de execução"><br>
  <sup>Fonte: Material produzido pelos autores, 2026.</sup>
</div>

### 4.7 Comparação entre as Alternativas

<!-- Consolidação do grupo: comparar o que cada alternativa revelou, diferenças observadas, pontos que apareceram em apenas uma delas e surpresas encontradas. Abaixo, os insumos de cada protótipo. -->

**O que a interface conversacional (Protótipo B) tornou visível:** como o usuário formula pedidos em linguagem natural e quanta ambiguidade cabe numa frase curta; o problema das versões e duplicatas de documentos; o ciclo de confirmação exigido pela entrada por voz; e a fronteira entre pedido de documento e pedido de dado estruturado.

**O que só o vídeo encenado (Protótipo A) consegue mostrar e a interface não:** o momento e a frequência da iniciativa do agente ao longo do tempo de trabalho — na interface sob demanda esse eixo simplesmente não existe, pois toda interação depende de uma ação explícita do usuário.

**Confirmação entre construção e execução (Protótipo B):** a fronteira entre pedido de documento e pedido de dado estruturado — identificada como decisão em aberto durante a construção (decisão nº 5 do inventário) — foi encontrada espontaneamente pelo participante durante a execução, sem que ele tivesse conhecimento do inventário. A execução também revelou um ponto que a construção não havia antecipado: a semelhança do protótipo com produtos reais gera expectativa de funcionalidade real, o que favorece o reconhecimento imediato da interface, mas produz frustração quando a simulação é percebida.

> **Inserir aqui os insumos do Protótipo A e a consolidação da comparação pelo grupo.**

### 4.8 Limites dos Protótipos

Esta seção explicita o que cada protótipo **não** permite concluir e o que ainda dependeria de testes com usuários reais.

#### Limites do Protótipo A — Vídeo Encenado

> **Inserir aqui os limites específicos do Protótipo A.**

#### Limites do Protótipo B — Interface de Interação Sob Demanda

- **Respostas fixas por palavra-chave:** não há PLN real, então nada se conclui sobre a qualidade de interpretação dos pedidos.
- **Voz simulada:** nada se conclui sobre a taxa de erro do ASR com o jargão do Metrô nem sobre o comportamento com ruído de ambiente.
- **Sem SharePoint real:** nada se conclui sobre tempo de resposta, cobertura da base documental ou permissões reais.
- **O participante do teste foi Roberto Filho, aluno de Engenharia de Software, fazendo o papel de analista de PMO:** a formulação de pedidos de um colaborador real, com vocabulário e pressa reais, só seria observada com usuários do Metrô.
- **A execução foi registrada por anotações e capturas de tela, sem gravação de vídeo:** o registro depende do que foi anotado no momento; reações e hesitações do participante não ficaram integralmente documentadas.

### 4.9 Inventário de Decisões em Aberto

Esta seção reúne as decisões de design e comportamento do agente que a construção dos protótipos revelou, mas que permanecem sem resposta definitiva. Para cada uma, registram-se as opções consideradas e o que está em jogo.

<!-- Mesclar aqui as decisões em aberto vindas do Protótipo A. -->

1. **Duplicatas e versões antigas no SharePoint.** Opções: (a) mostrar todas as versões com aviso; (b) mostrar só a mais recente e ocultar antigas; (c) perguntar ao usuário. Em jogo: risco de o colaborador usar documento desatualizado vs. poluição da resposta e desconfiança ("cadê o arquivo que eu sei que existe?").

2. **Transcrição de voz com baixa confiança em termos técnicos.** Opções: (a) buscar com o melhor palpite; (b) confirmar antes de buscar; (c) buscar e sinalizar a incerteza junto do resultado. Em jogo: fluidez da interação vs. risco de busca errada com jargão interno (AMV, CCO, via permanente) — central para o módulo de PLN.

3. **Exibição da transcrição.** Opções: (a) sempre visível; (b) oculta, só a resposta; (c) visível apenas quando houver incerteza. Em jogo: transparência e possibilidade de correção vs. ruído visual.

4. **O que a resposta por voz reproduz.** Opções: (a) leitura do documento; (b) resumo gerado; (c) apenas confirmação verbal ("encontrei, está na tela"). Em jogo: uso com mãos ocupadas / em deslocamento vs. tempo de escuta e risco de resumo impreciso.

5. **Pedido de dado estruturado vs. documento.** O protótipo só devolve arquivos; pedidos como "quantas ocorrências teve na L2" não têm comportamento definido. Opções: (a) responder consultando o banco; (b) devolver o documento-fonte; (c) declarar que só localiza documentos. Em jogo: escopo do agente e expectativa do usuário sobre o que ele "sabe".

6. **Acesso negado por permissão.** Opções: (a) ocultar o documento como se não existisse; (b) mostrar que existe e oferecer solicitação de acesso; (c) mostrar metadados mas não o conteúdo. Em jogo: transparência e agilidade vs. exposição de informação restrita (até o nome de um contrato pode ser sensível).

### 4.10 Repertório de Situações

Esta seção registra os casos e situações usados durante a construção e a execução dos protótipos, com destaque para aqueles que não foram atendidos.

#### Situações do Protótipo A

> **Inserir aqui as situações usadas no Protótipo A.**

#### Situações do Protótipo B

Situações embutidas na construção da interface:

- "preciso do último relatório de manutenção preventiva da linha 1" — **atendida**
- "me manda o cronograma atualizado" — **ambígua**; o protótipo respondeu com pergunta de desambiguação
- "abre o contrato de concessão da linha 4 pra mim" — **bloqueada por permissão**
- (voz) "acha pra mim o laudo do AMV da estação Sé" — sigla com baixa confiança na transcrição; o protótipo **pediu confirmação** antes de buscar

Situações registradas durante a execução (sessão com participante externo à construção):

- Uso livre da interface (localizar conversa, enviar texto, iniciar gravação) — **atendida sem instrução**, por reconhecimento do padrão convencional de chat
- Tentativa de enviar áudio real e ouvir a resposta falada — **não atendida**: funcionalidade simulada; exigiu explicação verbal
- "quantas ocorrências teve na L2 em julho?" — **não atendida**: pedido de dado estruturado; o protótipo caiu no fallback por só definir comportamento para busca de documentos

### 4.11 Registros Visuais

Esta seção reúne as evidências brutas da construção e da execução dos protótipos (fotos, vídeos, storyboard, desenhos e capturas de tela).

#### Registros do Protótipo A

> **Inserir aqui os registros visuais do Protótipo A (fotos do set, frames do vídeo, storyboard).**

#### Registros do Protótipo B

Os registros da construção da interface estão inseridos na [seção 4.5](#45-diário-de-construção-dos-dois-protótipos), na ordem em que os estados foram produzidos:

- **Imagem 4.5.1** — primeiro estado da interface, apenas com interação por texto ([estado-1-somente-texto.png](../assets/design/estado-1-somente-texto.png));
- **Imagem 4.5.2** — estado intermediário, com a adição da entrada por voz e dos botões "ouvir resposta" ([estado-2-emoji.png](../assets/design/estado-2-emoji.png));
- **Imagem 4.5.3** — estado intermediário, com gravação de voz, transcrição automática e confirmação de termo com baixa confiança ([estado-2-voz-emoji.png](../assets/design/estado-2-voz-emoji.png));
- **Imagem 4.5.4** — estado final do protótipo, com o fluxo completo de voz e permissões ([prototipo-chatbot-metro.png](../assets/design/prototipo-chatbot-metro.png));
- **Imagem 4.4.2** — mockup da interface apresentado na demonstração ([mockup-agente.png](../assets/design/mockup-agente.png)).

A execução do Protótipo B foi registrada por anotações feitas durante a sessão e por capturas de tela. A principal evidência da execução é a Imagem 4.6.1 ([execucao-fallback-dado-estruturado.png](../assets/design/execucao-fallback-dado-estruturado.png)), que mostra o protótipo falhando diante do pedido de dado estruturado. Não houve gravação de vídeo da sessão.

---

# 3. Registro de Decisões

Esta seção registra as principais decisões técnicas, de escopo e de processo tomadas durante a Sprint 1. O registro segue o formato: decisão, contexto, alternativas consideradas, justificativa, impacto, participantes, data e status.

| ID  | Decisão | Contexto | Alternativas consideradas | Justificativa | Impacto | Participantes | Data | Status |
| --- | ------- | -------- | ------------------------- | ------------- | ------- | ------------- | ---- | ------ |
| D01 | Validar o MVP exclusivamente com dados sintéticos | O TAPI proíbe o uso de dados corporativos sensíveis fora do ambiente homologado do Metrô | Utilizar dados reais anonimizados; solicitar acesso ao ambiente de homologação | Restrição de confidencialidade do parceiro; ambiente de produção não será disponibilizado durante o módulo | Nenhuma integração com o portfólio real no MVP; todas as validações do pipeline ocorrem sobre dados construídos pela equipe | Equipe | **PENDENTE DE VALIDAÇÃO DA EQUIPE** | Aprovada |
| D02 | Desenvolver interface própria no MVP, sem integrar diretamente o ecossistema Microsoft | O parceiro utiliza Microsoft Copilot Studio e Power Platform, mas o acesso ao ambiente corporativo depende de aprovação de TI e compliance | Desenvolver diretamente no Copilot Studio; aguardar liberação de acesso antes de iniciar o desenvolvimento | A liberação de acesso tem alta probabilidade de atraso (AM3, probabilidade 70%); a arquitetura desacoplada permite futuras integrações sem reescrita | O MVP é demonstrado em ambiente próprio da equipe; o material de correspondência com o ecossistema Microsoft é entregue separadamente | Equipe | **PENDENTE DE VALIDAÇÃO DA EQUIPE** | Aprovada |
| D03 | Manter o núcleo de PLN desacoplado das aplicações clientes e exposto por APIs REST | Premissa do parceiro de que a plataforma de gestão de portfólio pode ser substituída no futuro | Acoplar o pipeline ao Copilot Studio; desenvolver sem separação formal de camadas | Desacoplamento reduz o custo de migração e é requisito direto do RNF05; também sustenta a oportunidade OP1 da matriz de riscos | O pipeline pode ser consumido por qualquer aplicação cliente sem duplicação das regras de negócio | Equipe | **PENDENTE DE VALIDAÇÃO DA EQUIPE** | Aprovada |
| D04 | RF06 (Atualizar cadastro de projetos) não recebe diagrama de sequência na Sprint 1 | RF06 tem prioridade baixa e representa variação do cenário 2; no MVP, gera apenas sugestão copiável sem escrita nas fontes | Modelar RF06 com diagrama próprio; incluir fluxo de confirmação explícita | O comportamento sugestivo do RF06 é coberto pela modelagem do cenário 2; a escrita com confirmação pertence à evolução futura | A ausência de diagrama é declarada explicitamente no documento como limitação desta sprint e não como omissão | Equipe | **PENDENTE DE VALIDAÇÃO DA EQUIPE** | Aprovada |
| D05 | Cenários de sequência representam apenas o fluxo principal nesta sprint | Os desvios (rejeição de intenção desconhecida, esclarecimento de parâmetros, falha de transcrição, indisponibilidade de fonte) aumentariam significativamente a complexidade dos diagramas | Incluir todos os fragmentos alternativos desde a Sprint 1; dividir cada cenário em diagrama principal e diagrama de exceção | Privilegiar legibilidade na primeira especificação; os desvios entram na Sprint 2 conforme registrado no documento | Os critérios de aceitação dos RFs descrevem os desvios, mas eles não aparecem graficamente nesta sprint | Equipe | **PENDENTE DE VALIDAÇÃO DA EQUIPE** | Aprovada |
| D06 | RNF09 substituído de "Tratamento de ambiguidades" para "Auditabilidade das interações" | A equipe não possuía informações suficientes para sustentar metas mensuráveis para o RNF09 original; o componente de auditoria já estava presente na arquitetura (seção 2.4) sem requisito formal correspondente | Manter o RNF09 original com metas pendentes; remover o requisito sem substituição | Auditabilidade é exigência direta das restrições de rastreabilidade do parceiro e estava prevista na arquitetura sem cobertura por requisito não funcional | O RNF09 de auditabilidade passou a cobrir o componente "Auditoria e Feedback" da solução técnica; o tratamento de ambiguidades permanece como comportamento descrito nos critérios de aceitação do RF02 | Equipe | 2026-08-14 | Aprovada |

# 4. Fontes

- ANPTrilhos. [Balanço do Setor Metroferroviário 2024](https://anptrilhos.org.br/balanco-metroferroviario-2024-transporte-sobre-trilhos-cresce-e-transporta-257-bilhoes-de-passageiros/). Acesso em ago. 2026.
- Microsoft. [Design effective language understanding — Microsoft Copilot Studio](https://learn.microsoft.com/en-us/microsoft-copilot-studio/guidance/language-understanding). Acesso em ago. 2026.
- Metrô/CPTM. [Guia do Metrô de São Paulo em 2026](https://www.metrocptm.com.br/guia-do-metro-de-sao-paulo-em-2026-linhas-operacao-e-como-usar-o-sistema/). Acesso em ago. 2026.
- Rasa. [Intents and Entities — Rasa Documentation](https://rasa.com/docs/reference/primitives/intents-and-entities/). Acesso em ago. 2026.
- Wikipédia. [Metropolitano de São Paulo](https://pt.wikipedia.org/wiki/Metropolitano_de_S%C3%A3o_Paulo). Acesso em ago. 2026.
