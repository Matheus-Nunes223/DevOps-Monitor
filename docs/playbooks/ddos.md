# Playbook · Pico de tráfego (possível DDoS)

**Gatilho:** alerta Vermelho `ddos` (z-score do RPS > 3 ou RPS > 5× a média de 15 min). O e-mail e a página **Segurança** trazem os 5 IPs que mais requisitaram.

1. **Validar:** o pico é tráfego legítimo (campanha, teste de carga) ou anômalo? Conferir os IPs e o URI mais acessado nos logs.
2. **Medir impacto:** latência p95 e taxa 5xx em `/services/web`.
3. **Conter:** bloquear os IPs ofensores no Nginx (`deny <ip>;`) ou limitar com `limit_req`; recarregar com `nginx -s reload`. *Essa mudança dispara o alerta de configuração — aceite a nova base depois.*
4. **Escalar:** se o tráfego vier de muitos IPs, acionar o provedor/CDN.
5. **Encerrar:** o alerta se resolve sozinho após 4 ciclos normais; registrar o incidente.
