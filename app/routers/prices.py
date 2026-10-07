from datetime import date
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session
from app.database import get_session
from app.schemas import LatestPrice, PriceRead
from app.services import price_service


router = APIRouter(prefix="/prices", tags=["prices"])


@router.get("", response_model=list[PriceRead])
def get_prices(
 crop: Optional[str] = None,
 market_id: Optional[int] = None,
 date_from: Optional[date] = None,
 date_to: Optional[date] = None,
 limit: int = Query(20, ge=1, le=100),
 offset: int = Query(0, ge=0),
 session: Session = Depends(get_session),
):
    return price_service.list_prices(session, crop, market_id, date_from, date_to, limit, offset)


@router.get("/latest", response_model=list[LatestPrice])
def latest(crop: str, session: Session = Depends(get_session)):
    rows = price_service.latest_prices(session, crop)
    if not rows:
        raise HTTPException(404, f"'{crop}' no crops prices found!")
    return rows
