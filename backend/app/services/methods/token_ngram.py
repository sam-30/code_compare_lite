"""
Token n-gram fingerprinting (Winnowing algorithm, as used by MOSS/JPlag).

1. Tokenise each file using tree-sitter leaf nodes (type stripped to category).
2. Build k-grams and hash each.
3. Apply a rolling window to select the minimum hash per window (Winnowing).
4. Compare the two fingerprint multi-sets.
"""
import hashlib
from collections import Counter
from pathlib import Path

from app.services.parser import parse
from .base import ComparisonMethod, MethodResult

K = 5    # k-gram size
W = 4    # window size for winnowing


_SKIP = object()  # sentinel: skip this token entirely

_CATEGORY = {
    "identifier": "ID",
    "integer": "NUM",
    "float": "NUM",
    "string": "STR",
    "string_content": "STR",
    "comment": _SKIP,
    "line_comment": _SKIP,
    "block_comment": _SKIP,
}


def _tokenise(path: Path) -> list[str]:
    result = parse(path)
    if result is None:
        return []
    root, src = result
    tokens: list[str] = []

    def walk(node):
        if not node.children:
            cat = _CATEGORY.get(node.type, node.type)  # default: use raw type
            if cat is _SKIP:
                return
            tokens.append(cat)
        for child in node.children:
            walk(child)

    walk(root)
    return tokens


def _kgram_hashes(tokens: list[str], k: int) -> list[int]:
    if len(tokens) < k:
        return []
    hashes = []
    for i in range(len(tokens) - k + 1):
        gram = "".join(tokens[i:i+k])
        h = int(hashlib.md5(gram.encode()).hexdigest(), 16) % (2**32)
        hashes.append(h)
    return hashes


def _winnow(hashes: list[int], w: int) -> Counter:
    if not hashes:
        return Counter()
    fingerprints: Counter = Counter()
    for i in range(len(hashes) - w + 1):
        window = hashes[i:i+w]
        fingerprints[min(window)] += 1
    return fingerprints


def _fingerprint(path: Path) -> Counter:
    tokens = _tokenise(path)
    hashes = _kgram_hashes(tokens, K)
    return _winnow(hashes, W)


def _jaccard(a: Counter, b: Counter) -> float:
    if not a and not b:
        return 1.0
    intersection = sum((a & b).values())
    union = sum((a | b).values())
    return intersection / union if union else 0.0


class TokenNgramMethod(ComparisonMethod):
    method_id = "token_ngram"
    default_weight = 0.20

    def compare(self, root_a, files_a, root_b, files_b, language):
        if not files_a or not files_b:
            return MethodResult(method_id=self.method_id, score=0.0)

        fp_a: Counter = Counter()
        for f in files_a:
            fp_a += _fingerprint(f)

        total_score = 0.0
        for fb in files_b:
            fp_b = _fingerprint(fb)
            total_score += _jaccard(fp_a, fp_b)

        score = total_score / len(files_b)
        return MethodResult(
            method_id=self.method_id,
            score=score,
            details={"avg_ngram_jaccard": round(score, 4), "k": K, "w": W},
        )
