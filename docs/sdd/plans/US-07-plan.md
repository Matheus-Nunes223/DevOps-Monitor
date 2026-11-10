# Plano · US-07 · Métricas DNS

- **Spec:** `docs/sdd/features/US-07.md`
- **Fonte de métricas:** `docs/sdd/02-plan.md` §4.

## Arquivos
| Ação | Caminho | Responsabilidade |
|---|---|---|
| criar | `collector/src/monitor/probes/dns.py` | consultas ativas e scraping Prometheus |
| criar | `collector/tests/unit/test_dns.py` | respostas, falhas, NXDOMAIN, QPS e resets |
| atualizar | `collector/src/monitor/main.py` | registrar a probe no ciclo |

## TDD
- [x] Escrever testes antes da implementação; a execução red prévia não foi capturada.
- [x] Implementar parser de `coredns_dns_requests_total`.
- [x] Implementar três consultas com expectativa explícita.
- [x] Calcular métricas e integrar no runner como probes separadas para não perder as consultas ativas se o scrape falhar.
- [x] Rodar suíte completa: 48 testes unitários passaram via unittest.

## Validação integrada pendente
- [ ] Confirmar os nomes lab e encaminhamento externo no CoreDNS por Compose.
- [ ] Conferir QPS com carga DNS controlada e comparação ao endpoint `/metrics`.
