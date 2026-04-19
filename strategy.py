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
    # 6-month return, skipping the most recent month (6-1 momentum)
    mom = prices.pct_change(126).shift(21)

    # Risk-adjust: divide momentum by 126d realized vol of daily returns.
    # Emphasizes smooth winners; noisy high-return names get deflated.
    rets = prices.pct_change()
    vol = rets.rolling(126).std().shift(21)
    score = mom / vol

    # Cross-sectional rank → long the top decile (rank ≥ 0.9), equal-weight.
    ranks = score.rank(axis=1, pct=True)
    w = (ranks >= 0.9).astype(float)

    # Normalize each row to gross leverage 1.0 (or 0 if nothing qualifies yet).
    row_sum = w.sum(axis=1).replace(0, 1)
    w = w.div(row_sum, axis=0)

    # Rebalance monthly: forward-fill the last weight of each month across the month.
    w = w.resample("ME").last().reindex(prices.index, method="ffill").fillna(0.0)

    # Portfolio-level vol targeting with monthly scale lock.
    port_rets = (w.shift(1) * rets).sum(axis=1)
    port_vol = port_rets.rolling(42).std() * (252 ** 0.5)
    scale = (0.12 / port_vol).clip(lower=0.3, upper=2.0).fillna(1.0)
    scale = scale.resample("ME").last().reindex(prices.index, method="ffill").fillna(1.0)
    w = w.mul(scale, axis=0)
    return w


if __name__ == "__main__":
    prices = load_prices()
    with TimeBudget() as tb:
        weights = generate_weights(prices)
        results = run_backtest(weights, prices)
    print_summary(results)
