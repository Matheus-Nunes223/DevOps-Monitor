# Runbook · DNS (CoreDNS)

**Serviço:** `dns` · **Container:** `coredns` · **Painel:** `/services/dns`

## Como o alerta é gerado
- **Vermelho**: 2 consultas seguidas falharam, `dns.resolve_ms` > 500 ms ou falhas > 20 %.
- **Amarelo**: 1 falha, resolução > 100 ms ou falhas > 5 %.

## Diagnóstico rápido
```bash
docker compose ps coredns
docker compose logs --tail=100 coredns
dig @127.0.0.1 -p 1053 web.lab.local
dig @127.0.0.1 -p 1053 example.com
docker compose exec coredns /bin/busybox wget -qO- http://127.0.0.1:9153/metrics | head
```

## Causas prováveis e ações
| Sintoma | Causa provável | Ação |
|---|---|---|
| Sem resposta | Container parado | `docker compose start coredns` |
| `web.lab.local` falha | Zona alterada | Conferir `infra/coredns/lab.local.db` e o `Corefile` |
| Só nomes externos lentos | Forwarders (1.1.1.1/8.8.8.8) indisponíveis | Testar a rede do host; a zona local continua funcionando |

## Escalonamento
Se o serviço não voltar em 15 min ou o alerta reabrir após a correção, registrar o incidente (horário, métrica, ação tomada) e seguir o playbook [`servico-fora.md`](../playbooks/servico-fora.md).
