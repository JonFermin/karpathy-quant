# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

Autonomous quant strategy research loop for daily US equities. An agent edits one file (`strategy.py`), runs a backtest, lets a grader (`log_result.py`) decide keep/discard, and repeats — capped at 20 trials per branch. The canonical agent instructions live in `program.md`; the `README.md` covers design rationale and the honest list of where the loop still fools you. **Read `program.md` before starting any experiment loop.** This `CLAUDE.md` is the short orientation; `program.md` is the contract.

## The ground rules

- **`strategy.py` is the ONLY file the agent edits.** Everything inside `generate_weights()` is fair game.
- **`prepare.py` is READ-ONLY.** It owns the constants, data loader, cost model, hard constraints, and — critically — the `weights.shift(1)` T+1 execution shift inside `run_backtest`. Do NOT pre-shift in `strategy.py`; double-shifting silently cripples the signal. `test_lookahead.py` regression-tests the shift.
- **The grader, not the agent, decides status.** The agent runs `uv run log_result.py "thesis: <one-liner>"` and branches on its exit code (see below). The agent does NOT inspect OOS metrics under `SHOW_OOS=0`, does NOT cat `oos_results.tsv` or the trial cache, and does NOT pick `keep`/`discard`/`crash` itself.
- **Form hypotheses on IS; OOS is a verdict, not a gradient.** No tuning toward OOS; no peeking at per-year OOS lines in `run.log`.
- **No new dependencies** beyond `pyproject.toml` (`numpy`, `pandas`, `pyarrow`, `yfinance`, `matplotlib`, `jupyter`).

## What is and isn't gitignored

Tracked: `CLAUDE.md`, `program.md`, `README.md`, `prepare.py`, `strategy.py`, `log_result.py`, `running_best.py`, `walkforward.py`, `null_test.py`, `sensitivity.py`, `cross_universe.py`, `stats.py`, `analysis.ipynb`, `test_lookahead.py`, `universe_*.json`, `summaries/<tag>.md` (per-run audit), and `.claude/{commands,skills}/`.

Gitignored (per `.gitignore`): `results.tsv`, `run.log`, `oos_results.tsv` (+ `.old*` migration backups), `null_results_*.json`, `sensitivity_results_*.json`, `worktrees/`, `AGENTS.md`, `dev/`, `.venv/`. Do NOT `git add` any of these — the autoresearch skill explicitly relies on them being untracked so per-run worktrees don't collide.

## Commands

```bash
uv sync                                       # install deps
uv run prepare.py                             # one-time price download for $UNIVERSE_TAG
UNIVERSE_TAG=sp500_2024 uv run prepare.py     # different universe → different cache file
uv run prepare.py --refresh                   # force re-download

# Single backtest. ALWAYS redirect — do not tee or stream into context.
SHOW_OOS=0 uv run strategy.py > run.log 2>&1

# Headline metrics (under SHOW_OOS=0, OOS-derived lines render as "<hidden, SHOW_OOS=0>").
grep "^is_sharpe:\|^max_drawdown:\|^turnover_annual:\|^num_trades:\|^status_hint:" run.log
tail -n 50 run.log                            # if grep is empty → crash; read the trace

# Submit a row to the grader (the only way to write results.tsv).
uv run log_result.py "thesis: <one-line rationale, axis-tagged>"

# Loop-state probes (safe under SHOW_OOS=0):
uv run running_best.py                        # best kept oos_sharpe so far
uv run running_best.py --baseline             # the seed row's oos_sharpe
uv run running_best.py --trials               # rows on this branch (cap awareness)
```

`log_result.py` exit codes drive the loop:

| code | meaning | what to do |
|------|---------|------------|
| 0 | row logged; stdout ends with `status=keep` or `status=discard` | parse and act — `keep` advances; `discard` → `git reset --hard HEAD~1` |
| 2 | description invalid (missing `thesis:` prefix, or contains tab/newline) | fix the command and rerun; nothing was logged |
| 3 | AST duplicate of a prior trial on this universe (any branch, via shared cache) | `git reset --hard HEAD~1`; pick a genuinely different hypothesis |
| 4 | trial cap reached (default 20 / `AUTORESEARCH_TRIAL_CAP`) | **stop** the loop; summarize for review |
| 5 | crash row logged (run never reached `print_summary`) | `git reset --hard HEAD~1`; inspect `run.log` |

The grader's keep rule (computed by `log_result.py`, not the agent) requires ALL of: `oos_sharpe > baseline + 0.15 + sr0(N)` (deflation), `oos_sharpe_ci_lo > baseline`, `median_fold_sharpe > baseline_median_fold + 0.10`, `min_fold_sharpe > 0`, `max_drawdown ≤ 0.35`, `turnover_annual ≤ 50`, `num_trades ≥ 50`. The baseline is the first non-crash row and is **fixed once seeded** — every subsequent run competes against the same anchor.

## On-disk state

All caches live **outside** the repo at `~/.cache/karpathy-quant-auto-research/`:

- `prices_<UNIVERSE_TAG>.parquet` — per-universe price panel (so universes coexist without swapping).
- `trial_cache_<UNIVERSE_TAG>.tsv` — shared cross-branch trial cache. `log_result.py` writes every trial here (AST hash + OOS Sharpe + status), reads it to (a) reject AST duplicates from any prior trial on this universe (exit 3) and (b) pool `sigma_n` / `N` for the deflation hurdle. **Harness-side only — the agent must not cat or grep it; it leaks OOS-sensitive numbers.** To retire a universe's accumulated exploration history, `rm` the file.

Inside the repo: `oos_results.tsv` is the harness-owned audit trail (also OOS-leaking — never cat under SHOW_OOS=0). `results.tsv` is the agent-visible 6-col log (`commit oos_sharpe max_dd turnover status description`); cols 2/3/4 leak OOS, so even `results.tsv` should only be read via `awk -F'\t' 'NR>1 {print $1, $6}'` (commit + thesis only).

## Universes

Each universe = a frozen `universe_<tag>.json` ticker list + its own parquet cache. Switch with `UNIVERSE_TAG=<tag>` on every command (it's read at import time):

| tag | names | character |
|-----|-------|-----------|
| `sp100_2024` *(default)* | 100 | S&P 100 mega-caps. Most efficient; hardest to beat; moderate survivorship bias. |
| `sp500_2024` | 503 | S&P 500. Sanity-check vs SP100. |
| `sp400_2024` | 400 | S&P MidCap 400. Less coverage; bigger survivorship bias (mid caps churn). |
| `sp600_2024` | 603 | S&P SmallCap 600. Least efficient cap-based; worst SP-family survivorship. |
| `ndx100_2024` | 101 | Nasdaq 100. Tech/growth-concentrated. |
| `xbi_2026` | 148 | XBI biotech ETF holdings. Sector universe; binary trial / FDA-driven; worst survivorship in the repo. |
| `xlk_2026` | ~70 | XLK tech-sector ETF holdings. |
| `gdxj_2026` | ~50 | GDXJ junior gold miners. |

`prepare.py` carries per-universe overrides (e.g. `_BORROW_BPS_BY_UNIVERSE` raises borrow cost for thinner universes; `IMPACT_BPS_SLOPE` env var enables vol-scaled per-name impact). Defaults preserve backwards compatibility with cached Sharpes.

## Backtest contract (what `run_backtest` enforces)

- IS: 2010-01-01 → 2019-12-31. OOS: 2020-01-01 → 2024-12-31.
- `weights` shape: `(date × ticker)`, row sums = gross leverage, negatives = shorts.
- Costs: `COST_BPS = 5` per side on `|Δw|`; per-universe annual borrow on short exposure (default 200 bps); optional `IMPACT_BPS_SLOPE` for vol-scaled impact.
- Hard constraints → `force_discard`: `max_drawdown > 0.35` OR `turnover_annual > 50`. `num_trades < MIN_TRADES (50)` → `crash`.
- `status_hint` is informational only; the real status comes from `log_result.py`.
- `TIME_BUDGET_S = 300` wall-clock cap inside `run_backtest`.

## Output format (what `print_summary` emits)

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
oos_sharpe_2020:  1.122334    # ... per-year through 2024
fold_2014_2015:   0.612345    # ... walk-forward folds
median_fold_sharpe: 0.712345
min_fold_sharpe:    0.562345
status_hint:      keep_eligible | force_discard | crash
```

Under `SHOW_OOS=0`, every OOS-derived line above (the headline `oos_sharpe`, `oos_sharpe_ci`, all `oos_sharpe_YYYY`, all `fold_*`, `median_fold_sharpe`, `min_fold_sharpe`) is replaced with `<hidden, SHOW_OOS=0>`; `is_sharpe`, `max_drawdown`, `turnover_annual`, `num_trades`, `status_hint`, and `backtest_seconds` stay visible. The full numbers go to `oos_results.tsv` for the human reviewer. Empty grep output ⇒ the run crashed before reaching `print_summary`.

## How a fresh experiment is launched

The repo ships skills/commands under `.claude/`:

- **`/autoresearch [universe]`** (skill: `quant-autoresearch`) — creates a timestamped worktree at `worktrees/MMDD-HHMMSS/`, branches `quant-research/<tag>` off master, exports `SHOW_OOS=0`, runs the 20-trial loop, archives a per-run `summaries/<tag>.md`, pushes to origin, and (on real-keep runs) opens a PR. Default universe `sp100_2024`.
- **`/autoresearch-all [csv]`** (skill: `quant-autoresearch-all`) — fans the above across multiple universes in parallel, one subagent per universe, each with a unique pre-assigned tag.
- **`deep-autoresearch`** — fans N agents across the **same** universe; cross-branch AST dedup + pooled deflation are handled by the shared trial cache, so parallelism is safe by construction.

Agents launched outside a skill should still respect the worktree pattern (one `quant-research/<tag>` branch per session, isolated under `worktrees/<tag>/`) so concurrent runs don't stomp on each other's `results.tsv` / `run.log` / strategy edits.

## Auxiliary scripts (read-only, run in morning review — not inside the loop)

- `walkforward.py` — re-evaluates the currently-checked-out `strategy.py` on five non-overlapping 2yr folds. Runs OOS by definition; never invoke during a `SHOW_OOS=0` loop.
- `null_test.py`, `sensitivity.py` — per-commit null-distribution + parameter-sensitivity audits; outputs `null_results_<commit>.json` / `sensitivity_results_<commit>.json` (gitignored).
- `cross_universe.py` — cross-universe replication of a strategy.
- `stats.py` — `expected_max_sharpe_null` (the deflation `sr0(N)` term) and `jobson_korkie_memmel` (Sharpe-difference test). Imported by `log_result.py`.
- `analysis.ipynb` — review notebook; deflated Sharpe lives here.

## NEVER STOP EARLY

Once the experiment loop has begun, do not pause to ask the human if you should continue. The only valid stop conditions are: `log_result.py` exit 4 (trial cap), human interrupt, or genuine inability to articulate a non-micro-variant hypothesis (in which case write a one-paragraph summary and stop — do not fabricate filler trials). 20 honest hypotheses beat 580 knob-twists; that's the whole point of the cap.
