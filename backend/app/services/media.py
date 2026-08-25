from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile

from app.config import settings


ALLOWED_IMAGES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/heic": ".heic",
}
ALLOWED_VIDEOS = {
    "video/mp4": ".mp4",
    "video/quicktime": ".mov",
    "video/webm": ".webm",
}


def ensure_runtime_dirs() -> Path:
    upload_root = settings.upload_path
    upload_root.mkdir(parents=True, exist_ok=True)
    Path(settings.database_url.replace("sqlite:///", "")).parent.mkdir(parents=True, exist_ok=True)
    return upload_root


def runtime_writable() -> bool:
    try:
        root = ensure_runtime_dirs()
        probe = root / ".write_probe"
        probe.write_text("ok")
        probe.unlink(missing_ok=True)
        return True
    except OSError:
        return False


def _safe_ext(upload: UploadFile, allowed: dict[str, str]) -> str:
    content_type = (upload.content_type or "").lower()
    if content_type not in allowed:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {content_type or 'unknown'}")
    return allowed[content_type]


async def save_upload(ticket_id: str, upload: UploadFile | None, kind: str) -> str | None:
    if upload is None or not upload.filename:
        return None

    allowed = ALLOWED_IMAGES if kind == "photo" else ALLOWED_VIDEOS
    max_bytes = settings.max_image_bytes if kind == "photo" else settings.max_video_bytes
    ext = _safe_ext(upload, allowed)
    data = await upload.read()
    if not data:
        return None
    if len(data) > max_bytes:
        limit_mb = max_bytes // (1024 * 1024)
        raise HTTPException(status_code=400, detail=f"{kind.title()} must be {limit_mb} MB or smaller.")

    relative_dir = Path(ticket_id)
    dest_dir = settings.upload_path / relative_dir
    dest_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{kind}-{uuid.uuid4().hex[:8]}{ext}"
    dest = dest_dir / filename
    dest.write_bytes(data)
    return str(relative_dir / filename)
