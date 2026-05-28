"""
Import / dependency profile comparison.

Extracts all imported module names from both repos and computes Jaccard
similarity of the two sets.
"""
from pathlib import Path

from app.services.parser import get_language, parse, PY_LANGUAGE, JS_LANGUAGE, TS_LANGUAGE, TSX_LANGUAGE
from .base import ComparisonMethod, MethodResult

_IMPORT_QUERIES = {
    PY_LANGUAGE: """
        (import_statement (dotted_name) @module)
        (import_from_statement module_name: (dotted_name) @module)
        (import_from_statement module_name: (relative_import) @module)
    """,
    JS_LANGUAGE: """
        (import_statement source: (string (string_fragment) @module))
        (call_expression function: (identifier) @require
          arguments: (arguments (string (string_fragment) @module)))
    """,
    TS_LANGUAGE: """
        (import_statement source: (string (string_fragment) @module))
    """,
    TSX_LANGUAGE: """
        (import_statement source: (string (string_fragment) @module))
    """,
}


def _extract_imports(path: Path) -> set[str]:
    result = parse(path)
    if result is None:
        return set()
    root, src = result
    lang = get_language(path)
    if lang is None:
        return set()
    query_str = _IMPORT_QUERIES.get(lang, "")
    if not query_str:
        return set()
    try:
        query = lang.query(query_str)
        captures: dict = query.captures(root)
        modules: set[str] = set()
        for node_list in captures.values():
            for node in node_list:
                name = src[node.start_byte:node.end_byte].decode(errors="replace").strip("\"'")
                # Normalise: use only root package name
                root_pkg = name.split(".")[0].split("/")[0].lstrip(".")
                if root_pkg:
                    modules.add(root_pkg)
        return modules
    except Exception:
        return set()


def _jaccard(a: set, b: set) -> float:
    if not a and not b:
        return 1.0
    union = a | b
    return len(a & b) / len(union) if union else 0.0


class ImportAnalysisMethod(ComparisonMethod):
    method_id = "import_analysis"
    default_weight = 0.05

    def compare(self, root_a, files_a, root_b, files_b, language):
        imports_a: set[str] = set()
        for f in files_a:
            imports_a |= _extract_imports(f)

        imports_b: set[str] = set()
        for f in files_b:
            imports_b |= _extract_imports(f)

        score = _jaccard(imports_a, imports_b)
        shared = sorted(imports_a & imports_b)
        return MethodResult(
            method_id=self.method_id,
            score=score,
            details={
                "shared_imports": shared[:30],
                "shared_count": len(shared),
                "unique_to_a": len(imports_a - imports_b),
                "unique_to_b": len(imports_b - imports_a),
            },
        )
