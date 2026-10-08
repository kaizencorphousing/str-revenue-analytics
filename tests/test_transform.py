"""Offline tests for src/transform.py using small synthetic reservations (no real guest data)."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
import transform as t  # noqa: E402


def money(c):
    return {"amount": c, "formatted": f"${c / 100:.2f}"}


def fake_res(arrival, nights, status="accepted", platform="airbnb", acc=30000, breakdown=None,
             discounts=(), host_fees=(("Host service fee", -3000),), cleaning=15000, taxes=()):
    disc = [{"label": l, "amount": a} for l, a in discounts]
    fees = [{"label": l, "amount": a} for l, a in host_fees]
    tax = [{"label": l, "amount": a} for l, a in taxes]
    from datetime import date, timedelta
    departure = (date.fromisoformat(arrival) + timedelta(days=nights)).isoformat()
    revenue = acc + cleaning + sum(a for _, a in discounts) + sum(a for _, a in host_fees) + sum(a for _, a in taxes)
    return {
        "arrival_date": f"{arrival}T16:00:00-04:00", "departure_date": departure, "booking_date": "2026-07-01",
        "nights": nights, "platform": platform, "status": status, "guests": {"total": 4},
        "financials": {"host": {
            "accommodation": money(acc),
            "accommodation_breakdown": breakdown,
            "guest_fees": [{"label": "Cleaning fee", "amount": cleaning}] if cleaning else [],
            "host_fees": fees, "discounts": disc, "taxes": tax, "adjustments": [],
            "revenue": money(revenue)}},
    }


def bd(*pairs):
    return [{"label": d, "amount": a, "category": "Accommodation"} for d, a in pairs]


def test_surrogate_ids_follow_checkin_order_and_cents_become_dollars():
    log = t.QualityLog()
    res, _ = t.build_reservations([
        fake_res("2026-10-02", 1, breakdown=bd(("2026-10-02", 30000))),
        fake_res("2026-09-01", 1, breakdown=bd(("2026-09-01", 30000))),
    ], log)
    assert list(res.reservation_id) == ["R01", "R02"]
    assert list(res.checkin) == ["2026-09-01", "2026-10-02"]
    assert res.host_accommodation.iloc[0] == 300.00 and res.cleaning_fee.iloc[0] == 150.00
    assert "code" not in res.columns and "platform_id" not in res.columns


def test_duplicate_breakdown_dates_are_summed_and_logged():
    log = t.QualityLog()
    _, nights = t.build_reservations([fake_res(
        "2026-10-23", 2, acc=30000,
        breakdown=bd(("2026-10-23", 10000), ("2026-10-23", 5000), ("2026-10-24", 15000)))], log)
    assert list(nights.nightly_rate) == [150.0, 150.0]
    assert [e["check_name"] for e in log] == ["duplicate_night_rows"]


def test_missing_breakdown_is_spread_to_the_cent():
    log = t.QualityLog()
    _, nights = t.build_reservations([fake_res("2027-03-19", 3, platform="vrbo", acc=10000, breakdown=None)], log)
    assert list(nights.nightly_rate) == [33.34, 33.33, 33.33]
    assert round(nights.nightly_rate.sum(), 2) == 100.00
    assert set(nights.allocated) == {1}


def test_discount_mapping_and_unknown_label_goes_to_other():
    log = t.QualityLog()
    res, _ = t.build_reservations([fake_res(
        "2026-09-01", 1, breakdown=bd(("2026-09-01", 30000)),
        discounts=(("Daily_discount", -1000), ("Mystery deal", -500)))], log)
    assert res.discount_top_rated.iloc[0] == 10.0 and res.discount_other.iloc[0] == 5.0
    assert any(e["check_name"] == "unmapped_discount" for e in log)


def test_denied_maps_to_declined_and_gets_no_nights():
    log = t.QualityLog()
    res, nights = t.build_reservations([fake_res("2026-09-26", 1, status="denied", platform="vrbo")], log)
    assert res.status.iloc[0] == "declined" and nights.empty


def test_revenue_that_does_not_reconcile_raises():
    r = fake_res("2026-09-01", 1, breakdown=bd(("2026-09-01", 30000)))
    r["financials"]["host"]["revenue"]["amount"] += 1
    with pytest.raises(ValueError, match="revenue"):
        t.build_reservations([r], t.QualityLog())


def test_dim_date_weekend_is_fri_and_sat_nights():
    d = t.build_dim_date().set_index("date")
    assert d.loc["2026-10-16", "is_weekend"] == 1  # Friday
    assert d.loc["2026-10-17", "is_weekend"] == 1  # Saturday
    assert d.loc["2026-10-18", "is_weekend"] == 0  # Sunday
    assert d.index[0] == "2026-08-15" and d.index[-1] == "2027-06-30"


def test_checkout_must_match_nights():
    r = fake_res("2026-09-01", 1, breakdown=bd(("2026-09-01", 30000)))
    r["departure_date"] = "2026-09-05"
    with pytest.raises(ValueError, match="nights"):
        t.build_reservations([r], t.QualityLog())


def test_pms_fee_and_taxes_split_from_platform_fee():
    log = t.QualityLog()
    res, _ = t.build_reservations([fake_res(
        "2026-09-26", 1, status="denied", platform="vrbo", cleaning=0,
        host_fees=(("Hospitable service fee", -1275), ("Vrbo commission", -1455)),
        taxes=(("County lodging tax", 1455),))], log)
    row = res.iloc[0]
    assert (row.platform_fee, row.pms_fee, row.host_taxes) == (14.55, 12.75, 14.55)
