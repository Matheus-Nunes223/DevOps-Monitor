-- US-02: core schema for the DevOps Monitor.
create schema if not exists extensions;
create extension if not exists pgcrypto with schema extensions;
create extension if not exists pgtap with schema extensions;
create extension if not exists pg_cron with schema pg_catalog;

create table public.services (
  id text primary key check (id in ('web', 'db', 'dns', 'smtp')),
  name text not null,
  host text not null,
  current_level text not null default 'green'
    check (current_level in ('green', 'yellow', 'red'))
);

create table public.metrics (
  id bigint generated always as identity primary key,
  service_id text not null references public.services(id),
  metric text not null,
  value double precision,
  labels jsonb not null default '{}'::jsonb,
  collected_at timestamptz not null default now()
);
create index metrics_lookup on public.metrics (service_id, metric, collected_at desc);

create table public.service_status (
  id bigint generated always as identity primary key,
  service_id text not null references public.services(id),
  up boolean not null,
  check_kind text not null check (check_kind in ('icmp', 'protocol')),
  latency_ms double precision check (latency_ms is null or latency_ms >= 0),
  error text,
  collected_at timestamptz not null default now()
);
create index status_lookup on public.service_status (service_id, collected_at desc);

create table public.alert_rules (
  id bigint generated always as identity primary key,
  service_id text not null references public.services(id),
  metric text not null,
  operator text not null check (operator in ('>', '<', '>=')),
  warn_threshold double precision not null,
  crit_threshold double precision not null,
  consecutive_cycles integer not null default 2 check (consecutive_cycles > 0),
  enabled boolean not null default true,
  unique (service_id, metric),
  check (
    (operator = '>' and warn_threshold <= crit_threshold)
    or (operator = '>=' and warn_threshold <= crit_threshold)
    or (operator = '<' and warn_threshold >= crit_threshold)
  )
);

create table public.alerts (
  id bigint generated always as identity primary key,
  rule_id bigint references public.alert_rules(id),
  service_id text not null references public.services(id),
  kind text not null check (kind in ('threshold', 'availability', 'ddos', 'bruteforce', 'config_change', 'cve')),
  level text not null check (level in ('yellow', 'red')),
  status text not null default 'open' check (status in ('open', 'resolved')),
  value double precision,
  message text not null,
  details jsonb not null default '{}'::jsonb,
  opened_at timestamptz not null default now(),
  resolved_at timestamptz,
  last_notified_at timestamptz
);
create index alerts_open on public.alerts (status, opened_at desc);
create index alerts_service_history on public.alerts (service_id, opened_at desc);

create table public.security_events (
  id bigint generated always as identity primary key,
  service_id text not null references public.services(id),
  type text not null check (type in ('ddos', 'bruteforce', 'config_change')),
  details jsonb not null,
  detected_at timestamptz not null default now()
);
create index security_events_history on public.security_events (service_id, detected_at desc);

create table public.vulnerabilities (
  id bigint generated always as identity primary key,
  service_id text not null references public.services(id),
  product_version text not null,
  cve_id text not null,
  cvss numeric(3, 1) check (cvss is null or cvss between 0 and 10),
  summary text,
  published_at timestamptz,
  checked_at timestamptz not null default now(),
  unique (service_id, cve_id)
);
create index vulnerabilities_history on public.vulnerabilities (service_id, checked_at desc);

create table public.config_baselines (
  path text primary key check (path in ('nginx.conf', 'Corefile', 'postgresql.conf', 'main.cf')),
  service_id text not null references public.services(id),
  sha256 text not null check (sha256 ~ '^[0-9a-f]{64}$'),
  content text not null,
  accepted_at timestamptz not null default now()
);

revoke create on schema public from public, anon, authenticated;
grant usage on schema public to anon, authenticated, service_role;

-- Enable row-level security on every exposed table. Anon may issue SELECT,
-- but has no matching policy and therefore receives no rows. Only authenticated
-- users get read policies. The collector's service_role writes through RLS bypass.
do $rls$
declare
  table_name text;
begin
  foreach table_name in array array[
    'services', 'metrics', 'service_status', 'alert_rules', 'alerts',
    'security_events', 'vulnerabilities', 'config_baselines'
  ] loop
    execute format('alter table public.%I enable row level security', table_name);
    execute format(
      'create policy authenticated_read on public.%I for select to authenticated using (true)',
      table_name
    );
    execute format('revoke all on public.%I from public, anon, authenticated', table_name);
    execute format('grant select on public.%I to anon, authenticated', table_name);
    execute format('grant select, insert, update, delete on public.%I to service_role', table_name);
  end loop;
end
$rls$;
grant usage, select on all sequences in schema public to service_role;

-- Valid ranges are deliberately bounded; empty buckets remain NULL instead of
-- being displayed as fabricated zero measurements. SECURITY INVOKER preserves RLS.
create or replace function public.metric_series(
  p_service text,
  p_metric text,
  p_range interval
)
returns table (bucket timestamptz, value double precision, sample_count bigint)
language plpgsql
stable
security invoker
set search_path = ''
as $function$
declare
  bucket_size interval;
begin
  if p_range is null or p_range not in (interval '1 hour', interval '6 hours', interval '24 hours') then
    raise exception using errcode = '22023', message = 'range must be 1, 6, or 24 hours';
  end if;

  bucket_size := case p_range
    when interval '1 hour' then interval '1 minute'
    when interval '6 hours' then interval '5 minutes'
    else interval '15 minutes'
  end;

  return query
    with bounds as (
      select pg_catalog.date_bin(bucket_size, now() - p_range, timestamptz '2000-01-01') as first_bucket,
             pg_catalog.date_bin(bucket_size, now(), timestamptz '2000-01-01') as last_bucket
    ), buckets as (
      select generated.bucket
      from bounds b
      cross join lateral pg_catalog.generate_series(b.first_bucket, b.last_bucket, bucket_size) as generated(bucket)
    )
    select b.bucket,
           pg_catalog.avg(m.value)::double precision,
           pg_catalog.count(m.id)::bigint
    from buckets b
    left join public.metrics m
      on m.service_id = p_service
     and m.metric = p_metric
     and m.collected_at >= now() - p_range
     and m.collected_at < now()
     and pg_catalog.date_bin(bucket_size, m.collected_at, timestamptz '2000-01-01') = b.bucket
    group by b.bucket
    order by b.bucket;
end
$function$;
revoke all on function public.metric_series(text, text, interval) from public, anon;
grant execute on function public.metric_series(text, text, interval) to authenticated;

-- This is the only browser-side write. The path is an allowlist, content is
-- bounded, and the digest is computed by Postgres rather than trusted from UI.
create or replace function public.accept_config_baseline(
  p_path text,
  p_content text,
  p_sha256 text
)
returns void
language plpgsql
security definer
set search_path = ''
as $function$
declare
  target_service text;
  actual_sha256 text;
begin
  if auth.uid() is null then
    raise exception using errcode = '42501', message = 'authenticated user required';
  end if;
  target_service := case p_path
    when 'nginx.conf' then 'web'
    when 'Corefile' then 'dns'
    when 'postgresql.conf' then 'db'
    when 'main.cf' then 'smtp'
    else null
  end;
  if target_service is null then
    raise exception using errcode = '22023', message = 'path is not an accepted configuration file';
  end if;
  if p_content is null or pg_catalog.octet_length(p_content) > 1048576 then
    raise exception using errcode = '22023', message = 'content is missing or exceeds 1 MiB';
  end if;
  actual_sha256 := pg_catalog.encode(extensions.digest(pg_catalog.convert_to(p_content, 'UTF8'), 'sha256'), 'hex');
  if p_sha256 is distinct from actual_sha256 then
    raise exception using errcode = '22023', message = 'provided SHA-256 does not match content';
  end if;

  insert into public.config_baselines (path, service_id, sha256, content, accepted_at)
  values (p_path, target_service, actual_sha256, p_content, now())
  on conflict (path) do update
    set service_id = excluded.service_id,
        sha256 = excluded.sha256,
        content = excluded.content,
        accepted_at = excluded.accepted_at;

  update public.alerts
  set status = 'resolved', resolved_at = now()
  where service_id = target_service
    and kind = 'config_change'
    and status = 'open'
    and details ->> 'path' = p_path;
end
$function$;
revoke all on function public.accept_config_baseline(text, text, text) from public, anon;
grant execute on function public.accept_config_baseline(text, text, text) to authenticated;

-- Retention job removes data older than seven days. The function is callable by
-- the scheduler only; it is not exposed to anon/authenticated clients.
create or replace function public.purge_old_monitoring_data()
returns void
language plpgsql
security definer
set search_path = ''
as $function$
begin
  delete from public.metrics where collected_at < now() - interval '7 days';
  delete from public.service_status where collected_at < now() - interval '7 days';
end
$function$;
revoke all on function public.purge_old_monitoring_data() from public, anon, authenticated;
do $retention$
declare
  old_job record;
begin
  for old_job in select jobid from cron.job where jobname = 'devops-monitor-retention-7d' loop
    perform cron.unschedule(old_job.jobid);
  end loop;
  perform cron.schedule('devops-monitor-retention-7d', '0 3 * * *', 'select public.purge_old_monitoring_data();');
end
$retention$;

-- Realtime publication exists in managed and local Supabase installations.
do $realtime$
declare
  table_name text;
begin
  if not exists (select 1 from pg_catalog.pg_publication where pubname = 'supabase_realtime') then
    raise exception 'supabase_realtime publication is missing';
  end if;
  foreach table_name in array array['alerts', 'service_status', 'services'] loop
    if not exists (
      select 1 from pg_catalog.pg_publication_tables
      where pubname = 'supabase_realtime' and schemaname = 'public' and tablename = table_name
    ) then
      execute format('alter publication supabase_realtime add table public.%I', table_name);
    end if;
  end loop;
end
$realtime$;
