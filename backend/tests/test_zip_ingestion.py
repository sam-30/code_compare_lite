"""Unit tests for app/services/zip_ingestion.py."""
import io
import zipfile
import pytest

from app.services.zip_ingestion import extract_zip


def _make_zip(files: dict[str, str]) -> bytes:
    """Build an in-memory zip from a dict of path → content."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, content in files.items():
            zf.writestr(name, content)
    return buf.getvalue()


class TestExtractZip:
    def test_extracts_files(self, tmp_path):
        zb = _make_zip({"a.py": "x = 1\n", "b.py": "y = 2\n"})
        root = extract_zip(zb, str(tmp_path))
        assert (root / "a.py").read_text() == "x = 1\n"
        assert (root / "b.py").read_text() == "y = 2\n"

    def test_extracts_nested_files(self, tmp_path):
        # Zip has one top-level dir "src/" → it gets unwrapped, so root IS src/
        zb = _make_zip({"src/main.py": "pass\n", "src/util.py": "pass\n"})
        root = extract_zip(zb, str(tmp_path))
        assert (root / "main.py").exists()
        assert (root / "util.py").exists()

    def test_single_top_level_dir_unwrapped(self, tmp_path):
        """A zip with one root directory should be unwrapped to that directory."""
        zb = _make_zip({"myproject/a.py": "x = 1\n", "myproject/b.py": "y = 2\n"})
        root = extract_zip(zb, str(tmp_path))
        # Should unwrap: root is the myproject directory
        assert (root / "a.py").exists() or (root.name == "myproject")

    def test_multiple_top_level_items_not_unwrapped(self, tmp_path):
        """A zip with multiple root items should not be unwrapped."""
        zb = _make_zip({"a.py": "x=1\n", "b.py": "y=2\n"})
        root = extract_zip(zb, str(tmp_path))
        assert (root / "a.py").exists()
        assert (root / "b.py").exists()

    def test_returns_path(self, tmp_path):
        from pathlib import Path
        zb = _make_zip({"a.py": "pass\n"})
        result = extract_zip(zb, str(tmp_path))
        assert isinstance(result, Path)

    def test_invalid_zip_raises(self, tmp_path):
        with pytest.raises(Exception):
            extract_zip(b"not a zip file", str(tmp_path))
