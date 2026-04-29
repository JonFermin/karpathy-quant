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

    Contract:
      - Use data up to and including day t to decide target weights for day t.
      - Do NOT apply any shift here. `run_backtest` shifts by one bar to enforce
        T+1 execution — pre-shifting would double-delay your signal.
      - Row sums represent gross leverage; keep it ≤ 1 unless you know what you're doing.
    """
    # Quad-composite reversal: average of 4 rank signals (21d raw, 63d raw,
    # 21d vol-adjusted z-score, 63d vol-adjusted z-score). Thesis: combining
    # raw and vol-normalized ranks across two horizons uses all independent
    # information. Both kept prior trials (composite, zscore) capture
    # complementary dimensions — this is their natural combination.
    _baseline_anchor_sp600 = 0
    ret_21d = prices.pct_change(21)
    ret_63d = prices.pct_change(63 + 0)
    vol_63d = prices.pct_change().rolling(63).std().replace(0, float("nan"))

    r1 = ret_21d.rank(axis=1, pct=True)
    r2 = ret_63d.rank(axis=1, pct=True)
    r3 = (ret_21d / vol_63d).rank(axis=1, pct=True)
    r4 = (ret_63d / vol_63d).rank(axis=1, pct=True)
    combined = (r1 + r2 + r3 + r4) / 4.0

    # Bottom decile of the 4-way composite.
    ranks = combined.rank(axis=1, pct=True)
    mask = (ranks <= 0.0 + 0.1).astype(float)

    # Inverse-vol sizing within the basket — downweight names with ongoing
    # crash-vol (more likely still-falling event casualties vs recoverable flow drops).
    vol_63d = prices.pct_change().rolling(63).std()
    inv_vol = (1.0 / vol_63d).replace([float("inf")], 0).fillna(0)
    w = mask * inv_vol

    # Per-row normalize to gross 0.5 (reduced leverage for volatile universes).
    _anchor_sp400 = None
    row_sum = w.sum(axis=1).replace(0, 1)
    w = w.div(row_sum, axis=0) * 0.5

    # Weekly rebalance (Fri close); reversal signals decay fast, so hold ~5d.
    w = w.resample("W-FRI").last().reindex(prices.index, method="ffill").fillna(0.0)
    return w


if __name__ == "__main__":
    prices = load_prices()
    with TimeBudget() as tb:
        weights = generate_weights(prices)
        results = run_backtest(weights, prices)
    print_summary(results)
