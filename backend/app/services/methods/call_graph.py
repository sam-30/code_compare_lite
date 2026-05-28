"""
Call graph / logic tracing comparison.

Builds a directed call graph per file using tree-sitter queries:
  - nodes = function/method names
  - edges = function A calls function B

Then for each file in Repo B, finds its most similar counterpart in Repo A
using cosine similarity of their degree-sequence vectors (in-degree,
out-degree per node).
"""
import math
from pathlib import Path

import networkx as nx

from app.services.parser import get_language, parse, PY_LANGUAGE, JS_LANGUAGE, TS_LANGUAGE, TSX_LANGUAGE
from .base import ComparisonMethod, FileMatch, MethodResult

# Queries to find call expressions and their callee names
_CALL_QUERIES = {
    PY_LANGUAGE: """
        (call function: (identifier) @callee)
        (call function: (attribute attribute: (identifier) @callee))
    """,
    JS_LANGUAGE: """
        (call_expression function: (identifier) @callee)
        (call_expression function: (member_expression property: (property_identifier) @callee))
    """,
    TS_LANGUAGE: """
        (call_expression function: (identifier) @callee)
        (call_expression function: (member_expression property: (property_identifier) @callee))
    """,
    TSX_LANGUAGE: """
        (call_expression function: (identifier) @callee)
        (call_expression function: (member_expression property: (property_identifier) @callee))
    """,
}


def _build_call_graph(path: Path) -> nx.DiGraph:
    result = parse(path)
    G = nx.DiGraph()
    if result is None:
        return G

    root, src = result
    lang = get_language(path)
    if lang is None:
        return G

    # First collect all defined function names (nodes)
    from app.services.parser import extract_function_names
    func_names = extract_function_names(path)
    for name in func_names:
        G.add_node(name)

    # Find calls using tree-sitter query
    query_str = _CALL_QUERIES.get(lang, "")
    if not query_str:
        return G

    try:
        query = lang.query(query_str)
        captures: dict = query.captures(root)

        # We need the enclosing function for each call to build caller→callee edges.
        # Simplified: build a flat list of callees and connect the first function defined
        # above each call as the caller. For simplicity, we just track which names are called.
        called_names: set[str] = set()
        for node_list in captures.values():
            for node in node_list:
                name = src[node.start_byte:node.end_byte].decode(errors="replace")
                called_names.add(name)

        # Add edges between defined functions and the functions they call
        for caller in func_names:
            for callee in called_names:
                if callee != caller and callee in func_names:
                    G.add_edge(caller, callee)
    except Exception:
        pass

    return G


def _degree_vector(G: nx.DiGraph) -> list[float]:
    if not G.nodes:
        return []
    nodes = sorted(G.nodes())
    vec = []
    for n in nodes:
        vec.append(float(G.in_degree(n)))
        vec.append(float(G.out_degree(n)))
    return vec


def _cosine(a: list[float], b: list[float]) -> float:
    if len(a) != len(b) or not a:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    mag_a = math.sqrt(sum(x**2 for x in a))
    mag_b = math.sqrt(sum(y**2 for y in b))
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot / (mag_a * mag_b)


def _graph_similarity(ga: nx.DiGraph, gb: nx.DiGraph) -> float:
    if ga.number_of_nodes() == 0 and gb.number_of_nodes() == 0:
        return 1.0
    if ga.number_of_nodes() == 0 or gb.number_of_nodes() == 0:
        return 0.0

    # Pad degree vectors to same length
    va = _degree_vector(ga)
    vb = _degree_vector(gb)
    max_len = max(len(va), len(vb))
    va += [0.0] * (max_len - len(va))
    vb += [0.0] * (max_len - len(vb))
    return _cosine(va, vb)


class CallGraphMethod(ComparisonMethod):
    method_id = "call_graph"
    default_weight = 0.10

    def compare(self, root_a, files_a, root_b, files_b, language):
        if not files_a or not files_b:
            return MethodResult(method_id=self.method_id, score=0.0)

        graphs_a = [_build_call_graph(f) for f in files_a]
        file_matches: list[FileMatch] = []
        total_score = 0.0

        for fb in files_b:
            gb = _build_call_graph(fb)
            best = max((_graph_similarity(ga, gb) for ga in graphs_a), default=0.0)
            total_score += best
            if best > 0:
                file_matches.append(FileMatch(
                    file_a="(best match)",
                    file_b=str(fb.relative_to(root_b)),
                    score=best,
                ))

        score = total_score / len(files_b)
        return MethodResult(
            method_id=self.method_id,
            score=score,
            file_matches=file_matches,
            details={"avg_call_graph_sim": round(score, 4)},
        )
