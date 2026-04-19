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
import subprocess
import time
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

# Weight-panel sanity guards. These catch obviously broken generate_weights
# outputs (all-NaN frame, accidental 10× leverage, frozen constant weights)
# and force a `crash` with a reason rather than producing misleading metrics.
MAX_GROSS_LEVERAGE = 3.0         # single-row gross L1 above this → crash
MAX_WEIGHT_NAN_FRACTION = 0.99   # >99% of cells NaN → crash (empty panel)
MIN_WEIGHT_DISTINCT_ROWS = 2     # panel must have >=2 distinct rows over OOS

# Stationary block bootstrap (OOS Sharpe CI). 200 resamples at block_len=20d
# is enough for a usable band on ~1260 OOS observations and costs <1s.
BOOTSTRAP_RESAMPLES = 200
BOOTSTRAP_BLOCK_DAYS = 20
BOOTSTRAP_CI = 0.90              # 5th / 95th percentile of resampled Sharpe
BOOTSTRAP_SEED = 20200101        # fixed so the CI is reproducible per-run

TRADING_DAYS_PER_YEAR = 252

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parent
CACHE_DIR = Path.home() / ".cache" / "karpathy-quant-auto-research"
PRICES_PARQUET = CACHE_DIR / "prices.parquet"
UNIVERSE_JSON = REPO_ROOT / f"universe_{UNIVERSE_TAG}.json"

# Side-channel OOS log. Every run appends the full result dict here so the
# reviewer has an audit trail even when SHOW_OOS is off. The agent is
# expected NOT to `cat` or `grep` this file during the experiment loop.
OOS_RESULTS_TSV = REPO_ROOT / "oos_results.tsv"


def _show_oos() -> bool:
    """Whether print_summary reveals OOS numbers.

    Default True (backwards-compatible). Set `SHOW_OOS=0` to activate the
    strict honesty mode: the agent sees IS Sharpe + status_hint only;
    OOS detail lands in oos_results.tsv and the analysis notebook.
    """
    raw = os.environ.get("SHOW_OOS", "1").strip().lower()
    return raw not in {"0", "false", "no", "off"}


def _short_commit() -> str:
    """Current short git hash, or 'unknown' outside a repo."""
    try:
        out = subprocess.check_output(
            ["git", "-C", str(REPO_ROOT), "rev-parse", "--short=7", "HEAD"],
            stderr=subprocess.DEVNULL,
            timeout=5,
        )
        return out.decode().strip() or "unknown"
    except Exception:
        return "unknown"

# ---------------------------------------------------------------------------
# Universe
# ---------------------------------------------------------------------------

def load_universe() -> list[str]:
    """Return the frozen ticker list for UNIVERSE_TAG."""
    with open(UNIVERSE_JSON) as f:
        data = json.load(f)
    return list(data["tickers"])


def universe_asof(date: pd.Timestamp | str, prices: pd.DataFrame | None = None) -> list[str]:
    """Point-in-time universe membership as of `date`.

    Current behavior (no membership schedule file present): returns the
    static universe restricted to tickers that have at least one valid
    price at or before `date`. This partially mitigates survivorship bias
    for IPO-era additions (a ticker that started trading in 2015 is
    correctly absent from the 2010–2014 universe). Full PIT removals /
    delistings require an explicit `universe_membership_*.json` schedule
    that replays add/remove events; not yet supplied.

    Keep the signature stable — `run_backtest` and the notebook may call
    this regardless of whether a schedule exists.
    """
    ts = pd.Timestamp(date)
    full = load_universe()
    if prices is None:
        return full
    active = []
    for t in full:
        if t not in prices.columns:
            continue
        col = prices[t]
        first_valid = col.first_valid_index()
        if first_valid is not None and first_valid <= ts:
            active.append(t)
    return active


def membership_mask(prices: pd.DataFrame) -> pd.DataFrame:
    """(date × ticker) boolean mask: True where the ticker is active.

    Built from `universe_asof` — today equivalent to "has a valid price
    at or before this date". `run_backtest` uses this to force inactive
    weights to 0 so the agent cannot inadvertently long a not-yet-listed
    ticker with the residual allocation surviving through ffill.
    """
    cols = list(prices.columns)
    # first_valid_index per ticker: the first date we have a price for it.
    first_valid = {c: prices[c].first_valid_index() for c in cols}
    mask = pd.DataFrame(True, index=prices.index, columns=cols)
    for c, fv in first_valid.items():
        if fv is None:
            mask[c] = False
        else:
            mask.loc[mask.index < fv, c] = False
    return mask

# ---------------------------------------------------------------------------
# Price download + cache
# ---------------------------------------------------------------------------

def _download_batch(tickers: list[str], threads: bool):
    """Single yfinance call; returns dict of ticker -> Close series."""
    import yfinance as yf

    raw = yf.download(
        tickers=tickers,
        start=START_DATE,
        end=VAL_END_DATE,
        interval=BARS,
        auto_adjust=True,
        progress=False,
        threads=threads,
        group_by="ticker",
    )
    closes: dict[str, pd.Series] = {}
    if isinstance(raw.columns, pd.MultiIndex):
        for t in tickers:
            if (t, "Close") in raw.columns:
                s = raw[(t, "Close")].dropna()
                if len(s):
                    closes[t] = s
    else:
        s = raw["Close"].dropna() if "Close" in raw.columns else pd.Series(dtype=float)
        if len(s):
            closes[tickers[0]] = s
    return closes


def _download_prices(tickers: list[str]) -> pd.DataFrame:
    """Download adjusted closes via yfinance. Returns date x ticker DataFrame."""
    print(f"Downloading {len(tickers)} tickers from {START_DATE} to {VAL_END_DATE}...")
    closes = _download_batch(tickers, threads=True)

    # Retry any missing tickers serially (yfinance's sqlite cache locks under parallelism).
    missing = [t for t in tickers if t not in closes]
    if missing:
        print(f"Retrying {len(missing)} missing tickers serially: {missing}")
        retry = _download_batch(missing, threads=False)
        closes.update(retry)

    prices = pd.DataFrame(closes)
    if prices.index.tz is not None:
        prices.index = prices.index.tz_localize(None)
    prices.index = pd.to_datetime(prices.index)
    prices = prices.sort_index().dropna(axis=1, how="all")

    final_missing = [t for t in tickers if t not in prices.columns]
    if final_missing:
        print(f"WARNING: no data for {len(final_missing)} tickers (likely delisted): {final_missing}")

    # Sanity check: print the 10 largest single-day |returns| across the
    # panel. Most will be legit (March 2020 crash, earnings, etc.). A
    # stray 500% bar almost always signals a corporate-action artifact
    # (unadjusted split, bad dividend) worth investigating by hand.
    try:
        rets = prices.pct_change().abs()
        flat = rets.stack()
        if len(flat):
            top = flat.nlargest(10)
            print("Top 10 absolute daily returns in cached panel (sanity check):")
            for (dt, tk), val in top.items():
                print(f"  {pd.Timestamp(dt).date()}  {tk:<6} |r|={val:.3f}")
    except Exception as e:
        print(f"(corp-action audit skipped: {e})")

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


def is_prices(prices: pd.DataFrame) -> pd.DataFrame:
    """Return prices truncated to the IS window (START_DATE..TRAIN_END_DATE).

    Use this in `generate_weights` when you want to form a hypothesis
    without structurally touching OOS data — feed `is_prices(prices)` into
    your signal-building code during development. The experiment loop
    still passes the full frame, and T+1 / membership / costs apply on the
    full panel in `run_backtest`. This is just an opt-in honesty nudge.
    """
    return prices.loc[START_DATE:TRAIN_END_DATE]

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


def _validate_weight_panel(weights: pd.DataFrame, prices: pd.DataFrame) -> str | None:
    """Cheap pre-flight checks on the raw agent-produced weight panel.

    Returns None if OK, else a short reason string used as crash_reason.
    Checks run on the raw panel (pre-align) so an all-NaN or wrong-shaped
    frame is caught before metrics are computed from noise.
    """
    if not isinstance(weights, pd.DataFrame):
        return f"weights is {type(weights).__name__}, expected DataFrame"
    if weights.size == 0:
        return "weights panel is empty"
    nan_frac = float(weights.isna().values.mean()) if weights.size else 1.0
    if nan_frac > MAX_WEIGHT_NAN_FRACTION:
        return f"weights {nan_frac:.1%} NaN (> {MAX_WEIGHT_NAN_FRACTION:.0%})"
    return None


def _validate_effective_weights(w_eff: pd.DataFrame) -> str | None:
    """Post-align, post-shift checks. Looks for leverage blowups and
    pathologically frozen OOS behavior.
    """
    gross = w_eff.abs().sum(axis=1)
    max_gross = float(gross.max()) if len(gross) else 0.0
    if max_gross > MAX_GROSS_LEVERAGE:
        return f"max gross leverage {max_gross:.2f} > {MAX_GROSS_LEVERAGE:.2f}"
    # Frozen OOS panel: all OOS rows identical ⇒ never rebalances ⇒
    # likely a bug (row_sum div-by-zero collapsing to 0, cadence error).
    oos_w = val_slice(w_eff)
    if len(oos_w):
        # distinct rows (tolerant to float dust)
        rounded = oos_w.round(10)
        n_distinct = len(rounded.drop_duplicates())
        if n_distinct < MIN_WEIGHT_DISTINCT_ROWS:
            return f"OOS weights have only {n_distinct} distinct row(s)"
    return None


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


def _bootstrap_sharpe_ci(
    daily_returns: pd.Series,
    resamples: int = BOOTSTRAP_RESAMPLES,
    block_days: int = BOOTSTRAP_BLOCK_DAYS,
    ci: float = BOOTSTRAP_CI,
    seed: int = BOOTSTRAP_SEED,
) -> tuple[float, float]:
    """Stationary block bootstrap CI on annualized Sharpe.

    Politis–Romano: at each step either continue the current block (prob
    1 - 1/block_days) or jump to a uniformly-random new start. This
    preserves local autocorrelation structure while producing resamples
    the same length as the input.

    Returns (lo, hi) at the given central interval. (nan, nan) if the
    input is too short or non-finite.
    """
    r = daily_returns.dropna().to_numpy()
    n = len(r)
    if n < block_days * 2 or resamples < 1:
        return (float("nan"), float("nan"))

    rng = np.random.default_rng(seed)
    daily_rf = RISK_FREE_ANNUAL / TRADING_DAYS_PER_YEAR
    ann = math.sqrt(TRADING_DAYS_PER_YEAR)
    p_restart = 1.0 / block_days

    sharpes = np.empty(resamples, dtype=float)
    for k in range(resamples):
        idx = np.empty(n, dtype=np.int64)
        pos = int(rng.integers(0, n))
        for t in range(n):
            if t > 0 and rng.random() < p_restart:
                pos = int(rng.integers(0, n))
            idx[t] = pos
            pos = (pos + 1) % n
        sample = r[idx] - daily_rf
        sigma = sample.std(ddof=1)
        if sigma == 0 or not np.isfinite(sigma):
            sharpes[k] = np.nan
        else:
            sharpes[k] = sample.mean() / sigma * ann

    sharpes = sharpes[np.isfinite(sharpes)]
    if sharpes.size == 0:
        return (float("nan"), float("nan"))

    alpha = (1.0 - ci) / 2.0
    lo = float(np.quantile(sharpes, alpha))
    hi = float(np.quantile(sharpes, 1.0 - alpha))
    return (lo, hi)


def strat_returns(weights: pd.DataFrame, prices: pd.DataFrame) -> pd.Series:
    """Compute the daily strategy return series using the same math as
    run_backtest (T+1 shift, costs, borrow), without the metric reporting.

    Exposed for walk-forward / per-period analyses in the notebook. Runs
    on the full price history; slice the returned series to the window of
    interest before computing fold-level metrics.
    """
    w_raw = _align_weights(weights, prices)
    w_raw = w_raw.where(membership_mask(prices), 0.0)
    w_eff = w_raw.shift(1).fillna(0.0)
    rets = prices.pct_change().fillna(0.0)
    dw = w_eff.diff().abs().fillna(0.0)
    tc = dw.sum(axis=1) * (COST_BPS / 10_000.0)
    short_exposure = (-w_eff.clip(upper=0.0)).sum(axis=1)
    borrow = short_exposure * ((BORROW_BPS_ANNUAL / 10_000.0) / TRADING_DAYS_PER_YEAR)
    return (w_eff * rets).sum(axis=1) - tc - borrow


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

    # Pre-flight: catch malformed panels before any metrics are computed.
    pre_fail = _validate_weight_panel(weights, prices)
    if pre_fail is not None:
        return _crash_result(t_start, reason=pre_fail)

    # Align + clean
    w_raw = _align_weights(weights, prices)
    # Point-in-time membership: zero out weights on tickers that did not
    # yet exist (no price data on/before that date). This plugs the most
    # egregious IPO leak; full PIT removal of delisters requires a
    # membership schedule that we do not yet have.
    w_raw = w_raw.where(membership_mask(prices), 0.0)
    # T+1 shift: today's close executes yesterday's target weights
    w_eff = w_raw.shift(1).fillna(0.0)

    # Daily simple returns from adjusted closes
    rets = prices.pct_change().fillna(0.0)

    # Sanity: detect NaN/inf anywhere in weights that survived alignment
    if not np.isfinite(w_eff.values).all():
        return _crash_result(t_start, reason="non-finite weights")

    # Post-shift sanity: reject over-leveraged or frozen OOS panels
    post_fail = _validate_effective_weights(w_eff)
    if post_fail is not None:
        return _crash_result(t_start, reason=post_fail)

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

    # Per-calendar-year OOS Sharpe: decomposes the headline number so a
    # single-year driver (e.g. 2020 vol harvest) is visible to the reviewer.
    yearly_sharpe: dict[int, float] = {}
    if len(oos_ret):
        for year, group in oos_ret.groupby(oos_ret.index.year):
            yearly_sharpe[int(year)] = _sharpe(group)

    # Block-bootstrap CI on OOS Sharpe: how wide is the noise band around
    # the point estimate? A 0.42 → 0.51 "improvement" often lives inside
    # this interval, so the agent's keep rule tightens to `lo > running_best`.
    oos_sharpe_lo, oos_sharpe_hi = _bootstrap_sharpe_ci(oos_ret)
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
        "oos_sharpe_lo": float(oos_sharpe_lo),
        "oos_sharpe_hi": float(oos_sharpe_hi),
        "is_sharpe": float(is_sharpe),
        "max_drawdown": float(max_dd),
        "annual_return": float(annual_return),
        "annual_vol": float(annual_vol),
        "turnover_annual": float(turnover_annual),
        "calmar": float(calmar),
        "num_trades": int(num_trades),
        "backtest_seconds": float(backtest_seconds),
        "status_hint": status_hint,
        "yearly_sharpe": {y: float(s) for y, s in yearly_sharpe.items()},
    }


def _crash_result(t_start: float, reason: str) -> dict:
    return {
        "oos_sharpe": float("nan"),
        "oos_sharpe_lo": float("nan"),
        "oos_sharpe_hi": float("nan"),
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
        "yearly_sharpe": {},
    }

# ---------------------------------------------------------------------------
# Output contract
# ---------------------------------------------------------------------------

_OOS_HIDDEN = "<hidden, SHOW_OOS=0>"


def _append_oos_log(results: dict) -> None:
    """Append one row of OOS metrics to OOS_RESULTS_TSV (create if missing).

    Runs regardless of SHOW_OOS — the reviewer always has the audit trail.
    The schema is fixed and append-only; the agent should not read this
    file during the experiment loop.
    """
    header = [
        "commit",
        "oos_sharpe",
        "oos_sharpe_lo",
        "oos_sharpe_hi",
        "is_sharpe",
        "max_drawdown",
        "annual_return",
        "annual_vol",
        "turnover_annual",
        "calmar",
        "num_trades",
        "status_hint",
        "yearly_sharpe_json",
    ]
    try:
        new_file = not OOS_RESULTS_TSV.exists()
        row_vals = [
            _short_commit(),
            f"{results.get('oos_sharpe', float('nan')):.6f}",
            f"{results.get('oos_sharpe_lo', float('nan')):.6f}",
            f"{results.get('oos_sharpe_hi', float('nan')):.6f}",
            f"{results.get('is_sharpe', float('nan')):.6f}",
            f"{results.get('max_drawdown', float('nan')):.6f}",
            f"{results.get('annual_return', float('nan')):.6f}",
            f"{results.get('annual_vol', float('nan')):.6f}",
            f"{results.get('turnover_annual', float('nan')):.6f}",
            f"{results.get('calmar', float('nan')):.6f}",
            str(results.get("num_trades", 0)),
            str(results.get("status_hint", "")),
            json.dumps(results.get("yearly_sharpe", {})),
        ]
        with open(OOS_RESULTS_TSV, "a", encoding="utf-8", newline="") as f:
            if new_file:
                f.write("\t".join(header) + "\n")
            f.write("\t".join(row_vals) + "\n")
    except OSError:
        # Logging is best-effort — never let a filesystem hiccup crash a run.
        pass


def print_summary(results: dict) -> None:
    """Print the fixed summary block. The agent greps this from run.log.

    If `SHOW_OOS=0`, OOS-derived lines are replaced with a hidden marker
    (`<hidden — SHOW_OOS=0>`) and full metrics are preserved in
    `oos_results.tsv` for the reviewer. `status_hint` is always shown —
    it is the only OOS-derived signal the agent is allowed to see,
    because it encodes keep_eligible / force_discard / crash without
    revealing the underlying numbers.
    """
    _append_oos_log(results)
    show = _show_oos()

    def oos(val: float, fmt: str) -> str:
        return fmt.format(val) if show else _OOS_HIDDEN

    print("---")
    print(f"oos_sharpe:       {oos(results['oos_sharpe'], '{:.6f}')}")
    if show:
        lo = results.get("oos_sharpe_lo", float("nan"))
        hi = results.get("oos_sharpe_hi", float("nan"))
        print(f"oos_sharpe_ci:    [{lo:.6f}, {hi:.6f}]")
    else:
        print(f"oos_sharpe_ci:    {_OOS_HIDDEN}")
    print(f"is_sharpe:        {results['is_sharpe']:.6f}")
    print(f"max_drawdown:     {oos(results['max_drawdown'], '{:.4f}')}")
    print(f"annual_return:    {oos(results['annual_return'], '{:.4f}')}")
    print(f"annual_vol:       {oos(results['annual_vol'], '{:.4f}')}")
    print(f"turnover_annual:  {oos(results['turnover_annual'], '{:.2f}')}")
    print(f"calmar:           {oos(results['calmar'], '{:.4f}')}")
    print(f"num_trades:       {results['num_trades']}")
    print(f"backtest_seconds: {results['backtest_seconds']:.1f}")
    # Per-year OOS Sharpe — revealed only when SHOW_OOS is on.
    if show:
        for year in sorted(results.get("yearly_sharpe", {}).keys()):
            val = results["yearly_sharpe"][year]
            print(f"oos_sharpe_{year}:  {val:.6f}")
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
    print(f"Loaded prices: {prices.shape[0]} rows x {prices.shape[1]} tickers")
    print(f"Date range:    {prices.index.min().date()} -> {prices.index.max().date()}")
    print("Done! Ready to experiment.")


if __name__ == "__main__":
    main()
