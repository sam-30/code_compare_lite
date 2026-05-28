import json
import uuid
from pathlib import Path
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, UploadFile

from app.config import settings
from app.schemas import CompareRequest, RepoSource

router = APIRouter()

# In-memory job store: job_id -> {status, result, error}
_jobs: dict = {}


@router.post("/compare")
async def create_comparison(payload: CompareRequest, background_tasks: BackgroundTasks):
    job_id = str(uuid.uuid4())[:8]
    _jobs[job_id] = {"status": "running", "result": None, "error": None}
    background_tasks.add_task(_run_job, job_id, payload)
    return {"job_id": job_id}


@router.post("/compare/upload")
async def create_comparison_upload(
    repo_a_name: str = Form(...),
    repo_b_name: str = Form(...),
    repo_a_zip: UploadFile = File(...),
    repo_b_zip: UploadFile = File(...),
    background_tasks: BackgroundTasks = BackgroundTasks(),
):
    job_id = str(uuid.uuid4())[:8]
    _jobs[job_id] = {"status": "running", "result": None, "error": None}
    zip_a = await repo_a_zip.read()
    zip_b = await repo_b_zip.read()
    background_tasks.add_task(_run_zip_job, job_id, repo_a_name, repo_b_name, zip_a, zip_b)
    return {"job_id": job_id}


@router.get("/compare/{job_id}")
async def get_job(job_id: str):
    job = _jobs.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


async def _run_job(job_id: str, payload: CompareRequest):
    from app.services.comparison import run_comparison
    try:
        result = await run_comparison(job_id, payload.repo_a, payload.repo_b, payload.methods)
        _save_json(job_id, result)
        _jobs[job_id] = {"status": "complete", "result": result, "error": None}
    except Exception as exc:
        _jobs[job_id] = {"status": "failed", "result": None, "error": str(exc)}


async def _run_zip_job(job_id: str, name_a: str, name_b: str, zip_a: bytes, zip_b: bytes):
    import tempfile
    from app.services.comparison import run_comparison
    from app.services.zip_ingestion import extract_zip
    try:
        with tempfile.TemporaryDirectory() as tmp_a, tempfile.TemporaryDirectory() as tmp_b:
            extract_zip(zip_a, tmp_a)
            extract_zip(zip_b, tmp_b)
            src_a = RepoSource(name=name_a, source="local", path=tmp_a)
            src_b = RepoSource(name=name_b, source="local", path=tmp_b)
            result = await run_comparison(job_id, src_a, src_b, None)
        _save_json(job_id, result)
        _jobs[job_id] = {"status": "complete", "result": result, "error": None}
    except Exception as exc:
        _jobs[job_id] = {"status": "failed", "result": None, "error": str(exc)}


def _save_json(job_id: str, result: dict):
    out_dir = Path(settings.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"comparison_{job_id}.json"
    with open(out_path, "w") as f:
        json.dump(result, f, indent=2, default=str)
