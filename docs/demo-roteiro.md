# Roteiro da demonstração (≈ 10 min)

**Preparação (antes):** `docker compose up -d --build`; painel aberto e logado; MailHog em `http://localhost:8025`; `ALERT_EMAIL_TO` definido; coletor rodando há pelo menos 3 min (a detecção de tráfego precisa de histórico). Gravar um vídeo do ensaio como plano B.

| Min | O que mostrar | Comando / ação | Resultado esperado |
|---|---|---|---|
| 0–1 | Arquitetura e visão consolidada | Slide da `docs/arquitetura.md`; abrir `/` | 4 cartões Verdes, disponibilidade 24 h |
| 1–3 | Dashboards por serviço | `/services/web`, `db`, `dns`, `smtp`; trocar 1 h / 6 h / 24 h | Todas as métricas do enunciado |
| 3–4 | Tráfego normal e pico | `uv run --project loadgen devops-loadgen normal` e depois `spike` | RPS sobe; **Segurança** mostra evento DDoS com top IPs; e-mail no MailHog |
| 4–6 | Serviço fora do ar | `devops-loadgen stop_service --service nginx --duration 60 --confirm-fault` | Amarelo → Vermelho em ~30 s; e-mail `[CRÍTICO] web indisponível`; volta a Verde + `[RESOLVIDO] web` |
| 6–7 | Brute-force | `devops-loadgen bruteforce --attempts 20` | Evento com IP e contagem; alerta Vermelho |
| 7–8 | Mudança de configuração | `devops-loadgen edit_config --duration 45 --confirm-fault` | Alerta Amarelo com diff; clicar em **Aceitar como base** |
| 8–9 | Vulnerabilidades | Página **Segurança**, tabela de CVEs | CVEs por serviço com CVSS |
| 9–10 | Segurança e testes | Mostrar RLS (sem login → `/login`), relatório do Playwright | Redirecionamento e evidências |

Observações: `edit_config` precisa durar mais que um ciclo (15 s) para ser detectado; `stop_service` precisa durar mais de 30 s para chegar ao Vermelho.
