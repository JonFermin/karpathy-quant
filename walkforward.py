"""
walkforward.py — per-fold Sharpe sanity check for a strategy.

The default IS/OOS split is a single boundary at 2019-12-31. A strategy
with a real edge should clear (or at least not collapse) in other
non-overlapping 2-year OOS windows too. This CLI computes fold-level
Sharpes on the *currently-checked-out* `strategy.py` and prints a table.

Meant to be run in the morning review on commits marked `keep`:

    git checkout <kept-commit>
    uv run walkforward.py
    git checkout -                           # back to where you were

The harness keeps `generate_weights` the same across folds — this is a
stability check on the weight panel's OOS behavior under different
evaluation windows, not a re-fit. For strategies that genuinely train
parameters, this will under-report their true walk-forward performance;
for lookback/momentum-style strategies it is an honest robustness probe.
"""

from __future__ import annotations

import math
import sys

import numpy as np
import pandas as pd

from prepare import (
    RISK_FREE_ANNUAL,
    TRADING_DAYS_PER_YEAR,
    load_prices,
    strat_returns,
)
from strategy import generate_weights

# Five non-overlapping 2-year OOS windows spanning 2014–2023. 2024 is
# left out so the sole headline-OOS year is not double-counted in the
# kept row's morning review. 2010–2013 seeds the strategy's lookback.
FOLDS: list[tuple[str, str, str]] = [
    ("fold_2014_2015", "2014-01-01", "2015-12-31"),
    ("fold_2016_2017", "2016-01-01", "2017-12-31"),
    ("fold_2018_2019", "2018-01-01", "2019-12-31"),
    ("fold_2020_2021", "2020-01-01", "2021-12-31"),
    ("fold_2022_2023", "2022-01-01", "2023-12-31"),
]


def _sharpe(r: pd.Series) -> float:
    r = r.dropna()
    if len(r) < 2:
        return float("nan")
    daily_rf = RISK_FREE_ANNUAL / TRADING_DAYS_PER_YEAR
    excess = r - daily_rf
    sigma = excess.std(ddof=1)
    if sigma == 0 or not np.isfinite(sigma):
        return float("nan")
    return float(excess.mean() / sigma * math.sqrt(TRADING_DAYS_PER_YEAR))


def walkforward(weights: pd.DataFrame, prices: pd.DataFrame) -> pd.DataFrame:
    """Return a (folds × [sharpe, days]) DataFrame of per-fold metrics."""
    daily = strat_returns(weights, prices)
    rows = []
    for name, start, end in FOLDS:
        fold_ret = daily.loc[start:end]
        rows.append({
            "fold": name,
            "start": start,
            "end": end,
            "days": int(len(fold_ret)),
            "sharpe": _sharpe(fold_ret),
        })
    return pd.DataFrame(rows).set_index("fold")


def main() -> int:
    prices = load_prices()
    weights = generate_weights(prices)
    df = walkforward(weights, prices)
    print(df.to_string(float_format=lambda x: f"{x: .4f}"))
    # Summary stats across folds — median Sharpe is the robust number.
    finite = df["sharpe"].dropna()
    if len(finite):
        print(f"\nmedian_fold_sharpe: {finite.median():.4f}")
        print(f"min_fold_sharpe:    {finite.min():.4f}")
        print(f"max_fold_sharpe:    {finite.max():.4f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
