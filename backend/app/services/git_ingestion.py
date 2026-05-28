import tempfile
from pathlib import Path


def clone_repo(url: str, into: str) -> Path:
    from git import Repo as GitRepo
    GitRepo.clone_from(url, into, depth=1)
    return Path(into)
