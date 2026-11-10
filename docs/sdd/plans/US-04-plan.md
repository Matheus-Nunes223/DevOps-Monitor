# Plano · US-04 · Disponibilidade

- **Spec:** `docs/sdd/features/US-04.md`
- **Branch:** `feat/US-04-disponibilidade`
- **Docs consultadas:** [icmplib](https://pypi.org/project/icmplib/), [dnspython resolver](https://dnspython.readthedocs.io/en/stable/resolver.html), [Psycopg 3](https://www.psycopg.org/psycopg3/docs/basic/usage.html). Context7 não está disponível nesta sessão.

## Arquivos
| Ação | Caminho | Responsabilidade |
|---|---|---|
| criar | `collector/src/monitor/probes/availability.py` | ICMP e quatro protocolos reais |
| testar | `collector/tests/unit/test_availability.py` | testes sem rede real, com adaptadores injetados |
| atualizar | `collector/src/monitor/config.py` | DSN DB de laboratório e destinos monitorados |
| atualizar | `collector/config.yaml` | defaults não secretos do laboratório |
| atualizar | `collector/pyproject.toml` | icmplib e dnspython |
| criar | `supabase/migrations/20261109000100_availability_24h.sql` | agregação de disponibilidade medida em 24 h |
| testar | `supabase/tests/database/availability_test.sql` | pgTAP de agregação por tipo de check |

## Tarefas
### 1. Contrato e testes
- [x] Testar ICMP UP/DOWN e falha de biblioteca sem status inventado.
- [x] Testar HTTP, `SELECT 1`, resolução A via CoreDNS e EHLO SMTP.
- [x] Testar que as quatro provas de protocolo e quatro ICMP são registradas separadamente.

### 2. Implementação
- [x] Criar adapters com timeout e dependências injetáveis.
- [x] Criar as oito `ProbeDefinition` do runner; falhas de protocolo podem indicar DOWN, erro ICMP fica como medição ausente.
- [x] Atualizar config e dependências.

### 3. Disponibilidade 24 h (T-041)
- [x] Criar a função `service_availability_24h`, separada por serviço e tipo de check.
- [x] Escrever pgTAP cobrindo a disponibilidade calculada a partir de linhas medidas.

## Verificação final
- [ ] `uv run pytest tests/unit/test_availability.py` (pytest/uv não disponíveis; os testes foram executados via `unittest`).
- [ ] Executar probes no Docker lab e comparar com respostas reais (Docker ausente).
- [ ] Aplicar e executar migration/pgTAP em Supabase local (CLI e Docker ausentes).
- [ ] Confirmar com US-01 que o DNS do coletor aponta ao CoreDNS e que o DSN local é segredo de ambiente.

Nove testes específicos da US-04 e oito testes anteriores do coletor passaram via `unittest` no Python 3.14 disponível. `compileall`, limite manual de 100 caracteres e parse de TOML/YAML passaram. Não houve teste de rede ou SQL real.

## Revisão
- [ ] Revisar timeouts e garantir que uma probe não impede a outra.
- [ ] Confirmar que nenhum dado de exceção contém DSN/token nos logs.
