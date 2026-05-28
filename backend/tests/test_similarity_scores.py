"""
End-to-end similarity score tests.

Four fixture pairs with known characteristics verify that the comparison
engine produces meaningfully different scores for different levels of
code overlap. Tests also assert strict ordering:

    identical > high_similarity > low_similarity

and that the bug where empty-set methods returned 1.0 (producing the
same score for unrelated repos) is gone.
"""
import pytest
from httpx import AsyncClient

from tests.conftest import FIXTURES, run_comparison


# ── Individual scenario tests ─────────────────────────────────────────────────

async def test_identical_repos_score_near_perfect(client: AsyncClient):
    """Exact file copies must score > 0.85 across all methods."""
    result = await run_comparison(
        client,
        FIXTURES / "identical_a",
        FIXTURES / "identical_b",
    )
    score = result["overall_score"]
    assert score > 0.85, (
        f"Identical repos scored {score:.3f} — expected > 0.85.\n"
        f"Methods: {_method_summary(result)}"
    )
    assert result["files_found_a"] > 0, "No Python files found in identical_a"
    assert result["files_found_b"] > 0, "No Python files found in identical_b"


async def test_similar_repos_score_moderate(client: AsyncClient):
    """Same algorithms with renamed identifiers must score between 0.30 and 0.85."""
    result = await run_comparison(
        client,
        FIXTURES / "similar_a",
        FIXTURES / "similar_b",
    )
    score = result["overall_score"]
    assert 0.30 < score < 0.85, (
        f"High-similarity repos scored {score:.3f} — expected between 0.30 and 0.85.\n"
        f"Methods: {_method_summary(result)}"
    )


async def test_different_repos_score_low(client: AsyncClient):
    """Completely unrelated codebases must score < 0.20."""
    result = await run_comparison(
        client,
        FIXTURES / "different_a",
        FIXTURES / "different_b",
    )
    score = result["overall_score"]
    assert score < 0.20, (
        f"Different repos scored {score:.3f} — expected < 0.20.\n"
        f"Methods: {_method_summary(result)}"
    )


# ── Ordering test ─────────────────────────────────────────────────────────────

async def test_scores_are_strictly_ordered(client: AsyncClient):
    """identical > similar > different — all three must be distinct."""
    score_identical = (await run_comparison(
        client, FIXTURES / "identical_a", FIXTURES / "identical_b",
    ))["overall_score"]

    score_similar = (await run_comparison(
        client, FIXTURES / "similar_a", FIXTURES / "similar_b",
    ))["overall_score"]

    score_different = (await run_comparison(
        client, FIXTURES / "different_a", FIXTURES / "different_b",
    ))["overall_score"]

    assert score_identical > score_similar, (
        f"identical ({score_identical:.3f}) should be > similar ({score_similar:.3f})"
    )
    assert score_similar > score_different, (
        f"similar ({score_similar:.3f}) should be > different ({score_different:.3f})"
    )


# ── Regression: no fixed score from empty-set bug ────────────────────────────

async def test_different_repos_do_not_share_score_with_similar(client: AsyncClient):
    """
    Regression for the bug where empty-set Jaccard returned 1.0,
    causing unrelated repos to produce the same score as similar ones.
    """
    score_similar = (await run_comparison(
        client, FIXTURES / "similar_a", FIXTURES / "similar_b",
    ))["overall_score"]

    score_different = (await run_comparison(
        client, FIXTURES / "different_a", FIXTURES / "different_b",
    ))["overall_score"]

    assert score_similar != score_different, (
        f"similar and different repos both scored {score_similar:.4f} — "
        "the empty-set bug may have returned."
    )
    # Verify the gap is substantial, not just floating-point noise
    assert abs(score_similar - score_different) > 0.10, (
        f"Scores are too close: similar={score_similar:.4f}, different={score_different:.4f}. "
        "Expected a gap of at least 0.10."
    )


# ── Method-level assertions ───────────────────────────────────────────────────

async def test_file_hash_detects_identical_files(client: AsyncClient):
    """file_hash method must return 1.0 for exact copies."""
    result = await run_comparison(
        client, FIXTURES / "identical_a", FIXTURES / "identical_b",
    )
    methods = {m["method_id"]: m for m in result["methods"]}
    fh = methods.get("file_hash")
    assert fh is not None, "file_hash method not present in results"
    assert fh["score"] == 1.0, f"file_hash scored {fh['score']} on identical files — expected 1.0"


async def test_file_hash_zero_for_different_files(client: AsyncClient):
    """file_hash must return 0.0 for completely different codebases."""
    result = await run_comparison(
        client, FIXTURES / "different_a", FIXTURES / "different_b",
    )
    methods = {m["method_id"]: m for m in result["methods"]}
    fh = methods.get("file_hash")
    assert fh is not None
    assert fh["score"] == 0.0, f"file_hash scored {fh['score']} on different files — expected 0.0"


async def test_function_names_shared_on_identical(client: AsyncClient):
    """function_names details must list shared names for identical repos."""
    result = await run_comparison(
        client, FIXTURES / "identical_a", FIXTURES / "identical_b",
    )
    methods = {m["method_id"]: m for m in result["methods"]}
    fn = methods.get("function_names")
    assert fn is not None
    assert fn["score"] > 0.8, f"function_names scored {fn['score']} on identical repos"
    shared = fn["details"].get("shared_names", [])
    assert len(shared) > 0, "function_names returned no shared names for identical repos"


async def test_no_method_errors(client: AsyncClient):
    """No method should record an error field for valid repos."""
    for pair in [("identical_a", "identical_b"), ("similar_a", "similar_b"), ("different_a", "different_b")]:
        result = await run_comparison(
            client, FIXTURES / pair[0], FIXTURES / pair[1],
        )
        for m in result["methods"]:
            assert "error" not in m["details"], (
                f"Method {m['method_id']} has an error for pair {pair}: {m['details'].get('error')}"
            )


async def test_file_counts_reported(client: AsyncClient):
    """Result must include how many files were indexed per repo."""
    result = await run_comparison(
        client, FIXTURES / "identical_a", FIXTURES / "identical_b",
    )
    assert "files_found_a" in result
    assert "files_found_b" in result
    assert result["files_found_a"] == 1
    assert result["files_found_b"] == 1


async def test_line_similarity_returns_matching_blocks(client: AsyncClient):
    """line_similarity file matches must include matching_blocks for identical repos."""
    result = await run_comparison(
        client, FIXTURES / "identical_a", FIXTURES / "identical_b",
    )
    line_matches = [fm for fm in result["file_matches"] if fm["method_id"] == "line_similarity"]
    assert len(line_matches) > 0, "No line_similarity file matches for identical repos"
    for fm in line_matches:
        assert "matching_blocks" in fm["detail"], "matching_blocks missing from line_similarity detail"
        blocks = fm["detail"]["matching_blocks"]
        assert len(blocks) > 0, "No matching blocks found for identical files"
        for block in blocks:
            assert "lines" in block
            assert "a_line_start" in block
            assert "b_line_start" in block
            assert block["length"] >= 3


# ── Helpers ───────────────────────────────────────────────────────────────────

def _method_summary(result: dict) -> str:
    return ", ".join(
        f"{m['method_id']}={m['score']:.3f}"
        for m in result.get("methods", [])
    )
