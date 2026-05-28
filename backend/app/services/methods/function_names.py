"""
Function / class / method name overlap.

Collects all function and class names from both repos, computes Jaccard
similarity of the two name sets.
"""
from pathlib import Path

from app.services.parser import extract_function_names
from .base import ComparisonMethod, FileMatch, MethodResult


def _jaccard(a: set, b: set) -> float:
    if not a or not b:
        return 0.0
    union = a | b
    return len(a & b) / len(union)


class FunctionNamesMethod(ComparisonMethod):
    method_id = "function_names"
    default_weight = 0.15

    def compare(self, root_a, files_a, root_b, files_b, language):
        names_a_per_file = {f: extract_function_names(f) for f in files_a}
        names_b_per_file = {f: extract_function_names(f) for f in files_b}

        names_a: set[str] = set().union(*names_a_per_file.values()) if names_a_per_file else set()
        names_b: set[str] = set().union(*names_b_per_file.values()) if names_b_per_file else set()

        score = _jaccard(names_a, names_b)
        shared = sorted(names_a & names_b)

        # Per-file matches: find file pairs that share function names
        file_matches: list[FileMatch] = []
        for fb, nb in names_b_per_file.items():
            if not nb:
                continue
            best_score = 0.0
            best_fa = None
            best_shared: list[str] = []
            for fa, na in names_a_per_file.items():
                s = _jaccard(na, nb)
                if s > best_score:
                    best_score = s
                    best_fa = fa
                    best_shared = sorted(na & nb)
            if best_fa is not None and best_score > 0:
                file_matches.append(FileMatch(
                    file_a=str(best_fa.relative_to(root_a)),
                    file_b=str(fb.relative_to(root_b)),
                    score=best_score,
                    detail={"shared_functions": best_shared[:30]},
                ))

        return MethodResult(
            method_id=self.method_id,
            score=score,
            file_matches=file_matches,
            details={
                "shared_names": shared[:50],
                "unique_to_a": len(names_a - names_b),
                "unique_to_b": len(names_b - names_a),
                "shared_count": len(shared),
            },
        )
