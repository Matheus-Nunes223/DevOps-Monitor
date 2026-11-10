import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import { buildOverviewSnapshot } from "@/lib/overview";

const mocks = vi.hoisted(() => {
  const channel = {
    on: vi.fn(),
    subscribe: vi.fn(),
  };
  const router = { refresh: vi.fn() };
  channel.on.mockReturnValue(channel);
  channel.subscribe.mockImplementation((callback: (status: string) => void) => {
    callback("SUBSCRIBED");
    return channel;
  });
  return {
    channel,
    router,
    createClient: vi.fn(() => ({
      channel: vi.fn(() => channel),
      removeChannel: vi.fn(),
      rpc: vi.fn().mockResolvedValue({ data: [], error: null }),
    })),
  };
});

vi.mock("@/lib/supabase/client", () => ({ createClient: mocks.createClient }));
vi.mock("next/navigation", () => ({ useRouter: () => mocks.router }));

import { OverviewLive } from "@/components/overview-live";

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

const initial = buildOverviewSnapshot({
  services: [
    { id: "web", name: "Web Server", current_level: "green" },
    { id: "db", name: "Banco de dados", current_level: "green" },
    { id: "dns", name: "DNS", current_level: "green" },
    { id: "smtp", name: "SMTP", current_level: "green" },
  ],
  statuses: [],
  availability: [],
  alerts: [],
});

describe("OverviewLive", () => {
  it("subscribes to the three authorized tables and refreshes initial server data after joining", async () => {
    render(<OverviewLive initial={initial} />);

    expect(await screen.findByText("Atualizações em tempo real ativas")).toBeInTheDocument();
    expect(mocks.channel.on).toHaveBeenCalledTimes(3);
    expect(mocks.channel.on).toHaveBeenCalledWith(
      "postgres_changes",
      expect.objectContaining({ schema: "public", table: "services" }),
      expect.any(Function),
    );
    expect(mocks.channel.on).toHaveBeenCalledWith(
      "postgres_changes",
      expect.objectContaining({ schema: "public", table: "service_status" }),
      expect.any(Function),
    );
    expect(mocks.channel.on).toHaveBeenCalledWith(
      "postgres_changes",
      expect.objectContaining({ schema: "public", table: "alerts" }),
      expect.any(Function),
    );
    expect(mocks.router.refresh).toHaveBeenCalledOnce();
  });
});
