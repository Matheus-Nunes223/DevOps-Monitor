# Plano · US-10 · Login e layout

- **Spec:** `docs/sdd/features/US-10.md`
- **Branch:** `feat/US-10-login-layout` (o workspace não possui repositório Git configurado)
- **Docs consultadas:** Next.js 15 Middleware; Supabase SSR (createServerClient/createBrowserClient/getClaims); Tailwind CSS para Next.js.

## Arquivos
| Ação | Caminho | Responsabilidade |
|---|---|---|
| criar | `web/package.json`, `web/pnpm-lock.yaml`, config Next/TS/Tailwind | aplicação Next.js App Router reprodutível |
| criar | `web/app/login/*`, `web/app/(dash)/page.tsx` | autenticação e estado inicial do painel |
| criar | `web/app/(dash)/layout.tsx`, `web/app/(dash)/page.tsx` | shell autenticado e estado sem dados |
| criar | `web/components/*` | navegação responsiva, logo e formulário de login |
| criar | `web/lib/supabase/*`, `web/middleware.ts` | clientes SSR e renovação/proteção de sessão |
| atualizar | `web/README.md`, `.env.example`, `docs/instalacao.md` | setup, variáveis e execução |
| atualizar | `docs/sdd/03-tasks.md` | estado das tarefas verificado |

## Execução e verificação
- [x] Escrever a spec e definir a fronteira de segurança antes do código.
- [x] Criar aplicação e configuração estrita TypeScript/Tailwind/shadcn-style.
- [x] Escrever verificações automatizadas de proteção de rotas e validação do formulário.
- [x] Instalar dependências e executar lint, typecheck, Vitest e build.
- [ ] Exercitar login real e sessão em projeto Supabase configurado (aguarda URL, chave pública e conta de teste).
- [x] Verificar tela de login em 360 px, 390×844 e 1440×900 no navegador; shell móvel conferido com teste de interação.
- [ ] Criar/validar deployment preview na Vercel após credenciais externas.

## Riscos / bloqueios conhecidos
- Login real depende de URL/chave pública e usuário de demonstração no Supabase.
- Deploy preview depende de projeto e credenciais Vercel.
