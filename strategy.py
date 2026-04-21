"""
strategy.py — the one file the agent edits.

Define `generate_weights(prices)` that returns a (date × ticker) weight panel.
The __main__ block calls `run_backtest` (which enforces the T+1 shift) and
prints the fixed output block.

Baseline: 12-1 month momentum, monthly rebalance, long top decile equal-weight.
"""

from __future__ import annotations

import pandas as pd

from prepare import (
    TimeBudget,
    load_prices,
    print_summary,
    run_backtest,
)


def generate_weights(prices: pd.DataFrame) -> pd.DataFrame:
    """
    Build a (date × ticker) target-weight panel.

    Contract:
      - Use data up to and including day t to decide target weights for day t.
      - Do NOT apply any shift here. `run_backtest` shifts by one bar to enforce
        T+1 execution — pre-shifting would double-delay your signal.
      - Row sums represent gross leverage; keep it ≤ 1 unless you know what you're doing.
    """
    # 12-1 momentum: 252d return, skip the last 21d to avoid the 1-month reversal.
    mom = prices.pct_change(252).shift(21)

    # Top decile, equal-weighted.
    ranks = mom.rank(axis=1, pct=True)
    w = (ranks >= 1 - 0.1).astype(float)

    # Per-row normalize to gross 1.0 (0 if no names qualify).
    row_sum = w.sum(axis=1).replace(0, 1)
    w = w.div(row_sum, axis=0)

    # Month-end rebalance; hold through the month.
    w = w.resample("ME").last().reindex(prices.index, method="ffill").fillna(0.0)
    return w


if __name__ == "__main__":
    prices = load_prices()
    with TimeBudget() as tb:
        weights = generate_weights(prices)
        results = run_backtest(weights, prices)
    print_summary(results)
