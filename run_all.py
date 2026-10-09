"""Run the whole pipeline: extract -> transform + load (with checks) -> analysis queries -> export.

Usage:
  python run_all.py            # pull fresh data from the Hospitable API (needs .env)
  python run_all.py --offline  # rebuild from the latest files already in data/raw/
Stops with a non-zero exit code at the first failing step.
"""
import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))
import export  # noqa: E402
import extract  # noqa: E402
import load  # noqa: E402
import run_queries  # noqa: E402


def step(name, fn):
    print(f"\n=== {name} ===")
    t0 = time.perf_counter()
    fn()
    print(f"--- {name} done in {time.perf_counter() - t0:.1f}s")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--offline", action="store_true", help="skip the API and rebuild from data/raw/")
    args = parser.parse_args()

    if args.offline:
        if not list(extract.RAW_DIR.glob("reservations_*.json")):
            sys.exit("--offline needs raw snapshots in data/raw/ (gitignored). "
                     "Run once without --offline, with HOSPITABLE_TOKEN in .env.")
        print("Offline: skipping extract, using the latest files in data/raw/")
    else:
        step("Extract (Hospitable API, read-only)", extract.main)
    step("Transform + load + reconciliation checks", load.main)
    step("Analysis queries", run_queries.main)
    step("Export for dashboard", export.main)
    print("\nPipeline finished. Dashboard: streamlit run app/dashboard.py")


if __name__ == "__main__":
    main()
