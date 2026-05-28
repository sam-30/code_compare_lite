"""
Line similarity comparison.

For each file in Repo B, find the most similar file in Repo A using
difflib SequenceMatcher. Reports the fraction of matching lines and
includes the actual matching code blocks.
"""
import difflib
from pathlib import Path

from .base import ComparisonMethod, FileMatch, MethodResult


def _read_lines(path: Path) -> list[str]:
    try:
        text = path.read_text(errors="replace")
    except OSError:
        return []
    return [ln.strip() for ln in text.splitlines() if ln.strip()]


def _read_lines_raw(path: Path) -> list[str]:
    """Read lines preserving original formatting for display."""
    try:
        return path.read_text(errors="replace").splitlines()
    except OSError:
        return []


def _match_blocks(lines_a: list[str], lines_b: list[str], raw_b: list[str]) -> list[dict]:
    """Return the top matching blocks with actual line content."""
    matcher = difflib.SequenceMatcher(None, lines_a, lines_b, autojunk=False)
    blocks = []
    for block in matcher.get_matching_blocks():
        if block.size < 3:
            continue
        # Map back to raw (un-stripped) lines for display
        snippet = raw_b[block.b: block.b + block.size][:8]
        blocks.append({
            "a_line_start": block.a + 1,
            "b_line_start": block.b + 1,
            "length": block.size,
            "lines": snippet,
        })
    # Return top blocks by length
    return sorted(blocks, key=lambda x: x["length"], reverse=True)[:5]


class LineSimilarityMethod(ComparisonMethod):
    method_id = "line_similarity"
    default_weight = 0.20

    def compare(self, root_a, files_a, root_b, files_b):
        if not files_a or not files_b:
            return MethodResult(method_id=self.method_id, score=0.0)

        cached_a = {f: _read_lines(f) for f in files_a}
        file_matches: list[FileMatch] = []
        total_score = 0.0

        for fb in files_b:
            lines_b = _read_lines(fb)
            if not lines_b:
                continue

            best_score = 0.0
            best_fa: Path | None = None
            for fa, lines_a in cached_a.items():
                if not lines_a:
                    continue
                matcher = difflib.SequenceMatcher(None, lines_a, lines_b, autojunk=False)
                s = matcher.ratio()
                if s > best_score:
                    best_score = s
                    best_fa = fa

            total_score += best_score
            if best_fa is not None and best_score > 0.05:
                raw_b = _read_lines_raw(fb)
                blocks = _match_blocks(cached_a[best_fa], lines_b, raw_b)
                file_matches.append(FileMatch(
                    file_a=str(best_fa.relative_to(root_a)),
                    file_b=str(fb.relative_to(root_b)),
                    score=best_score,
                    detail={
                        "line_ratio": round(best_score, 4),
                        "matching_blocks": blocks,
                    },
                ))

        if not files_b:
            score = 0.0
        else:
            score = total_score / len(files_b)

        return MethodResult(
            method_id=self.method_id,
            score=score,
            file_matches=file_matches,
            details={"avg_best_ratio": round(score, 4)},
        )
