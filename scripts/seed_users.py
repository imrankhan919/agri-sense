from sqlmodel import Session, select
from app.database import create_db_and_tables, engine
from app.models import Crop, Listing, Market, User
from app.security import hash_password


DEMO = [
 ("Admin", "admin@agrisense.dev", "admin123", "admin", "Madhya Pradesh"),
 ("Ramesh (farmer)", "farmer@agrisense.dev", "farmer123", "farmer", "Madhya Pradesh"),
 ("Sunita (farmer)", "farmer2@agrisense.dev", "farmer123", "farmer", "Maharashtra"),
 ("Vikas (buyer)", "buyer@agrisense.dev", "buyer123", "buyer", "Rajasthan"),
]


def main() -> None:
    create_db_and_tables()
    with Session(engine) as s:
        for name, email, pw, role, state in DEMO:
            if not s.exec(select(User).where(User.email == email)).first():
                s.add(User(name=name, email=email, role=role, state=state,
                hashed_password=hash_password(pw)))
        s.commit()
 
        def by_email(e):
            return s.exec(select(User).where(User.email == e)).one()
        wheat = s.exec(select(Crop).where(Crop.name == "Wheat")).one()
        onion = s.exec(select(Crop).where(Crop.name == "Onion")).one()
        indore = s.exec(select(Market).where(Market.name == "Indore")).one()
        nashik = s.exec(select(Market).where(Market.name == "Nashik")).one()
        if not s.exec(select(Listing)).first():
            s.add(Listing(farmer_id=by_email("farmer@agrisense.dev").id, crop_id=wheat.id,
                market_id=indore.id, quantity_kg=500, ask_price=2450))
            s.add(Listing(farmer_id=by_email("farmer2@agrisense.dev").id, crop_id=onion.id,
                market_id=nashik.id, quantity_kg=1000, ask_price=1900))
            s.commit()
    print("Demo users ready.")



if __name__ == "__main__":
    main()
