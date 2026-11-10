import { createBrowserClient } from "@supabase/ssr";
import { getSupabasePublicConfig } from "@/lib/supabase/config";
import type { Database } from "@/lib/supabase/types";

export function createClient() {
  const config = getSupabasePublicConfig();
  if (!config) {
    throw new Error("Supabase não está configurado. Defina URL e chave pública.");
  }

  return createBrowserClient<Database>(config.url, config.key);
}
