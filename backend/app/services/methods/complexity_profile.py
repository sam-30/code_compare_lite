"""
Cyclomatic complexity profile comparison.

Counts branch-inducing nodes (if, for, while, try, elif, case, …) per
function to approximate cyclomatic complexity, then compares the sorted
complexity histograms using cosine similarity.
"""
import math
from collections import Counter
from pathlib import Path

from app.services.parser import get_language, parse, PY_LANGUAGE, JS_LANGUAGE, TS_LANGUAGE, TSX_LANGUAGE
from .base import ComparisonMethod, MethodResult

_BRANCH_TYPES = {
    # Python
    "if_statement", "elif_clause", "for_statement", "while_statement",
    "try_statement", "except_clause", "with_statement", "match_statement",
    # JavaScript / TypeScript
    "if_statement", "for_statement", "while_statement", "do_statement",
    "try_statement", "catch_clause", "switch_case", "ternary_expression",
    "conditional_expression",
}

_FUNC_TYPES = {
    "function_definition", "function_declaration", "method_definition",
    "arrow_function",
}


def _count_branches_in_subtree(node) -> int:
    count = 0
    if node.type in _BRANCH_TYPES:
        count += 1
    for child in node.children:
        count += _count_branches_in_subtree(child)
    return count


def _complexity_histogram(path: Path) -> Counter:
    result = parse(path)
    if result is None:
        return Counter()
    root, _ = result

    hist: Counter = Counter()

    def walk(node):
        if node.type in _FUNC_TYPES:
            c = _count_branches_in_subtree(node) + 1  # baseline complexity = 1
            hist[c] += 1
        else:
            for child in node.children:
                walk(child)

    walk(root)
    return hist


def _cosine_counters(a: Counter, b: Counter) -> float:
    if not a and not b:
        return 1.0
    keys = set(a.keys()) | set(b.keys())
    dot = sum(a[k] * b[k] for k in keys)
    mag_a = math.sqrt(sum(v**2 for v in a.values()))
    mag_b = math.sqrt(sum(v**2 for v in b.values()))
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot / (mag_a * mag_b)


class ComplexityProfileMethod(ComparisonMethod):
    method_id = "complexity_profile"
    default_weight = 0.05

    def compare(self, root_a, files_a, root_b, files_b, language):
        hist_a: Counter = Counter()
        for f in files_a:
            hist_a += _complexity_histogram(f)

        hist_b: Counter = Counter()
        for f in files_b:
            hist_b += _complexity_histogram(f)

        score = _cosine_counters(hist_a, hist_b)
        return MethodResult(
            method_id=self.method_id,
            score=score,
            details={
                "complexity_cosine": round(score, 4),
                "a_func_count": sum(hist_a.values()),
                "b_func_count": sum(hist_b.values()),
            },
        )
