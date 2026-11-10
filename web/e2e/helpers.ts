import { expect, type Page } from "@playwright/test";

export const authenticated = Boolean(process.env.E2E_EMAIL && process.env.E2E_PASSWORD);

export async function login(page: Page) {
  await page.goto("/login");
  await page.getByLabel("E-mail").fill(process.env.E2E_EMAIL ?? "");
  await page.getByRole("textbox", { name: "Senha" }).fill(process.env.E2E_PASSWORD ?? "");
  await page.getByRole("button", { name: "Entrar no painel" }).click();
  await expect(page).toHaveURL(/\/$/);
}

export async function expectNoHorizontalOverflow(page: Page) {
  await expect
    .poll(() => page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth))
    .toBe(true);
}
