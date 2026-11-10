# Plano · US-01 · Ambiente monitorado

- **Spec:** `docs/sdd/features/US-01.md`
- **Branch:** `feat/US-01-ambiente-monitorado`
- **Docs consultadas (context7):** nenhuma API de biblioteca é usada na app demo; imagens e diretivas Docker precisam de verificação em máquina com Docker.

## Arquivos
| Ação | Caminho | Responsabilidade |
|---|---|---|
| criar | `infra/demo-app/app.py` | HTTP server simples da fixture demo |
| testar | `infra/demo-app/tests/test_app.py` | contrato HTTP e escaping |
| criar | `infra/nginx/*` | proxy, log JSON e status interno |
| criar | `infra/postgres/*` | PostgreSQL e extensão de estatísticas |
| criar | `infra/coredns/*` | zona local, métricas Prometheus e probe de saúde |
| criar | `infra/postfix/*` | relay SMTP interno para MailHog |
| criar | `docker-compose.yml` | composição, rede, healthchecks e volumes |
| atualizar | `docs/instalacao.md` | comandos e limites de validação |

## Tarefas
### 1. Aplicação demo (T-013)
- [x] Escrever testes com `unittest` para `GET /`, `GET /health`, `POST /login` 401 e header de usuário escapável.
- [x] Executar os testes antes do código e observar falha esperada (`ModuleNotFoundError: app`).
- [x] Implementar servidor HTTP padrão Python sem dependências de runtime.
- [x] Executar novamente os testes (5 passando; requer `PYTHONPATH=infra/demo-app` por causa do hífen no nome do diretório).

### 2. Configuração dos serviços (T-012, T-014, T-015, T-016)
- [x] Criar configs Nginx, PostgreSQL, CoreDNS e Postfix conforme spec.
- [x] Revisar portas publicadas no loopback, credenciais restritas ao laboratório e volumes.

### 3. Composição (T-011)
- [x] Declarar rede isolada, healthchecks e volumes compartilhados.
- [x] Validar sintaxe YAML disponível localmente com PyYAML.
- [ ] Executar `docker compose config` e `docker compose up` em ambiente com Docker; aguardar saúde até 60 s (T-017).

## Verificação final
- [x] `PYTHONPATH=infra/demo-app python3 -m unittest discover -s infra/demo-app/tests -v` (5 testes passando).
- [x] YAML parseado por PyYAML (seis serviços e PostgreSQL 16 conferidos).
- [ ] `docker compose config` e smoke tests do ambiente (bloqueados neste ambiente enquanto Docker não estiver instalado).

## Revisão
- [ ] Revisar diff por segredos, portas expostas e falhas silenciosas.
