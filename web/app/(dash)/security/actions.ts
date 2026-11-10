"use server";

import { revalidatePath } from "next/cache";
import { createClient } from "@/lib/supabase/server";

export type AcceptResult = { ok: true } | { ok: false; message: string };

/**
 * "Aceitar como base" (RF-16): the only write the dashboard performs. The content and
 * hash come from the alert row (written by the collector), never from the browser, and
 * the RPC re-computes the SHA-256 server-side.
 */
export async function acceptConfigBaseline(alertId: number): Promise<AcceptResult> {
  if (!Number.isSafeInteger(alertId) || alertId <= 0) return { ok: false, message: "Alerta inválido." };
  const supabase = await createClient();
  const { data: auth } = await supabase.auth.getUser();
  if (!auth.user) return { ok: false, message: "Sessão expirada. Entre novamente." };

  const { data: alert, error } = await supabase
    .from("alerts")
    .select("kind, status, details")
    .eq("id", alertId)
    .single();
  if (error || !alert) return { ok: false, message: "Alerta não encontrado." };
  if (alert.kind !== "config_change" || alert.status !== "open") {
    return { ok: false, message: "Este alerta não está aberto ou não é de configuração." };
  }

  const details = alert.details as { path?: unknown; current_content?: unknown; current_sha256?: unknown } | null;
  if (typeof details?.path !== "string" || typeof details.current_content !== "string" || typeof details.current_sha256 !== "string") {
    return { ok: false, message: "O alerta não traz o conteúdo do arquivo; aceite manualmente." };
  }

  const { error: rpcError } = await supabase.rpc("accept_config_baseline", {
    p_path: details.path,
    p_content: details.current_content,
    p_sha256: details.current_sha256,
  });
  if (rpcError) return { ok: false, message: "Não foi possível aceitar a nova base." };

  revalidatePath("/security");
  revalidatePath("/");
  return { ok: true };
}
