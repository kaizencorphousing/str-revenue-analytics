# Progress

Updated at the end of every phase. A fresh session reads this to know where we are.

| Phase | Status | Commit | Notes |
|---|---|---|---|
| 0 Scaffold | done | first commit | venv, pinned requirements, git init; ignore check + pip install verified |
| 1 Extract | done | Phase 1 commit | 15 reservations (9 accepted, 1 cancelled, 2 denied, 3 expired), 266 calendar days; 6 offline tests pass |
| 2 Transform + load | done | Phase 2 commit | 15 reservations, 66 booked nights, 266 calendar rows; 6/6 reconciliation checks pass; 15 tests pass |
| 3 Analysis SQL | done | Phase 3 commit | 13 queries run; results/RESULTS.md + 13 CSVs; all 16 SPEC reference numbers match exactly |
| 4 Dashboard | done | Phase 4 commit | Streamlit app runs with 0 exceptions; KPI tiles = query 01 exactly (36.7% / $284.14 / $63.21 / $8,786.61); TABLEAU_GUIDE.md written |
| 5 Pipeline, tests, docs, repo | built; repo push pending approval | Phase 5 commit | run_all.py --offline clean; 44 tests pass; README, RESUME, SCHEDULE, LEARNING_NOTES complete |

## Decisions made
(add as we go: what was decided, why, and who decided)
- 2026-10-08: Project moved out of OneDrive to `C:\Users\patna\projects\str-revenue-analytics`, because OneDrive sync locks or corrupts `.venv`, `.git` and SQLite files. Decided by owner. The old copy under `OneDrive\Desktop\str-revenue-analytics-kit` is stale; don't edit it.
- 2026-10-08: Pinned the latest releases as of today: requests 2.34.2, python-dotenv 1.2.4, pandas 3.0.6, streamlit 1.65.0, plotly 7.1.0, pytest 9.1.1 (Python 3.11.9). Only direct dependencies are pinned; transitive ones float.
- 2026-10-08: The repo-local git identity uses the GitHub no-reply email, so the personal address isn't published in commit history.
- 2026-10-08: Added `.gitattributes` (`* text=auto eol=lf`) so line endings stay consistent between Windows and Streamlit Cloud (Linux).

- 2026-10-08: Phase 1 API findings (verified live): base `https://public.api.hospitable.com/v2`, Bearer PAT, pagination via `page` + `meta.last_page`. No rate-limit headers were seen, so backoff honours `Retry-After` and otherwise waits 1, 2, 4... seconds.
- 2026-10-08: Reservations are fetched with **no status filter**. The API returns every status by default, and its `status[]` filter only accepts `not_accepted, request, accepted, cancelled, checkpoint` (not the spec's "declined"/"expired"). The API calls declined bookings `denied`. Phase 2 should map `denied` to declined and use the top-level `status` field (there's also a nested `reservation_status`).
- 2026-10-08: `date_query=checkin` is pinned so the date window is unambiguously on check-in. `include=financials,properties` is used, and the extractor exits if any reservation isn't tied only to GAINESVILLE (`3841e818-afdd-4e3f-8d6c-754c4ba81cd6`).
- 2026-10-08: One calendar call covers the full range (266 days); 365-day chunking is kept as a fallback.
- 2026-10-08: The PII hook command now uses `git rev-parse --show-toplevel` instead of `$CLAUDE_PROJECT_DIR`, which still pointed at the old OneDrive path after the move and blocked every Bash call.
- 2026-10-08: Phase 2 modelling choices: discounts and fees are stored as **positive** dollars. `platform_fee` = channel fee only (Airbnb host service fee, Vrbo commission); Hospitable's own fee is in `pms_fee`, and pass-through lodging tax is in `host_taxes` (excluded from `net_rev_ex_cleaning`). Today, pms_fee and taxes only appear on unconverted Vrbo requests, so revenue is unaffected.
- 2026-10-08: The transform refuses to build if any reservation's API revenue can't be rebuilt from its parts to the cent, or if checkout - checkin != nights.
- 2026-10-08: `night_status` = booked / vacant_past (before the latest snapshot date, unsold) / open_for_sale / blocked / not_in_snapshot. If two calendar pulls happen on the same day, the later one wins (logged).
- 2026-10-08: Sanity check against the SPEC Phase 3 reference, Aug 15-Dec 31: 139 nights, 51 booked, 36.7%, ADR $284.14, net ex cleaning $8,786.61. **Exact match.** Note: net revenue rounds per night in `fact_nightly`; the unrounded sum is $8,786.67.
- 2026-10-08: Phase 3 query conventions: windows default to Aug 15-Dec 31 2026 where the spec says so; Q02/Q12 cover the whole spine (Aug 2026-Jun 2027), so forward months mostly show unsold future nights. Rent is the full $2,350 even for partial August. Conversion = accepted / all records (cancelled stays in the denominator). The 15.5% Airbnb fee in Q12 is hardcoded per spec.
- 2026-10-08: Postgres differences are noted in each query header (NUMERIC money, ROUND casts, SUM(boolean) -> COUNT FILTER, julianday -> date subtraction, CEIL).
- 2026-10-08: **Headline findings (Oct 8 data):** Sun-Thu occupancy 31.0% vs Fri/Sat 51.3%; the Sun-Thu booked ADR is only $135.74. Oct occupancy 19.4%, Nov 6.7%. Away-game weekends are priced 36.8% *below* ordinary weekends. Vrbo converted 1 of 6 requests; all 5 losses were for nights already sold on Airbnb (calendar sync / availability problem, not price). Discounts gave away 22.5% of gross rent. The 31-night stay earns $102/night contribution vs $597 for 1-2 night stays. The biggest unsold run is Nov 8-Dec 22 (45 nights, $7,885 at current ask). Oct is 2 nights short of covering rent; Nov needs 8, Dec 12.
- 2026-10-08: The dashboard reads only `data/processed/*.csv`, written by `src/export.py` (anonymized: surrogate ids only, calendar notes not exported). Findings are computed from the data at render time; finding 3 picks the night with the largest list-price swing.
- 2026-10-08: Colour: blue `#2a78d6` means *booked* only; covered-rent and weekend bars use dark grey. The Streamlit theme is in `.streamlit/config.toml`.
- 2026-10-08: The date filter (default Aug 15-Dec 31 2026) drives the KPIs, calendar, monthly and weekday charts. Findings stay fixed to the default window.
- 2026-10-08: Tests run the real transform + load on a synthetic fixture (tests/conftest.py), so pytest passes on a fresh clone without private data. run_all.py --offline needs data/raw/ (gitignored): on a fresh clone it works once raw snapshots are copied in or re-pulled. The dashboard works straight from the committed data/processed/.

## Open issues
- The monthly chart compares partial August (17 nights) with full rent; the caption says so.
- The public GitHub repo isn't created yet (needs owner approval), and Streamlit Cloud isn't deployed. Add the dashboard link to README.md and docs/RESUME.md after deploying.
