import { AlertCircle, AlertTriangle, BellRing, CheckCheck, CircleHelp } from "lucide-react";
import type { OverviewAlert } from "@/lib/overview";
import type { ServiceId } from "@/lib/supabase/types";

const serviceLabels: Record<ServiceId, string> = {
  web: "Web Server",
  db: "Banco de dados",
  dns: "DNS",
  smtp: "SMTP",
};

const kindLabels: Record<OverviewAlert["kind"], string> = {
  threshold: "Limite de métrica",
  availability: "Disponibilidade",
  ddos: "Anomalia de tráfego",
  bruteforce: "Brute-force",
  config_change: "Mudança de configuração",
  cve: "Vulnerabilidade",
};

function formatAlertTime(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Horário indisponível";
  const timestamp = date.toISOString();
  return `${timestamp.slice(8, 10)}/${timestamp.slice(5, 7)} ${timestamp.slice(11, 16)} UTC`;
}

export function AlertList({ alerts, loaded = true }: { alerts: OverviewAlert[]; loaded?: boolean }) {
  return (
    <section className="alerts-panel" aria-labelledby="active-alerts-title">
      <div className="alerts-panel-heading">
        <div>
          <span className="eyebrow">ACOMPANHAMENTO</span>
          <h2 id="active-alerts-title">Alertas ativos</h2>
        </div>
        <span className="alert-count">{loaded ? alerts.length : "—"}</span>
      </div>

      {!loaded ? (
        <div className="alerts-empty" role="status">
          <CircleHelp size={18} aria-hidden="true" />
          <span>Alertas indisponíveis</span>
          <small>Não foi possível consultar os alertas agora.</small>
        </div>
      ) : alerts.length === 0 ? (
        <div className="alerts-empty">
          <CheckCheck size={18} aria-hidden="true" />
          <span>Nenhum alerta ativo</span>
          <small>Alertas abertos serão listados aqui.</small>
        </div>
      ) : (
        <ul className="alert-items" aria-live="polite" aria-relevant="additions removals">
          {alerts.map((alert) => {
            const critical = alert.level === "red";
            const Icon = critical ? AlertCircle : AlertTriangle;
            return (
              <li className={`alert-item alert-item-${alert.level}`} key={alert.id} data-alert-id={alert.id}>
                <span className={`alert-item-icon alert-item-icon-${alert.level}`}><Icon size={16} aria-hidden="true" /></span>
                <div className="alert-item-copy">
                  <div className="alert-item-title-row">
                    <strong>{alert.message}</strong>
                    <span className={`alert-level-label alert-level-label-${alert.level}`}>
                      {critical ? "Crítico" : "Atenção"}
                    </span>
                  </div>
                  <span className="alert-item-meta">{serviceLabels[alert.service_id]} <i /> {kindLabels[alert.kind]}</span>
                  <time dateTime={alert.opened_at}>{formatAlertTime(alert.opened_at)}</time>
                </div>
              </li>
            );
          })}
        </ul>
      )}

      <div className="alerts-panel-foot"><BellRing size={13} /> Leitura autenticada no Supabase</div>
    </section>
  );
}
