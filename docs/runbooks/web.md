# Runbook · Web Server (Nginx + app demo)

**Serviço:** `web` · **Container:** `nginx` · **Painel:** `/services/web`

## Como o alerta é gerado
- **Vermelho**: 2 verificações HTTP seguidas falharam (`web.up`), `web.latency_p95_ms` > 2000 ms ou `web.error_5xx_rate` > 10 %.
- **Amarelo**: 1 falha de verificação, p95 > 500 ms ou 5xx > 2 %.

## Diagnóstico rápido
```bash
docker compose ps nginx
docker compose logs --tail=100 nginx
curl -i http://localhost:8080/
docker compose exec nginx nginx -t
tail -n 20 $(docker volume inspect -f '{{.Mountpoint}}' $(basename $PWD)_nginx-logs)/access.log
```

## Causas prováveis e ações
| Sintoma | Causa provável | Ação |
|---|---|---|
| Container parado | Falha ou parada manual | `docker compose start nginx` |
| 502/504 (5xx alto) | `demo-app` fora do ar | `docker compose restart demo-app` e conferir `docker compose ps` |
| Latência alta | Pico de tráfego | Ver página Segurança (DDoS); playbook [`ddos.md`](../playbooks/ddos.md) |
| `nginx -t` com erro | Configuração alterada | Playbook [`config-alterada.md`](../playbooks/config-alterada.md) |

## Escalonamento
Se o serviço não voltar em 15 min ou o alerta reabrir após a correção, registrar o incidente (horário, métrica, ação tomada) e seguir o playbook [`servico-fora.md`](../playbooks/servico-fora.md).
