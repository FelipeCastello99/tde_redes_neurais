import { expect, test } from "@playwright/test";

test("alternar tema e recarregar mantém a escolha", async ({ page }) => {
  await page.goto("/");
  await page.getByTitle("Claro").click();

  await expect(page.locator("html")).toHaveClass(/light/);

  await page.reload();
  await expect(page.locator("html")).toHaveClass(/light/);
});
