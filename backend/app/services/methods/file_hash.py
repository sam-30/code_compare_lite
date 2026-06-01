"""
File hash comparison.

Normalises each file (strip comments + blank lines) then SHA-256 hashes it.
Computes the fraction of files in Repo B whose normalised hash matches ANY
file in Repo A.

Common boilerplate files (empty package markers, auto-generated indexes, etc.)
are excluded from the comparison so they don't inflate the score.
"""
import hashlib
import re
from pathlib import Path

from .base import ComparisonMethod, FileMatch, MethodResult

_BLANK_OR_COMMENT = re.compile(
    r"^\s*$|^\s*(#|//|/\*|\*|--)", re.MULTILINE
)

# Files that are almost always identical boilerplate across projects and should
# not be counted as evidence of similarity.
IGNORED_FILENAMES = frozenset({
    # Python package / tooling markers
    "__init__.py",
    "__main__.py",
    "conftest.py",
    "setup.py",
    # JavaScript / TypeScript barrel files
    "index.js",
    "index.ts",
    "index.jsx",
    "index.tsx",
    "index.mjs",
    "index.cjs",
})


def _normalise(content: str) -> str:
    lines = [
        ln for ln in content.splitlines()
        if not _BLANK_OR_COMMENT.match(ln)
    ]
    return "\n".join(lines)


def _hash_file(path: Path) -> str:
    try:
        text = path.read_text(errors="replace")
    except OSError:
        return ""
    normalised = _normalise(text)
    return hashlib.sha256(normalised.encode()).hexdigest()


def _keep(path: Path) -> bool:
    return path.name not in IGNORED_FILENAMES


class FileHashMethod(ComparisonMethod):
    method_id = "file_hash"
    default_weight = 0.15

    def compare(self, root_a, files_a, root_b, files_b):
        files_a = [f for f in files_a if _keep(f)]
        files_b = [f for f in files_b if _keep(f)]

        hashes_a = {_hash_file(f) for f in files_a if f}
        hashes_a.discard("")

        if not files_b:
            return MethodResult(
                method_id=self.method_id,
                score=0.0,
                details={"matched_files": 0, "total_b_files": 0},
            )

        matches: list[FileMatch] = []
        matched = 0
        for fb in files_b:
            hb = _hash_file(fb)
            if hb and hb in hashes_a:
                matched += 1
                rel_b = str(fb.relative_to(root_b))
                for fa in files_a:
                    if _hash_file(fa) == hb:
                        matches.append(FileMatch(
                            file_a=str(fa.relative_to(root_a)),
                            file_b=rel_b,
                            score=1.0,
                            detail={"hash": hb[:16] + "…"},
                        ))
                        break

        score = matched / len(files_b)
        return MethodResult(
            method_id=self.method_id,
            score=score,
            file_matches=matches,
            details={"matched_files": matched, "total_b_files": len(files_b)},
        )
