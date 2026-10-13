from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlmodel import Session, select
from app.database import get_session
from app.deps import require_role
from app.models import Crop, Listing, Market, User
from app.schemas import ListingCreate, ListingRead

router = APIRouter(prefix="/listings", tags=["listings"])


@router.post("", response_model=ListingRead, status_code=201)
def create_listing(
    body: ListingCreate,
    user: User = Depends(require_role("farmer")),
    session: Session = Depends(get_session),):
    if session.get(Crop, body.crop_id) is None:
        raise HTTPException(404, "Crop nahi mila")
    if session.get(Market, body.market_id) is None:
        raise HTTPException(404, "Market nahi mila")
    if body.quantity_kg <= 0 or body.ask_price <= 0:
        raise HTTPException(400, "quantity aur price 0 se zyada hone chahiye")
    listing = Listing(farmer_id=user.id, **body.model_dump())
    session.add(listing)
    session.commit()
    session.refresh(listing)
    return listing



@router.get("", response_model=list[ListingRead])
def browse_listings(crop: Optional[str] = None, session: Session = Depends(get_session)):
    stmt = select(Listing).where(Listing.status == "open")
    if crop:
        stmt = stmt.join(Crop, Crop.id == Listing.crop_id).where(func.lower(Crop.name) == crop.lower())
    return session.exec(stmt.order_by(Listing.id.desc()).limit(50)).all()


@router.get("/mine", response_model=list[ListingRead])
def my_listings(user: User = Depends(require_role("farmer")), session: Session = Depends(get_session)):
    return session.exec(select(Listing).where(Listing.farmer_id == user.id)).all()
