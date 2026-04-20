---
name: quant-autoresearch
description: Use when the user asks to kick off / start / begin a new quant research experiment in this repo, run the autonomous strategy loop, or launch an overnight SHOW_OOS=0 run. Triggers on phrases like "kick off a new experiment", "start the autoresearch loop", "run program.md", "launch strict-honesty mode". Drives the program.md loop: edit strategy.py → commit → backtest → log_result.py → keep/discard, on a fresh quant-research/<tag> branch, in strict-honesty SHOW_OOS=0 mode, never stopping until the grader exits 4 or the human interrupts.
---

# quant-autoresearch

Kicks off an autonomous quant-strategy experiment loop in this repo per `program.md`. Strict-honesty `SHOW_OOS=0` mode. Runs on a fresh `quant-research/<tag>` branch. Never stops until the grader returns exit 4 (trial cap) or the human interrupts.

## Non-negotiable ground rules (do not violate)

- `strategy.py` is the ONLY file you edit. Everything inside `generate_weights()` is fair game.
- `prepare.py` is READ-ONLY. It already does `weights.shift(1)` inside `run_backtest` — do NOT pre-shift in `strategy.py`.
- `SHOW_OOS=0` means: do **not** `cat oos_results.tsv`, do **not** grep the OOS lines out of `run.log`, do **not** peek at per-year OOS. Form hypotheses on `is_sharpe` / `status_hint` / `running_best.py`. That is the whole point of strict-honesty mode.
- Never stop to ask "should I keep going?". The human may be asleep. Only three exits: grader returns 4, human interrupts, or you genuinely run out of defensible hypotheses (documented in a one-paragraph summary — not a 19th micro-variant).
- Never `git add results.tsv` or `oos_results.tsv` — both are gitignored by design.
- No new dependencies. No modifications to `prepare.py`, `log_result.py`, or `running_best.py`.

## Step 1 — Setup

Run these checks in parallel:

```bash
git status
git rev-parse --abbrev-ref HEAD
ls ~/.cache/karpathy-quant-auto-research/prices.parquet
```

Then:

1. **Pick a tag**: propose `<month-abbrev><day>` from today's date (e.g. `apr19`). Verify `git branch --list quant-research/<tag>` is empty. If it exists, bump the tag (`apr19b`, `apr19c`, …).
2. **Fresh branch from master**: `git checkout master && git checkout -b quant-research/<tag>`. If the working tree has uncommitted changes, stop and tell the human — do not blow them away.
3. **Verify prices cache**: if `~/.cache/karpathy-quant-auto-research/prices.parquet` is missing, stop and tell the human to `uv run prepare.py`. Do not try to run it yourself — it re-downloads several MB from yfinance.
4. **Seed `results.tsv`** with just the header row if it is absent or not header-only:
   ```
   commit	oos_sharpe	max_dd	turnover	status	description
   ```
   (tab-separated, no trailing newline weirdness). Do NOT stage or commit it.
5. **Read context**: `README.md`, `prepare.py`, `strategy.py`. You've already read `program.md` (that's why you're here). Skim `log_result.py` and `running_best.py` only if you need to confirm an exit-code detail — don't re-derive the rules, they're in `program.md`.
6. **Baseline run FIRST**: do not edit `strategy.py` yet. The very first run of the branch is the baseline commit-free run to seed `oos_results.tsv`. Follow the loop below with a trivial identity-commit path — see "First iteration" note at the bottom.

## Step 2 — The loop

Repeat until the grader exits 4 or the human interrupts:

```bash
# 1. Form a hypothesis (one line, economic intuition, not a knob-twist)
# 2. Edit strategy.py — real code change (comments/whitespace-only is auto-rejected)
git add strategy.py
git commit -m "<short imperative summary of the change>"

# 3. Backtest in strict-honesty mode — ALWAYS redirect, never tee/stream
SHOW_OOS=0 uv run strategy.py > run.log 2>&1

# 4. Extract IS-only headline metrics (OOS lines will be masked <hidden, SHOW_OOS=0>)
grep "^is_sharpe:\|^max_drawdown:\|^turnover_annual:\|^num_trades:\|^status_hint:" run.log
# If empty → crash. tail -n 50 run.log to read the trace.

# 5. Log the row (grader writes status, not you)
uv run log_result.py "thesis: <one-line rationale>"
echo "exit=$?"

# 6. Branch on exit code:
#    0 → parse "status=keep" or "status=discard" from last stdout line
#        keep    → advance (do nothing, next iteration starts from this HEAD)
#        discard → git reset --hard HEAD~1
#    2 → description invalid. Fix the command and rerun log_result.py.
#        Nothing was logged; do NOT reset.
#    3 → no-op commit (AST-equal to HEAD~1). git reset --hard HEAD~1.
#        Do not retry the same non-change.
#    4 → TRIAL CAP. Stop. Summarize results.tsv for morning review.
#    5 → crash row written. git reset --hard HEAD~1. tail -n 50 run.log,
#        learn, then try a different idea (or fix the bug if obvious).
```

### Probing state between iterations (all safe under SHOW_OOS=0)

```bash
uv run running_best.py              # single number: best kept oos_sharpe so far
uv run running_best.py --baseline   # seed row's oos_sharpe
uv run running_best.py --trials     # rows on this branch (cap awareness)
git log --oneline -10               # recent experiment commits
grep '^thesis:' results.tsv         # scan your hypothesis history
grep '^keep' results.tsv            # survivors so far
```

Do NOT run `cat oos_results.tsv` during the loop. Do NOT `grep oos_sharpe_2` or any per-year OOS. If you catch yourself about to peek, stop.

### First iteration (baseline)

`log_result.py` requires a real code change against `HEAD~1`, so the baseline needs a tiny scaffolding commit to anchor it. Make the first iteration a genuine minimal tweak — e.g. a single-line guard, a rename, a clarifying refactor — then run the full loop above. This produces the first `oos_results.tsv` row that becomes the fixed baseline anchor. Subsequent keeps are judged against this anchor, not the running max.

## Hypothesis discipline

- Frame the thesis **before** editing. Write it as the `thesis:` line first; if you can't, skip the idea.
- Prefer changes with economic intuition (why a market would pay for this edge) over parameter sweeps.
- A 5-line change with a thesis beats a 10-hyperparam grid search. Simpler is better. Deleting code that works equally well is a win.
- "Nothing beat baseline" is the most likely correct outcome on a survivorship-biased 100-name universe. Do not pad the count to reach 20 — fewer honest hypotheses beats knob-twist churn.

## Idea seeds (from program.md — pick ones you can defend, don't sweep them)

Momentum variants (3-1 / 6-1 / 12-1; risk-adjusted; residual) · short-horizon reversal (5d / 21d) · z-score ranks vs decile cutoffs · sector / beta neutralization · inverse-vol sizing · regime gate (SPY drawdown or equal-weighted universe drawdown — no VIX in cache) · combination of two previously-kept signals with a complementarity thesis · long-only vs long-short · gross leverage / per-name caps.

## Stop conditions (the only three)

1. `log_result.py` returns exit 4 → trial cap reached. Print a one-screen summary: count of keep / discard / crash rows, best kept Sharpe from `running_best.py`, baseline from `running_best.py --baseline`, a list of the `thesis:` lines grouped by status. Exit the loop cleanly.
2. Human interrupts (Ctrl-C or explicit "stop"). Leave the branch as-is; do not tidy up.
3. You cannot articulate a defensible non-micro-variant hypothesis. Write a one-paragraph summary to chat (not to a file) and stop. Do NOT fabricate a filler trial.

## Morning-review hint for the human (do NOT act on this during the loop)

After the human wakes up, they will typically run:

```bash
cat results.tsv
grep '^keep' results.tsv
# for each kept commit the human wants to sanity-check:
git checkout <commit> && uv run walkforward.py
```

That walk-forward check is the human's job, not yours. You do not run `walkforward.py` inside the loop — it is a post-hoc OOS check.
