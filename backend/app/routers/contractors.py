from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Contractor
from app.serializers import contractor_out

router = APIRouter(prefix="/api/contractors", tags=["contractors"])


@router.get("")
def list_contractors(db: Session = Depends(get_db)):
    contractors = db.query(Contractor).order_by(Contractor.name.asc()).all()
    return {"contractors": [contractor_out(item) for item in contractors]}
