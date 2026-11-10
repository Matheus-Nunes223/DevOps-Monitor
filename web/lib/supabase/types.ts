// Schema mirrors supabase/migrations/20261109000000_init.sql and
// 20261109000100_availability_24h.sql. Regenerate with Supabase CLI after
// linking the external project; this workspace has no linked project yet.
export type Json =
  | string
  | number
  | boolean
  | null
  | { [key: string]: Json | undefined }
  | Json[];

export type ServiceId = "web" | "db" | "dns" | "smtp";
export type ServiceLevel = "green" | "yellow" | "red";
export type AlertKind =
  | "threshold"
  | "availability"
  | "ddos"
  | "bruteforce"
  | "config_change"
  | "cve";

type Table<Row, Insert, Update> = {
  Row: Row;
  Insert: Insert;
  Update: Update;
  Relationships: [];
};

export type ServiceRow = {
  id: ServiceId;
  name: string;
  host: string;
  current_level: ServiceLevel;
};

export type ServiceStatusRow = {
  id: number;
  service_id: ServiceId;
  up: boolean;
  check_kind: "icmp" | "protocol";
  latency_ms: number | null;
  error: string | null;
  collected_at: string;
};

export type AlertRow = {
  id: number;
  rule_id: number | null;
  service_id: ServiceId;
  kind: AlertKind;
  level: Exclude<ServiceLevel, "green">;
  status: "open" | "resolved";
  value: number | null;
  message: string;
  details: Json;
  opened_at: string;
  resolved_at: string | null;
  last_notified_at: string | null;
};

export type Database = {
  public: {
    Tables: {
      services: Table<
        ServiceRow,
        Omit<ServiceRow, "current_level"> & { current_level?: ServiceLevel },
        Partial<ServiceRow>
      >;
      metrics: Table<
        {
          id: number;
          service_id: ServiceId;
          metric: string;
          value: number | null;
          labels: Json;
          collected_at: string;
        },
        {
          id?: number;
          service_id: ServiceId;
          metric: string;
          value?: number | null;
          labels?: Json;
          collected_at?: string;
        },
        Partial<{
          service_id: ServiceId;
          metric: string;
          value: number | null;
          labels: Json;
          collected_at: string;
        }>
      >;
      service_status: Table<
        ServiceStatusRow,
        Omit<ServiceStatusRow, "id" | "collected_at"> & {
          id?: number;
          collected_at?: string;
        },
        Partial<Omit<ServiceStatusRow, "id">>
      >;
      alert_rules: Table<
        {
          id: number;
          service_id: ServiceId;
          metric: string;
          operator: ">" | "<" | ">=";
          warn_threshold: number;
          crit_threshold: number;
          consecutive_cycles: number;
          enabled: boolean;
        },
        {
          id?: number;
          service_id: ServiceId;
          metric: string;
          operator: ">" | "<" | ">=";
          warn_threshold: number;
          crit_threshold: number;
          consecutive_cycles?: number;
          enabled?: boolean;
        },
        Partial<{
          service_id: ServiceId;
          metric: string;
          operator: ">" | "<" | ">=";
          warn_threshold: number;
          crit_threshold: number;
          consecutive_cycles: number;
          enabled: boolean;
        }>
      >;
      alerts: Table<
        AlertRow,
        Omit<AlertRow, "id" | "opened_at" | "resolved_at" | "last_notified_at"> & {
          id?: number;
          opened_at?: string;
          resolved_at?: string | null;
          last_notified_at?: string | null;
        },
        Partial<Omit<AlertRow, "id">>
      >;
      security_events: Table<
        {
          id: number;
          service_id: ServiceId;
          type: "ddos" | "bruteforce" | "config_change";
          details: Json;
          detected_at: string;
        },
        {
          id?: number;
          service_id: ServiceId;
          type: "ddos" | "bruteforce" | "config_change";
          details: Json;
          detected_at?: string;
        },
        Partial<{
          service_id: ServiceId;
          type: "ddos" | "bruteforce" | "config_change";
          details: Json;
          detected_at: string;
        }>
      >;
      vulnerabilities: Table<
        {
          id: number;
          service_id: ServiceId;
          product_version: string;
          cve_id: string;
          cvss: number | null;
          summary: string | null;
          published_at: string | null;
          checked_at: string;
        },
        {
          id?: number;
          service_id: ServiceId;
          product_version: string;
          cve_id: string;
          cvss?: number | null;
          summary?: string | null;
          published_at?: string | null;
          checked_at?: string;
        },
        Partial<{
          service_id: ServiceId;
          product_version: string;
          cve_id: string;
          cvss: number | null;
          summary: string | null;
          published_at: string | null;
          checked_at: string;
        }>
      >;
      config_baselines: Table<
        {
          path: "nginx.conf" | "Corefile" | "postgresql.conf" | "main.cf";
          service_id: ServiceId;
          sha256: string;
          content: string;
          accepted_at: string;
        },
        {
          path: "nginx.conf" | "Corefile" | "postgresql.conf" | "main.cf";
          service_id: ServiceId;
          sha256: string;
          content: string;
          accepted_at?: string;
        },
        Partial<{
          path: "nginx.conf" | "Corefile" | "postgresql.conf" | "main.cf";
          service_id: ServiceId;
          sha256: string;
          content: string;
          accepted_at: string;
        }>
      >;
    };
    Views: Record<string, never>;
    Functions: {
      metric_series: {
        Args: { p_service: string; p_metric: string; p_range: string };
        Returns: { bucket: string; value: number | null; sample_count: number }[];
      };
      service_availability_24h: {
        Args: { p_service_id?: string | null };
        Returns: {
          service_id: ServiceId;
          check_kind: "icmp" | "protocol";
          availability_pct: number | null;
          check_count: number;
        }[];
      };
      accept_config_baseline: {
        Args: { p_path: string; p_content: string; p_sha256: string };
        Returns: undefined;
      };
      purge_old_monitoring_data: {
        Args: Record<string, never>;
        Returns: undefined;
      };
    };
    Enums: Record<string, never>;
    CompositeTypes: Record<string, never>;
  };
};
