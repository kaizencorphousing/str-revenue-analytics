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
