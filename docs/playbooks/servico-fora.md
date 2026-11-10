# Playbook · Serviço fora do ar ou degradado

**Gatilho:** e-mail `[CRÍTICO] <serviço> indisponível` ou alerta Vermelho de disponibilidade/limite.

1. **Confirmar** no painel (`/services/<id>`) se é queda real: cartão Vermelho e série `up`/latência.
2. **Classificar:** processo parado (`docker compose ps`), erro de aplicação (logs) ou saturação (métricas de CPU, conexões, fila).
3. **Conter/Restaurar:** seguir o [runbook](../runbooks/) do serviço; reiniciar com `docker compose start <container>`.
4. **Verificar:** após 2 ciclos de coleta (30 s) o cartão volta a Verde e chega o e-mail `[RESOLVIDO]`.
5. **Registrar:** horário, causa, ação e tempo de indisponibilidade (o painel mostra a disponibilidade 24 h).
6. **Prevenir:** se houve causa raiz repetível, abrir tarefa de correção.
