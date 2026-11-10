import type { ServiceStatusRow } from "@/lib/supabase/types";

type Availability = { check_kind: "icmp" | "protocol"; availability_pct: number | null; check_count: number };
type LastCheck = Pick<ServiceStatusRow, "check_kind" | "up" | "latency_ms" | "error" | "collected_at">;

const kindLabels = { protocol: "Protocolo (HTTP / SQL / DNS / EHLO)", icmp: "Ping (ICMP)" } as const;

export function pickLatest(rows: LastCheck[], kind: LastCheck["check_kind"]): LastCheck | null {
  return rows.filter((row) => row.check_kind === kind).sort((a, b) => b.collected_at.localeCompare(a.collected_at))[0] ?? null;
}

export function AvailabilityPanel({ availability, recent, error }: { availability: Availability[]; recent: LastCheck[]; error: boolean }) {
  return (
    <section className="history-panel" aria-labelledby="availability-title">
      <div className="history-heading"><div><span className="eyebrow">DISPONIBILIDADE</span><h2 id="availability-title">Estado e disponibilidade em 24 h</h2></div></div>
      {error ? <p className="metric-empty" role="status">Disponibilidade indisponível no momento.</p> : (
        <ul className="history-items">
          {(["protocol", "icmp"] as const).map((kind) => {
            const last = pickLatest(recent, kind);
            const stats = availability.find((item) => item.check_kind === kind);
            return (
              <li className="history-item" key={kind}>
                <span className={`history-level ${last === null ? "" : last.up ? "" : "history-level-red"}`} aria-label={last === null ? "Sem dados" : last.up ? "UP" : "DOWN"} />
                <div>
                  <strong>{kindLabels[kind]}: {last === null ? "sem dados" : last.up ? "UP" : "DOWN"}</strong>
                  <span>
                    {stats?.availability_pct == null ? "Sem verificações em 24 h" : `${stats.availability_pct}% em ${stats.check_count} verificações`}
                    {last?.latency_ms != null && ` · última resposta ${Math.round(last.latency_ms)} ms`}
                    {last && !last.up && last.error && ` · erro: ${last.error}`}
                  </span>
                </div>
                <time dateTime={last?.collected_at}>{last ? `${last.collected_at.slice(0, 16).replace("T", " ")} UTC` : "—"}</time>
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}
