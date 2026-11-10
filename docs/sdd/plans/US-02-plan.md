# Plano · US-02 · Banco de dados no Supabase

- **Spec:** `docs/sdd/features/US-02.md`
- **Branch:** `feat/US-02-banco-supabase`
- **Docs consultadas:** [Supabase RLS](https://supabase.com/docs/guides/database/postgres/row-level-security), [Database Functions](https://supabase.com/docs/guides/database/functions), [Testing Your Database](https://supabase.com/docs/guides/database/testing), [pgTAP](https://supabase.com/docs/guides/database/extensions/pgtap). Context7 não está disponível nesta sessão.

## Arquivos
| Ação | Caminho | Responsabilidade |
|---|---|---|
| criar | `supabase/migrations/20261109000000_init.sql` | tabelas, RLS, RPCs, índices, Realtime e retenção |
| criar | `supabase/seed.sql` | quatro serviços e regras iniciais |
| testar | `supabase/tests/database/rls_test.sql` | pgTAP para RLS, permissões e seed |
| atualizar | `supabase/config.toml` | habilitar testes e seed local |

## Tarefas
### 1. Especificação e testes (T-020 a T-023)
- [x] Definir contratos, limites e exceção semântica de `*.up` nesta spec.
- [x] Escrever testes pgTAP antes da migração.
- [ ] Aplicar migração e demonstrar testes com Supabase local/CLI.

### 2. Migração e seed (T-020 a T-022)
- [x] Criar schema conforme `docs/sdd/02-plan.md` §3 e RF-06.
- [x] Habilitar RLS e conceder somente leitura aos papéis anon/authenticated, sem política de leitura anon; escrita via service_role.
- [x] Criar funções RPC com privilégios mínimos, limites de entrada e `search_path` fixo nas funções `SECURITY DEFINER`.
- [x] Semear serviços e limites da spec de produto.

## Verificação final
- [ ] `supabase start && supabase db reset && supabase test db` (não executado: Supabase CLI e Docker ausentes).
- [ ] Revisar advisor Supabase de segurança/desempenho (T-024; exige projeto/CLI conectado).
- [ ] Confirmar anon sem sessão lê zero linhas e authenticated não insere.

## Revisão
- [ ] Verificar privilégios efetivos, `SECURITY DEFINER`, índices e retenção em instância Supabase.
