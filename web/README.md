# Painel DevOps Monitor

Aplicação Next.js 15 App Router com TypeScript `strict`, Tailwind CSS 4, componentes no padrão shadcn/ui e autenticação SSR do Supabase. A interface conserva a direção visual do frontend de referência (`frontend/`): tema escuro, acentos verde-menta, hierarquia compacta e tipografia legível. Nenhuma métrica demonstrativa é tratada como dado medido.

## Requisitos

- Node.js 22 ou superior.
- pnpm 11 ou superior.
- Um projeto Supabase com Auth habilitado e um usuário de operador criado.

## Configuração local

Copie `web/.env.example` para `web/.env.local` e preencha `NEXT_PUBLIC_SUPABASE_URL` e `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY` (ou a chave `NEXT_PUBLIC_SUPABASE_ANON_KEY` legada). O app valida que a chave tem formato publishable/anon e interrompe o build se detectar uma service-role key.

```bash
cd web
cp .env.example .env.local
pnpm install --frozen-lockfile
pnpm dev
```

Abra `http://localhost:3000`. Sem configuração Supabase, a rota `/` continua protegida e redireciona a `/login`; o formulário explica como configurar o acesso sem simular uma sessão. Configure também a URL local no Supabase Auth: `http://localhost:3000/**`.

## Comandos de qualidade

```bash
pnpm lint
pnpm typecheck
pnpm test
pnpm build
pnpm exec playwright install chromium --only-shell
pnpm test:e2e
```

Os testes unitários não precisam de projeto Supabase. O E2E roda sem credenciais e verifica redirecionamento, headers e viewport. O teste de login contra Auth real depende de usuário/URL configurados; nenhum segredo deve ser salvo nos testes ou no repositório.

## Estrutura

- `app/login/`: tela e formulário de autenticação.
- `app/(dash)/`: layout e páginas acessíveis apenas com sessão.
- `components/ui/`: primitivas compatíveis com a convenção shadcn/ui.
- `lib/supabase/`: configuração pública e clientes de browser/servidor.
- `middleware.ts`: renovação de sessão via `getClaims` e redirecionamento de visitantes.

A visão geral consulta serviços, última checagem de protocolo, disponibilidade medida em 24 h e alertas abertos no Supabase. As tabelas `services`, `service_status` e `alerts` atualizam via Realtime; sem medições, o painel mostra “Sem dados”. A US-12 ainda precisa entregar gráficos de métricas e páginas detalhadas por serviço. A validação com alteração real no banco (T-112) depende de configurar o projeto Supabase e aplicar as migrations.
