from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Restaurant
from app.schemas import RestaurantOut

router = APIRouter(prefix="/api/restaurants", tags=["restaurants"])


@router.get("")
def list_restaurants(db: Session = Depends(get_db)):
    restaurants = db.query(Restaurant).order_by(Restaurant.name.asc()).all()
    return {"restaurants": [RestaurantOut.model_validate(item) for item in restaurants]}
