from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlmodel import Session
from app.config import settings
from app.database import get_session
from app.deps import require_role
from app.models import User
from app.ratelimit import rate_limit
from app.schemas import MarketCompare, TrendPoint
from app.services import price_service


router = APIRouter(tags=["analytics"])
analytics_limit = rate_limit(settings.read_limit_per_min, 60, "sliding")


@router.get("/prices/trend", response_model=list[TrendPoint], dependencies=[Depends(analytics_limit)])
def price_trend(
    crop: str,
    market_id: int,
    months: int = Query(6, ge=1, le=36),
    session: Session = Depends(get_session),
    ):
    rows = price_service.trend(session, crop, market_id, months)
    if not rows:
        raise HTTPException(404, "Is crop/market ka data nahi mila")
    return rows


@router.get("/prices/compare", response_model=list[MarketCompare], dependencies=[Depends(analytics_limit)])
def compare(crop: str, limit: int = Query(10, ge=1, le=30), session: Session = Depends(get_session)):
    rows = price_service.compare_markets(session, crop, limit)
    if not rows:
        raise HTTPException(404, f"'{crop}' ka data nahi mila")
    return rows

@router.post("/admin/refresh-rollups")
def refresh_rollups(user: User = Depends(require_role("admin")), session: Session = Depends(get_session)):
    session.exec(text("REFRESH MATERIALIZED VIEW CONCURRENTLY mv_monthly_prices"))
    session.commit()
    return {"status": "refreshed"}