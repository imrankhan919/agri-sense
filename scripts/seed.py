import math
import random
import sys
from datetime import date, timedelta
from sqlalchemy import insert, text
from sqlmodel import Session, select
from app.database import create_db_and_tables, engine
from app.models import Crop, Market, PriceRecord


random.seed(42)

MARKETS = [
 ("Indore", "Madhya Pradesh", "Indore"), ("Ujjain", "Madhya Pradesh", "Ujjain"),
 ("Mandsaur", "Madhya Pradesh", "Mandsaur"), ("Bhopal", "Madhya Pradesh", "Bhopal"),
 ("Jaipur", "Rajasthan", "Jaipur"), ("Kota", "Rajasthan", "Kota"),
 ("Jodhpur", "Rajasthan", "Jodhpur"), ("Nagpur", "Maharashtra", "Nagpur"),
 ("Pune", "Maharashtra", "Pune"), ("Nashik", "Maharashtra", "Nashik"),
 ("Ahmedabad", "Gujarat", "Ahmedabad"), ("Rajkot", "Gujarat", "Rajkot"),
 ("Surat", "Gujarat", "Surat"), ("Lucknow", "Uttar Pradesh", "Lucknow"),
 ("Kanpur", "Uttar Pradesh", "Kanpur"), ("Agra", "Uttar Pradesh", "Agra"),
 ("Ludhiana", "Punjab", "Ludhiana"), ("Amritsar", "Punjab", "Amritsar"),
 ("Karnal", "Haryana", "Karnal"), ("Hisar", "Haryana", "Hisar"),
 ("Patna", "Bihar", "Patna"), ("Gaya", "Bihar", "Gaya"),
 ("Kolkata", "West Bengal", "Kolkata"), ("Siliguri", "West Bengal", "Darjeeling"),
 ("Hyderabad", "Telangana", "Hyderabad"), ("Warangal", "Telangana", "Warangal"),
 ("Bengaluru", "Karnataka", "Bengaluru"), ("Hubballi", "Karnataka", "Dharwad"),
 ("Raipur", "Chhattisgarh", "Raipur"), ("Bhubaneswar", "Odisha", "Khordha"),
]


CROPS = [
 ("Wheat", "grain", 2400), ("Rice", "grain", 3300), ("Maize", "grain", 2100),
 ("Bajra", "grain", 2400), ("Jowar", "grain", 3200), ("Soybean", "oilseed", 4600),
 ("Mustard", "oilseed", 5800), ("Groundnut", "oilseed", 6200), ("Chana", "pulse", 5500),
 ("Tur", "pulse", 7400), ("Moong", "pulse", 8200), ("Urad", "pulse", 7000),
 ("Cotton", "fibre", 7300), ("Onion", "vegetable", 1800), ("Potato", "vegetable", 1500),
 ("Tomato", "vegetable", 2200), ("Garlic", "spice", 12000), ("Turmeric", "spice", 13000),
 ("Coriander", "spice", 7500), ("Ginger", "spice", 6000),
]


START, END = date(2024, 1, 1), date(2026, 9, 30)
BATCH = 10_000

def seed(force: bool = False) -> None:
    create_db_and_tables()

    with Session(engine) as session:
        if session.exec(select(Market)).first():
            if not force:
                print("Data already hai. Dobara load karna ho to --force lagao.")
                return

        session.exec(
            text("TRUNCATE price_records, crop, market RESTART IDENTITY CASCADE")
        )
        session.commit()

        session.add_all(
            [Market(name=n, state=s, district=d) for n, s, d in MARKETS]
        )

        session.add_all(
            [Crop(name=n, category=c) for n, c, _ in CROPS]
        )

        session.commit()

        markets = session.exec(select(Market)).all()
        crops = session.exec(select(Crop)).all()

        state_factor = {
            m.state: random.uniform(0.92, 1.12)
            for m in markets
        }

        crop_phase = {
            c.id: random.random()
            for c in crops
        }

        base = {
            c.id: CROPS[i][2]
            for i, c in enumerate(crops)
        }

        # Har (market, crop) jodi sabhi mandiyon me nahi bikti:
        # ~55% jodiyan active.
        #
        # Madhya Pradesh ki 4 mandiyon me sabhi 20 fasal milti hain
        # (class demo ke liye).
        home = {"Indore", "Ujjain", "Mandsaur", "Bhopal"}

        pairs = [
            (m, c)
            for m in markets
            for c in crops
            if m.name in home or random.random() < 0.55
        ]

        days = (END - START).days + 1

        rows = []
        total = 0

        with engine.begin() as conn:
            for d in range(days):
                day = START + timedelta(days=d)

                year_pos = day.timetuple().tm_yday / 365

                # Saal me ~4% mehngayi
                growth = 1 + 0.04 * (d / 365)

                for m, c in pairs:

                    # Kuch din mandi band / data missing
                    if random.random() > 0.85:
                        continue

                    season = (
                        1
                        + 0.10
                        * math.sin(
                            2
                            * math.pi
                            * (year_pos + crop_phase[c.id])
                        )
                    )

                    noise = 1 + random.gauss(0, 0.02)

                    modal = round(
                        base[c.id]
                        * state_factor[m.state]
                        * season
                        * growth
                        * noise,
                        2,
                    )

                    rows.append(
                        {
                            "crop_id": c.id,
                            "market_id": m.id,
                            "price_date": day,
                            "modal_price": modal,
                            "min_price": round(modal * 0.94, 2),
                            "max_price": round(modal * 1.06, 2),
                        }
                    )

                    if len(rows) >= BATCH:
                        conn.execute(
                            insert(PriceRecord.__table__),
                            rows,
                        )

                        total += len(rows)
                        rows = []

            # Remaining records
            if rows:
                conn.execute(
                    insert(PriceRecord.__table__),
                    rows,
                )

                total += len(rows)

        print(
            f"Done: {len(markets)} markets, "
            f"{len(crops)} crops, "
            f"{total:,} price records"
        )


if __name__ == "__main__":
    seed(force="--force" in sys.argv)