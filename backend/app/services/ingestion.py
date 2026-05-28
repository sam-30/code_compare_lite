import hashlib
from pathlib import Path

LANGUAGE_EXTENSIONS: dict[str, set[str]] = {
    "python": {".py"},
    "javascript": {".js", ".ts", ".jsx", ".tsx", ".mjs", ".cjs"},
}

IGNORED_DIRS = {
    ".git", ".hg", ".svn", "__pycache__", ".mypy_cache",
    "node_modules", ".venv", "venv", "env", ".env",
    "dist", "build", ".next", ".nuxt", "coverage",
    ".pytest_cache", ".ruff_cache",
}


def collect_files(root: Path, language: str) -> list[Path]:
    extensions = LANGUAGE_EXTENSIONS.get(language, set())
    results: list[Path] = []
    for p in root.rglob("*"):
        if any(part in IGNORED_DIRS for part in p.parts):
            continue
        if p.is_file() and p.suffix in extensions:
            results.append(p)
    return sorted(results)
