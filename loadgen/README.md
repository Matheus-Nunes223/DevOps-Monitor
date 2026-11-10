# Gerador de carga e falhas

Instale as dependências do pacote na raiz do projeto:

```bash
uv sync --project loadgen
uv run --project loadgen devops-loadgen --help
```

Com o laboratório ativo, os cenários HTTP usam por padrão `http://127.0.0.1:8080`. A CLI limita quantidades, taxa e concorrência; alvos fora de loopback exigem `--allow-remote-target`.

## Cenários

```bash
uv run --project loadgen devops-loadgen normal --requests 60 --rate 2
uv run --project loadgen devops-loadgen spike --requests 200 --concurrency 20
uv run --project loadgen devops-loadgen bruteforce --attempts 20
uv run --project loadgen devops-loadgen stop_service --service nginx --duration 10 --confirm-fault
uv run --project loadgen devops-loadgen edit_config --duration 10 --confirm-fault
uv run --project loadgen devops-loadgen smtp_flood --messages 10 --rate 2 --confirm-fault
```

`normal`, `spike` e `bruteforce` usam somente a aplicação demonstrativa. Brute force envia senhas aleatórias e uma identidade sintética para `/login`; não use contas ou senhas reais. SMTP flood usa o relay local publicado apenas em `127.0.0.1:2525` e envia para MailHog.

Os cenários `stop_service`, `edit_config` e `smtp_flood` exigem confirmação explícita. A parada aceita somente `nginx`, `postgres`, `coredns` e `postfix`, verifica que o serviço estava rodando e reinicia-o ao terminar. A edição altera somente `infra/nginx/nginx.conf`, roda `nginx -t`, recarrega e restaura os bytes originais em `finally`. O cenário SMTP aceita até 1.000 mensagens, com taxa máxima de 5/s. Não execute cenários de falha enquanto outra pessoa estiver usando o laboratório.

## Testes

```bash
uv run --project loadgen pytest
```

Os testes usam clientes falsos e arquivos temporários; eles não iniciam cargas reais nem param containers.
