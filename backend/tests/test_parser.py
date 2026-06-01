"""Unit tests for app/services/parser.py."""
import pytest
from pathlib import Path

from app.services.parser import (
    get_language, parse,
    extract_function_names, extract_identifiers,
    PY_LANGUAGE, JS_LANGUAGE, TS_LANGUAGE, TSX_LANGUAGE,
)


# ── get_language ──────────────────────────────────────────────────────────────

class TestGetLanguage:
    @pytest.mark.parametrize("ext,expected", [
        (".py", PY_LANGUAGE),
        (".js", JS_LANGUAGE),
        (".mjs", JS_LANGUAGE),
        (".cjs", JS_LANGUAGE),
        (".jsx", JS_LANGUAGE),
        (".ts", TS_LANGUAGE),
        (".tsx", TSX_LANGUAGE),
    ])
    def test_known_extensions(self, tmp_path, ext, expected):
        f = tmp_path / f"file{ext}"
        f.touch()
        assert get_language(f) == expected

    def test_unknown_extension_returns_none(self, tmp_path):
        f = tmp_path / "file.rb"
        f.touch()
        assert get_language(f) is None

    def test_no_extension_returns_none(self, tmp_path):
        f = tmp_path / "Makefile"
        f.touch()
        assert get_language(f) is None

    def test_extension_case_insensitive(self, tmp_path):
        f = tmp_path / "SCRIPT.PY"
        f.touch()
        assert get_language(f) == PY_LANGUAGE


# ── parse ─────────────────────────────────────────────────────────────────────

class TestParse:
    def test_parse_valid_python(self, tmp_path):
        f = tmp_path / "a.py"
        f.write_text("x = 1\n")
        result = parse(f)
        assert result is not None
        root, src = result
        assert b"x" in src

    def test_parse_valid_js(self, tmp_path):
        f = tmp_path / "a.js"
        f.write_text("const x = 1;\n")
        result = parse(f)
        assert result is not None

    def test_parse_valid_ts(self, tmp_path):
        f = tmp_path / "a.ts"
        f.write_text("const x: number = 1;\n")
        result = parse(f)
        assert result is not None

    def test_parse_unknown_extension_returns_none(self, tmp_path):
        f = tmp_path / "a.rb"
        f.write_text("x = 1\n")
        assert parse(f) is None

    def test_parse_missing_file_returns_none(self, tmp_path):
        f = tmp_path / "nonexistent.py"
        assert parse(f) is None

    def test_parse_empty_file(self, tmp_path):
        f = tmp_path / "a.py"
        f.write_text("")
        result = parse(f)
        assert result is not None  # empty file is still valid Python

    def test_parse_returns_root_node_and_bytes(self, tmp_path):
        f = tmp_path / "a.py"
        src_text = "def foo(): pass\n"
        f.write_text(src_text)
        root, src = parse(f)
        assert src == src_text.encode()
        assert root.type == "module"


# ── extract_function_names ────────────────────────────────────────────────────

class TestExtractFunctionNames:
    def test_python_function(self, tmp_path):
        f = tmp_path / "a.py"
        f.write_text("def hello():\n    pass\n")
        assert "hello" in extract_function_names(f)

    def test_python_class(self, tmp_path):
        f = tmp_path / "a.py"
        f.write_text("class MyClass:\n    pass\n")
        assert "MyClass" in extract_function_names(f)

    def test_python_multiple(self, tmp_path):
        f = tmp_path / "a.py"
        f.write_text("def foo():\n    pass\n\ndef bar():\n    pass\n")
        names = extract_function_names(f)
        assert "foo" in names
        assert "bar" in names

    def test_js_function_declaration(self, tmp_path):
        f = tmp_path / "a.js"
        f.write_text("function greet(name) { return name; }\n")
        assert "greet" in extract_function_names(f)

    def test_js_class(self, tmp_path):
        f = tmp_path / "a.js"
        f.write_text("class Animal { speak() { return 'roar'; } }\n")
        names = extract_function_names(f)
        assert "Animal" in names

    def test_ts_function(self, tmp_path):
        f = tmp_path / "a.ts"
        f.write_text("function add(a: number, b: number): number { return a + b; }\n")
        assert "add" in extract_function_names(f)

    def test_empty_file_returns_empty_set(self, tmp_path):
        f = tmp_path / "a.py"
        f.write_text("")
        assert extract_function_names(f) == set()

    def test_no_functions_returns_empty_set(self, tmp_path):
        f = tmp_path / "a.py"
        f.write_text("x = 1\ny = 2\n")
        assert extract_function_names(f) == set()

    def test_missing_file_returns_empty_set(self, tmp_path):
        f = tmp_path / "missing.py"
        assert extract_function_names(f) == set()

    def test_unknown_extension_returns_empty_set(self, tmp_path):
        f = tmp_path / "a.rb"
        f.write_text("def hello; end\n")
        assert extract_function_names(f) == set()


# ── extract_identifiers ────────────────────────────────────────────────────────

class TestExtractIdentifiers:
    def test_includes_variable_names(self, tmp_path):
        f = tmp_path / "a.py"
        f.write_text("my_var = 42\n")
        ids = extract_identifiers(f)
        assert "my_var" in ids

    def test_includes_function_name(self, tmp_path):
        f = tmp_path / "a.py"
        f.write_text("def compute(value):\n    return value\n")
        ids = extract_identifiers(f)
        assert "compute" in ids
        assert "value" in ids

    def test_excludes_keywords(self, tmp_path):
        f = tmp_path / "a.py"
        f.write_text("def foo():\n    return None\n")
        ids = extract_identifiers(f)
        assert "return" not in ids
        assert "def" not in ids
        assert "None" not in ids

    def test_empty_file_returns_empty_list(self, tmp_path):
        f = tmp_path / "a.py"
        f.write_text("")
        assert extract_identifiers(f) == []

    def test_missing_file_returns_empty_list(self, tmp_path):
        f = tmp_path / "missing.py"
        assert extract_identifiers(f) == []

    def test_unknown_extension_returns_empty_list(self, tmp_path):
        f = tmp_path / "a.rb"
        f.write_text("x = 1\n")
        assert extract_identifiers(f) == []

    def test_returns_duplicates(self, tmp_path):
        f = tmp_path / "a.py"
        f.write_text("x = 1\nx = 2\n")
        ids = extract_identifiers(f)
        assert ids.count("x") >= 2
