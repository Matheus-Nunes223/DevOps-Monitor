# Plano · US-11 · Visão consolidada

- **Spec:** `docs/sdd/features/US-11.md`
- **Branch:** `feat/US-11-visao-consolidada` (workspace sem repositório Git)
- **Docs consultadas:** Supabase SSR/Realtime e tipagem TypeScript do Supabase; componentes React Server/Client do Next.js 15.

## Arquivos
| Ação | Caminho | Responsabilidade |
|---|---|---|
| criar | `web/lib/supabase/types.ts` | contrato TypeScript alinhado às migrations atuais |
| criar | `web/lib/overview.ts` | consulta inicial e agregação pura dos dados reais |
| criar | `web/lib/overview.test.ts` | estados vazios, disponibilidade e ordenação de alertas |
| criar | `web/components/status-card.tsx`, `alert-list.tsx` | UI reutilizável e estados desconhecidos |
| criar | `web/components/overview-live.tsx` | subscriptions Realtime e atualização otimista/consistente |
| atualizar | `web/app/(dash)/page.tsx`, testes e documentação | integrar a visão consolidada |

## Tarefas e validação
- [x] Testes Vitest para reducers e componentes (sem mocks apresentados como medições).
- [x] Consultar services, últimas checagens e disponibilidade de protocolo 24 h com sessão SSR.
- [x] Consultar alertas abertos e renderizar somente dados retornados pelo banco.
- [x] Assinar as três tabelas autorizadas e remover o canal no unmount.
- [x] Lint, TypeScript, Vitest, build e E2E sem conta real: aprovados (25 testes unitários; 6 E2E).
- [ ] Testar alteração real do banco e atraso ≤5 s com Supabase configurado (T-112).

## Limitações de ambiente
- A integração de ponta a ponta depende de URL/chave/usuário Supabase e migrations aplicadas; nenhuma credencial Supabase está configurada neste workspace.
- Os dados reais de disponibilidade e alertas serão exibidos quando o coletor estiver gravando no banco; a interface não preenche lacunas com valores demonstrativos.
