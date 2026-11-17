import json
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Callable
from sqlmodel import Session, select
from app.models import Crop, Listing, Market, User
from app.services import price_service


MAX_ROWS = 10

@dataclass
class ToolSpec:
    name: str
    description: str 
    parameters: dict
    handler: Callable[[Session, User, dict], Any]


def _find_market(session: Session, name: str):
    return session.exec(select(Market).where(Market.name.ilike(f"%{name.strip()}%"))).first()


def _get_mandi_prices(session: Session, user: User, args: dict):
    rows = price_service.latest_prices(session, args["crop"])
    market = args.get("market")
    if market:
        rows = [r for r in rows if market.strip().lower() in r["market"].lower()]
    if not rows:
        return {"error": f"{args['crop']} ka price data nahi mila"}
    rows.sort(key=lambda r: r["modal_price"], reverse=True)
    return {"unit": "Rs per quintal", "prices": rows[:MAX_ROWS]}


def _compare_markets(session: Session, user: User, args: dict):
    rows = price_service.compare_markets(session, args["crop"], 5)
    if not rows:
        return {"error": f"{args['crop']} ka data nahi mila"}
    return {"unit": "Rs per quintal (monthly average)", "ranking": rows}



def _price_trend(session: Session, user: User, args: dict):
    market = _find_market(session, args["market"])
    if market is None:
        return {"error": f"'{args['market']}' naam ki mandi nahi mili"}
    months = max(1, min(int(args.get("months", 6)), 12))
    rows = price_service.trend(session, args["crop"], market.id, months)
    if not rows:
        return {"error": "Is crop aur mandi ka data nahi mila"}
    return {"market": market.name, "unit": "Rs per quintal (monthly average)", "months": rows}


def _list_my_produce(session: Session, user: User, args: dict):
    stmt = (
    select(Crop.name, Market.name, Listing.quantity_kg, Listing.ask_price, Listing.status)
    .select_from(Listing)
    .join(Crop, Crop.id == Listing.crop_id)
    .join(Market, Market.id == Listing.market_id)
    .where(Listing.farmer_id == user.id)
    .limit(MAX_ROWS)
    )
    rows = [
    dict(crop=c, market=m, quantity_kg=q, ask_price=p, status=s)
    for c, m, q, p, s in session.exec(stmt)
    ]
    return {"listings": rows} if rows else {"error": "Aapki koi listing nahi hai"}


CROP_PARAM = {"type": "string", "description": "Crop name in English, e.g. Wheat, Onion, Soybean, Tomato"}



TOOLS: dict[str, ToolSpec] = {t.name: t for t in [
    ToolSpec(
    "get_mandi_prices",
    "Get the latest mandi price (Rs per quintal) of a crop, optionally for one market.",
    {"type": "object", "properties": {
    "crop": CROP_PARAM,
    "market": {"type": "string", "description": "Optional mandi name, e.g. Indore"}},
    "required": ["crop"]},
    _get_mandi_prices),
    ToolSpec(
    "compare_markets",
    "Find which markets pay the best average price for a crop this month.",
    {"type": "object", "properties": {"crop": CROP_PARAM}, "required": ["crop"]},
    _compare_markets),
    ToolSpec(
    "price_trend",
    "Monthly price trend and percent change for a crop in one market.",
    {"type": "object", "properties": {
    "crop": CROP_PARAM,
    "market": {"type": "string", "description": "Mandi name, e.g. Indore"},
    "months": {"type": "integer", "description": "How many recent months (1-12), default 6"}},
    "required": ["crop", "market"]},
    _price_trend),
    ToolSpec(
    "list_my_produce",
    "List the logged-in farmer's own produce listings. Takes no arguments.",
    {"type": "object", "properties": {}},
    _list_my_produce),
    ]}


def tool_specs() -> list[ToolSpec]:
    return list(TOOLS.values())


def _jsonable(obj: Any) -> Any:
    """Decimal/date jaise objects ko plain JSON me badlo (LLM ko JSON hi bhej sakte hain)."""
    return json.loads(json.dumps(obj, default=lambda o: float(o) if isinstance(o, Decimal) else str(o)))


def run_tool(name: str, args: dict, session: Session, user: User) -> Any:
    spec = TOOLS.get(name)
    if spec is None:
        return {"error": f"Unknown tool: {name}"}
    allowed = spec.parameters["properties"].keys()
    clean = {k: v for k, v in (args or {}).items() if k in allowed} # extra/fake arguments hata do
    missing = [k for k in spec.parameters.get("required", []) if k not in clean]
    if missing:
        return {"error": f"Missing arguments: {missing}"}
    try:
        return _jsonable(spec.handler(session, user, clean))
    except Exception as exc: # tool toote to bhi agent loop zinda rahe
        session.rollback()
        return {"error": f"Tool failed: {type(exc).__name__}"}