export type StatusCountRow = { value: number | null; labels: unknown };

/** Sums `web.status_count{code}` samples (one per cycle) into totals per HTTP code. */
export function sumStatusCodes(rows: StatusCountRow[]): { code: string; total: number }[] {
  const totals = new Map<string, number>();
  for (const row of rows) {
    const labels = row.labels as { code?: unknown } | null;
    const code = typeof labels?.code === "string" ? labels.code : null;
    if (!code || row.value === null || !Number.isFinite(row.value)) continue;
    totals.set(code, (totals.get(code) ?? 0) + row.value);
  }
  return [...totals.entries()]
    .map(([code, total]) => ({ code, total }))
    .sort((a, b) => a.code.localeCompare(b.code));
}

export function codeClass(code: string): "ok" | "redirect" | "client" | "server" {
  if (code.startsWith("5")) return "server";
  if (code.startsWith("4")) return "client";
  if (code.startsWith("3")) return "redirect";
  return "ok";
}
