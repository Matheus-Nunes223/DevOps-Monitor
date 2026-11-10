import { expect, test } from "@playwright/test";
import { authenticated } from "./helpers";

test("protected overview redirects to an explanatory login screen", async ({ page }) => {
  test.skip(authenticated, "requires the blank-Supabase setup");
  const response = await page.goto("/");

  await expect(page).toHaveURL(/\/login\?reason=configuration$/);
  expect(response?.headers()["x-frame-options"]).toBe("DENY");
  expect(response?.headers()["content-security-policy"]).toContain("default-src 'self'");
  await expect(page.getByRole("heading", { name: "Bem-vindo de volta" })).toBeVisible();
  await expect(page.getByLabel("E-mail")).toBeVisible();
  await expect(page.getByRole("textbox", { name: "Senha" })).toBeVisible();
  await expect(page.getByRole("status")).toContainText("aguardando a configuração do projeto Supabase");
});

test("login form remains usable on a narrow viewport", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/login");

  await expect(page.getByRole("heading", { name: "Bem-vindo de volta" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Entrar no painel" })).toBeVisible();
  await expect.poll(() =>
    page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth),
  ).toBe(true);
});

test("login layout has no horizontal overflow at the 360px minimum width", async ({ page }) => {
  await page.setViewportSize({ width: 360, height: 800 });
  await page.goto("/login");

  await expect(page.getByRole("heading", { name: "Bem-vindo de volta" })).toBeVisible();
  await expect.poll(() =>
    page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth),
  ).toBe(true);
});
