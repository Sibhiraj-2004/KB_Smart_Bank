import os
import shutil
import tempfile

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse

from src.ingestion.ingestion import run_ingestion

router = APIRouter()

_ALLOWED_EXTENSIONS = {".pdf", ".txt"}
_UPLOAD_DIR = os.getenv("UPLOAD_DIR", "data/uploads")


@router.post("/admin/upload")
async def upload_document(file: UploadFile = File(...)):
    """
    Upload a PDF or TXT document, run Docling parsing + embedding ingestion,
    and store chunks in the multimodal_chunks table.
    """
    ext = os.path.splitext(file.filename or "")[-1].lower()
    if ext not in _ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{ext}'. Allowed: {_ALLOWED_EXTENSIONS}",
        )

    os.makedirs(_UPLOAD_DIR, exist_ok=True)

    # Save to a temp file first (UploadFile is a stream)
    try:
        suffix = ext
        with tempfile.NamedTemporaryFile(
            delete=False, suffix=suffix, dir=_UPLOAD_DIR
        ) as tmp:
            shutil.copyfileobj(file.file, tmp)
            tmp_path = tmp.name
    finally:
        await file.close()

    # Rename to the original filename for clean tracking
    dest_path = os.path.join(_UPLOAD_DIR, file.filename)
    os.replace(tmp_path, dest_path)

    try:
        result = run_ingestion(dest_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {e}")

    return JSONResponse(content={
        "filename": file.filename,
        "status": result.get("status"),
        "doc_id": result.get("doc_id"),
        "chunks_ingested": result.get("chunks_ingested"),
    })


@router.get("/admin/health")
def health_check():
    """Quick liveness probe."""
    return {"status": "ok"}