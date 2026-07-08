from fastapi import APIRouter, HTTPException, UploadFile, File
from pathlib import Path
from datetime import date
import uuid
import shutil

from core.deps import CurrentUser
from core.config import settings

router = APIRouter()

ALLOWED_EXTENSIONS = set(settings.ALLOWED_EXTENSIONS)


@router.post("/")
async def upload_file(current_user: CurrentUser, file: UploadFile = File(...), category: str = "general"):
    """
    Generic file upload endpoint. Returns a URL that can be attached to
    daily reports, documents, BOQ imports, etc.
    Files are stored under /uploads/{category}/{year}/{month}/{uuid}.{ext}
    """
    ext = file.filename.split(".")[-1].lower() if "." in file.filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"File type '.{ext}' not allowed. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
        )

    # Size check
    contents = await file.read()
    size_mb = len(contents) / (1024 * 1024)
    if size_mb > settings.MAX_FILE_SIZE_MB:
        raise HTTPException(
            status_code=400,
            detail=f"File too large: {size_mb:.1f}MB (max {settings.MAX_FILE_SIZE_MB}MB)"
        )

    today = date.today()
    rel_dir = Path(category) / str(today.year) / f"{today.month:02d}"
    abs_dir = Path(settings.UPLOAD_DIR) / rel_dir
    abs_dir.mkdir(parents=True, exist_ok=True)

    filename = f"{uuid.uuid4().hex}.{ext}"
    abs_path = abs_dir / filename
    rel_path = rel_dir / filename

    with open(abs_path, "wb") as f:
        f.write(contents)

    return {
        "filename": file.filename,
        "url": f"/uploads/{rel_path.as_posix()}",
        "size_bytes": len(contents),
        "content_type": file.content_type,
    }


@router.post("/multiple")
async def upload_multiple(
    current_user: CurrentUser,
    files: list[UploadFile] = File(...),
    category: str = "general",
):
    """Upload multiple files at once (e.g., daily report photos)."""
    results = []
    errors = []
    for file in files:
        try:
            result = await upload_file(current_user, file, category)
            results.append(result)
        except HTTPException as e:
            errors.append({"filename": file.filename, "error": e.detail})

    return {"uploaded": results, "errors": errors}


@router.delete("/")
async def delete_file(current_user: CurrentUser, url: str):
    """Delete an uploaded file by its relative URL."""
    if not url.startswith("/uploads/"):
        raise HTTPException(status_code=400, detail="Invalid file URL")

    rel_path = url.replace("/uploads/", "", 1)
    abs_path = Path(settings.UPLOAD_DIR) / rel_path

    if not abs_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    # Prevent path traversal
    if not str(abs_path.resolve()).startswith(str(Path(settings.UPLOAD_DIR).resolve())):
        raise HTTPException(status_code=400, detail="Invalid path")

    abs_path.unlink()
    return {"message": "File deleted"}
