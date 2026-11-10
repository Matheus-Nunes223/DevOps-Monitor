# Estrutura do relatório (PDF, padrão ABNT)

Mapeia cada item pedido no enunciado ao conteúdo do repositório.

1. **Introdução e objetivo** — problema, escopo, serviços monitorados.
2. **Fundamentação** — disponibilidade, latência, RPS, QPS, histerese de alertas, DDoS, brute-force.
3. **Arquitetura** — `docs/arquitetura.md` (diagrama, decisões, fluxo do ciclo).
4. **Implementação** — front-end responsivo; ingestão e armazenamento; tabela de métricas por serviço; regras de alerta (limites da spec §5).
5. **Alertas e notificações** — três níveis, e-mails, intervalos de reenvio, exemplos capturados no MailHog.
6. **Segurança e monitoramentos extras** — DDoS, brute-force, mudança de configuração, CVEs; segurança da própria plataforma (RLS, cabeçalhos, chaves).
7. **Guia de instalação** — `docs/instalacao.md`.
8. **Runbooks e playbooks** — `docs/runbooks/*` e `docs/playbooks/*`.
9. **Testes de navegação e uso** — `docs/testes.md` + evidências.
10. **Conclusão e trabalhos futuros**; **Referências** (ABNT).
