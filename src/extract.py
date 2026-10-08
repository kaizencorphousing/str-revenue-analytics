"""Extract raw reservations and calendar data for the GAINESVILLE property from the Hospitable API.

Read-only: this module only ever issues GET requests. Raw JSON is written to data/raw/
(gitignored) with a UTC timestamp in the filename, so every run adds a new snapshot and
older snapshots are never overwritten. Nothing guest-identifying is printed.
"""
import json
import os
import sys
import time
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv

BASE_URL = "https://public.api.hospitable.com/v2"
PROPERTY_NAME = "GAINESVILLE"
RES_START, RES_END = "2026-06-01", "2027-12-31"  # check-in window
CAL_END = date(2027, 6, 30)
CAL_CHUNK_DAYS = 365  # one call covered 266 days in testing; chunk defensively anyway
MAX_RETRIES = 5

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw"


def make_session() -> requests.Session:
    load_dotenv(ROOT / ".env")
    token = os.environ.get("HOSPITABLE_TOKEN", "").strip()
    if not token:
        sys.exit("HOSPITABLE_TOKEN is missing. Copy .env.example to .env and add your token.")
    s = requests.Session()
    s.headers.update({"Authorization": f"Bearer {token}", "Accept": "application/json"})
    return s


def get_json(session: requests.Session, path: str, params=None) -> dict:
    """GET with backoff on HTTP 429 and transient 5xx. GET is the only verb this project uses."""
    url = path if path.startswith("http") else f"{BASE_URL}{path}"
    for attempt in range(MAX_RETRIES + 1):
        resp = session.get(url, params=params, timeout=30)
        if resp.status_code == 429 or resp.status_code >= 500:
            if attempt == MAX_RETRIES:
                break
            try:
                wait = float(resp.headers["Retry-After"])
            except (KeyError, ValueError):  # missing, or sent as an HTTP date
                wait = 2 ** attempt
            print(f"  HTTP {resp.status_code}, retrying in {wait:.0f}s")
            time.sleep(wait)
            continue
        resp.raise_for_status()
        return resp.json()
    resp.raise_for_status()
    raise RuntimeError(f"Gave up on {url} after {MAX_RETRIES} retries")


def get_all_pages(session: requests.Session, path: str, params: dict) -> list:
    """Follow page=1..meta.last_page and return the concatenated `data` lists."""
    rows, page = [], 1
    while True:
        body = get_json(session, path, {**params, "page": page})
        rows.extend(body["data"])
        if page >= body["meta"]["last_page"]:
            return rows
        page += 1


def find_property(session: requests.Session) -> dict:
    props = get_all_pages(session, "/properties", {"per_page": 50})
    matches = [p for p in props if p.get("name") == PROPERTY_NAME]
    if len(matches) != 1:
        listing = "\n".join(f"  {p['id']}  {p.get('name')}" for p in props)
        sys.exit(f"Expected exactly one property named {PROPERTY_NAME}, found {len(matches)}:\n{listing}")
    return matches[0]


def fetch_reservations(session: requests.Session, property_id: str) -> list:
    # No status filter on purpose: the API returns every status by default, and its filter
    # does not accept "declined" or "expired" (it calls them "denied" / not filterable).
    params = {"properties[]": property_id, "start_date": RES_START, "end_date": RES_END,
              "date_query": "checkin", "include": "financials,properties", "per_page": 100}
    rows = get_all_pages(session, "/reservations", params)
    # Guard against client properties leaking in: every row must belong to GAINESVILLE.
    stray = [r["id"] for r in rows if {p["id"] for p in r.get("properties", [])} != {property_id}]
    if stray:
        sys.exit(f"{len(stray)} reservations are not tied only to {PROPERTY_NAME}; refusing to save.")
    return rows


def fetch_calendar(session: requests.Session, property_id: str, start: date, end: date) -> list:
    days, chunk_start = [], start
    while chunk_start <= end:
        chunk_end = min(chunk_start + timedelta(days=CAL_CHUNK_DAYS - 1), end)
        body = get_json(session, f"/properties/{property_id}/calendar",
                        {"start_date": chunk_start.isoformat(), "end_date": chunk_end.isoformat()})
        days.extend(body["data"]["days"])
        chunk_start = chunk_end + timedelta(days=1)
    return days


def save_raw(kind: str, payload: dict, stamp: str) -> Path:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    path = RAW_DIR / f"{kind}_{stamp}.json"
    if path.exists():  # never overwrite an earlier snapshot
        raise FileExistsError(path)
    path.write_text(json.dumps(payload, indent=1), encoding="utf-8")
    return path


def main() -> None:
    pulled_at = datetime.now(timezone.utc)
    stamp = pulled_at.strftime("%Y%m%dT%H%M%SZ")
    session = make_session()

    prop = find_property(session)
    print(f"Property: {prop['name']} ({prop['id']})")

    reservations = fetch_reservations(session, prop["id"])
    cal_start = date.today()
    calendar = fetch_calendar(session, prop["id"], cal_start, CAL_END)

    meta = {"pulled_at": pulled_at.isoformat(), "property_id": prop["id"], "property_name": prop["name"]}
    files = [
        save_raw("property", {**meta, "data": prop}, stamp),
        save_raw("reservations", {**meta, "check_in_from": RES_START, "check_in_to": RES_END,
                                  "data": reservations}, stamp),
        save_raw("calendar", {**meta, "start_date": cal_start.isoformat(), "end_date": CAL_END.isoformat(),
                              "days": calendar}, stamp),
    ]

    print(f"\nReservations: {len(reservations)}")
    for status, n in sorted(Counter(r["status"] for r in reservations).items()):
        print(f"  {status:<10} {n}")
    dates = [d["date"] for d in calendar]
    print(f"\nCalendar days: {len(calendar)} ({min(dates)} to {max(dates)})")
    for status, n in sorted(Counter(d["status"]["available"] for d in calendar).items()):
        print(f"  available={status!s:<6} {n}")
    print("\nSaved:")
    for f in files:
        print(f"  {f.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
