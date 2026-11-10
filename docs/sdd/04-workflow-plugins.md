# 04 · Fluxo de trabalho com os plugins do Claude Code

> Como cada plugin instalado entra no ciclo spec → plano → código → revisão → PR.
> Os nomes de comandos e skills podem variar entre versões. Confira com `/help` e `/plugin` antes de usar e ajuste esta página se algo mudou.

## 1. Arrumar o ambiente antes de começar

| Problema | O que fazer |
|---|---|
| **GitHub MCP com HTTP 401** | Gere um novo token (GitHub → Settings → Developer settings → Personal access tokens, fine-grained, com acesso ao repositório: Contents, Pull requests e Issues em leitura e escrita). Atualize a variável usada pelo servidor MCP do GitHub e reinicie o Claude Code. Enquanto isso, o `gh` CLI (`gh auth login`) cobre PRs e issues. |
| **superpowers instalado duas vezes** (7.0.0 em claude-plugins-official e 7.0.1 em superpowers-marketplace) | Mantenha só um. As skills têm os mesmos nomes e o Claude pode carregar a versão errada ou as duas. Sugestão: manter a 7.0.1 e desinstalar a outra pelo `/plugin`. |
| **dart-flutter e jdtls-lsp** | Não são usados neste projeto. Desative-os aqui para economizar contexto e evitar diagnósticos irrelevantes. |
| **supabase 0.1.16 vs 0.1.15 no projeto Luvoy** | Sem impacto aqui. Este projeto usa a versão do escopo de usuário. |

## 2. O ciclo de uma história

```
 US-XX no backlog
   │
   ▼
 ① Spec ............ superpowers: brainstorming          → docs/sdd/features/US-XX.md
   │
   ▼
 ② Plano ........... superpowers: writing-plans + context7 → docs/sdd/plans/US-XX-plan.md
   │
   ▼
 ③ Branch .......... superpowers: using-git-worktrees     → feat/US-XX-...
   │
   ▼
 ④ Implementação ... superpowers: test-driven-development
   │                 + subagent-driven-development (tarefas independentes)
   │                 + context7 · supabase · frontend-design · pyright/typescript LSP
   ▼
 ⑤ Verificação ..... superpowers: verification-before-completion + playwright
   │
   ▼
 ⑥ Revisão ......... code-review · pr-review-toolkit · code-simplifier
   │                 Trail of Bits (differential-review, insecure-defaults, sharp-edges, static-analysis)
   │                 owasp-security (telas e APIs)
   ▼
 ⑦ PR e deploy ..... superpowers: finishing-a-development-branch + GitHub MCP/gh + Vercel preview
   │
   ▼
 ⑧ Aprendizado ..... claude-md-management → atualiza CLAUDE.md
```

## 3. Cada etapa em detalhe

### ① Spec: `superpowers` → brainstorming
Peça: *"Use brainstorming para escrever a spec da US-05 a partir de docs/sdd/01-spec.md e do template docs/sdd/templates/feature-spec.md."*
O brainstorming faz perguntas uma de cada vez e fecha num documento. A spec tem que ter critérios em Given/When/Then e casos de borda (log vazio, log rotacionado, serviço fora).

### ② Plano: `superpowers` → writing-plans + `context7`
Peça: *"Use writing-plans para a US-05 seguindo docs/sdd/02-plan.md. Consulte o context7 para a API atual de cada biblioteca citada."*
O plano sai com tarefas de 2 a 5 minutos, caminho exato dos arquivos e o teste de cada passo.

### ③ Branch: `superpowers` → using-git-worktrees
Uma worktree por história deixa a dupla trabalhar em paralelo: um no coletor, outro no painel.

### ④ Implementação
| Ferramenta | Quando usar |
|---|---|
| **test-driven-development** (superpowers) | Sempre. Teste falhando primeiro, depois o código mínimo. Obrigatório em `calc.py`, `alerts/engine.py` e `security/*`. |
| **subagent-driven-development** (superpowers) | Tarefas independentes do mesmo plano, como as 4 páginas de dashboard (T-121 a T-124) ou as sondas DNS e SMTP. |
| **systematic-debugging** (superpowers) | Quando um teste falha sem motivo óbvio. Nada de "tentar coisas". |
| **context7** | Antes de usar qualquer API: Next.js, `@supabase/ssr`, Supabase Realtime, Recharts, psycopg, dnspython, APScheduler, docker SDK, icmplib, Playwright. |
| **supabase** (MCP) | Aplicar migrações, rodar SQL de verificação, gerar tipos TypeScript, rodar os advisors de segurança e desempenho depois de cada migração. Use num projeto de desenvolvimento, nunca com dados reais. |
| **frontend-design** | Todas as telas (US-10 a US-12, segurança). Defina a direção visual uma vez no início e registre no `CLAUDE.md`. |
| **pyright-lsp** / **typescript-lsp** | Ficam ativos o tempo todo. Erro de tipo bloqueia o "pronto". |

### ⑤ Verificação: `superpowers` → verification-before-completion + `playwright`
Antes de dizer "pronto", rode e mostre a saída de:
```
cd collector && uv run ruff check && uv run pyright && uv run pytest
cd web && pnpm lint && pnpm tsc --noEmit && pnpm vitest run && pnpm playwright test
```
Para telas, use o MCP do **Playwright** para navegar pelo preview, tirar capturas e conferir o responsivo (390 px e 1440 px).

### ⑥ Revisão
| Plugin | Uso neste projeto |
|---|---|
| **code-review** | Revisão geral do PR (`/code-review`). |
| **pr-review-toolkit** | Agentes especializados. Os mais úteis aqui: *silent-failure-hunter* (sondas que engolem exceção violam P1), *pr-test-analyzer* (cobertura dos critérios de aceite), *type-design-analyzer* (modelos `Metric`/`Alert`). |
| **code-simplifier** | Depois que a história funciona, para enxugar duplicação (ex.: as 4 páginas de dashboard). |
| **differential-review** (Trail of Bits) | Revisão de segurança focada no diff de cada PR. |
| **insecure-defaults** (Trail of Bits) | `docker-compose.yml`, configs de Nginx/Postgres/Postfix, `.env.example`: senhas padrão, portas expostas, socket Docker. |
| **sharp-edges** (Trail of Bits) | APIs perigosas: `subprocess`/`docker exec`, parsing de logs, SQL montado por string. |
| **static-analysis** (Trail of Bits) | Semgrep (e CodeQL, se disponível) no fim de cada sprint, em `collector/` e `web/`. |
| **variant-analysis** (Trail of Bits) | Achou um bug? Procure o mesmo padrão no resto do código. |
| **owasp-security** | Painel e Supabase: autenticação, RLS, cabeçalhos, XSS, exposição de chaves. Base do item "segurança da plataforma" no relatório. |

### ⑦ PR e deploy
- **finishing-a-development-branch** (superpowers) conduz o fechamento: testes, merge ou PR, limpeza da worktree.
- **GitHub MCP** (com o token renovado) ou `gh pr create`. O PR leva o link para `features/US-XX.md` e `plans/US-XX-plan.md` e a lista de critérios marcados.
- **vercel**: cada PR gera um preview; conferir variáveis de ambiente no projeto da Vercel e checar os logs de build quando algo falhar.

### ⑧ Aprendizado: `claude-md-management`
No fim de cada história (ou pelo menos de cada sprint), peça para revisar o `CLAUDE.md` com o que mudou: comandos novos, armadilhas encontradas, decisões tomadas. Mantém as próximas sessões alinhadas.

## 4. Prompts prontos

```text
# Começar uma história
Leia CLAUDE.md e docs/sdd/00-constitution.md. Use brainstorming para criar
docs/sdd/features/US-13.md a partir do template, da spec (§4.3 e §5) e do backlog.

# Planejar
Use writing-plans para gerar docs/sdd/plans/US-13-plan.md seguindo docs/sdd/02-plan.md §5.
Consulte o context7 para APScheduler e psycopg antes de escrever o plano.

# Executar
Crie uma worktree feat/US-13-motor-alertas e execute o plano com test-driven-development.
Não marque nenhuma tarefa como feita sem rodar os testes e mostrar a saída.

# Revisar
Rode o code-review e o silent-failure-hunter no diff. Depois rode differential-review
e sharp-edges. Liste os achados por severidade e corrija os altos.

# Fechar
Use finishing-a-development-branch. Abra o PR com links para a spec e o plano
e a lista de critérios de aceite marcados. Depois atualize o CLAUDE.md.
```
