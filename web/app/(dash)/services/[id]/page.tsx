import { notFound } from "next/navigation";
import { AlertTriangle, ChevronLeft, Gauge } from "lucide-react";
import Link from "next/link";
import { AlertHistory } from "@/components/alert-history";
import { MetricChart, type MetricPoint } from "@/components/metric-chart";
import { RangeFilter } from "@/components/range-filter";
import { metricRanges, parseMetricRange, scalePoints, serviceCatalog } from "@/lib/service-dashboard";
import { AvailabilityPanel } from "@/components/availability-panel";
import { StatusCodeTable } from "@/components/status-code-table";
import { sumStatusCodes, type StatusCountRow } from "@/lib/status-codes";
import { createClient } from "@/lib/supabase/server";
import type { ServiceId } from "@/lib/supabase/types";
import type { OverviewAlert } from "@/lib/overview";

const serviceIds = Object.keys(serviceCatalog) as ServiceId[];

export default async function ServiceDashboardPage({
  params,
  searchParams,
}: {
  params: Promise<{ id: string }>;
  searchParams: Promise<{ range?: string }>;
}) {
  const [{ id }, query] = await Promise.all([params, searchParams]);
  if (!serviceIds.includes(id as ServiceId)) notFound();
  const serviceId = id as ServiceId;
  const service = serviceCatalog[serviceId];
  const range = parseMetricRange(query.range);
  const supabase = await createClient();

  const seriesRequests = service.metrics.map(async (metric) => {
    const { data, error } = await supabase.rpc("metric_series", {
      p_service: serviceId,
      p_metric: metric.key,
      p_range: range,
    });
    return [metric.key, { data: scalePoints((data ?? []) as MetricPoint[], metric.scale), error: Boolean(error) }] as const;
  });

  const hours = range === "24 hours" ? 24 : range === "6 hours" ? 6 : 1;
  const statusCodes = serviceId === "web"
    ? await supabase
        .from("metrics")
        .select("value, labels")
        .eq("service_id", "web")
        .eq("metric", "web.status_count")
        .gte("collected_at", new Date(Date.now() - hours * 3600_000).toISOString())
        .limit(20000)
    : null;
  const [availabilityResult, recentResult] = await Promise.all([
    supabase.rpc("service_availability_24h", { p_service_id: serviceId }),
    supabase
      .from("service_status")
      .select("check_kind, up, latency_ms, error, collected_at")
      .eq("service_id", serviceId)
      .order("collected_at", { ascending: false })
      .limit(20),
  ]);
  const [seriesResults, alertResult] = await Promise.all([
    Promise.all(seriesRequests),
    supabase
      .from("alerts")
      .select("id, service_id, kind, level, message, opened_at, status")
      .eq("service_id", serviceId)
      .order("opened_at", { ascending: false })
      .limit(100),
  ]);
  const series = new Map(seriesResults);
  const alerts = (alertResult.data ?? []) as OverviewAlert[];

  return (
    <div className="service-dashboard">
      <Link className="back-link" href="/"><ChevronLeft size={15} /> Visão geral</Link>
      <div className="page-heading service-page-heading">
        <div>
          <div className="eyebrow"><span /> MONITORAMENTO / {serviceId.toUpperCase()}</div>
          <h1>{service.name}</h1>
          <p>{service.description}</p>
        </div>
        <span className="page-chip"><Gauge size={15} /> Dados medidos</span>
      </div>

      <div className="service-toolbar">
        <div><span className="eyebrow">SÉRIES TEMPORAIS</span><p>Agregação por bucket · horários em UTC</p></div>
        <RangeFilter serviceId={serviceId} range={range} />
      </div>

      <AvailabilityPanel
        availability={(availabilityResult.data ?? []) as { check_kind: "icmp" | "protocol"; availability_pct: number | null; check_count: number }[]}
        recent={(recentResult.data ?? []) as never}
        error={Boolean(availabilityResult.error || recentResult.error)}
      />
      {seriesResults.some(([, result]) => result.error) && (
        <div className="overview-warning" role="alert"><AlertTriangle size={16} /> Algumas séries não puderam ser consultadas; os demais dados continuam disponíveis.</div>
      )}
      <section className="metric-grid" aria-label={`Métricas de ${service.name}`}>
        {service.metrics.map((metric) => {
          const result = series.get(metric.key);
          return <MetricChart key={metric.key} title={metric.label} unit={metric.unit} data={result?.data ?? []} error={result?.error ?? true} />;
        })}
      </section>

      {statusCodes && <StatusCodeTable counts={sumStatusCodes((statusCodes.data ?? []) as StatusCountRow[])} error={Boolean(statusCodes.error)} />}
      <AlertHistory alerts={alerts} error={Boolean(alertResult.error)} />
      <p className="service-data-note">Período selecionado: {metricRanges[range]}. Valores e amostras vêm exclusivamente do Supabase.</p>
    </div>
  );
}
