"""End-to-end tests on the synthetic fixture database (see conftest.py) plus PII checks on exports."""
import re
from pathlib import Path

import pandas as pd
import pytest

import load

ROOT = Path(__file__).resolve().parent.parent
SQL_DIR = ROOT / "sql" / "analysis"
PROCESSED = ROOT / "data" / "processed"


def test_all_reconciliation_checks_pass(fixture_db):
    for label, sql in load.CHECKS.items():
        assert pd.read_sql(sql, fixture_db).empty, label


def test_nightly_totals_reconcile_to_the_cent(fixture_db):
    df = pd.read_sql("""SELECT r.reservation_id, r.host_accommodation, SUM(n.nightly_rate) AS s, COUNT(*) AS k
                        FROM reservations r JOIN reservation_nights n USING (reservation_id)
                        GROUP BY 1""", fixture_db).set_index("reservation_id")
    assert df.loc["R01", "s"] == pytest.approx(500.00) and df.loc["R01", "k"] == 2
    assert df.loc["R02", "s"] == pytest.approx(300.00) and df.loc["R02", "k"] == 3
    assert set(df.index) == {"R01", "R02"}  # expired and cancelled stays have no nights


def test_double_booking_is_detected(fixture_db):
    sql = load.CHECKS["no night is double booked across accepted stays"]
    assert pd.read_sql(sql, fixture_db).empty
    fixture_db.execute("INSERT INTO reservation_nights VALUES ('R02', '2026-09-01', 100, 0)")
    bad = pd.read_sql(sql, fixture_db)
    assert list(bad.night_date) == ["2026-09-01"]


def test_kpi_math_matches_hand_calculation(fixture_db):
    k = pd.read_sql((SQL_DIR / "01_headline_kpis.sql").read_text(encoding="utf-8"), fixture_db).iloc[0]
    # Window Aug 15 - Dec 31 2026 = 139 nights; booked = 2 (R01) + 3 (R02) = 5.
    assert k.calendar_nights == 139
    assert k.booked_nights == 5
    assert k.occupancy_pct == round(100 * 5 / 139, 1)                  # 3.6
    assert k.adr == pytest.approx((200 + 300 + 100 * 3) / 5)           # 160.00
    # Net ex cleaning: R01 (540 - 150) = 390, R02 270 -> 660 total.
    assert k.net_revenue == pytest.approx(660.00)
    assert k.net_revpar == pytest.approx(round(660 / 139, 2))


def test_lost_request_overlap_found(fixture_db):
    lost = pd.read_sql((SQL_DIR / "13_lost_requests.sql").read_text(encoding="utf-8"), fixture_db)
    assert list(lost.lost_request) == ["R03"]
    assert lost.overlapping_stay.iloc[0] == "R02" and lost.already_sold_at_request.iloc[0] == 1


@pytest.mark.parametrize("sql_file", sorted(SQL_DIR.glob("*.sql")), ids=lambda p: p.stem)
def test_every_analysis_query_runs_and_returns_rows(fixture_db, sql_file):
    df = pd.read_sql(sql_file.read_text(encoding="utf-8"), fixture_db)
    assert len(df) > 0, f"{sql_file.name} returned no rows"


PII_PATTERNS = {
    "email": re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),
    "phone": re.compile(r"(?<!\d)\(?\d{3}\)?[-.\s]\d{3}[-.\s]\d{4}(?!\d)"),
    "airbnb code": re.compile(r"\bHM[A-Z0-9]{8}\b"),
    "vrbo code": re.compile(r"\b(?:HA-[A-Z0-9]{6}|VRBO-[A-Z0-9]{6})\b"),
    "uuid (raw API id)": re.compile(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b"),
}
FORBIDDEN_COLUMNS = {"code", "platform_id", "conversation_id", "guest_name", "first_name", "last_name",
                     "email", "phone", "notes"}


@pytest.mark.parametrize("csv", sorted(PROCESSED.glob("*.csv")) + sorted((ROOT / "results").glob("*.csv")),
                         ids=lambda p: f"{p.parent.name}/{p.stem}")
def test_no_pii_in_processed_exports(csv):
    text = csv.read_text(encoding="utf-8")
    for label, rx in PII_PATTERNS.items():
        assert not rx.search(text), f"{csv.name}: possible {label}"
    cols = set(pd.read_csv(csv, nrows=0).columns)
    assert not cols & FORBIDDEN_COLUMNS, f"{csv.name}: forbidden columns {cols & FORBIDDEN_COLUMNS}"


def test_calendar_notes_not_exported():
    assert "note" not in pd.read_csv(PROCESSED / "nightly.csv", nrows=0).columns


def test_reservation_ids_are_surrogates():
    res = pd.read_csv(PROCESSED / "reservations.csv")
    assert res.reservation_id.str.fullmatch(r"R\d{2}").all()
