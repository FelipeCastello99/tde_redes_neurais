import { expect, test } from "@playwright/test";

const run = {
  id: "run-sim-1",
  name: "Modelo de Teste",
  target: "fatal_binario",
  status: "done",
  created_at: "2026-11-20T12:00:00Z",
  config: {
    data: {
      feature_groups: ["localizacao", "tempo", "via", "circunstancia", "frota"],
    },
    model: {},
  },
  metrics: {},
};

const meta = {
  feature_groups: ["localizacao", "tempo", "via", "circunstancia", "frota"],
  categories: {
    uf: ["SP", "MG"],
    dia_semana: ["segunda-feira", "sábado"],
    tipo_pista: ["Simples", "Dupla"],
    tracado_principal: ["Reta", "Curva"],
    uso_solo: ["Sim", "Não"],
    sentido_via: ["Crescente", "Decrescente"],
    causa_acidente: ["Ultrapassagem Indevida", "Velocidade incompatível"],
    tipo_acidente: ["Colisão frontal", "Saída de leito carroçável"],
    fase_dia: ["Pleno dia", "Plena Noite"],
    condicao_metereologica: ["Céu Claro", "Chuva"],
  },
};

test("simulador retorna probabilidade", async ({ page }) => {
  await page.route("**/api/meta", (route) =>
    route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(meta) })
  );
  await page.route("**/api/runs?limit=50", (route) =>
    route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify([run]) })
  );
  await page.route("**/api/predict", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        predicted_class_index: 1,
        predicted_class: "vitima_fatal",
        probabilities: { sem_vitima_fatal: 0.8, vitima_fatal: 0.2 },
        threshold_used: 0.5,
        contributions: [{ feature: "km", delta: 0.05 }],
      }),
    })
  );

  await page.goto("/simulador");
  await expect(page.locator("select").first()).toHaveValue("run-sim-1");
  await expect(page.locator("select").first()).toContainText("Modelo de Teste");
  await expect(page.getByText("TRACADO DA VIA (1º TERMO)")).toBeVisible();

  await page.getByRole("button", { name: /Estimar Gravidade/i }).click();

  await expect(page.getByRole("heading", { name: "vitima_fatal" })).toBeVisible();
  await expect(page.getByText(/20,0%/)).toBeVisible();
});
