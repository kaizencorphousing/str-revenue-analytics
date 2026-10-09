# Learning notes

One section per phase: what was built, why, and the concepts to be able to explain in an interview.

## Phase 0: Scaffold

**Built:** a Python virtual environment (`.venv`), a pinned `requirements.txt`, a `.gitignore` that keeps secrets and raw data out of git, and the first git commit.

**Concept: reproducible environments, and keeping secrets out of version control.**
A virtual environment is a private folder of Python packages for one project, so this project's pandas version can't clash with another project's. Pinning exact versions (`pandas==3.0.6`) means anyone who runs `pip install -r requirements.txt` gets the same code I tested with, so the results can be reproduced. `.gitignore` tells git which files never to track: the `.env` file with the API token, the raw API JSON containing guest details, the local database and the venv itself. The pre-commit hook is the safety net: if something sensitive gets staged by mistake, it blocks the commit before anything reaches GitHub.

**Interview question:** Why pin package versions, and why isn't `.gitignore` alone enough to protect secrets?
(Pinning makes builds reproducible. `.gitignore` only stops *untracked* files: it can be bypassed with `git add -f`, and it does nothing if a secret is pasted into a tracked file. A hook that scans the staged content adds a second layer.)

## Phase 1: Extract

**Built:** `src/extract.py` pulls the GAINESVILLE property, all its reservations (with financials) and its calendar from the Hospitable REST API, then saves raw timestamped JSON snapshots to `data/raw/`. `tests/test_extract.py` covers pagination, 429/5xx backoff, calendar chunking and the property guard, without using the network.

**Concept: the "E" in ETL. Extract raw data faithfully, and make it repeatable and safe.**
Extraction should copy the source as-is into a landing zone, so every later step can be rebuilt offline from those files without calling the API again. Paginated APIs return data in pages, so the code keeps requesting `page=1, 2, ...` until `meta.last_page`. When the server says "too many requests" (HTTP 429), the client waits (using `Retry-After` if given, otherwise 1s, 2s, 4s...) instead of failing; that's called exponential backoff. Each run writes new timestamped files instead of overwriting, which builds a history of calendar snapshots for measuring booking pace later. Finally, I verified the API against the spec instead of trusting it: the real status values and filters differed, so I adapted the code and wrote the reasons down.

**Interview question:** Why save the raw API response before transforming it, instead of transforming in memory and only saving the clean table?
(Saving raw data makes the pipeline reproducible and debuggable: you can re-run transforms offline, fix a transform bug without re-pulling, compare snapshots over time, and prove where every number came from.)

## Phase 2: Transform and load

**Built:** `src/transform.py` turns raw JSON plus seed CSVs into clean tables (cents become dollars here and only here). `sql/schema.sql` defines the SQLite model: `reservations` (one booking request), `reservation_nights` (one booked night), `calendar_snapshot` (one night per pull), seed tables, the `dim_date` spine, a `data_quality_log`, and the `fact_nightly` view. `src/load.py` builds `gainesville.db`, runs 6 reconciliation checks, and exits with an error if any fail.

**Concept: grain, reconciliation and a date spine.**
Every table has a *grain*, meaning what one row represents. Mixing grains (for example joining nightly rows to booking-level fees without dividing) silently double-counts money. A **date spine** (`dim_date`) has one row for every calendar date, so nights with no booking still appear and occupancy can be computed as booked / all nights; an inner join would hide the empty nights. **Reconciliation** means proving the cleaned data still adds up to the source: here, nightly prices must sum to each stay's rent to the cent, revenue must rebuild from its parts, and no night can be sold twice. Every judgement call (summing a duplicated date, spreading Vrbo rent evenly, relabelling "denied") goes into `data_quality_log`, so the cleaning is auditable instead of hidden.

**Interview question:** Why build a date spine and LEFT JOIN bookings onto it, instead of just querying the bookings table for occupancy?
(Bookings only contain sold nights. Without a spine you can't count the unsold nights, so occupancy, gaps and RevPAR all come out wrong. The LEFT JOIN keeps every date and leaves NULLs where nothing was booked.)

## Phase 3: Analysis SQL

**Built:** 13 analysis queries in `sql/analysis/`, each with a header stating its question and assumptions, and `src/run_queries.py`, which writes `results/<name>.csv` and `results/RESULTS.md`, including an automatic comparison against the reference numbers.

**Concept: window functions, and SQL patterns that answer business questions.**
A window function computes across related rows without collapsing them the way GROUP BY does: `ROW_NUMBER()` ranks rows (used for the median, and to flag the latest comp pull), and `LAG()` reads the previous row (used to measure each price change). **Gaps and islands** finds runs of consecutive dates: within a run, `date - ROW_NUMBER()` stays constant, so grouping by it collapses each run into one row. A **self-join with an interval-overlap test** (`a.checkin < b.checkout AND a.checkout > b.checkin`) checks whether two stays share any night. Here it proved that every lost Vrbo request was for nights already sold on Airbnb. **UNION ALL** can unpivot wide columns (five discount types) into rows so they can be ranked and totalled.

**Interview question:** How do you find a median in SQL when the database has no MEDIAN function, and how do you handle an even number of rows?
(Number the rows with `ROW_NUMBER() OVER (ORDER BY x)` and count them with `COUNT(*) OVER ()`, then keep rows where rn is `(n+1)/2` or `(n+2)/2` using integer division and average them. With odd n both expressions point at the same middle row; with even n they pick the two middle rows.)

## Phase 4: Dashboard

**Built:** `src/export.py` writes anonymized CSVs to `data/processed/`. `app/dashboard.py` (Streamlit + Plotly) shows KPI tiles, a night-by-night calendar heatmap, monthly revenue vs rent, weekday vs weekend, price history, price vs market, and a "Where the money leaks" tab, plus a findings panel computed from the data. `docs/TABLEAU_GUIDE.md` explains how to rebuild it in Tableau Public.

**Concept: separate the serving layer from the pipeline, and make every number traceable.**
The dashboard never calls the API or opens the database: it reads small, anonymized CSVs that the pipeline exports. That makes it safe to host publicly and fast to load, and it means one bad API day can't break the live site. The KPI tiles use the same definitions as query 01 and were checked to match it to the cent, so the dashboard can't quietly disagree with the SQL. Findings are computed from the data rather than typed in, so they stay true when the data changes. Design is restrained on purpose: one accent colour means "booked" everywhere, so a viewer learns it once.

**Interview question:** Why does the dashboard read exported CSVs instead of querying the database or the API directly?
(Security: no token or raw guest data on the public host. Reliability: the site doesn't depend on the API being up. Consistency: everyone sees the same snapshot that the analysis used. The trade-off is freshness: data is only as new as the last pipeline run.)

## Phase 5: Pipeline, tests, docs

**Built:** `run_all.py` (extract, then load with checks, then queries, then export; `--offline` skips the API), a 44-test pytest suite that runs the real pipeline on a synthetic fixture, the README case study, a resume page and a daily schedule.

**Concept: tests as proof, and orchestration.**
An orchestrator runs the steps in order and stops at the first failure, so a bad extract can never quietly feed the dashboard. The tests run the *real* transform and load code on a tiny made-up dataset whose answers I worked out by hand (5 booked nights, $160 ADR, $660 net). If the SQL or the cleaning logic changes behaviour, a test fails. Because the fixture is synthetic, the suite runs on a fresh clone without any private guest data, and a separate test scans every exported file for PII patterns.

---

## Concept index

**API pagination.** APIs return big lists in pages. You request `page=1, 2, ...` until the response says you've reached `last_page`. If the server replies 429 "too many requests", you wait and retry (backoff) instead of failing.

**Surrogate keys.** An id we invent (R01, R02...) instead of using the platform's confirmation code. It hides PII, it's short, and it carries no business meaning. The trade-off here is that ids are re-assigned by check-in order on every build.

**Grain.** What one row means: one booking request, one booked night, one date. Joining tables of different grains without care duplicates rows; for example, joining a stay-level fee onto 31 nightly rows counts that fee 31 times. That's why net revenue is divided by `nights` before it is put on each night.

**Star schema vs flat table.** A star schema has a central fact table (here `fact_nightly`, one row per night) surrounded by dimension tables (dates, events, reservations) that describe it. It avoids repeating descriptive data and makes "slice by anything" queries easy. A flat table is simpler to read but repeats data and drifts out of sync. This project keeps normalized tables and exposes a flat *view* for convenience, which gets the benefits of both.

**CTE vs subquery.** A CTE (`WITH name AS (...)`) is a named subquery that you define first and use later. It reads top to bottom like steps and can be referenced more than once. A subquery is nested inline. Most databases run both the same way; CTEs win on readability, which matters when someone else has to check your SQL.

**Window functions.** `ROW_NUMBER()`, `LAG()` and `SUM() OVER (...)` compute across a "window" of related rows without collapsing them the way `GROUP BY` does. `PARTITION BY` splits the rows into groups and `ORDER BY` sets the order inside each group. Used here for the median, the latest-pull flag and price-change deltas.

**Gaps and islands.** To find runs of consecutive dates, subtract each row's `ROW_NUMBER()` from its date. Within a consecutive run that difference is constant, so grouping by it collapses each run into one row with its start, end and length.

**Interval overlap.** Two stays [a.in, a.out) and [b.in, b.out) overlap exactly when `a.in < b.out AND a.out > b.in`. Strict inequalities let a checkout morning and a check-in afternoon share a date. A self-join with this condition showed that every lost request collided with a stay that was already sold.

**Data validation.** Don't trust a pipeline because it ran; prove it. Reconciliation compares the output with the source (nightly prices sum to the stay's rent to the cent), invariants catch impossible states (a double-booked night), and a quality log records every judgement call. Here the build fails loudly rather than producing a wrong dashboard.

---

## 10 likely interview questions, with honest answers

1. **Walk me through the pipeline.**
   Python pulls reservations and calendar data from the Hospitable REST API (GET only, paginated, with backoff) into timestamped raw JSON. A transform step cleans it, converts cents to dollars and assigns surrogate ids. A load step builds a SQLite model and runs reconciliation checks. Thirteen SQL queries answer the business questions, and anonymized CSV exports feed a Streamlit dashboard. `run_all.py` runs the whole thing.

2. **How do you know the numbers are right?**
   Three layers. The build fails if nightly prices don't sum to each stay's rent to the cent, if any night is double booked, or if the calendar disagrees with the bookings. The headline figures matched an independent manual pull exactly (139 nights, 51 booked, $284.14 ADR, $8,786.61 net). And tests check the KPI math against a hand calculation on a synthetic fixture.

3. **What was the hardest data problem?**
   The API didn't match the spec. Its status filter rejected "declined" and "expired", so I pulled every status and mapped `denied` to declined. One stay had duplicate nightly rows from a split rate, and the Vrbo stay had no nightly prices at all. I logged each fix in a data-quality table instead of silently patching it.

4. **Why SQLite and not Postgres?**
   It's one property with 15 bookings, so a file database with zero setup is the right size. The SQL is standard apart from a few functions, and each query notes the Postgres equivalent (date subtraction instead of `julianday`, `COUNT(*) FILTER`, `CEIL`, NUMERIC money).

5. **How did you protect guest privacy?**
   Raw JSON never leaves a gitignored folder. Tables carry surrogate ids, not names or confirmation codes. The dashboard reads only anonymized exports. A pre-commit hook blocks commits containing emails, phone numbers, booking codes or the token, and a test scans every export for those patterns.

6. **What's the main finding?**
   It isn't price level: at the latest comp pull our asks sit between -16% and +7% of the market median. The problems are weeknight demand (31% vs 51% weekend occupancy), Vrbo losing every unconverted request to dates already sold on Airbnb, and 22.5% of rent going to discounts. The biggest recoverable block is 45 unsold nights from Nov 8 to Dec 22.

7. **How did you calculate the median without a MEDIAN function?**
   `ROW_NUMBER()` over lead time plus `COUNT(*) OVER ()`, then keep rows where rn is `(n+1)/2` or `(n+2)/2` using integer division and average them. That handles both odd and even counts. The result is 77 days.

8. **What are the limitations?**
   Nine stays is a tiny sample, so this is descriptive, not statistical. Comps are list prices, not achieved rates. Revenue is spread evenly across a stay's nights. There's only a few days of calendar-snapshot history so far, so booking pace isn't measurable yet; the scheduled daily run fixes that over time.

9. **What would you do with more time or data?**
   Build booking-pace curves from the daily snapshots (how many future nights were sold N days out), add more properties to compare, and test pricing changes properly, for example alternating weeknight minimums and measuring the effect on fill rate.

10. **Why a date spine?**
    The bookings table only contains sold nights. To measure occupancy you need the unsold ones too, so every date gets a row and bookings are LEFT JOINed on. An inner join would drop the empty nights and make occupancy look like 100%.
