import { afterEach, describe, expect, it, vi } from "vitest";
import { getSupabasePublicConfig, isPublicSupabaseKey } from "@/lib/supabase/config";

afterEach(() => vi.unstubAllEnvs());

describe("getSupabasePublicConfig", () => {
  it("accepts the public publishable key and an HTTPS project URL", () => {
    vi.stubEnv("NEXT_PUBLIC_SUPABASE_URL", "https://project.supabase.co");
    vi.stubEnv("NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY", "sb_publishable_demo");
    vi.stubEnv("NEXT_PUBLIC_SUPABASE_ANON_KEY", "");

    expect(getSupabasePublicConfig()).toEqual({
      url: "https://project.supabase.co",
      key: "sb_publishable_demo",
    });
  });

  it("supports local Supabase HTTP and legacy anon keys", () => {
    vi.stubEnv("NEXT_PUBLIC_SUPABASE_URL", "http://127.0.0.1:54321");
    vi.stubEnv("NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY", "");
    vi.stubEnv(
      "NEXT_PUBLIC_SUPABASE_ANON_KEY",
      `header.${btoa(JSON.stringify({ role: "anon" }))}.signature`,
    );

    expect(getSupabasePublicConfig()?.key).toBe(
      `header.${btoa(JSON.stringify({ role: "anon" }))}.signature`,
    );
  });

  it("rejects missing or insecure non-local configuration", () => {
    vi.stubEnv("NEXT_PUBLIC_SUPABASE_URL", "http://supabase.example.com");
    vi.stubEnv("NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY", "public-key");
    vi.stubEnv("NEXT_PUBLIC_SUPABASE_ANON_KEY", "");

    expect(getSupabasePublicConfig()).toBeNull();

    vi.stubEnv("NEXT_PUBLIC_SUPABASE_URL", "");
    expect(getSupabasePublicConfig()).toBeNull();
  });

  it("accepts only publishable or anon-role keys, never a service-role JWT", () => {
    const anonPayload = btoa(JSON.stringify({ role: "anon" }));
    const servicePayload = btoa(JSON.stringify({ role: "service_role" }));

    expect(isPublicSupabaseKey(`header.${anonPayload}.signature`)).toBe(true);
    expect(isPublicSupabaseKey(`header.${servicePayload}.signature`)).toBe(false);
    expect(isPublicSupabaseKey("sb_secret_demo_value")).toBe(false);
  });
});
