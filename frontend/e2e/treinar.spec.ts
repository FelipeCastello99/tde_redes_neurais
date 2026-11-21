import { expect, test } from "@playwright/test";

const epoch = (n: number) => ({
  epoch: n,
  epochs: 2,
  loss_train: 0.5 - n * 0.1,
  loss_val: 0.55 - n * 0.1,
  acc_train: 0.7 + n * 0.05,
  acc_val: 0.68 + n * 0.05,
  f1_val: 0.6 + n * 0.05,
  grad_norm: 1.2,
  lr: 0.001,
  seconds: n * 0.2,
  best_epoch: n,
});

test("treinar com preset rápido e ver resultados", async ({ page }) => {
  await page.route("**/api/runs", async (route) => {
    if (route.request().method() === "POST") {
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          run_id: "run-train-1",
          name: "Demo",
          status: "queued",
          created_at: "2026-11-20T12:00:00Z",
        }),
      });
    }
    return route.continue();
  });

  await page.route("**/api/runs/run-train-1/stream", (route) =>
    route.fulfill({
      status: 200,
      headers: { "Content-Type": "text/event-stream", "Cache-Control": "no-cache" },
      body: [
        `data: ${JSON.stringify({ type: "status", status: "running" })}`,
        `data: ${JSON.stringify(epoch(1))}`,
        `data: ${JSON.stringify(epoch(2))}`,
        `data: ${JSON.stringify({ type: "done", status: "done" })}`,
      ].join("\n\n") + "\n\n",
    })
  );

  await page.goto("/treinar");
  await page.getByRole("button", { name: /Rápido \(Demo\)/ }).click();
  await page.getByRole("button", { name: /Iniciar Treinamento/i }).click();

  await expect(page.getByText("Treinamento Concluído")).toBeVisible({ timeout: 15_000 });
  await expect(page.getByRole("link", { name: /Ver Resultados Completos/i })).toBeVisible();
});
