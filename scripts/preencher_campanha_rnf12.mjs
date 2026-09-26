import fs from "node:fs/promises";
import path from "node:path";
import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";

const root = process.cwd();
const inputPath = path.join(root, "outputs/rnf12/campanha_rnf12.xlsx");
const outputPath = path.join(root, "outputs/rnf12/campanha_rnf12_executada.xlsx");
const responsesPath = path.join(root, "resultados/testes-rnf/0a61b353/rnf12/respostas_execucao.json");
const responses = JSON.parse(await fs.readFile(responsesPath, "utf8"));
const byId = new Map(responses.map((item) => [item.id, item]));

const workbook = await SpreadsheetFile.importXlsx(await FileBlob.load(inputPath));
const summary = workbook.worksheets.getItem("Resumo");
const rubric = workbook.worksheets.getItem("Rubrica");

summary.getRange("B11").values = [["Reprovado; avaliações independentes opcionais para caracterizar as falhas"]];
summary.getRange("A14:B19").values = [
  ["Resultado técnico", "Valor"],
  ["Consultas HTTP 200", 40],
  ["Positivas com fonte", 4],
  ["Referências apresentadas", 4],
  ["Referências recuperáveis", 4],
  ["Percentual recuperável", 1],
];
summary.getRange("A14:B14").format = {
  fill: "#1F4E78",
  font: { name: "Arial", size: 10, bold: true, color: "#FFFFFF" },
};
summary.getRange("B19").format.numberFormat = "0%";
summary.getRange("A14:B19").format.autofitColumns();
summary.getRange("A2:A19").format.columnWidth = 38;
summary.getRange("B2:B19").format.columnWidth = 70;

for (let row = 2; row <= 41; row += 1) {
  const id = String(rubric.getRange(`A${row}`).values[0][0]);
  const response = byId.get(id);
  if (!response) continue;
  const references = response.fontes.map((f) => `${f.projeto_id} · ${f.arquivo_origem} · ${f.secao} · chunk ${f.chunk_id}`).join("\n");
  const recoverable = response.fontes.length === 0
    ? "Sem referência"
    : response.fontes.every((f) => f.recuperavel_no_indice) ? "Sim" : "Não";
  rubric.getRange(`B${row}:D${row}`).values = [[response.reply, references, recoverable]];
}
rubric.getRange("B2:D41").format.fill = "#FFFFFF";
rubric.getRange("E2:J41").format.fill = "#FFF2CC";
rubric.getRange("B2:C41").format.wrapText = true;
rubric.getRange("B2").format.columnWidth = 55;
rubric.getRange("C2").format.columnWidth = 48;
rubric.getRange("D2").format.columnWidth = 18;
rubric.getRange("A1:J41").format.autofitRows();

workbook.recalculate();
const inspect = await workbook.inspect({
  kind: "table",
  range: "Rubrica!A1:J41",
  include: "values,formulas",
  tableMaxRows: 45,
  tableMaxCols: 10,
  maxChars: 30000,
});
await fs.writeFile(path.join(root, "outputs/rnf12/inspecao_rubrica_executada.ndjson"), inspect.ndjson, "utf8");
const errors = await workbook.inspect({
  kind: "match",
  searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!|#SPILL!|#CALC!",
  options: { useRegex: true, maxResults: 300 },
  summary: "final formula error scan",
});
await fs.writeFile(path.join(root, "outputs/rnf12/inspecao_erros_executada.ndjson"), errors.ndjson, "utf8");
const preview = await workbook.render({ sheetName: "Rubrica", autoCrop: "all", scale: 1, format: "png" });
await fs.writeFile(path.join(root, "outputs/rnf12/previews/campanha_Rubrica_executada.png"), new Uint8Array(await preview.arrayBuffer()));
const summaryPreview = await workbook.render({ sheetName: "Resumo", autoCrop: "all", scale: 1, format: "png" });
await fs.writeFile(path.join(root, "outputs/rnf12/previews/campanha_Resumo_executada.png"), new Uint8Array(await summaryPreview.arrayBuffer()));
const output = await SpreadsheetFile.exportXlsx(workbook);
await output.save(outputPath);
console.log(outputPath);
