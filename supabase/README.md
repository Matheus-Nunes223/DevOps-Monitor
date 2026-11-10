# Supabase

O schema inicial está versionado em `migrations/20261109000000_init.sql`; dados
iniciais em `seed.sql`; testes pgTAP em `tests/database/`.

Em uma máquina com Docker e Supabase CLI instalados, execute na raiz:

```bash
supabase start
supabase db reset
supabase test db
```

O reset recria o banco local e aplica migrações e seed. O teste usa pgTAP e
verifica RLS para anon/authenticated. O projeto remoto Supabase e os advisors
precisam ser configurados/executados separadamente; nenhum projeto ou segredo
remoto foi criado neste workspace.
