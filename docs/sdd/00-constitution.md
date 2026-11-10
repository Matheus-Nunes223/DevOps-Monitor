# 00 · Constituição do projeto

> Regras que não mudam de uma história para outra. Toda spec, plano e PR é avaliado contra este documento.
> Se uma regra precisar mudar, mude aqui primeiro (via PR) e só depois no código.

## 1. Fluxo spec-driven (obrigatório)

Nenhum código é escrito sem passar por estas etapas, nesta ordem:

1. **Spec da história** em `docs/sdd/features/US-XX.md` (template em `docs/sdd/templates/feature-spec.md`).
2. **Plano** em `docs/sdd/plans/US-XX-plan.md` (template em `docs/sdd/templates/plan.md`).
3. **Implementação com TDD**: teste falhando → código mínimo → refatorar.
4. **Verificação**: testes, lint, tipos e (para telas) Playwright passando antes de dizer "pronto".
5. **Revisão** de código e de segurança no diff.
6. **PR** com link para a spec e para o plano.

A spec diz **o quê** e **por quê**. O plano diz **como**. O código só implementa o plano.

## 2. Princípios técnicos

| # | Princípio | Consequência prática |
|---|---|---|
| P1 | **O coletor nunca para por causa de uma sonda.** | Cada sonda roda em `try/except` próprio, registra o erro em log e grava a métrica como ausente. Exceção engolida sem log é bug. |
| P2 | **Dado medido, não inventado.** | Nada de valores simulados no painel. Se a métrica não foi coletada, a tela mostra "sem dados". |
| P3 | **O banco é o contrato.** | Coletor e painel só conversam pelo Supabase. O schema em `supabase/migrations` é a fonte da verdade; os tipos TS são gerados dele. |
| P4 | **Escrita só pelo coletor.** | RLS ativa em todas as tabelas. O painel usa a anon key e só lê. A service role key existe apenas no coletor. |
| P5 | **Segredos só em variável de ambiente.** | `.env` no `.gitignore`; `.env.example` sempre atualizado. |
| P6 | **Limites de alerta são dados, não código.** | Ficam na tabela `alert_rules`, com seed em migração. |
| P7 | **Tudo reproduzível com um comando.** | `docker compose up` sobe o ambiente monitorado + coletor. `pnpm dev` sobe o painel. |
| P8 | **Documentação viva.** | Cada história que muda instalação ou operação atualiza o Guia de Instalação ou o runbook no mesmo PR. |

## 3. Stack fixada

| Camada | Escolha | Versão mínima |
|---|---|---|
| Coletor | Python | 3.12 |
| Gerência de pacotes Python | uv | — |
| Testes Python | pytest | — |
| Tipos Python | pyright (modo `standard`) | — |
| Lint Python | ruff | — |
| Painel | Next.js (App Router) + TypeScript `strict` | 15 |
| Gerência de pacotes JS | pnpm | — |
| UI | Tailwind CSS + shadcn/ui + Recharts | — |
| Testes JS | Vitest (unidade) + Playwright (E2E) | — |
| Banco/Auth/Realtime | Supabase | — |
| Deploy do painel | Vercel | — |
| Ambiente monitorado | Docker Compose | v2 |

Qualquer biblioteca nova precisa de justificativa no plano. Antes de usar uma API de biblioteca, consulte a documentação atual pelo **context7**.

## 4. Padrões de código

- Python: funções puras para cálculos (taxas, percentis, z-score, avaliação de regra) separadas do I/O. Tipagem completa. Sem `print`; use `logging` com JSON.
- TypeScript: sem `any`. Server Components por padrão; Client Components só onde há interação ou Realtime.
- Nomes de métricas no formato `<servico>.<metrica>` (`web.latency_p95_ms`, `db.qps`). Unidade no nome quando houver.
- Commits no padrão Conventional Commits, citando a história: `feat(US-05): coleta latência p95 do nginx`.
- Uma branch por história: `feat/US-XX-descricao-curta`.

## 5. Segurança mínima

- Nenhum PR é mesclado com achado de severidade **alta** das revisões de segurança.
- Cabeçalhos de segurança no Next.js (CSP, HSTS, X-Frame-Options, Referrer-Policy).
- Entradas externas (logs, respostas de APIs, nomes de arquivos) são tratadas como não confiáveis.
- Dependências fixadas em lockfile (`uv.lock`, `pnpm-lock.yaml`).

## 6. Definição de Pronto

1. Critérios de aceite da spec demonstrados no ambiente Docker.
2. Testes automatizados novos passando (pytest / Vitest / Playwright).
3. PR revisado (revisão automatizada + colega da dupla), sem achados de segurança altos.
4. Migrações versionadas e RLS ativa em tabelas novas.
5. Nenhum segredo no código; `.env.example` atualizado.
6. Preview na Vercel funcionando; Guia de Instalação atualizado se algo mudou.
