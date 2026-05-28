"""Tests for file collection and language detection (ingestion.py)."""
from pathlib import Path

from app.services.ingestion import collect_files, detect_language


def _touch(root: Path, *rel_paths: str) -> list[Path]:
    """Create empty files at the given relative paths under root."""
    created = []
    for rel in rel_paths:
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.touch()
        created.append(p)
    return created


# ── collect_files ──────────────────────────────────────────────────────────────

class TestCollectFiles:
    def test_collects_py_files(self, tmp_path):
        _touch(tmp_path, "a.py", "b.py", "sub/c.py")
        result = collect_files(tmp_path)
        assert len(result) == 3
        assert all(p.suffix == ".py" for p in result)

    def test_collects_js_extensions(self, tmp_path):
        _touch(tmp_path, "a.js", "b.ts", "c.jsx", "d.tsx", "e.mjs", "f.cjs")
        result = collect_files(tmp_path)
        assert len(result) == 6

    def test_collects_python_and_js_together(self, tmp_path):
        _touch(tmp_path, "server.py", "client.js", "types.ts")
        result = collect_files(tmp_path)
        assert len(result) == 3

    def test_ignores_non_source_extensions(self, tmp_path):
        _touch(tmp_path, "app.py", "README.md", "image.png", "data.json", "style.css")
        result = collect_files(tmp_path)
        assert len(result) == 1
        assert result[0].name == "app.py"

    def test_ignores_node_modules(self, tmp_path):
        _touch(tmp_path, "src/app.js", "node_modules/lib/index.js")
        result = collect_files(tmp_path)
        assert len(result) == 1
        assert "node_modules" not in result[0].relative_to(tmp_path).parts

    def test_ignores_pycache(self, tmp_path):
        _touch(tmp_path, "app.py")
        # Even if __pycache__ somehow contained a .py file it must be skipped
        cache_py = tmp_path / "__pycache__" / "cached.py"
        cache_py.parent.mkdir(parents=True, exist_ok=True)
        cache_py.touch()
        result = collect_files(tmp_path)
        assert len(result) == 1
        assert result[0].name == "app.py"

    def test_ignores_git_dir(self, tmp_path):
        _touch(tmp_path, "main.py")
        git_py = tmp_path / ".git" / "hooks" / "pre-commit.py"
        git_py.parent.mkdir(parents=True, exist_ok=True)
        git_py.touch()
        result = collect_files(tmp_path)
        assert len(result) == 1
        assert result[0].name == "main.py"

    def test_ignores_venv_dirs(self, tmp_path):
        _touch(tmp_path, "app.py", "venv/lib/site.py", ".venv/lib/compat.py", "env/util.py")
        result = collect_files(tmp_path)
        assert len(result) == 1
        assert result[0].name == "app.py"

    def test_ignores_dist_and_build(self, tmp_path):
        _touch(tmp_path, "src/main.js", "dist/bundle.js", "build/out.js")
        result = collect_files(tmp_path)
        assert len(result) == 1
        assert result[0].parts[-2] == "src"

    def test_returns_sorted(self, tmp_path):
        _touch(tmp_path, "z.py", "a.py", "m.py")
        result = collect_files(tmp_path)
        assert result == sorted(result)

    def test_empty_dir_returns_empty_list(self, tmp_path):
        assert collect_files(tmp_path) == []

    def test_extension_matching_is_case_insensitive(self, tmp_path):
        _touch(tmp_path, "Script.PY", "Module.JS")
        result = collect_files(tmp_path)
        assert len(result) == 2


# ── detect_language ────────────────────────────────────────────────────────────

class TestDetectLanguage:
    def test_python_only(self, tmp_path):
        paths = _touch(tmp_path, "a.py", "b.py")
        assert detect_language(paths) == "python"

    def test_javascript_js(self, tmp_path):
        paths = _touch(tmp_path, "a.js")
        assert detect_language(paths) == "javascript"

    def test_typescript(self, tmp_path):
        paths = _touch(tmp_path, "a.ts")
        assert detect_language(paths) == "javascript"

    def test_jsx(self, tmp_path):
        paths = _touch(tmp_path, "app.jsx")
        assert detect_language(paths) == "javascript"

    def test_tsx(self, tmp_path):
        paths = _touch(tmp_path, "app.tsx")
        assert detect_language(paths) == "javascript"

    def test_mjs_and_cjs(self, tmp_path):
        paths = _touch(tmp_path, "bundle.mjs", "require.cjs")
        assert detect_language(paths) == "javascript"

    def test_mixed_py_and_js(self, tmp_path):
        paths = _touch(tmp_path, "server.py", "client.js")
        assert detect_language(paths) == "mixed"

    def test_mixed_py_and_ts(self, tmp_path):
        paths = _touch(tmp_path, "server.py", "client.ts")
        assert detect_language(paths) == "mixed"

    def test_unknown_for_unrecognised_extensions(self, tmp_path):
        paths = _touch(tmp_path, "README.md", "data.json")
        assert detect_language(paths) == "unknown"

    def test_unknown_for_empty_list(self):
        assert detect_language([]) == "unknown"

    def test_extension_matching_is_case_insensitive(self, tmp_path):
        paths = _touch(tmp_path, "App.PY")
        assert detect_language(paths) == "python"
