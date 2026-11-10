import type { ServiceId } from "@/lib/supabase/types";

// `scale` converts the stored value to the displayed unit (rates are stored as 0..1).
export type MetricDefinition = { key: string; label: string; unit: string; scale?: number };

const PCT = 100;
const MIB = 1 / 1048576;
const KIB = 1 / 1024;

export const serviceCatalog: Record<ServiceId, { name: string; description: string; metrics: MetricDefinition[] }> = {
  web: {
    name: "Web Server",
    description: "Tráfego HTTP, latência de requisições e respostas com erro.",
    metrics: [
      { key: "web.rps", label: "Requisições por segundo", unit: "req/s" },
      { key: "web.latency_p50_ms", label: "Latência p50", unit: "ms" },
      { key: "web.latency_p95_ms", label: "Latência p95", unit: "ms" },
      { key: "web.error_4xx_rate", label: "Taxa de erros 4xx", unit: "%", scale: PCT },
      { key: "web.error_5xx_rate", label: "Taxa de erros 5xx", unit: "%", scale: PCT },
      { key: "web.active_connections", label: "Conexões ativas", unit: "conexões" },
    ],
  },
  db: {
    name: "Banco de dados",
    description: "Carga, conexões, armazenamento e atividade do PostgreSQL.",
    metrics: [
      { key: "db.qps", label: "Consultas por segundo", unit: "q/s" },
      { key: "db.rollback_rate", label: "Taxa de rollback", unit: "%", scale: PCT },
      { key: "db.xact_failure_rate", label: "Transações com falha", unit: "%", scale: PCT },
      { key: "db.connections", label: "Conexões abertas", unit: "conexões" },
      { key: "db.connections_ratio", label: "Uso do pool de conexões", unit: "%", scale: PCT },
      { key: "db.cpu_percent", label: "Uso de CPU", unit: "%" },
      { key: "db.mem_bytes", label: "Memória", unit: "MiB", scale: MIB },
      { key: "db.io_read_bps", label: "I/O de leitura", unit: "KiB/s", scale: KIB },
      { key: "db.io_write_bps", label: "I/O de escrita", unit: "KiB/s", scale: KIB },
      { key: "db.disk_read_ms", label: "Latência de leitura em disco", unit: "ms" },
      { key: "db.size_bytes", label: "Tamanho do banco", unit: "MiB", scale: MIB },
      { key: "db.growth_gb_day", label: "Crescimento estimado", unit: "GB/dia" },
      { key: "db.slow_queries_per_min", label: "Queries lentas (> 500 ms)", unit: "por min" },
    ],
  },
  dns: {
    name: "DNS",
    description: "Resolução de nomes, taxa de falhas e volume de consultas DNS.",
    metrics: [
      { key: "dns.resolve_ms", label: "Tempo de resolução", unit: "ms" },
      { key: "dns.failure_rate", label: "Taxa de falhas", unit: "%", scale: PCT },
      { key: "dns.qps", label: "Consultas por segundo", unit: "q/s" },
    ],
  },
  smtp: {
    name: "SMTP",
    description: "Fila, latência de entrega e taxas observadas no serviço SMTP.",
    metrics: [
      { key: "smtp.delivery_rate", label: "Taxa de entrega", unit: "%", scale: PCT },
      { key: "smtp.queue_length", label: "Mensagens na fila", unit: "mensagens" },
      { key: "smtp.send_latency_ms", label: "Latência de envio", unit: "ms" },
      { key: "smtp.reject_rate", label: "Taxa de rejeição", unit: "%", scale: PCT },
      { key: "smtp.timeout_rate", label: "Taxa de timeouts", unit: "%", scale: PCT },
      { key: "smtp.volume_per_min", label: "Volume por minuto", unit: "mensagens/min" },
      { key: "smtp.volume_per_hour", label: "Volume por hora", unit: "mensagens/h" },
    ],
  },
};

export function scalePoints<T extends { value: number | null }>(points: T[], scale = 1): T[] {
  return scale === 1 ? points : points.map((point) => ({ ...point, value: point.value === null ? null : point.value * scale }));
}

export const metricRanges = {
  "1 hour": "1 h",
  "6 hours": "6 h",
  "24 hours": "24 h",
} as const;

export type MetricRange = keyof typeof metricRanges;

export function parseMetricRange(value: string | undefined): MetricRange {
  return value && value in metricRanges ? (value as MetricRange) : "1 hour";
}
