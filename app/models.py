from datetime import date, datetime, timezone
from typing import Optional
from sqlmodel import Field, SQLModel

def utcnow() -> datetime:
    return datetime.now(timezone.utc)

class Market(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    state: str = Field(index=True)
    district: str


class Crop(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True, unique=True)
    category: str 

class PriceRecord(SQLModel, table=True):
    __tablename__ = "price_records"
    id: Optional[int] = Field(default=None, primary_key=True)
    crop_id: int = Field(foreign_key="crop.id")
    market_id: int = Field(foreign_key="market.id")
    price_date: date
    modal_price: float 
    min_price: float
    max_price: float


class User(SQLModel, table=True):
    __tablename__ = "users" # "user" Postgres ka reserved word hai, isliye "users"
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    email: str = Field(index=True, unique=True)
    hashed_password: str
    role: str = Field(default="farmer") # farmer / buyer / admin
    state: Optional[str] = None
    created_at: datetime = Field(default_factory=utcnow)

    
class Listing(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    farmer_id: int = Field(foreign_key="users.id", index=True)
    crop_id: int = Field(foreign_key="crop.id", index=True)
    market_id: int = Field(foreign_key="market.id")
    quantity_kg: int
    ask_price: float # Rs per quintal
    status: str = Field(default="open") # open / sold
    created_at: datetime = Field(default_factory=utcnow)