# karpathy-quant-auto-research

This is an experiment to have the LLM do its own quant strategy research.

## Setup

To set up a new experiment, work with the user to:

1. **Agree on a run tag**: propose a tag based on today's date (e.g. `mar5`). The branch `quant-research/<tag>` must not already exist — this is a fresh run.
2. **Create the branch**: `git checkout -b quant-research/<tag>` from current master.
3. **Read the in-scope files**: The repo is small. Read these files for full context:
   - `README.md` — repository context.
   - `prepare.py` — fixed constants, data loader, backtest engine, evaluation. Do not modify.
   - `strategy.py` — the file you modify. Signal generation → weight panel.
4. **Verify data exists**: Check that `~/.cache/karpathy-quant-auto-research/prices.parquet` exists. If not, tell the human to run `uv run prepare.py`.
5. **Initialize results.tsv**: Create `results.tsv` with just the header row. The baseline will be recorded after the first run.
6. **Confirm and go**: Confirm setup looks good.

Once you get confirmation, kick off the experimentation.

## Experimentation

Each experiment runs a vectorized daily-equity backtest, wrapped in a **5-minute wall-clock cap** (most backtests finish in seconds; the cap is a safety rail against runaway code). You launch it simply as: `uv run strategy.py`.

**What you CAN do:**
- Modify `strategy.py` — this is the only file you edit. Everything inside `generate_weights` is fair game: new signals, sizing, regime filters, rebalancing cadence, neutralization, etc.

**What you CANNOT do:**
- Modify `prepare.py`. It is read-only. It contains the fixed evaluation, price loading, date slicing, cost model, hard constraints, and — crucially — the T+1 shift inside `run_backtest`. Do NOT pre-shift weights in your strategy; `run_backtest` does it for you, and double-shifting silently cripples your signal.
- Install new packages or add dependencies. You can only use what's already in `pyproject.toml`.
- Modify the evaluation. `run_backtest` + `print_summary` in `prepare.py` are the ground truth.
- Train or tune on the OOS slice. The IS/OOS split is trusted, not sandboxed — the honesty contract is that you do not inspect per-run OOS metrics and tune toward them. Form hypotheses on IS, then look at OOS as a verdict, not a gradient.

**The goal is simple: get the highest `oos_sharpe`, subject to hard constraints on `max_drawdown` (must be ≤ 0.35) and `turnover_annual` (must be ≤ 50.0).** A high Sharpe that violates either constraint is a `discard`, not a `keep`. Note that this is a *constrained* compare, not the monotone compare used in the upstream autoresearch loop: a run with higher Sharpe but a DD violation loses to a lower-Sharpe run that stays inside the box.

**Overfitting discipline.** With 100 experiments, some high-Sharpe results will be luck. Prefer changes with *economic intuition* over parameter sweeps — a 5-line change with a thesis beats a grid-searched 10-hyperparam result. If a change improves OOS Sharpe but you can't articulate *why* the market would pay for that edge, you should be suspicious of it. Log the thesis in the description column with the literal prefix `thesis: ` so `grep '^thesis:' results.tsv` surfaces them for morning review. `log_result.py` enforces this for keep/discard rows.

**Simplicity criterion**: All else being equal, simpler is better. A small improvement that adds ugly complexity is not worth it. Conversely, removing something and getting equal or better results is a great outcome — that's a simplification win. When evaluating whether to keep a change, weigh the complexity cost against the improvement magnitude. A 0.05 Sharpe improvement that adds 30 lines of hacky code? Probably not worth it. A 0.05 Sharpe improvement from deleting code? Definitely keep.

**The first run**: Your very first run should always be to establish the baseline, so you will run `strategy.py` as is.

## Output format

Once the script finishes it prints a summary like this:

```
---
oos_sharpe:       1.234567
oos_sharpe_ci:    [0.812345, 1.623890]
is_sharpe:        1.456789
max_drawdown:     0.1823
annual_return:    0.1245
annual_vol:       0.0934
turnover_annual:  5.23
calmar:           0.6830
num_trades:       1247
backtest_seconds: 12.4
oos_sharpe_2020:  1.122334
oos_sharpe_2021:  0.998877
oos_sharpe_2022:  1.345678
oos_sharpe_2023:  1.211223
oos_sharpe_2024:  1.456789
status_hint:      keep_eligible
```

`oos_sharpe_ci` is a 90% block-bootstrap interval. A 0.03 point-estimate improvement over `running_best` whose CI lower-bound is below `running_best` is almost certainly noise. `oos_sharpe_YYYY` decomposes the headline by year — a strategy whose OOS Sharpe lives entirely in 2020 is very different from one that's flat-per-year.

Extract the headline metrics from the log file:

```
grep "^oos_sharpe\|^max_drawdown:\|^turnover_annual:\|^num_trades:" run.log
```

If the grep output is empty, the run crashed. `status_hint` is informational — `keep_eligible` / `force_discard` / `crash` — but the real keep/discard rule below is what you apply.

**Strict honesty mode (`SHOW_OOS=0`).** If you launch the experiment with `SHOW_OOS=0 uv run strategy.py`, OOS-derived lines are masked as `<hidden, SHOW_OOS=0>` in `run.log` and the full metrics go to a side-channel `oos_results.tsv` the reviewer reads in the morning. In this mode: form hypotheses on `is_sharpe`, use `status_hint` for pass/fail, and use `uv run running_best.py` to get a single number for the comparison. Do **not** `cat oos_results.tsv` during the loop — that defeats the whole point.

## Logging results

When an experiment is done, log it to `results.tsv` (tab-separated, NOT comma-separated — commas break in descriptions).

The TSV has a header row and 6 columns:

```
commit	oos_sharpe	max_dd	turnover	status	description
```

1. git commit hash (short, 7 chars)
2. `oos_sharpe` achieved (e.g. 1.234567) — use 0.000000 for crashes
3. `max_drawdown` as a fraction (e.g. 0.1823) — use 0.0 for crashes
4. `turnover_annual` (e.g. 5.23) — use 0.0 for crashes
5. status: `keep`, `discard`, or `crash` (lowercase)
6. short text description of what this experiment tried — include the thesis

Example:

```
commit	oos_sharpe	max_dd	turnover	status	description
a1b2c3d	0.423100	0.1823	5.23	keep	thesis: 12-1 momentum, 12m lookback with 1m skip harvests the momentum anomaly net of short-term reversal
b2c3d4e	0.512800	0.1902	8.71	keep	thesis: layering a 21d short-term reversal picks up the opposite effect at the short horizon
c3d4e5f	0.380200	0.1712	4.90	discard	thesis: widening to top quintile dilutes the signal — expected, confirmed
d4e5f6g	0.000000	0.0000	0.00	crash	attempt vol targeting, divide-by-zero on flat days
```

Prefer `uv run log_result.py <status> "thesis: ..."` — it reads run.log, formats the row correctly, and rejects keep/discard rows that are missing the `thesis:` prefix.

## The experiment loop

The experiment runs on a dedicated branch (e.g. `quant-research/mar5`).

LOOP FOREVER:

1. Look at the git state: the current branch/commit we're on.
2. Tune `strategy.py` with an experimental idea by directly hacking the code.
3. `git commit`
4. Run the experiment: `uv run strategy.py > run.log 2>&1` (redirect everything — do NOT use tee or let output flood your context)
5. Read out the results: `grep "^oos_sharpe:\|^max_drawdown:\|^turnover_annual:\|^num_trades:" run.log`
6. If the grep output is empty, the run crashed. Run `tail -n 50 run.log` to read the Python stack trace and attempt a fix. If you can't get things to work after more than a few attempts, give up.
7. Decide the status using the **keep rule**. Get the current best with `uv run running_best.py` (single number to stderr if no kept rows yet):
   - `keep` iff: `oos_sharpe > running_best` AND `oos_sharpe_ci_lo > running_best - 0.1` AND `max_drawdown ≤ 0.35` AND `turnover_annual ≤ 50.0` AND `num_trades ≥ 50`
   - `discard` if the run finished cleanly but fails the keep rule (including when OOS didn't improve, or when the CI lower bound is well below prior best — i.e. the "improvement" is inside the noise band)
   - `crash` if the grep was empty, any headline metric is NaN/inf, or the harness returned `status_hint=crash` with a `crash_reason`
8. Record the row in `results.tsv` (NOTE: do not commit the `results.tsv` file — leave it untracked by git)
9. If `keep`: advance the branch, keeping the git commit.
10. If `discard` or `crash`: `git reset --hard HEAD~1` back to where you started.

The idea is that you are a completely autonomous researcher trying things out. If they work, keep. If they don't, discard. And you're advancing the branch so that you can iterate. If you feel like you're getting stuck in some way, you can rewind but you should probably do this very very sparingly (if ever).

**Timeout**: Each backtest finishes in seconds under normal circumstances; the hard cap inside `run_backtest` is 5 minutes. If a run hangs past that, kill it and treat as crash.

**Crashes**: If a run crashes (a typo, missing import, divide-by-zero, shape mismatch), use your judgment: fix-and-retry for obvious bugs; skip-and-discard if the idea itself is fundamentally broken.

**Ideas when stuck** (framed as hypotheses, not a grid — pick ones you can defend):

- **Momentum variants**: different lookback (3-1, 6-1, 12-1); risk-adjusted momentum (return / vol); residual momentum (net of market beta).
- **Mean reversion**: short-horizon (5d, 21d) reversal overlay; bollinger-band style entries on oversold names.
- **Cross-sectional ranking**: soft scores (z-scores) instead of hard decile cutoffs; neutralize by sector or by market beta.
- **Volatility targeting**: scale positions by inverse realized vol so each name contributes equal risk.
- **Regime filter**: gate the whole book off when VIX level or SPY drawdown exceeds a threshold. (Note: if you don't have VIX in the cache, use a market-proxy drawdown from SPY if it's in the universe, or from the equal-weighted universe return.)
- **Combination**: weighted average of two previously-kept signals with a clear thesis for why they're complementary.
- **Sizing**: long-only vs long-short; gross-leverage limits; per-name weight caps.

Frame each idea with a one-line thesis *before* you run. If the thesis is "I have no idea, just trying stuff," reconsider.

**NEVER STOP**: Once the experiment loop has begun (after the initial setup), do NOT pause to ask the human if you should continue. Do NOT ask "should I keep going?" or "is this a good stopping point?". The human might be asleep, or gone from a computer and expects you to continue working *indefinitely* until you are manually stopped. You are autonomous. If you run out of ideas, think harder — read the baseline in `strategy.py` for new angles, try combining previous near-misses, try more radical changes. The loop runs until the human interrupts you, period.

As an example use case, a user might leave you running while they sleep. If each experiment takes about a minute (mostly backtest + git overhead) you can run ~60/hour, for ~300+ over an average human sleep. The user then wakes up to a morning of kept experiments to review.
