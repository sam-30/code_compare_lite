"""
Line similarity comparison.

For each file in Repo B, find the most similar file in Repo A using
difflib SequenceMatcher.  Reports the fraction of B's lines that appear
in A's closest match.
"""
import difflib
from pathlib import Path

from .base import ComparisonMethod, FileMatch, MethodResult


def _normalise_lines(path: Path) -> list[str]:
    try:
        text = path.read_text(errors="replace")
    except OSError:
        return []
    return [ln.strip() for ln in text.splitlines() if ln.strip()]


def _similarity(lines_a: list[str], lines_b: list[str]) -> float:
    if not lines_a or not lines_b:
        return 0.0
    matcher = difflib.SequenceMatcher(None, lines_a, lines_b, autojunk=False)
    return matcher.ratio()


class LineSimilarityMethod(ComparisonMethod):
    method_id = "line_similarity"
    default_weight = 0.20

    def compare(self, root_a, files_a, root_b, files_b, language):
        if not files_a or not files_b:
            return MethodResult(method_id=self.method_id, score=0.0)

        cached_a = {f: _normalise_lines(f) for f in files_a}
        file_matches: list[FileMatch] = []
        total_score = 0.0

        for fb in files_b:
            lines_b = _normalise_lines(fb)
            best_score = 0.0
            best_fa: Path | None = None
            for fa, lines_a in cached_a.items():
                s = _similarity(lines_a, lines_b)
                if s > best_score:
                    best_score = s
                    best_fa = fa

            total_score += best_score
            if best_fa is not None and best_score > 0:
                file_matches.append(FileMatch(
                    file_a=str(best_fa.relative_to(root_a)),
                    file_b=str(fb.relative_to(root_b)),
                    score=best_score,
                    detail={"line_ratio": round(best_score, 4)},
                ))

        score = total_score / len(files_b)
        return MethodResult(
            method_id=self.method_id,
            score=score,
            file_matches=file_matches,
            details={"avg_best_ratio": round(score, 4)},
        )
