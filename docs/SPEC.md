# Spec: STR Revenue Analytics

## Goal
A portfolio-quality, end-to-end analytics project built from real data: API extraction, a SQL data model, analysis queries, an interactive dashboard, tests, documentation and a public GitHub repo. It must hold up in a data/CS job interview, so every number traces back to a query and every step is explainable.

## Context
I operate a 4 bed / 4 bath townhouse at Lexington Crossing, Gainesville FL, near the University of Florida, listed on Airbnb and Vrbo and managed in Hospitable. Rent is $2,350/month. My cleaner charges $180 per turnover. The unit launched in August 2026. September was strong (one 31-night stay); October and November collapsed.

**Business question:** Why did October and November stall, and where is the revenue recoverable?

## Out of scope
- Any write to Hospitable, Airbnb or Vrbo.
- The client properties in the same Hospitable account.
- Machine learning or forecasting. The sample is about 9 stays; descriptive analysis only.

## Target layout
```
.claude/            settings, hooks, skills, agents (already present)
app/dashboard.py
data/raw/           gitignored, raw API JSON
data/seed/          provided seed CSVs (already present)
data/processed/     anonymized CSV exports (committed; the dashboard reads only these)
docs/               SPEC, PROGRESS, LEARNING_NOTES, TABLEAU_GUIDE, RESUME, SCHEDULE
results/            query outputs + RESULTS.md
sql/schema.sql
sql/analysis/01_...sql to 13_...sql
src/extract.py, src/transform.py, src/load.py, src/run_queries.py, src/export.py
tests/
run_all.py, requirements.txt, README.md, .gitignore, .env.example
```

---

## Phase 0: Scaffold
- `.venv`, `requirements.txt` (pinned: requests, python-dotenv, pandas, streamlit, plotly, pytest), `.gitignore` (must include `.env`, `.venv/`, `data/raw/`, `*.db`, `__pycache__/`), `.env.example` with `HOSPITABLE_TOKEN=`.
- `git init`, first commit.
- **Done when:** `git check-ignore .env data/raw/x.json gainesville.db` lists all three, and `pip install -r requirements.txt` succeeds.

## Phase 1: Extract (`src/extract.py`)
- Verify the current Hospitable public API docs first (expected base `https://public.api.hospitable.com/v2`, header `Authorization: Bearer <token>`). Make one small request to confirm the response shape before writing the full extractor. Adapt if the docs differ and tell me what changed.
- Find the property id for `GAINESVILLE`. If not certain, list property names and ids only and ask me.
- Reservations: check-in 2026-06-01 to 2027-12-31, all statuses (accepted, cancelled, declined, expired, request), `include=financials`. Paginate. Back off on HTTP 429.
- Calendar: today through 2027-06-30, chunked if needed.
- Save raw JSON to `data/raw/` with a timestamp. Each run adds a new dated calendar snapshot and never overwrites older ones (for booking pace later).
- **Done when:** running it prints counts by status and calendar days pulled, and raw files exist. Don't print guest fields.

## Phase 2: Transform and load (`src/transform.py`, `src/load.py`, `sql/schema.sql`)
SQLite database `gainesville.db`:

| Table | Grain | Notes |
|---|---|---|
| `reservations` | one booking request | surrogate id, platform, booked_at, checkin, checkout, nights, guests, status, host_accommodation (pre-discount rent), cleaning_fee, discount_promo, discount_top_rated, discount_length_of_stay, discount_early_booking, discount_other, platform_fee, host_revenue |
| `reservation_nights` | one booked night | from the per-night accommodation breakdown; `allocated` = 1 when there was no breakdown |
| `calendar_snapshot` | snapshot_date + night | price, min_stay, status (open / reserved / blocked), note |
| `price_changes`, `comps`, `events`, `cost_assumptions` | see `data/seed/` | loaded from seed CSVs |
| `dim_date` | one date | day_name, is_weekend (Fri/Sat nights), year_month, month, year; 2026-08-15 to 2027-06-30 |
| `data_quality_log` | one issue | every cleaning decision |
| `fact_nightly` (VIEW) | one date | date spine LEFT JOIN booked nights, reservations, latest calendar snapshot, events. night_status = booked / open_for_sale / vacant_past / blocked / not_in_snapshot. net_rev_ex_cleaning per booked night = (host_revenue - cleaning_fee) / nights |

Discount label mapping: "Promotion Discount" -> promo, "Daily_discount" -> top_rated, "Length Of Stay Discount" -> length_of_stay, "Early booking" -> early_booking, anything else -> other (and log it).

Data quality rules (log every fix in `data_quality_log`):
- For each accepted reservation, nightly prices must sum to host_accommodation to the cent. A previous manual pull found duplicate date rows on one reservation (a split rate on two nights): sum duplicates per date.
- Vrbo reservations may have no nightly breakdown: spread rent evenly, set `allocated = 1`.
- Cancelled reservations keep their row; financials are excluded from revenue.
- No night is double booked across accepted reservations.
- **Done when:** the build prints table row counts, all reconciliation checks pass, and `data_quality_log` is shown.

## Phase 3: Analysis SQL (`sql/analysis/`, `src/run_queries.py`)
One query per file. Header comment: the question it answers and its assumptions. SQLite syntax; comment any line that would differ in Postgres.

1. Headline KPIs, Aug 15 to Dec 31 2026: calendar nights, booked nights, occupancy %, ADR (pre-discount list price per booked night), net revenue, net RevPAR.
2. Monthly performance: occupancy, ADR, net revenue, open nights, rent.
3. Fri/Sat vs Sun-Thu: occupancy, booked ADR, average ask on open nights.
4. Booking lead time per confirmed stay, bucketed, median via ROW_NUMBER.
5. Discount leakage: $ and % of gross rent per discount type (UNION ALL unpivot).
6. Channel comparison: requests, confirmed, lost, conversion %, fee % of gross, net per night.
7. Stay economics: contribution after the $180 clean, per night, by stay length bucket.
8. Event premium: event-night price vs ordinary-night baseline for the same day type.
9. Price vs market: our total vs comp median, gap %, latest pull flagged with a window function.
10. Price change history: LAG for prior price, $ and % change.
11. Gaps and islands: consecutive unsold-night runs in the latest snapshot, length and value at current ask.
12. Rent coverage per month: net revenue vs rent, gap, nights needed at current average ask net of a 15.5% Airbnb host fee.
13. Lost requests: self-join with interval overlap (a.checkin < b.checkout AND a.checkout > b.checkin) to test whether unconverted requests overlapped already sold dates.

`run_queries.py` writes `results/<name>.csv` and `results/RESULTS.md`.

**Reference numbers from a manual pull on Oct 8 2026.** Yours will differ if bookings changed. If they differ a lot, find out why and tell me before moving on:
- Aug 15 to Dec 31: 139 nights, 51 booked, 36.7% occupancy, ADR $284.14, net revenue ex cleaning $8,786.61
- 15 reservation records: 9 accepted, 1 cancelled, 5 Vrbo requests declined or expired
- Discounts 22.5% of gross rent (top-rated 8.4%, weekly/monthly 9.7%, promo 3.5%, early booking 0.9%)
- All 5 lost Vrbo requests overlapped dates already sold on Airbnb
- Median lead time 77 days
- **Done when:** all 13 run, RESULTS.md exists, and you've compared against the reference numbers.

## Phase 4: Dashboard (`app/dashboard.py`, Streamlit + Plotly)
Reads only `data/processed/*.csv` (never the API or `.env`), so it can be deployed publicly. `src/export.py` writes those CSVs from the database.
- Header: "Why October stalled: STR revenue analytics", one-line description, data snapshot date.
- KPI row: occupancy %, ADR, net RevPAR, net revenue.
- Hero: calendar heatmap (weeks by weekday) colored by night status; hover shows price and event.
- Monthly net revenue vs rent (bars + rent reference line).
- Fri/Sat vs Sun-Thu occupancy and ADR.
- Price change history lines; price vs market gap chart (latest pull, zero line).
- Tab 2 "Where the money leaks": discount leakage, stay economics scatter, channel conversion with the overlap finding.
- Findings panel: 3 to 5 findings written from actual results, each tied to a chart.
- Sidebar date filter driving the nightly charts.
- Restrained design: one accent color for "booked", neutrals elsewhere, readable at laptop width.
- Also write `docs/TABLEAU_GUIDE.md`: exact steps (calculated fields, one sheet per chart, layout) to rebuild the main view in Tableau Public from `data/processed/`.
- **Done when:** `streamlit run app/dashboard.py` starts without errors, every chart renders, and KPI tiles match query 01 exactly. Show me a screenshot or the matching numbers.

## Phase 5: Pipeline, tests, docs, repo
- `run_all.py`: extract, transform, load, queries, export. `--offline` skips extraction.
- `tests/` (pytest): nightly totals reconcile; no double-booked nights; no PII patterns in `data/processed/`; every analysis query runs and returns rows; KPI math matches a hand calculation on a tiny fixture.
- `README.md` as a case study: business question, sources and grain table, Mermaid model diagram, cleaning decisions, findings with numbers, actions taken, limitations (one property, ~9 stays, comps are list prices), reproduce steps, query index with the SQL technique each uses, dashboard link placeholder.
- `docs/LEARNING_NOTES.md` complete: concept per phase (API pagination, surrogate keys, grain, star schema vs flat table, CTE vs subquery, window functions, gaps and islands, interval overlap, data validation) and 10 likely interview questions with honest answers.
- `docs/RESUME.md`: 4 bullets with real numbers from results.
- `docs/SCHEDULE.md`: run `python run_all.py` daily with Windows Task Scheduler to build snapshot history.
- Ask me before creating the public GitHub repo `str-revenue-analytics` with `gh`, then push. Walk me through Streamlit Community Cloud deployment (I sign in myself).
- **Done when:** `pytest -q` passes, `python run_all.py --offline` runs clean from a fresh clone, and the repo is pushed.
