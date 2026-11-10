# CLAUDE.md · Plataforma de Monitoramento DevOps

Trabalho final de Redes de Computadores (IDP). Ambiente Docker com Web, Banco, DNS e SMTP; coletor Python grava métricas no Supabase; painel Next.js na Vercel mostra dashboards e alertas.

## Leia antes de qualquer tarefa
1. `docs/sdd/00-constitution.md`: regras que não mudam
2. `docs/sdd/01-spec.md`: o que o produto faz (RF/RNF, limites de alerta)
3. `docs/sdd/02-plan.md`: arquitetura, schema, como cada métrica é coletada
4. `docs/sdd/03-tasks.md`: tarefas por sprint
5. `docs/sdd/04-workflow-plugins.md`: qual plugin usar em cada etapa

## Regras de trabalho
- **Spec-driven:** nenhuma história começa sem `docs/sdd/features/US-XX.md` e `docs/sdd/plans/US-XX-plan.md`. Use brainstorming e depois writing-plans.
- **TDD sempre** (skill test-driven-development). Teste falhando antes do código.
- **context7 antes de usar uma API de biblioteca.** Não confie na memória para Next.js, @supabase/ssr, Recharts, psycopg, dnspython, APScheduler.
- **Nada é "pronto" sem rodar a verificação** e mostrar a saída (skill verification-before-completion).
- Uma branch/worktree por história: `feat/US-XX-slug`. Commits: `feat(US-XX): ...`.
- Migrações só em `supabase/migrations`. Depois de cada uma: gerar tipos TS e rodar os advisors pelo MCP do Supabase.
- A service role key do Supabase **nunca** vai para `web/`.
- Sonda que falha registra log e segue (constituição P1). Nunca `except: pass`.

## Comandos
```bash
# Ambiente monitorado + coletor
docker compose up -d
docker compose logs -f collector

# Coletor
cd collector
uv sync
uv run ruff check && uv run pyright && uv run pytest
uv run pytest -m integration          # precisa do docker compose rodando

# Painel
cd web
pnpm install --frozen-lockfile
pnpm dev                               # http://localhost:3000
pnpm lint && pnpm typecheck && pnpm test && pnpm build
pnpm exec playwright install chromium --only-shell  # uma vez por máquina
pnpm test:e2e                          # E2E mobile + desktop

# Gerador de falhas (demo)
cd loadgen && uv run python -m loadgen <normal|spike|bruteforce|stop_service|edit_config|smtp_flood>

# Interfaces úteis
# MailHog: http://localhost:8025
```

## Revisão antes do PR
`/code-review` → pr-review-toolkit (silent-failure-hunter, pr-test-analyzer) → differential-review → insecure-defaults / sharp-edges / owasp-security conforme o que mudou. Achado de severidade alta bloqueia o merge.

## Convenções
- Métricas: `<servico>.<metrica>` com unidade no nome (`web.latency_p95_ms`, `db.size_bytes`).
- Estados: `green` / `yellow` / `red` no banco; Verde / Amarelo / Vermelho na interface.
- Textos da interface e da documentação em português.

## Aprendizados
<!-- Atualize com claude-md-management ao fim de cada história ou sprint. -->
- A interface Next.js mantém a identidade escura do protótipo, mas estados de serviço ficam como “sem dados” até receber métricas reais.
- Para o painel, copie apenas as duas variáveis públicas para `web/.env.local`; nunca copie a service role para `NEXT_PUBLIC_*`.
