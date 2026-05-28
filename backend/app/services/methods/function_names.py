"""
Function / class / method name overlap.

Collects all function and class names from both repos, computes Jaccard
similarity of the two name sets.
"""
from pathlib import Path

from app.services.parser import extract_function_names
from .base import ComparisonMethod, MethodResult


def _jaccard(a: set, b: set) -> float:
    if not a and not b:
        return 1.0
    union = a | b
    if not union:
        return 0.0
    return len(a & b) / len(union)


class FunctionNamesMethod(ComparisonMethod):
    method_id = "function_names"
    default_weight = 0.15

    def compare(self, root_a, files_a, root_b, files_b, language):
        names_a: set[str] = set()
        for f in files_a:
            names_a |= extract_function_names(f)

        names_b: set[str] = set()
        for f in files_b:
            names_b |= extract_function_names(f)

        score = _jaccard(names_a, names_b)
        shared = sorted(names_a & names_b)
        return MethodResult(
            method_id=self.method_id,
            score=score,
            details={
                "shared_names": shared[:50],
                "unique_to_a": len(names_a - names_b),
                "unique_to_b": len(names_b - names_a),
                "shared_count": len(shared),
            },
        )
