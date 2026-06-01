"""Tests for API endpoints (api.py)."""
import io
import zipfile
import asyncio
import pytest
from pathlib import Path
from httpx import AsyncClient

from tests.conftest import FIXTURES


# ── /health ───────────────────────────────────────────────────────────────────

async def test_health_check(client: AsyncClient):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


# ── POST /compare ─────────────────────────────────────────────────────────────

async def test_compare_returns_job_id(client: AsyncClient):
    resp = await client.post("/compare", json={
        "repo_a": {"name": "a", "source": "local", "path": str(FIXTURES / "identical_a")},
        "repo_b": {"name": "b", "source": "local", "path": str(FIXTURES / "identical_b")},
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "job_id" in data
    assert len(data["job_id"]) > 0


async def test_compare_job_id_is_unique(client: AsyncClient):
    payload = {
        "repo_a": {"name": "a", "source": "local", "path": str(FIXTURES / "identical_a")},
        "repo_b": {"name": "b", "source": "local", "path": str(FIXTURES / "identical_b")},
    }
    r1 = await client.post("/compare", json=payload)
    r2 = await client.post("/compare", json=payload)
    assert r1.json()["job_id"] != r2.json()["job_id"]


async def test_compare_bad_payload_returns_422(client: AsyncClient):
    resp = await client.post("/compare", json={"bad": "data"})
    assert resp.status_code == 422


# ── GET /compare/{job_id} ─────────────────────────────────────────────────────

async def test_get_job_missing_returns_404(client: AsyncClient):
    resp = await client.get("/compare/doesnotexist")
    assert resp.status_code == 404


async def test_get_job_initially_running(client: AsyncClient):
    resp = await client.post("/compare", json={
        "repo_a": {"name": "a", "source": "local", "path": str(FIXTURES / "identical_a")},
        "repo_b": {"name": "b", "source": "local", "path": str(FIXTURES / "identical_b")},
    })
    job_id = resp.json()["job_id"]
    poll = await client.get(f"/compare/{job_id}")
    assert poll.status_code == 200
    assert poll.json()["status"] in ("running", "complete")


async def test_get_job_completes(client: AsyncClient):
    resp = await client.post("/compare", json={
        "repo_a": {"name": "a", "source": "local", "path": str(FIXTURES / "identical_a")},
        "repo_b": {"name": "b", "source": "local", "path": str(FIXTURES / "identical_b")},
    })
    job_id = resp.json()["job_id"]

    deadline = asyncio.get_event_loop().time() + 60
    while asyncio.get_event_loop().time() < deadline:
        await asyncio.sleep(0.5)
        data = (await client.get(f"/compare/{job_id}")).json()
        if data["status"] == "complete":
            assert data["result"] is not None
            assert data["error"] is None
            return
        if data["status"] == "failed":
            pytest.fail(f"Job failed: {data.get('error')}")
    pytest.fail("Job did not complete within 60s")


async def test_compare_invalid_local_path_fails(client: AsyncClient):
    resp = await client.post("/compare", json={
        "repo_a": {"name": "a", "source": "local", "path": "/nonexistent/path/a"},
        "repo_b": {"name": "b", "source": "local", "path": "/nonexistent/path/b"},
    })
    job_id = resp.json()["job_id"]

    deadline = asyncio.get_event_loop().time() + 30
    while asyncio.get_event_loop().time() < deadline:
        await asyncio.sleep(0.3)
        data = (await client.get(f"/compare/{job_id}")).json()
        if data["status"] == "failed":
            assert data["error"] is not None
            return
        if data["status"] == "complete":
            pytest.fail("Expected failure for nonexistent path, but got complete")
    pytest.fail("Job did not settle within 30s")


# ── POST /compare/upload ───────────────────────────────────────────────────────

def _make_zip(files: dict[str, str]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, content in files.items():
            zf.writestr(name, content)
    return buf.getvalue()


async def test_upload_returns_job_id(client: AsyncClient):
    zip_a = _make_zip({"a.py": "def foo():\n    return 1\n"})
    zip_b = _make_zip({"b.py": "def foo():\n    return 1\n"})
    resp = await client.post(
        "/compare/upload",
        data={"repo_a_name": "A", "repo_b_name": "B"},
        files={"repo_a_zip": ("a.zip", zip_a), "repo_b_zip": ("b.zip", zip_b)},
    )
    assert resp.status_code == 200
    assert "job_id" in resp.json()


async def test_upload_job_completes(client: AsyncClient):
    zip_a = _make_zip({"a.py": "def foo():\n    return 1\n"})
    zip_b = _make_zip({"b.py": "def foo():\n    return 1\n"})
    resp = await client.post(
        "/compare/upload",
        data={"repo_a_name": "A", "repo_b_name": "B"},
        files={"repo_a_zip": ("a.zip", zip_a), "repo_b_zip": ("b.zip", zip_b)},
    )
    job_id = resp.json()["job_id"]

    deadline = asyncio.get_event_loop().time() + 60
    while asyncio.get_event_loop().time() < deadline:
        await asyncio.sleep(0.5)
        data = (await client.get(f"/compare/{job_id}")).json()
        if data["status"] == "complete":
            return
        if data["status"] == "failed":
            pytest.fail(f"Upload job failed: {data.get('error')}")
    pytest.fail("Upload job did not complete within 60s")


async def test_result_saved_to_json(client: AsyncClient, tmp_path):
    """Completed job writes a JSON file to the output directory."""
    resp = await client.post("/compare", json={
        "repo_a": {"name": "a", "source": "local", "path": str(FIXTURES / "identical_a")},
        "repo_b": {"name": "b", "source": "local", "path": str(FIXTURES / "identical_b")},
    })
    job_id = resp.json()["job_id"]

    deadline = asyncio.get_event_loop().time() + 60
    while asyncio.get_event_loop().time() < deadline:
        await asyncio.sleep(0.5)
        data = (await client.get(f"/compare/{job_id}")).json()
        if data["status"] == "complete":
            import json
            output_file = tmp_path / f"comparison_{job_id}.json"
            assert output_file.exists(), f"Expected {output_file} to exist"
            saved = json.loads(output_file.read_text())
            assert saved["job_id"] == job_id
            return
    pytest.fail("Job did not complete within 60s")
