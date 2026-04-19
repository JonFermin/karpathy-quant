"""
log_result.py — append a correctly-typed row to results.tsv.

Avoids hand-written TSV rows (easy to mis-tab, drop a column, or stamp
the wrong commit). Reads run.log to extract oos_sharpe / max_drawdown /
turnover_annual, resolves the current short git hash, and appends.

Usage:

    uv run log_result.py keep    "thesis: momentum with vol filter"
    uv run log_result.py discard "thesis: 6m reversal — did not improve"
    uv run log_result.py crash   "divide-by-zero on flat day"

Status must be one of: keep, discard, crash. Description is required and
MUST start with 'thesis:' for keep/discard rows so `grep '^thesis:' ...`
over descriptions is meaningful during morning review. Crashes are
exempt — the description should just explain what broke.

Writes to results.tsv in the repo root. Creates the header if the file
does not yet exist. `results.tsv` is gitignored.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

from prepare import REPO_ROOT

RESULTS_TSV = REPO_ROOT / "results.tsv"
RUN_LOG = REPO_ROOT / "run.log"

HEADER = ["commit", "oos_sharpe", "max_dd", "turnover", "status", "description"]
ALLOWED_STATUSES = {"keep", "discard", "crash"}


def _short_commit() -> str:
    out = subprocess.check_output(
        ["git", "-C", str(REPO_ROOT), "rev-parse", "--short=7", "HEAD"],
        stderr=subprocess.DEVNULL,
    )
    return out.decode().strip()


def _parse_metric(text: str, key: str) -> str:
    """Return formatted metric value from run.log text; 0 if missing/hidden/NaN."""
    m = re.search(rf"^{re.escape(key)}:\s*(.+)$", text, re.MULTILINE)
    if m is None:
        return "0.0"
    raw = m.group(1).strip()
    if raw.startswith("<") or raw.lower() == "nan":
        return "0.0"
    try:
        return f"{float(raw):.6f}" if key == "oos_sharpe" else f"{float(raw):.4f}"
    except ValueError:
        return "0.0"


def main() -> int:
    parser = argparse.ArgumentParser(description="Append a row to results.tsv")
    parser.add_argument("status", choices=sorted(ALLOWED_STATUSES))
    parser.add_argument("description", help="One-line description (start with 'thesis: ' for keep/discard)")
    parser.add_argument("--log", default=str(RUN_LOG), help="run.log path")
    args = parser.parse_args()

    status = args.status.strip().lower()
    desc = args.description.strip()
    if status in {"keep", "discard"} and not desc.lower().startswith("thesis:"):
        print("ERROR: keep/discard descriptions must start with 'thesis: '", file=sys.stderr)
        return 2
    if "\t" in desc or "\n" in desc:
        print("ERROR: description may not contain tabs or newlines", file=sys.stderr)
        return 2

    if status == "crash":
        oos, max_dd, turnover = "0.000000", "0.0000", "0.00"
    else:
        try:
            log_text = Path(args.log).read_text(encoding="utf-8", errors="replace")
        except FileNotFoundError:
            print(f"ERROR: {args.log} not found", file=sys.stderr)
            return 2
        oos = _parse_metric(log_text, "oos_sharpe")
        max_dd = _parse_metric(log_text, "max_drawdown")
        turnover_raw = re.search(r"^turnover_annual:\s*(.+)$", log_text, re.MULTILINE)
        turnover = "0.00"
        if turnover_raw and not turnover_raw.group(1).strip().startswith("<"):
            try:
                turnover = f"{float(turnover_raw.group(1)):.2f}"
            except ValueError:
                pass

    commit = _short_commit()
    new_file = not RESULTS_TSV.exists()
    row = [commit, oos, max_dd, turnover, status, desc]
    with open(RESULTS_TSV, "a", encoding="utf-8", newline="") as f:
        if new_file:
            f.write("\t".join(HEADER) + "\n")
        f.write("\t".join(row) + "\n")

    print(f"logged: {commit}\t{oos}\t{max_dd}\t{turnover}\t{status}\t{desc}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
