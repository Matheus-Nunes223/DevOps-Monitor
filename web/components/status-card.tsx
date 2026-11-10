import { Activity, AlertTriangle, CheckCircle2, CircleHelp, Database, Globe2, Mail } from "lucide-react";
import type { OverviewService } from "@/lib/overview";
import type { ServiceId, ServiceLevel } from "@/lib/supabase/types";

const serviceIcons = {
  web: Activity,
  db: Database,
  dns: Globe2,
  smtp: Mail,
} satisfies Record<ServiceId, typeof Activity>;

const levelLabels: Record<ServiceLevel | "unknown", string> = {
  green: "Operacional",
  yellow: "Degradado",
  red: "Crítico",
  unknown: "Sem dados",
};

function formatCheckTime(value: string | null) {
  if (!value) return "Sem checagens";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Horário indisponível";
  const timestamp = date.toISOString();
  return `${timestamp.slice(11, 19)} UTC`;
}

export function StatusCard({ service }: { service: OverviewService }) {
  const Icon = serviceIcons[service.id];
  const level = service.lastCheck || service.currentLevel !== "green"
    ? service.currentLevel
    : "unknown";
  const lastProbeLabel = service.protocolUp === null
    ? "Sem checagem de protocolo"
    : service.protocolUp
      ? "Última resposta: disponível"
      : "Última resposta: sem resposta";
  const ProbeIcon = service.protocolUp === true
    ? CheckCircle2
    : service.protocolUp === false
      ? AlertTriangle
      : CircleHelp;

  return (
    <article
      className={`status-card status-card-${level}`}
      data-service-id={service.id}
      aria-labelledby={`service-${service.id}-name`}
    >
      <div className="status-card-head">
        <span className={`status-card-icon status-card-icon-${service.id}`}><Icon size={17} aria-hidden="true" /></span>
        <span className={`level-pill level-pill-${level}`} data-testid={`level-${service.id}`}>
          <i aria-hidden="true" />{levelLabels[level]}
        </span>
      </div>
      <h2 id={`service-${service.id}-name`}>{service.name}</h2>
      <div className="status-card-metric">
        <span>Disponibilidade 24 h</span>
        <strong>{service.availability24h === null ? "—" : `${service.availability24h.toFixed(2)}%`}</strong>
      </div>
      <div className="status-card-foot">
        <span className={`probe-state ${service.protocolUp === true ? "probe-state-up" : ""} ${service.protocolUp === false ? "probe-state-down" : ""}`}>
          <ProbeIcon size={12} />
          {lastProbeLabel}
        </span>
        <span className="last-check">Última checagem: {formatCheckTime(service.lastCheck)}</span>
      </div>
    </article>
  );
}
