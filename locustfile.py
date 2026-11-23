import random
from locust import HttpUser, between, task

CROPS = ["Wheat", "Onion", "Soybean", "Tomato", "Chana", "Maize", "Rice", "Mustard"]

class Visitor(HttpUser):
    wait_time = between(0.2, 1.0)
    def _get(self, url: str, name: str):
        # 429 (rate limit) is test me "expected" hai, failure nahi
        with self.client.get(url, name=name, catch_response=True) as res:
            if res.status_code in (200, 429):
                res.success()
            else:
                res.failure(f"unexpected status {res.status_code}")
            
    @task(5)
    def latest_price(self):
        self._get(f"/prices/latest?crop={random.choice(CROPS)}", "/prices/latest")
    @task(3)
    def price_list(self):
        self._get(f"/prices?crop={random.choice(CROPS)}&limit=20", "/prices")
    @task(2)
    def trend(self):
        self._get(f"/prices/trend?crop={random.choice(CROPS)}&market_id={random.randint(1, 4)}&months=6",
            "/prices/trend")
    @task(1)
    def compare(self):
        self._get(f"/prices/compare?crop={random.choice(CROPS)}", "/prices/compare")