from typing import Literal, Optional
from pydantic import BaseModel


class RepoSource(BaseModel):
    name: str
    source: Literal["git", "local"]
    url: Optional[str] = None
    path: Optional[str] = None


class CompareRequest(BaseModel):
    repo_a: RepoSource
    repo_b: RepoSource
    methods: Optional[list[str]] = None


class MethodResult(BaseModel):
    method_id: str
    score: float
    weight: float
    duration_ms: int
    details: dict = {}


class FileMatch(BaseModel):
    file_a_path: str
    file_b_path: str
    similarity_score: float
    method_id: str


class CompareResult(BaseModel):
    job_id: str
    repo_a_name: str
    repo_b_name: str
    language: str
    files_found_a: int = 0
    files_found_b: int = 0
    files_a: list[str] = []
    files_b: list[str] = []
    overall_score: float
    methods: list[MethodResult]
    file_matches: list[FileMatch]
    output_file: str
    created_at: str


class JobStatus(BaseModel):
    status: Literal["running", "complete", "failed"]
    result: Optional[CompareResult] = None
    error: Optional[str] = None
