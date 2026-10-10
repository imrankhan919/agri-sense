from contextlib import asynccontextmanager
from fastapi import FastAPI

from app.database import create_db_and_tables
from app.routers import catalog, prices , auth


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables() 
    yield

app = FastAPI(title="AgriSense API", version="1.0", lifespan=lifespan)
app.include_router(catalog.router)
app.include_router(prices.router)
app.include_router(auth.router)


@app.get("/health")
def health():
    return {"status": "ok", "service": "agrisense"}