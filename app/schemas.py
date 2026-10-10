from datetime import date
from typing import Optional
from sqlmodel import SQLModel

class MarketRead(SQLModel):
    id: int
    name: str
    state: str
    district: str

class CropRead(SQLModel):
    id: int
    name: str
    category: str

class PriceRead(SQLModel):
    price_date: date
    crop: str
    market: str
    state: str
    modal_price: float
    min_price: float
    max_price: float

class LatestPrice(SQLModel):
    market: str
    state: str
    price_date: date
    modal_price: float


class UserCreate(SQLModel):
    name: str
    email: str
    password: str
    role: str = "farmer" # sirf farmer ya buyer allowed
    state: Optional[str] = None

class UserRead(SQLModel):
    id: int
    name: str
    email: str
    role: str
    state: Optional[str] = None

class Token(SQLModel):
    access_token: str
    token_type: str = "bearer"

class ListingCreate(SQLModel):
    crop_id: int
    market_id: int
    quantity_kg: int
    ask_price: float

class ListingRead(SQLModel):
    id: int
    farmer_id: int
    crop_id: int
    market_id: int
    quantity_kg: int
    ask_price: float
    status: str