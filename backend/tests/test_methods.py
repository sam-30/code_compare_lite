"""
Unit tests for all 9 comparison methods.

Each method is exercised with small in-memory Python/JS files whose
expected scores can be reasoned about directly.
"""
import pytest
from pathlib import Path


# ── shared helpers ─────────────────────────────────────────────────────────────

def _repo(tmp_path: Path, label: str, files: dict[str, str]):
    """Create a labelled repo directory containing the given files."""
    root = tmp_path / label
    root.mkdir()
    paths = []
    for name, content in files.items():
        p = root / name
        p.write_text(content)
        paths.append(p)
    return root, paths


PY_FUNCS = """\
def add(x, y):
    return x + y

def subtract(x, y):
    return x - y

class Calculator:
    def multiply(self, a, b):
        return a * b
"""

PY_IMPORTS = """\
import os
import sys
from pathlib import Path
from collections import Counter

def main():
    pass
"""

PY_CALLS = """\
def helper():
    return 1

def main():
    result = helper()
    return result
"""

PY_BRANCHES = """\
def complex_func(x, y):
    if x > 0:
        for i in range(x):
            if i % 2 == 0:
                continue
    elif y < 0:
        while y < 0:
            y += 1
    try:
        result = x / y
    except ZeroDivisionError:
        result = 0
    return result

def simple_func():
    return 42
"""

PY_DIFFERENT = """\
class HttpClient:
    def get(self, url):
        pass
    def post(self, url, data):
        pass
    def delete(self, url):
        pass
"""


# ── FileHashMethod ────────────────────────────────────────────────────────────

class TestFileHashMethod:
    @pytest.fixture(autouse=True)
    def _method(self):
        from app.services.methods.file_hash import FileHashMethod
        self.method = FileHashMethod()

    def test_identical_files_score_one(self, tmp_path):
        root_a, files_a = _repo(tmp_path, "a", {"f.py": PY_FUNCS})
        root_b, files_b = _repo(tmp_path, "b", {"f.py": PY_FUNCS})
        result = self.method.compare(root_a, files_a, root_b, files_b)
        assert result.score == 1.0

    def test_different_files_score_zero(self, tmp_path):
        root_a, files_a = _repo(tmp_path, "a", {"f.py": PY_FUNCS})
        root_b, files_b = _repo(tmp_path, "b", {"f.py": PY_DIFFERENT})
        result = self.method.compare(root_a, files_a, root_b, files_b)
        assert result.score == 0.0

    def test_comments_stripped_still_matches(self, tmp_path):
        with_comment = "# header comment\n" + PY_FUNCS
        root_a, files_a = _repo(tmp_path, "a", {"f.py": PY_FUNCS})
        root_b, files_b = _repo(tmp_path, "b", {"f.py": with_comment})
        result = self.method.compare(root_a, files_a, root_b, files_b)
        assert result.score == 1.0

    def test_blank_lines_stripped_still_matches(self, tmp_path):
        with_blanks = "\n\n" + PY_FUNCS + "\n\n"
        root_a, files_a = _repo(tmp_path, "a", {"f.py": PY_FUNCS})
        root_b, files_b = _repo(tmp_path, "b", {"f.py": with_blanks})
        result = self.method.compare(root_a, files_a, root_b, files_b)
        assert result.score == 1.0

    def test_partial_match_is_fraction(self, tmp_path):
        root_a, files_a = _repo(tmp_path, "a", {"f.py": PY_FUNCS})
        root_b, files_b = _repo(tmp_path, "b", {"f.py": PY_FUNCS, "g.py": PY_DIFFERENT})
        result = self.method.compare(root_a, files_a, root_b, files_b)
        assert result.score == pytest.approx(0.5)

    def test_empty_files_b_returns_zero(self, tmp_path):
        root_a, files_a = _repo(tmp_path, "a", {"f.py": PY_FUNCS})
        root_b = tmp_path / "b"
        root_b.mkdir()
        result = self.method.compare(root_a, files_a, root_b, [])
        assert result.score == 0.0

    def test_file_matches_populated(self, tmp_path):
        root_a, files_a = _repo(tmp_path, "a", {"f.py": PY_FUNCS})
        root_b, files_b = _repo(tmp_path, "b", {"f.py": PY_FUNCS})
        result = self.method.compare(root_a, files_a, root_b, files_b)
        assert len(result.file_matches) == 1
        assert result.file_matches[0].score == 1.0

    def test_details_include_counts(self, tmp_path):
        root_a, files_a = _repo(tmp_path, "a", {"f.py": PY_FUNCS})
        root_b, files_b = _repo(tmp_path, "b", {"f.py": PY_FUNCS, "g.py": PY_DIFFERENT})
        result = self.method.compare(root_a, files_a, root_b, files_b)
        assert result.details["matched_files"] == 1
        assert result.details["total_b_files"] == 2


# ── LineSimilarityMethod ──────────────────────────────────────────────────────

class TestLineSimilarityMethod:
    @pytest.fixture(autouse=True)
    def _method(self):
        from app.services.methods.line_similarity import LineSimilarityMethod
        self.method = LineSimilarityMethod()

    def test_identical_content_high_score(self, tmp_path):
        root_a, files_a = _repo(tmp_path, "a", {"f.py": PY_FUNCS})
        root_b, files_b = _repo(tmp_path, "b", {"f.py": PY_FUNCS})
        result = self.method.compare(root_a, files_a, root_b, files_b)
        assert result.score > 0.9

    def test_no_shared_lines_score_zero(self, tmp_path):
        root_a, files_a = _repo(tmp_path, "a", {"f.py": PY_FUNCS})
        root_b, files_b = _repo(tmp_path, "b", {"f.py": PY_DIFFERENT})
        result = self.method.compare(root_a, files_a, root_b, files_b)
        assert result.score < 0.3

    def test_order_independent(self, tmp_path):
        """Reversed-line content should score the same as original."""
        lines = [ln for ln in PY_FUNCS.splitlines() if ln.strip()]
        reversed_content = "\n".join(reversed(lines)) + "\n"
        root_a, files_a = _repo(tmp_path, "a", {"f.py": PY_FUNCS})
        root_b_fwd, files_b_fwd = _repo(tmp_path, "b_fwd", {"f.py": PY_FUNCS})
        root_b_rev, files_b_rev = _repo(tmp_path, "b_rev", {"f.py": reversed_content})
        score_fwd = self.method.compare(root_a, files_a, root_b_fwd, files_b_fwd).score
        score_rev = self.method.compare(root_a, files_a, root_b_rev, files_b_rev).score
        assert score_fwd == pytest.approx(score_rev, abs=0.01)

    def test_comment_only_lines_excluded(self, tmp_path):
        only_comments = "# line one\n# line two\n# line three\n"
        root_a, files_a = _repo(tmp_path, "a", {"f.py": "x = 1\n"})
        root_b, files_b = _repo(tmp_path, "b", {"f.py": only_comments})
        result = self.method.compare(root_a, files_a, root_b, files_b)
        # All B lines are comments, so total_b_lines = 0 → score = 0.0
        assert result.score == 0.0

    def test_stats_in_details(self, tmp_path):
        root_a, files_a = _repo(tmp_path, "a", {"f.py": PY_FUNCS})
        root_b, files_b = _repo(tmp_path, "b", {"f.py": PY_FUNCS})
        result = self.method.compare(root_a, files_a, root_b, files_b)
        d = result.details
        assert "all_b_lines_char_length" in d
        assert "matched_lines_char_length" in d
        for key in ("all_b_lines_char_length", "matched_lines_char_length"):
            stat = d[key]
            assert stat["min"] <= stat["avg"] <= stat["max"]

    def test_top_matched_lines_in_details(self, tmp_path):
        root_a, files_a = _repo(tmp_path, "a", {"f.py": PY_FUNCS})
        root_b, files_b = _repo(tmp_path, "b", {"f.py": PY_FUNCS})
        result = self.method.compare(root_a, files_a, root_b, files_b)
        top = result.details["top_matched_lines"]
        assert isinstance(top, list)
        for entry in top:
            assert "line" in entry
            assert "file_count" in entry

    def test_file_match_detail_fields(self, tmp_path):
        root_a, files_a = _repo(tmp_path, "a", {"f.py": PY_FUNCS})
        root_b, files_b = _repo(tmp_path, "b", {"f.py": PY_FUNCS})
        result = self.method.compare(root_a, files_a, root_b, files_b)
        assert len(result.file_matches) > 0
        fm = result.file_matches[0]
        assert "matched_lines" in fm.detail
        assert "total_b_lines" in fm.detail
        assert "sample_matches" in fm.detail

    def test_empty_files_returns_zero(self, tmp_path):
        root_a, files_a = _repo(tmp_path, "a", {"f.py": PY_FUNCS})
        root_b = tmp_path / "b"
        root_b.mkdir()
        result = self.method.compare(root_a, files_a, root_b, [])
        assert result.score == 0.0


# ── FunctionNamesMethod ────────────────────────────────────────────────────────

class TestFunctionNamesMethod:
    @pytest.fixture(autouse=True)
    def _method(self):
        from app.services.methods.function_names import FunctionNamesMethod
        self.method = FunctionNamesMethod()

    def test_identical_repos_score_one(self, tmp_path):
        root_a, files_a = _repo(tmp_path, "a", {"f.py": PY_FUNCS})
        root_b, files_b = _repo(tmp_path, "b", {"f.py": PY_FUNCS})
        result = self.method.compare(root_a, files_a, root_b, files_b)
        assert result.score == pytest.approx(1.0)

    def test_no_shared_names_score_zero(self, tmp_path):
        root_a, files_a = _repo(tmp_path, "a", {"f.py": PY_FUNCS})
        root_b, files_b = _repo(tmp_path, "b", {"f.py": PY_DIFFERENT})
        result = self.method.compare(root_a, files_a, root_b, files_b)
        assert result.score == 0.0

    def test_partial_overlap(self, tmp_path):
        # PY_FUNCS defines: add, subtract, Calculator, multiply
        # overlap.py defines: add only
        overlap = "def add(a, b):\n    return a + b\n"
        root_a, files_a = _repo(tmp_path, "a", {"f.py": PY_FUNCS})
        root_b, files_b = _repo(tmp_path, "b", {"f.py": overlap})
        result = self.method.compare(root_a, files_a, root_b, files_b)
        assert 0.0 < result.score < 1.0

    def test_shared_names_in_details(self, tmp_path):
        root_a, files_a = _repo(tmp_path, "a", {"f.py": PY_FUNCS})
        root_b, files_b = _repo(tmp_path, "b", {"f.py": PY_FUNCS})
        result = self.method.compare(root_a, files_a, root_b, files_b)
        assert "add" in result.details["shared_names"]

    def test_empty_files_b_score_zero(self, tmp_path):
        root_a, files_a = _repo(tmp_path, "a", {"f.py": PY_FUNCS})
        root_b = tmp_path / "b"
        root_b.mkdir()
        result = self.method.compare(root_a, files_a, root_b, [])
        assert result.score == 0.0

    def test_file_matches_populated(self, tmp_path):
        root_a, files_a = _repo(tmp_path, "a", {"f.py": PY_FUNCS})
        root_b, files_b = _repo(tmp_path, "b", {"f.py": PY_FUNCS})
        result = self.method.compare(root_a, files_a, root_b, files_b)
        assert len(result.file_matches) > 0


# ── AstStructureMethod ────────────────────────────────────────────────────────

class TestAstStructureMethod:
    @pytest.fixture(autouse=True)
    def _method(self):
        from app.services.methods.ast_structure import AstStructureMethod
        self.method = AstStructureMethod()

    def test_identical_code_high_score(self, tmp_path):
        root_a, files_a = _repo(tmp_path, "a", {"f.py": PY_FUNCS})
        root_b, files_b = _repo(tmp_path, "b", {"f.py": PY_FUNCS})
        result = self.method.compare(root_a, files_a, root_b, files_b)
        assert result.score > 0.8

    def test_different_structure_low_score(self, tmp_path):
        trivial = "x = 1\n"
        root_a, files_a = _repo(tmp_path, "a", {"f.py": PY_BRANCHES})
        root_b, files_b = _repo(tmp_path, "b", {"f.py": trivial})
        result = self.method.compare(root_a, files_a, root_b, files_b)
        assert result.score < 0.5

    def test_renamed_identifiers_still_matches(self, tmp_path):
        """AST structure ignores names, so renaming should not lower score much."""
        original = "def foo(x, y):\n    return x + y\n"
        renamed = "def bar(a, b):\n    return a + b\n"
        root_a, files_a = _repo(tmp_path, "a", {"f.py": original})
        root_b, files_b = _repo(tmp_path, "b", {"f.py": renamed})
        result = self.method.compare(root_a, files_a, root_b, files_b)
        assert result.score > 0.5

    def test_empty_inputs_returns_zero(self, tmp_path):
        root_a = tmp_path / "a"
        root_a.mkdir()
        root_b = tmp_path / "b"
        root_b.mkdir()
        result = self.method.compare(root_a, [], root_b, [])
        assert result.score == 0.0

    def test_file_matches_included(self, tmp_path):
        root_a, files_a = _repo(tmp_path, "a", {"f.py": PY_FUNCS})
        root_b, files_b = _repo(tmp_path, "b", {"f.py": PY_FUNCS})
        result = self.method.compare(root_a, files_a, root_b, files_b)
        assert any(fm.score > 0 for fm in result.file_matches)


# ── TokenNgramMethod ───────────────────────────────────────────────────────────

class TestTokenNgramMethod:
    @pytest.fixture(autouse=True)
    def _method(self):
        from app.services.methods.token_ngram import TokenNgramMethod
        self.method = TokenNgramMethod()

    def test_identical_code_high_score(self, tmp_path):
        root_a, files_a = _repo(tmp_path, "a", {"f.py": PY_FUNCS})
        root_b, files_b = _repo(tmp_path, "b", {"f.py": PY_FUNCS})
        result = self.method.compare(root_a, files_a, root_b, files_b)
        assert result.score > 0.8

    def test_different_code_lower_score(self, tmp_path):
        root_a, files_a = _repo(tmp_path, "a", {"f.py": PY_FUNCS})
        root_b_diff, files_b_diff = _repo(tmp_path, "b_diff", {"f.py": PY_DIFFERENT})
        root_b_same, files_b_same = _repo(tmp_path, "b_same", {"f.py": PY_FUNCS})
        score_diff = self.method.compare(root_a, files_a, root_b_diff, files_b_diff).score
        score_same = self.method.compare(root_a, files_a, root_b_same, files_b_same).score
        assert score_diff < score_same

    def test_empty_inputs_returns_zero(self, tmp_path):
        root_a = tmp_path / "a"
        root_a.mkdir()
        root_b = tmp_path / "b"
        root_b.mkdir()
        result = self.method.compare(root_a, [], root_b, [])
        assert result.score == 0.0

    def test_details_include_params(self, tmp_path):
        root_a, files_a = _repo(tmp_path, "a", {"f.py": PY_FUNCS})
        root_b, files_b = _repo(tmp_path, "b", {"f.py": PY_FUNCS})
        result = self.method.compare(root_a, files_a, root_b, files_b)
        assert "k" in result.details
        assert "w" in result.details

    def test_renamed_variables_similar_score(self, tmp_path):
        """Token categories normalize identifiers, so renaming should not hugely affect score."""
        original = "def foo(x, y):\n    result = x + y\n    return result\n"
        renamed = "def bar(a, b):\n    total = a + b\n    return total\n"
        root_a, files_a = _repo(tmp_path, "a", {"f.py": original})
        root_b, files_b = _repo(tmp_path, "b", {"f.py": renamed})
        result = self.method.compare(root_a, files_a, root_b, files_b)
        assert result.score > 0.5


# ── CallGraphMethod ────────────────────────────────────────────────────────────

class TestCallGraphMethod:
    @pytest.fixture(autouse=True)
    def _method(self):
        from app.services.methods.call_graph import CallGraphMethod
        self.method = CallGraphMethod()

    def test_identical_call_patterns_high_score(self, tmp_path):
        root_a, files_a = _repo(tmp_path, "a", {"f.py": PY_CALLS})
        root_b, files_b = _repo(tmp_path, "b", {"f.py": PY_CALLS})
        result = self.method.compare(root_a, files_a, root_b, files_b)
        assert result.score > 0.5

    def test_empty_inputs_returns_zero(self, tmp_path):
        root_a = tmp_path / "a"
        root_a.mkdir()
        root_b = tmp_path / "b"
        root_b.mkdir()
        result = self.method.compare(root_a, [], root_b, [])
        assert result.score == 0.0

    def test_graph_exported_in_details(self, tmp_path):
        root_a, files_a = _repo(tmp_path, "a", {"f.py": PY_CALLS})
        root_b, files_b = _repo(tmp_path, "b", {"f.py": PY_CALLS})
        result = self.method.compare(root_a, files_a, root_b, files_b)
        assert "graph" in result.details
        graph = result.details["graph"]
        assert "nodes" in graph
        assert "edges" in graph

    def test_graph_nodes_have_group(self, tmp_path):
        root_a, files_a = _repo(tmp_path, "a", {"f.py": PY_CALLS})
        root_b, files_b = _repo(tmp_path, "b", {"f.py": PY_CALLS})
        result = self.method.compare(root_a, files_a, root_b, files_b)
        nodes = result.details["graph"]["nodes"]
        assert len(nodes) > 0
        for node in nodes:
            assert node["group"] in ("a", "b", "shared")

    def test_shared_functions_labelled_shared(self, tmp_path):
        root_a, files_a = _repo(tmp_path, "a", {"f.py": PY_CALLS})
        root_b, files_b = _repo(tmp_path, "b", {"f.py": PY_CALLS})
        result = self.method.compare(root_a, files_a, root_b, files_b)
        nodes = {n["id"]: n["group"] for n in result.details["graph"]["nodes"]}
        # helper and main are defined in both repos → should be "shared"
        assert nodes.get("helper") == "shared"
        assert nodes.get("main") == "shared"

    def test_graph_capped_at_60_nodes(self, tmp_path):
        # Create a file with 80 functions to test the cap
        many_funcs = "\n".join(f"def func_{i}():\n    pass" for i in range(80))
        root_a, files_a = _repo(tmp_path, "a", {"f.py": many_funcs})
        root_b, files_b = _repo(tmp_path, "b", {"f.py": many_funcs})
        result = self.method.compare(root_a, files_a, root_b, files_b)
        nodes = result.details["graph"]["nodes"]
        assert len(nodes) <= 60

    def test_graph_edges_have_repo_field(self, tmp_path):
        root_a, files_a = _repo(tmp_path, "a", {"f.py": PY_CALLS})
        root_b, files_b = _repo(tmp_path, "b", {"f.py": PY_CALLS})
        result = self.method.compare(root_a, files_a, root_b, files_b)
        for edge in result.details["graph"]["edges"]:
            assert edge["repo"] in ("a", "b", "shared")


# ── ImportAnalysisMethod ──────────────────────────────────────────────────────

class TestImportAnalysisMethod:
    @pytest.fixture(autouse=True)
    def _method(self):
        from app.services.methods.import_analysis import ImportAnalysisMethod
        self.method = ImportAnalysisMethod()

    def test_identical_imports_score_one(self, tmp_path):
        root_a, files_a = _repo(tmp_path, "a", {"f.py": PY_IMPORTS})
        root_b, files_b = _repo(tmp_path, "b", {"f.py": PY_IMPORTS})
        result = self.method.compare(root_a, files_a, root_b, files_b)
        assert result.score == pytest.approx(1.0)

    def test_no_shared_imports_score_zero(self, tmp_path):
        a_code = "import os\nimport sys\n"
        b_code = "import json\nimport re\n"
        root_a, files_a = _repo(tmp_path, "a", {"f.py": a_code})
        root_b, files_b = _repo(tmp_path, "b", {"f.py": b_code})
        result = self.method.compare(root_a, files_a, root_b, files_b)
        assert result.score == 0.0

    def test_shared_imports_in_details(self, tmp_path):
        root_a, files_a = _repo(tmp_path, "a", {"f.py": PY_IMPORTS})
        root_b, files_b = _repo(tmp_path, "b", {"f.py": PY_IMPORTS})
        result = self.method.compare(root_a, files_a, root_b, files_b)
        assert "os" in result.details["shared_imports"]
        assert "sys" in result.details["shared_imports"]

    def test_root_package_normalised(self, tmp_path):
        a_code = "from pathlib import Path\n"
        b_code = "import pathlib\n"
        root_a, files_a = _repo(tmp_path, "a", {"f.py": a_code})
        root_b, files_b = _repo(tmp_path, "b", {"f.py": b_code})
        result = self.method.compare(root_a, files_a, root_b, files_b)
        assert result.score == pytest.approx(1.0)

    def test_js_imports(self, tmp_path):
        js_a = "import React from 'react';\nimport { useState } from 'react';\n"
        js_b = "import React from 'react';\n"
        root_a, files_a = _repo(tmp_path, "a", {"f.js": js_a})
        root_b, files_b = _repo(tmp_path, "b", {"f.js": js_b})
        result = self.method.compare(root_a, files_a, root_b, files_b)
        assert result.score == pytest.approx(1.0)

    def test_details_include_unique_counts(self, tmp_path):
        a_code = "import os\nimport sys\nimport json\n"
        b_code = "import os\nimport re\n"
        root_a, files_a = _repo(tmp_path, "a", {"f.py": a_code})
        root_b, files_b = _repo(tmp_path, "b", {"f.py": b_code})
        result = self.method.compare(root_a, files_a, root_b, files_b)
        assert result.details["unique_to_a"] >= 2  # sys, json
        assert result.details["unique_to_b"] >= 1  # re


# ── IdentifierSimilarityMethod ────────────────────────────────────────────────

class TestIdentifierSimilarityMethod:
    @pytest.fixture(autouse=True)
    def _method(self):
        from app.services.methods.identifier_similarity import IdentifierSimilarityMethod
        self.method = IdentifierSimilarityMethod()

    def test_identical_code_high_score(self, tmp_path):
        root_a, files_a = _repo(tmp_path, "a", {"f.py": PY_FUNCS})
        root_b, files_b = _repo(tmp_path, "b", {"f.py": PY_FUNCS})
        result = self.method.compare(root_a, files_a, root_b, files_b)
        assert result.score > 0.8

    def test_different_identifiers_low_score(self, tmp_path):
        a_code = "def alpha(beta, gamma):\n    return delta\n"
        b_code = "def omega(sigma, tau):\n    return upsilon\n"
        root_a, files_a = _repo(tmp_path, "a", {"f.py": a_code})
        root_b, files_b = _repo(tmp_path, "b", {"f.py": b_code})
        result = self.method.compare(root_a, files_a, root_b, files_b)
        assert result.score == 0.0

    def test_keywords_excluded(self, tmp_path):
        a_code = "def foo():\n    return None\n"
        b_code = "def bar():\n    return None\n"
        root_a, files_a = _repo(tmp_path, "a", {"f.py": a_code})
        root_b, files_b = _repo(tmp_path, "b", {"f.py": b_code})
        result = self.method.compare(root_a, files_a, root_b, files_b)
        # "return" and "None" are filtered, so only "foo"/"bar" remain → no overlap
        assert result.score == 0.0

    def test_details_include_shared_identifiers(self, tmp_path):
        root_a, files_a = _repo(tmp_path, "a", {"f.py": PY_FUNCS})
        root_b, files_b = _repo(tmp_path, "b", {"f.py": PY_FUNCS})
        result = self.method.compare(root_a, files_a, root_b, files_b)
        assert len(result.details["shared_identifiers"]) > 0

    def test_empty_files_score_zero(self, tmp_path):
        root_a = tmp_path / "a"
        root_a.mkdir()
        root_b = tmp_path / "b"
        root_b.mkdir()
        result = self.method.compare(root_a, [], root_b, [])
        assert result.score == 0.0


# ── ComplexityProfileMethod ───────────────────────────────────────────────────

class TestComplexityProfileMethod:
    @pytest.fixture(autouse=True)
    def _method(self):
        from app.services.methods.complexity_profile import ComplexityProfileMethod
        self.method = ComplexityProfileMethod()

    def test_identical_code_high_score(self, tmp_path):
        root_a, files_a = _repo(tmp_path, "a", {"f.py": PY_BRANCHES})
        root_b, files_b = _repo(tmp_path, "b", {"f.py": PY_BRANCHES})
        result = self.method.compare(root_a, files_a, root_b, files_b)
        assert result.score > 0.9

    def test_no_branches_vs_many_branches_lower_score(self, tmp_path):
        simple = "def foo():\n    return 1\n"
        root_a, files_a = _repo(tmp_path, "a", {"f.py": simple})
        root_b_complex, files_b_complex = _repo(tmp_path, "b_complex", {"f.py": PY_BRANCHES})
        root_b_simple, files_b_simple = _repo(tmp_path, "b_simple", {"f.py": simple})
        score_mismatch = self.method.compare(root_a, files_a, root_b_complex, files_b_complex).score
        score_identical = self.method.compare(root_a, files_a, root_b_simple, files_b_simple).score
        assert score_mismatch < score_identical

    def test_details_include_func_counts(self, tmp_path):
        root_a, files_a = _repo(tmp_path, "a", {"f.py": PY_BRANCHES})
        root_b, files_b = _repo(tmp_path, "b", {"f.py": PY_BRANCHES})
        result = self.method.compare(root_a, files_a, root_b, files_b)
        assert result.details["a_func_count"] > 0
        assert result.details["b_func_count"] > 0

    def test_empty_inputs_returns_zero(self, tmp_path):
        root_a = tmp_path / "a"
        root_a.mkdir()
        root_b = tmp_path / "b"
        root_b.mkdir()
        result = self.method.compare(root_a, [], root_b, [])
        assert result.score == 0.0

    def test_score_in_range(self, tmp_path):
        root_a, files_a = _repo(tmp_path, "a", {"f.py": PY_BRANCHES})
        root_b, files_b = _repo(tmp_path, "b", {"f.py": PY_DIFFERENT})
        result = self.method.compare(root_a, files_a, root_b, files_b)
        assert 0.0 <= result.score <= 1.0
