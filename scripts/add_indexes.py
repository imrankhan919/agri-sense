from sqlalchemy import text
from app.database import engine
# /prices: ek crop ki latest rows (crop_id, price_date DESC, id) index se seedhe mil jaati hain
INDEX_SQL = """
CREATE INDEX IF NOT EXISTS idx_price_crop_date
ON price_records (crop_id, price_date DESC, id)
"""
with engine.begin() as conn:
    conn.execute(text(INDEX_SQL))
    conn.execute(text("ANALYZE price_records"))
print("idx_price_crop_date ready")
