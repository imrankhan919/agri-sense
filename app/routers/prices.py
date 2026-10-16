from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session

from app.config import settings
from app.database import get_session
from app.deps import require_role
from app.models import User
from app.ratelimit import rate_limit
from app.schemas import LatestPrice, PriceRead , PriceSubmit
from app.services import price_service


router = APIRouter(prefix="/prices", tags=["prices"])


read_limit = rate_limit(settings.read_limit_per_min, 60)
latest_limit = rate_limit(settings.read_limit_per_min, 60, "sliding")
submit_limit = rate_limit(5, 60, "bucket") 

@router.get("", response_model=list[PriceRead] , dependencies=[Depends(read_limit)])
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


@router.get("/latest", response_model=list[LatestPrice] ,  dependencies=[Depends(latest_limit)])
def latest(crop: str, session: Session = Depends(get_session)):
    rows = price_service.latest_prices(session, crop)
    if not rows:
        raise HTTPException(404, f"'{crop}' no crops prices found!")
    return rows


@router.post("/submit", response_model=PriceRead, status_code=201, dependencies=[Depends(submit_limit)])
def submit_price(
    body: PriceSubmit,
    user: User = Depends(require_role("farmer", "admin")),
    session: Session = Depends(get_session),
    ):
    price_date = body.price_date or date.today()
    if price_date > date.today():
        raise HTTPException(400, "Future date is not allowed!")
    if body.modal_price <= 0:
        raise HTTPException(400, "0 price not allowed")
    try:
        return price_service.add_price(session, body.crop_id, body.market_id, body.modal_price, price_date)
    except ValueError as exc:
        raise HTTPException(404, str(exc))