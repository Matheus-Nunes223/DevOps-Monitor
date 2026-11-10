# Plano · US-05 · Métricas Web

- **Spec:** `docs/sdd/features/US-05.md`
- **Branch:** `feat/US-05-metricas-web`
- **Docs consultadas:** JSON da biblioteca padrão Python; Nginx `stub_status` conforme [documentação oficial](https://nginx.org/en/docs/http/ngx_http_stub_status_module.html). Nenhuma biblioteca adicional.

## Arquivos
| Ação | Caminho | Responsabilidade |
|---|---|---|
| criar | `collector/src/monitor/logtail.py` | offset incremental, append, rotação, truncamento e linhas parciais |
| criar | `collector/src/monitor/calc.py` | parser JSON e cálculos puros de contagem, taxas e percentis |
| criar | `collector/src/monitor/probes/web.py` | probes separadas para access log e `stub_status` |
| testar | `collector/tests/unit/test_logtail.py` | append, parcial, truncamento e rotação com arquivos temporários |
| testar | `collector/tests/unit/test_calc.py` | fixtures de linhas JSON e casos sem tráfego |
| testar | `collector/tests/unit/test_web.py` | integração das probes com readers/adapters falsos |
| atualizar | `infra/nginx/nginx.conf` | desativar access log para `/nginx_status` |
| atualizar | `collector/src/monitor/config.py` | caminho do access log e URL privada do status |
| atualizar | `collector/config.yaml` | destinos não secretos |
| atualizar | `collector/src/monitor/main.py` | registrar probes Web no ciclo |

## Tarefas
### 1. Logtail e parser/cálculos
- [x] Escrever testes para offset incremental, rotação, truncamento e linha incompleta.
- [x] Escrever testes para schema JSON, p50/p95, códigos HTTP, taxas e janela vazia.
- [x] Executar falha esperada antes da implementação (`ModuleNotFoundError` para os módulos ainda não criados).
- [x] Implementar logtail e funções puras.

### 2. Probes Web
- [x] Testar coleta do access log e conexões do stub_status separadamente.
- [x] Implementar probes, métricas com labels e logging seguro de JSON malformado.
- [x] Registrar as probes no ciclo do collector.
- [x] Evitar que `/nginx_status` contamine o access log.

## Verificação final
- [x] Suíte equivalente via `python3 -m unittest`: 14 testes US-05 passaram; suíte combinada do coletor: 31 testes passaram.
- [ ] Executar com Nginx real; gerar tráfego e comparar RPS/status/latência com logs.
- [ ] Confirmar stub_status somente na rede interna e log compartilhado read-only.

## Revisão
- [x] Verificar que RPS usa duração efetiva medida e que o primeiro ciclo não consome logs históricos (revisão de código/testes).
- [x] Verificar que status_count labels são JSON serializáveis e persistidos em lote (contrato `Metric` e testes).
- [x] Revisar logs: linhas inválidas são contadas sem expor conteúdo, IP ou usuário.

## Pendências de validação
- [ ] Rodar a suíte com `uv run pytest` e verificações ruff/pyright no ambiente com dependências.
- [ ] Executar com Nginx real, gerar tráfego e comparar RPS/status/latência com os logs.
- [ ] Confirmar `stub_status` restrito à rede interna e volume de log montado somente leitura via Docker Compose.
- [ ] A história não está concluída até os critérios de integração acima serem verificados.
