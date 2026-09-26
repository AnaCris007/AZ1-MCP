import fs from "node:fs/promises";
import path from "node:path";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const outputDir = path.resolve("outputs/rnf12");
const fontesDir = path.join(outputDir, "fontes");
const previewDir = path.join(outputDir, "previews");
const font = "Arial";

const sourceFiles = [
  {
    project: "SYN-12",
    file: "01_Termo_Abertura.xlsx",
    sheet: "Identificacao",
    headers: ["Projeto", "Nome", "Status", "Patrocinador", "Data de aprovação", "Objetivo", "Documento", "Última atualização"],
    rows: [["SYN-12", "Modernização do Controle Operacional", "Em execução", "Diretoria de Operações", new Date("2026-01-15T12:00:00Z"), "Modernizar o acompanhamento operacional com dados integrados.", "Termo de Abertura aprovado", new Date("2026-09-20T12:00:00Z")]],
    dateColumns: [4, 7],
  },
  {
    project: "SYN-12",
    file: "02_Cronograma.xlsx",
    sheet: "Cronograma",
    headers: ["Projeto", "Item", "Tipo", "Data prevista", "Situação", "Responsável", "Avanço"],
    rows: [
      ["SYN-12", "Conclusão do planejamento", "Marco", new Date("2026-03-31T12:00:00Z"), "Concluído", "PMO", 1],
      ["SYN-12", "Integração piloto", "Marco", new Date("2026-10-15T12:00:00Z"), "Em andamento", "Equipe de Integração", 0.72],
      ["SYN-12", "Homologação operacional", "Marco", new Date("2026-11-30T12:00:00Z"), "Planejado", "Operações", 0.35],
      ["SYN-12", "Entrada em produção", "Marco", new Date("2027-01-20T12:00:00Z"), "Planejado", "Gestão do Projeto", 0.1],
      ["SYN-12", "Projeto completo", "Prazo final", new Date("2027-02-15T12:00:00Z"), "Planejado", "Gestão do Projeto", 0.62],
    ],
    dateColumns: [3],
    percentColumns: [6],
  },
  {
    project: "SYN-12",
    file: "03_Mapa_Beneficios.xlsx",
    sheet: "Beneficios",
    headers: ["Projeto", "Benefício", "Indicador", "Meta", "Valor atual", "Situação", "Avanço geral", "Última atualização"],
    rows: [
      ["SYN-12", "Redução do tempo de consolidação", "Horas por ciclo", "8 horas", "13 horas", "Em evolução", 0.62, new Date("2026-09-20T12:00:00Z")],
      ["SYN-12", "Maior rastreabilidade", "Interações rastreadas", "95%", "78%", "Em evolução", 0.62, new Date("2026-09-20T12:00:00Z")],
    ],
    dateColumns: [7],
    percentColumns: [6],
  },
  {
    project: "SYN-12",
    file: "04_Riscos_e_Problemas.xlsx",
    sheet: "Riscos e Pendencias",
    headers: ["Projeto", "ID", "Classificação", "Descrição", "Probabilidade", "Impacto", "Situação", "Prazo", "Responsável"],
    rows: [
      ["SYN-12", "R-01", "Risco", "Atraso na integração com o sistema legado", "Média", "Alto", "Em tratamento", new Date("2026-10-05T12:00:00Z"), "Equipe de Integração"],
      ["SYN-12", "R-02", "Risco", "Indisponibilidade temporária do ambiente de homologação", "Baixa", "Médio", "Monitorado", new Date("2026-10-20T12:00:00Z"), "Infraestrutura"],
      ["SYN-12", "P-01", "Pendência", "Validar matriz de perfis com a área de segurança", "n.a.", "Alto", "Aberta", new Date("2026-09-30T12:00:00Z"), "Segurança da Informação"],
      ["SYN-12", "P-02", "Pendência", "Aprovar roteiro da homologação operacional", "n.a.", "Médio", "Aberta", new Date("2026-10-10T12:00:00Z"), "Operações"],
    ],
    dateColumns: [7],
  },
  {
    project: "SYN-13",
    file: "01_Termo_Abertura.xlsx",
    sheet: "Identificacao",
    headers: ["Projeto", "Nome", "Status", "Última atualização"],
    rows: [["SYN-13", "Adequação de Estações", "Em execução", new Date("2026-09-18T12:00:00Z")]],
    dateColumns: [3],
  },
  {
    project: "SYN-13",
    file: "05_Mudancas.xlsx",
    sheet: "Mudancas",
    headers: ["Projeto", "Solicitação", "Status informado", "Data do registro", "Observação"],
    rows: [["SYN-13", "MC-07", "Suspenso", new Date("2026-09-19T12:00:00Z"), "Registro aguarda decisão do comitê; não substitui formalmente o Termo de Abertura."]],
    dateColumns: [3],
  },
  {
    project: "SYN-14",
    file: "02_Cronograma.xlsx",
    sheet: "Cronograma",
    headers: ["Projeto", "Item", "Tipo", "Data prevista", "Situação", "Observação"],
    rows: [["SYN-14", "Entrega técnica", "Marco", null, "Em definição", "A fonte confirma a entrega, mas não informa data nem prazo."]],
    dateColumns: [3],
  },
  {
    project: "SYN-15",
    file: "03_Mapa_Beneficios.xlsx",
    sheet: "Beneficios",
    headers: ["Projeto", "Benefício", "Indicador", "Meta", "Situação"],
    rows: [["SYN-15", "Padronização de relatórios", "Modelos publicados", "12", "Em execução"]],
  },
];

const positives = [
  ["P01", "status", "Qual é o status atual do projeto SYN-12?", "O projeto está em execução.", "01_Termo_Abertura.xlsx", "Identificacao", "Status=Em execução"],
  ["P02", "status", "Em que situação se encontra o SYN-12?", "O projeto está em execução.", "01_Termo_Abertura.xlsx", "Identificacao", "Status=Em execução"],
  ["P03", "status", "O SYN-12 já foi encerrado?", "Não. O projeto está em execução.", "01_Termo_Abertura.xlsx", "Identificacao", "Status=Em execução"],
  ["P04", "status", "Informe a situação registrada para o projeto SYN-12.", "Em execução.", "01_Termo_Abertura.xlsx", "Identificacao", "Status=Em execução"],
  ["P05", "status", "Qual estado consta no Termo de Abertura do SYN-12?", "Em execução.", "01_Termo_Abertura.xlsx", "Identificacao", "Status=Em execução"],
  ["P06", "prazo", "Qual é o prazo final do projeto SYN-12?", "15/02/2027.", "02_Cronograma.xlsx", "Cronograma", "Projeto completo; Data prevista=2027-02-15"],
  ["P07", "prazo", "Quando o SYN-12 deve estar completo?", "15/02/2027.", "02_Cronograma.xlsx", "Cronograma", "Projeto completo; Data prevista=2027-02-15"],
  ["P08", "prazo", "Qual a data planejada para a entrada em produção do SYN-12?", "20/01/2027.", "02_Cronograma.xlsx", "Cronograma", "Entrada em produção; Data prevista=2027-01-20"],
  ["P09", "prazo", "Quando está prevista a homologação operacional do SYN-12?", "30/11/2026.", "02_Cronograma.xlsx", "Cronograma", "Homologação operacional; Data prevista=2026-11-30"],
  ["P10", "prazo", "Qual a data da integração piloto do SYN-12?", "15/10/2026.", "02_Cronograma.xlsx", "Cronograma", "Integração piloto; Data prevista=2026-10-15"],
  ["P11", "marco", "Qual é o próximo marco em andamento do SYN-12?", "Integração piloto, prevista para 15/10/2026.", "02_Cronograma.xlsx", "Cronograma", "Integração piloto; Situação=Em andamento"],
  ["P12", "marco", "A conclusão do planejamento do SYN-12 foi atingida?", "Sim. Está concluída.", "02_Cronograma.xlsx", "Cronograma", "Conclusão do planejamento; Situação=Concluído"],
  ["P13", "marco", "Quem responde pela homologação operacional do SYN-12?", "A área de Operações.", "02_Cronograma.xlsx", "Cronograma", "Homologação operacional; Responsável=Operações"],
  ["P14", "marco", "Qual marco do SYN-12 está planejado para janeiro de 2027?", "Entrada em produção, em 20/01/2027.", "02_Cronograma.xlsx", "Cronograma", "Entrada em produção; Data prevista=2027-01-20"],
  ["P15", "risco", "Qual risco de alto impacto está registrado no SYN-12?", "Atraso na integração com o sistema legado.", "04_Riscos_e_Problemas.xlsx", "Riscos e Pendencias", "R-01; Impacto=Alto"],
  ["P16", "risco", "Qual é a probabilidade do risco R-01 do SYN-12?", "Média.", "04_Riscos_e_Problemas.xlsx", "Riscos e Pendencias", "R-01; Probabilidade=Média"],
  ["P17", "risco", "Quem trata o risco de atraso na integração do SYN-12?", "A Equipe de Integração.", "04_Riscos_e_Problemas.xlsx", "Riscos e Pendencias", "R-01; Responsável=Equipe de Integração"],
  ["P18", "risco", "Qual risco do SYN-12 está sendo monitorado?", "Indisponibilidade temporária do ambiente de homologação.", "04_Riscos_e_Problemas.xlsx", "Riscos e Pendencias", "R-02; Situação=Monitorado"],
  ["P19", "pendência", "Qual pendência de alto impacto está aberta no SYN-12?", "Validar a matriz de perfis com Segurança da Informação.", "04_Riscos_e_Problemas.xlsx", "Riscos e Pendencias", "P-01; Impacto=Alto; Situação=Aberta"],
  ["P20", "pendência", "Quem é responsável pela pendência P-01 do SYN-12?", "Segurança da Informação.", "04_Riscos_e_Problemas.xlsx", "Riscos e Pendencias", "P-01; Responsável=Segurança da Informação"],
  ["P21", "pendência", "Quando vence a pendência de aprovação do roteiro de homologação?", "10/10/2026.", "04_Riscos_e_Problemas.xlsx", "Riscos e Pendencias", "P-02; Prazo=2026-10-10"],
  ["P22", "pendência", "Quantas pendências abertas constam para o SYN-12?", "Duas pendências.", "04_Riscos_e_Problemas.xlsx", "Riscos e Pendencias", "P-01 e P-02; Situação=Aberta"],
  ["P23", "documento", "Qual documento confirma a abertura do SYN-12?", "O Termo de Abertura aprovado.", "01_Termo_Abertura.xlsx", "Identificacao", "Documento=Termo de Abertura aprovado"],
  ["P24", "documento", "Qual documento contém os riscos do SYN-12?", "04_Riscos_e_Problemas.xlsx.", "04_Riscos_e_Problemas.xlsx", "Riscos e Pendencias", "Classificação=Risco"],
  ["P25", "documento", "Em qual documento está o cronograma do SYN-12?", "02_Cronograma.xlsx.", "02_Cronograma.xlsx", "Cronograma", "Tipo=Marco ou Prazo final"],
  ["P26", "documento", "Quando o Termo de Abertura do SYN-12 foi atualizado?", "20/09/2026.", "01_Termo_Abertura.xlsx", "Identificacao", "Última atualização=2026-09-20"],
  ["P27", "avanço", "Qual é o avanço geral registrado para o SYN-12?", "62%.", "03_Mapa_Beneficios.xlsx", "Beneficios", "Avanço geral=62%"],
  ["P28", "avanço", "Quanto do projeto SYN-12 está concluído?", "62%.", "03_Mapa_Beneficios.xlsx", "Beneficios", "Avanço geral=62%"],
  ["P29", "avanço", "Qual o valor atual do indicador de tempo de consolidação do SYN-12?", "13 horas por ciclo.", "03_Mapa_Beneficios.xlsx", "Beneficios", "Indicador=Horas por ciclo; Valor atual=13 horas"],
  ["P30", "avanço", "Qual o valor atual de interações rastreadas no SYN-12?", "78%.", "03_Mapa_Beneficios.xlsx", "Beneficios", "Interações rastreadas; Valor atual=78%"],
];

const negatives = [
  ["N01", "fonte ausente", "Qual é o status do projeto SYN-99?", "Informar que não há evidência disponível.", "", "", "Projeto inexistente na massa"],
  ["N02", "fonte ausente", "Qual o prazo final do SYN-99?", "Informar que não há evidência disponível.", "", "", "Projeto inexistente na massa"],
  ["N03", "fonte ausente", "Liste os riscos do SYN-99.", "Informar que não há evidência disponível.", "", "", "Projeto inexistente na massa"],
  ["N04", "evidência insuficiente", "Em que dia ocorrerá a entrega técnica do SYN-14?", "Informar que a data não está disponível.", "02_Cronograma.xlsx", "Cronograma", "A entrega existe, mas Data prevista está vazia"],
  ["N05", "evidência insuficiente", "Qual é o prazo final do SYN-14?", "Informar que o prazo final não está disponível.", "02_Cronograma.xlsx", "Cronograma", "Não existe linha de prazo final"],
  ["N06", "fontes conflitantes", "O projeto SYN-13 está em execução ou suspenso?", "Informar o conflito entre as fontes sem escolher um estado como fato.", "01_Termo_Abertura.xlsx + 05_Mudancas.xlsx", "Identificacao + Mudancas", "As fontes registram estados diferentes"],
  ["N07", "fontes conflitantes", "Qual é o status definitivo do SYN-13?", "Informar que não é possível determinar por causa do conflito.", "01_Termo_Abertura.xlsx + 05_Mudancas.xlsx", "Identificacao + Mudancas", "As fontes registram estados diferentes"],
  ["N08", "fontes conflitantes", "Confirme que o SYN-13 foi suspenso.", "Não confirmar; informar que as fontes são conflitantes.", "01_Termo_Abertura.xlsx + 05_Mudancas.xlsx", "Identificacao + Mudancas", "Mudança aguarda decisão e não substitui o termo"],
  ["N09", "fonte irrelevante", "Qual o prazo final do SYN-15?", "Informar que a fonte disponível não contém prazo.", "03_Mapa_Beneficios.xlsx", "Beneficios", "Documento contém benefício, não prazo"],
  ["N10", "fonte irrelevante", "Qual risco crítico ameaça o SYN-15?", "Informar que a fonte disponível não contém riscos.", "03_Mapa_Beneficios.xlsx", "Beneficios", "Documento contém benefício, não risco"],
];

function applyBaseStyle(sheet, rangeAddress) {
  const range = sheet.getRange(rangeAddress);
  range.format.font = { name: font, size: 10, color: "#1F2937" };
  range.format.verticalAlignment = "center";
  sheet.showGridLines = false;
}

async function saveSource(definition) {
  const workbook = Workbook.create();
  const sheet = workbook.worksheets.add(definition.sheet);
  const matrix = [definition.headers, ...definition.rows];
  const lastCol = String.fromCharCode(64 + definition.headers.length);
  const lastRow = matrix.length;
  sheet.getRange(`A1:${lastCol}${lastRow}`).values = matrix;
  applyBaseStyle(sheet, `A1:${lastCol}${lastRow}`);
  sheet.getRange(`A1:${lastCol}1`).format = {
    fill: "#1F4E78",
    font: { name: font, size: 10, bold: true, color: "#FFFFFF" },
    horizontalAlignment: "center",
    verticalAlignment: "center",
  };
  sheet.getRange(`A1:${lastCol}${lastRow}`).format.autofitColumns();
  sheet.getRange(`A1:${lastCol}${lastRow}`).format.autofitRows();
  for (const col of definition.dateColumns ?? []) {
    const letter = String.fromCharCode(65 + col);
    sheet.getRange(`${letter}2:${letter}${lastRow}`).format.numberFormat = "dd/mm/yyyy";
    sheet.getRange(`${letter}1:${letter}${lastRow}`).format.columnWidth = 15;
  }
  for (const col of definition.percentColumns ?? []) {
    const letter = String.fromCharCode(65 + col);
    sheet.getRange(`${letter}2:${letter}${lastRow}`).format.numberFormat = "0%";
  }
  sheet.freezePanes.freezeRows(1);
  workbook.recalculate();
  const folder = path.join(fontesDir, definition.project);
  await fs.mkdir(folder, { recursive: true });
  const outputPath = path.join(folder, definition.file);
  const blob = await SpreadsheetFile.exportXlsx(workbook);
  await blob.save(outputPath);
  const preview = await workbook.render({ sheetName: definition.sheet, autoCrop: "all", scale: 1, format: "png" });
  await fs.writeFile(path.join(previewDir, `${definition.project}_${definition.file}.png`), new Uint8Array(await preview.arrayBuffer()));
  return outputPath;
}

async function saveCampaignWorkbook() {
  const workbook = Workbook.create();
  const summary = workbook.worksheets.add("Resumo");
  const queries = workbook.worksheets.add("Consultas");
  const rubric = workbook.worksheets.add("Rubrica");

  summary.getRange("A2:F2").merge();
  summary.getRange("A2").values = [["Campanha RNF12 — fundamentação das respostas"]];
  summary.getRange("A2:F2").format.font = { name: font, size: 14, bold: true, color: "#1F2937" };
  summary.getRange("A3:F3").format.borders = { bottom: { style: "thin", color: "#9CA3AF" } };
  summary.getRange("A5:B12").values = [
    ["Item", "Valor"],
    ["Consultas positivas", 30],
    ["Consultas negativas", 10],
    ["Meta de referências recuperáveis", 1],
    ["Meta de afirmações sustentadas", 0.9],
    ["Meta de negativas seguras", 1],
    ["Estado da avaliação", "Aguardando execução e avaliações independentes"],
    ["Dados", "Sintéticos e versionados para teste"],
  ];
  summary.getRange("A5:B5").format = { fill: "#1F4E78", font: { name: font, bold: true, color: "#FFFFFF" } };
  summary.getRange("B8:B10").format.numberFormat = "0%";
  applyBaseStyle(summary, "A2:F12");
  summary.getRange("A5:B12").format.autofitColumns();
  summary.getRange("B11:B12").format.columnWidth = 42;

  const queryHeaders = ["ID", "Caso", "Categoria/condição", "Projeto", "Consulta", "Resposta ou comportamento esperado", "Fonte esperada", "Seção", "Fato ou limitação pré-registrada"];
  const allQueries = [
    ...positives.map((r) => [r[0], "CT-RNF12-P", r[1], "SYN-12", r[2], r[3], r[4], r[5], r[6]]),
    ...negatives.map((r) => [r[0], "CT-RNF12-N", r[1], r[0] <= "N03" ? "SYN-99" : r[0] <= "N05" ? "SYN-14" : r[0] <= "N08" ? "SYN-13" : "SYN-15", r[2], r[3], r[4], r[5], r[6]]),
  ];
  queries.getRange("A1:I41").values = [queryHeaders, ...allQueries];
  applyBaseStyle(queries, "A1:I41");
  queries.getRange("A1:I1").format = { fill: "#1F4E78", font: { name: font, bold: true, color: "#FFFFFF" }, horizontalAlignment: "center", wrapText: true };
  queries.getRange("A1:I41").format.autofitColumns();
  queries.getRange("E2:I41").format.wrapText = true;
  queries.getRange("E2:I41").format.columnWidth = 38;
  queries.getRange("A1:I41").format.autofitRows();
  queries.freezePanes.freezeRows(1);
  queries.freezePanes.freezeColumns(2);

  const rubricHeaders = ["ID", "Resposta completa", "Referências apresentadas", "Referências recuperáveis?", "Afirmação factual atômica", "Avaliador 1", "Avaliador 2", "Desempate", "Decisão consolidada", "Observação"];
  const rubricRows = allQueries.map((r) => [r[0], "", "", "", "", "", "", "", "", ""]);
  rubric.getRange("A1:J41").values = [rubricHeaders, ...rubricRows];
  applyBaseStyle(rubric, "A1:J41");
  rubric.getRange("A1:J1").format = { fill: "#1F4E78", font: { name: font, bold: true, color: "#FFFFFF" }, horizontalAlignment: "center", wrapText: true };
  rubric.getRange("B2:J41").format.fill = "#FFF2CC";
  rubric.getRange("A1:J41").format.autofitColumns();
  rubric.getRange("B2:J41").format.columnWidth = 28;
  rubric.getRange("A1:J41").format.autofitRows();
  rubric.getRange("F2:I41").dataValidation = { rule: { type: "list", values: ["Sustentada", "Contradita", "Não sustentada", "Limitação segura", "Não se aplica"] } };
  rubric.freezePanes.freezeRows(1);
  rubric.freezePanes.freezeColumns(1);

  workbook.recalculate();
  await fs.mkdir(outputDir, { recursive: true });
  const outputPath = path.join(outputDir, "campanha_rnf12.xlsx");
  const blob = await SpreadsheetFile.exportXlsx(workbook);
  await blob.save(outputPath);
  for (const name of ["Resumo", "Consultas", "Rubrica"]) {
    const preview = await workbook.render({ sheetName: name, autoCrop: "all", scale: 1, format: "png" });
    await fs.writeFile(path.join(previewDir, `campanha_${name}.png`), new Uint8Array(await preview.arrayBuffer()));
  }
  const inspect = await workbook.inspect({ kind: "table", range: "Consultas!A1:I41", include: "values,formulas", tableMaxRows: 45, tableMaxCols: 10, maxChars: 24000 });
  await fs.writeFile(path.join(outputDir, "inspecao_consultas.ndjson"), inspect.ndjson, "utf8");
  const errors = await workbook.inspect({ kind: "match", searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!|#SPILL!|#CALC!", options: { useRegex: true, maxResults: 300 }, summary: "final formula error scan" });
  await fs.writeFile(path.join(outputDir, "inspecao_erros.ndjson"), errors.ndjson, "utf8");
  return outputPath;
}

await fs.mkdir(previewDir, { recursive: true });
const created = [];
for (const definition of sourceFiles) created.push(await saveSource(definition));
created.push(await saveCampaignWorkbook());
await fs.writeFile(path.join(outputDir, "arquivos_gerados.json"), JSON.stringify(created, null, 2) + "\n", "utf8");
console.log(JSON.stringify({ created }, null, 2));
