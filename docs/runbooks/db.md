# Runbook · Banco de dados (PostgreSQL 16)

**Serviço:** `db` · **Container:** `postgres` · **Painel:** `/services/db`

## Como o alerta é gerado
- **Vermelho**: 2 verificações `SELECT 1` falharam, conexões > 90 % do máximo, queries lentas > 20/min ou CPU > 95 %.
- **Amarelo**: 1 falha, conexões > 70 %, queries lentas > 5/min ou CPU > 75 %.

## Diagnóstico rápido
```bash
docker compose ps postgres
docker compose logs --tail=100 postgres
docker compose exec postgres pg_isready -U devops_lab -d devops_monitor
docker compose exec postgres psql -U devops_lab -d devops_monitor -c "select state, count(*) from pg_stat_activity group by 1;"
docker compose exec postgres psql -U devops_lab -d devops_monitor -c "select query, calls, mean_exec_time from pg_stat_statements order by mean_exec_time desc limit 5;"
```

## Causas prováveis e ações
| Sintoma | Causa provável | Ação |
|---|---|---|
| Sem conexão | Container parado | `docker compose start postgres` |
| Conexões altas | Aplicação sem pool ou conexões presas | Encerrar sessões ociosas: `select pg_terminate_backend(pid) from pg_stat_activity where state='idle' and pid<>pg_backend_pid();` |
| Queries lentas | Falta de índice / consulta pesada | Analisar com `EXPLAIN ANALYZE` a query do topo do `pg_stat_statements` |
| CPU alta | Carga de consultas | Identificar a query e limitar a origem |
| Crescimento GB/dia alto | Volume de dados anormal | Verificar tabelas maiores com `pg_total_relation_size` |

## Escalonamento
Se o serviço não voltar em 15 min ou o alerta reabrir após a correção, registrar o incidente (horário, métrica, ação tomada) e seguir o playbook [`servico-fora.md`](../playbooks/servico-fora.md).
