"""
AST structural similarity.

Serialises the AST of each file into a sequence of node types (identifiers
stripped), hashes overlapping subtrees, and computes Jaccard similarity of
the two subtree-fingerprint multisets.
"""
import hashlib
from collections import Counter
from pathlib import Path

from app.services.parser import parse
from .base import ComparisonMethod, FileMatch, MethodResult

_STRIP_TYPES = {
    "identifier", "string", "integer", "float", "comment",
    "string_content", "escape_sequence",
}


def _subtree_hash(node, src: bytes) -> str:
    """Recursively hash the structural shape of an AST subtree."""
    if not node.children:
        tag = node.type if node.type not in _STRIP_TYPES else "LEAF"
        return hashlib.md5(tag.encode()).hexdigest()[:8]
    child_hashes = "".join(_subtree_hash(c, src) for c in node.children)
    combined = node.type + child_hashes
    return hashlib.md5(combined.encode()).hexdigest()[:8]


def _subtree_fingerprints(path: Path, min_depth: int = 3) -> Counter:
    result = parse(path)
    if result is None:
        return Counter()
    root, src = result
    counts: Counter = Counter()

    def walk(node, depth: int = 0):
        h = _subtree_hash(node, src)
        if depth >= min_depth:
            counts[h] += 1
        for child in node.children:
            walk(child, depth + 1)

    walk(root)
    return counts


def _jaccard_multiset(a: Counter, b: Counter) -> float:
    if not a and not b:
        return 1.0
    intersection = sum((a & b).values())
    union = sum((a | b).values())
    return intersection / union if union else 0.0


class AstStructureMethod(ComparisonMethod):
    method_id = "ast_structure"
    default_weight = 0.20

    def compare(self, root_a, files_a, root_b, files_b, language):
        if not files_a or not files_b:
            return MethodResult(method_id=self.method_id, score=0.0)

        fp_a: Counter = Counter()
        for f in files_a:
            fp_a += _subtree_fingerprints(f)

        file_matches: list[FileMatch] = []
        total_score = 0.0

        for fb in files_b:
            fp_b = _subtree_fingerprints(fb)
            s = _jaccard_multiset(fp_a, fp_b)
            total_score += s
            if s > 0:
                file_matches.append(FileMatch(
                    file_a="(any)",
                    file_b=str(fb.relative_to(root_b)),
                    score=s,
                    detail={"ast_jaccard": round(s, 4)},
                ))

        score = total_score / len(files_b)
        return MethodResult(
            method_id=self.method_id,
            score=score,
            file_matches=file_matches,
            details={"avg_ast_jaccard": round(score, 4)},
        )
