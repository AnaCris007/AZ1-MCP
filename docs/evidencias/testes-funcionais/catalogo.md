# Catálogo operacional da campanha funcional

Fichas herdadas de Projeto.md, Seções 6.2.3 e 6.2.6. Pré-condições e massas: Seções 6.1.3 e 6.2.3. Preparar o estado, executar a entrada, comparar todos os observáveis, registrar e restaurar. Estados abaixo são resultados desta campanha, não a coluna histórica de prontidão.

## CT-RF01-01

Estado: **Parcial**. Variantes executadas não atendem todas as pré-condições/observáveis da ficha; não contabilizar aprovação integral.

- **Propósito:** Confirmar que os quatro formatos aceitos entram no sistema e ficam armazenados
- **Procedimento:** Enviar `POST /api/v1/audio` com `multipart/form-data`, campo `audio`, usando cada um dos quatro arquivos do conjunto A
- **Resultado esperado:** `201` com corpo `{"id": "...", "status": "received", "message": "Áudio recebido com sucesso."}` e objeto gravado sob `incoming/{audio_id}`
- **Critério de aprovação:** Os quatro formatos do conjunto A aprovados, sem exceção
- **Evidência a registrar:** Código HTTP, corpo da resposta e presença do objeto sob `incoming/{audio_id}` no bucket

## CT-RF01-02

Estado: **Bloqueado**. Falta execução navegador/microfone real ou gravações faladas nos quatro formatos; comparação comum de intenção pendente.

- **Propósito:** Confirmar que o áudio armazenado é convertido em texto com os metadados do reconhecimento
- **Procedimento:** Preparar upload próprio e, a partir do `audio_id` retornado, enviar `POST /api/v1/audio/{audio_id}/transcribe?language=pt-BR`
- **Resultado esperado:** `200` com `text` não vazio, `language` igual a `pt-BR`, `confidence` numérico ou nulo conforme schema e `duration_seconds` compatível com a gravação
- **Critério de aprovação:** Transcrição inteligível em todos os quatro áudios; a fidelidade é medida no teste de RNF06 da Seção 6.3
- **Evidência a registrar:** Código HTTP e os campos `text`, `language`, `confidence` e `duration_seconds`

## CT-RF01-03

Estado: **Parcial**. Variantes executadas não atendem todas as pré-condições/observáveis da ficha; não contabilizar aprovação integral.

- **Propósito:** Confirmar que o usuário vê e pode conferir a transcrição antes de ela ser processada
- **Procedimento:** Pela interface, gravar uma solicitação por voz e acompanhar a tela até a resposta
- **Resultado esperado:** A transcrição é exibida na tela e permanece visível antes de a solicitação seguir para processamento
- **Critério de aprovação:** A transcrição precede a resposta na tela e é legível pelo usuário
- **Evidência a registrar:** Se a transcrição aparece na tela **antes** de a resposta ser solicitada, e se o usuário pode conferi-la nesse intervalo

## CT-RF01-04

Estado: **Aprovado controlado**. Todos os observáveis deste caso passaram no recorte controlado; não comprova SSO/modelo externo real.

- **Propósito:** Confirmar que a solicitação em texto é processada sem passar pelo canal de voz
- **Procedimento:** Enviar `POST /api/v1/chat` com `{"message": "...", "conversation_id": "..."}` usando cinco solicitações do conjunto C
- **Resultado esperado:** `200` com `reply` em texto não vazio
- **Critério de aprovação:** Cinco solicitações de cinco aprovadas
- **Evidência a registrar:** Código HTTP e o campo `reply`, verificando que é texto não vazio

## CT-RF01-05

Estado: **Bloqueado**. Falta execução navegador/microfone real ou gravações faladas nos quatro formatos; comparação comum de intenção pendente.

- **Propósito:** Confirmar que os dois canais de entrada levam ao mesmo entendimento da solicitação
- **Procedimento:** Submeter a mesma solicitação pelos dois canais: gravada em áudio do conjunto A e digitada em texto; comparar a intenção classificada nos dois caminhos
- **Resultado esperado:** Resposta textual nos dois canais; intenção equivalente quando o pipeline comum existir
- **Critério de aprovação:** Todas as cinco duplas apresentam texto. `/chat` não retorna intenção; essa comparação depende de integração/instrumentação. Não atribuir divergência à transcrição sem evidência
- **Evidência a registrar:** Resposta textual; intenção/confiança somente quando expostas pelo fluxo integrado

## CT-RF01-06

Estado: **Aprovado controlado**. Todos os observáveis deste caso passaram no recorte controlado; não comprova SSO/modelo externo real.

- **Propósito:** Confirmar que formato fora da lista é recusado como formato, e não como arquivo inválido
- **Procedimento:** `POST /api/v1/audio` com o arquivo `.ogg` do conjunto B
- **Resultado esperado:** `415` com `error` igual a `unsupported_format`
- **Critério de aprovação:** Correspondência exata de código HTTP e de `error`
- **Evidência a registrar:** Código HTTP e o campo `error` do corpo

## CT-RF01-07

Estado: **Aprovado controlado**. Todos os observáveis deste caso passaram no recorte controlado; não comprova SSO/modelo externo real.

- **Propósito:** Confirmar que o limite de 10 MB é aplicado antes de qualquer processamento
- **Procedimento:** `POST /api/v1/audio` com o arquivo de 12 MB
- **Resultado esperado:** `413` com `error` igual a `file_too_large`
- **Critério de aprovação:** Correspondência exata
- **Evidência a registrar:** Código HTTP e o campo `error`

## CT-RF01-08

Estado: **Aprovado controlado**. Todos os observáveis deste caso passaram no recorte controlado; não comprova SSO/modelo externo real.

- **Propósito:** Confirmar que o limite de 5 minutos é aplicado sobre a duração real, e não sobre o tamanho
- **Procedimento:** `POST /api/v1/audio` com a gravação de 6 minutos
- **Resultado esperado:** `422` com `error` igual a `audio_too_long`
- **Critério de aprovação:** Correspondência exata
- **Evidência a registrar:** Código HTTP e o campo `error`

## CT-RF01-09

Estado: **Aprovado controlado**. Todos os observáveis deste caso passaram no recorte controlado; não comprova SSO/modelo externo real.

- **Propósito:** Confirmar que arquivo vazio e arquivo corrompido são recusados pelo conteúdo binário
- **Procedimento:** `POST /api/v1/audio` com o arquivo de zero byte e, em seguida, com o `.wav` truncado
- **Resultado esperado:** `422` com `error` igual a `invalid_audio` nos dois envios
- **Critério de aprovação:** Correspondência exata nos dois
- **Evidência a registrar:** Código HTTP e o campo `error` em cada envio

## CT-RF01-10

Estado: **Aprovado controlado**. Todos os observáveis deste caso passaram no recorte controlado; não comprova SSO/modelo externo real.

- **Propósito:** Confirmar que requisição estruturalmente inválida é distinguida de arquivo inválido
- **Procedimento:** `POST /api/v1/audio` com corpo `application/json`, e não `multipart/form-data`
- **Resultado esperado:** `422` com `detail` apontando campo `audio` ausente para corpo JSON
- **Critério de aprovação:** Nenhum armazenamento; `400 bad_request` é erro de parsing HTTP/multipart, não este caso
- **Evidência a registrar:** Código HTTP e o campo `error`

## CT-RF01-11

Estado: **Aprovado controlado**. Todos os observáveis deste caso passaram no recorte controlado; não comprova SSO/modelo externo real.

- **Propósito:** Confirmar que identificador inexistente não é tratado como falha do provedor externo
- **Procedimento:** `POST /api/v1/audio/aud_inexistente/transcribe`
- **Resultado esperado:** `404` com `error` igual a `audio_not_found`
- **Critério de aprovação:** Correspondência exata
- **Evidência a registrar:** Código HTTP e o campo `error`

## CT-RF01-12

Estado: **Parcial**. Variantes executadas não atendem todas as pré-condições/observáveis da ficha; não contabilizar aprovação integral.

- **Propósito:** Confirmar que a falha do serviço externo chega ao cliente como erro previsto, sem vazar exceção
- **Procedimento:** Executar a transcrição com o provedor de Speech to Text configurado para falhar, usando a resposta de erro armazenada conforme a Seção 6.4.3
- **Resultado esperado:** `502` com `error` igual a `transcription_failed` e mensagem orientando nova tentativa
- **Critério de aprovação:** Correspondência exata, e ausência de rastro de exceção no corpo devolvido
- **Evidência a registrar:** Código HTTP, o campo `error` e a mensagem devolvida ao cliente

## CT-RF01-13

Estado: **Aprovado controlado**. Todos os observáveis deste caso passaram no recorte controlado; não comprova SSO/modelo externo real.

- **Propósito:** Confirmar que mensagem vazia é recusada antes de consumir o modelo de linguagem
- **Procedimento:** `POST /api/v1/chat` com `message` vazia e, em seguida, com apenas espaços
- **Resultado esperado:** `422` com `error` igual a `empty_message` nos dois envios
- **Critério de aprovação:** Correspondência exata nos dois
- **Evidência a registrar:** Código HTTP e o campo `error` em cada envio

## CT-RF01-14

Estado: **Aprovado controlado**. Todos os observáveis deste caso passaram no recorte controlado; não comprova SSO/modelo externo real.

- **Propósito:** Confirmar que o limite de 4.000 caracteres da mensagem é aplicado
- **Procedimento:** `POST /api/v1/chat` com `message` de 4.001 caracteres
- **Resultado esperado:** `422` com `error` igual a `message_too_long`
- **Critério de aprovação:** Correspondência exata
- **Evidência a registrar:** Código HTTP e o campo `error`

## CT-RF01-15

Estado: **Parcial**. Variantes executadas não atendem todas as pré-condições/observáveis da ficha; não contabilizar aprovação integral.

- **Propósito:** Confirmar que a indisponibilidade do backend é comunicada, e não substituída por conteúdo de exemplo
- **Procedimento:** Pela interface, enviar uma mensagem com o backend interrompido
- **Resultado esperado:** A interface informa que o serviço está indisponível
- **Critério de aprovação:** Nenhum conteúdo de demonstração é apresentado como resposta do agente
- **Evidência a registrar:** O que a tela apresenta ao usuário: mensagem de erro identificável ou resposta indistinguível de uma resposta real

## CT-RF01-16

Estado: **Aprovado controlado**. Todos os observáveis deste caso passaram no recorte controlado; não comprova SSO/modelo externo real.

- **Requisito e componente:** RF01; recepção
- **Propósito:** Limites / positivo e negativo
- **Procedimento:** 1. Preparar áudio válido com 10 MiB e outro com 10 MiB + 1 byte; durações de 300 s e acima de 300 s, isolando tamanho/duração. 2. Enviar cada arquivo. 3. Contar gravações
- **Resultado esperado:** Limites exatos aceitos se o arquivo for válido; acima do tamanho: 413; acima da duração: 422 `audio_too_long`; nenhum objeto para rejeitados

## CT-RF01-17

Estado: **Aprovado controlado**. Todos os observáveis deste caso passaram no recorte controlado; não comprova SSO/modelo externo real.

- **Requisito e componente:** RF01; sondagem
- **Propósito:** MIME falso / negativo e alternativo
- **Procedimento:** 1. Preparar WAV real com MIME genérico e arquivo texto anunciado como WAV. 2. Enviar por multipart. 3. Relê-los no bucket quando aceitos
- **Resultado esperado:** Conteúdo válido aceito pela assinatura; conteúdo não áudio recebe 415, sem persistência. Não rejeitar um WAV válido apenas pelo nome ou MIME

## CT-RF01-18

Estado: **Aprovado controlado**. Todos os observáveis deste caso passaram no recorte controlado; não comprova SSO/modelo externo real.

- **Requisito e componente:** RF01; chat/TTS
- **Propósito:** Limite textual / positivo e negativo
- **Procedimento:** 1. Preparar mensagens com 3999, 4000 e 4001 caracteres após trim, além de espaços externos. 2. Enviar ao chat; repetir como `text` no TTS. 3. Contar chamadas externas
- **Resultado esperado:** Até 4000 seguem ao provedor; 4001 recebe 422 com código específico; vazia recebe 422. Entrada inválida não consome geração

## CT-RF01-19

Estado: **Parcial**. Variantes executadas não atendem todas as pré-condições/observáveis da ficha; não contabilizar aprovação integral.

- **Requisito e componente:** RF01; interface
- **Propósito:** Corrigir/desistir / alternativo
- **Procedimento:** 1. Gravar áudio e aguardar transcrição. 2. Editar um nome e confirmar; repetir com descarte. 3. Inspecionar rede
- **Resultado esperado:** Chat recebe apenas texto confirmado/editado; descarte não chama chat. Captura da tela e ordem das chamadas comprovam conferência prévia

## CT-RF02-01

Estado: **Bloqueado**. Base cega independente e entidades de referência não disponibilizadas/congeladas; não usar base saturada para aceitar requisito.

- **Propósito:** Confirmar que solicitação sobre projeto é reconhecida como consulta ao portfólio
- **Procedimento:** Submeter dez solicitações do conjunto C rotuladas como `consultar_projeto_sintetico` a `POST /api/v1/audio/{audio_id}/analyze` ou diretamente ao classificador
- **Resultado esperado:** Intenção `consultar_projeto_sintetico` nas dez solicitações
- **Critério de aprovação:** Registrar dez previsões; aprovação estatística exclusivamente em CT-RNF03-P/N, sem inferir F1 a partir de nove acertos
- **Evidência a registrar:** Intenção prevista, confiança e rótulo esperado de cada solicitação

## CT-RF02-02

Estado: **Bloqueado**. Base cega independente e entidades de referência não disponibilizadas/congeladas; não usar base saturada para aceitar requisito.

- **Propósito:** Confirmar que solicitação sobre norma é distinguida de solicitação sobre projeto
- **Procedimento:** Repetir com dez solicitações rotuladas como `consultar_documentos_normativos`
- **Resultado esperado:** Intenção e confiança nas dez solicitações normativas
- **Critério de aprovação:** Registrar dez previsões; métricas e aprovação agregada em CT-RNF03-P/N
- **Evidência a registrar:** Os mesmos campos

## CT-RF02-03

Estado: **Bloqueado**. Base cega independente e entidades de referência não disponibilizadas/congeladas; não usar base saturada para aceitar requisito.

- **Propósito:** Medir se o classificador separa as dez classes do catálogo em condição não vista no treinamento
- **Procedimento:** Executar o protocolo cego de CT-RNF03-P/N e apurar F1-macro, cobertura, rejeição e matriz de confusão
- **Resultado esperado:** Relatório do conjunto cego de CT-RNF03-P/N
- **Critério de aprovação:** F1-macro ≥ 0,85, cobertura ≥ 90%, aceitação indevida ≤ 15%; acurácia complementar, sem piso por classe inventado
- **Evidência a registrar:** F1-macro, precisão/recall/F1 por classe, cobertura, aceitação indevida e confusões

## CT-RF02-04

Estado: **Bloqueado**. Massa E/F e recuperação vetorial real com versões, referências e gabaritos dedicados não provisionadas nesta campanha.

- **Propósito:** Confirmar que o projeto nomeado na solicitação é associado ao registro correto
- **Procedimento:** Submeter dez solicitações que nomeiem projetos do conjunto E e verificar a entidade extraída e o registro correspondente
- **Resultado esperado:** A entidade `nome_projeto` é extraída e associada ao registro correto
- **Critério de aprovação:** Correspondência correta em pelo menos nove das dez solicitações, conforme o indicador de 90% da Seção 2.1
- **Evidência a registrar:** Entidade extraída, registro associado e se corresponde ao projeto nomeado

## CT-RF02-05

Estado: **Bloqueado**. Massa E/F e recuperação vetorial real com versões, referências e gabaritos dedicados não provisionadas nesta campanha.

- **Propósito:** Confirmar que o dado devolvido vem da fonte, e não da geração livre do modelo
- **Procedimento:** Consultar cinco dados específicos de projetos do conjunto E e comparar o valor devolvido com o registro na fonte
- **Resultado esperado:** O valor devolvido é idêntico ao registrado na fonte
- **Critério de aprovação:** Coincidência exata nas cinco consultas
- **Evidência a registrar:** Valor devolvido, valor na fonte e se coincidem

## CT-RF02-06

Estado: **Reprovado**. Observável obrigatório divergente; consultar funcionais.json e registro de defeitos.

- **Propósito:** Confirmar que o esclarecimento pede apenas o que falta e preserva o que já foi informado
- **Procedimento:** Enviar "qual é o status do projeto?", sem nomear o projeto; responder à pergunta de esclarecimento com o nome; verificar se o dado originalmente pedido foi preservado
- **Resultado esperado:** O agente pergunta qual é o projeto, e a resposta final traz o dado originalmente pedido
- **Critério de aprovação:** O pedido original é preservado; o usuário não precisa reformular a pergunta inteira
- **Evidência a registrar:** Texto da pergunta de esclarecimento, resposta final e se o pedido original foi mantido

## CT-RF02-07

Estado: **Reprovado**. Observável obrigatório divergente; consultar funcionais.json e registro de defeitos.

- **Propósito:** Confirmar que pedido fora do escopo é recusado antes de qualquer consulta às fontes
- **Procedimento:** Submeter as vinte solicitações do conjunto D e observar a classificação e a resposta
- **Resultado esperado:** Intenção `fora_do_catalogo`, resposta explicando o limite e indicando as interações disponíveis, sem registro de consulta às fontes
- **Critério de aprovação:** No máximo três de vinte aceitas indevidamente, conforme RNF03; todas as rejeitadas informam limite sem consultar fontes. Verificar chamadas com spy, além da auditoria
- **Evidência a registrar:** Intenção atribuída, teor da resposta e, nos registros de auditoria, se houve consulta às fontes

## CT-RF02-08

Estado: **Bloqueado**. Massa E/F e recuperação vetorial real com versões, referências e gabaritos dedicados não provisionadas nesta campanha.

- **Propósito:** Confirmar que o agente admite não ter o dado em vez de fabricá-lo
- **Procedimento:** Consultar um projeto que não existe no conjunto E
- **Resultado esperado:** O agente declara não ter encontrado o projeto
- **Critério de aprovação:** Nenhuma resposta apresenta dado sobre projeto inexistente; o caso é a verificação direta do risco de alucinação registrado na Seção 1.9.2
- **Evidência a registrar:** Teor da resposta, verificando se declara não ter encontrado o projeto ou se apresenta conteúdo fabricado

## CT-RF02-09

Estado: **Bloqueado**. Massa E/F e recuperação vetorial real com versões, referências e gabaritos dedicados não provisionadas nesta campanha.

- **Propósito:** Confirmar que a resposta dentro de um fluxo guiado não reinicia a classificação de intenção
- **Procedimento:** Iniciar um fluxo guiado, responder à pergunta do agente com um valor simples, como uma data, e observar se o sistema trata a resposta como preenchimento de entidade ou como nova intenção
- **Resultado esperado:** A resposta é tratada como preenchimento da entidade em curso, sem nova classificação de intenção
- **Critério de aprovação:** O fluxo guiado avança para o passo seguinte, conforme a regra da Seção 3.1
- **Evidência a registrar:** Estado do fluxo após a resposta e intenção registrada, se houver

## CT-RF02-10

Estado: **Fora do recorte**. D04/D07; preservar caso histórico; escrita futura não entra no aceite do MVP.

- **Propósito:** Confirmar que o alcance do perfil limita o que é devolvido
- **Procedimento:** Autenticado como líder do projeto P1, consultar um dado do projeto P2, liderado por outro perfil
- **Resultado esperado:** O dado de P2 não é devolvido, e a tentativa é registrada
- **Critério de aprovação:** Nenhum dado de P2 aparece na resposta
- **Evidência a registrar:** Código HTTP, teor da resposta e registro de auditoria da tentativa

## CT-RF02-11

Estado: **Bloqueado**. Massa E/F e recuperação vetorial real com versões, referências e gabaritos dedicados não provisionadas nesta campanha.

- **Requisito e componente:** RF02; diálogo
- **Propósito:** Projetos semelhantes / alternativo
- **Procedimento:** 1. Criar dois projetos sintéticos de nomes semelhantes. 2. Perguntar pelo nome ambíguo. 3. Selecionar um e manter o indicador pedido
- **Resultado esperado:** Pergunta específica de esclarecimento antes da consulta de dados de negócio; resposta final só do projeto escolhido, sem mistura

## CT-RF02-12

Estado: **Bloqueado**. Massa E/F e recuperação vetorial real com versões, referências e gabaritos dedicados não provisionadas nesta campanha.

- **Requisito e componente:** RF02/RF03; recuperação
- **Propósito:** Fonte indisponível / erro
- **Procedimento:** 1. Preparar consulta com fonte conhecida. 2. Injetar falha de rede e timeout em rodadas separadas. 3. Inspecionar tentativas e resposta
- **Resultado esperado:** Aviso de indisponibilidade, sem fato fabricado; no fluxo arquitetural futuro, até duas tentativas da Seção 2.2.3. Registrar backoff e timeout efetivos do adaptador antes da rodada; o conjunto de tentativas deve respeitar o teto textual do RNF01

## CT-RF02-13

Estado: **Bloqueado**. Massa E/F e recuperação vetorial real com versões, referências e gabaritos dedicados não provisionadas nesta campanha.

- **Requisito e componente:** RF02/RF03/RNF12; recuperação
- **Propósito:** Atualização/conflito / negativo
- **Procedimento:** 1. Preparar versões antiga e recente com valores conflitantes e datas conhecidas. 2. Consultar antes e depois de reindexar. 3. Inspecionar fonte exibida
- **Resultado esperado:** Não apresentar dado antigo como atual nem misturar versões sem aviso; fonte/data corretas e conflito declarado. Comparar a data e a versão de cada fonte com o gabarito; conflito não resolvido deve ser explicitado ao usuário

## CT-RF02-14

Estado: **Bloqueado**. Base cega independente e entidades de referência não disponibilizadas/congeladas; não usar base saturada para aceitar requisito.

- **Requisito e componente:** RF02; extração
- **Propósito:** Variações linguísticas / positivo e negativo
- **Procedimento:** 1. Congelar dez consultas com entidades anotadas, incluindo nome, data, indicador, sinônimo, erro ortográfico e negação. 2. Executar pipeline. 3. Comparar spans/valores e registro associado
- **Resultado esperado:** Extração correta / entidades de referência ≥ 85% e associação correta em ≥ 9/10 consultas, metas da Seção 2.1; reportar entidades espúrias separadamente; ausência deve pedir esclarecimento

## CT-RF03-01

Estado: **Bloqueado**. Massa E/F e recuperação vetorial real com versões, referências e gabaritos dedicados não provisionadas nesta campanha.

- **Propósito:** Confirmar que os três elementos de origem acompanham o dado de negócio
- **Procedimento:** Consultar um dado de projeto cuja origem seja um único artefato do conjunto F
- **Resultado esperado:** A resposta traz documento de origem, referência e data da última atualização
- **Critério de aprovação:** Os três elementos presentes; a ausência de qualquer um reprova o caso
- **Evidência a registrar:** Os três elementos exigidos na resposta: documento, referência e data

## CT-RF03-02

Estado: **Bloqueado**. Massa E/F e recuperação vetorial real com versões, referências e gabaritos dedicados não provisionadas nesta campanha.

- **Propósito:** Confirmar que nenhuma fonte usada na composição da resposta é omitida
- **Procedimento:** Formular uma consulta cuja resposta exija combinar dois artefatos distintos
- **Resultado esperado:** As duas fontes utilizadas são listadas
- **Critério de aprovação:** Nenhuma fonte utilizada fica omitida
- **Evidência a registrar:** Quantidade de fontes listadas e se corresponde às efetivamente utilizadas

## CT-RF03-03

Estado: **Bloqueado**. Massa E/F e recuperação vetorial real com versões, referências e gabaritos dedicados não provisionadas nesta campanha.

- **Propósito:** Confirmar que a referência é acionável, e não apenas presente na tela
- **Procedimento:** Preparar consulta própria com fonte conhecida e tomar a referência exibida e tentar localizar o documento no repositório a partir dela
- **Resultado esperado:** O documento é localizado no repositório a partir da referência exibida
- **Critério de aprovação:** A localização ocorre sem informação além da referência
- **Evidência a registrar:** Se a referência levou ao documento correto, sem informação adicional

## CT-RF03-04

Estado: **Bloqueado**. Massa E/F e recuperação vetorial real com versões, referências e gabaritos dedicados não provisionadas nesta campanha.

- **Propósito:** Confirmar que dado sem origem não é apresentado como fundamentado
- **Procedimento:** Consultar o dado de negócio que, no conjunto F, não possui artefato de origem
- **Resultado esperado:** O agente declara não haver fonte para o dado, ou não o apresenta
- **Critério de aprovação:** O dado não é apresentado como fundamentado
- **Evidência a registrar:** Se a resposta declara a ausência de fonte ou apresenta o dado como fundamentado

## CT-RF03-05

Estado: **Bloqueado**. Massa E/F e recuperação vetorial real com versões, referências e gabaritos dedicados não provisionadas nesta campanha.

- **Propósito:** Confirmar que a lacuna de data é declarada em vez de preenchida
- **Procedimento:** Consultar o dado cujo artefato de origem está sem `data` preenchida
- **Resultado esperado:** O agente indica que a data de atualização não está disponível
- **Critério de aprovação:** Nenhuma data vazia, nula ou estimada é exibida
- **Evidência a registrar:** Se a resposta indica a lacuna ou exibe data vazia, nula ou inventada

## CT-RF03-06

Estado: **Bloqueado**. Massa E/F e recuperação vetorial real com versões, referências e gabaritos dedicados não provisionadas nesta campanha.

- **Requisito e componente:** RF03/RNF12; fontes
- **Propósito:** Referência incorreta/inacessível / negativo
- **Procedimento:** 1. Preparar referência inexistente, referência de outro documento e fonte temporariamente inacessível. 2. Consultar e abrir cada referência. 3. Confrontar citação com conteúdo
- **Resultado esperado:** Não declarar referência errada como válida; avisar limitação e preservar autoria/data conhecidas. Acesso por cargo não é imposto: D07; acesso administrativo permanece RNF09

## CT-RF04-01

Estado: **Bloqueado**. Fluxo integrado por campo e massa G não disponíveis; campo_artefato sem massa nesta campanha.

- **Propósito:** Confirmar a correspondência de um para um entre campo pendente e sugestão
- **Procedimento:** Solicitar apoio no preenchimento do TAP com três campos pendentes
- **Resultado esperado:** Três sugestões, uma para cada campo pendente, cada uma identificando o campo
- **Critério de aprovação:** Correspondência de um para um entre campos pendentes e sugestões
- **Evidência a registrar:** Quantidade de sugestões apresentadas e a qual campo cada uma corresponde

## CT-RF04-02

Estado: **Bloqueado**. Fluxo integrado por campo e massa G não disponíveis; campo_artefato sem massa nesta campanha.

- **Propósito:** Confirmar que a cópia isola exatamente a sugestão escolhida
- **Procedimento:** Acionar a cópia de uma sugestão individual na interface e colar em um editor
- **Resultado esperado:** O conteúdo copiado corresponde exatamente à sugestão escolhida
- **Critério de aprovação:** Nenhum conteúdo de outra sugestão é incluído
- **Evidência a registrar:** Conteúdo efetivamente copiado e se corresponde apenas àquela sugestão

## CT-RF04-03

Estado: **Bloqueado**. Fluxo integrado por campo e massa G não disponíveis; campo_artefato sem massa nesta campanha.

- **Propósito:** Confirmar que a interação não escreve no documento de origem
- **Procedimento:** Comparar o documento de origem antes e depois da interação, por soma de verificação
- **Resultado esperado:** O documento de origem permanece inalterado
- **Critério de aprovação:** Somas de verificação idênticas antes e depois
- **Evidência a registrar:** Somas de verificação antes e depois e se coincidem

## CT-RF04-04

Estado: **Bloqueado**. Fluxo integrado por campo e massa G não disponíveis; campo_artefato sem massa nesta campanha.

- **Propósito:** Confirmar que a sugestão é rastreável até a fonte que a fundamenta
- **Procedimento:** Examinar cada sugestão de CT-RF04-01 quanto à fonte e à justificativa apresentadas
- **Resultado esperado:** Cada sugestão apresenta fonte e justificativa
- **Critério de aprovação:** As três sugestões atendem, coerente com o piso de 85% do RNF11
- **Evidência a registrar:** Presença de fonte identificável e de justificativa em cada sugestão

## CT-RF04-05

Estado: **Bloqueado**. Fluxo integrado por campo e massa G não disponíveis; campo_artefato sem massa nesta campanha.

- **Propósito:** Confirmar que ausência de pendência não é preenchida com sugestão desnecessária
- **Procedimento:** Solicitar apoio no preenchimento do mapa de benefícios integralmente preenchido
- **Resultado esperado:** O agente informa que não há campos pendentes
- **Critério de aprovação:** Nenhuma sugestão é produzida para campo já preenchido
- **Evidência a registrar:** Teor da resposta, verificando se informa a ausência de pendências ou produz sugestões sem necessidade

## CT-RF04-06

Estado: **Bloqueado**. Fluxo integrado por campo e massa G não disponíveis; campo_artefato sem massa nesta campanha.

- **Propósito:** Confirmar que o limite do conjunto suportado é declarado ao usuário
- **Procedimento:** Solicitar apoio para o documento de tipo não previsto no catálogo
- **Resultado esperado:** O agente explica que o tipo de documento não é suportado
- **Critério de aprovação:** A limitação é declarada, e não substituída por sugestão genérica
- **Evidência a registrar:** Teor da resposta e se a limitação é explicada ao usuário

## CT-RF04-07

Estado: **Bloqueado**. Fluxo integrado por campo e massa G não disponíveis; campo_artefato sem massa nesta campanha.

- **Requisito e componente:** RF04/RNF11; sugestões
- **Propósito:** Sugestão inadequada/sem contexto / negativo
- **Procedimento:** 1. Preparar campo pendente sem fonte suficiente e fonte incompatível com o campo. 2. Solicitar sugestão. 3. Comparar conteúdo/fonte
- **Resultado esperado:** Abstenção ou pedido de contexto; nenhuma sugestão afirmada como fundamentada sem evidência; documento inalterado

## CT-RF04-08

Estado: **Bloqueado**. Fluxo integrado por campo e massa G não disponíveis; campo_artefato sem massa nesta campanha.

- **Requisito e componente:** RF04; interface
- **Propósito:** Recusa / alternativo
- **Procedimento:** 1. Preparar documento com três campos pendentes. 2. Obter sugestões. 3. Ignorar/recusar uma e copiar outra. 4. Comparar hash do documento
- **Resultado esperado:** Cópia individual correta, nenhuma escrita automática e nenhum registro fictício de aceite; se não houver botão de recusa, ignorar a sugestão é o comportamento testado

## CT-RF05-01

Estado: **Bloqueado**. Agendador/canal de entrega e configuração de elegibilidade não disponibilizados; assinantes/webhooks não comprovam notificação automática.

- **Propósito:** Confirmar que a notificação parte do sistema, e não de uma solicitação do usuário
- **Procedimento:** Inserir uma pendência nova em projeto acompanhado pelo usuário de teste e aguardar o ciclo do agendador, sem realizar nenhuma solicitação
- **Resultado esperado:** Notificação entregue por iniciativa do sistema, contendo projeto e pendência
- **Critério de aprovação:** Notificação recebida sem nenhuma solicitação do usuário, com os dois elementos presentes
- **Evidência a registrar:** Se a notificação ocorreu, e se identifica o projeto e a pendência

## CT-RF05-02

Estado: **Bloqueado**. Agendador/canal de entrega e configuração de elegibilidade não disponibilizados; assinantes/webhooks não comprovam notificação automática.

- **Propósito:** Confirmar que o alcance da notificação segue a relação `acompanha`
- **Procedimento:** Preparar pendência própria, executar um ciclo e verificar quais usuários receberam a notificação
- **Resultado esperado:** Somente quem acompanha o projeto recebeu a notificação
- **Critério de aprovação:** Lista de destinatários idêntica à lista de acompanhantes
- **Evidência a registrar:** Lista de destinatários confrontada com a lista de quem acompanha o projeto

## CT-RF05-03

Estado: **Bloqueado**. Agendador/canal de entrega e configuração de elegibilidade não disponibilizados; assinantes/webhooks não comprovam notificação automática.

- **Propósito:** Confirmar que o alerta não se repete a cada ciclo do agendador
- **Procedimento:** Executar um segundo ciclo do agendador sem alterar as pendências
- **Resultado esperado:** Nenhuma notificação nova sobre a mesma pendência
- **Critério de aprovação:** Zero notificações repetidas
- **Evidência a registrar:** Se houve nova notificação sobre a mesma pendência

## CT-RF05-04

Estado: **Bloqueado**. Agendador/canal de entrega e configuração de elegibilidade não disponibilizados; assinantes/webhooks não comprovam notificação automática.

- **Propósito:** Confirmar que quem não acompanha o projeto não é alcançado
- **Procedimento:** Inserir uma pendência em projeto que o usuário de teste não acompanha e aguardar o ciclo
- **Resultado esperado:** O usuário que não acompanha o projeto não recebe notificação
- **Critério de aprovação:** Zero notificações indevidas
- **Evidência a registrar:** Se o usuário recebeu notificação indevida

## CT-RF05-05

Estado: **Bloqueado**. Agendador/canal de entrega e configuração de elegibilidade não disponibilizados; assinantes/webhooks não comprovam notificação automática.

- **Propósito:** Confirmar que pendência incompleta não vira notificação com campo vazio
- **Procedimento:** Inserir a pendência sem prazo do conjunto H e aguardar o ciclo
- **Resultado esperado:** Nenhuma notificação é emitida, ou a notificação declara a ausência do prazo
- **Critério de aprovação:** Nenhum campo vazio, nulo ou de preenchimento automático é exibido ao usuário
- **Evidência a registrar:** Se houve notificação, e, havendo, se o conteúdo está completo ou apresenta campo vazio ao usuário

## CT-RF05-06

Estado: **Bloqueado**. Agendador/canal de entrega e configuração de elegibilidade não disponibilizados; assinantes/webhooks não comprovam notificação automática.

- **Requisito e componente:** RF05; agendador
- **Propósito:** Elegibilidade / positivo e limite
- **Procedimento:** 1. Congelar relógio `t0` e janela aprovada `J`. 2. Preparar prazo antes/no/depois de `t0+J`, vencido, documento ausente e campo incompleto. 3. Rodar ciclo
- **Resultado esperado:** Notificar somente elegíveis do oráculo, identificando projeto e pendência; precisão de alertas ≥ 90% conforme Seção 2.1. Copiar `J`, periodicidade e filtros da configuração do agendador para o manifesto antes de preparar os prazos

## CT-RF05-07

Estado: **Bloqueado**. Agendador/canal de entrega e configuração de elegibilidade não disponibilizados; assinantes/webhooks não comprovam notificação automática.

- **Requisito e componente:** RF05; notificações
- **Propósito:** Resolução e reentrega / negativo
- **Procedimento:** 1. Notificar pendência própria. 2. Marcá-la resolvida. 3. Repetir evento/ciclo e enviar evento antigo
- **Resultado esperado:** Zero nova notificação da pendência resolvida e zero duplicidade; usar ID de evento/pendência estável. Política de reabertura deve ser confirmada

## CT-RF05-08

Estado: **Bloqueado**. Agendador/canal de entrega e configuração de elegibilidade não disponibilizados; assinantes/webhooks não comprovam notificação automática.

- **Requisito e componente:** RF05; notificações
- **Propósito:** Baixa relevância/adiamento / alternativo
- **Procedimento:** 1. Preparar alertas de prioridades diferentes e um alheio à consulta atual. 2. Apresentar ao usuário de teste. 3. Recusar/adiar quando disponível. 4. Rodar próximo ciclo
- **Resultado esperado:** Respeitar prioridade/frequência/adiamento aprovados, não descrever recusa como resolução da pendência. Registrar os limites configurados e executar recusa/adiamento somente se essas ações estiverem disponíveis na versão testada

## CT-RF05-09

Estado: **Bloqueado**. Agendador/canal de entrega e configuração de elegibilidade não disponibilizados; assinantes/webhooks não comprovam notificação automática.

- **Requisito e componente:** RF05/RNF04/RNF07; entrega
- **Propósito:** Serviço indisponível / erro
- **Procedimento:** 1. Preparar pendência própria. 2. Indisponibilizar entrega. 3. Executar ciclo, restaurar e repetir. 4. Contar entregas e eventos
- **Resultado esperado:** Erro observável, pendência preservada e entrega única após recuperação; número de tentativas/backoff e mecanismo de entrega dependem do contrato futuro

## CT-RF06-01

Estado: **Fora do recorte**. D04/D07; preservar caso histórico; escrita futura não entra no aceite do MVP.

- **Propósito:** Confirmar que a instrução em linguagem natural vira alteração explícita e revisável
- **Procedimento:** Autenticado como líder de P1, enviar "atualiza o avanço do projeto P1 para 45% neste mês"
- **Resultado esperado:** Projeto e campo corretamente identificados, com os valores exibidos antes da gravação
- **Critério de aprovação:** O usuário vê o valor que será gravado antes de qualquer escrita
- **Evidência a registrar:** Projeto e campos identificados e os valores exibidos antes da gravação

## CT-RF06-02

Estado: **Fora do recorte**. D04/D07; preservar caso histórico; escrita futura não entra no aceite do MVP.

- **Propósito:** Confirmar que a gravação ocorre e deixa rastro de autoria e data
- **Procedimento:** Confirmar explicitamente a alteração proposta no caso anterior
- **Resultado esperado:** O valor é gravado, e o registro de auditoria contém autor e data
- **Critério de aprovação:** Valor na fonte igual ao confirmado; autor e data presentes no registro
- **Evidência a registrar:** Valor gravado na fonte e os campos de autor e data do registro de auditoria

## CT-RF06-03

Estado: **Fora do recorte**. D04/D07; preservar caso histórico; escrita futura não entra no aceite do MVP.

- **Propósito:** Confirmar que a ausência de confirmação preserva o valor anterior
- **Procedimento:** Repetir a instrução e, em vez de confirmar, recusar ou abandonar a conversa
- **Resultado esperado:** Nenhuma alteração é gravada
- **Critério de aprovação:** O campo permanece com o valor anterior
- **Evidência a registrar:** Valor do campo na fonte após a interação

## CT-RF06-04

Estado: **Fora do recorte**. D04/D07; preservar caso histórico; escrita futura não entra no aceite do MVP.

- **Propósito:** Confirmar que a permissão de alteração segue a relação `lidera`
- **Procedimento:** Autenticado como líder de P1, instruir a atualização de um campo do projeto P2
- **Resultado esperado:** A alteração é recusada e o campo de P2 permanece inalterado
- **Critério de aprovação:** Recusa explícita e valor original preservado
- **Evidência a registrar:** Código HTTP, teor da resposta e valor do campo em P2 após a tentativa

## CT-RF06-05

Estado: **Fora do recorte**. D04/D07; preservar caso histórico; escrita futura não entra no aceite do MVP.

- **Propósito:** Confirmar que valor ambíguo não é resolvido por conta própria pelo agente
- **Procedimento:** Enviar "atualiza a data de término do projeto P1 para amanhã de manhã cedo", com valor incompatível com o tipo `date` do campo
- **Resultado esperado:** O agente pede a data em formato preciso
- **Critério de aprovação:** Nenhuma data é gravada por interpretação própria do agente
- **Evidência a registrar:** Teor da resposta e se o sistema pede correção ou grava uma interpretação própria

## CT-RF06-06

Estado: **Bloqueado**. Fonte dedicada para comparação antes/depois e diálogo explicativo do MVP ainda precisam ser exercitados conjuntamente.

- **Requisito e componente:** RF06/D04; chat
- **Propósito:** Proteção do MVP / negativo
- **Procedimento:** 1. Preparar cópia sintética de projeto. 2. Solicitar alteração e enviar confirmação explícita. 3. Comparar fonte antes/depois
- **Resultado esperado:** MVP permanece sem escrita; resposta explica limite e alternativa. Este caso verifica D04, não comprova a escrita exigida pela versão literal do RF06

