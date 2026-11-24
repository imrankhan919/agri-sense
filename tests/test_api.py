import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.redis_client import r


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(autouse=True)
def clean_redis():
    for pattern in ("rl:*", "latest:*", "agent:tokens:*"):
        for key in r.scan_iter(pattern):
            r.delete(key)


def auth(client: TestClient, email: str, password: str) -> dict[str, str]:
    res = client.post("/auth/login", data={"username": email, "password": password})
    assert res.status_code == 200, res.text
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


def test_health(client: TestClient):
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


def test_markets_and_crops(client: TestClient):
    markets_res = client.get("/markets?limit=5")
    assert markets_res.status_code == 200
    assert len(markets_res.json()) == 5

    crops_res = client.get("/crops")
    assert crops_res.status_code == 200
    assert any(c["name"] == "Wheat" for c in crops_res.json())


def test_latest_cache_miss_then_hit(client: TestClient):
    first = client.get("/prices/latest?crop=Wheat")
    second = client.get("/prices/latest?crop=Wheat")

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.headers["X-Cache"] == "MISS"
    assert second.headers["X-Cache"] == "HIT"


def test_protected_route_needs_token(client: TestClient):
    res = client.get("/auth/me")
    assert res.status_code == 401


def test_buyer_cannot_create_listing(client: TestClient):
    buyer = auth(client, "buyer@agrisense.dev", "buyer123")
    body = {"crop_id": 1, "market_id": 1, "quantity_kg": 100, "ask_price": 2000}

    res = client.post("/listings", json=body, headers=buyer)
    assert res.status_code == 403


def test_farmer_listing_and_buyer_purchase(client: TestClient):
    farmer = auth(client, "farmer@agrisense.dev", "farmer123")
    buyer = auth(client, "buyer@agrisense.dev", "buyer123")

    body = {"crop_id": 1, "market_id": 1, "quantity_kg": 300, "ask_price": 2000}
    create_res = client.post("/listings", json=body, headers=farmer)
    assert create_res.status_code == 201, create_res.text
    listing_id = create_res.json()["id"]

    # First purchase: 200 kg @ 2000/quintal = 4000.0 (100 kg remaining)
    ok = client.post(
        f"/listings/{listing_id}/buy",
        json={"quantity_kg": 200},
        headers=buyer,
    )
    assert ok.status_code == 201, ok.text
    assert ok.json()["total_amount"] == 4000.0

    # Second purchase exceeds remaining 100 kg inventory
    too_much = client.post(
        f"/listings/{listing_id}/buy",
        json={"quantity_kg": 200},
        headers=buyer,
    )
    assert too_much.status_code == 409


def test_trend_and_compare(client: TestClient):
    trend_res = client.get("/prices/trend?crop=Wheat&market_id=1&months=3")
    assert trend_res.status_code == 200
    assert len(trend_res.json()) <= 3

    compare_res = client.get("/prices/compare?crop=Wheat")
    assert compare_res.status_code == 200
    compare_data = compare_res.json()
    assert len(compare_data) > 0, "Expected seeded Wheat price comparison records"
    assert compare_data[0]["rank"] == 1


def test_submit_price_rate_limited(client: TestClient):
    farmer = auth(client, "farmer@agrisense.dev", "farmer123")
    bad_payload = {
        "crop_id": 1,
        "market_id": 1,
        "modal_price": 2000,
        "price_date": "2999-01-01",
    }

    codes = [
        client.post("/prices/submit", json=bad_payload, headers=farmer).status_code
        for _ in range(6)
    ]
    # First 5 reach validation (400 future date); 6th exhausts token bucket (429)
    assert codes[:5] == [400] * 5
    assert codes[5] == 429


def test_agent_chat_uses_tool(client: TestClient):
    farmer = auth(client, "farmer@agrisense.dev", "farmer123")

    res = client.post(
        "/agent/chat",
        json={"question": "Indore me gehu ka bhaav kya hai?"},
        headers=farmer,
    )
    assert res.status_code == 200, res.text
    assert "get_mandi_prices" in res.json()["tools_used"]

    usage_res = client.get("/agent/usage", headers=farmer)
    assert usage_res.status_code == 200
    assert usage_res.json()["tokens_used_today"] > 0


def test_agent_needs_login(client: TestClient):
    res = client.post("/agent/chat", json={"question": "hi"})
    assert res.status_code == 401