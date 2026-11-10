import { AlertTriangle, ShieldAlert } from "lucide-react";
import { AcceptBaselineButton } from "@/components/accept-baseline-button";
import {
  configAlertDetails,
  eventLabels,
  groupVulnerabilities,
  severityOf,
  summarizeEvent,
  type SecurityEventType,
  type VulnerabilityRow,
} from "@/lib/security";
import type { AlertKind, Json, ServiceId } from "@/lib/supabase/types";

const serviceNames: Record<ServiceId, string> = { web: "Web Server", db: "Banco de dados", dns: "DNS", smtp: "SMTP" };
const kindNames: Partial<Record<AlertKind, string>> = { ddos: "Pico de tráfego", bruteforce: "Brute-force", config_change: "Configuração", cve: "Vulnerabilidade" };

function utc(value: string) {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "—" : `${date.toISOString().slice(0, 16).replace("T", " ")} UTC`;
}

export type SecurityAlert = { id: number; service_id: ServiceId; kind: AlertKind; level: "yellow" | "red"; message: string; details: Json; opened_at: string };
export type SecurityEventRow = { id: number; service_id: ServiceId; type: SecurityEventType; details: Json; detected_at: string };

export function OpenSecurityAlerts({ alerts, error }: { alerts: SecurityAlert[]; error: boolean }) {
  return (
    <section className="history-panel" aria-labelledby="sec-alerts-title">
      <div className="history-heading"><div><span className="eyebrow">AGORA</span><h2 id="sec-alerts-title">Alertas de segurança abertos</h2></div><span>{error ? "—" : alerts.length}</span></div>
      {error ? <p className="metric-empty" role="status">Alertas indisponíveis no momento.</p> : alerts.length === 0 ? <p className="metric-empty">Nenhum alerta de segurança aberto.</p> : (
        <ul className="history-items">
          {alerts.map((alert) => {
            const config = alert.kind === "config_change" ? configAlertDetails(alert.details) : null;
            return (
              <li className="history-item history-item-block" key={alert.id}>
                <span className={`history-level history-level-${alert.level}`} aria-label={alert.level === "red" ? "Crítico" : "Atenção"} />
                <div>
                  <strong>{alert.message}</strong>
                  <span>{serviceNames[alert.service_id]} · {kindNames[alert.kind] ?? alert.kind}</span>
                  {config && config.diff && <pre className="diff-block" aria-label={`Diferenças em ${config.path}`}>{config.diff}</pre>}
                  {config && <AcceptBaselineButton alertId={alert.id} disabled={!config.canAccept} />}
                </div>
                <time dateTime={alert.opened_at}>{utc(alert.opened_at)}</time>
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}

export function SecurityEventList({ events, error }: { events: SecurityEventRow[]; error: boolean }) {
  return (
    <section className="history-panel" aria-labelledby="sec-events-title">
      <div className="history-heading"><div><span className="eyebrow">HISTÓRICO</span><h2 id="sec-events-title">Eventos de segurança</h2></div><span>{error ? "—" : events.length}</span></div>
      {error ? <p className="metric-empty" role="status">Eventos indisponíveis no momento.</p> : events.length === 0 ? <p className="metric-empty">Nenhum evento detectado.</p> : (
        <ul className="history-items">
          {events.map((event) => (
            <li className="history-item" key={event.id}>
              <ShieldAlert size={15} aria-hidden="true" className="event-icon" />
              <div><strong>{eventLabels[event.type]}</strong><span>{serviceNames[event.service_id]} · {summarizeEvent(event.type, event.details)}</span></div>
              <time dateTime={event.detected_at}>{utc(event.detected_at)}</time>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

export function VulnerabilityTable({ rows, error }: { rows: VulnerabilityRow[]; error: boolean }) {
  const groups = groupVulnerabilities(rows);
  return (
    <section className="history-panel" aria-labelledby="vuln-title">
      <div className="history-heading"><div><span className="eyebrow">NVD · CONSULTA DIÁRIA</span><h2 id="vuln-title">Vulnerabilidades conhecidas por serviço</h2></div><span>{error ? "—" : rows.length}</span></div>
      {error ? <p className="metric-empty" role="status">Vulnerabilidades indisponíveis no momento.</p> : groups.length === 0 ? <p className="metric-empty">Nenhuma vulnerabilidade registrada. A primeira consulta ao NVD ocorre logo após o coletor iniciar.</p> : (
        groups.map((group) => (
          <div className="vuln-group" key={group.serviceId}>
            <h3>{serviceNames[group.serviceId]} <small>versão {group.version} · checado em {utc(group.checkedAt)}</small>
              {group.highCount > 0 && <span className="level-pill level-pill-yellow"><AlertTriangle size={11} aria-hidden="true" /> {group.highCount} com CVSS ≥ 7,0</span>}
            </h3>
            <div className="table-scroll">
              <table className="vuln-table">
                <thead><tr><th scope="col">CVE</th><th scope="col">CVSS</th><th scope="col">Resumo</th></tr></thead>
                <tbody>
                  {group.rows.slice(0, 15).map((row) => (
                    <tr key={row.id}>
                      <td><code>{row.cve_id}</code></td>
                      <td><span className={`cvss cvss-${severityOf(row.cvss)}`}>{row.cvss === null ? "—" : row.cvss.toFixed(1)}</span></td>
                      <td>{row.summary ?? "Sem descrição."}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {group.rows.length > 15 && <p className="metric-sample-note">Mostrando 15 de {group.rows.length} (ordenadas por CVSS).</p>}
          </div>
        ))
      )}
    </section>
  );
}
