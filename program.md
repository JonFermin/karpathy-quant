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
4. **Verify data exists**: Check that `~/.cache/karpathy-quant-auto-research/prices_<UNIVERSE_TAG>.parquet` exists for the chosen universe (default `sp100_2024`). If not, tell the human to run `UNIVERSE_TAG=<tag> uv run prepare.py`.
5. **Initialize results.tsv**: Create `results.tsv` with just the header row. The baseline will be recorded after the first run.
6. **Confirm and go**: Confirm setup looks good.

Once you get confirmation, kick off the experimentation.

## Experimentation

Each experiment runs a vectorized daily-equity backtest, wrapped in a **5-minute wall-clock cap** (most backtests finish in seconds; the cap is a safety rail against runaway code). You launch it simply as: `uv run strategy.py`.

**What you CAN do:**
- Modify `strategy.py` — this is the only file you edit. Everything inside `generate_weights` is fair game: new signals, sizing, regime filters, rebalancing cadence, neutralization, etc.

**Available data** (loaders in `prepare.py`):

| Loader | Returns | Use case |
|---|---|---|
| `load_prices()` | adjusted close (date × ticker) | the canonical price frame; `run_backtest` already sees this |
| `load_open()` / `load_high()` / `load_low()` | adjusted OHL (date × ticker) | intraday range, gap analysis, OHLC-based realized vol (Garman-Klass) |
| `load_volume()` | split-adjusted share volume (date × ticker) | raw turnover signal — but for sizing prefer dollar volume |
| `load_dollar_volume()` | close × volume (date × ticker) | the canonical liquidity proxy; ADV-based gross caps, illiquid-name screens, liquidity-weighted sizing |
| `load_panel()` | dict of all six frames above | when you need multiple fields together |
| `load_market_proxy()` | SPY adjusted close (date,) | regime gates (drawdown from peak, 200d MA), beta-neutralization, excess-return residualization |

All frames share the same date index as `prices`. Common derived features:
- Overnight return = `load_open() / load_prices().shift(1) - 1` (news-driven gaps; large for biotech)
- Intraday return = `load_prices() / load_open() - 1` (vs overnight — they have different statistical properties)
- Daily range = `(load_high() - load_low()) / load_prices()` (more efficient daily vol estimator than close-to-close)
- Beta to market = rolling cov(asset_ret, market_ret) / var(market_ret) using `load_market_proxy()`

**What you CANNOT do:**
- Modify `prepare.py`. It is read-only. It contains the fixed evaluation, price loading, date slicing, cost model, hard constraints, and — crucially — the T+1 shift inside `run_backtest`. Do NOT pre-shift weights in your strategy; `run_backtest` does it for you, and double-shifting silently cripples your signal.
- Install new packages or add dependencies. You can only use what's already in `pyproject.toml`.
- Modify the evaluation. `run_backtest` + `print_summary` in `prepare.py` are the ground truth.
- Train or tune on the OOS slice. The IS/OOS split is trusted, not sandboxed — the honesty contract is that you do not inspect per-run OOS metrics and tune toward them. Form hypotheses on IS, then look at OOS as a verdict, not a gradient.

**The goal is simple: get the highest `oos_sharpe`, subject to hard constraints on `max_drawdown` (must be ≤ 0.35) and `turnover_annual` (must be ≤ 50.0).** A high Sharpe that violates either constraint is a `discard`, not a `keep`. Note that this is a *constrained* compare, not the monotone compare used in the upstream autoresearch loop: a run with higher Sharpe but a DD violation loses to a lower-Sharpe run that stays inside the box.

**Overfitting discipline.** The 20-trial cap exists because 580 knob-twists is indistinguishable from a random search — by trial N=500, the expected max Sharpe under the null swamps any plausible real edge. Prefer changes with *economic intuition* over parameter sweeps — a 5-line change with a thesis beats a grid-searched 10-hyperparam result. If a change improves OOS Sharpe but you can't articulate *why* the market would pay for that edge, you should be suspicious of it. Log the thesis in the description column with the literal prefix `thesis: ` so `grep '^thesis:' results.tsv` surfaces them for morning review. `log_result.py` enforces this for keep/discard rows.

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
fold_2014_2015:   0.612345
fold_2016_2017:   0.712345
fold_2018_2019:   0.562345
fold_2020_2021:   0.982345
fold_2022_2023:   0.742345
median_fold_sharpe: 0.712345
min_fold_sharpe:    0.562345
status_hint:      keep_eligible
```

`oos_sharpe_ci` is a 90% block-bootstrap interval. A 0.03 point-estimate improvement over `running_best` whose CI lower-bound is below `running_best` is almost certainly noise. `oos_sharpe_YYYY` decomposes the headline by year. The `fold_*` and `median_fold_sharpe`/`min_fold_sharpe` lines are the walk-forward view — a real edge should survive most folds, not depend on one 2-year regime.

Extract the headline metrics from the log file:

```
grep "^oos_sharpe\|^max_drawdown:\|^turnover_annual:\|^num_trades:" run.log
```

If the grep output is empty, the run crashed. `status_hint` is informational — `keep_eligible` / `force_discard` / `crash` — but the real keep/discard rule below is what you apply.

**Strict honesty mode (`SHOW_OOS=0`).** If you launch the experiment with `SHOW_OOS=0 uv run strategy.py`, OOS-derived lines are masked as `<hidden, SHOW_OOS=0>` in `run.log` and the full metrics go to a side-channel `oos_results.tsv` the reviewer reads in the morning. In this mode: form hypotheses on `is_sharpe`, use `status_hint` for pass/fail, and use `uv run running_best.py` to get a single number for the comparison. Do **not** `cat oos_results.tsv` during the loop — that defeats the whole point.

## Logging results (the grader, not you, decides the status)

You no longer choose `keep` / `discard` / `crash` yourself — the harness does. All you do is state your hypothesis:

```
uv run log_result.py "thesis: short one-line rationale for what I just tried"
```

`log_result.py` reads `oos_results.tsv` (the harness-owned audit trail), computes the status, writes the row to `results.tsv`, and exits with a code that tells you what to do next.

**Exit codes** — branch the loop on these:

| Code | Meaning                           | What to do |
|------|-----------------------------------|------------|
| 0    | row logged; status is on stdout   | Parse `status=keep\|discard` from the last stdout line. `keep` → advance. `discard` → `git reset --hard HEAD~1`. |
| 2    | description invalid (missing `thesis:` prefix, or contains tab/newline) | Fix the command and rerun — nothing was logged. |
| 3    | AST duplicate of a prior trial on this universe (any branch, checked against the shared trial cache) | You committed an AST-identical version of a hypothesis already tried. `git reset --hard HEAD~1` and pick a genuinely different thesis. Nothing was logged. |
| 4    | trial cap reached (default 20 per branch) | **Stop the loop.** Surface the branch's results.tsv for review. Do not raise the cap without a good reason — 20 is enough to select a real edge if one exists. |
| 5    | crash row logged (no `oos_results.tsv` row for this commit — the run never reached `print_summary`) | `git reset --hard HEAD~1`. Inspect `run.log`. |

The TSV has a header row and 6 columns — same schema as before, written by the grader:

```
commit	oos_sharpe	max_dd	turnover	status	description
```

Example:

```
commit	oos_sharpe	max_dd	turnover	status	description
a1b2c3d	0.423100	0.1823	5.23	keep	thesis: 12-1 momentum — baseline seed
b2c3d4e	0.512800	0.1902	8.71	keep	thesis: layering a 21d short-term reversal picks up the opposite effect at the short horizon
c3d4e5f	0.380200	0.1712	4.90	discard	thesis: widening to top quintile dilutes the signal — expected, confirmed
d4e5f6g	0.000000	0.0000	0.00	crash	attempted vol targeting — divide-by-zero on flat days
```

**The keep rule (computed by `log_result.py`, not you)** — a run is kept only if ALL of:

- `oos_sharpe > baseline + 0.15 + sr0(N)` (deflation term: expected max Sharpe under the null of no edge given the N trials on this branch)
- `oos_sharpe_ci_lo > baseline` (90% block-bootstrap lower bound)
- `median_fold_sharpe > baseline_median_fold + 0.10` (walk-forward robustness)
- `min_fold_sharpe > 0`
- `max_drawdown ≤ 0.35`
- `turnover_annual ≤ 50`
- `num_trades ≥ 50`

The baseline is the first non-crash row in `results.tsv` — **fixed once seeded**. The bar does not drift upward after each kept row; every subsequent run competes against the same anchor. If nothing clears this bar after 20 trials, that is a legitimate result.

## The experiment loop

The experiment runs on a dedicated branch (e.g. `quant-research/mar5`). You are capped at **20 trials per branch** (default `AUTORESEARCH_TRIAL_CAP=20`). If none of the 20 clears the baseline gate, that is a legitimate outcome — close the branch and report it.

Useful state probes (none of these show you per-run OOS):

```
uv run running_best.py              # best kept oos_sharpe so far (single number)
uv run running_best.py --baseline   # the seed row's oos_sharpe
uv run running_best.py --trials     # rows logged on this branch (cap awareness)
```

LOOP until the grader exits 4 (trial cap) or the human stops you:

1. Look at the git state: the current branch/commit we're on.
2. Tune `strategy.py` with an experimental idea by directly hacking the code. Frame the thesis *before* you edit — if you can't articulate why a market would pay for this edge, skip it.
3. `git commit` — a real code change. Comment/whitespace/docstring-only commits are auto-rejected.
4. Run the experiment: `uv run strategy.py > run.log 2>&1` (redirect everything — do NOT use tee or let output flood your context)
5. `grep "^oos_sharpe:\|^max_drawdown:\|^turnover_annual:\|^num_trades:" run.log` — if empty, the run crashed; `tail -n 50 run.log` to read the trace.
6. Log the run: `uv run log_result.py "thesis: <one-line rationale>"`. The grader computes the status; you don't.
7. Branch on the grader's exit code:
   - **0** — stdout ends with `status=keep` (advance the branch) or `status=discard` (`git reset --hard HEAD~1`).
   - **3** — AST-duplicate of a prior trial on this universe (any branch). `git reset --hard HEAD~1`, pick a genuinely different hypothesis.
   - **4** — trial cap. **Stop**. Summarize `results.tsv` for the human; the loop is done.
   - **5** — crash row written. `git reset --hard HEAD~1`. Look at `run.log` to learn from the failure before the next attempt.

You are a completely autonomous researcher. The grader is strict on purpose: it enforces a deflation-aware hurdle that accounts for the N trials you've run, so a "winner" has to actually clear that bar — not just point-estimate-beat the baseline.

**Mindset**: "nothing beat baseline" is the correct answer most of the time on a survivorship-biased 100-name universe. The trial cap is there to stop you before you've peeked so many times that the OOS window stops being OOS. If none of your 20 ideas cleared the gate, don't pad the count with micro-variants of the last near-miss — close the branch and report. Fewer, better hypotheses is the bar; the loop was re-designed to make that mandatory, not optional.

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
- **Liquidity conditioning** (uses `load_dollar_volume()`): screen out the bottom-quartile of 21d-avg dollar volume before signal selection (illiquid names dominate naive cross-sections); or weight by sqrt(ADV) so capacity-constrained names get less risk.
- **Overnight vs intraday split** (uses `load_open()`): the equity premium is famously concentrated overnight — a long signal from `open_t / close_{t-1} - 1` and a short signal from `close_t / open_t - 1` may have very different statistical properties. Test the two horizons separately before combining.
- **OHLC-based realized vol** (uses `load_high()`, `load_low()`): Garman-Klass `0.5*ln(H/L)^2 - (2*ln(2) - 1)*ln(C/O)^2` is a 5-7× more efficient daily vol estimator than close-to-close — useful as a denominator for risk-adjusted momentum or as a regime-gate input.
- **Beta neutralization** (uses `load_market_proxy()`): regress per-name returns on SPY returns over a rolling window; trade the residuals (idiosyncratic component) instead of total returns. Removes a chunk of common-factor noise without needing a full risk model.

Frame each idea with a one-line thesis *before* you run. If the thesis is "I have no idea, just trying stuff," reconsider.

**NEVER STOP EARLY**: Once the experiment loop has begun, do NOT pause to ask the human if you should continue. Do NOT ask "should I keep going?" or "is this a good stopping point?". The human might be asleep. You are autonomous until ONE of three things happens:

1. `log_result.py` exits 4 — the trial cap was reached. Summarize `results.tsv` for morning review and stop.
2. The human interrupts you.
3. You genuinely cannot think of a defensible hypothesis that isn't a micro-variant of something already tried. In that case, stop and write a one-paragraph summary of what was attempted. Do NOT fabricate a 19th trial just to fill the cap — a shorter branch with honest hypotheses is worth more than 20 knob-twists.

A user might leave you running while they sleep. With a 20-trial cap and ~1 minute per run, the loop is likely to finish in well under an hour — which means they wake up to a clean, complete branch rather than a 580-row churn log. That is the whole point of the redesign.
