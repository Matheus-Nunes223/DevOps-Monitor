import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { StatusCard } from "@/components/status-card";
import type { OverviewService } from "@/lib/overview";

describe("StatusCard", () => {
  it("does not turn the seeded green level into a measured healthy state", () => {
    const service: OverviewService = {
      id: "web",
      name: "Web Server",
      currentLevel: "green",
      protocolUp: null,
      lastCheck: null,
      availability24h: null,
      availabilityChecks: 0,
    };
    render(<StatusCard service={service} />);

    expect(screen.getByTestId("level-web")).toHaveTextContent("Sem dados");
    expect(screen.getByText("Disponibilidade 24 h").nextElementSibling).toHaveTextContent("—");
    expect(screen.queryByText("100.00%")).not.toBeInTheDocument();
  });

  it("shows measured availability and a real failed protocol check", () => {
    const service: OverviewService = {
      id: "db",
      name: "Banco de dados",
      currentLevel: "red",
      protocolUp: false,
      lastCheck: "2026-11-09T12:30:00Z",
      availability24h: 96.5,
      availabilityChecks: 200,
    };
    render(<StatusCard service={service} />);

    expect(screen.getByTestId("level-db")).toHaveTextContent("Crítico");
    expect(screen.getByText("96.50%")).toBeInTheDocument();
    expect(screen.getByText("Última resposta: sem resposta")).toBeInTheDocument();
    expect(screen.getByText(/12:30:00 UTC/)).toBeInTheDocument();
  });
});
