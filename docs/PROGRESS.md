# Progress

Updated at the end of every phase. A fresh session reads this to know where we are.

| Phase | Status | Commit | Notes |
|---|---|---|---|
| 0 Scaffold | done | first commit | venv, pinned requirements, git init; ignore check + pip install verified |
| 1 Extract | done | Phase 1 commit | 15 reservations (9 accepted, 1 cancelled, 2 denied, 3 expired), 266 calendar days; 6 offline tests pass |
| 2 Transform + load | not started | | |
| 3 Analysis SQL | not started | | |
| 4 Dashboard | not started | | |
| 5 Pipeline, tests, docs, repo | not started | | |

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

## Open issues
- The Phase 2 transform must map `denied` -> declined and pick `status` as the canonical field.
