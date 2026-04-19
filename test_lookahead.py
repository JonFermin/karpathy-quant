"""
Regression test: the T+1 shift inside `run_backtest` must neutralize the
oracle-foresight strategy `weights[t] = sign(return[t])`.

Rationale: `strategy.py` is allowed to compute day t's weights using data
through day t (including `prices.pct_change()` at day t). If `run_backtest`
did NOT shift, that "legal" strategy would score an infinite Sharpe by
multiplying sign(r_t) * r_t each day. With the mandated `.shift(1)`, the
effective weight on day t is sign(r_{t-1}), so strat_return on day t is
sign(r_{t-1}) * r_t — lag-1 return autocorrelation, which for daily US
equities is statistically near zero.

If this test ever fails with a high Sharpe, someone has weakened the shift
(or added a bypass). The harness's single hardest honesty guarantee has
been violated — investigate before trusting any subsequent result.

Run: `uv run test_lookahead.py`
"""

from __future__ import annotations

import sys

import numpy as np
import pandas as pd

from prepare import load_prices, run_backtest

# Upper bound on |Sharpe|. sign(r_{t-1}) * r_t on SP100 daily returns is
# a weak mean-reversion signal; empirically |Sharpe| stays well below 2.
# An actual look-ahead leak produces Sharpes in the 10–100+ range, so 2.5
# easily separates the two regimes while absorbing universe/period drift.
ORACLE_SHARPE_MAX = 2.5


def _oracle_weights(prices: pd.DataFrame) -> pd.DataFrame:
    """Weights that the T+1 shift is supposed to neutralize.

    Builds sign(pct_change) at each date, equal-weighted so row L1 = 1.
    """
    rets = prices.pct_change()
    w = np.sign(rets).fillna(0.0)
    gross = w.abs().sum(axis=1).replace(0, 1.0)
    return w.div(gross, axis=0)


def main() -> int:
    prices = load_prices()
    weights = _oracle_weights(prices)
    results = run_backtest(weights, prices)

    sh = results["oos_sharpe"]
    print(f"oracle strategy oos_sharpe (post-shift): {sh:.4f}")
    print(f"allowed |Sharpe| upper bound:            {ORACLE_SHARPE_MAX:.4f}")

    if not np.isfinite(sh):
        print("FAIL: oos_sharpe is not finite")
        return 1
    if abs(sh) > ORACLE_SHARPE_MAX:
        print("FAIL: oracle look-ahead not neutralized — the T+1 shift is broken")
        return 1

    print("PASS: T+1 shift correctly neutralizes the oracle")
    return 0


if __name__ == "__main__":
    sys.exit(main())
