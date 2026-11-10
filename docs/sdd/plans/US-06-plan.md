# Plano · US-06 · Métricas de Banco

- **Spec:** `docs/sdd/features/US-06.md`
- **Métricas e fontes:** `docs/sdd/02-plan.md` §4.
- **Arquitetura:** probe dedicado PostgreSQL; cálculos puros testados isoladamente.

## Arquivos
| Ação | Caminho | Responsabilidade |
|---|---|---|
| criar | `collector/src/monitor/probes/database.py` | snapshots PostgreSQL e métricas derivadas |
| criar | `collector/src/monitor/probes/docker_metrics.py` | CPU, memória e I/O do container Postgres |
| criar | `infra/docker_stats_proxy/` | proxy Docker com allowlist exata do endpoint stats |
| criar | `collector/src/monitor/dbcalc.py` | deltas de contador e regressão de crescimento |
| criar | `collector/tests/unit/test_dbcalc.py` | testes dos cálculos sem banco |
| criar | `collector/tests/unit/test_database.py` | teste da query por conexão fake |
| atualizar | `collector/src/monitor/main.py` | registrar probe de métricas do DB |
| atualizar | `collector/src/monitor/config.py` | manter DSN lab validado pelo settings existente |

## Execução TDD
- [x] Criar casos de teste antes dos módulos.
- [x] Confirmar falha esperada (`ModuleNotFoundError` antes de criar os módulos).
- [x] Implementar funções de deltas, tratamento de reset e regressão.
- [x] Implementar consulta agregada sem texto SQL de usuário.
- [x] Registrar probe com baseline independente no runner.
- [x] Adicionar probe Docker stats com cálculo de CPU e I/O.
- [x] Rodar suíte unitária e allowlist proxy (integração real pendente).

## Pendências de integração
- [ ] Validar reset/reinício de contadores contra Postgres real.
- [ ] Validar permissões e nomes de colunas no PostgreSQL 16 com extensões habilitadas (Docker indisponível).
- [ ] Validar cálculo do SDK contra Docker Engine real e volume/socket no Compose.
- [ ] Executar `docker compose config` e `docker compose up` no host com Docker.
- [ ] Verificar o ciclo inteiro no Compose.
