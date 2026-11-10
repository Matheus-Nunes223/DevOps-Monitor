// T-112 / RNF-02: "alerta ao vivo". Needs the whole stack running:
//   docker compose up -d   (collector writing to the same Supabase the panel reads)
//   E2E_LIVE=1 E2E_EMAIL=... E2E_PASSWORD=... pnpm test:e2e --project=desktop live-alert
// The test itself stops nginx through Docker, waits for the card to turn red and restarts it.
import { execFileSync } from "node:child_process";
import { expect, test } from "@playwright/test";
import { authenticated, login } from "./helpers";

test.skip(!authenticated || process.env.E2E_LIVE !== "1", "requer E2E_LIVE=1 e o ambiente completo");
test.setTimeout(180_000);

test("parar o Nginx deixa o cartão do Web Server vermelho e voltar o torna verde", async ({ page }) => {
  await login(page);
  const card = page.locator("article, section, div").filter({ hasText: "Web Server" }).first();
  try {
    execFileSync("docker", ["compose", "stop", "nginx"], { cwd: "..", stdio: "inherit" });
    await expect(page.getByText(/Crítico|Vermelho/).first()).toBeVisible({ timeout: 90_000 });
    await page.screenshot({ path: "e2e-evidence/alerta-ao-vivo-critico.png", fullPage: true });
  } finally {
    execFileSync("docker", ["compose", "start", "nginx"], { cwd: "..", stdio: "inherit" });
  }
  await expect(card).toBeVisible();
  await expect(page.getByText(/Normal|Verde|Operacional/).first()).toBeVisible({ timeout: 120_000 });
  await page.screenshot({ path: "e2e-evidence/alerta-ao-vivo-resolvido.png", fullPage: true });
});
