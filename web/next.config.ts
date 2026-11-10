import type { NextConfig } from "next";
import { isPublicSupabaseKey } from "./lib/supabase/config";

const configuredPublicKey =
  process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY || process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
if (configuredPublicKey && !isPublicSupabaseKey(configuredPublicKey.trim())) {
  throw new Error(
    "A chave do frontend deve ser publishable/anon. Não use a service-role key em NEXT_PUBLIC_*.",
  );
}

const securityHeaders = [
  { key: "X-Content-Type-Options", value: "nosniff" },
  { key: "X-Frame-Options", value: "DENY" },
  { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
  { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=()" },
];

const nextConfig: NextConfig = {
  poweredByHeader: false,
  async headers() {
    const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
    let supabaseOrigin = "https://*.supabase.co";
    try {
      if (supabaseUrl) supabaseOrigin = new URL(supabaseUrl).origin;
    } catch {
      // Keep the default CSP origin; runtime auth validation will show a setup error.
    }
    const realtimeOrigin = supabaseOrigin.startsWith("https:")
      ? supabaseOrigin.replace("https:", "wss:")
      : supabaseOrigin.replace("http:", "ws:");
    const csp = [
      "default-src 'self'",
      "base-uri 'self'",
      "object-src 'none'",
      "frame-ancestors 'none'",
      "form-action 'self'",
      "img-src 'self' data: blob:",
      "font-src 'self' data:",
      "style-src 'self' 'unsafe-inline'",
      `script-src 'self' 'unsafe-inline'${process.env.NODE_ENV === "development" ? " 'unsafe-eval'" : ""}`,
      `connect-src 'self' ${supabaseOrigin} ${realtimeOrigin}`,
    ].join("; ");

    return [
      {
        source: "/:path*",
        headers: [
          ...securityHeaders,
          { key: "Strict-Transport-Security", value: "max-age=63072000; includeSubDomains; preload" },
          { key: "Content-Security-Policy", value: csp },
        ],
      },
    ];
  },
};

export default nextConfig;
