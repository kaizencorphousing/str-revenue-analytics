# STR Revenue Analytics

Portfolio analytics project: Hospitable API -> SQLite model -> SQL analysis -> Streamlit dashboard, for one short-term rental I operate in Gainesville, FL. Full spec: `docs/SPEC.md`. Progress and handoff notes: `docs/PROGRESS.md`.

## Commands (Windows, PowerShell or Git Bash)
- Setup: `py -m venv .venv` then `.venv\Scripts\activate` then `pip install -r requirements.txt`
- Full pipeline: `python run_all.py` (add `--offline` to rebuild from the latest raw files without calling the API)
- Tests: `pytest -q`
- Dashboard: `streamlit run app/dashboard.py`

## Rules
- IMPORTANT: The Hospitable API is read-only for this project. GET requests only. Never create, update, cancel or message anything.
- IMPORTANT: Never read, print or commit `.env`. Code loads the token with python-dotenv. If I paste a token in chat, tell me to put it in `.env` instead.
- Only the property named `GAINESVILLE` (public name "Lexington Crossing Townhouse"). The account also has client properties; exclude them.
- No guest PII anywhere in tracked files: no guest names, emails, phones, messages, or platform confirmation codes. Raw API JSON lives only in `data/raw/` (gitignored). Reservations get surrogate keys R01, R02... ordered by check-in.
- Money arrives in cents from the API. Convert to dollars once, in `src/transform.py`.
- Seed data the API can't provide is in `data/seed/`. Load it; don't retype it.

## How we work
- One phase per session. I start each with `/next-phase <n>`. Plan first, then build, then prove it works with real output, then update `docs/PROGRESS.md`, commit, and stop.
- I'm learning this for interviews. After each phase, explain the main concept in 3 to 5 plain sentences and add it to `docs/LEARNING_NOTES.md`.
- Don't claim something works unless you ran it and showed the output.
- Be direct. If the spec is wrong or there's a better approach, say so before building.
- When compacting, preserve: current phase, files changed, failing checks, and any decision I made.
