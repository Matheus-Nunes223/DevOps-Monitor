import { describe, expect, it } from "vitest";
import { configAlertDetails, groupVulnerabilities, severityOf, summarizeEvent, type VulnerabilityRow } from "@/lib/security";

describe("summarizeEvent", () => {
  it("lists the top IPs of a traffic spike", () => {
    const text = summarizeEvent("ddos", { rps: 60, mean_rps: 2, top_ips: [{ ip: "10.0.0.1", count: 900 }] });
    expect(text).toContain("60 req/s");
    expect(text).toContain("10.0.0.1 (900)");
  });

  it("shows IP and account counts for brute-force", () => {
    const text = summarizeEvent("bruteforce", { ips: [{ ip: "172.28.0.1", count: 12 }], accounts: [{ user: "admin", count: 12 }] });
    expect(text).toBe("IP 172.28.0.1: 12 falhas · conta admin: 12 falhas");
  });

  it("names the changed config file and tolerates empty payloads", () => {
    expect(summarizeEvent("config_change", { path: "nginx.conf" })).toContain("nginx.conf");
    expect(summarizeEvent("bruteforce", null)).toContain("acima do limite");
  });
});

describe("configAlertDetails", () => {
  it("only allows accepting when content and hash are present", () => {
    expect(configAlertDetails({ path: "nginx.conf", diff: "-a\n+b", current_content: "b", current_sha256: "x" })?.canAccept).toBe(true);
    expect(configAlertDetails({ path: "nginx.conf", diff: "" })?.canAccept).toBe(false);
    expect(configAlertDetails({ diff: "" })).toBeNull();
  });
});

describe("vulnerabilities", () => {
  const row = (id: number, service_id: VulnerabilityRow["service_id"], cvss: number | null): VulnerabilityRow => ({
    id, service_id, product_version: "1.0", cve_id: `CVE-${id}`, cvss, summary: null, checked_at: "2026-11-09T00:00:00Z",
  });

  it("classifies CVSS severity", () => {
    expect([9.8, 7, 5, 2, null].map(severityOf)).toEqual(["critical", "high", "medium", "low", "unknown"]);
  });

  it("groups by service in display order, sorts by score and counts CVSS >= 7", () => {
    const groups = groupVulnerabilities([row(1, "smtp", 5), row(2, "web", 5), row(3, "web", 9.1), row(4, "web", null)]);
    expect(groups.map((g) => g.serviceId)).toEqual(["web", "smtp"]);
    expect(groups[0].rows.map((r) => r.cve_id)).toEqual(["CVE-3", "CVE-2", "CVE-4"]);
    expect(groups[0].highCount).toBe(1);
  });
});
