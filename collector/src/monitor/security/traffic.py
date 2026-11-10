"""Traffic spike / DDoS indicator (US-15, RF-14).

z-score of the current RPS over a moving window (60 samples = 15 min at 15 s), or
RPS above `ratio_threshold` times the window mean. Samples flagged as anomalous are
kept out of the baseline so a sustained attack stays flagged instead of becoming
"normal".
"""

from __future__ import annotations

import statistics
from collections import Counter, deque
from datetime import datetime

from monitor.model import ActiveCondition, SecurityEvent


class TrafficDetector:
    def __init__(
        self,
        window: int = 60,
        z_threshold: float = 3.0,
        ratio_threshold: float = 5.0,
        min_samples: int = 8,
        min_rps: float = 5.0,
        top_n: int = 5,
    ) -> None:
        self._samples: deque[float] = deque(maxlen=window)
        self._z = z_threshold
        self._ratio = ratio_threshold
        self._min_samples = min_samples
        self._min_rps = min_rps  # ignore "spikes" in near-idle traffic
        self._top_n = top_n
        self._in_episode = False

    def observe(self, rps: float, ip_counts: Counter[str], now: datetime) -> ActiveCondition | None:
        if len(self._samples) < self._min_samples:
            self._samples.append(rps)
            return None

        mean = statistics.fmean(self._samples)
        stdev = statistics.pstdev(self._samples)
        zscore = (rps - mean) / stdev if stdev > 0 else None
        by_z = zscore is not None and zscore > self._z
        by_ratio = rps > self._ratio * mean
        if rps < self._min_rps or not (by_z or by_ratio):
            self._samples.append(rps)
            self._in_episode = False
            return None

        top_ips = [{"ip": ip, "count": count} for ip, count in ip_counts.most_common(self._top_n)]
        details: dict[str, object] = {
            "rps": round(rps, 2),
            "mean_rps": round(mean, 2),
            "stdev_rps": round(stdev, 2),
            "zscore": None if zscore is None else round(zscore, 2),
            "reason": "zscore" if by_z else "ratio",
            "top_ips": top_ips,
        }
        event = None
        if not self._in_episode:
            event = SecurityEvent("web", "ddos", details, now)
            self._in_episode = True
        return ActiveCondition(
            key="ddos",
            service_id="web",
            kind="ddos",
            level="red",
            message=f"Pico de tráfego: {rps:.1f} req/s (média {mean:.1f} req/s)",
            details=details,
            event=event,
        )
