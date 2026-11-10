export function BrandMark({ compact = false }: { compact?: boolean }) {
  return (
    <span className="brand-lockup" aria-label="DevOps Monitor">
      <span className="brand-symbol" aria-hidden="true">
        <i />
        <i />
        <i />
      </span>
      {!compact && (
        <span className="brand-wordmark">
          devops<span>monitor</span>
          <small>OBSERVABILITY PLATFORM</small>
        </span>
      )}
    </span>
  );
}
