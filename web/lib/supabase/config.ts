export type SupabasePublicConfig = {
  url: string;
  key: string;
};

export function isPublicSupabaseKey(key: string): boolean {
  if (key.startsWith("sb_publishable_")) return true;
  if (!key.includes(".")) return false;

  try {
    const payload = key.split(".")[1];
    const base64 = payload.replace(/-/g, "+").replace(/_/g, "/");
    const decoded = JSON.parse(atob(base64.padEnd(Math.ceil(base64.length / 4) * 4, "="))) as {
      role?: unknown;
    };
    return decoded.role === "anon";
  } catch {
    return false;
  }
}

export function getSupabasePublicConfig(): SupabasePublicConfig | null {
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL?.trim();
  const key = (
    process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY ||
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY
  )?.trim();

  if (!url || !key || !isPublicSupabaseKey(key)) return null;

  try {
    const parsedUrl = new URL(url);
    const isLoopback = ["localhost", "127.0.0.1", "[::1]"].includes(parsedUrl.hostname);
    if (parsedUrl.protocol !== "https:" && !(parsedUrl.protocol === "http:" && isLoopback)) {
      return null;
    }
    if (parsedUrl.username || parsedUrl.password || parsedUrl.search || parsedUrl.hash) return null;
  } catch {
    return null;
  }

  return { url, key };
}
