# Plano · US-09 · Gerador de Carga e Falhas

- **Spec:** `docs/sdd/features/US-09.md`
- **Arquitetura:** CLI Python local, dependência httpx para carga HTTP e smtplib para SMTP.

## Arquivos
| Ação | Caminho | Responsabilidade |
|---|---|---|
| criar | `loadgen/pyproject.toml` | dependência e comando `devops-loadgen` |
| criar | `loadgen/src/loadgen/scenarios/*.py` | um módulo por cenário controlado |
| criar | `loadgen/src/loadgen/cli.py`, `__main__.py` | CLI comum, validação de limites e opt-in |
| criar | `loadgen/tests/test_scenarios.py` | adapters falsos e configuração temporária |
| atualizar | `docker-compose.yml` | bind mount Nginx read-only para edição temporária no host |
| atualizar | `loadgen/README.md` | comandos, limites, salvaguardas e limpeza |

## TDD
- [x] Criar testes de cenário/salvaguardas e registrar a falha esperada (`ModuleNotFoundError`).
- [x] Implementar cenários HTTP e SMTP limitados.
- [x] Implementar stop/restore com estado inicial preservado.
- [x] Implementar edição Nginx com restauração em `finally`.
- [x] Integrar CLI única; 8 testes com adapters falsos passaram.

## Validação integrada pendente
- [ ] Executar `normal` e `spike` no ambiente Docker e comparar logs/métricas.
- [ ] Executar cenários de falha deliberadamente e confirmar detecção/recuperação.
