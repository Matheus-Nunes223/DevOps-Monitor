# Plano · US-03 · Esqueleto do coletor

- **Spec:** `docs/sdd/features/US-03.md`
- **Branch:** `feat/US-03-esqueleto-coletor`
- **Docs consultadas:** [Pydantic Settings](https://pydantic.dev/docs/validation/latest/concepts/pydantic_settings/), [APScheduler 3.x](https://apscheduler.readthedocs.io/en/3.x/userguide.html), [Psycopg 3 usage](https://www.psycopg.org/psycopg3/docs/basic/usage.html). Context7 não está disponível nesta sessão.

## Arquivos
| Ação | Caminho | Responsabilidade |
|---|---|---|
| criar | `collector/pyproject.toml` | dependências e configurações de lint/tipos/testes |
| criar | `collector/config.yaml` | defaults não secretos |
| criar | `collector/src/monitor/config.py` | settings validados, YAML/env |
| criar | `collector/src/monitor/model.py` | contratos imutáveis de métrica, status e probe |
| criar | `collector/src/monitor/store.py` | insert transacional em lote com psycopg |
| criar | `collector/src/monitor/main.py` | logging JSON, execução concorrente e scheduler |
| testar | `collector/tests/unit/test_*.py` | TDD para config, store e isolamento de probes |
| criar | `collector/Dockerfile` | imagem Python 3.12 |

## Tarefas
### 1. Contratos e configuração (T-030, T-031)
- [x] Escrever testes para precedence YAML/env e validação de intervalo.
- [x] Executar falha esperada antes da implementação (módulos `monitor.*` ainda não existiam).
- [x] Criar pyproject, config, modelos e settings.

### 2. Persistência (T-031)
- [x] Testar insert em lote e preservação de `None` como NULL.
- [x] Implementar store com parâmetros e transação Psycopg.

### 3. Ciclo e agendamento (T-032)
- [x] Testar exceção e timeout de probe isolados sem parar colegas.
- [x] Implementar executor paralelo, logs JSON e APScheduler sem sobreposição.
- [x] Tratar falha de persistência com log e permitir o próximo ciclo.

## Verificação final
- [ ] `uv run ruff check && uv run pyright && uv run pytest` (não executado: uv/pytest/ruff/pyright ausentes; Python local é 3.14, projeto exige 3.12).
- [ ] `uv lock` e `uv sync --locked` (não executado: uv ausente; `uv.lock` ainda não existe).
- [ ] Testar contra Postgres/Supabase local (depende da US-02 aplicada).

Testes de model/runner/scheduler/store executados com unittest: 8 passaram. Testes de config estão escritos, mas não carregam sem `pydantic`/`pydantic-settings`. `compileall` e parse de TOML passaram. Uma tentativa de instalar as dependências em `/tmp` falhou por DNS indisponível; nada foi instalado no ambiente do sistema.

## Revisão
- [ ] Revisar logs para confirmar que DSNs/segredos nunca aparecem.
- [ ] Rever timeouts, cancelamento e comportamento do executor no shutdown.
