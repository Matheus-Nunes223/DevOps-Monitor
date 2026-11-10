import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

const mocks = vi.hoisted(() => ({
  createClient: vi.fn(),
  replace: vi.fn(),
  refresh: vi.fn(),
  signInWithPassword: vi.fn(),
}));

vi.mock("@/lib/supabase/client", () => ({ createClient: mocks.createClient }));
vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: mocks.replace, refresh: mocks.refresh }),
}));

import { LoginForm } from "@/components/login-form";

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("LoginForm", () => {
  it("reports missing Supabase configuration without attempting authentication", async () => {
    const user = userEvent.setup();
    render(<LoginForm configured={false} redirectTo="/" />);

    await user.type(screen.getByLabelText("E-mail"), "operator@example.test");
    await user.type(screen.getByLabelText("Senha"), "not-a-real-password");
    await user.click(screen.getByRole("button", { name: "Entrar no painel" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("ainda não está configurado");
    expect(mocks.createClient).not.toHaveBeenCalled();
  });

  it("shows a generic credential message when Supabase rejects sign-in", async () => {
    const user = userEvent.setup();
    mocks.createClient.mockReturnValue({
      auth: { signInWithPassword: mocks.signInWithPassword },
    });
    mocks.signInWithPassword.mockResolvedValue({ error: new Error("private backend detail") });
    render(<LoginForm configured redirectTo="/" />);

    await user.type(screen.getByLabelText("E-mail"), "operator@example.test");
    await user.type(screen.getByLabelText("Senha"), "not-a-real-password");
    await user.click(screen.getByRole("button", { name: "Entrar no painel" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Confira o e-mail e a senha");
    expect(screen.queryByText("private backend detail")).not.toBeInTheDocument();
    expect(mocks.replace).not.toHaveBeenCalled();
  });

  it("navigates only to the validated local destination after successful sign-in", async () => {
    const user = userEvent.setup();
    mocks.createClient.mockReturnValue({
      auth: { signInWithPassword: mocks.signInWithPassword },
    });
    mocks.signInWithPassword.mockResolvedValue({ error: null });
    render(<LoginForm configured redirectTo="/services/web" />);

    await user.type(screen.getByLabelText("E-mail"), "operator@example.test");
    await user.type(screen.getByLabelText("Senha"), "correct-horse");
    await user.click(screen.getByRole("button", { name: "Entrar no painel" }));

    expect(mocks.signInWithPassword).toHaveBeenCalledWith({
      email: "operator@example.test",
      password: "correct-horse",
    });
    expect(mocks.replace).toHaveBeenCalledWith("/services/web");
    expect(mocks.refresh).toHaveBeenCalledOnce();
  });

  it("lets the user reveal and hide the password", async () => {
    const user = userEvent.setup();
    render(<LoginForm configured redirectTo="/" />);
    const password = screen.getByLabelText("Senha");

    expect(password).toHaveAttribute("type", "password");
    await user.click(screen.getByRole("button", { name: "Mostrar senha" }));
    expect(password).toHaveAttribute("type", "text");
    await user.click(screen.getByRole("button", { name: "Ocultar senha" }));
    expect(password).toHaveAttribute("type", "password");
  });
});
