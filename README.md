# ⚡ DevOps Monitor

### Plataforma de Monitoramento, Observabilidade e Segurança de Infraestrutura

Monitoramento centralizado de serviços Web, Banco de Dados, DNS e SMTP, com coleta automatizada de métricas, análise de eventos, detecção de ameaças e visualização em tempo real.

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.12-blue?logo=python" />
  <img src="https://img.shields.io/badge/Next.js-15-black?logo=next.js" />
  <img src="https://img.shields.io/badge/TypeScript-5-blue?logo=typescript" />
  <img src="https://img.shields.io/badge/React-19-61DAFB?logo=react" />
  <img src="https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker" />
  <img src="https://img.shields.io/badge/Supabase-Database%20%7C%20Auth%20%7C%20Realtime-3FCF8E?logo=supabase" />
</p>

<p align="center">
  **Projeto acadêmico — Engenharia de Software | IDP**
</p>

---

## 📌 Sobre o projeto

O **DevOps Monitor** é uma plataforma de monitoramento, observabilidade e segurança desenvolvida para acompanhar o funcionamento de diferentes serviços que compõem uma infraestrutura de TI.

A proposta é centralizar informações operacionais em um único ambiente, permitindo acompanhar a disponibilidade dos serviços, identificar degradações de desempenho, analisar eventos e detectar comportamentos potencialmente maliciosos.

A plataforma contempla quatro componentes principais:

| Serviço | Indicadores monitorados |
|---|---|
| 🌐 **Web** | Requisições por segundo, latência, erros HTTP, conexões e disponibilidade |
| 🗄️ **Database** | Consultas, conexões, transações, consultas lentas e utilização de recursos |
| 🌍 **DNS** | Tempo de resolução, falhas de consulta e volume de requisições |
| ✉️ **SMTP** | Fila de mensagens, entregas, rejeições e latência de envio |

O projeto utiliza um coletor desenvolvido em Python para executar sondas de monitoramento e processar informações dos serviços. Os dados são persistidos no Supabase e disponibilizados por meio de um painel web desenvolvido com Next.js e TypeScript.

Além do monitoramento convencional, a solução incorpora mecanismos de detecção de anomalias, tentativas de força bruta, alterações em arquivos de configuração e vulnerabilidades conhecidas.

O ambiente de infraestrutura é reproduzido localmente com Docker Compose, permitindo realizar testes controlados, simular incidentes e observar o comportamento da plataforma diante de diferentes situações.

## 🎯 Objetivos

- Centralizar o monitoramento de diferentes serviços de infraestrutura.
- Acompanhar disponibilidade e indicadores de desempenho.
- Armazenar e consultar métricas históricas.
- Identificar indisponibilidades e comportamentos anormais.
- Detectar possíveis ameaças e alterações suspeitas.
- Automatizar a identificação e o registro de incidentes.
- Disponibilizar informações em um dashboard intuitivo.
- Simular situações de falha e eventos de segurança em ambiente controlado.

## 🏗️ Arquitetura do sistema

A arquitetura foi organizada em componentes independentes, separando a infraestrutura monitorada, a coleta de dados, o armazenamento, a aplicação web e os mecanismos de teste.

### Fluxo de funcionamento

1. **Infraestrutura:** os serviços monitorados são inicializados em containers Docker.
2. **Coleta:** o coletor Python executa sondas periódicas e obtém informações dos serviços.
3. **Processamento:** as métricas são calculadas, normalizadas e avaliadas pelos mecanismos de monitoramento e segurança.
4. **Persistência:** os dados são armazenados no PostgreSQL do Supabase.
5. **Alertas:** condições operacionais e eventos suspeitos são avaliados pelo motor de alertas.
6. **Visualização:** o painel Next.js consulta os dados e recebe atualizações por meio do Supabase Realtime.

### Componentes da arquitetura

| Componente | Responsabilidade |
|---|---|
| `infra/` | Ambiente Docker com os serviços monitorados e aplicações auxiliares |
| `collector/` | Coleta, processamento de métricas, detecção de eventos e geração de alertas |
| `supabase/` | Banco de dados, migrações, políticas de acesso e dados iniciais |
| `web/` | Aplicação web, autenticação e dashboards |
| `loadgen/` | Geração controlada de tráfego e simulação de falhas |
| `docs/` | Documentação técnica, arquitetura, instalação e procedimentos operacionais |

O coletor funciona independentemente do painel web. Essa separação permite executar tarefas contínuas de monitoramento sem depender do ciclo de execução de uma aplicação web.

## 🚀 Funcionalidades

### 1. Monitoramento de infraestrutura

O coletor realiza verificações periódicas dos quatro serviços contemplados pelo projeto.

| Serviço | Monitoramento |
|---|---|
| Web | Disponibilidade HTTP, RPS, latência, erros 4xx/5xx e conexões |
| Database | Disponibilidade, consultas, conexões, transações, consultas lentas e recursos |
| DNS | Resolução de nomes, tempo de resposta, falhas e volume de consultas |
| SMTP | Disponibilidade, fila, entrega de mensagens e rejeições |

A coleta utiliza diferentes mecanismos, incluindo consultas SQL, sondas de protocolo, leitura de logs estruturados e informações disponibilizadas pelos containers.

### 2. Dashboard de observabilidade

A aplicação web foi desenvolvida utilizando Next.js, React e TypeScript.

Entre os recursos presentes na interface estão:

- Autenticação de operadores.
- Proteção de rotas por sessão.
- Visão geral dos serviços monitorados.
- Indicadores de disponibilidade.
- Histórico e acompanhamento de alertas.
- Atualizações de informações utilizando Supabase Realtime.
- Visualização de métricas e informações operacionais.
- Área dedicada aos mecanismos de segurança.
- Interface adaptável a diferentes tamanhos de tela.

O painel diferencia informações não disponíveis de métricas efetivamente coletadas, evitando apresentar valores fictícios como resultados reais de monitoramento.

### 3. Sistema de alertas

O motor de alertas avalia as condições dos serviços e identifica situações que exigem atenção.

O sistema utiliza regras de avaliação, níveis de severidade e mecanismos de histerese para reduzir oscilações desnecessárias nos estados dos alertas.

| Nível | Significado |
|---|---|
| 🟢 Verde | Condição normal |
| 🟡 Amarelo | Situação de atenção |
| 🔴 Vermelho | Condição crítica |

O mecanismo também contempla notificações por e-mail, controle de intervalos de reenvio e mensagens de resolução quando uma condição crítica é normalizada.

### 4. Segurança e detecção de ameaças

Além da observabilidade, o DevOps Monitor possui mecanismos específicos para identificar eventos potencialmente maliciosos.

| Mecanismo | Descrição |
|---|---|
| **Análise de tráfego** | Identifica variações incomuns no volume de requisições utilizando análise estatística e Z-Score. |
| **Brute Force Detection** | Identifica tentativas repetidas de autenticação associadas a endereços IP e contas. |
| **Config Watch** | Monitora alterações nos arquivos de configuração utilizando hashes SHA-256. |
| **CVE Scanner** | Consulta a base do NVD para identificar vulnerabilidades associadas às versões dos serviços monitorados. |

Os eventos identificados são registrados e podem influenciar o estado de segurança apresentado no painel.

### 5. Simulação de carga e falhas

O projeto conta com um gerador de cenários desenvolvido em Python, utilizado para testar o comportamento da infraestrutura e demonstrar os mecanismos de monitoramento.

Cenários disponíveis:

| Cenário | Finalidade |
|---|---|
| `normal` | Geração de tráfego convencional |
| `spike` | Simulação de aumento repentino de requisições |
| `bruteforce` | Simulação de tentativas repetidas de autenticação |
| `stop_service` | Interrupção controlada de um serviço |
| `edit_config` | Alteração temporária de um arquivo de configuração |
| `smtp_flood` | Envio controlado de mensagens ao ambiente SMTP local |

Os cenários que podem afetar a disponibilidade dos serviços exigem confirmação explícita e possuem limites de execução. Seu uso é destinado exclusivamente ao laboratório isolado do projeto.

## 🛠️ Tecnologias utilizadas

### Backend e coleta de dados

| Tecnologia | Aplicação |
|---|---|
| Python 3.12 | Coletor e ferramentas auxiliares |
| APScheduler | Agendamento dos ciclos de coleta |
| Pydantic | Configuração e validação de dados |
| Psycopg 3 | Comunicação com PostgreSQL |
| dnspython | Consultas e monitoramento DNS |
| icmplib | Verificações de disponibilidade via ICMP |
| Docker SDK | Consulta controlada de estatísticas dos containers |
| PyYAML | Configuração do coletor |

### Frontend

| Tecnologia | Aplicação |
|---|---|
| Next.js 15 | Framework da aplicação web |
| React 19 | Construção dos componentes |
| TypeScript | Tipagem estática |
| Tailwind CSS 4 | Estilização da interface |
| Supabase SSR | Autenticação e gerenciamento de sessões |
| Vitest | Testes unitários |
| Playwright | Testes end-to-end |

### Infraestrutura e armazenamento

- Docker e Docker Compose.
- Nginx.
- PostgreSQL 16.
- CoreDNS.
- Postfix.
- MailHog.
- Supabase (PostgreSQL, Auth e Realtime).
- API do NVD (National Vulnerability Database).

## 📂 Estrutura do projeto

```text
DevOps-Monitor/
│
├── collector/                  # Coletor e mecanismos de monitoramento
│   ├── src/monitor/
│   │   ├── probes/             # Sondas dos serviços
│   │   ├── alerts/             # Motor e notificações de alertas
│   │   ├── security/            # Detectores de segurança
│   │   ├── main.py
│   │   ├── pipeline.py
│   │   ├── model.py
│   │   ├── store.py
│   │   ├── calc.py
│   │   └── config.py
│   ├── tests/                  # Testes automatizados
│   ├── Dockerfile
│   └── pyproject.toml
│
├── web/                        # Aplicação Next.js
│   ├── app/
│   │   ├── login/              # Autenticação
│   │   └── (dash)/             # Área protegida do painel
│   ├── components/             # Componentes da interface
│   ├── lib/                    # Integrações e utilitários
│   ├── e2e/                    # Testes end-to-end
│   └── package.json
│
├── frontend/                   # Protótipo visual anterior
│
├── infra/                      # Serviços do laboratório
│   ├── nginx/
│   ├── demo-app/
│   ├── postgres/
│   ├── coredns/
│   ├── postfix/
│   └── docker_stats_proxy/
│
├── loadgen/                    # Gerador de carga e falhas
│   ├── src/loadgen/
│   │   └── scenarios/
│   ├── tests/
│   └── pyproject.toml
│
├── supabase/                   # Banco e configurações
│   ├── migrations/
│   ├── tests/
│   ├── config.toml
│   └── seed.sql
│
├── docs/                       # Documentação técnica
│   ├── sdd/
│   ├── runbooks/
│   ├── playbooks/
│   ├── arquitetura.md
│   ├── instalacao.md
│   ├── testes.md
│   └── demo-roteiro.md
│
├── docker-compose.yml
├── .env.example
├── .gitignore
└── README.md
```

**Observação:** `frontend/` contém o protótipo visual anterior. A aplicação web principal e utilizada na arquitetura atual está em `web/`.

## ⚙️ Instalação e execução

### Pré-requisitos

- Docker Engine.
- Docker Compose v2.
- Python 3.12.
- `uv` (para execução local do coletor e gerador de carga).
- Node.js 22 ou superior.
- pnpm 11 ou superior.
- Projeto Supabase configurado, para persistência e autenticação completas.

### 1. Clonar o repositório

```bash
git clone https://github.com/Matheus-Nunes223/DevOps-Monitor.git

cd DevOps-Monitor
```

### 2. Configurar as variáveis de ambiente

Na raiz do projeto:

```bash
cp .env.example .env
```

Configure as variáveis necessárias, principalmente:

- `SUPABASE_DB_URL`: conexão do coletor com o banco do Supabase.
- `LAB_DB_URL`: conexão com o PostgreSQL do laboratório.
- `NVD_API_KEY`: chave opcional para consultas à API do NVD.

Para o painel web:

```bash
cd web

cp .env.example .env.local
```

Configure:

```env
NEXT_PUBLIC_SUPABASE_URL=
NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY=
```

Também é aceita a chave legada `NEXT_PUBLIC_SUPABASE_ANON_KEY`.

**Importante:** nunca exponha `SUPABASE_SERVICE_ROLE_KEY` no frontend, em variáveis `NEXT_PUBLIC_*` ou no repositório.

### 3. Inicializar a infraestrutura

Na raiz do projeto:

```bash
docker compose up --build -d
```

Verifique os containers:

```bash
docker compose ps
```

Principais endereços locais:

| Serviço | Endereço |
|---|---|
| Aplicação Web de demonstração | http://localhost:8080 |
| Interface MailHog | http://localhost:8025 |
| Relay SMTP | `127.0.0.1:2525` |
| CoreDNS | `127.0.0.1:1053` |

O PostgreSQL do laboratório não possui porta publicada diretamente no host.

### 4. Executar o dashboard

Dentro do diretório `web/`:

```bash
pnpm install --frozen-lockfile

pnpm dev
```

Acesse:

```text
http://localhost:3000
```

A autenticação real depende da configuração do Supabase Auth, das URLs de redirecionamento e da criação de um usuário de operador.

### 5. Executar o coletor localmente

Com Python 3.12, `uv`, infraestrutura e banco configurados:

```bash
cd collector

uv sync --dev

uv run pytest

uv run devops-monitor
```

A execução integrada requer as variáveis de conexão com o Supabase e com o PostgreSQL do laboratório.

### 6. Executar o gerador de cenários

Na raiz do projeto:

```bash
uv sync --project loadgen

uv run --project loadgen devops-loadgen --help
```

Exemplo de geração de tráfego:

```bash
uv run --project loadgen devops-loadgen normal --requests 60 --rate 2
```

Para simular uma interrupção controlada:

```bash
uv run --project loadgen devops-loadgen stop_service --service nginx --duration 10 --confirm-fault
```

Consulte [`loadgen/README.md`](loadgen/README.md) antes de executar os cenários que modificam ou interrompem serviços.

### Encerrando o ambiente

Na raiz do projeto:

```bash
docker compose down
```

Para remover também os volumes persistentes do laboratório:

```bash
docker compose down -v
```

Atenção: o segundo comando remove os dados persistidos nos volumes do ambiente local.

## 🧪 Testes e validação

O projeto possui testes automatizados distribuídos entre seus principais componentes.

| Camada | Ferramenta | Finalidade |
|---|---|---|
| Coletor | Pytest | Validar cálculos, sondas, parsers, persistência e alertas |
| Segurança | Pytest | Validar detectores de eventos e mecanismos de proteção |
| Gerador de carga | Pytest | Validar cenários e limites de execução |
| Frontend | Vitest | Validar componentes e comportamentos |
| Interface | Playwright | Validar navegação, responsividade e fluxos da aplicação |
| Banco de dados | pgTAP | Validar políticas RLS e funções do banco |
| Qualidade | ESLint e TypeScript | Verificar padrões de código e tipagem |
| Build | Next.js | Verificar a compilação da aplicação |

Para executar os testes:

```bash
# Coletor
cd collector
uv run pytest
```

```bash
# Gerador de cenários
uv run --project loadgen pytest
```

```bash
# Frontend
cd web
pnpm lint
pnpm typecheck
pnpm test
pnpm test:e2e
pnpm build
```

Os testes integrados dependem da disponibilidade do Docker, das migrações do Supabase e da configuração dos serviços externos. A existência de testes automatizados não representa, por si só, uma homologação completa do ambiente de produção.

Mais informações estão disponíveis em [`docs/testes.md`](docs/testes.md).

## 🔐 Segurança

A segurança é um dos pilares do DevOps Monitor.

Entre as medidas contempladas na arquitetura estão:

- Separação entre credenciais públicas e privadas.
- Autenticação e proteção de rotas do dashboard.
- Políticas de Row Level Security (RLS) no Supabase.
- Restrição de portas publicadas ao loopback quando aplicável.
- Proxy dedicado para limitar as operações disponibilizadas pela API Docker.
- Montagem dos arquivos de configuração monitorados em modo somente leitura.
- Limites de execução e confirmação explícita nos cenários de falha.
- Separação entre a rede dos serviços monitorados e a comunicação com a API Docker.
- Registro e acompanhamento de eventos de segurança.

O projeto foi desenvolvido para demonstração e experimentação em ambiente controlado. Sua utilização em infraestruturas de produção exige revisão adicional de segurança, configuração, disponibilidade e gerenciamento de credenciais.

## 📚 Documentação

A documentação complementar está organizada no diretório `docs/`.

| Documento | Conteúdo |
|---|---|
| [`docs/arquitetura.md`](docs/arquitetura.md) | Arquitetura e comunicação entre componentes |
| [`docs/instalacao.md`](docs/instalacao.md) | Instalação e configuração do laboratório |
| [`docs/testes.md`](docs/testes.md) | Estratégia de testes e validação |
| [`docs/demo-roteiro.md`](docs/demo-roteiro.md) | Roteiro para demonstração do projeto |
| [`docs/sdd/`](docs/sdd/) | Especificações, planejamento e desenvolvimento por funcionalidades |
| [`docs/runbooks/`](docs/runbooks/) | Procedimentos operacionais dos serviços |
| [`docs/playbooks/`](docs/playbooks/) | Procedimentos de resposta a incidentes |
| [`collector/README.md`](collector/README.md) | Configuração e execução do coletor |
| [`web/README.md`](web/README.md) | Configuração e execução do dashboard |
| [`loadgen/README.md`](loadgen/README.md) | Cenários de carga e falhas |

## 👥 Equipe de desenvolvimento

Projeto desenvolvido por:

| Integrante | Participação |
|---|---|
| **Matheus Nunes** | Desenvolvimento |
| **João Guilherme** | Desenvolvimento |
| **Bruna Cayres** | Desenvolvimento |

**Instituição:** Instituto Brasileiro de Ensino, Desenvolvimento e Pesquisa (IDP)  
**Curso:** Engenharia de Software  
**Disciplina:** Redes de Computadores e Internet  
**Natureza:** Projeto acadêmico

---

<p align="center">
  **DevOps Monitor**
  <br />
  Monitoramento, observabilidade e segurança em um único ambiente.
  <br /><br />
  Desenvolvido como projeto acadêmico, integrando conceitos de redes de computadores, infraestrutura, desenvolvimento de software e segurança da informação.
</p>
