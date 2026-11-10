-- US-04 / T-041: measured availability by service and check type.
-- Missing checks are absent from the denominator; no synthetic UP/DOWN rows are added.
create or replace function public.service_availability_24h(p_service_id text default null)
returns table (
  service_id text,
  check_kind text,
  availability_pct numeric,
  check_count bigint
)
language sql
stable
security invoker
set search_path = ''
as $function$
  select s.service_id,
         s.check_kind,
         round(
           100.0 * count(*) filter (where s.up)::numeric / nullif(count(*), 0),
           2
         ) as availability_pct,
         count(*)::bigint as check_count
  from public.service_status as s
  where s.collected_at >= pg_catalog.now() - interval '24 hours'
    and s.collected_at < pg_catalog.now()
    and (p_service_id is null or s.service_id = p_service_id)
  group by s.service_id, s.check_kind
  order by s.service_id, s.check_kind;
$function$;

revoke all on function public.service_availability_24h(text) from public, anon;
grant execute on function public.service_availability_24h(text) to authenticated;
