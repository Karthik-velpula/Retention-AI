import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { Workbook, SpreadsheetFile } from "@oai/artifact-tool";

const scriptDir = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(scriptDir, "..");
const inputPath = path.join(repoRoot, "exports", "seeded-data-2026-04-23", "full_project_data_studentwise.csv");
const outputPath = path.join(repoRoot, "exports", "seeded-data-2026-04-23", "full_project_data_studentwise.xlsx");

const csvText = await fs.readFile(inputPath, "utf8");
const workbook = await Workbook.fromCSV(csvText, { sheetName: "Student Data" });
const sheet = workbook.worksheets.get("Student Data");

if (!sheet) {
  throw new Error("Student Data sheet was not created.");
}

sheet.freezePanes = { rows: 1, cols: 2 };

const usedRange = sheet.getUsedRange();
usedRange.format.wrapText = false;

const headerRange = sheet.getRange("A1:BP1");
headerRange.format.font.bold = true;
headerRange.format.fill.color = "#DCE6F2";

const outputDir = path.dirname(outputPath);
await fs.mkdir(outputDir, { recursive: true });
const output = await SpreadsheetFile.exportXlsx(workbook);
await output.save(outputPath);

console.log(outputPath);
