# 02 · Plano técnico

> **Como** a spec (`01-spec.md`) será construída. Respeita a constituição (`00-constitution.md`).
> Antes de implementar qualquer parte, confirme a API atual da biblioteca pelo **context7**: as versões mudam.

## 1. Arquitetura

```mermaid
flowchart LR
  subgraph Docker["Ambiente local (Docker Compose)"]
    NGX["Nginx + app demo<br/>/login, stub_status<br/>access.log JSON"]
    PG["PostgreSQL 16<br/>pg_stat_statements"]
    DNS["CoreDNS<br/>zona lab.local<br/>:9153 métricas"]
    PF["Postfix"] --> MH["MailHog<br/>:8025 UI/API"]
    COL["Coletor Python<br/>sondas · alertas · segurança"]
    GEN["Gerador de carga<br/>e falhas"]
  end
  COL -- ping + HTTP + logs --> NGX
  COL -- SQL --> PG
  COL -- DNS query + /metrics --> DNS
  COL -- EHLO + postqueue + log --> PF
  COL -- Docker API ro --> Docker
  GEN -. tráfego/falhas .-> NGX
  COL -- "INSERT (service role)" --> SB[("Supabase<br/>Postgres · Auth · Realtime")]
  COL -- e-mail de alerta --> SMTPOUT["SMTP de alertas<br/>(MailHog ou Gmail)"]
  WEB["Painel Next.js<br/>(Vercel)"] -- "SELECT + Realtime (anon key + sessão)" --> SB
  NVD["API NVD (CVEs)"] <-- 1x/dia --- COL
```

**Por que o coletor não roda na Vercel:** funções serverless não ficam rodando, não fazem ping ICMP e não alcançam a rede privada do Docker. O coletor roda ao lado dos serviços e só fala para fora com o Supabase, o SMTP de alertas e a API do NVD.

## 2. Estrutura do repositório

```
monitor-devops/
├── CLAUDE.md
├── docker-compose.yml
├── .env.example
├── infra/                      # US-01
│   ├── nginx/{nginx.conf, Dockerfile}      # log_format JSON com $request_time
│   ├── demo-app/               # app mínima com GET / e POST /login (401 em senha errada)
│   ├── postgres/{postgresql.conf, init.sql}
│   ├── coredns/{Corefile, lab.local.db}
│   └── postfix/main.cf         # relayhost = mailhog:1025
├── collector/                  # US-03..US-09, US-13..US-18
│   ├── pyproject.toml  uv.lock  config.yaml  Dockerfile
│   ├── src/monitor/
│   │   ├── main.py             # APScheduler, um job por ciclo
│   │   ├── config.py           # carrega YAML + env (pydantic-settings)
│   │   ├── store.py            # grava em lote (psycopg) no Supabase
│   │   ├── model.py            # dataclasses Metric, Status, Alert, SecurityEvent
│   │   ├── calc.py             # funções puras: percentil, taxa, z-score, GB/dia
│   │   ├── logtail.py          # lê logs incrementalmente (offset + rotação)
│   │   ├── probes/{availability,web,db,dns,smtp,containers}.py
│   │   ├── alerts/{engine,notifier,templates}.py
│   │   └── security/{traffic,bruteforce,config_watch,cve}.py
│   └── tests/{unit,integration}/
├── loadgen/                    # US-09: scripts de cenário (Python + httpx)
│   └── scenarios/{normal,spike,bruteforce,stop_service,edit_config,smtp_flood}.py
├── supabase/                   # US-02
│   ├── config.toml
│   ├── migrations/
│   └── seed.sql                # services + alert_rules iniciais
├── web/                        # US-10..US-12, US-18, US-19
│   ├── app/
│   │   ├── login/page.tsx
│   │   ├── (dash)/layout.tsx           # sidebar + header, exige sessão
│   │   ├── (dash)/page.tsx             # visão consolidada
│   │   ├── (dash)/services/[id]/page.tsx
│   │   └── (dash)/security/page.tsx
│   ├── components/{status-card,metric-chart,alert-list,range-filter}.tsx
│   ├── lib/supabase/{client,server,types}.ts   # types.ts gerado
│   ├── middleware.ts           # renova sessão, protege rotas
│   ├── next.config.ts          # cabeçalhos de segurança
│   └── e2e/*.spec.ts           # US-20 (Playwright)
└── docs/
    ├── sdd/                    # este kit
    ├── runbooks/{web,db,dns,smtp}.md
    ├── playbooks/{servico-fora,ddos,bruteforce,config-alterada,cve-critico}.md
    └── instalacao.md
```

## 3. Modelo de dados (Supabase)

Migração inicial `supabase/migrations/<timestamp>_init.sql`:

```sql
create table services (
  id text primary key check (id in ('web','db','dns','smtp')),
  name text not null,
  host text not null,
  current_level text not null default 'green' check (current_level in ('green','yellow','red'))
);

create table metrics (
  id bigint generated always as identity primary key,
  service_id text not null references services(id),
  metric text not null,                       -- ex.: 'web.latency_p95_ms'
  value double precision,                     -- null = sonda falhou
  labels jsonb not null default '{}',         -- ex.: {"code":"502"}
  collected_at timestamptz not null default now()
);
create index metrics_lookup on metrics (service_id, metric, collected_at desc);

create table service_status (
  id bigint generated always as identity primary key,
  service_id text not null references services(id),
  up boolean not null,
  check_kind text not null check (check_kind in ('icmp','protocol')),
  latency_ms double precision,
  error text,
  collected_at timestamptz not null default now()
);
create index status_lookup on service_status (service_id, collected_at desc);

create table alert_rules (
  id bigint generated always as identity primary key,
  service_id text not null references services(id),
  metric text not null,
  operator text not null check (operator in ('>','<','>=')),
  warn_threshold double precision not null,
  crit_threshold double precision not null,
  consecutive_cycles int not null default 2,
  enabled boolean not null default true,
  unique (service_id, metric)
);

create table alerts (
  id bigint generated always as identity primary key,
  rule_id bigint references alert_rules(id),
  service_id text not null references services(id),
  kind text not null check (kind in ('threshold','availability','ddos','bruteforce','config_change','cve')),
  level text not null check (level in ('yellow','red')),
  status text not null default 'open' check (status in ('open','resolved')),
  value double precision,
  message text not null,
  details jsonb not null default '{}',
  opened_at timestamptz not null default now(),
  resolved_at timestamptz,
  last_notified_at timestamptz
);
create index alerts_open on alerts (status, opened_at desc);

create table security_events (
  id bigint generated always as identity primary key,
  service_id text not null references services(id),
  type text not null check (type in ('ddos','bruteforce','config_change')),
  details jsonb not null,
  detected_at timestamptz not null default now()
);

create table vulnerabilities (
  id bigint generated always as identity primary key,
  service_id text not null references services(id),
  product_version text not null,
  cve_id text not null,
  cvss numeric(3,1),
  summary text,
  published_at timestamptz,
  checked_at timestamptz not null default now(),
  unique (service_id, cve_id)
);

create table config_baselines (
  path text primary key,
  service_id text not null references services(id),
  sha256 text not null,
  content text not null,
  accepted_at timestamptz not null default now()
);

-- RLS: autenticado lê; ninguém escreve pela API (o coletor usa conexão com service role)
do $$ declare t text; begin
  foreach t in array array['services','metrics','service_status','alert_rules','alerts',
                           'security_events','vulnerabilities','config_baselines'] loop
    execute format('alter table %I enable row level security', t);
    execute format('create policy "leitura autenticada" on %I for select to authenticated using (true)', t);
  end loop;
end $$;

-- Realtime para o painel
alter publication supabase_realtime add table alerts, service_status, services;

-- Retenção de 7 dias (extensão pg_cron habilitada no painel do Supabase)
select cron.schedule('retencao-metricas', '0 3 * * *',
  $$delete from metrics where collected_at < now() - interval '7 days';
    delete from service_status where collected_at < now() - interval '7 days';$$);
```

**Exceção de escrita pelo painel:** "Aceitar como base" (RF-16) é a única ação de escrita do painel. Ela passa por uma função `security definer` `accept_config_baseline(path text)` que só pode ser executada por `authenticated`, em vez de liberar `update` direto na tabela.

`seed.sql` insere os 4 serviços e as regras da seção 5 da spec.

Depois de cada migração: gerar os tipos TS (`supabase gen types typescript` ou a ferramenta do MCP do Supabase) em `web/lib/supabase/types.ts` e rodar os advisors de segurança e desempenho do Supabase.

## 4. Coletor: como cada métrica é obtida

| Métrica | Fonte | Técnica |
|---|---|---|
| UP/DOWN (todos) | ICMP + protocolo | `icmplib` (sem root: `privileged=False`) + HTTP 200 / `SELECT 1` / consulta A / `EHLO` |
| `web.rps`, `web.latency_p50_ms`, `web.latency_p95_ms`, `web.status_count{code}`, `web.error_4xx_rate`, `web.error_5xx_rate` | `access.log` em JSON (volume compartilhado, leitura) | `logtail.py` lê linhas novas desde o último offset; `calc.py` agrega na janela do ciclo |
| `web.active_connections` | `stub_status` | GET `http://nginx/nginx_status` (só rede interna) |
| `db.qps`, `db.rollback_rate`, `db.xact_failure_rate` | `pg_stat_database` | diferença de `xact_commit`, `xact_rollback` e `pg_stat_statements.calls` entre ciclos |
| `db.connections`, `db.connections_ratio` | `pg_stat_activity`, `max_connections` | contagem / máximo |
| `db.cpu_percent`, `db.mem_bytes`, `db.io_read_bps`, `db.io_write_bps` | Docker Engine API | `docker` SDK com socket montado **somente leitura**; `container.stats(stream=False)` |
| `db.disk_read_ms` | `pg_stat_io` / `pg_stat_database.blk_read_time` | exige `track_io_timing = on` |
| `db.size_bytes`, `db.growth_gb_day` | `pg_database_size()` | crescimento = regressão linear das últimas 24 h |
| `db.slow_queries_per_min` | `pg_stat_statements` | novas chamadas com `mean_exec_time > 500` desde o ciclo anterior |
| `dns.resolve_ms`, `dns.failure_rate` | consulta ativa | `dnspython`, 3 consultas por ciclo (nome existente, inexistente, externo) |
| `dns.qps` | CoreDNS `:9153/metrics` | diferença de `coredns_dns_requests_total` |
| `smtp.queue_length` | Postfix | `postqueue -j` via `docker exec` (SDK) e contagem de linhas |
| `smtp.delivery_rate`, `smtp.reject_rate`, `smtp.timeout_rate`, `smtp.volume_per_min` | log do Postfix | contagem de `status=sent`, `status=deferred`, `status=bounced`, `reject:` |
| `smtp.send_latency_ms` | e-mail sonda | envia com `smtplib` um e-mail com ID único e consulta a API do MailHog (`/api/v2/search`) até achá-lo |

**Ciclo (main.py):** a cada 15 s roda as sondas em paralelo (`ThreadPoolExecutor`, timeout de 8 s por sonda), grava métricas e status em lote, depois chama o motor de alertas e os detectores de segurança. A CVE roda num job separado, 1x/dia e no start.

## 5. Motor de alertas

```
para cada regra habilitada:
    valor = última métrica do ciclo
    nivel_bruto = red se viola crit, yellow se viola warn, senão green
    contador[regra] = contador + 1 se nivel_bruto == candidato, senão 1 (novo candidato)
    se contador >= consecutive_cycles e candidato != nivel_atual:
        fecha alerta aberto (se houver) → e-mail de resolução se candidato == green
        abre alerta novo se candidato != green → notifier
estado do serviço = pior nível entre as regras dele → services.current_level
```

- O estado do contador fica em memória e é reconstruído no start a partir dos alertas abertos.
- `notifier.py` decide reenvio por `last_notified_at` (Vermelho 10 min, Amarelo 30 min).
- SMTP de alertas configurável por env (`ALERT_SMTP_HOST`, `ALERT_SMTP_PORT`, `ALERT_SMTP_USER`, `ALERT_SMTP_PASSWORD`, `ALERT_EMAIL_TO`). Dev: MailHog. Demo: Gmail com senha de app ou outro provedor SMTP.
- Assunto: `[CRÍTICO] web indisponível`, `[ATENÇÃO] db conexões em 78%`, `[RESOLVIDO] web`. Corpo com valor, limite, horário, link do painel e link do runbook.

## 6. Segurança (detectores)

| Detector | Entrada | Regra |
|---|---|---|
| `traffic.py` | RPS por ciclo, IPs do `access.log` | janela móvel de 60 amostras (15 min); z-score > 3 ou RPS > 5× a média → evento + alerta Vermelho com top 5 IPs |
| `bruteforce.py` | linhas do log com `POST /login` e status 401; campo `user` registrado pelo app demo | janela deslizante de 5 min por IP (≥ 10) e por conta (≥ 5) |
| `config_watch.py` | arquivos montados somente leitura | SHA-256 a cada ciclo vs `config_baselines`; diff com `difflib.unified_diff` no `details` |
| `cve.py` | versão de cada serviço (`Server` header, `select version()`, `coredns -version` pelo log de start ou `/metrics` `coredns_build_info`, `postconf mail_version`) | NVD API 2.0 `cves/2.0?cpeName=...` (conferir o CPE exato de cada produto no NVD); respeitar limite de 5 req/30 s sem chave; CVSS v3.1 ≥ 7,0 → alerta Amarelo |

## 7. Painel

- `@supabase/ssr` com cliente de servidor (Server Components) e de browser (Realtime).
- `middleware.ts` renova a sessão e redireciona para `/login` sem usuário.
- Visão consolidada: Server Component busca o estado inicial; um Client Component assina `alerts`, `service_status` e `services` via Realtime.
- Dashboards: consultas agregadas por `date_trunc` numa função SQL `metric_series(service, metric, range)` para não puxar milhares de linhas.
- Gráficos com Recharts; cores dos estados num único `status-colors.ts`.
- Visual feito com a skill **frontend-design** (layout escuro estilo "sala de operações", tipografia mono para números).
- Deploy pela Vercel; envs: `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`. **Nunca** a service role no painel.

## 8. Estratégia de testes

| Camada | Ferramenta | O que cobre |
|---|---|---|
| Cálculos puros | pytest | percentis, taxas, z-score, GB/dia, avaliação de regras com histerese, janelas do brute-force |
| Parsers | pytest + fixtures de log reais | `access.log` JSON, log do Postfix, saída do `postqueue -j`, `/metrics` do CoreDNS |
| Sondas | pytest + `docker compose` (marcador `integration`) | cada sonda contra o serviço real |
| Notificador | pytest + MailHog | e-mail chega com assunto e corpo certos; reenvio respeita intervalos |
| Componentes | Vitest + Testing Library | cartão de status, filtro de período |
| Banco | SQL + MCP do Supabase | RLS: anon sem sessão lê 0 linhas; authenticated não consegue `insert` |
| E2E | Playwright (projetos `mobile` 390×844 e `desktop` 1440×900) | login, consolidada, 4 dashboards, segurança, alerta ao vivo após `loadgen stop_service web` |

## 9. Variáveis de ambiente (`.env.example`)

```
# Coletor
SUPABASE_DB_URL=postgresql://postgres.<ref>:<senha>@aws-0-<regiao>.pooler.supabase.com:5432/postgres
COLLECT_INTERVAL_SECONDS=15
ALERT_SMTP_HOST=mailhog
ALERT_SMTP_PORT=1025
ALERT_SMTP_USER=
ALERT_SMTP_PASSWORD=
ALERT_EMAIL_TO=dupla@example.com
DASHBOARD_URL=http://localhost:3000
NVD_API_KEY=            # opcional, aumenta o limite de requisições

# Painel (web/.env.local e Vercel)
NEXT_PUBLIC_SUPABASE_URL=
NEXT_PUBLIC_SUPABASE_ANON_KEY=
```

## 10. Riscos

| Risco | Mitigação |
|---|---|
| ICMP bloqueado dentro do Docker | `icmplib` sem privilégio ou `cap_add: NET_RAW` no coletor; o check de protocolo também define UP/DOWN |
| Socket do Docker dá poder demais ao coletor | montar `:ro` e documentar no relatório como risco aceito no laboratório |
| Limite do plano grátis do Supabase (500 MB) | retenção de 7 dias; estimativa ~40 métricas × 4/min ≈ 230 mil linhas/dia |
| Rede da faculdade instável na demo | painel também roda local (`pnpm dev`); vídeo gravado como plano B |
| API do NVD lenta ou fora | cache na tabela `vulnerabilities`; a página mostra a data da última checagem |
