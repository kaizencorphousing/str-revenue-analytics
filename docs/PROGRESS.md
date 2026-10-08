# Progress

Updated at the end of every phase. A fresh session reads this to know where we are.

| Phase | Status | Commit | Notes |
|---|---|---|---|
| 0 Scaffold | done | first commit | venv, pinned requirements, git init; ignore check + pip install verified |
| 1 Extract | not started | | |
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

## Open issues
- `.env` isn't created yet. Before Phase 1, the owner must copy `.env.example` to `.env` and paste the Hospitable token in Notepad, not in chat.
