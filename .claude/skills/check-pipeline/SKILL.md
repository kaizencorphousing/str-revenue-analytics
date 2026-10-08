---
name: check-pipeline
description: Rebuild the project offline and run all tests to confirm everything still works end to end. Use after any change to src/, sql/ or app/.
---
1. Run `python run_all.py --offline` and report row counts and any data quality log entries.
2. Run `pytest -q` and report pass/fail with the failing test names.
3. Compare `results/01_headline_kpis.csv` with what the dashboard KPI tiles compute; they must match.
4. Report only what ran and what it returned. If something fails, show the error and the likely root cause before changing anything.
