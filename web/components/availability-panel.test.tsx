import { afterEach, describe, expect, it } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import { AvailabilityPanel, pickLatest } from "@/components/availability-panel";

afterEach(cleanup);

const row = (kind: "icmp" | "protocol", up: boolean, at: string) => ({ check_kind: kind, up, latency_ms: 12, error: up ? null : "timeout", collected_at: at });

describe("AvailabilityPanel", () => {
  it("picks the newest check per kind", () => {
    const rows = [row("protocol", true, "2026-11-10T10:00:00Z"), row("protocol", false, "2026-11-10T10:00:15Z")];
    expect(pickLatest(rows, "protocol")?.up).toBe(false);
    expect(pickLatest(rows, "icmp")).toBeNull();
  });

  it("shows UP/DOWN, percentage and the failure reason", () => {
    render(<AvailabilityPanel error={false}
      availability={[{ check_kind: "protocol", availability_pct: 99.5, check_count: 200 }]}
      recent={[row("protocol", false, "2026-11-10T10:00:15Z")]} />);
    expect(screen.getByText(/Protocolo.*: DOWN/)).toBeInTheDocument();
    expect(screen.getByText(/99.5% em 200 verificações/)).toBeInTheDocument();
    expect(screen.getByText(/erro: timeout/)).toBeInTheDocument();
    expect(screen.getByText(/Ping \(ICMP\): sem dados/)).toBeInTheDocument();
  });

  it("explains when the query failed", () => {
    render(<AvailabilityPanel error availability={[]} recent={[]} />);
    expect(screen.getByRole("status")).toHaveTextContent("indisponível");
  });
});
