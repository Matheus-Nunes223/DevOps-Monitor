# 01 · Especificação do produto

> **O quê** e **por quê**. Nada de "como" aqui; isso fica no `02-plan.md`.
> Fonte: enunciado do Trabalho Final de Redes de Computadores (IDP, Profa. Lorena Borges) e Product Backlog v2.

## 1. Problema

Uma equipe DevOps precisa saber, num único lugar, se os serviços de rede (Web, Banco, DNS e SMTP) estão no ar e com bom desempenho. Também precisa ser avisada por e-mail quando algo degrada ou cai, e quando há sinais de ataque.

## 2. Usuários

| Persona | O que precisa |
|---|---|
| **Operador** (a dupla, na demo) | Ver a saúde geral em segundos, investigar um serviço, receber alertas. |
| **Professora** (avaliadora) | Ver todas as métricas pedidas, alertas funcionando ao vivo, documentação e evidências de teste. |

## 3. Escopo

**Dentro:** 4 serviços monitorados num ambiente Docker local; coleta a cada 15 s; painel web responsivo com login; alertas em 3 níveis por e-mail; detecção de DDoS, brute-force, mudança de configuração e CVEs; testes E2E; relatório ABNT.

**Fora:** monitorar serviços de terceiros na internet; múltiplas organizações; alertas por SMS, Slack ou push; machine learning; alta disponibilidade do próprio coletor.

## 4. Requisitos funcionais

### 4.1 Coleta (RF-01 a RF-06)

| ID | Requisito | História |
|---|---|---|
| RF-01 | Verificar a cada ciclo (padrão 15 s) se cada serviço está UP ou DOWN, por ping e por checagem do próprio protocolo. | US-04 |
| RF-02 | Web: RPS, latência p50/p95 (ms), contagem e taxa de 4xx e 5xx por código, conexões ativas. | US-05 |
| RF-03 | Banco: QPS, taxa de rollback e de transações com falha, conexões abertas vs máximo, CPU/RAM/I-O do container, latência de disco, tamanho e crescimento (GB/dia), queries lentas (> 500 ms). | US-06 |
| RF-04 | DNS: tempo de resolução (ms), taxa de falhas, queries por segundo, disponibilidade. | US-07 |
| RF-05 | SMTP: taxa de entrega, tamanho da fila, latência de envio, taxa de rejeições e timeouts, volume por minuto e por hora. | US-08 |
| RF-06 | Guardar as métricas por no mínimo 7 dias. | US-02 |

### 4.2 Painel (RF-07 a RF-10)

| ID | Requisito | História |
|---|---|---|
| RF-07 | Acesso só com login (e-mail e senha). | US-10 |
| RF-08 | Visão consolidada: um cartão por serviço com estado (cor), disponibilidade 24 h, última checagem; lista de alertas ativos; atualização automática em até 5 s. | US-11 |
| RF-09 | Dashboard por serviço com todas as métricas de RF-02 a RF-05 em séries temporais, filtro 1 h / 6 h / 24 h e histórico de alertas. | US-12 |
| RF-10 | Página de segurança com eventos (DDoS, brute-force, configuração) e vulnerabilidades por serviço. | US-15 a US-18 |

### 4.3 Alertas (RF-11 a RF-13)

| ID | Requisito | História |
|---|---|---|
| RF-11 | Cada métrica com regra é classificada em **Verde** (OK), **Amarelo** (degradação) ou **Vermelho** (crítico / indisponível). O estado de um serviço é o pior estado das suas métricas. | US-13 |
| RF-12 | O nível só muda depois de **2 ciclos seguidos** no novo nível (evita oscilação). | US-13 |
| RF-13 | E-mail: Vermelho no mesmo ciclo em que abre e reenvio a cada 10 min; Amarelo ao abrir e reenvio no máximo a cada 30 min; e-mail de resolução ao voltar ao Verde. | US-14 |

### 4.4 Segurança e monitoramentos extras (RF-14 a RF-17)

| ID | Requisito | História |
|---|---|---|
| RF-14 | Pico de tráfego: z-score do RPS > 3 sobre a média móvel de 15 min, ou RPS > 5× a média → alerta Vermelho com os 5 IPs que mais requisitaram. | US-15 |
| RF-15 | Brute-force: ≥ 10 respostas 401 em `POST /login` do mesmo IP em 5 min, ou ≥ 5 na mesma conta → alerta Vermelho. | US-16 |
| RF-16 | Configuração: mudança no SHA-256 de `nginx.conf`, `Corefile`, `postgresql.conf` ou `main.cf` → alerta Amarelo com diff; o operador pode aceitar a nova versão como base. | US-17 |
| RF-17 | Vulnerabilidades: detectar a versão de cada serviço e consultar CVEs uma vez por dia; CVSS ≥ 7,0 → alerta Amarelo. | US-18 |

## 5. Limites iniciais de alerta

| Serviço | Métrica (`alert_rules.metric`) | Operador | Amarelo | Vermelho |
|---|---|---|---|---|
| todos | `*.up` (falhas seguidas) | ≥ | 1 | 2 |
| web | `web.latency_p95_ms` | > | 500 | 2000 |
| web | `web.error_5xx_rate` | > | 0.02 | 0.10 |
| db | `db.connections_ratio` | > | 0.70 | 0.90 |
| db | `db.slow_queries_per_min` | > | 5 | 20 |
| db | `db.cpu_percent` | > | 75 | 95 |
| dns | `dns.resolve_ms` | > | 100 | 500 |
| dns | `dns.failure_rate` | > | 0.05 | 0.20 |
| smtp | `smtp.queue_length` | > | 50 | 200 |
| smtp | `smtp.delivery_rate` | < | 0.95 | 0.80 |

## 6. Requisitos não funcionais

| ID | Requisito |
|---|---|
| RNF-01 | Painel responsivo e utilizável de 360 px a 1440 px de largura. |
| RNF-02 | Um alerta Vermelho aparece no painel em até 5 s depois de gravado e o e-mail sai no mesmo ciclo. |
| RNF-03 | Um ciclo completo de coleta termina em menos de 10 s (folga para o intervalo de 15 s). |
| RNF-04 | A falha de uma sonda não interrompe as demais (constituição P1). |
| RNF-05 | Só usuários autenticados leem dados; só o coletor escreve (P4). |
| RNF-06 | Instalação completa em até 15 min seguindo o Guia de Instalação. |

## 7. Cenários de aceite principais (Gherkin)

```gherkin
Funcionalidade: Alerta de serviço fora do ar

  Cenário: Web Server cai e volta
    Dado que o painel mostra o Web Server em Verde
    Quando o container do Nginx é parado
    E se passam 2 ciclos de coleta
    Então o cartão do Web Server fica Vermelho na visão consolidada em até 5 s
    E um e-mail "[CRÍTICO] web indisponível" chega à caixa configurada
    Quando o container do Nginx é iniciado de novo
    E se passam 2 ciclos de coleta
    Então o cartão volta a Verde
    E um e-mail "[RESOLVIDO] web" é enviado

Funcionalidade: Brute-force

  Cenário: Muitas senhas erradas do mesmo IP
    Dado o gerador de falhas no cenário "bruteforce"
    Quando 12 requisições POST /login retornam 401 do mesmo IP em 2 minutos
    Então um evento "bruteforce" com IP e contagem aparece na página de segurança
    E um alerta Vermelho é aberto e notificado por e-mail

Funcionalidade: Mudança de configuração

  Cenário: Alguém edita o nginx.conf
    Dado que o hash do nginx.conf está na base aceita
    Quando uma linha é adicionada ao nginx.conf
    Então no ciclo seguinte um alerta Amarelo "config alterada: nginx.conf" é aberto com o diff
    Quando o operador clica em "Aceitar como base"
    Então o alerta é resolvido

Funcionalidade: Acesso ao painel

  Cenário: Visitante sem login
    Dado um visitante não autenticado
    Quando ele acessa /
    Então é redirecionado para /login
    E nenhuma métrica é retornada pela API do Supabase para a anon key sem sessão
```

## 8. Perguntas em aberto

- [ ] A professora aceita o uso de exporters prontos (ex.: métricas nativas do CoreDNS) ou quer toda a coleta escrita pela dupla? *(Este plano usa as métricas nativas do CoreDNS só para QPS; o resto é coletado pela dupla.)*
- [ ] Para onde vão os e-mails de alerta na apresentação: MailHog (mostrado na tela) ou uma caixa real (Gmail com senha de app)?
- [ ] A demo será na máquina de um da dupla ou numa VM? Isso define onde o Docker roda.
