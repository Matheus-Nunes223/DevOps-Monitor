# Playbook · Configuração alterada

**Gatilho:** alerta Amarelo `config alterada: <arquivo>` (`nginx.conf`, `Corefile`, `postgresql.conf` ou `main.cf`). O diff aparece na página **Segurança**.

1. **Ler o diff:** a mudança era esperada (deploy, ajuste planejado)?
2. **Se foi planejada:** clicar em **Aceitar como base** — o alerta se resolve e a nova versão vira referência.
3. **Se não foi planejada:** restaurar o arquivo a partir do Git (`git checkout -- <arquivo>`), recarregar o serviço e investigar quem alterou.
4. **Registrar** o incidente se houve alteração não autorizada.
