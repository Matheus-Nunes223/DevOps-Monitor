import { ShieldCheck } from "lucide-react";
import {
  OpenSecurityAlerts,
  SecurityEventList,
  VulnerabilityTable,
  type SecurityAlert,
  type SecurityEventRow,
} from "@/components/security-panels";
import type { VulnerabilityRow } from "@/lib/security";
import { createClient } from "@/lib/supabase/server";

export default async function SecurityPage() {
  const supabase = await createClient();
  const [alerts, events, vulnerabilities] = await Promise.all([
    supabase
      .from("alerts")
      .select("id, service_id, kind, level, message, details, opened_at")
      .eq("status", "open")
      .in("kind", ["ddos", "bruteforce", "config_change", "cve"])
      .order("opened_at", { ascending: false }),
    supabase
      .from("security_events")
      .select("id, service_id, type, details, detected_at")
      .order("detected_at", { ascending: false })
      .limit(50),
    supabase
      .from("vulnerabilities")
      .select("id, service_id, product_version, cve_id, cvss, summary, checked_at")
      .order("cvss", { ascending: false, nullsFirst: false })
      .limit(300),
  ]);

  return (
    <div className="service-dashboard">
      <div className="page-heading service-page-heading">
        <div>
          <div className="eyebrow"><span /> OPERAÇÕES / SEGURANÇA</div>
          <h1>Segurança</h1>
          <p>Tráfego anômalo, brute-force, mudanças de configuração e vulnerabilidades conhecidas.</p>
        </div>
        <span className="page-chip"><ShieldCheck size={15} /> Detecção ativa</span>
      </div>
      <OpenSecurityAlerts alerts={(alerts.data ?? []) as SecurityAlert[]} error={Boolean(alerts.error)} />
      <SecurityEventList events={(events.data ?? []) as SecurityEventRow[]} error={Boolean(events.error)} />
      <VulnerabilityTable rows={(vulnerabilities.data ?? []) as VulnerabilityRow[]} error={Boolean(vulnerabilities.error)} />
    </div>
  );
}
