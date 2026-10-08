"""PreToolUse hook: blocks `git commit` if staged files contain secrets or guest PII.

Claude Code runs this before any Bash call matching `git commit *` (see .claude/settings.json).
Exit 2 blocks the commit and shows the reason to Claude; exit 0 lets it through.
"""
import json
import re
import subprocess
import sys

BLOCKED_PATHS = (".env", "data/raw/")
PATTERNS = {
    "email address": re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),
    "phone number": re.compile(r"(?<!\d)\(?\d{3}\)?[-.\s]\d{3}[-.\s]\d{4}(?!\d)"),
    "Airbnb confirmation code": re.compile(r"\bHM[A-Z0-9]{8}\b"),
    "Vrbo confirmation code": re.compile(r"\b(?:HA-[A-Z0-9]{6}|VRBO-[A-Z0-9]{6})\b"),
    "API token": re.compile(r"HOSPITABLE_TOKEN[ \t]*=[ \t]*[A-Za-z0-9._|-]{16,}"),
}
ALLOWED = {"noreply@anthropic.com"}
SKIP_FILES = {".claude/hooks/pii_guard.py"}


def main() -> int:
    try:
        json.load(sys.stdin)  # hook input; not needed beyond confirming the call
    except Exception:
        pass
    staged = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"],
        capture_output=True, text=True,
    ).stdout.split()

    problems = []
    for path in staged:
        norm = path.replace("\\", "/")
        if norm in SKIP_FILES:
            continue
        if norm == ".env" or norm.startswith(".env.") and norm != ".env.example" or norm.startswith("data/raw/"):
            problems.append(f"{path}: this file must never be committed")
            continue
        content = subprocess.run(["git", "show", f":{path}"], capture_output=True, text=True,
                                 errors="ignore").stdout
        for label, rx in PATTERNS.items():
            for m in rx.finditer(content):
                if m.group(0) in ALLOWED:
                    continue
                line = content.count("\n", 0, m.start()) + 1
                problems.append(f"{path}:{line}: possible {label}")
                break

    if problems:
        print("Commit blocked by PII guard:\n" + "\n".join(problems[:20]) +
              "\nRemove or anonymize these, unstage the file, then commit again.", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
