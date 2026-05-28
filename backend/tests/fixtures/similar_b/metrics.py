"""Data analysis helpers for numerical datasets."""
import math
from typing import List, Optional


def rescale_data(dataset: List[float]) -> List[float]:
    if not dataset:
        return []
    minimum = min(dataset)
    maximum = max(dataset)
    if maximum == minimum:
        return [0.0] * len(dataset)
    return [(item - minimum) / (maximum - minimum) for item in dataset]


def sliding_average(dataset: List[float], span: int) -> List[float]:
    if span <= 0 or not dataset:
        return []
    averaged = []
    for idx in range(len(dataset)):
        begin = max(0, idx - span + 1)
        window = dataset[begin : idx + 1]
        averaged.append(sum(window) / len(window))
    return averaged


def compute_percentile(dataset: List[float], pct: float) -> float:
    if not dataset:
        raise ValueError("Dataset must not be empty")
    ranked = sorted(dataset)
    position = (len(ranked) - 1) * pct / 100
    left = int(position)
    right = left + 1
    if right >= len(ranked):
        return ranked[left]
    return ranked[left] + (ranked[right] - ranked[left]) * (position - left)


def compute_z_scores(dataset: List[float]) -> List[float]:
    if len(dataset) < 2:
        return [0.0] * len(dataset)
    mu = sum(dataset) / len(dataset)
    sigma_sq = sum((x - mu) ** 2 for x in dataset) / (len(dataset) - 1)
    sigma = math.sqrt(sigma_sq)
    if sigma == 0:
        return [0.0] * len(dataset)
    return [(x - mu) / sigma for x in dataset]


class DataStats:
    def __init__(self, dataset: List[float]):
        self.dataset = list(dataset)
        self._cached_mean: Optional[float] = None
        self._cached_var: Optional[float] = None

    def mean(self) -> float:
        if self._cached_mean is None:
            self._cached_mean = sum(self.dataset) / len(self.dataset) if self.dataset else 0.0
        return self._cached_mean

    def variance(self) -> float:
        if self._cached_var is None:
            m = self.mean()
            self._cached_var = (
                sum((x - m) ** 2 for x in self.dataset) / len(self.dataset)
                if self.dataset
                else 0.0
            )
        return self._cached_var

    def std_dev(self) -> float:
        return math.sqrt(self.variance())

    def median(self) -> Optional[float]:
        if not self.dataset:
            return None
        sorted_vals = sorted(self.dataset)
        length = len(sorted_vals)
        if length % 2:
            return sorted_vals[length // 2]
        return (sorted_vals[length // 2 - 1] + sorted_vals[length // 2]) / 2

    def describe(self) -> dict:
        return {
            "count": len(self.dataset),
            "mean": self.mean(),
            "std_dev": self.std_dev(),
            "median": self.median(),
            "min": min(self.dataset) if self.dataset else None,
            "max": max(self.dataset) if self.dataset else None,
        }
