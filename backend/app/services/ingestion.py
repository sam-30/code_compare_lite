from pathlib import Path

LANGUAGE_EXTENSIONS: dict[str, set[str]] = {
    "python": {".py"},
    "javascript": {".js", ".ts", ".jsx", ".tsx", ".mjs", ".cjs"},
}

ALL_EXTENSIONS: set[str] = {ext for exts in LANGUAGE_EXTENSIONS.values() for ext in exts}

IGNORED_DIRS = {
    ".git", ".hg", ".svn", "__pycache__", ".mypy_cache",
    "node_modules", ".venv", "venv", "env", ".env",
    "dist", "build", ".next", ".nuxt", "coverage",
    ".pytest_cache", ".ruff_cache",
}


def collect_files(root: Path) -> list[Path]:
    results: list[Path] = []
    for p in root.rglob("*"):
        if any(part in IGNORED_DIRS for part in p.parts):
            continue
        if p.is_file() and p.suffix.lower() in ALL_EXTENSIONS:
            results.append(p)
    return sorted(results)


def detect_language(files: list[Path]) -> str:
    """Return 'python', 'javascript', or 'mixed' based on file extensions found."""
    py_exts = LANGUAGE_EXTENSIONS["python"]
    js_exts = LANGUAGE_EXTENSIONS["javascript"]
    has_py = any(f.suffix.lower() in py_exts for f in files)
    has_js = any(f.suffix.lower() in js_exts for f in files)
    if has_py and has_js:
        return "mixed"
    if has_py:
        return "python"
    if has_js:
        return "javascript"
    return "unknown"
