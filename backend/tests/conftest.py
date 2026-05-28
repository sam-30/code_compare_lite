import asyncio
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.main import app

FIXTURES = Path(__file__).parent / "fixtures"


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


async def run_comparison(client: AsyncClient, path_a: Path, path_b: Path, language: str = "python") -> dict:
    """POST /compare with two local fixture paths and poll until done."""
    resp = await client.post("/compare", json={
        "repo_a": {"name": path_a.name, "source": "local", "path": str(path_a)},
        "repo_b": {"name": path_b.name, "source": "local", "path": str(path_b)},
        "language": language,
    })
    assert resp.status_code == 200, f"POST /compare failed: {resp.text}"
    job_id = resp.json()["job_id"]

    deadline = asyncio.get_event_loop().time() + 60
    while asyncio.get_event_loop().time() < deadline:
        await asyncio.sleep(0.5)
        poll = await client.get(f"/compare/{job_id}")
        data = poll.json()
        if data["status"] == "complete":
            return data["result"]
        if data["status"] == "failed":
            raise AssertionError(f"Comparison failed: {data.get('error')}")

    raise TimeoutError(f"Job {job_id} did not complete within 60s")
