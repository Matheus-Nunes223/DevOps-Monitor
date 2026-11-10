begin;
select plan(3);

insert into public.service_status (service_id, up, check_kind, latency_ms, error, collected_at) values
  ('web', true, 'protocol', 12, null, now() - interval '1 hour'),
  ('web', false, 'protocol', null, 'TimeoutError', now() - interval '30 minutes'),
  ('web', true, 'icmp', 3, null, now() - interval '1 hour'),
  ('web', false, 'icmp', null, null, now() - interval '30 minutes');

select set_config('request.jwt.claim.sub', '00000000-0000-0000-0000-000000000001', true);
set local role authenticated;

select is(
  (select count(*)::int from public.service_availability_24h('web')),
  2,
  'availability is returned separately for ICMP and protocol checks'
);
select is(
  (select availability_pct from public.service_availability_24h('web') where check_kind = 'protocol'),
  50.00::numeric,
  'protocol availability reflects measured UP checks only'
);
select is(
  (select availability_pct from public.service_availability_24h('web') where check_kind = 'icmp'),
  50.00::numeric,
  'ICMP availability reflects measured UP checks only'
);

select * from finish();
rollback;
