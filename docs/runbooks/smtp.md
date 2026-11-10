# Runbook · SMTP (Postfix → MailHog)

**Serviço:** `smtp` · **Container:** `postfix` · **Painel:** `/services/smtp`

## Como o alerta é gerado
- **Vermelho**: 2 verificações EHLO falharam, fila > 200 mensagens ou taxa de entrega < 80 %.
- **Amarelo**: 1 falha, fila > 50 ou entrega < 95 %.
- Os e-mails de alerta **não** passam por este Postfix: saem por canal próprio (MailHog/Gmail).

## Diagnóstico rápido
```bash
docker compose ps postfix
docker compose logs --tail=100 postfix
docker compose exec postfix postqueue -p
docker compose exec postfix postfix status
# Interface de mensagens: http://localhost:8025
```

## Causas prováveis e ações
| Sintoma | Causa provável | Ação |
|---|---|---|
| EHLO falha | Container parado | `docker compose start postfix` |
| Fila crescendo | MailHog fora ou relay inválido | `docker compose ps mailhog`; depois `docker compose exec postfix postqueue -f` |
| Rejeições | Política do destino | Ler `docker compose logs postfix` (`status=bounced`/`reject:`) |
| Volume anormal | Envio em massa (`smtp_flood` ou abuso) | Identificar origem no log e bloquear |

## Escalonamento
Se o serviço não voltar em 15 min ou o alerta reabrir após a correção, registrar o incidente (horário, métrica, ação tomada) e seguir o playbook [`servico-fora.md`](../playbooks/servico-fora.md).
