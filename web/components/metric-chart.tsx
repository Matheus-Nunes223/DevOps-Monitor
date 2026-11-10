export type MetricPoint = { bucket: string; value: number | null; sample_count: number };

type ChartPoint = { x: number; y: number; source: MetricPoint };

export function buildChartSegments(data: MetricPoint[], width = 720, height = 220) {
  const padding = { top: 14, right: 14, bottom: 22, left: 14 };
  const values = data.filter((point) => point.value !== null && point.sample_count > 0);
  if (values.length === 0) return [] as ChartPoint[][];

  const min = Math.min(...values.map((point) => point.value as number));
  const max = Math.max(...values.map((point) => point.value as number));
  const spread = max - min || Math.max(Math.abs(max) * 0.1, 1);
  const plotWidth = width - padding.left - padding.right;
  const plotHeight = height - padding.top - padding.bottom;
  const points = data.map((point, index): ChartPoint | null => {
    if (point.value === null || point.sample_count <= 0) return null;
    const x = padding.left + (data.length <= 1 ? plotWidth / 2 : (index / (data.length - 1)) * plotWidth);
    const y = padding.top + ((max - point.value) / spread) * plotHeight;
    return { x, y, source: point };
  });

  const segments: ChartPoint[][] = [];
  for (const point of points) {
    if (point === null) continue;
    if (!segments.length || points[points.indexOf(point) - 1] === null) segments.push([]);
    segments[segments.length - 1].push(point);
  }
  return segments;
}

export function MetricChart({
  title,
  unit,
  data,
  error,
}: {
  title: string;
  unit: string;
  data: MetricPoint[];
  error?: boolean;
}) {
  const segments = buildChartSegments(data);
  const measured = data.filter((point) => point.value !== null && point.sample_count > 0);
  const latest = measured.at(-1)?.value;

  return (
    <section className="metric-panel" aria-labelledby={`metric-${title.replaceAll(" ", "-")}`}>
      <div className="metric-panel-heading">
        <div><h2 id={`metric-${title.replaceAll(" ", "-")}`}>{title}</h2><span>{unit}</span></div>
        <strong>{latest === undefined || latest === null ? "—" : `${Number(latest.toPrecision(4))} ${unit}`}</strong>
      </div>
      {error ? (
        <div className="metric-empty" role="status">Não foi possível carregar esta série.</div>
      ) : measured.length === 0 ? (
        <div className="metric-empty" role="status">Sem medições neste período.</div>
      ) : (
        <svg className="metric-chart" viewBox="0 0 720 220" role="img" aria-label={`${title} nos últimos períodos, unidade ${unit}`}>
          <line x1="14" y1="198" x2="706" y2="198" className="chart-axis" />
          {segments.map((segment, index) => (
            <g key={index}>
              {segment.length > 1 && <polyline points={segment.map(({ x, y }) => `${x},${y}`).join(" ")} className="chart-line" />}
              {segment.map(({ x, y, source }) => (
                <circle cx={x} cy={y} r="2.4" className="chart-point" key={source.bucket}>
                  <title>{new Date(source.bucket).toISOString()} · {source.value} {unit} · {source.sample_count} amostras</title>
                </circle>
              ))}
            </g>
          ))}
        </svg>
      )}
      {measured.length > 0 && <p className="metric-sample-note">{measured.reduce((total, point) => total + point.sample_count, 0)} amostras nos buckets com dados</p>}
    </section>
  );
}
