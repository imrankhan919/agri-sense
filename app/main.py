import logging
import time

from contextlib import asynccontextmanager
from fastapi import FastAPI , Request
from app.database import create_db_and_tables
from app.routers import analytics, catalog, prices , auth , listings , agent


log = logging.getLogger("agrisense")


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables() 
    yield

app = FastAPI(title="AgriSense API", version="1.0", lifespan=lifespan)


@app.middleware("http")
async def timing_middleware(request: Request, call_next):
    started = time.perf_counter()
    response = await call_next(request)
    ms = (time.perf_counter() - started) * 1000
    response.headers["X-Process-Time-ms"] = f"{ms:.1f}" # load test me latency yahin se dikhegi
    if response.status_code == 429:
        log.warning("rate limited: %s %s", request.method, request.url.path)
    return response



app.include_router(catalog.router)
app.include_router(prices.router)
app.include_router(auth.router)
app.include_router(analytics.router)
app.include_router(listings.router)
app.include_router(agent.router)




@app.get("/health")
def health():
    return {"status": "ok", "service": "agrisense"}