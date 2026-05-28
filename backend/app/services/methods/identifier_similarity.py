"""
Variable / identifier name similarity.

Extracts all non-keyword identifiers from both repos and computes Jaccard
similarity of the two multisets (converted to sets for simplicity).
"""
from pathlib import Path

from app.services.parser import extract_identifiers
from .base import ComparisonMethod, MethodResult


class IdentifierSimilarityMethod(ComparisonMethod):
    method_id = "identifier_similarity"
    default_weight = 0.05

    def compare(self, root_a, files_a, root_b, files_b, language):
        ids_a: set[str] = set()
        for f in files_a:
            ids_a |= set(extract_identifiers(f))

        ids_b: set[str] = set()
        for f in files_b:
            ids_b |= set(extract_identifiers(f))

        if not ids_a and not ids_b:
            score = 1.0
        else:
            union = ids_a | ids_b
            score = len(ids_a & ids_b) / len(union) if union else 0.0

        shared = sorted(ids_a & ids_b)
        return MethodResult(
            method_id=self.method_id,
            score=score,
            details={
                "shared_identifiers_count": len(shared),
                "unique_to_a": len(ids_a - ids_b),
                "unique_to_b": len(ids_b - ids_a),
            },
        )
