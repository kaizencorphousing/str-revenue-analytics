"""Build gainesville.db from the latest raw snapshot + seed CSVs, then run reconciliation checks.

Usage: python src/load.py
Exits non-zero if any check fails, so the pipeline can't silently continue on bad data.
"""
import sqlite3
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from transform import ROOT, build_all  # noqa: E402

DB_PATH = ROOT / "gainesville.db"
SCHEMA = ROOT / "sql" / "schema.sql"

# Each check is a query that returns the offending rows; zero rows means pass.
CHECKS = {
    "nightly prices sum to host_accommodation (to the cent)": """
        SELECT r.reservation_id, r.host_accommodation, ROUND(SUM(n.nightly_rate), 2) AS nightly_sum
        FROM reservations r JOIN reservation_nights n USING (reservation_id)
        WHERE r.status = 'accepted'
        GROUP BY r.reservation_id
        HAVING ROUND(SUM(n.nightly_rate) * 100) != ROUND(r.host_accommodation * 100)""",
    "every accepted stay has exactly `nights` night rows": """
        SELECT r.reservation_id, r.nights, COUNT(n.night_date) AS night_rows
        FROM reservations r LEFT JOIN reservation_nights n USING (reservation_id)
        WHERE r.status = 'accepted'
        GROUP BY r.reservation_id HAVING COUNT(n.night_date) != r.nights""",
    "only accepted stays have night rows": """
        SELECT DISTINCT n.reservation_id, r.status
        FROM reservation_nights n JOIN reservations r USING (reservation_id)
        WHERE r.status != 'accepted'""",
    "no night is double booked across accepted stays": """
        SELECT night_date, COUNT(*) AS stays FROM reservation_nights
        GROUP BY night_date HAVING COUNT(*) > 1""",
    "latest calendar 'reserved' nights match accepted bookings": """
        WITH latest AS (SELECT * FROM calendar_snapshot
                        WHERE snapshot_date = (SELECT MAX(snapshot_date) FROM calendar_snapshot))
        SELECT l.night_date, l.status, n.reservation_id
        FROM latest l LEFT JOIN reservation_nights n USING (night_date)
        WHERE (l.status = 'reserved') != (n.reservation_id IS NOT NULL)""",
    "fact_nightly has one row per date (no join fan-out)": """
        SELECT (SELECT COUNT(*) FROM fact_nightly) AS fact_rows, (SELECT COUNT(*) FROM dim_date) AS dates
        WHERE (SELECT COUNT(*) FROM fact_nightly) != (SELECT COUNT(*) FROM dim_date)""",
}


def build(db_path: Path = DB_PATH) -> sqlite3.Connection:
    tables = build_all()
    source = tables.pop("_source").iloc[0]
    con = sqlite3.connect(db_path)
    con.executescript(SCHEMA.read_text(encoding="utf-8"))
    for name, df in tables.items():
        df.to_sql(name, con, if_exists="append", index=False)
    con.commit()
    print(f"Built {db_path.name} from {source.reservations_file}\n")
    return con


def report(con: sqlite3.Connection) -> bool:
    print("Row counts")
    names = [r[0] for r in con.execute(
        "SELECT name FROM sqlite_master WHERE type IN ('table','view') ORDER BY type, name")]
    for n in names:
        print(f"  {n:<20} {con.execute(f'SELECT COUNT(*) FROM {n}').fetchone()[0]:>5}")

    print("\nReconciliation checks")
    ok = True
    for label, sql in CHECKS.items():
        bad = pd.read_sql(sql, con)
        print(f"  [{'PASS' if bad.empty else 'FAIL'}] {label}")
        if not bad.empty:
            ok = False
            print(bad.to_string(index=False))

    print("\nnight_status counts (fact_nightly)")
    print(pd.read_sql("SELECT night_status, COUNT(*) AS nights FROM fact_nightly GROUP BY 1 ORDER BY 2 DESC",
                      con).to_string(index=False))

    print("\ndata_quality_log")
    with pd.option_context("display.max_colwidth", 70, "display.width", 200):
        print(pd.read_sql("SELECT log_id, check_name, reservation_id, detail, action FROM data_quality_log",
                          con).to_string(index=False))
    return ok


def main() -> None:
    con = build()
    ok = report(con)
    con.close()
    if not ok:
        sys.exit("\nOne or more reconciliation checks FAILED.")
    print("\nAll reconciliation checks passed.")


if __name__ == "__main__":
    main()
