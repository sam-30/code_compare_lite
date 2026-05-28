"""
Thin wrapper around tree-sitter providing a single parse() function
and query helpers for supported languages.
"""
from pathlib import Path
from functools import lru_cache

import tree_sitter_python as tspython
import tree_sitter_javascript as tsjavascript
import tree_sitter_typescript as tstypescript
from tree_sitter import Language, Parser

PY_LANGUAGE = Language(tspython.language())
JS_LANGUAGE = Language(tsjavascript.language())
TS_LANGUAGE = Language(tstypescript.language_typescript())
TSX_LANGUAGE = Language(tstypescript.language_tsx())

_LANG_MAP: dict[str, Language] = {
    ".py": PY_LANGUAGE,
    ".js": JS_LANGUAGE,
    ".mjs": JS_LANGUAGE,
    ".cjs": JS_LANGUAGE,
    ".jsx": JS_LANGUAGE,
    ".ts": TS_LANGUAGE,
    ".tsx": TSX_LANGUAGE,
}

# tree-sitter query strings for function/class/method names
_FUNCTION_QUERIES: dict[Language, str] = {
    PY_LANGUAGE: """
        (function_definition name: (identifier) @name)
        (class_definition name: (identifier) @name)
    """,
    JS_LANGUAGE: """
        (function_declaration name: (identifier) @name)
        (method_definition name: (property_identifier) @name)
        (class_declaration name: (identifier) @name)
    """,
    TS_LANGUAGE: """
        (function_declaration name: (identifier) @name)
        (method_definition name: (property_identifier) @name)
        (class_declaration name: (identifier) @name)
    """,
    TSX_LANGUAGE: """
        (function_declaration name: (identifier) @name)
        (method_definition name: (property_identifier) @name)
        (class_declaration name: (identifier) @name)
    """,
}


@lru_cache(maxsize=4)
def _get_parser(language: Language) -> Parser:
    return Parser(language)


def get_language(path: Path) -> Language | None:
    return _LANG_MAP.get(path.suffix.lower())


def parse(path: Path) -> tuple["tree_sitter.Node", bytes] | None:  # type: ignore[name-defined]
    lang = get_language(path)
    if lang is None:
        return None
    try:
        src = path.read_bytes()
    except OSError:
        return None
    parser = _get_parser(lang)
    tree = parser.parse(src)
    return tree.root_node, src


def extract_function_names(path: Path) -> set[str]:
    result = parse(path)
    if result is None:
        return set()
    root, src = result
    lang = get_language(path)
    query_str = _FUNCTION_QUERIES.get(lang, "")  # type: ignore[arg-type]
    if not query_str:
        return set()
    query = lang.query(query_str)  # type: ignore[union-attr]
    # tree-sitter 0.23 returns dict[capture_name, list[Node]]
    captures: dict = query.captures(root)
    names: set[str] = set()
    for node_list in captures.values():
        for node in node_list:
            names.add(src[node.start_byte:node.end_byte].decode(errors="replace"))
    return names


def extract_identifiers(path: Path) -> list[str]:
    result = parse(path)
    if result is None:
        return []
    root, src = result

    KEYWORD_LIKE = {
        "def", "class", "return", "import", "from", "if", "else", "elif",
        "for", "while", "try", "except", "finally", "with", "as", "pass",
        "break", "continue", "yield", "lambda", "None", "True", "False",
        "function", "const", "let", "var", "new", "this", "super",
        "export", "default", "async", "await",
    }

    identifiers: list[str] = []

    def walk(node):
        if node.type == "identifier":
            name = src[node.start_byte:node.end_byte].decode(errors="replace")
            if name not in KEYWORD_LIKE:
                identifiers.append(name)
        for child in node.children:
            walk(child)

    walk(root)
    return identifiers
