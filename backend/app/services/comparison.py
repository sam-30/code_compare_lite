import asyncio
import time
from datetime import datetime, timezone
from pathlib import Path

from app.schemas import RepoSource
from app.services.ingestion import collect_files
from app.services.methods.base import ComparisonMethod
from app.services.methods.file_hash import FileHashMethod
from app.services.methods.line_similarity import LineSimilarityMethod
from app.services.methods.function_names import FunctionNamesMethod
from app.services.methods.ast_structure import AstStructureMethod
from app.services.methods.token_ngram import TokenNgramMethod
from app.services.methods.call_graph import CallGraphMethod
from app.services.methods.import_analysis import ImportAnalysisMethod
from app.services.methods.identifier_similarity import IdentifierSimilarityMethod
from app.services.methods.complexity_profile import ComplexityProfileMethod

ALL_METHODS: list[ComparisonMethod] = [
    FileHashMethod(),
    LineSimilarityMethod(),
    FunctionNamesMethod(),
    AstStructureMethod(),
    TokenNgramMethod(),
    CallGraphMethod(),
    ImportAnalysisMethod(),
    IdentifierSimilarityMethod(),
    ComplexityProfileMethod(),
]


def _default_weights() -> dict[str, float]:
    total = sum(m.default_weight for m in ALL_METHODS)
    return {m.method_id: m.default_weight / total for m in ALL_METHODS}


async def run_comparison(
    job_id: str,
    src_a: RepoSource,
    src_b: RepoSource,
    language: str,
    enabled_methods: list[str] | None,
) -> dict:
    import tempfile

    # Resolve repo paths (clone git repos to temp dirs)
    tmp_dirs = []
    try:
        root_a = await _resolve_path(src_a, tmp_dirs)
        root_b = await _resolve_path(src_b, tmp_dirs)

        files_a = collect_files(root_a, language)
        files_b = collect_files(root_b, language)

        weights = _default_weights()
        enabled = set(enabled_methods) if enabled_methods else {m.method_id for m in ALL_METHODS}

        method_results = []
        file_matches = []
        weighted_sum = 0.0
        total_weight = 0.0

        for method in ALL_METHODS:
            if method.method_id not in enabled:
                continue

            weight = weights.get(method.method_id, method.default_weight)
            start = time.monotonic()
            loop = asyncio.get_event_loop()
            try:
                result = await loop.run_in_executor(
                    None, method.compare, root_a, files_a, root_b, files_b, language
                )
            except Exception as exc:
                duration_ms = int((time.monotonic() - start) * 1000)
                method_results.append({
                    "method_id": method.method_id,
                    "score": 0.0,
                    "weight": round(weight, 4),
                    "duration_ms": duration_ms,
                    "details": {"error": str(exc)[:200]},
                })
                continue

            duration_ms = int((time.monotonic() - start) * 1000)

            method_results.append({
                "method_id": result.method_id,
                "score": round(result.score, 4),
                "weight": round(weight, 4),
                "duration_ms": duration_ms,
                "details": result.details,
            })

            for fm in result.file_matches:
                file_matches.append({
                    "file_a_path": fm.file_a,
                    "file_b_path": fm.file_b,
                    "similarity_score": round(fm.score, 4),
                    "method_id": result.method_id,
                    "detail": fm.detail,
                })

            weighted_sum += result.score * weight
            total_weight += weight

        overall = weighted_sum / total_weight if total_weight > 0 else 0.0

        return {
            "job_id": job_id,
            "repo_a_name": src_a.name,
            "repo_b_name": src_b.name,
            "language": language,
            "files_found_a": len(files_a),
            "files_found_b": len(files_b),
            "overall_score": round(overall, 4),
            "methods": method_results,
            "file_matches": sorted(file_matches, key=lambda x: x["similarity_score"], reverse=True)[:200],
            "output_file": f"output/comparison_{job_id}.json",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
    finally:
        import shutil
        for d in tmp_dirs:
            shutil.rmtree(d, ignore_errors=True)


async def _resolve_path(src: RepoSource, tmp_dirs: list) -> Path:
    if src.source == "local":
        return Path(src.path)
    elif src.source == "git":
        import tempfile
        from app.services.git_ingestion import clone_repo
        tmp = tempfile.mkdtemp()
        tmp_dirs.append(tmp)
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, clone_repo, src.url, tmp)
    raise ValueError(f"Unknown source type: {src.source}")
