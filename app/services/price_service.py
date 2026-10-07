from datetime import date
from typing import Optional
from sqlalchemy import func, text
from sqlmodel import Session, select
from app.models import Crop, Market, PriceRecord


def _rows(result) -> list[dict]:
    return [dict(row._mapping) for row in result]

def list_prices(
 session: Session,
 crop: Optional[str],
 market_id: Optional[int],
 date_from: Optional[date],
 date_to: Optional[date],
 limit: int,
 offset: int,
) -> list[dict] :
    stmt = (
        select(
            PriceRecord.price_date,
            Crop.name.label("crop"),
            Market.name.label("market"),
            Market.state,
            PriceRecord.modal_price,
            PriceRecord.min_price,
            PriceRecord.max_price,
        )
        .join(Crop, Crop.id == PriceRecord.crop_id)
        .join(Market, Market.id == PriceRecord.market_id)
        )
    if crop:
        stmt = stmt.where(func.lower(Crop.name) == crop.lower())
        if market_id:
            stmt = stmt.where(PriceRecord.market_id == market_id)
        if date_from:
            stmt = stmt.where(PriceRecord.price_date >= date_from)
        if date_to:
            stmt = stmt.where(PriceRecord.price_date <= date_to)
        stmt = stmt.order_by(PriceRecord.price_date.desc(), PriceRecord.id).limit(limit).offset(offset)
        return _rows(session.exec(stmt))


def latest_prices(session: Session, crop: str) -> list[dict]:
    """Ek crop ka har market me sabse latest price (DISTINCT ON = har market ki 1 row)."""
    sql = """
    SELECT DISTINCT ON (p.market_id)
    m.name AS market, m.state, p.price_date, p.modal_price
    FROM price_records p
    JOIN crop c ON c.id = p.crop_id
    JOIN market m ON m.id = p.market_id
    WHERE LOWER(c.name) = LOWER(:crop)
    ORDER BY p.market_id, p.price_date DESC
    """
    return _rows(session.exec(text(sql), params={"crop": crop}))    