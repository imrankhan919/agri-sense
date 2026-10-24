from sqlalchemy import text
from app.database import engine

CREATE_MV = """
CREATE MATERIALIZED VIEW IF NOT EXISTS mv_monthly_prices AS
SELECT crop_id,
 market_id,
 date_trunc('month', price_date)::date AS month,
 ROUND(AVG(modal_price)::numeric, 2) AS avg_price,
 MIN(modal_price) AS min_price,
 MAX(modal_price) AS max_price,
 COUNT(*) AS samples
FROM price_records
GROUP BY crop_id, market_id, date_trunc('month', price_date)
"""

CREATE_INDEX = """
CREATE UNIQUE INDEX IF NOT EXISTS ux_mv_monthly
ON mv_monthly_prices (crop_id, market_id, month)
"""

def main() -> None:
    with engine.begin() as conn:
        conn.execute(text(CREATE_MV))
        conn.execute(text(CREATE_INDEX))
        conn.execute(text("REFRESH MATERIALIZED VIEW mv_monthly_prices"))
        count = conn.execute(text("SELECT COUNT(*) FROM mv_monthly_prices")).scalar()
    print(f"mv_monthly_prices ready: {count:,} rows")
    
if __name__ == "__main__":
    main()