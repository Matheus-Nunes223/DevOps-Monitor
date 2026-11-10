import Link from "next/link";
import { metricRanges, type MetricRange } from "@/lib/service-dashboard";

export function RangeFilter({ serviceId, range }: { serviceId: string; range: MetricRange }) {
  return (
    <nav className="range-filter" aria-label="Período das métricas">
      {Object.entries(metricRanges).map(([value, label]) => (
        <Link
          className={`range-option${value === range ? " range-option-active" : ""}`}
          aria-current={value === range ? "page" : undefined}
          href={`/services/${serviceId}?range=${encodeURIComponent(value)}`}
          key={value}
        >
          {label}
        </Link>
      ))}
    </nav>
  );
}
