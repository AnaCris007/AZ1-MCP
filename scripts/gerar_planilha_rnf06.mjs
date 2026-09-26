import fs from "node:fs/promises";

import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const inputPath =
  "resultados/testes-rnf/6b3eb96/rnf06/resultado.json";
const outputDir = "outputs/rnf06-20260925";
const outputPath = `${outputDir}/resultado-rnf06.xlsx`;

const raw = JSON.parse(await fs.readFile(inputPath, "utf8"));
const { resumo, registros } = raw;
if (registros.length !== 30) {
  throw new Error(`Esperados 30 registros; encontrados ${registros.length}`);
}

const wb = Workbook.create();
const summary = wb.worksheets.add("Resumo");
const details = wb.worksheets.add("Detalhes");

const navy = "#17365D";
const blue = "#D9EAF7";
const lightBlue = "#EEF5FB";
const green = "#E2F0D9";
const greenText = "#375623";
const red = "#FCE4D6";
const redText = "#9C0006";
const gray = "#666666";
const border = "#C9D2DC";

summary.showGridLines = false;
summary.tabColor = navy;
summary.mergeCells("A1:F1");
summary.getRange("A1").values = [["RNF06 — Acurácia da transcrição de voz"]];
summary.getRange("A1:F1").format = {
  fill: navy,
  font: { bold: true, color: "#FFFFFF", size: 16 },
  horizontalAlignment: "left",
  verticalAlignment: "center",
};
summary.getRange("A1:F1").format.rowHeight = 30;

summary.mergeCells("A2:F2");
summary.getRange("A2").values = [[
  "Execução automatizada dos 30 áudios pelo mesmo contrato HTTP usado pelo produto",
]];
summary.getRange("A2:F2").format = {
  fill: lightBlue,
  font: { color: gray, italic: true, size: 10 },
};

summary.getRange("A4:B4").values = [["Indicador", "Resultado"]];
summary.getRange("A4:B4").format = {
  fill: navy,
  font: { bold: true, color: "#FFFFFF" },
  borders: { preset: "all", style: "thin", color: border },
};
summary.getRange("A5:A12").values = [
  ["Caso de teste"],
  ["Áudios executados"],
  ["Áudios com erro"],
  ["WER geral"],
  ["WER — fala limpa"],
  ["WER — com ruído"],
  ["Meta máxima"],
  ["Resultado"],
];
summary.getRange("B5").values = [[resumo.caso]];
summary.getRange("B6").formulas = [["=COUNTIFS(Detalhes!F2:F31,\"Executado\")"]];
summary.getRange("B7").formulas = [["=30-B6"]];
summary.getRange("B8").formulas = [[
  "=(SUM(Detalhes!L2:L31)+SUM(Detalhes!M2:M31)+SUM(Detalhes!N2:N31))/SUM(Detalhes!O2:O31)",
]];
summary.getRange("B9").formulas = [[
  "=(SUMIFS(Detalhes!L2:L31,Detalhes!E2:E31,\"limpa\")+SUMIFS(Detalhes!M2:M31,Detalhes!E2:E31,\"limpa\")+SUMIFS(Detalhes!N2:N31,Detalhes!E2:E31,\"limpa\"))/SUMIFS(Detalhes!O2:O31,Detalhes!E2:E31,\"limpa\")",
]];
summary.getRange("B10").formulas = [[
  "=(SUMIFS(Detalhes!L2:L31,Detalhes!E2:E31,\"ruido\")+SUMIFS(Detalhes!M2:M31,Detalhes!E2:E31,\"ruido\")+SUMIFS(Detalhes!N2:N31,Detalhes!E2:E31,\"ruido\"))/SUMIFS(Detalhes!O2:O31,Detalhes!E2:E31,\"ruido\")",
]];
summary.getRange("B11").values = [[resumo.meta_wer]];
summary.getRange("B12").formulas = [[
  "=IF(B6<30,\"Bloqueado\",IF(B8<=B11,\"Aprovado\",\"Reprovado\"))",
]];
summary.getRange("A5:B12").format.borders = {
  preset: "all",
  style: "thin",
  color: border,
};
summary.getRange("A5:A12").format.fill = "#F3F6F9";
summary.getRange("A5:A12").format.font = { bold: true, color: "#24364B" };
summary.getRange("B8:B11").setNumberFormat("0.00%");
summary.getRange("B12").format = {
  fill: green,
  font: { bold: true, color: greenText },
  horizontalAlignment: "center",
};

summary.getRange("D4:F4").values = [["Condição", "Áudios", "WER"]];
summary.getRange("D4:F4").format = {
  fill: navy,
  font: { bold: true, color: "#FFFFFF" },
  borders: { preset: "all", style: "thin", color: border },
};
summary.getRange("D5:D7").values = [["Fala limpa"], ["Com ruído"], ["Total"]];
summary.getRange("E5").formulas = [["=COUNTIFS(Detalhes!E2:E31,\"limpa\")"]];
summary.getRange("E6").formulas = [["=COUNTIFS(Detalhes!E2:E31,\"ruido\")"]];
summary.getRange("E7").formulas = [["=SUM(E5:E6)"]];
summary.getRange("F5").formulas = [["=B9"]];
summary.getRange("F6").formulas = [["=B10"]];
summary.getRange("F7").formulas = [["=B8"]];
summary.getRange("D5:F7").format.borders = {
  preset: "all",
  style: "thin",
  color: border,
};
summary.getRange("D7:F7").format = {
  fill: blue,
  font: { bold: true, color: navy },
  borders: { preset: "all", style: "thin", color: border },
};
summary.getRange("F5:F7").setNumberFormat("0.00%");

summary.getRange("D9:E9").values = [["Metadado", "Valor"]];
summary.getRange("D9:E9").format = {
  fill: navy,
  font: { bold: true, color: "#FFFFFF" },
  borders: { preset: "all", style: "thin", color: border },
};
summary.getRange("D10:D15").values = [
  ["Modelo"],
  ["Idioma"],
  ["Commit"],
  ["Início (UTC)"],
  ["Fim (UTC)"],
  ["Normalização"],
];
summary.getRange("E10:E15").values = [
  [resumo.modelo],
  [resumo.idioma],
  [resumo.commit],
  [resumo.iniciado_em_utc],
  [resumo.finalizado_em_utc],
  [resumo.normalizacao],
];
summary.getRange("D10:E15").format.borders = {
  preset: "all",
  style: "thin",
  color: border,
};
summary.getRange("D10:D15").format.fill = "#F3F6F9";
summary.getRange("D10:D15").format.font = { bold: true };
summary.getRange("E12:E14").format.font = { name: "Consolas", size: 9 };
summary.getRange("E13:E14").setNumberFormat("yyyy-mm-dd hh:mm:ss");
summary.getRange("E15").format.wrapText = true;

summary.mergeCells("A14:B14");
summary.getRange("A14").values = [["Critério de decisão"]];
summary.getRange("A14:B14").format = {
  fill: blue,
  font: { bold: true, color: navy },
};
summary.mergeCells("A15:B17");
summary.getRange("A15").values = [[
  "Aprova quando os 30 áudios são transcritos sem falha e o WER do corpus é menor ou igual a 15%. WER = (substituições + exclusões + inserções) ÷ palavras da referência.",
]];
summary.getRange("A15:B17").format = {
  wrapText: true,
  verticalAlignment: "top",
  borders: { preset: "all", style: "thin", color: border },
};

summary.getRange("A1:F17").format.font.name = "Aptos";
summary.getRange("A:A").format.columnWidth = 25;
summary.getRange("B:B").format.columnWidth = 20;
summary.getRange("C:C").format.columnWidth = 3;
summary.getRange("D:D").format.columnWidth = 18;
summary.getRange("E:E").format.columnWidth = 56;
summary.getRange("F:F").format.columnWidth = 14;
summary.getRange("A15:B17").format.rowHeight = 26;
summary.freezePanes.freezeRows(2);

const headers = [
  "ID",
  "Arquivo",
  "Locutor",
  "Frase",
  "Condição",
  "Status",
  "Referência",
  "Transcrição",
  "Idioma",
  "Confiança",
  "Duração (s)",
  "S",
  "D",
  "I",
  "N",
  "WER",
  "SHA-256",
  "Bytes",
  "Audio ID",
  "Erro",
];
details.showGridLines = false;
details.tabColor = "#5B9BD5";
details.getRange("A1:T1").values = [headers];
details.getRange("A1:T1").format = {
  fill: navy,
  font: { bold: true, color: "#FFFFFF" },
  horizontalAlignment: "center",
  verticalAlignment: "center",
  wrapText: true,
  borders: { preset: "all", style: "thin", color: "#FFFFFF" },
};
details.getRange("A1:T1").format.rowHeight = 30;

const rows = registros.map((r) => [
  r.id,
  r.arquivo,
  r.locutor,
  r.frase,
  r.condicao,
  r.status,
  r.referencia,
  r.transcricao,
  r.idioma,
  r.confianca,
  r.duracao_s,
  r.substituicoes,
  r.exclusoes,
  r.insercoes,
  r.palavras_referencia,
  null,
  r.sha256,
  r.bytes,
  r.audio_id,
  r.erro,
]);
details.getRange("A2:T31").values = rows;
details.getRange("P2").formulasR1C1 = [["=IF(RC[-10]=\"Executado\",(RC[-4]+RC[-3]+RC[-2])/RC[-1],\"\")"]];
details.getRange("P2:P31").fillDown();
details.getRange("A2:T31").format.borders = {
  preset: "all",
  style: "thin",
  color: border,
};
details.getRange("A2:T31").format.verticalAlignment = "top";
details.getRange("G2:H31").format.wrapText = true;
details.getRange("T2:T31").format.wrapText = true;
details.getRange("J2:J31").setNumberFormat("0.000");
details.getRange("K2:K31").setNumberFormat("0.000");
details.getRange("P2:P31").setNumberFormat("0.00%");
details.getRange("R2:R31").setNumberFormat("0");
details.getRange("A2:T31").format.font = { name: "Aptos", size: 9 };
for (let row = 2; row <= 31; row += 2) {
  details.getRange(`A${row}:T${row}`).format.fill = "#F7FAFC";
}
details.getRange("P2:P31").conditionalFormats.add("cellIs", {
  operator: "greaterThan",
  formula: resumo.meta_wer,
  format: { fill: red, font: { color: redText, bold: true } },
});
details.getRange("P2:P31").conditionalFormats.add("cellIs", {
  operator: "lessThanOrEqual",
  formula: resumo.meta_wer,
  format: { fill: green, font: { color: greenText } },
});
details.freezePanes.freezeRows(1);
details.freezePanes.freezeColumns(2);
details.getRange("A:A").format.columnWidth = 13;
details.getRange("B:B").format.columnWidth = 24;
details.getRange("C:F").format.columnWidth = 12;
details.getRange("G:H").format.columnWidth = 52;
details.getRange("I:I").format.columnWidth = 10;
details.getRange("J:K").format.columnWidth = 13;
details.getRange("L:P").format.columnWidth = 8;
details.getRange("Q:Q").format.columnWidth = 66;
details.getRange("R:R").format.columnWidth = 12;
details.getRange("S:S").format.columnWidth = 36;
details.getRange("T:T").format.columnWidth = 32;
details.tables.add("A1:T31", true, "ResultadosRNF06");

wb.recalculate();

const summaryCheck = await wb.inspect({
  kind: "region",
  sheetId: "Resumo",
  range: "A1:F17",
  maxChars: 7000,
});
const detailCheck = await wb.inspect({
  kind: "region",
  sheetId: "Detalhes",
  range: "A1:T31",
  maxChars: 12000,
  tableMaxRows: 35,
  tableMaxCols: 20,
});
const checksText = `${summaryCheck.ndjson}\n${detailCheck.ndjson}`;
const formulaErrors = checksText.match(/#(?:REF!|DIV\/0!|VALUE!|NAME\?|N\/A)/g) ?? [];
if (formulaErrors.length) {
  throw new Error(`Erros de fórmula encontrados: ${formulaErrors.join(", ")}`);
}

await fs.mkdir(outputDir, { recursive: true });
const summaryPreview = await wb.render({
  sheetName: "Resumo",
  autoCrop: "all",
  scale: 1,
  format: "png",
});
await fs.writeFile(
  "/private/tmp/rnf06-resumo.png",
  new Uint8Array(await summaryPreview.arrayBuffer()),
);
const detailsPreview = await wb.render({
  sheetName: "Detalhes",
  autoCrop: "all",
  scale: 0.5,
  format: "png",
});
await fs.writeFile(
  "/private/tmp/rnf06-detalhes.png",
  new Uint8Array(await detailsPreview.arrayBuffer()),
);

const xlsx = await SpreadsheetFile.exportXlsx(wb);
await xlsx.save(outputPath);

console.log(JSON.stringify({ outputPath, summaryCheck: summaryCheck.ndjson }, null, 2));
