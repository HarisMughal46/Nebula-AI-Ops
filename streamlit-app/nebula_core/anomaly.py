"""Rolling z-score + configurable threshold anomaly detector."""

from __future__ import annotations

import math
import time
from collections import deque

THRESHOLDS = {"cpu": 90.0, "ram": 90.0, "disk": 95.0}


class AnomalyDetector:
    def __init__(
        self,
        window: int = 60,
        z: float = 3.0,
        min_samples: int = 10,
        thresholds: dict[str, float] | None = None,
    ) -> None:
        self.window, self.z, self.min_samples = window, z, min_samples
        self.thresholds: dict[str, float] = dict(thresholds or THRESHOLDS)
        self.history: dict[str, deque[float]] = {}

    def set_thresholds(self, thresholds: dict[str, float]) -> None:
        self.thresholds.update(thresholds)

    def _stats(self, key: str) -> tuple[float, float]:
        h = self.history[key]
        mean = sum(h) / len(h)
        var = sum((x - mean) ** 2 for x in h) / len(h)
        return mean, math.sqrt(var)

    def update(self, metrics: dict[str, float]) -> list[dict]:
        alerts: list[dict] = []
        for key, value in metrics.items():
            hist = self.history.setdefault(key, deque(maxlen=self.window))
            limit = self.thresholds.get(key)
            if limit is not None and value >= limit:
                alerts.append(self._alert(key, value, "critical", f"{key} above {limit:.0f}%"))
            elif len(hist) >= self.min_samples:
                mean, std = self._stats(key)
                if std > 1e-6:
                    score = (value - mean) / std
                    if abs(score) >= self.z:
                        alerts.append(
                            self._alert(key, value, "warning", f"{key} spike (z={score:.1f})")
                        )
            hist.append(value)
        return alerts

    @staticmethod
    def _alert(metric: str, value: float, level: str, msg: str) -> dict:
        return {"ts": time.time(), "metric": metric, "value": value, "level": level, "message": msg}
