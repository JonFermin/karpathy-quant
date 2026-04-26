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

UNIVERSE_TAG = os.environ.get("UNIVERSE_TAG", "sp100_2024").strip() or "sp100_2024"
BARS = "1d"

COST_BPS = 5.0                   # per-side transaction cost, applied to |Δw|

# Optional per-name vol-scaled impact slope. When IMPACT_BPS_SLOPE > 0, cost
# for each name is COST_BPS + IMPACT_BPS_SLOPE * vol_rank_pct, where
# vol_rank_pct is the name's 63d realized-vol percentile that day. This
# penalizes thin high-vol names the way a realistic execution cost would.
# Defaults to 0 (no impact) for backwards compatibility with the original
# harness. Set IMPACT_BPS_SLOPE=20 to emulate realistic biotech/small-cap.
IMPACT_BPS_SLOPE = float(os.environ.get("IMPACT_BPS_SLOPE", "0"))

# Per-universe borrow rate (bps per year on short exposure). Large caps are
# easy to borrow; small caps and biotechs are not. Opt-in via env var so
# existing cached Sharpes stay comparable; default is the flat 200bps.
_BORROW_BPS_BY_UNIVERSE = {
    "sp100_2024": 150.0,
    "sp500_2024": 200.0,
    "ndx100_2024": 150.0,
    "sp400_2024": 250.0,
    "sp600_2024": 400.0,
    "xbi_2026":   600.0,
}
_USE_UNIVERSE_TIER_BORROW = os.environ.get("USE_UNIVERSE_TIER_BORROW", "0").strip().lower() not in {"0", "false", "no", "off", ""}
BORROW_BPS_ANNUAL = (
    _BORROW_BPS_BY_UNIVERSE.get(UNIVERSE_TAG, 200.0)
    if _USE_UNIVERSE_TIER_BORROW else 200.0
)

RISK_FREE_ANNUAL = 0.03          # fallback when time-varying RF is disabled
USE_TIME_VARYING_RF = os.environ.get("USE_TIME_VARYING_RF", "0").strip().lower() not in {"0", "false", "no", "off", ""}

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

# Walk-forward fold definitions. Five non-overlapping 2-year windows spanning
# 2014–2023. 2010–2013 seeds lookback windows; 2024 is left out so the headline
# OOS year (2020–2024) is not fully re-used at fold granularity. Exported so
# `run_backtest` and `walkforward.py` share one source of truth — the fold
# set is part of the immutable contract, not a per-strategy choice.
WALKFORWARD_FOLDS: list[tuple[str, str, str]] = [
    ("fold_2014_2015", "2014-01-01", "2015-12-31"),
    ("fold_2016_2017", "2016-01-01", "2017-12-31"),
    ("fold_2018_2019", "2018-01-01", "2019-12-31"),
    ("fold_2020_2021", "2020-01-01", "2021-12-31"),
    ("fold_2022_2023", "2022-01-01", "2023-12-31"),
]

# Honest walk-forward split. IS_FOLDS live entirely inside the 2010-2019
# training window — they are the only folds that test true out-of-sample
# robustness without re-using the headline 2020-2024 OOS data. OOS_FOLDS
# are sub-windows of the headline OOS, so they inform regime stability
# but are NOT independent tests. The grader gates on IS_FOLDS median (hard)
# and OOS_FOLDS median (soft) separately.
IS_FOLDS: list[tuple[str, str, str]] = [
    ("fold_2014_2015", "2014-01-01", "2015-12-31"),
    ("fold_2016_2017", "2016-01-01", "2017-12-31"),
    ("fold_2018_2019", "2018-01-01", "2019-12-31"),
]
OOS_FOLDS: list[tuple[str, str, str]] = [
    ("fold_2020_2021", "2020-01-01", "2021-12-31"),
    ("fold_2022_2023", "2022-01-01", "2023-12-31"),
]

# Days of embargo trimmed from the start of each fold before the fold's
# Sharpe is computed. Absorbs lookback bleed-over — a strategy using a 63d
# rolling window at fold_start would contaminate the first ~63 trading days
# of the fold with pre-fold price information. 21 is a pragmatic compromise
# that handles most short-horizon lookbacks; longer-horizon strategies (6-
# 12 months) would want more.
EMBARGO_DAYS = 21

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parent
CACHE_DIR = Path.home() / ".cache" / "karpathy-quant-auto-research"
PRICES_PARQUET = CACHE_DIR / f"prices_{UNIVERSE_TAG}.parquet"
OPEN_PARQUET = CACHE_DIR / f"open_{UNIVERSE_TAG}.parquet"
HIGH_PARQUET = CACHE_DIR / f"high_{UNIVERSE_TAG}.parquet"
LOW_PARQUET = CACHE_DIR / f"low_{UNIVERSE_TAG}.parquet"
VOLUME_PARQUET = CACHE_DIR / f"volume_{UNIVERSE_TAG}.parquet"
# Broad-market reference (SPY adjusted close). Universe-agnostic — the
# agent uses it for regime gates, beta-neutralization, and excess-return
# residualization. Cached once and shared across universes.
MARKET_PROXY_TICKER = os.environ.get("MARKET_PROXY_TICKER", "SPY").strip().upper() or "SPY"
MARKET_PROXY_PARQUET = CACHE_DIR / f"market_proxy_{MARKET_PROXY_TICKER}.parquet"
UNIVERSE_JSON = REPO_ROOT / f"universe_{UNIVERSE_TAG}.json"
# Optional PIT membership schedule. Schema:
#   {"removals": [{"ticker": "XXX", "date": "YYYY-MM-DD"}, ...],
#    "additions": [{"ticker": "YYY", "date": "YYYY-MM-DD"}, ...]}
# Absence is a signal: current behavior is "ticker is active whenever it
# has valid prices". Presence overlays explicit removals and lazy-additions
# on top. Population is out-of-scope for this harness — the user is
# expected to curate it from iShares/SPDR holdings history.
UNIVERSE_MEMBERSHIP_JSON = REPO_ROOT / f"universe_membership_{UNIVERSE_TAG}.json"
# Cached 13-week T-bill discount rate (^IRX) for time-varying risk-free.
RF_PARQUET = CACHE_DIR / "rf_3m.parquet"

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


def _load_membership_schedule() -> dict | None:
    """Load the optional PIT membership schedule for UNIVERSE_TAG.

    Returns None when the file is absent or malformed (caller falls back
    to the first-valid-index heuristic). A well-formed schedule is a dict
    with keys 'removals' and/or 'additions', each a list of
    {ticker, date} records.
    """
    if not UNIVERSE_MEMBERSHIP_JSON.exists():
        return None
    try:
        with open(UNIVERSE_MEMBERSHIP_JSON) as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict):
        return None
    return data


def membership_mask(prices: pd.DataFrame) -> pd.DataFrame:
    """(date × ticker) boolean mask: True where the ticker is active.

    Baseline rule: a ticker is active on dates on or after its
    first-valid-price date. If a PIT membership schedule exists for this
    universe, it overlays:
      - `additions`: each ticker becomes active only on/after its added date
        (later of first-valid-price and schedule's added date).
      - `removals`: each ticker becomes inactive strictly after its
        removed date, no matter how much price data exists beyond that.
    `run_backtest` uses this to force inactive weights to 0 so the agent
    cannot inadvertently long a not-yet-listed or already-delisted ticker.
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

    schedule = _load_membership_schedule()
    if schedule is None:
        return mask

    for rec in schedule.get("additions") or []:
        ticker = str(rec.get("ticker", "")).strip()
        added = rec.get("date")
        if ticker not in mask.columns or added is None:
            continue
        try:
            added_ts = pd.Timestamp(added)
        except (ValueError, TypeError):
            continue
        mask.loc[mask.index < added_ts, ticker] = False

    for rec in schedule.get("removals") or []:
        ticker = str(rec.get("ticker", "")).strip()
        removed = rec.get("date")
        if ticker not in mask.columns or removed is None:
            continue
        try:
            removed_ts = pd.Timestamp(removed)
        except (ValueError, TypeError):
            continue
        mask.loc[mask.index > removed_ts, ticker] = False

    return mask

# ---------------------------------------------------------------------------
# Price download + cache
# ---------------------------------------------------------------------------

_OHLCV_FIELDS = ("Open", "High", "Low", "Close", "Volume")
_FIELD_TO_PARQUET = {
    "open": OPEN_PARQUET,
    "high": HIGH_PARQUET,
    "low": LOW_PARQUET,
    "close": PRICES_PARQUET,
    "volume": VOLUME_PARQUET,
}


def _download_batch(tickers: list[str], threads: bool):
    """Single yfinance call; returns dict[field, dict[ticker, Series]] over OHLCV.

    `auto_adjust=True` back-adjusts Open/High/Low/Close for splits and
    dividends, and split-adjusts Volume. So a stock that did a 2-for-1
    in 2018 will not show a synthetic price gap or volume pop on the
    split date — what the agent sees is a clean continuous series.
    """
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
    out: dict[str, dict[str, pd.Series]] = {f: {} for f in _OHLCV_FIELDS}
    if isinstance(raw.columns, pd.MultiIndex):
        for t in tickers:
            for field in _OHLCV_FIELDS:
                if (t, field) in raw.columns:
                    s = raw[(t, field)].dropna()
                    if len(s):
                        out[field][t] = s
    else:
        # Single-ticker download flattens columns.
        if tickers:
            t = tickers[0]
            for field in _OHLCV_FIELDS:
                if field in raw.columns:
                    s = raw[field].dropna()
                    if len(s):
                        out[field][t] = s
    return out


def _download_panel(tickers: list[str]) -> dict[str, pd.DataFrame]:
    """Download adjusted OHLCV via yfinance. Returns {field_lower: date×ticker DataFrame}."""
    print(f"Downloading {len(tickers)} tickers from {START_DATE} to {VAL_END_DATE}...")
    out = _download_batch(tickers, threads=True)

    # Retry any missing tickers serially (yfinance's sqlite cache locks under parallelism).
    missing = [t for t in tickers if t not in out["Close"]]
    if missing:
        print(f"Retrying {len(missing)} missing tickers serially: {missing}")
        retry = _download_batch(missing, threads=False)
        for field, series_map in retry.items():
            out[field].update(series_map)

    panels: dict[str, pd.DataFrame] = {}
    for field in _OHLCV_FIELDS:
        df = pd.DataFrame(out[field])
        if df.index.tz is not None:
            df.index = df.index.tz_localize(None)
        df.index = pd.to_datetime(df.index)
        df = df.sort_index().dropna(axis=1, how="all")
        panels[field.lower()] = df

    final_missing = [t for t in tickers if t not in panels["close"].columns]
    if final_missing:
        print(f"WARNING: no data for {len(final_missing)} tickers (likely delisted): {final_missing}")

    # Sanity check on close: top 10 absolute daily returns. Stray 500% bars
    # usually signal a corporate-action artifact (unadjusted split, bad div).
    try:
        rets = panels["close"].pct_change().abs()
        flat = rets.stack()
        if len(flat):
            top = flat.nlargest(10)
            print("Top 10 absolute daily returns in cached panel (sanity check):")
            for (dt, tk), val in top.items():
                print(f"  {pd.Timestamp(dt).date()}  {tk:<6} |r|={val:.3f}")
    except Exception as e:
        print(f"(corp-action audit skipped: {e})")

    return panels


def _all_ohlcv_caches_exist() -> bool:
    return all(p.exists() for p in _FIELD_TO_PARQUET.values())


def _ensure_ohlcv_caches(refresh: bool = False) -> None:
    """Make sure all OHLCV parquets exist on disk for UNIVERSE_TAG.

    If `refresh` is False, the existing close cache is preserved even when
    other fields are missing — re-downloading would silently shift prior
    backtest results because yfinance's corporate-action data updates over
    time. To force a full refresh of all 5 fields, pass `--refresh`.
    """
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    if not refresh and _all_ohlcv_caches_exist():
        return
    close_exists = PRICES_PARQUET.exists()
    tickers = load_universe()
    panels = _download_panel(tickers)
    for field, path in _FIELD_TO_PARQUET.items():
        # Preserve the existing close cache unless --refresh is explicit, so
        # adding new fields to an existing universe does not invalidate prior
        # cached Sharpes.
        if field == "close" and close_exists and not refresh:
            continue
        df = panels.get(field)
        if df is None:
            continue
        df.to_parquet(path)
    n_rows = panels["close"].shape[0]
    n_cols = panels["close"].shape[1]
    print(f"Cached OHLCV ({n_rows} rows × {n_cols} tickers, 5 fields) to {CACHE_DIR}")


def _read_field_parquet(path: Path) -> pd.DataFrame:
    df = pd.read_parquet(path)
    df.index = pd.to_datetime(df.index)
    return df


def load_prices(refresh: bool = False) -> pd.DataFrame:
    """Adjusted close prices (date × ticker) for the universe.

    Triggers a one-time OHLCV download if any feature cache is missing.
    Existing close caches are preserved on backfill so prior backtest
    results stay reproducible — pass refresh=True (or `--refresh` on the
    CLI) to force a full re-download of all five fields.
    """
    _ensure_ohlcv_caches(refresh=refresh)
    return _read_field_parquet(PRICES_PARQUET)


def load_open(refresh: bool = False) -> pd.DataFrame:
    """Adjusted opens (date × ticker)."""
    _ensure_ohlcv_caches(refresh=refresh)
    return _read_field_parquet(OPEN_PARQUET)


def load_high(refresh: bool = False) -> pd.DataFrame:
    """Adjusted intraday highs (date × ticker)."""
    _ensure_ohlcv_caches(refresh=refresh)
    return _read_field_parquet(HIGH_PARQUET)


def load_low(refresh: bool = False) -> pd.DataFrame:
    """Adjusted intraday lows (date × ticker)."""
    _ensure_ohlcv_caches(refresh=refresh)
    return _read_field_parquet(LOW_PARQUET)


def load_volume(refresh: bool = False) -> pd.DataFrame:
    """Split-adjusted daily share volume (date × ticker).

    Useful as a raw liquidity signal. For dollar liquidity, prefer
    `load_dollar_volume()` (close × volume) — comparing share volume across
    a $5 microcap and a $500 megacap directly would be meaningless.
    """
    _ensure_ohlcv_caches(refresh=refresh)
    return _read_field_parquet(VOLUME_PARQUET)


def load_dollar_volume(refresh: bool = False) -> pd.DataFrame:
    """Daily dollar volume (date × ticker) = close × volume.

    The canonical liquidity proxy for cross-sectional sizing — execution
    capacity scales with dollar volume, not share volume. Common uses:
    liquidity-weighted sizing, illiquid-name screen, ADV-based gross caps.
    """
    _ensure_ohlcv_caches(refresh=refresh)
    close = _read_field_parquet(PRICES_PARQUET)
    volume = _read_field_parquet(VOLUME_PARQUET)
    return close * volume


def load_panel(refresh: bool = False) -> dict[str, pd.DataFrame]:
    """Full OHLCV panel + dollar_volume as a dict of DataFrames.

    Keys: open, high, low, close, volume, dollar_volume.

    Use this when a strategy needs multiple fields together (e.g. daily
    range = (high - low) / close, overnight return = open / close.shift(1) - 1,
    Garman-Klass realized vol). Reads from disk once per field.
    """
    _ensure_ohlcv_caches(refresh=refresh)
    panel = {field: _read_field_parquet(path) for field, path in _FIELD_TO_PARQUET.items()}
    panel["dollar_volume"] = panel["close"] * panel["volume"]
    return panel


def load_market_proxy(refresh: bool = False) -> pd.Series:
    """Adjusted close of the broad-market reference (default SPY).

    Use for regime gating (drawdown from peak, 200d MA filter), beta
    neutralization (regress per-name returns on market returns), or
    excess-return residualization. The series is universe-agnostic — it
    is downloaded once per MARKET_PROXY_TICKER and shared across all
    universes that load it.
    """
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    if MARKET_PROXY_PARQUET.exists() and not refresh:
        df = pd.read_parquet(MARKET_PROXY_PARQUET)
        df.index = pd.to_datetime(df.index)
        return df.iloc[:, 0]

    panels = _download_panel([MARKET_PROXY_TICKER])
    s = panels["close"].iloc[:, 0] if not panels["close"].empty else pd.Series(dtype=float)
    s.name = MARKET_PROXY_TICKER
    s.to_frame().to_parquet(MARKET_PROXY_PARQUET)
    print(f"Cached market proxy {MARKET_PROXY_TICKER}: {len(s)} rows -> {MARKET_PROXY_PARQUET}")
    return s

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


def load_rf(prices: pd.DataFrame) -> pd.Series:
    """Daily risk-free rate series aligned to prices.index.

    When USE_TIME_VARYING_RF is on, pulls ^IRX (13-week T-bill discount
    rate) from a cached parquet (downloads on first call), converts the
    annualized percentage to a daily simple rate, ffills across price
    dates, and fills any head gaps with RISK_FREE_ANNUAL/252. When off,
    returns a constant-valued series (RISK_FREE_ANNUAL/252 every day).
    """
    daily_const = RISK_FREE_ANNUAL / TRADING_DAYS_PER_YEAR
    if not USE_TIME_VARYING_RF:
        return pd.Series(daily_const, index=prices.index, name="rf_daily")

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    if not RF_PARQUET.exists():
        try:
            import yfinance as yf
            raw = yf.download(
                tickers="^IRX",
                start=START_DATE,
                end=VAL_END_DATE,
                interval=BARS,
                auto_adjust=False,
                progress=False,
                threads=False,
            )
            if isinstance(raw.columns, pd.MultiIndex):
                close = raw["Close"].iloc[:, 0] if "Close" in raw.columns.levels[0] else raw.iloc[:, 0]
            else:
                close = raw["Close"] if "Close" in raw.columns else raw.iloc[:, 0]
            close = close.dropna()
            if close.index.tz is not None:
                close.index = close.index.tz_localize(None)
            close.to_frame(name="irx").to_parquet(RF_PARQUET)
        except Exception as e:
            print(f"(load_rf: ^IRX download failed — {e}; falling back to flat RF)")
            return pd.Series(daily_const, index=prices.index, name="rf_daily")

    try:
        df = pd.read_parquet(RF_PARQUET)
        irx = df.iloc[:, 0]
    except Exception:
        return pd.Series(daily_const, index=prices.index, name="rf_daily")

    # ^IRX is quoted as an annual discount rate in percentage points.
    # Convert to daily simple rate: (annual_pct / 100) / 252.
    rf_daily = (irx / 100.0) / TRADING_DAYS_PER_YEAR
    rf_daily = rf_daily.reindex(prices.index).ffill().fillna(daily_const)
    rf_daily.name = "rf_daily"
    return rf_daily


def _sharpe(daily_returns: pd.Series, daily_rf: pd.Series | float | None = None) -> float:
    """Annualized Sharpe on daily returns (excess over daily RF).

    `daily_rf` may be a pandas Series aligned on the same date index as
    `daily_returns`, a scalar, or None (falls back to the flat
    RISK_FREE_ANNUAL / 252).
    """
    r = daily_returns.dropna()
    if len(r) < 2:
        return float("nan")
    if daily_rf is None:
        rf = RISK_FREE_ANNUAL / TRADING_DAYS_PER_YEAR
        excess = r - rf
    elif isinstance(daily_rf, pd.Series):
        rf = daily_rf.reindex(r.index).fillna(RISK_FREE_ANNUAL / TRADING_DAYS_PER_YEAR)
        excess = r - rf
    else:
        excess = r - float(daily_rf)
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
    daily_rf: pd.Series | float | None = None,
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
    if daily_rf is None:
        rf_arr = np.full(n, RISK_FREE_ANNUAL / TRADING_DAYS_PER_YEAR)
    elif isinstance(daily_rf, pd.Series):
        rf_arr = daily_rf.reindex(daily_returns.dropna().index).fillna(
            RISK_FREE_ANNUAL / TRADING_DAYS_PER_YEAR
        ).to_numpy()
    else:
        rf_arr = np.full(n, float(daily_rf))
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
        sample = r[idx] - rf_arr[idx]
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


def _transaction_cost_series(
    dw: pd.DataFrame, prices: pd.DataFrame
) -> pd.Series:
    """Daily transaction cost series.

    Base rate: COST_BPS per side per unit |Δw|. When IMPACT_BPS_SLOPE > 0,
    a per-name impact term is added: each name's bps is
    COST_BPS + IMPACT_BPS_SLOPE * vol_rank_pct, where vol_rank_pct is
    that name's 63-day realized-vol percentile that day (cross-sectional
    rank in [0,1]). Thin high-vol names pay more per trade, which is a
    first-order correction toward realistic execution on biotech/small-cap
    universes.
    """
    base = dw.sum(axis=1) * (COST_BPS / 10_000.0)
    if IMPACT_BPS_SLOPE <= 0:
        return base
    vol_63d = prices.pct_change().rolling(63).std()
    vol_rank = vol_63d.rank(axis=1, pct=True)  # (date × ticker), pct rank
    bps_per_name = (COST_BPS + IMPACT_BPS_SLOPE * vol_rank) / 10_000.0
    bps_per_name = bps_per_name.reindex(
        index=dw.index, columns=dw.columns
    ).fillna(COST_BPS / 10_000.0)
    impact = (dw * bps_per_name).sum(axis=1)
    # Subtract the base (which used flat COST_BPS) so we don't double-count
    # the intercept — `impact` already includes the COST_BPS term.
    return impact


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
    tc = _transaction_cost_series(dw, prices)
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

    # Transaction cost: per-name bps * |Δw|, summed across names (uses
    # IMPACT_BPS_SLOPE when the env var is on, flat COST_BPS otherwise).
    dw = w_eff.diff().abs().fillna(0.0)
    turnover_daily = dw.sum(axis=1)  # sum of |Δw_i| per day (reported)
    tc = _transaction_cost_series(dw, prices)

    # Borrow cost on shorts: (sum of negative weights, as a positive number) * daily borrow rate
    short_exposure = (-w_eff.clip(upper=0.0)).sum(axis=1)
    daily_borrow_rate = (BORROW_BPS_ANNUAL / 10_000.0) / TRADING_DAYS_PER_YEAR
    borrow = short_exposure * daily_borrow_rate

    strat_daily = pnl_per_name.sum(axis=1) - tc - borrow
    equity = (1.0 + strat_daily).cumprod()

    # Time-varying risk-free rate (falls back to flat RISK_FREE_ANNUAL when
    # USE_TIME_VARYING_RF is off). Sharpes below use this for excess returns.
    rf_daily = load_rf(prices)

    # Slice into IS / OOS
    is_ret = train_slice(strat_daily)
    oos_ret = val_slice(strat_daily)
    oos_eq = val_slice(equity)

    # Metrics (OOS is the headline)
    oos_sharpe = _sharpe(oos_ret, daily_rf=rf_daily)
    is_sharpe = _sharpe(is_ret, daily_rf=rf_daily)

    # Per-calendar-year OOS Sharpe: decomposes the headline number so a
    # single-year driver (e.g. 2020 vol harvest) is visible to the reviewer.
    yearly_sharpe: dict[int, float] = {}
    if len(oos_ret):
        for year, group in oos_ret.groupby(oos_ret.index.year):
            yearly_sharpe[int(year)] = _sharpe(group, daily_rf=rf_daily)

    # Walk-forward per-fold Sharpes with an embargo trim at each fold's
    # start — see EMBARGO_DAYS constant. IS_FOLDS are entirely inside
    # the training window (honest walk-forward); OOS_FOLDS are inside the
    # headline OOS window (regime stability, NOT independent). The grader
    # gates on IS_FOLDS median hard, OOS_FOLDS median soft.
    def _fold_sharpe(f_start: str, f_end: str) -> float:
        seg = strat_daily.loc[f_start:f_end]
        if len(seg) <= EMBARGO_DAYS:
            return float("nan")
        return _sharpe(seg.iloc[EMBARGO_DAYS:], daily_rf=rf_daily)

    fold_sharpes: dict[str, float] = {}
    is_fold_sharpes: dict[str, float] = {}
    oos_fold_sharpes: dict[str, float] = {}
    for name, f_start, f_end in IS_FOLDS:
        s = _fold_sharpe(f_start, f_end)
        is_fold_sharpes[name] = s
        fold_sharpes[name] = s
    for name, f_start, f_end in OOS_FOLDS:
        s = _fold_sharpe(f_start, f_end)
        oos_fold_sharpes[name] = s
        fold_sharpes[name] = s

    def _median_min(d: dict[str, float]) -> tuple[float, float]:
        finite = [v for v in d.values() if np.isfinite(v)]
        if not finite:
            return (float("nan"), float("nan"))
        return (float(np.median(finite)), float(min(finite)))

    median_fold_sharpe, min_fold_sharpe = _median_min(fold_sharpes)
    is_fold_median_sharpe, is_fold_min_sharpe = _median_min(is_fold_sharpes)
    oos_fold_median_sharpe, oos_fold_min_sharpe = _median_min(oos_fold_sharpes)

    # Block-bootstrap CI on OOS Sharpe: how wide is the noise band around
    # the point estimate? A 0.42 → 0.51 "improvement" often lives inside
    # this interval, so the agent's keep rule tightens to `lo > running_best`.
    oos_sharpe_lo, oos_sharpe_hi = _bootstrap_sharpe_ci(oos_ret, daily_rf=rf_daily)
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
        "fold_sharpes": {k: float(v) for k, v in fold_sharpes.items()},
        "median_fold_sharpe": median_fold_sharpe,
        "min_fold_sharpe": min_fold_sharpe,
        "is_fold_sharpes": {k: float(v) for k, v in is_fold_sharpes.items()},
        "oos_fold_sharpes": {k: float(v) for k, v in oos_fold_sharpes.items()},
        "is_fold_median_sharpe": is_fold_median_sharpe,
        "is_fold_min_sharpe": is_fold_min_sharpe,
        "oos_fold_median_sharpe": oos_fold_median_sharpe,
        "oos_fold_min_sharpe": oos_fold_min_sharpe,
        # Serialized OOS daily-return series so the grader can paired-test
        # (Jobson-Korkie/Memmel) against the baseline's OOS returns.
        "oos_daily_returns_json": oos_ret.to_json(
            orient="split", date_format="iso", date_unit="s"
        ),
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
        "fold_sharpes": {},
        "median_fold_sharpe": float("nan"),
        "min_fold_sharpe": float("nan"),
        "is_fold_sharpes": {},
        "oos_fold_sharpes": {},
        "is_fold_median_sharpe": float("nan"),
        "is_fold_min_sharpe": float("nan"),
        "oos_fold_median_sharpe": float("nan"),
        "oos_fold_min_sharpe": float("nan"),
        "oos_daily_returns_json": "",
    }

# ---------------------------------------------------------------------------
# Output contract
# ---------------------------------------------------------------------------

_OOS_HIDDEN = "<hidden, SHOW_OOS=0>"


OOS_LOG_HEADER = [
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
    "median_fold_sharpe",
    "min_fold_sharpe",
    "fold_sharpes_json",
    "is_fold_median_sharpe",
    "is_fold_min_sharpe",
    "oos_fold_median_sharpe",
    "oos_fold_min_sharpe",
    "is_fold_sharpes_json",
    "oos_fold_sharpes_json",
    "oos_daily_returns_json",
]


def _migrate_oos_log_if_needed() -> None:
    """If OOS_RESULTS_TSV exists with an older header, set it aside so the
    new run starts a fresh file with OOS_LOG_HEADER. Best-effort; the file
    is gitignored, so worst-case we lose an audit trail the user can still
    recover from the `.old` backup.
    """
    if not OOS_RESULTS_TSV.exists():
        return
    try:
        # Empty file isn't old-schema — don't pointlessly rotate a 0-byte file
        # (and worse, clobber the existing .old in doing so).
        if OOS_RESULTS_TSV.stat().st_size == 0:
            return
        with open(OOS_RESULTS_TSV, "r", encoding="utf-8") as f:
            first = f.readline().rstrip("\n")
        if first.split("\t") == OOS_LOG_HEADER:
            return
        # If a previous .old backup already exists, pick a timestamped suffix
        # so migrations never destroy prior audit trails.
        base = OOS_RESULTS_TSV.with_suffix(OOS_RESULTS_TSV.suffix + ".old")
        backup = base
        if backup.exists():
            from datetime import datetime as _dt
            backup = OOS_RESULTS_TSV.with_suffix(
                OOS_RESULTS_TSV.suffix + f".old.{_dt.now():%Y%m%d_%H%M%S}"
            )
        OOS_RESULTS_TSV.replace(backup)
    except OSError:
        pass


def _append_oos_log(results: dict) -> None:
    """Append one row of OOS metrics to OOS_RESULTS_TSV (create if missing).

    Runs regardless of SHOW_OOS — the reviewer always has the audit trail.
    The schema is fixed and append-only; the agent should not read this
    file during the experiment loop (log_result.py reads it; that's the
    one sanctioned consumer).
    """
    try:
        _migrate_oos_log_if_needed()
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
            f"{results.get('median_fold_sharpe', float('nan')):.6f}",
            f"{results.get('min_fold_sharpe', float('nan')):.6f}",
            json.dumps(results.get("fold_sharpes", {})),
            f"{results.get('is_fold_median_sharpe', float('nan')):.6f}",
            f"{results.get('is_fold_min_sharpe', float('nan')):.6f}",
            f"{results.get('oos_fold_median_sharpe', float('nan')):.6f}",
            f"{results.get('oos_fold_min_sharpe', float('nan')):.6f}",
            json.dumps(results.get("is_fold_sharpes", {})),
            json.dumps(results.get("oos_fold_sharpes", {})),
            results.get("oos_daily_returns_json", ""),
        ]
        with open(OOS_RESULTS_TSV, "a", encoding="utf-8", newline="") as f:
            if new_file:
                f.write("\t".join(OOS_LOG_HEADER) + "\n")
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
    # Per-fold Sharpes. Folds overlap the 2020–2024 OOS window so the
    # numbers are masked under SHOW_OOS=0 (revealing them would leak OOS
    # signal the agent is not supposed to see during the loop). The grader
    # still reads the real values out of oos_results.tsv.
    fold_sharpes = results.get("fold_sharpes", {}) or {}
    for name in sorted(fold_sharpes.keys()):
        val = fold_sharpes[name]
        print(f"{name}:  {oos(val, '{:.6f}')}")
    med = results.get("median_fold_sharpe", float("nan"))
    mn = results.get("min_fold_sharpe", float("nan"))
    print(f"median_fold_sharpe: {oos(med, '{:.6f}')}")
    print(f"min_fold_sharpe:    {oos(mn, '{:.6f}')}")
    # Split IS-fold and OOS-fold summaries. IS-fold numbers are honest
    # walk-forward (2014-2019, inside training window); OOS-fold numbers
    # are sub-windows of 2020-2024 and leak OOS info, so they are masked
    # under SHOW_OOS=0.
    is_med = results.get("is_fold_median_sharpe", float("nan"))
    is_mn = results.get("is_fold_min_sharpe", float("nan"))
    # IS-fold medians are computed on IS-only data, so reveal them even
    # under SHOW_OOS=0 — they are honest IS robustness signal.
    if math.isfinite(is_med):
        print(f"is_fold_median_sharpe: {is_med:.6f}")
    else:
        print("is_fold_median_sharpe: nan")
    if math.isfinite(is_mn):
        print(f"is_fold_min_sharpe:    {is_mn:.6f}")
    else:
        print("is_fold_min_sharpe:    nan")
    oos_med = results.get("oos_fold_median_sharpe", float("nan"))
    oos_mn = results.get("oos_fold_min_sharpe", float("nan"))
    print(f"oos_fold_median_sharpe: {oos(oos_med, '{:.6f}')}")
    print(f"oos_fold_min_sharpe:    {oos(oos_mn, '{:.6f}')}")
    # status_hint is informational only; the grader (log_result.py) applies
    # the real keep/discard rule.
    print(f"status_hint:      {results['status_hint']}")

# ---------------------------------------------------------------------------
# Main (data prep only)
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Prepare price + OHLCV + market proxy cache for karpathy-quant-auto-research")
    parser.add_argument("--refresh", action="store_true", help="Force re-download even if cache exists (rewrites all 5 OHLCV fields and the market proxy)")
    parser.add_argument("--skip-market-proxy", action="store_true", help="Skip downloading the broad-market reference (SPY by default)")
    args = parser.parse_args()

    print(f"Cache directory: {CACHE_DIR}")
    print(f"Universe: {UNIVERSE_TAG} ({UNIVERSE_JSON.name})")
    prices = load_prices(refresh=args.refresh)
    print(f"Loaded prices: {prices.shape[0]} rows x {prices.shape[1]} tickers")
    print(f"Date range:    {prices.index.min().date()} -> {prices.index.max().date()}")
    volume = load_volume(refresh=False)  # already populated by load_prices on first run
    nz = float((volume > 0).values.mean()) if volume.size else 0.0
    print(f"Loaded volume: {volume.shape[0]} rows x {volume.shape[1]} tickers ({nz*100:.1f}% non-zero cells)")
    if not args.skip_market_proxy:
        proxy = load_market_proxy(refresh=args.refresh)
        if len(proxy):
            print(f"Loaded market proxy {MARKET_PROXY_TICKER}: {len(proxy)} rows ({proxy.index.min().date()} -> {proxy.index.max().date()})")
        else:
            print(f"WARNING: market proxy {MARKET_PROXY_TICKER} download empty")
    print("Done! Ready to experiment.")


if __name__ == "__main__":
    main()
