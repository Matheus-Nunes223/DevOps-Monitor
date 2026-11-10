begin;
select plan(7);

select is(
  (select count(*)::int from pg_catalog.pg_class c
   join pg_catalog.pg_namespace n on n.oid = c.relnamespace
   where n.nspname = 'public'
     and c.relname = any (array['services','metrics','service_status','alert_rules','alerts','security_events','vulnerabilities','config_baselines'])
     and c.relrowsecurity),
  8,
  'RLS is enabled on all eight public tables'
);

set local role anon;
select is((
  (select count(*) from public.services)
  + (select count(*) from public.metrics)
  + (select count(*) from public.service_status)
  + (select count(*) from public.alert_rules)
  + (select count(*) from public.alerts)
  + (select count(*) from public.security_events)
  + (select count(*) from public.vulnerabilities)
  + (select count(*) from public.config_baselines)
)::int, 0, 'anon cannot read rows from any monitored table');
reset role;

select set_config('request.jwt.claim.sub', '00000000-0000-0000-0000-000000000001', true);
set local role authenticated;
select is((select count(*)::int from public.services), 4, 'authenticated can read seeded services');
select throws_ok(
  $$insert into public.metrics (service_id, metric, value) values ('web', 'web.test', 1)$$,
  '42501',
  null,
  'authenticated cannot insert metrics'
);
select lives_ok(
  $$select public.accept_config_baseline('nginx.conf', '{}', '44136fa355b3678a1146ad16f7e8649e94fb4fc21fe77e8310c060f61caaff8a')$$,
  'authenticated can accept an allowlisted baseline through the RPC'
);
select is((select count(*)::int from public.config_baselines where path = 'nginx.conf'), 1, 'accepted baseline is stored');
select throws_ok(
  $$select public.accept_config_baseline('nginx.conf', 'not allowed', 'abc')$$,
  '22023',
  null,
  'authenticated cannot accept a baseline with an invalid hash'
);
reset role;

select * from finish();
rollback;
