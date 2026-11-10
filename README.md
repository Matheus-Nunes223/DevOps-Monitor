# DevOps Monitor

Plataforma acadêmica de monitoramento de Web, Database, DNS e SMTP.

## Arquitetura alvo (Backlog v2)

- `infra/`: ambiente Docker dos serviços monitorados.
- `collector/`: coletor Python, sondas, regras de alerta e detectores de segurança.
- `supabase/`: configuração, migrações e seed do banco/autenticação.
- `web/`: painel Next.js/TypeScript.
- `loadgen/`: cenários controlados de tráfego e falhas para demonstração.
- `docs/`: especificação, plano, runbooks e playbooks.

## Estado atual

Código implementado para as histórias US-01 a US-18, US-20 (testes escritos) e a documentação de US-21 (runbooks, playbooks, arquitetura, roteiro). Coletor: 100+ testes unitários; painel: lint, tipos, build e testes unitários passam. Pendente de execução externa: subir o Docker, aplicar as migrações no projeto Supabase, criar o usuário do painel, deploy na Vercel, rodar os testes E2E logados, ensaio da demo e montagem do PDF ABNT. `frontend/` é o protótipo estático antigo, mantido só como referência visual; o painel real é `web/`.

O fluxo, as specs e os planos por história estão em `docs/sdd/`. A arquitetura alvo segue o Backlog v2: coletor Python + Supabase + Next.js/Vercel, sem introduzir FastAPI.

## Segredos e configuração

Copie `.env.example` para `.env` local e preencha somente no ambiente apropriado. Nunca versione `.env`, tokens ou credenciais. A chave `SUPABASE_SERVICE_ROLE_KEY` deve permanecer no coletor e nunca ser exposta ao painel.

## Execução

O frontend demonstrativo legado pode ser servido com:

```bash
python3 -m http.server 8000 --directory frontend
```

Para o painel Next.js, siga [`web/README.md`](web/README.md). O guia do laboratório e do coletor está em [`docs/instalacao.md`](docs/instalacao.md) e [`collector/README.md`](collector/README.md). O ambiente completo ainda requer Docker e um projeto Supabase configurado e validado.
