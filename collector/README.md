# Coletor Python

O coletor contém contratos de métricas/status, configuração Pydantic Settings
com YAML e variáveis de ambiente, gravação transacional em lote via Psycopg 3,
executor paralelo com logs JSON, probes de disponibilidade (ICMP e protocolo
para Web, Banco, DNS e SMTP) e coleta Web inicial por access log JSON e
`stub_status`. A integração do coletor com o laboratório ainda requer validação
em Docker.

## Execução local

Requer Python 3.12, `uv`, Docker lab ativo e Supabase local/remoto com as
migrações aplicadas. Configure `SUPABASE_DB_URL` (destino da persistência) e
`LAB_DB_URL` (Postgres local monitorado) no ambiente ou em `.env` local; nunca
coloque DSNs no `config.yaml` versionado.

```bash
cd collector
uv sync --dev
uv run pytest
uv run devops-monitor
```

`config.yaml` guarda somente defaults não secretos. Variáveis de ambiente têm
precedência sobre YAML. O ciclo admite até oito segundos por probe; falhas são
registradas sem expor texto de exceção e seus valores ficam `NULL`. A falha de
persistência é logada e não impede o ciclo agendado seguinte.

## Estado de validação

cinquenta e sete testes unitários de model, runner, scheduler, store, availability,
logtail, cálculos Web/DB/DNS/SMTP, probes e allowlist do proxy passaram com o Python disponível. Os testes
de settings, lint, checagem de tipos, lockfile e execução integrada ainda
dependem de Python 3.12, `uv`, dependências do projeto, Docker e migrações
aplicadas. O serviço `collector` lê o volume `nginx-logs` em modo somente
leitura e requer `SUPABASE_DB_URL` e `LAB_DB_URL` configurados no ambiente. US-06
coleta métricas SQL e Docker; US-07 consulta três nomes DNS e lê QPS do CoreDNS;
US-08 lê logs/fila Postfix e mede entrega por MailHog. O Docker SDK fala com um proxy
dedicado; não monte o socket Docker diretamente no coletor. A API allowlist e o
SDK ainda precisam ser validados contra Docker Engine real. A descoberta completa
do unittest reporta o `test_config.py` sem execução porque Pydantic não está
instalado neste ambiente; os 57 testes listados explicitamente passaram.
