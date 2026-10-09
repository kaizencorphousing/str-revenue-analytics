"""Export anonymized CSVs from gainesville.db to data/processed/ for the dashboard.

The dashboard reads only these files, so it can be deployed publicly without the API,
the token or the raw data. Only surrogate ids, dates, counts and money leave the database;
calendar notes are deliberately not exported.
Usage: python src/export.py
"""
import sqlite3
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "gainesville.db"
SQL_DIR = ROOT / "sql" / "analysis"
OUT_DIR = ROOT / "data" / "processed"

TABLE_EXPORTS = {
    "nightly": """
        SELECT night_date, day_name, is_weekend, year_month, reservation_id, platform,
               nightly_rate, net_rev_ex_cleaning, snapshot_price, event, event_type, night_status
        FROM fact_nightly ORDER BY night_date""",
    "reservations": """
        SELECT reservation_id, platform, booked_at, checkin, checkout, nights, status,
               host_accommodation, cleaning_fee, discount_promo, discount_top_rated,
               discount_length_of_stay, discount_early_booking, discount_other,
               platform_fee, pms_fee, host_taxes, host_revenue
        FROM reservations ORDER BY reservation_id""",
    "price_changes": "SELECT * FROM price_changes ORDER BY night_date, changed_on",
    "cost_assumptions": "SELECT * FROM cost_assumptions",
    "meta": """
        SELECT (SELECT MAX(snapshot_date) FROM calendar_snapshot) AS snapshot_date,
               (SELECT amount FROM cost_assumptions WHERE item = 'rent_monthly') AS rent_monthly""",
}
# Analysis query outputs the dashboard shows as-is (file stem -> export name).
QUERY_EXPORTS = {
    "05_discount_leakage": "discount_leakage",
    "06_channel_comparison": "channel_comparison",
    "09_price_vs_market": "price_vs_market",
    "13_lost_requests": "lost_requests",
}


def main() -> None:
    if not DB_PATH.exists():
        sys.exit("gainesville.db not found. Run src/load.py first.")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    exports = {name: pd.read_sql(sql, con) for name, sql in TABLE_EXPORTS.items()}
    for stem, name in QUERY_EXPORTS.items():
        exports[name] = pd.read_sql((SQL_DIR / f"{stem}.sql").read_text(encoding="utf-8"), con)
    con.close()
    for name, df in exports.items():
        df.to_csv(OUT_DIR / f"{name}.csv", index=False, lineterminator="\n")
        print(f"  data/processed/{name}.csv  {len(df)} rows")


if __name__ == "__main__":
    main()
