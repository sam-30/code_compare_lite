"""Abstract base for all comparison methods."""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class FileMatch:
    file_a: str
    file_b: str
    score: float
    detail: dict = field(default_factory=dict)


@dataclass
class MethodResult:
    method_id: str
    score: float                       # 0.0 – 1.0
    file_matches: list[FileMatch] = field(default_factory=list)
    details: dict = field(default_factory=dict)


class ComparisonMethod(ABC):
    method_id: str
    default_weight: float = 0.1

    @abstractmethod
    def compare(
        self,
        root_a: Path,
        files_a: list[Path],
        root_b: Path,
        files_b: list[Path],
        language: str,
    ) -> MethodResult:
        ...
