# Playbook · Brute-force em /login

**Gatilho:** alerta Vermelho `bruteforce`: ≥ 10 respostas 401 do mesmo IP ou ≥ 5 da mesma conta em 5 min.

1. **Identificar** IP(s) e conta(s) na página **Segurança** (evento com contagem).
2. **Verificar** se a conta foi comprometida (houve algum login com sucesso depois das falhas?).
3. **Conter:** bloquear o IP no Nginx; forçar redefinição de senha da conta atacada; considerar bloqueio temporário após N falhas.
4. **Endurecer:** habilitar MFA e limitação de taxa em `/login`.
5. **Encerrar:** o alerta resolve quando a janela de 5 min esvazia; registrar o incidente.
