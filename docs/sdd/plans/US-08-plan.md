# Plano · US-08 · Métricas SMTP

- **Spec:** `docs/sdd/features/US-08.md`
- **Fontes:** `docs/sdd/02-plan.md` §4; manuais oficiais Postfix `postqueue(1)` e MailHog API v2.

## Arquivos
| Ação | Caminho | Responsabilidade |
|---|---|---|
| criar | `collector/src/monitor/probes/smtp.py` | parse de logs, fila, envio e busca no MailHog |
| criar | `collector/tests/unit/test_smtp.py` | fixtures de logs e JSON Lines, adapters SMTP/HTTP falsos |
| atualizar | `infra/docker_stats_proxy/server.py` | acesso restrito a logs e comando fixo da fila Postfix |
| atualizar | `collector/src/monitor/main.py` | registrar probes SMTP independentes |
| atualizar | `collector/src/monitor/config.py` | parâmetros não secretos do MailHog e destinos da sonda |
| atualizar | `docker-compose.yml` | identidade fixa do container Postfix e dependências |

## TDD
- [x] Escrever os testes e registrar a falha antes da implementação (`ModuleNotFoundError`).
- [x] Implementar parsers puros de log e `postqueue -j`.
- [x] Implementar probes isoladas de logs/fila e mensagem sonda.
- [x] Integrar fila e logs através do proxy com allowlist.
- [x] Integrar no ciclo; os 57 testes executáveis passaram via unittest.

## Validação integrada
- [ ] `test_config.py` e settings: indisponíveis até instalar Pydantic Settings no ambiente.
- [ ] Subir Postfix/MailHog e verificar envio, entrega, busca, fila vazia e mensagens adiadas.
- [ ] Confirmar que o proxy bloqueia rotas/execuções fora da allowlist.
