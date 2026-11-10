# US-XX · <título da história>

> Spec de uma história. Diz **o quê** e **por quê**; o **como** fica em `plans/US-XX-plan.md`.

- **Épico:** <Infra | Coleta | Painel | Alertas | Segurança | Qualidade>
- **Prioridade / pontos:** <Alta | Média> · <n>
- **Requisitos da spec geral:** RF-xx, RNF-xx
- **Depende de:** US-xx

## História
Como **<papel>**, quero **<ação>** para **<benefício>**.

## Critérios de aceite
```gherkin
Cenário: <caminho feliz>
  Dado ...
  Quando ...
  Então ...

Cenário: <falha / borda>
  Dado ...
  Quando ...
  Então ...
```

## Casos de borda
- [ ] Serviço fora do ar durante a coleta
- [ ] Dado ausente ou vazio (ex.: log sem linhas novas)
- [ ] <outros>

## Fora do escopo desta história
- ...

## Dados e contratos afetados
- Tabelas: ...
- Métricas (`<servico>.<metrica>`): ...
- Telas / rotas: ...

## Segurança
- Entradas não confiáveis: ...
- Segredos envolvidos: ...

## Perguntas em aberto
- [ ] ...
