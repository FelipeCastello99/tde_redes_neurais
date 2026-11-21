import { expect, test } from "@playwright/test";

test.describe("responsividade", () => {
  test.use({ viewport: { width: 390, height: 844 } });

  test("mobile esconde a sidebar e mantém o conteúdo", async ({ page }) => {
    await page.goto("/");
    await expect(page.locator("aside")).toBeHidden();
    await expect(page.getByRole("link", { name: /Novo Treinamento/i })).toBeVisible();
  });
});

test.describe("desktop", () => {
  test.use({ viewport: { width: 1366, height: 768 } });

  test("desktop mostra a sidebar e a navegação", async ({ page }) => {
    await page.goto("/");
    await expect(page.locator("aside")).toBeVisible();
    await expect(page.getByRole("link", { name: "Simulador" })).toBeVisible();
  });
});
