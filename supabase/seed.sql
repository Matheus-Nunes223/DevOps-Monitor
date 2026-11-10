insert into public.services (id, name, host, current_level) values
  ('web', 'Web Server', 'nginx', 'green'),
  ('db', 'Banco de dados', 'postgres', 'green'),
  ('dns', 'DNS', 'coredns', 'green'),
  ('smtp', 'SMTP', 'postfix', 'green')
on conflict (id) do update set name = excluded.name, host = excluded.host;

-- `.up` represents consecutive failed checks, as clarified in US-02.
insert into public.alert_rules (service_id, metric, operator, warn_threshold, crit_threshold, consecutive_cycles) values
  ('web', 'web.up', '>=', 1, 2, 2),
  ('db', 'db.up', '>=', 1, 2, 2),
  ('dns', 'dns.up', '>=', 1, 2, 2),
  ('smtp', 'smtp.up', '>=', 1, 2, 2),
  ('web', 'web.latency_p95_ms', '>', 500, 2000, 2),
  ('web', 'web.error_5xx_rate', '>', 0.02, 0.10, 2),
  ('db', 'db.connections_ratio', '>', 0.70, 0.90, 2),
  ('db', 'db.slow_queries_per_min', '>', 5, 20, 2),
  ('db', 'db.cpu_percent', '>', 75, 95, 2),
  ('dns', 'dns.resolve_ms', '>', 100, 500, 2),
  ('dns', 'dns.failure_rate', '>', 0.05, 0.20, 2),
  ('smtp', 'smtp.queue_length', '>', 50, 200, 2),
  ('smtp', 'smtp.delivery_rate', '<', 0.95, 0.80, 2)
on conflict (service_id, metric) do update set
  operator = excluded.operator,
  warn_threshold = excluded.warn_threshold,
  crit_threshold = excluded.crit_threshold,
  consecutive_cycles = excluded.consecutive_cycles,
  enabled = true;
