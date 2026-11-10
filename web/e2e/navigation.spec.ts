// US-20 / T-200: navigation and usage tests.
//   - "sem sessão" tests always run (no Supabase needed).
//   - "com sessão" tests need a real Supabase user:
//       E2E_EMAIL=... E2E_PASSWORD=... NEXT_PUBLIC_SUPABASE_URL=... \
//       NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY=... pnpm test:e2e
//     They also save screenshots to e2e-evidence/ for the ABNT report (T-201).
import { expect, test } from "@playwright/test";
import { authenticated, expectNoHorizontalOverflow, login } from "./helpers";

const protectedRoutes = ["/", "/services/web", "/services/db", "/services/dns", "/services/smtp", "/security"];

test.describe("sem sessão", () => {
  test.skip(authenticated, "executa apenas sem credenciais de teste");

  for (const route of protectedRoutes) {
    test(`rota protegida ${route} redireciona para /login`, async ({ page }) => {
      await page.goto(route);
      await expect(page).toHaveURL(/\/login/);
      await expect(page.getByRole("button", { name: "Entrar no painel" })).toBeVisible();
    });
  }

  test("página de login é responsiva em 360, 390 e 1440 px", async ({ page }) => {
    for (const width of [360, 390, 1440]) {
      await page.setViewportSize({ width, height: 800 });
      await page.goto("/login");
      await expect(page.getByRole("heading", { name: "Bem-vindo de volta" })).toBeVisible();
      await expectNoHorizontalOverflow(page);
    }
  });
});

test.describe("com sessão", () => {
  test.skip(!authenticated, "defina E2E_EMAIL e E2E_PASSWORD (e as variáveis do Supabase)");

  test("visão consolidada mostra um cartão por serviço", async ({ page }, info) => {
    await login(page);
    for (const name of ["Web Server", "Banco de dados", "DNS", "SMTP"]) {
      await expect(page.getByText(name, { exact: false }).first()).toBeVisible();
    }
    await expectNoHorizontalOverflow(page);
    await page.screenshot({ path: `e2e-evidence/${info.project.name}-visao-geral.png`, fullPage: true });
  });

  for (const id of ["web", "db", "dns", "smtp"]) {
    test(`dashboard ${id}: gráficos, filtro de período e histórico`, async ({ page }, info) => {
      await login(page);
      await page.goto(`/services/${id}`);
      await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
      await expect(page.getByRole("navigation", { name: "Período das métricas" })).toBeVisible();
      await expect(page.getByRole("heading", { name: "Histórico de alertas" })).toBeVisible();

      for (const label of ["6 h", "24 h", "1 h"]) {
        await page.getByRole("link", { name: label, exact: true }).click();
        await expect(page.getByRole("link", { name: label, exact: true })).toHaveAttribute("aria-current", "page");
      }
      await expectNoHorizontalOverflow(page);
      await page.screenshot({ path: `e2e-evidence/${info.project.name}-servico-${id}.png`, fullPage: true });
    });
  }

  test("página de segurança lista alertas, eventos e vulnerabilidades", async ({ page }, info) => {
    await login(page);
    await page.goto("/security");
    await expect(page.getByRole("heading", { name: "Alertas de segurança abertos" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Eventos de segurança" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Vulnerabilidades conhecidas por serviço" })).toBeVisible();
    await expectNoHorizontalOverflow(page);
    await page.screenshot({ path: `e2e-evidence/${info.project.name}-seguranca.png`, fullPage: true });
  });

  test("navegação lateral leva a cada tela", async ({ page }, info) => {
    test.skip(info.project.name === "mobile", "menu lateral é testado abaixo no mobile");
    await login(page);
    await page.getByRole("link", { name: "Segurança" }).click();
    await expect(page).toHaveURL(/\/security$/);
    await page.getByRole("link", { name: "DNS" }).click();
    await expect(page).toHaveURL(/\/services\/dns$/);
  });

  test("menu mobile abre e navega", async ({ page }, info) => {
    test.skip(info.project.name !== "mobile", "somente no viewport mobile");
    await login(page);
    await page.getByRole("button", { name: "Abrir navegação" }).click();
    await page.getByRole("link", { name: "SMTP" }).click();
    await expect(page).toHaveURL(/\/services\/smtp$/);
  });

  test("sair da conta volta para o login", async ({ page }, info) => {
    test.skip(info.project.name === "mobile", "botão de sair fica no menu lateral");
    await login(page);
    await page.getByRole("button", { name: "Sair da conta" }).click();
    await expect(page).toHaveURL(/\/login/);
  });
});
