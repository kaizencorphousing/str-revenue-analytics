"""Turn raw Hospitable JSON (data/raw/) and seed CSVs (data/seed/) into clean tables.

This is the only place cents become dollars. Every cleaning decision is appended to the
data-quality log so it ends up in the `data_quality_log` table. No guest-identifying fields
(names, confirmation codes, conversation ids) are carried into any output.
"""
import json
from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw"
SEED_DIR = ROOT / "data" / "seed"

DATE_START, DATE_END = date(2026, 8, 15), date(2027, 6, 30)
STATUS_MAP = {"accepted": "accepted", "cancelled": "cancelled", "denied": "declined",
              "declined": "declined", "expired": "expired", "request": "request"}
DISCOUNT_MAP = {"Promotion Discount": "discount_promo", "Daily_discount": "discount_top_rated",
                "Length Of Stay Discount": "discount_length_of_stay",
                "Early booking": "discount_early_booking"}
DISCOUNT_COLS = ["discount_promo", "discount_top_rated", "discount_length_of_stay",
                 "discount_early_booking", "discount_other"]
CALENDAR_STATUS = {"AVAILABLE": "open", "RESERVED": "reserved"}  # anything else -> blocked


def dollars(cents: int) -> float:
    return round(cents / 100, 2)


class QualityLog(list):
    def add(self, check, detail, action, reservation_id=None, night_date=None):
        self.append({"check_name": check, "reservation_id": reservation_id,
                     "night_date": night_date, "detail": detail, "action": action})


def raw_files(kind: str) -> list[Path]:
    files = sorted(RAW_DIR.glob(f"{kind}_*.json"))
    if not files:
        raise FileNotFoundError(f"No {kind}_*.json in {RAW_DIR}. Run src/extract.py first.")
    return files


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _split_nightly(total_cents: int, nights: int) -> list[int]:
    """Spread cents evenly; the first nights absorb the remainder so the sum is exact."""
    base, rem = divmod(total_cents, nights)
    return [base + (1 if i < rem else 0) for i in range(nights)]


def build_reservations(raw: list[dict], log: QualityLog) -> tuple[pd.DataFrame, pd.DataFrame]:
    raw = sorted(raw, key=lambda r: (r["arrival_date"], r["booking_date"]))
    res_rows, night_rows = [], []
    for i, r in enumerate(raw, 1):
        rid = f"R{i:02d}"
        h = r["financials"]["host"]
        checkin = date.fromisoformat(r["arrival_date"][:10])
        nights = r["nights"]

        status = STATUS_MAP.get(r["status"])
        if status is None:
            raise ValueError(f"{rid}: unknown status {r['status']!r}")
        if status != r["status"]:
            log.add("status_mapping", f"API status '{r['status']}' mapped to '{status}'", "relabelled", rid)

        acc = h["accommodation"]["amount"]
        cleaning = sum(f["amount"] for f in h["guest_fees"] if f["label"] == "Cleaning fee")
        other_guest_fees = [f for f in h["guest_fees"] if f["label"] != "Cleaning fee"]
        for f in other_guest_fees:
            log.add("unmapped_guest_fee", f"guest fee '{f['label']}' not modelled", "kept in host_revenue only", rid)
        disc = dict.fromkeys(DISCOUNT_COLS, 0)
        for d in h["discounts"]:
            col = DISCOUNT_MAP.get(d["label"], "discount_other")
            if col == "discount_other":
                log.add("unmapped_discount", f"discount label '{d['label']}'", "counted as discount_other", rid)
            disc[col] += -d["amount"]  # API sends discounts negative
        pms_fee = -sum(f["amount"] for f in h["host_fees"] if f["label"] == "Hospitable service fee")
        platform_fee = -sum(f["amount"] for f in h["host_fees"]) - pms_fee
        taxes = sum(t["amount"] for t in h["taxes"])
        adjustments = sum(a["amount"] for a in h["adjustments"])
        revenue = h["revenue"]["amount"]

        # The API's revenue must be explainable from its parts, to the cent.
        rebuilt = (acc + cleaning + sum(f["amount"] for f in other_guest_fees)
                   - sum(disc.values()) - platform_fee - pms_fee + taxes + adjustments)
        if rebuilt != revenue:
            raise ValueError(f"{rid}: revenue {revenue} != components {rebuilt} (cents)")
        if taxes:
            log.add("pass_through_tax", f"host taxes {dollars(taxes):.2f} included in API revenue",
                    "stored in host_taxes; excluded from net revenue", rid)
        checkout = date.fromisoformat(r["departure_date"][:10])
        if (checkout - checkin).days != nights:
            raise ValueError(f"{rid}: checkout - checkin != nights ({nights})")

        res_rows.append({
            "reservation_id": rid, "platform": r["platform"], "booked_at": r["booking_date"][:10],
            "checkin": checkin.isoformat(), "checkout": checkout.isoformat(), "nights": nights,
            "guests": r["guests"]["total"], "status": status,
            "host_accommodation": dollars(acc), "cleaning_fee": dollars(cleaning),
            **{k: dollars(v) for k, v in disc.items()},
            "platform_fee": dollars(platform_fee), "pms_fee": dollars(pms_fee),
            "host_taxes": dollars(taxes), "host_revenue": dollars(revenue),
        })

        if status != "accepted":
            if status == "cancelled":
                log.add("cancelled_excluded", f"cancelled stay, revenue {dollars(revenue):.2f}",
                        "row kept; excluded from revenue and nights", rid)
            continue

        stay_dates = [(checkin + timedelta(days=k)).isoformat() for k in range(nights)]
        breakdown = h.get("accommodation_breakdown") or []
        if breakdown:
            per_date: dict[str, int] = {}
            for b in breakdown:
                per_date[b["label"]] = per_date.get(b["label"], 0) + b["amount"]
            if len(breakdown) != len(per_date):
                dupes = sorted(d for d in per_date if sum(b["label"] == d for b in breakdown) > 1)
                log.add("duplicate_night_rows", f"{len(breakdown)} breakdown rows for {len(per_date)} nights; "
                        f"split rates on {', '.join(dupes)}", "summed per date", rid)
            if sorted(per_date) != stay_dates:
                raise ValueError(f"{rid}: breakdown dates don't match the stay dates")
            for d in stay_dates:
                night_rows.append({"reservation_id": rid, "night_date": d,
                                   "nightly_rate": dollars(per_date[d]), "allocated": 0})
        else:
            log.add("no_nightly_breakdown", f"{r['platform']} gave no per-night prices",
                    f"spread {dollars(acc):.2f} evenly over {nights} nights (allocated=1)", rid)
            for d, c in zip(stay_dates, _split_nightly(acc, nights)):
                night_rows.append({"reservation_id": rid, "night_date": d,
                                   "nightly_rate": dollars(c), "allocated": 1})

    return pd.DataFrame(res_rows), pd.DataFrame(night_rows)


def build_calendar(files: list[Path], log: QualityLog) -> pd.DataFrame:
    """One row per (snapshot_date, night). If two pulls share a day, the later one wins."""
    by_day: dict[str, Path] = {}
    for f in files:  # sorted by timestamp, so later files overwrite earlier ones
        day = read_json(f)["pulled_at"][:10]
        if day in by_day:
            log.add("same_day_snapshots", f"{by_day[day].name} superseded by {f.name}", "kept the later pull")
        by_day[day] = f
    rows, unknown = [], set()
    for day, f in sorted(by_day.items()):
        for d in read_json(f)["days"]:
            reason = d["status"]["reason"]
            status = CALENDAR_STATUS.get(reason, "blocked")
            if reason not in CALENDAR_STATUS and reason not in unknown:
                unknown.add(reason)
                log.add("unknown_calendar_status", f"calendar reason '{reason}' first seen on {d['date']}",
                        "treated as blocked", night_date=d["date"])
            rows.append({"snapshot_date": day, "night_date": d["date"],
                         "price": dollars(d["price"]["amount"]) if d.get("price") else None,
                         "min_stay": d.get("min_stay"), "status": status, "note": d.get("note")})
    return pd.DataFrame(rows)


def build_dim_date() -> pd.DataFrame:
    days = pd.date_range(DATE_START, DATE_END, freq="D")
    return pd.DataFrame({
        "date": days.strftime("%Y-%m-%d"),
        "day_name": days.day_name(),
        "is_weekend": days.dayofweek.isin([4, 5]).astype(int),  # Fri and Sat nights
        "year_month": days.strftime("%Y-%m"),
        "month": days.month,
        "year": days.year,
    })


def load_seeds() -> dict[str, pd.DataFrame]:
    return {p.stem: pd.read_csv(p) for p in sorted(SEED_DIR.glob("*.csv"))}


def build_all() -> dict[str, pd.DataFrame]:
    log = QualityLog()
    res_file = raw_files("reservations")[-1]
    reservations, nights = build_reservations(read_json(res_file)["data"], log)
    calendar = build_calendar(raw_files("calendar"), log)
    tables = {"reservations": reservations, "reservation_nights": nights,
              "calendar_snapshot": calendar, "dim_date": build_dim_date(), **load_seeds()}
    tables["data_quality_log"] = pd.DataFrame(
        log, columns=["check_name", "reservation_id", "night_date", "detail", "action"])
    tables["_source"] = pd.DataFrame([{"reservations_file": res_file.name,
                                       "built_at": datetime.now().isoformat(timespec="seconds")}])
    return tables
