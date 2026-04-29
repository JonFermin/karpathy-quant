"""
strategy.py — XBI losers-mean-reversion (ad-hoc spec ported into harness).

Spec:
  - Every Friday close, rank each name by trailing 1w/1m/3m/6m total return.
    Worst return = rank 1. Average the four ranks.
  - Long the 14 names with the lowest average rank.
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
    rank_frames = []
    for n in LOOKBACKS:
        ret_n = prices.pct_change(n)
        rank_frames.append(ret_n.rank(axis=1, method="average", ascending=True))
    avg_rank = sum(rank_frames) / len(rank_frames)

    name_rank = avg_rank.rank(axis=1, method="first", ascending=True)
    basket_mask = (name_rank <= N_LONGS).astype(float)

    vol_21d = prices.pct_change().rolling(VOL_WINDOW).std()
    inv_vol = (1.0 / vol_21d).replace([np.inf, -np.inf], np.nan).fillna(0.0)

    w = basket_mask * inv_vol
    row_sum = w.sum(axis=1).replace(0, np.nan)
    w = w.div(row_sum, axis=0).fillna(0.0) * GROSS_LEVERAGE

    w = w.resample("W-FRI").last().reindex(prices.index, method="ffill").fillna(0.0)
    return w


if __name__ == "__main__":
    prices = load_prices()
    with TimeBudget() as tb:
        weights = generate_weights(prices)
        results = run_backtest(weights, prices)
    print_summary(results)
