from concurrent.futures import ThreadPoolExecutor
import httpx


BASE = "http://localhost:8000"


def login(client: httpx.Client, email: str, password: str) -> dict:
    res = client.post("/auth/login", data={"username": email, "password": password})
    res.raise_for_status()
    return {"Authorization": f"Bearer {res.json()['access_token']}"}

def main() -> None:
    with httpx.Client(base_url=BASE, timeout=30) as client:
        farmer = login(client, "farmer@agrisense.dev", "farmer123")
        buyer = login(client, "buyer@agrisense.dev", "buyer123")
        listing = client.post(
        "/listings", headers=farmer,
        json={"crop_id": 1, "market_id": 1, "quantity_kg": 500, "ask_price": 2400},
        ).json()
        print("Naya listing:", listing["id"], "stock:", listing["quantity_kg"], "kg")
        def buy(_):
            with httpx.Client(base_url=BASE, timeout=30) as c:
                url = f"/listings/{listing['id']}/buy"
                return c.post(url, headers=buyer, json={"quantity_kg": 100}).status_code
        with ThreadPoolExecutor(max_workers=20) as pool:
            codes = list(pool.map(buy, range(20)))
            
        print("201 (order bana):", codes.count(201), "| 409 (stock khatam):", codes.count(409))
        mine = client.get("/listings/mine", headers=farmer).json()
        final = next(x for x in mine if x["id"] == listing["id"])
        print("Final stock:", final["quantity_kg"], "kg | status:", final["status"])


if __name__ == "__main__":
    main()
