"""Shared fixture: run the real transform + load code on a tiny synthetic dataset.

No real reservations are used, so the suite passes on a fresh clone (data/raw/ is gitignored).

Hand-built scenario (all in Sept 2026):
  R01 airbnb accepted  Sep 01-03 (2 nights) nightly 200 + 300 = 500, cleaning 150, promo -50, fee -60 -> payout 540
  R02 vrbo   accepted  Sep 10-13 (3 nights) no breakdown, rent 300 -> 100/night, fee -30 -> payout 270
  R03 vrbo   expired   Sep 11-12, requested after R02 was booked (a lost request on sold dates)
  R04 airbnb cancelled Sep 20-22
Calendar pulled Sep 05: Sep 10-12 reserved, every other night Sep 05-Oct 15 open at $150
(covers the Oct 9-10 Homecoming event nights in the seed events).
"""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import load  # noqa: E402
import transform  # noqa: E402
from test_transform import bd, fake_res  # noqa: E402


def synthetic_reservations():
    r1 = fake_res("2026-09-01", 2, acc=50000, breakdown=bd(("2026-09-01", 20000), ("2026-09-02", 30000)),
                  discounts=(("Promotion Discount", -5000),), host_fees=(("Host service fee", -6000),))
    r2 = fake_res("2026-09-10", 3, platform="vrbo", acc=30000, breakdown=None, cleaning=0,
                  host_fees=(("Vrbo commission", -3000),))
    r2["booking_date"] = "2026-08-01"
    r3 = fake_res("2026-09-11", 1, status="expired", platform="vrbo", acc=10000, cleaning=0,
                  host_fees=(("Vrbo commission", -500),))
    r3["booking_date"] = "2026-08-20"
    r4 = fake_res("2026-09-20", 2, status="cancelled", acc=0, cleaning=0, host_fees=())
    return [r1, r2, r3, r4]


def synthetic_calendar():
    from datetime import date, timedelta
    days = []
    for k in range((date(2026, 10, 15) - date(2026, 9, 5)).days + 1):
        iso = (date(2026, 9, 5) + timedelta(days=k)).isoformat()
        reserved = iso in ("2026-09-10", "2026-09-11", "2026-09-12")
        days.append({"date": iso, "min_stay": 1, "note": None,
                     "status": {"reason": "RESERVED" if reserved else "AVAILABLE", "available": not reserved},
                     "price": {"amount": 15000}})
    return days


@pytest.fixture
def fixture_db(tmp_path, monkeypatch):
    raw = tmp_path / "raw"
    raw.mkdir()
    (raw / "reservations_20260905T120000Z.json").write_text(json.dumps({"data": synthetic_reservations()}))
    (raw / "calendar_20260905T120000Z.json").write_text(
        json.dumps({"pulled_at": "2026-09-05T12:00:00+00:00", "days": synthetic_calendar()}))
    monkeypatch.setattr(transform, "RAW_DIR", raw)
    con = load.build(tmp_path / "fixture.db")
    yield con
    con.close()
