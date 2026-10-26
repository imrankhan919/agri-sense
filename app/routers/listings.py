from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlmodel import Session, select
from app.database import get_session
from app.deps import require_role
from app.models import Crop, Listing, Market, User , Order
from app.schemas import ListingCreate, ListingRead , OrderCreate , OrderRead

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



@router.post("/{listing_id}/buy", response_model=OrderRead, status_code=201)
def buy_listing(
 listing_id: int,
 body: OrderCreate,
 user: User = Depends(require_role("buyer")),
 session: Session = Depends(get_session),
) :
    if body.quantity_kg <= 0:
        raise HTTPException(400, "Qty should be greater than 0")
    stmt = select(Listing).where(Listing.id == listing_id).with_for_update()
    listing = session.exec(stmt).first()
    if listing is None:
        raise HTTPException(404, "Listing nahi mili")
    if listing.status != "open" or listing.quantity_kg < body.quantity_kg:
        raise HTTPException(409, f"Itna stock available nahi hai (bacha: {listing.quantity_kg} kg)")
    listing.quantity_kg -= body.quantity_kg 
    if listing.quantity_kg == 0:
        listing.status = "sold"
    order = Order(
    listing_id=listing.id,
    buyer_id=user.id,
    quantity_kg=body.quantity_kg,
    total_amount=round(body.quantity_kg / 100 * listing.ask_price, 2), 
    )
    session.add(listing)
    session.add(order)
    session.commit() 
    session.refresh(order)
    return order
