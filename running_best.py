"""
running_best.py — report the current best kept oos_sharpe from results.tsv.

Used by the agent inside the experiment loop so the keep rule

    keep iff oos_sharpe > running_best AND constraints met

is evaluated against an unambiguous number instead of a by-eye scan of
the TSV. Prints nothing but a single float; exit code 0 on success, 1
if the file is missing or has no kept rows.

Usage:

    uv run running_best.py                    # print current best
    uv run running_best.py --path results.tsv # explicit path
    uv run running_best.py --verbose          # show which row won

Under the 3.6 honesty contract this is the ONLY sanctioned way for the
agent to learn an OOS number during the loop — and it only reveals the
best-so-far (a lower bound on the keep threshold), not per-run OOS.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

from prepare import OOS_RESULTS_TSV, REPO_ROOT

DEFAULT_PATH = REPO_ROOT / "results.tsv"


def running_best(path: Path | str = DEFAULT_PATH) -> tuple[float, str] | None:
    """Return (best_sharpe, commit) over kept rows, or None if none exist.

    When SHOW_OOS is disabled the agent has been writing 0 for oos_sharpe
    in results.tsv; fall back to the harness-owned oos_results.tsv and
    join on commit so the best number still reflects reality.
    """
    p = Path(path)
    if not p.exists():
        return None
    df = pd.read_csv(p, sep="\t")
    if "status" not in df.columns or "commit" not in df.columns:
        return None
    df["status"] = df["status"].astype(str).str.strip().str.lower()
    if "oos_sharpe" in df.columns:
        df["oos_sharpe"] = pd.to_numeric(df["oos_sharpe"], errors="coerce")

    kept = df[df["status"] == "keep"].copy()
    if kept.empty:
        return None

    use_side_channel = (
        "oos_sharpe" not in df.columns
        or kept["oos_sharpe"].fillna(0).max() == 0.0
    )
    if use_side_channel and OOS_RESULTS_TSV.exists():
        side = pd.read_csv(OOS_RESULTS_TSV, sep="\t")
        side["oos_sharpe"] = pd.to_numeric(side["oos_sharpe"], errors="coerce")
        kept = kept.merge(
            side[["commit", "oos_sharpe"]],
            on="commit",
            how="left",
            suffixes=("_log", ""),
        )
    if "oos_sharpe" not in kept.columns:
        return None
    kept = kept.dropna(subset=["oos_sharpe"])
    if kept.empty:
        return None
    idx = kept["oos_sharpe"].idxmax()
    return float(kept.loc[idx, "oos_sharpe"]), str(kept.loc[idx].get("commit", ""))


def main() -> int:
    parser = argparse.ArgumentParser(description="Print current best kept oos_sharpe")
    parser.add_argument("--path", default=str(DEFAULT_PATH), help="results.tsv path")
    parser.add_argument("--verbose", action="store_true", help="show which row won")
    args = parser.parse_args()

    result = running_best(args.path)
    if result is None:
        print("no kept rows yet", file=sys.stderr)
        return 1
    best, commit = result
    if args.verbose:
        print(f"running_best: {best:.6f}  (commit {commit})")
    else:
        print(f"{best:.6f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
