# Guia de instalação local

## Pré-requisitos

- Docker Engine com Docker Compose v2.
- Portas locais 8080, 1053 (UDP/TCP), 2525 (SMTP relay) e 8025 livres.

## Subir o laboratório US-01

Na raiz do projeto:

```bash
docker compose up --build -d
docker compose ps
```

Nginx/app fica em `http://localhost:8080`, MailHog em `http://localhost:8025`, o relay SMTP fica em `127.0.0.1:2525` e CoreDNS escuta em `127.0.0.1:1053`. PostgreSQL não é publicado no host. O Postgres de laboratório usa credenciais fixas sem valor fora deste ambiente acadêmico.

Verificações básicas:

```bash
curl -i http://localhost:8080/
curl -i -X POST -d 'username=teste&password=errada' http://localhost:8080/login
docker compose logs nginx
```

O endpoint `POST /login` é uma fixture: sempre responde 401 e não autentica usuários. O volume `nginx-logs` é lido pelo coletor em modo somente leitura. Para iniciar o coletor, configure `SUPABASE_DB_URL` e `LAB_DB_URL` no ambiente; a primeira aponta para o Supabase de persistência, a segunda para o Postgres do laboratório. Não coloque valores reais no YAML versionado.

O Compose também inicia `docker-stats-proxy` numa rede interna separada. O serviço do coletor não recebe o socket Docker. O proxy só encaminha a leitura de estatísticas do container `devops-monitor-postgres`; o socket do host fica montado somente no proxy. Essa integração precisa de Docker Engine local e ainda não foi exercitada neste ambiente.

## Painel Next.js (US-10)

Requer Node.js 22+ e pnpm 11. Configure apenas `NEXT_PUBLIC_SUPABASE_URL` e `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY` (ou `NEXT_PUBLIC_SUPABASE_ANON_KEY`) em `web/.env.local`. Não copie as variáveis privadas do coletor para esse arquivo. O build rejeita chaves service-role/secret no campo público. Crie o usuário de demonstração no Supabase Auth e autorize `http://localhost:3000/**` nas URLs de redirecionamento.

```bash
cd web
cp .env.example .env.local
pnpm install --frozen-lockfile
pnpm dev
```

Acesse `http://localhost:3000`. Sem essas variáveis, o painel mantém as rotas protegidas e mostra uma mensagem de configuração na tela de login. Os comandos de lint, typecheck, testes e build estão descritos em [`web/README.md`](../web/README.md). Login real e publicação Vercel dependem da configuração externa do projeto e não foram validados aqui.

O coletor calcula as métricas de access log em ciclos de coleta e consulta o `stub_status` pela rede interna. O endpoint de status não registra requisições no access log para evitar que a própria sonda altere as métricas.

O coletor também consulta a fila Postfix e envia uma mensagem sonda periódica pelo relay; a sonda só é considerada entregue quando aparece na API do MailHog. Isso gera mensagens de teste na caixa local durante a execução.

Encerrar:

```bash
docker compose down
```

Este guia descreve a configuração implementada, mas o ciclo completo `docker compose up` e a comparação das métricas com tráfego real ainda precisam ser verificados em uma máquina com Docker disponível.

Os cenários controlados de carga estão documentados em [`loadgen/README.md`](../loadgen/README.md). Cenários de falha exigem a opção `--confirm-fault` e devem ser executados somente no laboratório.

## Alertas por e-mail e segurança (US-13 a US-18)

Variáveis do coletor (no `.env` da raiz, lidas pelo `docker-compose.yml`):

| Variável | Uso |
|---|---|
| `ALERT_SMTP_HOST` / `ALERT_SMTP_PORT` | SMTP dos alertas; padrão `mailhog:1025` (caixa visível em `http://localhost:8025`) |
| `ALERT_SMTP_USER` / `ALERT_SMTP_PASSWORD` | Opcionais; se `USER` for definido, usa STARTTLS + login (ex.: Gmail com senha de app, porta 587) |
| `ALERT_EMAIL_TO` | Um ou mais destinatários separados por vírgula. **Vazio = e-mails desativados** |
| `DASHBOARD_URL` | Link usado nos e-mails (padrão `http://localhost:3000`) |
| `NVD_API_KEY` | Opcional; sem ela a consulta de CVEs é mais lenta (limite de 5 requisições/30 s) |

O detector de mudança de configuração lê `nginx.conf`, `Corefile`, `postgresql.conf` e `main.cf` montados em modo somente leitura. Na primeira execução cada arquivo vira a base aceita. A consulta de CVEs roda 30 s após o coletor iniciar e depois a cada 24 h; a versão do Postfix só é detectada porque `main.cf` expõe `$mail_version` no banner SMTP.

## Verificação ponta a ponta

```bash
docker compose up -d --build && docker compose logs -f collector   # sem "probe failed" repetido
uv run --project loadgen devops-loadgen stop_service --service nginx --duration 60 --confirm-fault
# esperado: e-mails no MailHog e cartão Vermelho no painel
```
