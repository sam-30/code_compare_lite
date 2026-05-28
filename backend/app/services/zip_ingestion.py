import io
import zipfile
from pathlib import Path


def extract_zip(zip_bytes: bytes, into: str) -> Path:
    root = Path(into)
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        zf.extractall(root)
    # Unwrap single top-level directory if present
    children = [c for c in root.iterdir()]
    if len(children) == 1 and children[0].is_dir():
        return children[0]
    return root
