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




def add_price(session: Session, crop_id: int, market_id: int, modal_price: float, price_date: date) -> dict:
    crop = session.get(Crop, crop_id)
    market = session.get(Market, market_id)
    if crop is None or market is None:
        raise ValueError("Crop ya market nahi mila")
    record = PriceRecord(
        crop_id=crop_id, market_id=market_id, price_date=price_date, modal_price=modal_price,
        min_price=round(modal_price * 0.95, 2), max_price=round(modal_price * 1.05, 2),
    )
    session.add(record)
    session.commit()
    return dict(
        price_date=price_date, crop=crop.name, market=market.name, state=market.state,
        modal_price=record.modal_price, min_price=record.min_price, max_price=record.max_price,
    )


MIN_SAMPLES = 10

def trend(session: Session, crop: str, market_id: int, months: int) -> list[dict]:
    sql = """
        WITH t AS (
        SELECT mv.month,
        mv.avg_price,
        LAG(mv.avg_price) OVER (ORDER BY mv.month) AS prev_avg
        FROM mv_monthly_prices mv
        JOIN crop c ON c.id = mv.crop_id
        WHERE LOWER(c.name) = LOWER(:crop) AND mv.market_id = :market_id
        AND mv.samples >= :min_samples -- adhoora mahina (bahut kam records) ignore
        )
    SELECT month, avg_price,
    ROUND(((avg_price - prev_avg) / prev_avg * 100)::numeric, 2) AS change_pct
    FROM t
    ORDER BY month DESC
    LIMIT :months
    """
    return _rows(session.exec(text(sql), params={"crop": crop, "market_id": market_id, "months": months, "min_samples": MIN_SAMPLES}))


def compare_markets(session: Session, crop: str, limit: int = 10) -> list[dict]:
    sql = """
        SELECT RANK() OVER (ORDER BY mv.avg_price DESC) AS rank,
        m.name AS market, m.state, mv.month, mv.avg_price
        FROM mv_monthly_prices mv
        JOIN crop c ON c.id = mv.crop_id
        JOIN market m ON m.id = mv.market_id
        WHERE LOWER(c.name) = LOWER(:crop)
        AND mv.samples >= :min_samples
        AND mv.month = (SELECT MAX(month) FROM mv_monthly_prices
        WHERE crop_id = mv.crop_id AND samples >= :min_samples)
        ORDER BY rank
        LIMIT :limit
        """
    return _rows(session.exec(text(sql), params={"crop": crop, "limit": limit, "min_samples": MIN_SAMPLES}))