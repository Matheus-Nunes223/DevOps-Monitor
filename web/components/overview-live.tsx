"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { AlertTriangle, CircleCheck, RadioTower, RefreshCw } from "lucide-react";
import {
  applyAlertRow,
  applyAvailability,
  applyProtocolStatus,
  applyServiceRow,
  type OverviewSnapshot,
  type OverviewService,
} from "@/lib/overview";
import { AlertList } from "@/components/alert-list";
import { StatusCard } from "@/components/status-card";
import { createClient } from "@/lib/supabase/client";
import type { AlertRow, ServiceId, ServiceRow, ServiceStatusRow } from "@/lib/supabase/types";

type ConnectionState = "connecting" | "connected" | "error";

function replaceAvailability(
  current: OverviewService[],
  serviceId: ServiceId,
  row: Parameters<typeof applyAvailability>[2],
) {
  return applyAvailability(current, serviceId, row);
}

export function OverviewLive({ initial }: { initial: OverviewSnapshot }) {
  const router = useRouter();
  const [services, setServices] = useState(initial.services);
  const [alerts, setAlerts] = useState(initial.activeAlerts);
  const [servicesLoaded, setServicesLoaded] = useState(initial.servicesLoaded);
  const [alertsLoaded, setAlertsLoaded] = useState(initial.alertsLoaded);
  const [connection, setConnection] = useState<ConnectionState>("connecting");
  const [availabilityRefreshFailed, setAvailabilityRefreshFailed] = useState(false);

  useEffect(() => {
    setServices(initial.services);
    setAlerts(initial.activeAlerts);
    setServicesLoaded(initial.servicesLoaded);
    setAlertsLoaded(initial.alertsLoaded);
  }, [initial]);

  useEffect(() => {
    let active = true;
    let supabase: ReturnType<typeof createClient>;
    const availabilityTimers = new Map<ServiceId, ReturnType<typeof setTimeout>>();

    try {
      supabase = createClient();
    } catch {
      setConnection("error");
      return;
    }

    const refreshAvailability = async (serviceId: ServiceId) => {
      const { data, error } = await supabase.rpc("service_availability_24h", {
        p_service_id: serviceId,
      });
      if (!active) return;
      if (error) {
        console.error("[overview] Realtime availability refresh failed", error.code);
        setAvailabilityRefreshFailed(true);
        return;
      }
      setAvailabilityRefreshFailed(false);
      const protocolRow = data?.find((item) => item.check_kind === "protocol");
      setServices((current) => replaceAvailability(current, serviceId, protocolRow));
    };

    const scheduleAvailabilityRefresh = (serviceId: ServiceId) => {
      const existingTimer = availabilityTimers.get(serviceId);
      if (existingTimer) clearTimeout(existingTimer);
      availabilityTimers.set(
        serviceId,
        setTimeout(() => {
          availabilityTimers.delete(serviceId);
          void refreshAvailability(serviceId);
        }, 250),
      );
    };

    const channel = supabase
      .channel("overview-live")
      .on(
        "postgres_changes",
        { event: "*", schema: "public", table: "services" },
        (payload) => {
          if (payload.eventType === "DELETE") {
            const removed = payload.old as Partial<ServiceRow>;
            if (removed.id) {
              setServices((current) => current.filter((service) => service.id !== removed.id));
              setServicesLoaded(true);
            }
            return;
          }
          setServices((current) =>
            applyServiceRow(current, payload.new as ServiceRow, payload.eventType),
          );
          setServicesLoaded(true);
        },
      )
      .on(
        "postgres_changes",
        { event: "*", schema: "public", table: "service_status" },
        (payload) => {
          if (payload.eventType === "DELETE") {
            router.refresh();
            return;
          }
          const status = payload.new as ServiceStatusRow;
          setServices((current) => applyProtocolStatus(current, status));
          if (status.check_kind === "protocol") {
            scheduleAvailabilityRefresh(status.service_id);
          }
        },
      )
      .on(
        "postgres_changes",
        { event: "*", schema: "public", table: "alerts" },
        (payload) => {
          const alert = (payload.eventType === "DELETE" ? payload.old : payload.new) as AlertRow;
          setAlerts((current) => applyAlertRow(current, alert, payload.eventType));
          setAlertsLoaded(true);
        },
      )
      .subscribe((status) => {
        if (!active) return;
        if (status === "SUBSCRIBED") {
          setConnection("connected");
          router.refresh();
        } else if (status === "CHANNEL_ERROR" || status === "TIMED_OUT" || status === "CLOSED") {
          setConnection("error");
        }
      });

    return () => {
      active = false;
      availabilityTimers.forEach((timer) => clearTimeout(timer));
      void supabase.removeChannel(channel);
    };
  }, [router]);

  return (
    <div className="overview-live">
      <div className="page-heading">
        <div>
          <div className="eyebrow"><span /> WORKSPACE / OVERVIEW</div>
          <h1>Visão geral</h1>
          <p>Saúde e atividade da infraestrutura monitorada.</p>
        </div>
        <span className="page-chip"><RadioTower size={15} /> Painel autenticado</span>
      </div>

      {initial.error && (
        <div className="overview-warning" role="alert">
          <AlertTriangle size={16} /> {initial.error}
        </div>
      )}
      {availabilityRefreshFailed && (
        <div className="overview-warning" role="alert">
          <AlertTriangle size={16} /> A disponibilidade 24 h não pôde ser atualizada; o último valor conhecido foi mantido.
        </div>
      )}

      <div className={`realtime-status realtime-status-${connection}`} role="status" aria-live="polite">
        {connection === "connected" ? <CircleCheck size={14} /> : <RefreshCw size={13} />}
        <span>
          {connection === "connected"
            ? "Atualizações em tempo real ativas"
            : connection === "connecting"
              ? "Conectando às atualizações em tempo real…"
              : "Atualização ao vivo indisponível; tentando reconectar"}
        </span>
      </div>

      {servicesLoaded && services.length > 0 ? (
        <section className="status-grid" aria-label="Status dos serviços">
          {services.map((service) => <StatusCard key={service.id} service={service} />)}
        </section>
      ) : servicesLoaded ? (
        <section className="overview-empty" aria-label="Sem serviços">
          <RadioTower size={21} />
          <h2>Sem serviços cadastrados</h2>
          <p>Os cartões aparecerão quando a tabela de serviços tiver dados.</p>
        </section>
      ) : (
        <section className="overview-empty" aria-label="Serviços indisponíveis">
          <AlertTriangle size={21} />
          <h2>Serviços temporariamente indisponíveis</h2>
          <p>Não foi possível consultar a tabela de serviços.</p>
        </section>
      )}

      <AlertList alerts={alerts} loaded={alertsLoaded} />
    </div>
  );
}
