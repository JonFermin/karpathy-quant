"""Cache-only diagnostic: how often does the deflated_oos_sharpe gate alone
block a keep?

Most historical worktrees have been cleaned up, so per-trial metrics
(max_dd, turnover, fold sharpes, daily returns) are gone. The shared trial
cache still has (commit, branch_tag, oos_sharpe, status) for every trial,
which is enough to audit gate #1 — the deflated Sharpe hurdle:

    keep ⟹ oos_sharpe > baseline + 0.15 + expected_max_sharpe_null(σ_pool, N_pool)

For each non-seed, non-crash trial we ask: would this trial have cleared
the deflated-Sharpe gate alone, against its branch's seed Sharpe and the
sigma/N pooled from all PRIOR cache rows of the same hurdle_version?

That's a lower bound on overall pass rate — the other 7 gates can only
block, never rescue.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))

from stats import expected_max_sharpe_null  # noqa: E402

CACHE_DIR = Path.home() / ".cache" / "karpathy-quant-auto-research"

BASELINE_HURDLE_SHARPE = 0.15
HURDLE_VERSION = "2"


def audit(universe: str):
    cache_path = CACHE_DIR / f"trial_cache_{universe}.tsv"
    if not cache_path.exists():
        return None
    cache = pd.read_csv(
        cache_path, sep="\t",
        dtype={"ast_sha256": str, "branch_tag": str, "commit": str,
               "status": str, "hurdle_version": str, "written_at": str},
    )
    cache["oos_sharpe"] = pd.to_numeric(cache["oos_sharpe"], errors="coerce")
    cache = cache.sort_values("written_at").reset_index(drop=True)

    # Seed = first non-crash trial of each branch (in chronological order).
    seeds = (
        cache[cache["status"] != "crash"]
        .groupby("branch_tag", as_index=False)
        .first()[["branch_tag", "commit", "oos_sharpe"]]
        .rename(columns={"commit": "seed_commit", "oos_sharpe": "seed_sharpe"})
    )
    cache = cache.merge(seeds, on="branch_tag", how="left")

    n_eval = 0
    n_pass_deflated = 0
    n_pass_no_deflation = 0  # would pass without the sr0 term
    sr0_history = []
    margin_history = []  # oos_sharpe - hurdle (negative = fails)
    margin_no_defl = []  # oos_sharpe - (baseline + 0.15) only

    for i, row in cache.iterrows():
        if row["status"] == "crash":
            continue
        if row["commit"] == row["seed_commit"]:
            continue
        if not math.isfinite(row["oos_sharpe"]):
            continue
        # Pool sigma_n / N from prior cache rows of same hurdle_version.
        prior = cache.iloc[:i]
        prior = prior[
            (prior["status"] != "crash")
            & (prior["hurdle_version"].astype(str) == HURDLE_VERSION)
        ]
        prior_pool = prior["oos_sharpe"].dropna().to_numpy()
        prior_pool = prior_pool[np.isfinite(prior_pool)]
        if prior_pool.size >= 2:
            sigma_n = float(prior_pool.std(ddof=1))
            n_pool = max(int(prior_pool.size), 2)
        else:
            sigma_n = 0.0
            n_pool = 2
        sr0 = expected_max_sharpe_null(sigma_n, n_pool) if sigma_n > 0 else 0.0
        if sr0 is None or not math.isfinite(sr0) or sr0 < 0:
            sr0 = 0.0

        base = float(row["seed_sharpe"])
        cur = float(row["oos_sharpe"])
        hurdle = base + BASELINE_HURDLE_SHARPE + sr0
        hurdle_no_defl = base + BASELINE_HURDLE_SHARPE

        n_eval += 1
        sr0_history.append(sr0)
        margin_history.append(cur - hurdle)
        margin_no_defl.append(cur - hurdle_no_defl)
        if cur > hurdle:
            n_pass_deflated += 1
        if cur > hurdle_no_defl:
            n_pass_no_deflation += 1

    return {
        "universe": universe,
        "n_evaluated": n_eval,
        "n_pass_deflated_gate": n_pass_deflated,
        "n_pass_baseline_only": n_pass_no_deflation,
        "median_sr0": float(np.median(sr0_history)) if sr0_history else float("nan"),
        "p90_sr0": float(np.percentile(sr0_history, 90)) if sr0_history else float("nan"),
        "median_margin": float(np.median(margin_history)) if margin_history else float("nan"),
        "median_margin_no_defl": float(np.median(margin_no_defl)) if margin_no_defl else float("nan"),
    }


def main():
    universes = sorted(p.stem.replace("trial_cache_", "")
                       for p in CACHE_DIR.glob("trial_cache_*.tsv"))
    rows = [r for u in universes if (r := audit(u)) is not None]

    print(f"\n=== Deflated-Sharpe gate audit (cache-only) ===\n")
    print(f"{'universe':<14}{'n_eval':>8}{'pass_defl':>11}{'pass_base_only':>16}"
          f"{'median_sr0':>12}{'p90_sr0':>10}{'med_margin':>13}{'med_margin_nodefl':>20}")
    for r in rows:
        n = r["n_evaluated"]
        if n == 0:
            continue
        pd_pct = 100 * r["n_pass_deflated_gate"] / n
        pb_pct = 100 * r["n_pass_baseline_only"] / n
        print(
            f"{r['universe']:<14}{n:>8}"
            f"{r['n_pass_deflated_gate']:>5} ({pd_pct:>3.1f}%)"
            f"{r['n_pass_baseline_only']:>9} ({pb_pct:>4.1f}%)"
            f"{r['median_sr0']:>12.4f}{r['p90_sr0']:>10.4f}"
            f"{r['median_margin']:>13.4f}{r['median_margin_no_defl']:>20.4f}"
        )

    n_total = sum(r["n_evaluated"] for r in rows)
    pd_total = sum(r["n_pass_deflated_gate"] for r in rows)
    pb_total = sum(r["n_pass_baseline_only"] for r in rows)
    print(f"\n{'TOTAL':<14}{n_total:>8}"
          f"{pd_total:>5} ({100*pd_total/n_total:>3.1f}%)"
          f"{pb_total:>9} ({100*pb_total/n_total:>4.1f}%)")
    print(f"\nObserved keeps in cache: {sum((pd.read_csv(CACHE_DIR / f'trial_cache_{u}.tsv', sep=chr(9)).status=='keep').sum() for u in universes)}")
    print("Among these would-pass-deflated trials, the OTHER 7 gates "
          "(JK-Memmel, IS/OOS fold medians, min fold, max_dd, turnover, num_trades) "
          "still need to clear. The gap between 'pass_defl' here and observed keeps "
          "shows how much the other gates filter on top.")


if __name__ == "__main__":
    main()
