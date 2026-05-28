"""Numerical metrics and data scaling utilities."""
import math
from typing import List, Optional


def scale_to_unit(values: List[float]) -> List[float]:
    if not values:
        return []
    lo = min(values)
    hi = max(values)
    if hi == lo:
        return [0.0] * len(values)
    return [(v - lo) / (hi - lo) for v in values]


def rolling_mean(values: List[float], size: int) -> List[float]:
    if size <= 0 or not values:
        return []
    output = []
    for i in range(len(values)):
        start = max(0, i - size + 1)
        segment = values[start : i + 1]
        output.append(sum(segment) / len(segment))
    return output


def quantile(values: List[float], q: float) -> float:
    if not values:
        raise ValueError("Cannot compute quantile of empty sequence")
    ordered = sorted(values)
    pos = (len(ordered) - 1) * q / 100
    lower = int(pos)
    upper = lower + 1
    if upper >= len(ordered):
        return ordered[lower]
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (pos - lower)


def standard_scores(values: List[float]) -> List[float]:
    if len(values) < 2:
        return [0.0] * len(values)
    avg = sum(values) / len(values)
    var = sum((v - avg) ** 2 for v in values) / (len(values) - 1)
    sd = math.sqrt(var)
    if sd == 0:
        return [0.0] * len(values)
    return [(v - avg) / sd for v in values]


class MetricSummary:
    def __init__(self, values: List[float]):
        self.values = list(values)
        self._avg: Optional[float] = None
        self._var: Optional[float] = None

    def average(self) -> float:
        if self._avg is None:
            self._avg = sum(self.values) / len(self.values) if self.values else 0.0
        return self._avg

    def variance(self) -> float:
        if self._var is None:
            avg = self.average()
            self._var = (
                sum((v - avg) ** 2 for v in self.values) / len(self.values)
                if self.values
                else 0.0
            )
        return self._var

    def std_dev(self) -> float:
        return math.sqrt(self.variance())

    def median(self) -> Optional[float]:
        if not self.values:
            return None
        s = sorted(self.values)
        n = len(s)
        return s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2

    def report(self) -> dict:
        return {
            "n": len(self.values),
            "average": self.average(),
            "std_dev": self.std_dev(),
            "median": self.median(),
            "minimum": min(self.values) if self.values else None,
            "maximum": max(self.values) if self.values else None,
        }
