# Testes e evidências

| Camada | Comando | Cobertura |
|---|---|---|
| Coletor | `cd collector && uv run pytest` | Cálculos, parsers, sondas, motor de alertas, notificador, detectores, CVE |
| Painel (unidade) | `cd web && pnpm test` | Componentes, reducers, utilitários |
| Painel (E2E) | `cd web && pnpm test:e2e` | Rotas protegidas, responsividade (360/390/1440 px) |
| Painel (E2E logado) | `E2E_EMAIL=… E2E_PASSWORD=… pnpm test:e2e` | Todas as telas, filtro de período, menu mobile, capturas em `web/e2e-evidence/` |
| Alerta ao vivo | `E2E_LIVE=1 … pnpm test:e2e --project=desktop live-alert` | Para o Nginx, espera Vermelho, reinicia, espera Verde |
| Banco | `supabase test db` | RLS e disponibilidade 24 h (pgTAP) |
| Integração (coletor) | `uv run pytest -m integration` | Sondas contra o Docker real |

Anexar ao relatório ABNT: saída dos comandos, capturas de `e2e-evidence/`, o relatório HTML do Playwright (`web/playwright-report/`) e os e-mails recebidos no MailHog.
