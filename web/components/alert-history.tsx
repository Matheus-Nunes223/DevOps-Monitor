import type { OverviewAlert } from "@/lib/overview";

const serviceNames = { web: "Web Server", db: "Banco de dados", dns: "DNS", smtp: "SMTP" } as const;

export function AlertHistory({ alerts, error }: { alerts: OverviewAlert[]; error: boolean }) {
  return (
    <section className="history-panel" aria-labelledby="alert-history-title">
      <div className="history-heading"><div><span className="eyebrow">EVENTOS</span><h2 id="alert-history-title">Histórico de alertas</h2></div><span>{error ? "—" : alerts.length}</span></div>
      {error ? <p className="metric-empty" role="status">Histórico indisponível no momento.</p> : alerts.length === 0 ? <p className="metric-empty">Nenhum alerta no período consultado.</p> : (
        <ul className="history-items">
          {alerts.map((alert) => (
            <li className="history-item" key={alert.id}>
              <span className={`history-level history-level-${alert.level}`} aria-label={alert.level === "red" ? "Crítico" : "Atenção"} />
              <div><strong>{alert.message}</strong><span>{serviceNames[alert.service_id]} · {alert.status === "open" ? "Aberto" : "Resolvido"}</span></div>
              <time dateTime={alert.opened_at}>{new Date(alert.opened_at).toISOString().slice(0, 16).replace("T", " ")} UTC</time>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
