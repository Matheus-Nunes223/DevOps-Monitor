# 03 · Tarefas

> Lista de execução derivada do plano. Cada tarefa cabe em uma sessão curta do Claude Code.
> `[P]` = pode rodar em paralelo com a anterior. A etiqueta 🔧 diz qual plugin, skill ou MCP usar (detalhes em `04-workflow-plugins.md`).
> Antes de começar uma história, gere a spec e o plano detalhados dela (`features/US-XX.md`, `plans/US-XX-plan.md`).

Legenda 🔧: **BS** brainstorming · **WP** writing-plans · **TDD** test-driven-development · **SDD** subagent-driven-development · **C7** context7 · **SB** MCP do Supabase · **VC** Vercel · **PW** Playwright · **FD** frontend-design · **REV** revisão (code-review + pr-review-toolkit) · **SEC** segurança (Trail of Bits + owasp-security) · **VER** verification-before-completion

---

## Sprint 0 · Preparação (antes da Sprint 1, ~1 h)

- [ ] **T-000** Renovar o token do GitHub para o MCP voltar a conectar (ver `04-workflow-plugins.md` §1).
- [ ] **T-001** Remover a cópia duplicada do superpowers e desativar `dart-flutter` e `jdtls-lsp` neste projeto.
- [ ] **T-002** Criar o repositório, copiar este kit e o `CLAUDE.md`, primeiro commit.
- [ ] **T-003** Criar o projeto no Supabase e o projeto na Vercel (vazio), guardar URLs e chaves num `.env` local.

## Sprint 1 · Base e coleta (30 pts)

### US-01 Ambiente monitorado (5)
- [ ] **T-010** Spec + plano da história. 🔧 BS, WP
- [ ] **T-011** `docker-compose.yml` com rede `lab`, healthchecks e volumes de log compartilhados. 🔧 C7 (Docker Compose)
- [ ] **T-012** [P] Nginx com `log_format` JSON (`$remote_addr`, `$status`, `$request_time`, `$request_uri`, `$request_method`) e `stub_status` interno.
- [ ] **T-013** [P] App demo com `GET /` e `POST /login` (registra o usuário tentado em header de resposta para o log).
- [ ] **T-014** [P] PostgreSQL com `shared_preload_libraries=pg_stat_statements` e `track_io_timing=on`.
- [ ] **T-015** [P] CoreDNS com zona `lab.local` e plugin `prometheus :9153`.
- [ ] **T-016** [P] Postfix com `relayhost=[mailhog]:1025` + MailHog.
- [ ] **T-017** Verificar: `docker compose up` → todos saudáveis em até 60 s. 🔧 VER

### US-02 Banco no Supabase (3)
- [x] **T-020** Migração `init` conforme `02-plan.md` §3. 🔧 SB (aplicar migração), C7 (Supabase)
- [x] **T-021** `seed.sql` com serviços e regras da spec §5.
- [x] **T-022** Função `accept_config_baseline` e função `metric_series`.
- [ ] **T-023** Testes de RLS (anon sem sessão = 0 linhas; authenticated não insere). 🔧 SB, TDD
- [ ] **T-024** Rodar os advisors de segurança e desempenho do Supabase; corrigir avisos. 🔧 SB, SEC

### US-03 Esqueleto do coletor (3)
- [ ] **T-030** `uv init`, ruff, pyright `standard`, pytest; Dockerfile.
- [ ] **T-031** `config.py`, `model.py`, `store.py` (insert em lote com psycopg). 🔧 TDD, C7 (psycopg)
- [ ] **T-032** `main.py` com APScheduler e execução paralela com timeout por sonda; sonda que lança exceção é logada e não derruba o ciclo. 🔧 TDD
- [ ] **T-033** Revisão focada em erros silenciosos. 🔧 REV (silent-failure-hunter)

### US-04 Disponibilidade (3)
- [x] **T-040** `probes/availability.py`: ICMP + checagem de protocolo dos 4 serviços. 🔧 TDD, C7 (icmplib, dnspython) (unit tests passam; integração real aguarda Docker)
- [ ] **T-041** Cálculo de disponibilidade 24 h (função SQL ou view). 🔧 SB (migration e pgTAP escritos; sem validação em banco local)

### US-05 Métricas Web (5)
- [x] **T-050** `logtail.py` com offset e rotação de arquivo (testes unitários passaram).
- [x] **T-051** `calc.py`: RPS, p50/p95, taxas 4xx/5xx a partir de fixtures de log (testes unitários passaram).
- [x] **T-052** `probes/web.py` + leitura do `stub_status` (testes com adapters falsos passaram; integração Nginx real pendente).

### US-06 Métricas Banco (8)
- [x] **T-060** Consultas de `pg_stat_database`, `pg_stat_activity`, `pg_stat_statements`, tamanho (implementação e mocks unitários; validação PostgreSQL real pendente). 🔧 TDD
- [x] **T-061** [P] CPU, memória e I/O pela Docker API via proxy allowlist (testes unitários; Docker real pendente). 🔧 docker SDK
- [x] **T-062** Crescimento GB/dia por regressão linear (função pura e testes unitários).
- [x] **T-063** Revisão do acesso ao socket: proxy isolado, só GET stats para container fixo; allowlist testada. Integração real pendente. 🔧 SEC

### US-07 Métricas DNS (3)
- [x] **T-070** `probes/dns.py`: tempo de resolução, falhas, NXDOMAIN esperado e QPS do `/metrics` (testes unitários; CoreDNS real pendente). 🔧 TDD

**Fim da Sprint 1:** PR da sprint revisado. 🔧 REV, SEC (differential-review no diff da sprint). Atualizar `CLAUDE.md` com o que foi aprendido. 🔧 claude-md-management

## Sprint 2 · Painel e alertas (32 pts)

### US-08 Métricas SMTP (5)
- [x] **T-080** Parser do log do Postfix e de `postqueue -j` com fixtures (testes unitários; execução Postfix real pendente). 🔧 TDD
- [x] **T-081** E-mail sonda e medição de latência via API do MailHog (adapters falsos; integração real pendente). 🔧 TDD

### US-09 Gerador de carga e falhas (3)
- [x] **T-090** `loadgen/scenarios/*` (normal, spike, bruteforce, stop_service, edit_config, smtp_flood) com CLI única; testes com fakes passaram, ensaio real pendente. 🔧 TDD

### US-10 Login e layout (3)
- [x] **T-100** App Next.js 15 App Router, TypeScript strict, Tailwind 4 e primitivas shadcn/ui; lint, tipos e build passaram.
- [x] **T-101** Clientes Supabase SSR, `middleware.ts` e login por e-mail/senha; 12 testes unitários e 6 E2E passaram sem conta Supabase real.
- [x] **T-102** Shell responsivo base e tela de entrada; checagem Playwright em 1440×900, 390×844 e 360 px; integração real Supabase pendente.
- [ ] **T-103** Projeto na Vercel com variáveis de ambiente; preview a cada PR. 🔧 VC

### US-11 Visão consolidada (5)
- [x] **T-110** `status-card` e `alert-list` com testes Vitest; estados sem dados e falha de consulta cobertos.
- [x] **T-111** Assinatura Realtime de `alerts`, `service_status`, `services`; reducers e ciclo de vida do canal cobertos por testes.
- [ ] **T-112** Teste E2E: alterar estado no banco → cartão muda em até 5 s. 🔧 PW (aguarda projeto Supabase configurado e migrations aplicadas)

### US-12 Dashboards por serviço (8)
- [x] **T-120** `metric-chart` + `range-filter` usando `metric_series`. 🔧 FD, C7 (Recharts)
- [x] **T-121** [P] Página Web. **T-122** [P] Banco. **T-123** [P] DNS. **T-124** [P] SMTP. 🔧 SDD (um subagente por página)
- [x] **T-125** Histórico de alertas por serviço.
- [ ] **T-126** Simplificar componentes repetidos entre as 4 páginas. 🔧 code-simplifier

### US-13 Motor de alertas (5)
- [x] **T-130** `alerts/engine.py` puro com histerese de 2 ciclos; testes de tabela com sequências de valores. 🔧 TDD
- [x] **T-131** Integração com `store.py`, atualização de `services.current_level` e reconstrução no start.

### US-14 E-mail de alertas (3)
- [x] **T-140** `notifier.py` + templates; intervalos de reenvio. 🔧 TDD
- [ ] **T-141** Teste de integração com MailHog usando o cenário `stop_service`. 🔧 VER

**Fim da Sprint 2:** demo interna com o gerador de falhas. 🔧 PW (gravar vídeo e capturas). PR revisado. 🔧 REV, SEC (owasp-security no painel).

## Sprint 3 · Segurança e entrega (25 pts)

### US-15 Anomalias de tráfego (3)
- [x] **T-150** `security/traffic.py` com z-score em janela móvel; testes com séries sintéticas. 🔧 TDD

### US-16 Brute-force (3)
- [x] **T-160** `security/bruteforce.py` com janelas por IP e por conta. 🔧 TDD

### US-17 Mudança de configuração (2)
- [x] **T-170** `security/config_watch.py` + botão "Aceitar como base" no painel. 🔧 TDD

### US-18 CVEs (3)
- [x] **T-180** Detecção de versão de cada serviço. 🔧 TDD
- [x] **T-181** Cliente NVD com cache e limite de taxa; página de vulnerabilidades. 🔧 C7, FD

### US-19 Segurança da plataforma (2)
- [x] **T-190** Cabeçalhos de segurança no `next.config.ts`. 🔧 SEC (owasp-security)
- [ ] **T-191** Varredura completa: static-analysis (Semgrep) em `collector/` e `web/`, insecure-defaults em `docker-compose.yml` e configs, advisors do Supabase. 🔧 SEC, SB
- [ ] **T-192** Para cada achado corrigido, procurar o mesmo padrão no resto do código. 🔧 SEC (variant-analysis)

### US-20 Testes de navegação (5)
- [x] **T-200** Suíte Playwright (mobile + desktop) cobrindo todas as telas e o alerta ao vivo. 🔧 PW, TDD
- [ ] **T-201** Relatório HTML com capturas como evidência para o relatório ABNT.

### US-21 Relatório ABNT (5)
- [x] **T-210** Runbooks por serviço e playbooks de incidente em `docs/`.
- [ ] **T-211** Guia de instalação testado do zero numa máquina limpa. 🔧 VER
- [ ] **T-212** Montar o PDF ABNT (arquitetura, instalação, runbooks, playbooks, evidências).

### US-22 Roteiro da demo (2)
- [ ] **T-220** Roteiro de 10 min, ensaio e vídeo de plano B. 🔧 PW (gravação)
