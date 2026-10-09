# Daily snapshot schedule (Windows Task Scheduler)

Every run of `python run_all.py` saves a new, timestamped calendar snapshot to `data/raw/` and never overwrites older ones. Running it once a day builds the history needed to measure **booking pace**: how many future nights were sold N days ahead, and how prices moved.

## One-time setup (about 5 minutes)

1. Make sure `python run_all.py` works by hand from the project folder (it needs `.env` with your token).
2. Open **Task Scheduler** (Start menu, type "Task Scheduler") and choose **Create Basic Task...**
3. **Name:** `STR analytics daily pull`. Click Next.
4. **Trigger:** Daily, start tomorrow at **06:00**, recur every 1 day.
5. **Action:** Start a program.
   - **Program/script:** `C:\Users\patna\projects\str-revenue-analytics\.venv\Scripts\python.exe`
   - **Add arguments:** `run_all.py`
   - **Start in:** `C:\Users\patna\projects\str-revenue-analytics`
6. Tick "Open the Properties dialog" and click Finish. Then in Properties:
   - **General:** choose "Run whether user is logged on or not". Windows asks for your Windows password and keeps it.
   - **Conditions:** on a laptop, untick "Start the task only if the computer is on AC power".
   - **Settings:** tick "Run task as soon as possible after a scheduled start is missed".

## Keep a log (optional)

Create a `logs` folder in the project and add `logs/` to `.gitignore`. Then change the action to:
- **Program/script:** `cmd.exe`
- **Add arguments:** `/c ".venv\Scripts\python.exe run_all.py >> logs\run_all.log 2>&1"`
- **Start in:** the same project folder.

## Check it

- Task Scheduler → Task Scheduler Library → right-click the task → **Run**. Then confirm that a new `data\raw\calendar_<timestamp>.json` appears.
- **Last Run Result** should be `0x0`. Anything else means a step failed. The pipeline stops on any failed reconciliation check, so the dashboard data is never half-updated.

## Publishing updates

The schedule only refreshes your local database, `results/` and `data/processed/`. To update the public dashboard, run `pytest -q` (it scans the exports for PII), then commit and push the changed `data/processed/` and `results/` files. The git pre-commit hook in `.githooks/` scans every commit, provided it was enabled once with `git config core.hooksPath .githooks`.
