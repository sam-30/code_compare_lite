"""
Line similarity comparison — order-independent.

Normalises each line (strip comments + whitespace, skip blanks and
lines shorter than 4 chars), then checks whether that line appears
anywhere in the other repo.  Score = matched_lines / total_b_lines.
"""
import re
from collections import Counter
from pathlib import Path

from .base import ComparisonMethod, FileMatch, MethodResult

_COMMENT_LINE = re.compile(r"^\s*(#|//|/\*|\*|--)")


def _normalise_line(line: str) -> str | None:
    stripped = line.strip()
    if not stripped or _COMMENT_LINE.match(stripped) or len(stripped) < 4:
        return None
    return stripped


def _file_lines(path: Path) -> set[str]:
    try:
        text = path.read_text(errors="replace")
    except OSError:
        return set()
    result = set()
    for line in text.splitlines():
        norm = _normalise_line(line)
        if norm:
            result.add(norm)
    return result


def _len_stats(lines: set[str]) -> dict:
    if not lines:
        return {"min": 0, "avg": 0.0, "max": 0}
    lengths = [len(l) for l in lines]
    return {
        "min": min(lengths),
        "avg": round(sum(lengths) / len(lengths), 1),
        "max": max(lengths),
    }


class LineSimilarityMethod(ComparisonMethod):
    method_id = "line_similarity"
    default_weight = 0.20

    def compare(self, root_a, files_a, root_b, files_b):
        if not files_a or not files_b:
            return MethodResult(method_id=self.method_id, score=0.0)

        # Build per-file line sets for A, plus a repo-wide union for fast lookup
        file_lines_a: dict[Path, set[str]] = {f: _file_lines(f) for f in files_a}
        repo_lines_a: set[str] = set().union(*file_lines_a.values()) if file_lines_a else set()

        file_matches: list[FileMatch] = []
        total_matched = 0
        total_lines = 0
        all_b_lines: set[str] = set()
        all_matched_lines: set[str] = set()
        # counts how many B files each matched line appears in
        matched_line_freq: Counter = Counter()

        for fb in files_b:
            lines_b = _file_lines(fb)
            if not lines_b:
                continue

            matched = lines_b & repo_lines_a
            n_matched = len(matched)
            n_total = len(lines_b)
            total_matched += n_matched
            total_lines += n_total
            all_b_lines |= lines_b
            all_matched_lines |= matched
            matched_line_freq.update(matched)

            ratio = n_matched / n_total
            if ratio > 0.05:
                # Find which file in A contributes the most lines to this match
                best_fa = max(file_lines_a.items(), key=lambda kv: len(kv[1] & lines_b))
                file_matches.append(FileMatch(
                    file_a=str(best_fa[0].relative_to(root_a)),
                    file_b=str(fb.relative_to(root_b)),
                    score=ratio,
                    detail={
                        "matched_lines": n_matched,
                        "total_b_lines": n_total,
                        "sample_matches": sorted(matched)[:10],
                    },
                ))

        score = total_matched / total_lines if total_lines > 0 else 0.0
        return MethodResult(
            method_id=self.method_id,
            score=score,
            file_matches=file_matches,
            details={
                "matched_lines": total_matched,
                "total_b_lines": total_lines,
                "all_b_lines_char_length": _len_stats(all_b_lines),
                "matched_lines_char_length": _len_stats(all_matched_lines),
                "top_matched_lines": [
                    {"line": line, "file_count": count}
                    for line, count in matched_line_freq.most_common(10)
                ],
            },
        )
