from __future__ import annotations

import base64
import io
import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile
from PIL import Image

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


def encode_photo_for_triage(photo_path: str | None, max_edge: int = 1024, max_chars: int = 900_000) -> str | None:
    if not photo_path:
        return None
    path = settings.upload_path / photo_path
    if not path.exists():
        return None
    try:
        with Image.open(path) as image:
            image = image.convert("RGB")
            image.thumbnail((max_edge, max_edge))
            quality = 80
            data_url = ""
            while quality >= 40:
                buffer = io.BytesIO()
                image.save(buffer, format="JPEG", quality=quality, optimize=True)
                encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
                data_url = f"data:image/jpeg;base64,{encoded}"
                if len(data_url) <= max_chars:
                    return data_url
                quality -= 10
            return data_url if data_url and len(data_url) <= max_chars else None
    except OSError:
        return None
