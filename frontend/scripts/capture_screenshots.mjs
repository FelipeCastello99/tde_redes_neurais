import { chromium } from "playwright";
import fs from "node:fs";
import path from "node:path";

const baseURL = process.env.SCREENSHOT_BASE_URL || "http://localhost:3000";
const outDir = path.resolve(process.env.SCREENSHOT_OUT_DIR || "../docs/screenshots");
fs.mkdirSync(outDir, { recursive: true });

async function main() {
  const runs = await fetch(`${baseURL}/api/runs`).then((response) => response.json());
  const run = runs.find((item) => item.status === "done") || runs[0];
  if (!run) throw new Error("Nenhum run disponível para as capturas");

  const browser = await chromium.launch();
  const page = await browser.newPage({
    viewport: { width: 1440, height: 1000 },
    colorScheme: "dark",
  });

  const shots = [
    ["01-dashboard", "/", "Histórico Recente"],
    ["02-treinar", "/treinar", "Treinamento de Rede Neural"],
    ["03-resultados", `/resultados/${run.id}`, "Matriz de Confusão"],
    ["04-comparar", `/comparar?ids=${run.id}`, "Desempenho Geral"],
    ["05-dados", "/dados", "Dicionário do Dataset"],
  ];

  for (const [name, route, marker] of shots) {
    await page.goto(`${baseURL}${route}`, { waitUntil: "networkidle" });
    await page.addStyleTag({ content: "header{position:static!important}.sticky{position:static!important}" });
    await page.getByText(marker, { exact: false }).first().waitFor({ timeout: 30_000 });
    await page.waitForTimeout(800);
    await page.screenshot({ path: path.join(outDir, `${name}.png`), fullPage: true });
    console.log("captured", name);
  }

  await page.goto(`${baseURL}/simulador?run=${run.id}`, { waitUntil: "networkidle" });
  await page.addStyleTag({ content: "header{position:static!important}.sticky{position:static!important}" });
  await page.getByRole("button", { name: /Estimar Gravidade/i }).click();
  await page.getByText("Previsão do Modelo").waitFor({ timeout: 30_000 });
  await page.waitForTimeout(800);
  await page.screenshot({ path: path.join(outDir, "06-simulador.png"), fullPage: true });
  console.log("captured 06-simulador");

  await browser.close();
  fs.writeFileSync(
    path.join(outDir, "README.md"),
    `# Capturas de tela\n\nGeradas com \`frontend/scripts/capture_screenshots.mjs\` a partir do run \`${run.id}\` (${run.name}).\n`
  );
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
