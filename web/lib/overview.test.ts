import { describe, expect, it } from "vitest";
import {
  applyAlertRow,
  applyAvailability,
  applyProtocolStatus,
  applyServiceRow,
  buildOverviewSnapshot,
  type OverviewSourceData,
} from "@/lib/overview";

const baseSource: OverviewSourceData = {
  services: [
    { id: "smtp", name: "SMTP", current_level: "green" },
    { id: "web", name: "Web Server", current_level: "green" },
    { id: "db", name: "Banco de dados", current_level: "yellow" },
    { id: "dns", name: "DNS", current_level: "red" },
  ],
  statuses: [],
  availability: [],
  alerts: [],
};

describe("buildOverviewSnapshot", () => {
  it("keeps seeded services unknown until a protocol check is measured", () => {
    const snapshot = buildOverviewSnapshot(baseSource);

    expect(snapshot.services.map((service) => service.id)).toEqual(["web", "db", "dns", "smtp"]);
    expect(snapshot.services.every((service) => service.lastCheck === null)).toBe(true);
    expect(snapshot.services.every((service) => service.protocolUp === null)).toBe(true);
    expect(snapshot.services.every((service) => service.availability24h === null)).toBe(true);
  });

  it("uses the latest protocol result and ignores ICMP for service availability", () => {
    const snapshot = buildOverviewSnapshot({
      ...baseSource,
      statuses: [
        {
          id: 1,
          service_id: "web",
          check_kind: "protocol",
          up: true,
          collected_at: "2026-11-09T12:00:00Z",
        },
        {
          id: 2,
          service_id: "web",
          check_kind: "protocol",
          up: false,
          collected_at: "2026-11-09T12:00:15Z",
        },
        {
          id: 3,
          service_id: "web",
          check_kind: "icmp",
          up: true,
          collected_at: "2026-11-09T12:00:20Z",
        },
      ],
      availability: [
        { service_id: "web", check_kind: "icmp", availability_pct: 100, check_count: 50 },
        { service_id: "web", check_kind: "protocol", availability_pct: 98.5, check_count: 200 },
      ],
    });

    const web = snapshot.services[0];
    expect(web.protocolUp).toBe(false);
    expect(web.lastCheck).toBe("2026-11-09T12:00:15Z");
    expect(web.availability24h).toBe(98.5);
    expect(web.availabilityChecks).toBe(200);
  });

  it("shows only open alerts and sorts them newest first", () => {
    const snapshot = buildOverviewSnapshot({
      ...baseSource,
      alerts: [
        {
          id: 8,
          service_id: "web",
          kind: "threshold",
          level: "yellow",
          message: "Latência p95 alta",
          opened_at: "2026-11-09T11:30:00Z",
          status: "open",
        },
        {
          id: 9,
          service_id: "db",
          kind: "availability",
          level: "red",
          message: "Banco fora do ar",
          opened_at: "2026-11-09T11:45:00Z",
          status: "open",
        },
        {
          id: 10,
          service_id: "dns",
          kind: "threshold",
          level: "red",
          message: "Alerta resolvido",
          opened_at: "2026-11-09T11:55:00Z",
          status: "resolved",
        },
      ],
    });

    expect(snapshot.activeAlerts.map((alert) => alert.id)).toEqual([9, 8]);
  });

  it("applies service state changes and preserves unknown measurements for a new service", () => {
    const initial = buildOverviewSnapshot(baseSource).services;
    const changed = applyServiceRow(initial, {
      id: "web",
      name: "Web Server",
      current_level: "red",
    }, "UPDATE");
    const added = applyServiceRow(changed, {
      id: "dns",
      name: "DNS",
      current_level: "green",
    }, "INSERT");

    expect(added.find((service) => service.id === "web")?.currentLevel).toBe("red");
    expect(added.find((service) => service.id === "dns")?.lastCheck).toBeNull();
    expect(added.filter((service) => service.id === "dns")).toHaveLength(1);
  });

  it("updates last protocol check without letting older or ICMP events replace it", () => {
    const initial = buildOverviewSnapshot(baseSource).services;
    const latest = applyProtocolStatus(initial, {
      service_id: "web",
      check_kind: "protocol",
      up: true,
      collected_at: "2026-11-09T12:00:15Z",
    });
    const stale = applyProtocolStatus(latest, {
      service_id: "web",
      check_kind: "protocol",
      up: false,
      collected_at: "2026-11-09T12:00:00Z",
    });
    const icmp = applyProtocolStatus(stale, {
      service_id: "web",
      check_kind: "icmp",
      up: false,
      collected_at: "2026-11-09T12:00:30Z",
    });

    expect(icmp[0].protocolUp).toBe(true);
    expect(icmp[0].lastCheck).toBe("2026-11-09T12:00:15Z");
  });

  it("refreshes protocol availability from the measured 24-hour aggregate", () => {
    const initial = buildOverviewSnapshot(baseSource).services;
    const updated = applyAvailability(initial, "web", {
      service_id: "web",
      check_kind: "protocol",
      availability_pct: 99.25,
      check_count: 400,
    });

    expect(updated[0].availability24h).toBe(99.25);
    expect(updated[0].availabilityChecks).toBe(400);
  });

  it("adds, orders, and removes active alerts as their database state changes", () => {
    const older = {
      id: 1,
      service_id: "web" as const,
      kind: "threshold" as const,
      level: "yellow" as const,
      message: "Latência alta",
      opened_at: "2026-11-09T11:00:00Z",
      status: "open" as const,
    };
    const newer = { ...older, id: 2, opened_at: "2026-11-09T11:30:00Z" };
    const withAlerts = applyAlertRow([older], newer, "INSERT");
    const resolved = applyAlertRow(withAlerts, { ...newer, status: "resolved" }, "UPDATE");

    expect(withAlerts.map((alert) => alert.id)).toEqual([2, 1]);
    expect(resolved.map((alert) => alert.id)).toEqual([1]);
  });
});
