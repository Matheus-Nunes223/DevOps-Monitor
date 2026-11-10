import type { Json, ServiceId } from "@/lib/supabase/types";

export type SecurityEventType = "ddos" | "bruteforce" | "config_change";

export const eventLabels: Record<SecurityEventType, string> = {
  ddos: "Pico de tráfego (possível DDoS)",
  bruteforce: "Brute-force de login",
  config_change: "Mudança de configuração",
};

function asRecord(value: Json | undefined): Record<string, Json | undefined> {
  return value !== null && typeof value === "object" && !Array.isArray(value) ? value : {};
}

/** One-line, human summary of a security event's `details` payload. */
export function summarizeEvent(type: SecurityEventType, details: Json): string {
  const d = asRecord(details);
  if (type === "ddos") {
    const top = Array.isArray(d.top_ips) ? d.top_ips.map(asRecord) : [];
    const ips = top.slice(0, 5).map((item) => `${item.ip} (${item.count})`).join(", ");
    return `${d.rps} req/s contra média de ${d.mean_rps} req/s${ips ? ` · top IPs: ${ips}` : ""}`;
  }
  if (type === "bruteforce") {
    const ips = (Array.isArray(d.ips) ? d.ips.map(asRecord) : []).map((item) => `IP ${item.ip}: ${item.count} falhas`);
    const users = (Array.isArray(d.accounts) ? d.accounts.map(asRecord) : []).map((item) => `conta ${item.user}: ${item.count} falhas`);
    return [...ips, ...users].join(" · ") || "Falhas de login acima do limite";
  }
  return `Arquivo ${d.path ?? "desconhecido"} diferente da base aceita`;
}

export type ConfigAlertDetails = { path: string; diff: string; canAccept: boolean };

export function configAlertDetails(details: Json): ConfigAlertDetails | null {
  const d = asRecord(details);
  if (typeof d.path !== "string") return null;
  return {
    path: d.path,
    diff: typeof d.diff === "string" ? d.diff : "",
    canAccept: typeof d.current_content === "string" && typeof d.current_sha256 === "string",
  };
}

export type VulnerabilityRow = {
  id: number;
  service_id: ServiceId;
  product_version: string;
  cve_id: string;
  cvss: number | null;
  summary: string | null;
  checked_at: string;
};

export const CVSS_HIGH = 7;

export function severityOf(cvss: number | null): "critical" | "high" | "medium" | "low" | "unknown" {
  if (cvss === null) return "unknown";
  if (cvss >= 9) return "critical";
  if (cvss >= CVSS_HIGH) return "high";
  if (cvss >= 4) return "medium";
  return "low";
}

export type VulnerabilityGroup = {
  serviceId: ServiceId;
  version: string;
  checkedAt: string;
  highCount: number;
  rows: VulnerabilityRow[];
};

const ORDER: ServiceId[] = ["web", "db", "dns", "smtp"];

export function groupVulnerabilities(rows: VulnerabilityRow[]): VulnerabilityGroup[] {
  const groups = new Map<ServiceId, VulnerabilityGroup>();
  for (const row of rows) {
    const group = groups.get(row.service_id) ?? { serviceId: row.service_id, version: row.product_version, checkedAt: row.checked_at, highCount: 0, rows: [] };
    group.rows.push(row);
    if ((row.cvss ?? 0) >= CVSS_HIGH) group.highCount += 1;
    if (row.checked_at > group.checkedAt) group.checkedAt = row.checked_at;
    groups.set(row.service_id, group);
  }
  for (const group of groups.values()) group.rows.sort((a, b) => (b.cvss ?? -1) - (a.cvss ?? -1));
  return ORDER.filter((id) => groups.has(id)).map((id) => groups.get(id) as VulnerabilityGroup);
}
