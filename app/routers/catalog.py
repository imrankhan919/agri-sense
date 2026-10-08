from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlmodel import Session, select
from app.database import get_session
from app.models import Crop, Market
from app.schemas import CropRead, MarketRead


router = APIRouter(tags=["catalog"])


@router.get("/markets", response_model=list[MarketRead])
def list_markets(
    state: Optional[str] = None,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    session: Session = Depends(get_session),
) :
    stmt = select(Market)
    if state:
        stmt = stmt.where(Market.state == state)
    stmt = stmt.order_by(Market.name).offset(offset).limit(limit)
    return session.exec(stmt).all()


@router.get("/crops", response_model=list[CropRead])
def list_crops(session: Session = Depends(get_session)):
    return session.exec(select(Crop).order_by(Crop.name)).all()
