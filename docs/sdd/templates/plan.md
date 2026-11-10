# Plano · US-XX · <título>

> Gerado com a skill writing-plans a partir de `features/US-XX.md`. Cada tarefa leva de 2 a 5 minutos e começa por um teste.

- **Spec:** `docs/sdd/features/US-XX.md`
- **Branch:** `feat/US-XX-<slug>`
- **Docs consultadas (context7):** <biblioteca@versão, ...>

## Arquivos
| Ação | Caminho | Responsabilidade |
|---|---|---|
| criar | `collector/src/monitor/...` | ... |
| testar | `collector/tests/unit/test_...py` | ... |

## Tarefas
### 1. <nome>
- [ ] Escrever o teste `test_...` que falha porque ...
- [ ] Rodar: `uv run pytest tests/unit/test_...py -k ...` → **falha esperada**
- [ ] Implementar o mínimo em `...`
- [ ] Rodar de novo → **passa**
- [ ] Commit: `feat(US-XX): ...`

### 2. <nome>
...

## Verificação final
- [ ] `uv run ruff check && uv run pyright && uv run pytest`
- [ ] `pnpm lint && pnpm tsc --noEmit && pnpm vitest run && pnpm playwright test` (se tocou no painel)
- [ ] Critérios de aceite da spec demonstrados (cole a evidência)

## Revisão
- [ ] code-review / pr-review-toolkit
- [ ] differential-review + (insecure-defaults | sharp-edges | owasp-security, conforme o que mudou)
