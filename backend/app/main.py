from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from app.config import settings
from app.database import Base, SessionLocal, engine
from app.models import Ticket
from app.routers import contractors, restaurants, tickets
from app.schemas import HealthOut
from app.seed import seed_core
from app.services.media import ensure_runtime_dirs, runtime_writable


def create_app() -> FastAPI:
    ensure_runtime_dirs()
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        seed_core(db)

    app = FastAPI(title=settings.app_name, version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_origin_regex=r"https://.*\.vercel\.app",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(tickets.router)
    app.include_router(contractors.router)
    app.include_router(restaurants.router)

    upload_root = settings.upload_path
    upload_root.mkdir(parents=True, exist_ok=True)
    app.mount("/uploads", StaticFiles(directory=upload_root), name="uploads")

    @app.get("/health", response_model=HealthOut)
    def health():
        db: Session = SessionLocal()
        try:
            ticket_count = db.query(Ticket).count()
        finally:
            db.close()
        return HealthOut(
            status="ok",
            runtime_writable=runtime_writable(),
            openrouter_configured=bool(settings.openrouter_api_key),
            ticket_count=ticket_count,
        )

    @app.get("/api/health", response_model=HealthOut)
    def api_health():
        return health()

    return app


app = create_app()
