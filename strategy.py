"""
strategy.py — losers mean-reversion baseline.

Spec:
  - Each week (Friday close), rank each name by trailing 1w/1m/3m/6m total return.
    Worst (most negative) return = rank 1. Average the four ranks.
  - Long the 14 names with the lowest average rank (the biggest recent losers).
  - Inverse 21d realized-vol weights, normalized so sum(w) = 0.35.
  - Hold to next Friday close (T+1 shift applied by run_backtest).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from prepare import (
    TimeBudget,
    load_prices,
    print_summary,
    run_backtest,
)

LOOKBACKS = (5, 21, 63, 126)
N_LONGS = 14
GROSS_LEVERAGE = 0.35
VOL_WINDOW = 21


def generate_weights(prices: pd.DataFrame) -> pd.DataFrame:
    """
    Contract:
      - Use data up to and including day t to decide target weights for day t.
      - Do NOT apply any shift here. run_backtest shifts by one bar to enforce
        T+1 execution; pre-shifting would double-delay the signal.
      - Row sums represent gross leverage.
    """
    # Average cross-sectional rank of trailing returns over four lookbacks.
    # Ascending rank means the biggest losers receive the lowest ranks.
    rank_frames = []
    for n in LOOKBACKS:
        ret_n = prices.pct_change(n)
        rank_frames.append(ret_n.rank(axis=1, method="average", ascending=True))
    avg_rank = sum(rank_frames) / len(rank_frames)

    # Long the N_LONGS biggest losers (lowest average rank).
    long_rank = avg_rank.rank(axis=1, method="first", ascending=True)
    mask = (long_rank <= N_LONGS).astype(float)

    # Inverse realized-vol sizing within the basket.
    vol = prices.pct_change().rolling(VOL_WINDOW).std()
    inv_vol = (1.0 / vol).replace([np.inf, -np.inf], 0.0).fillna(0.0)
    w = mask * inv_vol

    # Normalize each row to gross leverage GROSS_LEVERAGE.
    row_sum = w.sum(axis=1).replace(0, 1)
    w = w.div(row_sum, axis=0) * GROSS_LEVERAGE

    # Weekly rebalance (Friday close); hold ~5 trading days.
    w = w.resample("W-FRI").last().reindex(prices.index, method="ffill").fillna(0.0)
    return w


if __name__ == "__main__":
    prices = load_prices()
    with TimeBudget() as tb:
        weights = generate_weights(prices)
        results = run_backtest(weights, prices)
    print_summary(results)
