"""Statistical analysis utilities."""
import math
from typing import List, Optional


def normalize_values(data: List[float]) -> List[float]:
    if not data:
        return []
    min_val = min(data)
    max_val = max(data)
    if max_val == min_val:
        return [0.0] * len(data)
    return [(x - min_val) / (max_val - min_val) for x in data]


def moving_average(data: List[float], window: int) -> List[float]:
    if window <= 0 or not data:
        return []
    result = []
    for i in range(len(data)):
        start = max(0, i - window + 1)
        chunk = data[start : i + 1]
        result.append(sum(chunk) / len(chunk))
    return result


def percentile(data: List[float], p: float) -> float:
    if not data:
        raise ValueError("Cannot compute percentile of empty list")
    sorted_data = sorted(data)
    idx = (len(sorted_data) - 1) * p / 100
    lo = int(idx)
    hi = lo + 1
    if hi >= len(sorted_data):
        return sorted_data[lo]
    return sorted_data[lo] + (sorted_data[hi] - sorted_data[lo]) * (idx - lo)


def z_scores(data: List[float]) -> List[float]:
    if len(data) < 2:
        return [0.0] * len(data)
    mean = sum(data) / len(data)
    variance = sum((x - mean) ** 2 for x in data) / (len(data) - 1)
    std = math.sqrt(variance)
    if std == 0:
        return [0.0] * len(data)
    return [(x - mean) / std for x in data]


class Statistics:
    def __init__(self, data: List[float]):
        self.data = list(data)
        self._mean: Optional[float] = None
        self._variance: Optional[float] = None

    def mean(self) -> float:
        if self._mean is None:
            self._mean = sum(self.data) / len(self.data) if self.data else 0.0
        return self._mean

    def variance(self) -> float:
        if self._variance is None:
            m = self.mean()
            self._variance = (
                sum((x - m) ** 2 for x in self.data) / len(self.data)
                if self.data
                else 0.0
            )
        return self._variance

    def std_dev(self) -> float:
        return math.sqrt(self.variance())

    def median(self) -> Optional[float]:
        if not self.data:
            return None
        s = sorted(self.data)
        n = len(s)
        return s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2

    def summary(self) -> dict:
        return {
            "count": len(self.data),
            "mean": self.mean(),
            "std_dev": self.std_dev(),
            "median": self.median(),
            "min": min(self.data) if self.data else None,
            "max": max(self.data) if self.data else None,
        }
