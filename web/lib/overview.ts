import type { SupabaseClient } from "@supabase/supabase-js";
import type { AlertRow, Database, ServiceId, ServiceLevel, ServiceRow, ServiceStatusRow } from "@/lib/supabase/types";

export type OverviewService = {
  id: ServiceId;
  name: string;
  currentLevel: ServiceLevel;
  protocolUp: boolean | null;
  lastCheck: string | null;
  availability24h: number | null;
  availabilityChecks: number;
};

export type OverviewAlert = Pick<
  AlertRow,
  "id" | "service_id" | "kind" | "level" | "message" | "opened_at" | "status"
>;

export type OverviewSnapshot = {
  services: OverviewService[];
  activeAlerts: OverviewAlert[];
  error: string | null;
  servicesLoaded: boolean;
  alertsLoaded: boolean;
};

export type OverviewSourceData = {
  services: Pick<ServiceRow, "id" | "name" | "current_level">[];
  statuses: Pick<ServiceStatusRow, "id" | "service_id" | "check_kind" | "up" | "collected_at">[];
  availability: Database["public"]["Functions"]["service_availability_24h"]["Returns"];
  alerts: OverviewAlert[];
};

const SERVICE_ORDER: Record<ServiceId, number> = {
  web: 0,
  db: 1,
  dns: 2,
  smtp: 3,
};

export function buildOverviewSnapshot(source: OverviewSourceData): OverviewSnapshot {
  const latestProtocolCheck = new Map<ServiceId, OverviewSourceData["statuses"][number]>();
  const sortedChecks = [...source.statuses]
    .filter((status) => status.check_kind === "protocol")
    .sort((left, right) => Date.parse(right.collected_at) - Date.parse(left.collected_at));

  for (const status of sortedChecks) {
    if (!latestProtocolCheck.has(status.service_id)) {
      latestProtocolCheck.set(status.service_id, status);
    }
  }

  const protocolAvailability = new Map<ServiceId, { percentage: number; count: number }>();
  for (const item of source.availability) {
    if (item.check_kind === "protocol" && item.check_count > 0 && item.availability_pct !== null) {
      protocolAvailability.set(item.service_id, {
        percentage: item.availability_pct,
        count: item.check_count,
      });
    }
  }

  const services = [...source.services]
    .sort((left, right) => SERVICE_ORDER[left.id] - SERVICE_ORDER[right.id])
    .map((service): OverviewService => {
      const latest = latestProtocolCheck.get(service.id);
      const availability = protocolAvailability.get(service.id);
      return {
        id: service.id,
        name: service.name,
        currentLevel: service.current_level,
        protocolUp: latest?.up ?? null,
        lastCheck: latest?.collected_at ?? null,
        availability24h: availability?.percentage ?? null,
        availabilityChecks: availability?.count ?? 0,
      };
    });

  const activeAlerts = source.alerts
    .filter((alert) => alert.status === "open")
    .sort((left, right) => Date.parse(right.opened_at) - Date.parse(left.opened_at));

  return {
    services,
    activeAlerts,
    error: null,
    servicesLoaded: true,
    alertsLoaded: true,
  };
}

export function applyServiceRow(
  services: OverviewService[],
  row: Pick<ServiceRow, "id" | "name" | "current_level">,
  event: "INSERT" | "UPDATE" | "DELETE",
): OverviewService[] {
  if (event === "DELETE") return services.filter((service) => service.id !== row.id);

  const existing = services.find((service) => service.id === row.id);
  if (existing) {
    return services.map((service) =>
      service.id === row.id ? { ...service, name: row.name, currentLevel: row.current_level } : service,
    );
  }

  return [
    ...services,
    {
      id: row.id,
      name: row.name,
      currentLevel: row.current_level,
      protocolUp: null,
      lastCheck: null,
      availability24h: null,
      availabilityChecks: 0,
    },
  ].sort((left, right) => SERVICE_ORDER[left.id] - SERVICE_ORDER[right.id]);
}

export function applyProtocolStatus(
  services: OverviewService[],
  status: Pick<ServiceStatusRow, "service_id" | "check_kind" | "up" | "collected_at">,
): OverviewService[] {
  if (status.check_kind !== "protocol") return services;
  return services.map((service) => {
    if (service.id !== status.service_id) return service;
    if (service.lastCheck && Date.parse(status.collected_at) < Date.parse(service.lastCheck)) {
      return service;
    }
    return { ...service, protocolUp: status.up, lastCheck: status.collected_at };
  });
}

export function applyAvailability(
  services: OverviewService[],
  serviceId: ServiceId,
  result: Database["public"]["Functions"]["service_availability_24h"]["Returns"][number] | undefined,
): OverviewService[] {
  const availability = result?.check_kind === "protocol" && result.check_count > 0
    ? { percentage: result.availability_pct, count: result.check_count }
    : null;

  return services.map((service) =>
    service.id === serviceId
      ? {
          ...service,
          availability24h: availability?.percentage ?? null,
          availabilityChecks: availability?.count ?? 0,
        }
      : service,
  );
}

export function applyAlertRow(
  alerts: OverviewAlert[],
  alert: OverviewAlert,
  event: "INSERT" | "UPDATE" | "DELETE",
): OverviewAlert[] {
  if (event === "DELETE" || alert.status !== "open") {
    return alerts.filter((item) => item.id !== alert.id);
  }

  return [alert, ...alerts.filter((item) => item.id !== alert.id)]
    .sort((left, right) => Date.parse(right.opened_at) - Date.parse(left.opened_at));
}

export async function readOverviewSnapshot(
  supabase: SupabaseClient<Database>,
): Promise<OverviewSnapshot> {
  try {
    const [servicesResult, statusResult, availabilityResult, alertsResult] = await Promise.all([
      supabase.from("services").select("id, name, current_level"),
      supabase
        .from("service_status")
        .select("id, service_id, check_kind, up, collected_at")
        .order("collected_at", { ascending: false })
        .limit(200),
      supabase.rpc("service_availability_24h", { p_service_id: null }),
      supabase
        .from("alerts")
        .select("id, service_id, kind, level, message, opened_at, status")
        .eq("status", "open")
        .order("opened_at", { ascending: false })
        .limit(100),
    ]);

    const queryErrors = [
      servicesResult.error,
      statusResult.error,
      availabilityResult.error,
      alertsResult.error,
    ].filter((error) => error !== null);

    if (queryErrors.length > 0) {
      console.error(
        "[overview] Supabase query failure",
        queryErrors.map(({ code }) => code),
      );
    }

    const snapshot = buildOverviewSnapshot({
      services: servicesResult.data ?? [],
      statuses: statusResult.data ?? [],
      availability: availabilityResult.data ?? [],
      alerts: (alertsResult.data ?? []) as OverviewAlert[],
    });

    return {
      ...snapshot,
      servicesLoaded: servicesResult.error === null,
      alertsLoaded: alertsResult.error === null,
      error:
        queryErrors.length > 0
          ? "Parte dos dados não pôde ser carregada. A lista será atualizada quando a conexão voltar."
          : null,
    };
  } catch (error) {
    console.error("[overview] Supabase request failed", error instanceof Error ? error.name : "unknown");
    return {
      services: [],
      activeAlerts: [],
      error: "Não foi possível carregar os dados do painel. A conexão será atualizada quando voltar.",
      servicesLoaded: false,
      alertsLoaded: false,
    };
  }
}
