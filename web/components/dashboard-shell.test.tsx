import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

vi.mock("@/components/logout-button", () => ({
  LogoutButton: () => <button type="button">Sair da conta</button>,
}));

import { DashboardShell } from "@/components/dashboard-shell";

afterEach(cleanup);

describe("DashboardShell", () => {
  it("shows the signed-in operator and links to the implemented pages and keeps alerts unavailable", () => {
    render(<DashboardShell email="operator@example.test">Conteúdo</DashboardShell>);

    expect(screen.getByText("operator@example.test")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Visão geral/ })).toHaveAttribute("href", "/");
    expect(screen.getAllByText("em breve")).toHaveLength(1);
  });

  it("opens and closes the mobile navigation with accessible controls", async () => {
    const user = userEvent.setup();
    render(<DashboardShell email="operator@example.test">Conteúdo</DashboardShell>);

    const openButton = screen.getByRole("button", { name: "Abrir navegação" });
    await user.click(openButton);
    expect(openButton).toHaveAttribute("aria-expanded", "true");
    expect(screen.getByRole("complementary", { name: "Navegação principal" })).toHaveClass("sidebar-open");

    await user.click(screen.getByRole("button", { name: "Fechar navegação" }));
    expect(openButton).toHaveAttribute("aria-expanded", "false");
  });
});
