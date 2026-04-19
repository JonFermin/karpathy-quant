# karpathy-quant-auto-research

*One day, frontier quant research used to be done by meat traders staring at Bloomberg terminals between coffee and lunch, synchronizing once in a while in the ritual of "the morning meeting." That era is long gone. Research is now entirely the domain of autonomous swarms of AI agents grinding through centuries of tick data overnight while everyone sleeps. The agents claim that we are now in the 4,311th generation of the strategy repo; in any case no one could tell if that's right or wrong as the "strategy" is now a self-modifying signal graph that has grown beyond human comprehension. This repo is the story of how it all began.*

The idea: give an AI agent a small but real vectorized backtesting harness on daily US equities and let it experiment autonomously overnight. It modifies the signal generator, runs a backtest against a frozen IS/OOS split, checks if OOS Sharpe improved subject to hard constraints, keeps or discards, and repeats. You wake up in the morning to a log of ~100 experiments and (hopefully) a better strategy. This is a direct fork of the pattern established in [karpathy/autoresearch](https://github.com/karpathy/autoresearch) — swap LLM pretraining for quant strategy search. The agent edits one file. The human reviews in the morning.

**This is research, not a product.** There is no live deployment, no broker connection, no paper-trading link. The deliverable is a git-native audit trail of experiments for a human to review.

## How it works

The repo is deliberately kept small and only really has three files that matter:

- **`prepare.py`** — fixed constants, one-time data prep (downloads adjusted closes via yfinance), and the backtest engine (`run_backtest`, `print_summary`, `TimeBudget`). The T+1 execution shift lives inside `run_backtest` so the agent cannot accidentally introduce look-ahead. **Not modified.**
- **`strategy.py`** — the single file the agent edits. Contains `generate_weights(prices) → weights` and a driver that calls `run_backtest` and prints the output block. Everything inside `generate_weights` is fair game: new signals, sizing, regime filters, rebalancing cadence, neutralization, etc.
- **`program.md`** — baseline instructions for one agent. Point your agent here and let it go. **This file is edited and iterated on by the human.**

The metric is **`oos_sharpe`** (out-of-sample annualized Sharpe on the 2020–2024 slice) subject to hard constraints: `max_drawdown ≤ 0.35` and `turnover_annual ≤ 50.0`. Higher Sharpe is better. Constraint-violating runs are force-discarded regardless of Sharpe.

## Quick start

**Requirements:** Python 3.10+, [uv](https://docs.astral.sh/uv/), internet access for the one-time yfinance download.

```bash
# 1. Install uv (if you don't already have it)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. Install dependencies
uv sync

# 3. Download and cache prices (one-time, ~1–2 min)
uv run prepare.py

# 4. Manually run the baseline backtest (~a few seconds)
uv run strategy.py
```

If the above all work, your setup is good and you can go into autonomous research mode.

## Running the agent

Spin up Claude Code (or Codex, or whatever) in this repo and prompt something like:

```
Hi have a look at program.md and let's kick off a new experiment! let's do the setup first.
```

The `program.md` file is essentially a super lightweight "skill."

## Project structure

```
prepare.py                  — constants, data loader, backtest engine (do not modify)
strategy.py                 — signal + weights (agent modifies this)
program.md                  — agent instructions
universe_sp100_2024.json    — frozen ticker list (checked in)
analysis.ipynb              — notebook for reviewing results.tsv
running_best.py             — CLI: current best kept oos_sharpe
log_result.py               — CLI: append a row to results.tsv from run.log
walkforward.py              — CLI: per-fold Sharpe sanity check for a strategy
test_lookahead.py           — regression test for the T+1 shift
pyproject.toml              — dependencies
```

## Design choices

- **Single file to modify.** The agent only touches `strategy.py`. This keeps scope manageable and diffs reviewable.
- **T+1 shift enforced in the harness.** The weights your strategy produces using data up to day `t` only take effect at the close of day `t+1`. This is done inside `run_backtest` — the strategy cannot bypass it without editing `prepare.py`, which is forbidden.
- **Single IS/OOS split, not walk-forward.** 2010–2019 is IS, 2020–2024 is OOS. The research loop uses this single split so the agent can run hundreds of experiments cheaply; `walkforward.py` (5 non-overlapping 2-year folds, 2014–2023) and deflated Sharpe in `analysis.ipynb` are morning-review analyses layered on top of kept rows.
- **Trust-based IS/OOS honesty with an optional strict mode.** `run_backtest` reports both splits on every run; set `SHOW_OOS=0` in the environment and OOS-derived lines are masked in `run.log`, with the full audit trail written to a side-channel `oos_results.tsv` the reviewer consults. The agent forms hypotheses on `is_sharpe` and uses `status_hint` + `running_best.py` to gate keep/discard.
- **Bootstrap CI on OOS Sharpe.** A stationary block bootstrap (200 resamples, 20-day blocks) is reported with every run. The keep rule tightens to `ci_lo > running_best - 0.1` so a 0.03 "improvement" that lives inside the noise band is not kept.
- **Per-year OOS Sharpe decomposition.** Each run emits `oos_sharpe_2020..2024` so a single-year driver (e.g. a 2020 vol harvest) is visible instead of hidden inside the headline.
- **Hard constraints are blunt.** Max-DD and turnover caps keep degenerate strategies (leveraged martingale, daily-rebalance parameter fits) out of the `keep` list. They don't guarantee the strategy is good — just that it isn't obviously broken.

## Caveats / disclaimers

This repo is designed for **research process, not production alpha.** Known issues with the backtest:

- **Survivorship bias.** The universe is a frozen 2024-dated SP100 snapshot. Any ticker that was delisted or renamed before 2024-12-31 is silently absent; `run_backtest` does force weights to 0 on tickers that have no price data yet (mitigating IPO-era leakage for e.g. META, ABBV, TSLA), but a proper point-in-time membership schedule is not yet supplied. Results are biased upward relative to a real PIT backtest.
- **Data fidelity.** Prices come from yfinance (free, unaudited, adjusted closes). Corporate-action handling, dividend handling, and split adjustments follow yfinance's conventions. Gaps and errors are not corrected.
- **Cost model is crude.** 5bps per side + 200bps annual borrow on shorts. No market-impact model, no bid/ask, no capacity analysis.
- **No deployment.** There is no broker integration, no paper trading, no live signal generation. A good `oos_sharpe` in this repo is *not* a trade-ready signal — it is a hypothesis that survived one specific backtest.

If you want to use any idea that comes out of this loop for real money, you owe it a real point-in-time backtest, a real capacity/impact study, and a real live-trading sandbox. This repo does none of those things.

## License

MIT
