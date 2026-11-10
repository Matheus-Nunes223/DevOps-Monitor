import { codeClass } from "@/lib/status-codes";

export function StatusCodeTable({ counts, error }: { counts: { code: string; total: number }[]; error: boolean }) {
  return (
    <section className="history-panel" aria-labelledby="status-codes-title">
      <div className="history-heading">
        <div><span className="eyebrow">HTTP</span><h2 id="status-codes-title">Contagem por código de resposta</h2></div>
        <span>{error ? "—" : counts.reduce((sum, item) => sum + item.total, 0)}</span>
      </div>
      {error ? (
        <p className="metric-empty" role="status">Contagem indisponível no momento.</p>
      ) : counts.length === 0 ? (
        <p className="metric-empty">Nenhuma resposta registrada no período.</p>
      ) : (
        <ul className="code-chips">
          {counts.map(({ code, total }) => (
            <li className={`code-chip code-chip-${codeClass(code)}`} key={code}><strong>{code}</strong><span>{total}</span></li>
          ))}
        </ul>
      )}
    </section>
  );
}
