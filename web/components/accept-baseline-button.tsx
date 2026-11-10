"use client";

import { useState, useTransition } from "react";
import { Check } from "lucide-react";
import { acceptConfigBaseline } from "@/app/(dash)/security/actions";

export function AcceptBaselineButton({ alertId, disabled = false }: { alertId: number; disabled?: boolean }) {
  const [pending, startTransition] = useTransition();
  const [message, setMessage] = useState<string | null>(null);

  return (
    <div className="accept-baseline">
      <button
        type="button"
        className="accept-button"
        disabled={disabled || pending}
        onClick={() =>
          startTransition(async () => {
            const result = await acceptConfigBaseline(alertId);
            setMessage(result.ok ? "Nova base aceita." : result.message);
          })
        }
      >
        <Check size={14} aria-hidden="true" /> {pending ? "Aceitando…" : "Aceitar como base"}
      </button>
      {message && <span role="status">{message}</span>}
    </div>
  );
}
