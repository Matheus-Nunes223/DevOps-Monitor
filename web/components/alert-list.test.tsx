import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { AlertList } from "@/components/alert-list";
import type { OverviewAlert } from "@/lib/overview";

describe("AlertList", () => {
  it("shows an explicit empty state instead of inventing alerts", () => {
    render(<AlertList alerts={[]} />);

    expect(screen.getByRole("heading", { name: "Alertas ativos" })).toBeInTheDocument();
    expect(screen.getByText("Nenhum alerta ativo")).toBeInTheDocument();
    expect(screen.getByText("0")).toBeInTheDocument();
  });

  it("does not call a failed query an empty alert list", () => {
    render(<AlertList alerts={[]} loaded={false} />);

    expect(screen.getByText("Alertas indisponíveis")).toBeInTheDocument();
    expect(screen.getByText("—")).toBeInTheDocument();
    expect(screen.queryByText("Nenhum alerta ativo")).not.toBeInTheDocument();
  });

  it("renders escaped alert messages and their measured service/severity", () => {
    const alert: OverviewAlert = {
      id: 44,
      service_id: "web",
      kind: "bruteforce",
      level: "red",
      message: "Tentativas <script>alert(1)</script>",
      opened_at: "2026-11-09T12:30:00Z",
      status: "open",
    };
    const { container } = render(<AlertList alerts={[alert]} />);

    expect(screen.getByText(alert.message)).toBeInTheDocument();
    expect(screen.getByText("Web Server", { exact: false })).toBeInTheDocument();
    expect(screen.getByText("Crítico")).toBeInTheDocument();
    expect(container.querySelector("script")).toBeNull();
  });
});
