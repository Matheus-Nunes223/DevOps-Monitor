"""Portuguese subjects and bodies for alert e-mails (RF-13)."""

from __future__ import annotations

from dataclasses import dataclass

from monitor.model import AlertKind, AlertLevel, AlertRule, ServiceId

METRIC_LABELS: dict[str, str] = {
    "web.latency_p95_ms": "latência p95",
    "web.error_5xx_rate": "erros 5xx",
    "db.connections_ratio": "conexões",
    "db.slow_queries_per_min": "queries lentas/min",
    "db.cpu_percent": "CPU",
    "dns.resolve_ms": "tempo de resolução",
    "dns.failure_rate": "falhas de resolução",
    "smtp.queue_length": "fila de e-mails",
    "smtp.delivery_rate": "taxa de entrega",
}

KIND_LABELS: dict[AlertKind, str] = {
    "threshold": "limite de métrica",
    "availability": "disponibilidade",
    "ddos": "pico de tráfego (possível DDoS)",
    "bruteforce": "brute-force de login",
    "config_change": "alteração de configuração",
    "cve": "vulnerabilidade conhecida",
}

RUNBOOKS: dict[str, str] = {
    "web": "docs/runbooks/web.md",
    "db": "docs/runbooks/db.md",
    "dns": "docs/runbooks/dns.md",
    "smtp": "docs/runbooks/smtp.md",
}
PLAYBOOKS: dict[AlertKind, str] = {
    "threshold": "docs/playbooks/servico-fora.md",
    "availability": "docs/playbooks/servico-fora.md",
    "ddos": "docs/playbooks/ddos.md",
    "bruteforce": "docs/playbooks/bruteforce.md",
    "config_change": "docs/playbooks/config-alterada.md",
    "cve": "docs/playbooks/cve-critico.md",
}

_TAG: dict[AlertLevel, str] = {"red": "CRÍTICO", "yellow": "ATENÇÃO"}


@dataclass(frozen=True, slots=True)
class RenderedEmail:
    subject: str
    body: str


def format_value(metric: str, value: float) -> str:
    """Rates and ratios are stored as 0..1 and shown as percentages."""
    if metric.endswith(("_rate", "_ratio")):
        return f"{value * 100:.0f}%"
    if metric.endswith("_ms"):
        return f"{value:.0f} ms"
    if metric.endswith("_percent"):
        return f"{value:.0f}%"
    return f"{value:g}"


def _link(dashboard_url: str, service_id: str) -> str:
    return f"{dashboard_url.rstrip('/')}/services/{service_id}"


def _footer(
    service_id: ServiceId, kind: AlertKind, dashboard_url: str, opened_at: str
) -> list[str]:
    return [
        f"Horário (UTC): {opened_at}",
        f"Painel: {_link(dashboard_url, service_id)}",
        f"Runbook: {RUNBOOKS[service_id]}",
        f"Playbook: {PLAYBOOKS[kind]}",
    ]


def threshold_message(rule: AlertRule, level: AlertLevel, value: float) -> str:
    label = METRIC_LABELS.get(rule.metric, rule.metric)
    limit = rule.crit_threshold if level == "red" else rule.warn_threshold
    if rule.metric.endswith(".up"):
        return f"{rule.service_id}: {int(value)} verificações seguidas falharam"
    return (
        f"{rule.service_id} {label}: {format_value(rule.metric, value)} "
        f"(limite {format_value(rule.metric, limit)})"
    )


def render_open(
    *,
    service_id: ServiceId,
    kind: AlertKind,
    level: AlertLevel,
    message: str,
    metric: str | None,
    value: float | None,
    dashboard_url: str,
    opened_at: str,
    reminder: bool = False,
) -> RenderedEmail:
    tag = _TAG[level]
    if kind == "availability":
        subject = (
            f"[{tag}] {service_id} indisponível"
            if level == "red"
            else f"[{tag}] {service_id} com falhas de verificação"
        )
    elif kind == "threshold" and metric is not None and value is not None:
        label = METRIC_LABELS.get(metric, metric)
        subject = f"[{tag}] {service_id} {label} em {format_value(metric, value)}"
    else:
        subject = f"[{tag}] {service_id}: {KIND_LABELS[kind]}"
    if reminder:
        subject = f"{subject} (lembrete)"
    lines = [
        f"Serviço: {service_id}",
        f"Nível: {tag}",
        f"Tipo: {KIND_LABELS[kind]}",
        f"Detalhe: {message}",
        *_footer(service_id, kind, dashboard_url, opened_at),
    ]
    return RenderedEmail(subject=subject, body="\n".join(lines) + "\n")


def render_resolved(
    *,
    service_id: ServiceId,
    kind: AlertKind,
    message: str,
    dashboard_url: str,
    resolved_at: str,
) -> RenderedEmail:
    suffix = "" if kind in ("threshold", "availability") else f": {KIND_LABELS[kind]}"
    lines = [
        f"Serviço: {service_id}",
        "Nível: VERDE (normalizado)",
        f"Tipo: {KIND_LABELS[kind]}",
        f"Alerta encerrado: {message}",
        *_footer(service_id, kind, dashboard_url, resolved_at),
    ]
    return RenderedEmail(subject=f"[RESOLVIDO] {service_id}{suffix}", body="\n".join(lines) + "\n")
