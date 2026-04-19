"""
One-time data preparation + fixed backtest harness for karpathy-quant-auto-research.

Usage:
    python prepare.py                  # download + cache prices for the universe
    python prepare.py --refresh        # force re-download even if cache exists

Cached data lives in ~/.cache/karpathy-quant-auto-research/.

This module is READ-ONLY from the agent's perspective. It defines:
  - Fixed experiment constants (dates, costs, hard constraints)
  - Data loaders (prices, universe)
  - `run_backtest`: enforces T+1 shift, applies costs, computes metrics
  - `print_summary`: fixed stdout output contract
  - `TimeBudget`: wall-clock safety cap

The agent edits `strategy.py` only.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import signal
import sys
import time
from dataclasses import dataclass, asdict
from pathlib import Path

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Fixed constants (do not modify — the immutable contract)
# ---------------------------------------------------------------------------

TIME_BUDGET_S = 300              # wall-clock cap for a single backtest
START_DATE = "2010-01-01"
TRAIN_END_DATE = "2019-12-31"    # in-sample boundary (inclusive)
VAL_START_DATE = "2020-01-01"    # out-of-sample start
VAL_END_DATE = "2024-12-31"

UNIVERSE_TAG = "sp100_2024"
BARS = "1d"

COST_BPS = 5.0                   # per-side transaction cost, applied to |Δw|
BORROW_BPS_ANNUAL = 200.0        # borrow cost on short exposure, pro-rated daily
RISK_FREE_ANNUAL = 0.03

MIN_TRADES = 50                  # fewer than this → crash status
MAX_DRAWDOWN_HARD = 0.35         # exceeded → force_discard
MAX_ANNUAL_TURNOVER = 50.0       # exceeded → force_discard

TRADING_DAYS_PER_YEAR = 252

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parent
CACHE_DIR = Path.home() / ".cache" / "karpathy-quant-auto-research"
PRICES_PARQUET = CACHE_DIR / "prices.parquet"
UNIVERSE_JSON = REPO_ROOT / f"universe_{UNIVERSE_TAG}.json"

# ---------------------------------------------------------------------------
# Universe
# ---------------------------------------------------------------------------

def load_universe() -> list[str]:
    """Return the frozen ticker list for UNIVERSE_TAG."""
    with open(UNIVERSE_JSON) as f:
        data = json.load(f)
    return list(data["tickers"])

# ---------------------------------------------------------------------------
# Price download + cache
# ---------------------------------------------------------------------------

def _download_prices(tickers: list[str]) -> pd.DataFrame:
    """Download adjusted closes via yfinance. Returns date × ticker DataFrame."""
    import yfinance as yf  # imported lazily — not needed once cache exists

    print(f"Downloading {len(tickers)} tickers from {START_DATE} to {VAL_END_DATE}...")
    raw = yf.download(
        tickers=tickers,
        start=START_DATE,
        end=VAL_END_DATE,
        interval=BARS,
        auto_adjust=True,
        progress=False,
        threads=True,
        group_by="ticker",
    )

    # yfinance returns a MultiIndex column frame. Extract 'Close' per ticker.
    closes = {}
    if isinstance(raw.columns, pd.MultiIndex):
        for t in tickers:
            if (t, "Close") in raw.columns:
                closes[t] = raw[(t, "Close")]
    else:
        # Single-ticker case
        closes[tickers[0]] = raw["Close"]

    prices = pd.DataFrame(closes)
    prices.index = pd.to_datetime(prices.index).tz_localize(None)
    prices = prices.sort_index()
    # Drop tickers with no data at all
    prices = prices.dropna(axis=1, how="all")
    return prices


def load_prices(refresh: bool = False) -> pd.DataFrame:
    """
    Load adjusted close prices (date × ticker) for the universe.

    First call (or refresh=True) downloads from yfinance and writes parquet cache.
    Subsequent calls read the cache.
    """
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    if PRICES_PARQUET.exists() and not refresh:
        prices = pd.read_parquet(PRICES_PARQUET)
        prices.index = pd.to_datetime(prices.index)
        return prices

    tickers = load_universe()
    prices = _download_prices(tickers)
    prices.to_parquet(PRICES_PARQUET)
    print(f"Cached {prices.shape[0]} rows × {prices.shape[1]} tickers to {PRICES_PARQUET}")
    return prices

# ---------------------------------------------------------------------------
# Date slicing helpers
# ---------------------------------------------------------------------------

def train_slice(df: pd.DataFrame) -> pd.DataFrame:
    """In-sample slice: START_DATE through TRAIN_END_DATE inclusive."""
    return df.loc[START_DATE:TRAIN_END_DATE]


def val_slice(df: pd.DataFrame) -> pd.DataFrame:
    """Out-of-sample slice: VAL_START_DATE through VAL_END_DATE inclusive."""
    return df.loc[VAL_START_DATE:VAL_END_DATE]

# ---------------------------------------------------------------------------
# Time budget
# ---------------------------------------------------------------------------

class TimeBudget:
    """Context manager that raises TimeoutError if wall time exceeds TIME_BUDGET_S.

    Uses a lightweight check on __exit__ rather than signals (signals are
    platform-flaky on Windows and inside notebook kernels). Most backtests
    finish in seconds; the budget is a safety rail against runaway code.
    """

    def __init__(self, seconds: float = TIME_BUDGET_S):
        self.seconds = float(seconds)
        self.t_start: float | None = None
        self.t_end: float | None = None

    def __enter__(self):
        self.t_start = time.time()
        return self

    def __exit__(self, exc_type, exc, tb):
        self.t_end = time.time()
        elapsed = self.t_end - self.t_start
        if elapsed > self.seconds and exc_type is None:
            raise TimeoutError(
                f"Backtest wall time {elapsed:.1f}s exceeded TIME_BUDGET_S={self.seconds:.0f}s"
            )
        return False

    @property
    def elapsed(self) -> float:
        t_end = self.t_end if self.t_end is not None else time.time()
        if self.t_start is None:
            return 0.0
        return t_end - self.t_start

# ---------------------------------------------------------------------------
# Backtest engine
# ---------------------------------------------------------------------------

def _align_weights(weights: pd.DataFrame, prices: pd.DataFrame) -> pd.DataFrame:
    """Align weights to price index/columns. Missing entries fill to 0."""
    w = weights.reindex(index=prices.index, columns=prices.columns)
    w = w.ffill().fillna(0.0)
    return w


def _sharpe(daily_returns: pd.Series) -> float:
    """Annualized Sharpe on daily returns (excess over daily RF)."""
    r = daily_returns.dropna()
    if len(r) < 2:
        return float("nan")
    daily_rf = RISK_FREE_ANNUAL / TRADING_DAYS_PER_YEAR
    excess = r - daily_rf
    sigma = excess.std(ddof=1)
    if sigma == 0 or not np.isfinite(sigma):
        return float("nan")
    return float(excess.mean() / sigma * math.sqrt(TRADING_DAYS_PER_YEAR))


def _max_drawdown(equity: pd.Series) -> float:
    """Maximum drawdown as a positive fraction (0.2 = 20%)."""
    eq = equity.dropna()
    if len(eq) < 2:
        return float("nan")
    peak = eq.cummax()
    dd = (peak - eq) / peak
    return float(dd.max())


def _annualize_return(daily_returns: pd.Series) -> float:
    r = daily_returns.dropna()
    if len(r) == 0:
        return float("nan")
    total = float((1.0 + r).prod())
    years = len(r) / TRADING_DAYS_PER_YEAR
    if years <= 0 or total <= 0:
        return float("nan")
    return total ** (1.0 / years) - 1.0


def _annualize_vol(daily_returns: pd.Series) -> float:
    r = daily_returns.dropna()
    if len(r) < 2:
        return float("nan")
    return float(r.std(ddof=1) * math.sqrt(TRADING_DAYS_PER_YEAR))


def run_backtest(weights: pd.DataFrame, prices: pd.DataFrame) -> dict:
    """
    Run the fixed backtest on a weight panel.

    CRITICAL: this function applies `weights.shift(1)` internally. The agent's
    `generate_weights` may compute weights using data up to and including day t;
    those weights only take effect at the *close of day t+1*. This prevents
    look-ahead and is non-negotiable — do not pre-shift in the strategy.

    Parameters
    ----------
    weights : (date × ticker) target portfolio weights. Row sums are the gross
              leverage for that day. Negative entries are shorts.
    prices  : (date × ticker) adjusted close prices (full history from load_prices).

    Returns
    -------
    dict with keys used by `print_summary`:
      oos_sharpe, is_sharpe, max_drawdown, annual_return, annual_vol,
      turnover_annual, calmar, num_trades, backtest_seconds, status_hint.
    """
    t_start = time.time()

    # Align + clean
    w_raw = _align_weights(weights, prices)
    # T+1 shift: today's close executes yesterday's target weights
    w_eff = w_raw.shift(1).fillna(0.0)

    # Daily simple returns from adjusted closes
    rets = prices.pct_change().fillna(0.0)

    # Sanity: detect NaN/inf anywhere in weights that survived alignment
    if not np.isfinite(w_eff.values).all():
        return _crash_result(t_start, reason="non-finite weights")

    # Per-name pnl = effective weight * asset return
    pnl_per_name = w_eff * rets

    # Transaction cost: bps * |Δw| (summed across names), applied daily
    dw = w_eff.diff().abs().fillna(0.0)
    turnover_daily = dw.sum(axis=1)  # sum of |Δw_i| per day
    tc = turnover_daily * (COST_BPS / 10_000.0)

    # Borrow cost on shorts: (sum of negative weights, as a positive number) * daily borrow rate
    short_exposure = (-w_eff.clip(upper=0.0)).sum(axis=1)
    daily_borrow_rate = (BORROW_BPS_ANNUAL / 10_000.0) / TRADING_DAYS_PER_YEAR
    borrow = short_exposure * daily_borrow_rate

    strat_daily = pnl_per_name.sum(axis=1) - tc - borrow
    equity = (1.0 + strat_daily).cumprod()

    # Slice into IS / OOS
    is_ret = train_slice(strat_daily)
    oos_ret = val_slice(strat_daily)
    oos_eq = val_slice(equity)

    # Metrics (OOS is the headline)
    oos_sharpe = _sharpe(oos_ret)
    is_sharpe = _sharpe(is_ret)
    annual_return = _annualize_return(oos_ret)
    annual_vol = _annualize_vol(oos_ret)
    max_dd = _max_drawdown(oos_eq)
    calmar = (annual_return / max_dd) if (max_dd and np.isfinite(max_dd) and max_dd > 0) else float("nan")

    # Turnover (annualized, OOS): avg daily one-sided turnover × 252
    oos_turnover_daily = val_slice(turnover_daily)
    turnover_annual = float(oos_turnover_daily.mean() * TRADING_DAYS_PER_YEAR) if len(oos_turnover_daily) else float("nan")

    # Trade count: count days with any weight change (per name, summed)
    oos_dw = val_slice(dw)
    num_trades = int((oos_dw > 1e-9).sum().sum())

    backtest_seconds = time.time() - t_start

    # Status hint: crash if any headline metric is non-finite, else hard-constraint check
    headline = [oos_sharpe, is_sharpe, max_dd, annual_return, annual_vol, turnover_annual]
    if any(not np.isfinite(x) for x in headline):
        status_hint = "crash"
    elif num_trades < MIN_TRADES:
        status_hint = "crash"
    elif max_dd > MAX_DRAWDOWN_HARD:
        status_hint = "force_discard"
    elif turnover_annual > MAX_ANNUAL_TURNOVER:
        status_hint = "force_discard"
    else:
        status_hint = "keep_eligible"

    return {
        "oos_sharpe": float(oos_sharpe),
        "is_sharpe": float(is_sharpe),
        "max_drawdown": float(max_dd),
        "annual_return": float(annual_return),
        "annual_vol": float(annual_vol),
        "turnover_annual": float(turnover_annual),
        "calmar": float(calmar),
        "num_trades": int(num_trades),
        "backtest_seconds": float(backtest_seconds),
        "status_hint": status_hint,
    }


def _crash_result(t_start: float, reason: str) -> dict:
    return {
        "oos_sharpe": float("nan"),
        "is_sharpe": float("nan"),
        "max_drawdown": float("nan"),
        "annual_return": float("nan"),
        "annual_vol": float("nan"),
        "turnover_annual": float("nan"),
        "calmar": float("nan"),
        "num_trades": 0,
        "backtest_seconds": float(time.time() - t_start),
        "status_hint": "crash",
        "crash_reason": reason,
    }

# ---------------------------------------------------------------------------
# Output contract
# ---------------------------------------------------------------------------

def print_summary(results: dict) -> None:
    """Print the fixed summary block. The agent greps this from run.log."""
    print("---")
    print(f"oos_sharpe:       {results['oos_sharpe']:.6f}")
    print(f"is_sharpe:        {results['is_sharpe']:.6f}")
    print(f"max_drawdown:     {results['max_drawdown']:.4f}")
    print(f"annual_return:    {results['annual_return']:.4f}")
    print(f"annual_vol:       {results['annual_vol']:.4f}")
    print(f"turnover_annual:  {results['turnover_annual']:.2f}")
    print(f"calmar:           {results['calmar']:.4f}")
    print(f"num_trades:       {results['num_trades']}")
    print(f"backtest_seconds: {results['backtest_seconds']:.1f}")
    # status_hint is informational only; the agent applies the keep/discard
    # rule from program.md, which may differ from this hint on edge cases.
    print(f"status_hint:      {results['status_hint']}")

# ---------------------------------------------------------------------------
# Main (data prep only)
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Prepare price cache for karpathy-quant-auto-research")
    parser.add_argument("--refresh", action="store_true", help="Force re-download even if cache exists")
    args = parser.parse_args()

    print(f"Cache directory: {CACHE_DIR}")
    print(f"Universe: {UNIVERSE_TAG} ({UNIVERSE_JSON.name})")
    prices = load_prices(refresh=args.refresh)
    print(f"Loaded prices: {prices.shape[0]} rows × {prices.shape[1]} tickers")
    print(f"Date range:    {prices.index.min().date()} → {prices.index.max().date()}")
    print("Done! Ready to experiment.")


if __name__ == "__main__":
    main()
