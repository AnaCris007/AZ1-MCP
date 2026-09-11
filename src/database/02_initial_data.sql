-- =============================================================================
-- AZ1 — Carga inicial da base sintética
--
-- Os valores NÃO foram inventados: projetos, situações, percentuais, relações
-- entre projetos e pendências vêm dos documentos que já estão indexados em
-- vecs.documentos_metro (planilha de portfólio e planilhas 04_Riscos_e_Problemas).
-- Manter os dois lados idênticos é o que impede o agente de responder uma coisa
-- pelo banco e outra pelo RAG — divergência que o RNF12 mede diretamente.
--
-- Os nomes de pessoas são fictícios: a base sintética identifica responsáveis
-- por gerência, não por indivíduo, e projeto.lider_id exige um usuário.
--
-- Reexecutável: apaga a carga anterior antes de inserir.
--   psql "$SUPABASE_DB_URL" -v ON_ERROR_STOP=1 -f 02_initial_data.sql
-- =============================================================================

\set ON_ERROR_STOP on

BEGIN;

-- Idempotência. A ordem respeita as dependências; as tabelas de auditoria são
-- limpas aqui porque esta é a carga de desenvolvimento. Em produção o REVOKE
-- DELETE do 01_create_database.sql impede que este bloco seja executado por
-- qualquer papel que não seja o dono do schema.
TRUNCATE auditoria.mensagem_fonte, auditoria.avaliacao, auditoria.evento_plataforma,
         auditoria.notificacao, auditoria.mensagem, auditoria.conversa RESTART IDENTITY CASCADE;
TRUNCATE portfolio.usuario_projeto, portfolio.projeto_relacionado, portfolio.campo_artefato,
         portfolio.pendencia, portfolio.artefato, portfolio.projeto,
         portfolio.usuario, portfolio.portfolio RESTART IDENTITY CASCADE;


-- 1. Portfólios ---------------------------------------------------------------
-- Correspondem aos subportfólios declarados na planilha de portfólio, que é o
-- nível pelo qual o PMO agrupa os projetos de fato.
INSERT INTO portfolio.portfolio (nome, ano_exercicio) VALUES
    ('Desempenho, Eficiência e Segurança Operacional', 2026),
    ('Expansão da Rede', 2026),
    ('Gestão e Finanças', 2026),
    ('Pessoas e Patrimônio', 2026);


-- 2. Usuários -----------------------------------------------------------------
-- As três personas da Seção 1.5 mais um líder por projeto. auth_user_id fica
-- nulo até a frente de autenticação (RNF02) associar cada um ao SSO.
INSERT INTO portfolio.usuario (nome, email, perfil) VALUES
    ('Robson Oliveira', 'robson.oliveira@metro.example', 'diretor'),
    ('Maria Eduarda Santos', 'maria.santos@metro.example', 'pmo'),
    ('Rafael Antunes', 'rafael.antunes@metro.example', 'lider_projeto'),
    ('Camila Nogueira', 'camila.nogueira@metro.example', 'lider_projeto'),
    ('Eduardo Tanaka', 'eduardo.tanaka@metro.example', 'lider_projeto'),
    ('Patrícia Moraes', 'patricia.moraes@metro.example', 'lider_projeto'),
    ('Sérgio Vilela', 'sergio.vilela@metro.example', 'lider_projeto'),
    ('Juliana Prado', 'juliana.prado@metro.example', 'lider_projeto'),
    ('Marcos Ribeiro', 'marcos.ribeiro@metro.example', 'lider_projeto'),
    ('Ana Beatriz Lima', 'ana.lima@metro.example', 'lider_projeto');


-- 3. Projetos -----------------------------------------------------------------
-- percentual_previsto e percentual_avanco são as colunas Previsto e Realizado
-- da planilha, convertidas de fração para percentual. desvio_pp é gerado.
INSERT INTO portfolio.projeto
    (codigo, nome, fase, status, data_inicio, data_termino_prevista,
     percentual_previsto, percentual_avanco, portfolio_id, lider_id)
VALUES
    ('SYN-01', 'Modernização da Ventilação Operacional', 'Execução', 'Atrasado', DATE '2026-02-15', DATE '2026-11-30', 82, 64,
     (SELECT id FROM portfolio.portfolio WHERE nome = 'Desempenho, Eficiência e Segurança Operacional' AND ano_exercicio = 2026),
     (SELECT id FROM portfolio.usuario   WHERE nome = 'Rafael Antunes')),
    ('SYN-02', 'Sistema Integrado de Monitoramento de Ativos', 'Execução', 'Dentro do previsto', DATE '2026-03-01', DATE '2026-12-15', 68, 71,
     (SELECT id FROM portfolio.portfolio WHERE nome = 'Desempenho, Eficiência e Segurança Operacional' AND ano_exercicio = 2026),
     (SELECT id FROM portfolio.usuario   WHERE nome = 'Camila Nogueira')),
    ('SYN-03', 'Ampliação da Estação Horizonte', 'Execução', 'Em risco', DATE '2026-01-10', DATE '2027-06-30', 43, 41,
     (SELECT id FROM portfolio.portfolio WHERE nome = 'Expansão da Rede' AND ano_exercicio = 2026),
     (SELECT id FROM portfolio.usuario   WHERE nome = 'Eduardo Tanaka')),
    ('SYN-04', 'Integração de Comunicação Operacional', 'Execução', 'Parcialmente atrasado', DATE '2026-02-01', DATE '2026-10-31', 79, 70,
     (SELECT id FROM portfolio.portfolio WHERE nome = 'Desempenho, Eficiência e Segurança Operacional' AND ano_exercicio = 2026),
     (SELECT id FROM portfolio.usuario   WHERE nome = 'Patrícia Moraes')),
    ('SYN-05', 'Programa de Eficiência Energética das Instalações', 'Execução', 'Acima do previsto', DATE '2026-01-15', DATE '2026-12-15', 70, 78,
     (SELECT id FROM portfolio.portfolio WHERE nome = 'Gestão e Finanças' AND ano_exercicio = 2026),
     (SELECT id FROM portfolio.usuario   WHERE nome = 'Sérgio Vilela')),
    ('SYN-06', 'Plataforma de Gestão do Conhecimento Técnico', 'Iniciação', 'Em estruturação', DATE '2026-07-01', DATE '2027-06-30', 18, 15,
     (SELECT id FROM portfolio.portfolio WHERE nome = 'Pessoas e Patrimônio' AND ano_exercicio = 2026),
     (SELECT id FROM portfolio.usuario   WHERE nome = 'Juliana Prado')),
    ('SYN-07', 'Otimização da Manutenção Preventiva', 'Execução', 'Crítico', DATE '2026-01-01', DATE '2027-04-30', 61, 47,
     (SELECT id FROM portfolio.portfolio WHERE nome = 'Desempenho, Eficiência e Segurança Operacional' AND ano_exercicio = 2026),
     (SELECT id FROM portfolio.usuario   WHERE nome = 'Marcos Ribeiro')),
    ('SYN-08', 'Modernização do Centro Integrado de Controle', 'Encerramento', 'Concluído', DATE '2025-01-10', DATE '2026-06-30', 100, 100,
     (SELECT id FROM portfolio.portfolio WHERE nome = 'Desempenho, Eficiência e Segurança Operacional' AND ano_exercicio = 2026),
     (SELECT id FROM portfolio.usuario   WHERE nome = 'Ana Beatriz Lima'));


-- 4. Dependências entre projetos ----------------------------------------------
INSERT INTO portfolio.projeto_relacionado (projeto_id, relacionado_id, relacao) VALUES
    ((SELECT id FROM portfolio.projeto WHERE codigo = 'SYN-02'),
     (SELECT id FROM portfolio.projeto WHERE codigo = 'SYN-07'), 'Fornece dados de monitoramento'),
    ((SELECT id FROM portfolio.projeto WHERE codigo = 'SYN-03'),
     (SELECT id FROM portfolio.projeto WHERE codigo = 'SYN-04'), 'Compartilha recurso técnico especializado'),
    ((SELECT id FROM portfolio.projeto WHERE codigo = 'SYN-04'),
     (SELECT id FROM portfolio.projeto WHERE codigo = 'SYN-08'), 'Depende de infraestrutura entregue'),
    ((SELECT id FROM portfolio.projeto WHERE codigo = 'SYN-04'),
     (SELECT id FROM portfolio.projeto WHERE codigo = 'SYN-03'), 'Compartilha recurso técnico especializado'),
    ((SELECT id FROM portfolio.projeto WHERE codigo = 'SYN-07'),
     (SELECT id FROM portfolio.projeto WHERE codigo = 'SYN-02'), 'Utiliza dados de monitoramento'),
    ((SELECT id FROM portfolio.projeto WHERE codigo = 'SYN-08'),
     (SELECT id FROM portfolio.projeto WHERE codigo = 'SYN-04'), 'Fornece infraestrutura utilizada');


-- 5. Artefatos ----------------------------------------------------------------
-- Os 37 documentos de projeto que estão indexados. Os três documentos sem
-- projeto (planilha de portfólio e os dois materiais normativos) ficam de fora:
-- artefato.projeto_id é NOT NULL e a Seção 3.6.7 registra essa limitação. Eles
-- continuam citáveis como fonte por auditoria.mensagem_fonte.artefato_id nulo.
--
-- `data` usa a data de referência da carga: a base sintética não traz data de
-- emissão por documento.
INSERT INTO portfolio.artefato (projeto_id, tipo, referencia, titulo, data) VALUES
    ((SELECT id FROM portfolio.projeto WHERE codigo = 'SYN-01'), 'cronograma', 'base_sintetica_metro/SYN-01_modernizacao_da_ventilacao_operacional/02_Cronograma.xlsx', 'Cronograma', TIMESTAMPTZ '2026-08-31 00:00:00-03'),
    ((SELECT id FROM portfolio.projeto WHERE codigo = 'SYN-01'), 'mapa_beneficios', 'base_sintetica_metro/SYN-01_modernizacao_da_ventilacao_operacional/03_Mapa_de_Beneficios.xlsx', 'Mapa de Beneficios', TIMESTAMPTZ '2026-08-31 00:00:00-03'),
    ((SELECT id FROM portfolio.projeto WHERE codigo = 'SYN-01'), 'mudancas', 'base_sintetica_metro/SYN-01_modernizacao_da_ventilacao_operacional/05_Mudancas.xlsx', 'Mudancas', TIMESTAMPTZ '2026-08-31 00:00:00-03'),
    ((SELECT id FROM portfolio.projeto WHERE codigo = 'SYN-01'), 'riscos_problemas', 'base_sintetica_metro/SYN-01_modernizacao_da_ventilacao_operacional/04_Riscos_e_Problemas.xlsx', 'Riscos e Problemas', TIMESTAMPTZ '2026-08-31 00:00:00-03'),
    ((SELECT id FROM portfolio.projeto WHERE codigo = 'SYN-01'), 'termo_abertura', 'base_sintetica_metro/SYN-01_modernizacao_da_ventilacao_operacional/01_Termo_de_Abertura.docx', 'Termo de Abertura', TIMESTAMPTZ '2026-08-31 00:00:00-03'),
    ((SELECT id FROM portfolio.projeto WHERE codigo = 'SYN-02'), 'cronograma', 'base_sintetica_metro/SYN-02_sistema_integrado_de_monitoramento_de_ativos/02_Cronograma.xlsx', 'Cronograma', TIMESTAMPTZ '2026-08-31 00:00:00-03'),
    ((SELECT id FROM portfolio.projeto WHERE codigo = 'SYN-02'), 'mapa_beneficios', 'base_sintetica_metro/SYN-02_sistema_integrado_de_monitoramento_de_ativos/03_Mapa_de_Beneficios.xlsx', 'Mapa de Beneficios', TIMESTAMPTZ '2026-08-31 00:00:00-03'),
    ((SELECT id FROM portfolio.projeto WHERE codigo = 'SYN-02'), 'riscos_problemas', 'base_sintetica_metro/SYN-02_sistema_integrado_de_monitoramento_de_ativos/04_Riscos_e_Problemas.xlsx', 'Riscos e Problemas', TIMESTAMPTZ '2026-08-31 00:00:00-03'),
    ((SELECT id FROM portfolio.projeto WHERE codigo = 'SYN-02'), 'termo_abertura', 'base_sintetica_metro/SYN-02_sistema_integrado_de_monitoramento_de_ativos/01_Termo_de_Abertura.docx', 'Termo de Abertura', TIMESTAMPTZ '2026-08-31 00:00:00-03'),
    ((SELECT id FROM portfolio.projeto WHERE codigo = 'SYN-03'), 'cronograma', 'base_sintetica_metro/SYN-03_ampliacao_da_estacao_horizonte/02_Cronograma.xlsx', 'Cronograma', TIMESTAMPTZ '2026-08-31 00:00:00-03'),
    ((SELECT id FROM portfolio.projeto WHERE codigo = 'SYN-03'), 'mapa_beneficios', 'base_sintetica_metro/SYN-03_ampliacao_da_estacao_horizonte/03_Mapa_de_Beneficios.xlsx', 'Mapa de Beneficios', TIMESTAMPTZ '2026-08-31 00:00:00-03'),
    ((SELECT id FROM portfolio.projeto WHERE codigo = 'SYN-03'), 'riscos_problemas', 'base_sintetica_metro/SYN-03_ampliacao_da_estacao_horizonte/04_Riscos_e_Problemas.xlsx', 'Riscos e Problemas', TIMESTAMPTZ '2026-08-31 00:00:00-03'),
    ((SELECT id FROM portfolio.projeto WHERE codigo = 'SYN-03'), 'termo_abertura', 'base_sintetica_metro/SYN-03_ampliacao_da_estacao_horizonte/01_Termo_de_Abertura.docx', 'Termo de Abertura', TIMESTAMPTZ '2026-08-31 00:00:00-03'),
    ((SELECT id FROM portfolio.projeto WHERE codigo = 'SYN-04'), 'cronograma', 'base_sintetica_metro/SYN-04_integracao_de_comunicacao_operacional/02_Cronograma.xlsx', 'Cronograma', TIMESTAMPTZ '2026-08-31 00:00:00-03'),
    ((SELECT id FROM portfolio.projeto WHERE codigo = 'SYN-04'), 'mapa_beneficios', 'base_sintetica_metro/SYN-04_integracao_de_comunicacao_operacional/03_Mapa_de_Beneficios.xlsx', 'Mapa de Beneficios', TIMESTAMPTZ '2026-08-31 00:00:00-03'),
    ((SELECT id FROM portfolio.projeto WHERE codigo = 'SYN-04'), 'mudancas', 'base_sintetica_metro/SYN-04_integracao_de_comunicacao_operacional/05_Mudancas.xlsx', 'Mudancas', TIMESTAMPTZ '2026-08-31 00:00:00-03'),
    ((SELECT id FROM portfolio.projeto WHERE codigo = 'SYN-04'), 'riscos_problemas', 'base_sintetica_metro/SYN-04_integracao_de_comunicacao_operacional/04_Riscos_e_Problemas.xlsx', 'Riscos e Problemas', TIMESTAMPTZ '2026-08-31 00:00:00-03'),
    ((SELECT id FROM portfolio.projeto WHERE codigo = 'SYN-04'), 'termo_abertura', 'base_sintetica_metro/SYN-04_integracao_de_comunicacao_operacional/01_Termo_de_Abertura.docx', 'Termo de Abertura', TIMESTAMPTZ '2026-08-31 00:00:00-03'),
    ((SELECT id FROM portfolio.projeto WHERE codigo = 'SYN-05'), 'cronograma', 'base_sintetica_metro/SYN-05_programa_de_eficiência_energética_das_instalacões/02_Cronograma.xlsx', 'Cronograma', TIMESTAMPTZ '2026-08-31 00:00:00-03'),
    ((SELECT id FROM portfolio.projeto WHERE codigo = 'SYN-05'), 'mapa_beneficios', 'base_sintetica_metro/SYN-05_programa_de_eficiência_energética_das_instalacões/03_Mapa_de_Beneficios.xlsx', 'Mapa de Beneficios', TIMESTAMPTZ '2026-08-31 00:00:00-03'),
    ((SELECT id FROM portfolio.projeto WHERE codigo = 'SYN-05'), 'riscos_problemas', 'base_sintetica_metro/SYN-05_programa_de_eficiência_energética_das_instalacões/04_Riscos_e_Problemas.xlsx', 'Riscos e Problemas', TIMESTAMPTZ '2026-08-31 00:00:00-03'),
    ((SELECT id FROM portfolio.projeto WHERE codigo = 'SYN-05'), 'termo_abertura', 'base_sintetica_metro/SYN-05_programa_de_eficiência_energética_das_instalacões/01_Termo_de_Abertura.docx', 'Termo de Abertura', TIMESTAMPTZ '2026-08-31 00:00:00-03'),
    ((SELECT id FROM portfolio.projeto WHERE codigo = 'SYN-06'), 'cronograma', 'base_sintetica_metro/SYN-06_plataforma_de_gestao_do_conhecimento_técnico/02_Cronograma.xlsx', 'Cronograma', TIMESTAMPTZ '2026-08-31 00:00:00-03'),
    ((SELECT id FROM portfolio.projeto WHERE codigo = 'SYN-06'), 'mapa_beneficios', 'base_sintetica_metro/SYN-06_plataforma_de_gestao_do_conhecimento_técnico/03_Mapa_de_Beneficios.xlsx', 'Mapa de Beneficios', TIMESTAMPTZ '2026-08-31 00:00:00-03'),
    ((SELECT id FROM portfolio.projeto WHERE codigo = 'SYN-06'), 'riscos_problemas', 'base_sintetica_metro/SYN-06_plataforma_de_gestao_do_conhecimento_técnico/04_Riscos_e_Problemas.xlsx', 'Riscos e Problemas', TIMESTAMPTZ '2026-08-31 00:00:00-03'),
    ((SELECT id FROM portfolio.projeto WHERE codigo = 'SYN-06'), 'termo_abertura', 'base_sintetica_metro/SYN-06_plataforma_de_gestao_do_conhecimento_técnico/01_Termo_de_Abertura.docx', 'Termo de Abertura', TIMESTAMPTZ '2026-08-31 00:00:00-03'),
    ((SELECT id FROM portfolio.projeto WHERE codigo = 'SYN-07'), 'cronograma', 'base_sintetica_metro/SYN-07_otimizacao_da_manutencao_preventiva/02_Cronograma.xlsx', 'Cronograma', TIMESTAMPTZ '2026-08-31 00:00:00-03'),
    ((SELECT id FROM portfolio.projeto WHERE codigo = 'SYN-07'), 'mapa_beneficios', 'base_sintetica_metro/SYN-07_otimizacao_da_manutencao_preventiva/03_Mapa_de_Beneficios.xlsx', 'Mapa de Beneficios', TIMESTAMPTZ '2026-08-31 00:00:00-03'),
    ((SELECT id FROM portfolio.projeto WHERE codigo = 'SYN-07'), 'mudancas', 'base_sintetica_metro/SYN-07_otimizacao_da_manutencao_preventiva/05_Mudancas.xlsx', 'Mudancas', TIMESTAMPTZ '2026-08-31 00:00:00-03'),
    ((SELECT id FROM portfolio.projeto WHERE codigo = 'SYN-07'), 'riscos_problemas', 'base_sintetica_metro/SYN-07_otimizacao_da_manutencao_preventiva/04_Riscos_e_Problemas.xlsx', 'Riscos e Problemas', TIMESTAMPTZ '2026-08-31 00:00:00-03'),
    ((SELECT id FROM portfolio.projeto WHERE codigo = 'SYN-07'), 'termo_abertura', 'base_sintetica_metro/SYN-07_otimizacao_da_manutencao_preventiva/01_Termo_de_Abertura.docx', 'Termo de Abertura', TIMESTAMPTZ '2026-08-31 00:00:00-03'),
    ((SELECT id FROM portfolio.projeto WHERE codigo = 'SYN-08'), 'cronograma', 'base_sintetica_metro/SYN-08_modernizacao_do_centro_integrado_de_controle/02_Cronograma.xlsx', 'Cronograma', TIMESTAMPTZ '2026-08-31 00:00:00-03'),
    ((SELECT id FROM portfolio.projeto WHERE codigo = 'SYN-08'), 'mapa_beneficios', 'base_sintetica_metro/SYN-08_modernizacao_do_centro_integrado_de_controle/03_Mapa_de_Beneficios.xlsx', 'Mapa de Beneficios', TIMESTAMPTZ '2026-08-31 00:00:00-03'),
    ((SELECT id FROM portfolio.projeto WHERE codigo = 'SYN-08'), 'mudancas', 'base_sintetica_metro/SYN-08_modernizacao_do_centro_integrado_de_controle/05_Mudancas.xlsx', 'Mudancas', TIMESTAMPTZ '2026-08-31 00:00:00-03'),
    ((SELECT id FROM portfolio.projeto WHERE codigo = 'SYN-08'), 'relatorio_encerramento', 'base_sintetica_metro/SYN-08_modernizacao_do_centro_integrado_de_controle/06_Relatorio_Anual_Encerramento.docx', 'Relatorio Anual Encerramento', TIMESTAMPTZ '2026-08-31 00:00:00-03'),
    ((SELECT id FROM portfolio.projeto WHERE codigo = 'SYN-08'), 'riscos_problemas', 'base_sintetica_metro/SYN-08_modernizacao_do_centro_integrado_de_controle/04_Riscos_e_Problemas.xlsx', 'Riscos e Problemas', TIMESTAMPTZ '2026-08-31 00:00:00-03'),
    ((SELECT id FROM portfolio.projeto WHERE codigo = 'SYN-08'), 'termo_abertura', 'base_sintetica_metro/SYN-08_modernizacao_do_centro_integrado_de_controle/01_Termo_de_Abertura.docx', 'Termo de Abertura', TIMESTAMPTZ '2026-08-31 00:00:00-03');


-- 6. Pendências ---------------------------------------------------------------
-- Os 18 riscos e problemas registrados nas planilhas 04_Riscos_e_Problemas.
INSERT INTO portfolio.pendencia
    (projeto_id, codigo, tipo, titulo, descricao, criticidade, responsavel,
     acao_resposta, situacao)
VALUES
    ((SELECT id FROM portfolio.projeto WHERE codigo = 'SYN-01'), 'P01', 'problema',
     'Entrega parcial de equipamentos fora do prazo', 'Parte dos equipamentos foi entregue após a data planejada',
     'Alto', 'Gerência de Engenharia', 'Replanejar instalação e reforçar acompanhamento', 'em_tratamento'),
    ((SELECT id FROM portfolio.projeto WHERE codigo = 'SYN-01'), 'R01', 'risco',
     'Atraso adicional na entrega de equipamentos', 'Fornecedor pode postergar entregas remanescentes',
     'Crítico', 'Gerência de Engenharia', 'Diligenciar fornecedor e priorizar itens críticos', 'aberta'),
    ((SELECT id FROM portfolio.projeto WHERE codigo = 'SYN-01'), 'R02', 'risco',
     'Adequações elétricas não previstas', 'Infraestrutura existente pode exigir intervenções adicionais',
     'Moderado', 'Gerência de Sistemas', 'Realizar inspeções antecipadas', 'aberta'),
    ((SELECT id FROM portfolio.projeto WHERE codigo = 'SYN-01'), 'R03', 'risco',
     'Janela operacional insuficiente', 'Disponibilidade de janelas pode limitar instalações',
     'Alto', 'Gerência Operacional', 'Planejar janelas alternativas', 'aberta'),
    ((SELECT id FROM portfolio.projeto WHERE codigo = 'SYN-02'), 'R04', 'risco',
     'Incompatibilidade com equipamentos antigos', 'Parte do parque pode exigir adaptadores',
     'Moderado', 'Gerência de Manutenção', 'Executar testes de compatibilidade', 'aberta'),
    ((SELECT id FROM portfolio.projeto WHERE codigo = 'SYN-02'), 'R05', 'risco',
     'Baixa qualidade inicial dos dados', 'Sensores podem demandar calibração adicional',
     'Baixo', 'Gerência de Dados', 'Aplicar rotina de validação', 'aberta'),
    ((SELECT id FROM portfolio.projeto WHERE codigo = 'SYN-02'), 'R06', 'risco',
     'Atraso na aquisição de sensores', 'Prazo de fornecimento pode aumentar',
     'Moderado', 'Gerência de Suprimentos', 'Antecipar pedidos críticos', 'aberta'),
    ((SELECT id FROM portfolio.projeto WHERE codigo = 'SYN-03'), 'R07', 'risco',
     'Atraso na liberação de área', 'Liberação de área necessária à frente de obra pode ocorrer após o previsto',
     'Crítico', 'Gerência de Implantação', 'Acompanhar autorizações e preparar frente alternativa', 'aberta'),
    ((SELECT id FROM portfolio.projeto WHERE codigo = 'SYN-04'), 'P02', 'problema',
     'Atraso na integração de infraestrutura', 'Integração de parte da infraestrutura ocorreu após a data-base',
     'Moderado', 'Gerência de Sistemas', 'Reordenar sequência de testes', 'em_tratamento'),
    ((SELECT id FROM portfolio.projeto WHERE codigo = 'SYN-04'), 'R08', 'risco',
     'Indisponibilidade de ambientes para testes', 'Ambientes operacionais podem não estar disponíveis na janela prevista',
     'Moderado', 'Gerência Operacional', 'Reservar janelas alternativas', 'aberta'),
    ((SELECT id FROM portfolio.projeto WHERE codigo = 'SYN-04'), 'R09', 'risco',
     'Incompatibilidade entre equipamentos', 'Interfaces podem exigir ajustes adicionais',
     'Alto', 'Gerência de Sistemas', 'Realizar testes integrados antecipados', 'aberta'),
    ((SELECT id FROM portfolio.projeto WHERE codigo = 'SYN-05'), 'R10', 'risco',
     'Indisponibilidade de componentes', 'Componentes podem ter prazo de fornecimento superior ao previsto',
     'Baixo', 'Gerência de Suprimentos', 'Manter alternativas homologadas', 'aberta'),
    ((SELECT id FROM portfolio.projeto WHERE codigo = 'SYN-05'), 'R11', 'risco',
     'Economia inferior à estimada', 'Resultados podem ficar abaixo da estimativa inicial',
     'Baixo', 'Gerência de Energia', 'Acompanhar medição e ajustar parâmetros', 'aberta'),
    ((SELECT id FROM portfolio.projeto WHERE codigo = 'SYN-06'), 'R12', 'risco',
     'Baixa adesão das áreas', 'Áreas podem não priorizar as entrevistas e registros',
     'Moderado', 'Gerência de Conhecimento', 'Reservar agenda antecipadamente', 'aberta'),
    ((SELECT id FROM portfolio.projeto WHERE codigo = 'SYN-07'), 'P03', 'problema',
     'Equipamento crítico indisponível', 'Falha prematura de componente suspendeu testes e afetou entregas',
     'Crítico', 'Gerência de Manutenção', 'Substituir componente e revisar plano de testes', 'em_tratamento'),
    ((SELECT id FROM portfolio.projeto WHERE codigo = 'SYN-07'), 'R14', 'risco',
     'Indisponibilidade prolongada de equipamento crítico', 'Falha de componente pode impedir testes planejados',
     'Crítico', 'Gerência de Manutenção', 'Manter sobressalente e plano de contingência', 'materializada'),
    ((SELECT id FROM portfolio.projeto WHERE codigo = 'SYN-08'), 'P04', 'problema',
     'Infraestrutura intermediária entregue com atraso', 'Atraso pontual exigiu reprogramação de testes',
     'Moderado', 'Gerência de Tecnologia', 'Replanejamento concluído', 'resolvida'),
    ((SELECT id FROM portfolio.projeto WHERE codigo = 'SYN-08'), 'R15', 'risco',
     'Atraso de infraestrutura intermediária', 'A entrega de infraestrutura poderia afetar a sequência de testes',
     'Moderado', 'Gerência de Tecnologia', 'Reprogramar atividades sem impacto final', 'resolvida');


-- 7. Acompanhamento -----------------------------------------------------------
-- O diretor e a analista de PMO acompanham o portfólio inteiro; cada líder
-- acompanha o próprio projeto. Define os destinatários da notificação do RF05.
INSERT INTO portfolio.usuario_projeto (usuario_id, projeto_id)
SELECT u.id, p.id FROM portfolio.usuario u CROSS JOIN portfolio.projeto p
 WHERE u.perfil IN ('diretor', 'pmo')
UNION
SELECT p.lider_id, p.id FROM portfolio.projeto p;


COMMIT;


-- =============================================================================
-- Verificação da carga (T25: validar leitura e escrita)
-- =============================================================================
\echo ''
\echo '== Contagem por tabela =='
SELECT 'portfolio'   AS tabela, count(*) FROM portfolio.portfolio
UNION ALL SELECT 'usuario',            count(*) FROM portfolio.usuario
UNION ALL SELECT 'projeto',            count(*) FROM portfolio.projeto
UNION ALL SELECT 'projeto_relacionado',count(*) FROM portfolio.projeto_relacionado
UNION ALL SELECT 'artefato',           count(*) FROM portfolio.artefato
UNION ALL SELECT 'pendencia',          count(*) FROM portfolio.pendencia
UNION ALL SELECT 'usuario_projeto',    count(*) FROM portfolio.usuario_projeto;

\echo ''
\echo '== Situação do portfólio (a pergunta do Diretor) =='
SELECT codigo, status, percentual_previsto AS prev, percentual_avanco AS real,
       desvio_pp, pendencias_abertas, artefatos, lider
  FROM portfolio.vw_projeto_situacao ORDER BY desvio_pp;

\echo ''
\echo '== Cobertura: artefatos no banco x documentos indexados no RAG =='
-- As duas contagens devem bater, projeto a projeto. Divergência significa que
-- alguém indexou um documento sem cadastrá-lo, ou o contrário.
SELECT p.codigo,
       count(a.id)                                  AS artefatos_no_banco,
       (SELECT count(DISTINCT v.metadata->>'arquivo_origem')
          FROM vecs.documentos_metro v
         WHERE v.metadata->>'projeto_id' = p.codigo) AS documentos_indexados
  FROM portfolio.projeto p
  LEFT JOIN portfolio.artefato a ON a.projeto_id = p.id
 GROUP BY p.codigo ORDER BY p.codigo;

