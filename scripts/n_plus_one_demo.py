from sqlalchemy import event
from sqlmodel import Session, select
from app.database import engine
from app.models import Crop, Market, PriceRecord

counter = {"queries": 0}

@event.listens_for(engine, "before_cursor_execute")
def count_queries(conn, cursor, statement, parameters, context, executemany):
    counter["queries"] += 1 

def bad_way(session: Session) -> list[str]:
    records = session.exec(select(PriceRecord).limit(50)).all()
    out = []
    for rec in records:
        crop = session.exec(select(Crop).where(Crop.id == rec.crop_id)).one()
        market = session.exec(select(Market).where(Market.id == rec.market_id)).one()
        out.append(f"{crop.name} @ {market.name}")
    return out


def good_way(session: Session) -> list[str]:
    stmt = (
    select(Crop.name, Market.name)
    .select_from(PriceRecord)
    .join(Crop, Crop.id == PriceRecord.crop_id)
    .join(Market, Market.id == PriceRecord.market_id)
    .limit(50)
    )
    return [f"{c} @ {m}" for c, m in session.exec(stmt)]


if __name__ == "__main__":
    with Session(engine) as s:
        counter["queries"] = 0
        bad_way(s)
        print(f"Bad way : {counter['queries']} queries")
        counter["queries"] = 0
        good_way(s)
        print(f"Good way : {counter['queries']} query")