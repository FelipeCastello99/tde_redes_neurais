import { expect, test } from "@playwright/test";

const runs = [
  {
    id: "run-done",
    name: "Run antigo",
    status: "done",
    target: "fatal_binario",
    created_at: "2026-11-20T12:00:00Z",
    duration_s: 12.5,
    best_epoch: 3,
    config: { model: { epochs: 5 } },
    metrics: {
      precision_recall_f1: { macro: { f1: 0.5123 } },
      roc_auc: 0.7123,
    },
  },
  {
    id: "run-running",
    name: "Run em execução",
    status: "running",
    target: "fatal_binario",
    created_at: "2026-11-21T12:00:00Z",
    duration_s: null,
    best_epoch: null,
    config: { model: { epochs: 10 } },
    metrics: null,
  },
];

test("apaga um run concluído pelo dashboard", async ({ page }) => {
  const deleted: string[] = [];
  let current = [...runs];

  await page.route("**/api/runs**", async (route) => {
    const request = route.request();
    if (request.method() === "DELETE") {
      const id = request.url().split("/").pop() ?? "";
      deleted.push(id);
      current = current.filter((run) => run.id !== id);
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ status: "deleted" }),
      });
    }
    return route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(current),
    });
  });

  await page.goto("/");
  await expect(page.getByText("Run antigo")).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Apagar Run em execução" })
  ).toBeDisabled();

  await page.getByRole("button", { name: "Apagar Run antigo" }).click();
  const dialog = page.getByRole("dialog");
  await expect(dialog).toBeVisible();
  await expect(dialog.getByText("Run antigo")).toBeVisible();

  await dialog.getByRole("button", { name: "Apagar definitivamente" }).click();

  await expect(page.getByText("Run antigo")).toHaveCount(0);
  await expect(page.getByText("Run em execução")).toBeVisible();
  expect(deleted).toEqual(["run-done"]);
});
