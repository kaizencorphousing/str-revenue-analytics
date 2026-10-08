# Learning notes

One section per phase: what was built, why, and the concepts to be able to explain in an interview.

## Phase 0: Scaffold

**Built:** a Python virtual environment (`.venv`), a pinned `requirements.txt`, a `.gitignore` that keeps secrets and raw data out of git, and the first git commit.

**Concept: reproducible environments, and keeping secrets out of version control.**
A virtual environment is a private folder of Python packages for one project, so this project's pandas version can't clash with another project's. Pinning exact versions (`pandas==3.0.6`) means anyone who runs `pip install -r requirements.txt` gets the same code I tested with, so the results can be reproduced. `.gitignore` tells git which files never to track: the `.env` file with the API token, the raw API JSON containing guest details, the local database and the venv itself. The pre-commit hook is the safety net: if something sensitive gets staged by mistake, it blocks the commit before anything reaches GitHub.

**Interview question:** Why pin package versions, and why isn't `.gitignore` alone enough to protect secrets?
(Pinning makes builds reproducible. `.gitignore` only stops *untracked* files: it can be bypassed with `git add -f`, and it does nothing if a secret is pasted into a tracked file. A hook that scans the staged content adds a second layer.)
