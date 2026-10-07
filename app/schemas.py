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
