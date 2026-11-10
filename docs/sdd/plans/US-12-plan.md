# Plano · US-12 · Dashboards por serviço

- **Spec:** `docs/sdd/features/US-12.md`
- **Dados:** função `metric_series(text, text, interval)` e tabela `alerts` da migration base.
- **Métricas:** catálogo reconciliado com os nomes emitidos em `collector/src/monitor/probes/`.

## Implementação
- criar catálogo tipado de serviços, rótulos e unidades.
- criar componente SVG de série temporal sem dependência de dados inventados.
- criar filtro de período via query string (1 h, 6 h, 24 h).
- criar página server-side com consultas autenticadas para séries e histórico.
- ativar links na navegação e adaptar layout para mobile.

## Limitações de validação
- Consulta real e qualidade dos gráficos com dados do coletor dependem de um projeto Supabase configurado e com migrations aplicadas.
