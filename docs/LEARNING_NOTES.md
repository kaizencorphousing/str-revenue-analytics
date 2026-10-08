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
