---
name: quant-autoresearch
description: Use when the user asks to kick off / start / begin a new quant research experiment in this repo, run the autonomous strategy loop, or launch an overnight SHOW_OOS=0 run. Triggers on phrases like "kick off a new experiment", "start the autoresearch loop", "run program.md", "launch strict-honesty mode". Drives the program.md loop: edit strategy.py → commit → backtest → log_result.py → keep/discard, inside a dedicated git worktree on a fresh quant-research/<tag> branch (timestamped so parallel launches don't collide), in strict-honesty SHOW_OOS=0 mode, never stopping until the grader exits 4 or the human interrupts.
---

# quant-autoresearch

Kicks off an autonomous quant-strategy experiment loop in this repo per `program.md`. Strict-honesty `SHOW_OOS=0` mode. Runs inside a **dedicated git worktree** on a fresh `quant-research/<tag>` branch, where `<tag>` is **timestamped** `MMDD-HHMMSS` (e.g. `0419-223742`) so two experiments can run in parallel without stomping on each other. Numeric tags only — locale-independent and sortable. Never stops until the grader returns exit 4 (trial cap) or the human interrupts.

## Non-negotiable ground rules (do not violate)

- `strategy.py` is the ONLY file you edit. Everything inside `generate_weights()` is fair game.
- `prepare.py` is READ-ONLY. It already does `weights.shift(1)` inside `run_backtest` — do NOT pre-shift in `strategy.py`.
- `SHOW_OOS=0` means: do **not** `cat oos_results.tsv`, do **not** grep the OOS lines out of `run.log`, do **not** peek at per-year OOS. Form hypotheses on `is_sharpe` / `status_hint` / `running_best.py`. That is the whole point of strict-honesty mode.
- Never stop to ask "should I keep going?". The human may be asleep. Only three exits: grader returns 4, human interrupts, or you genuinely run out of defensible hypotheses (documented in a one-paragraph summary — not a 19th micro-variant).
- Never `git add results.tsv` or `oos_results.tsv` — both are gitignored by design.
- No new dependencies. No modifications to `prepare.py`, `log_result.py`, or `running_best.py`.

## Step 1 — Setup

You start in the repo root (the main checkout).

**First, resolve the universe.** If the launch prompt names a non-default universe (e.g. "on SP500", `UNIVERSE_TAG=sp500_2024`, or `/autoresearch sp500`), `export UNIVERSE_TAG=sp500_2024` **before** any preflight check, any loop command, and any helper invocation. Default is `sp100_2024`. Every helper (`strategy.py`, `log_result.py`, `running_best.py`, `prepare.py`) reads this env var at import time, so the export must persist for the whole session. See "Universe selection" below for the full rules.

Then run these checks in parallel:

```bash
git status
git rev-parse --abbrev-ref HEAD
ls ~/.cache/karpathy-quant-auto-research/prices_${UNIVERSE_TAG:-sp100_2024}.parquet
grep -q '^worktrees/' .gitignore && echo ok || echo "NEEDS worktrees/ in .gitignore"
```

Then:

1. **Pick a timestamped tag and export it**: numeric `MMDD-HHMMSS` from the current local time (e.g. `0419-223742`). Numeric only — locale-independent and sortable. The seconds suffix is what lets two concurrent skill launches coexist — do NOT drop it even if you're the only one running.
   ```bash
   TAG=$(date +%m%d-%H%M%S)
   git branch --list "quant-research/$TAG"   # must be empty; if not, append b/c/d as a collision bump
   export TAG
   ```
   `$TAG` is used throughout the rest of the skill — setup, loop, archive. Do not retype the literal value.
2. **Create a dedicated worktree on a fresh branch from master**:
   ```bash
   mkdir -p worktrees
   git worktree add -b "quant-research/$TAG" "worktrees/$TAG" master
   cd "worktrees/$TAG"
   ```
   Every subsequent command in the loop runs from **inside the worktree** (`worktrees/$TAG/`). `results.tsv`, `oos_results.tsv`, `run.log`, and the `strategy.py` edits all live there — so parallel experiments never touch each other's state. If the main working tree has uncommitted changes, that's fine (worktrees are independent) — but check that `worktrees/` is in `.gitignore` (see the grep check above). If it isn't, stop and tell the human to add it before proceeding; otherwise `git status` in the main tree will fill with worktree noise.
3. **Verify prices cache**: if `~/.cache/karpathy-quant-auto-research/prices_<tag>.parquet` is missing for the chosen `UNIVERSE_TAG` (default `sp100_2024`), stop and tell the human to run `UNIVERSE_TAG=<tag> uv run prepare.py`. Do not try to run it yourself — it re-downloads several MB from yfinance. Each universe has its own cache file (`prices_sp100_2024.parquet`, `prices_sp500_2024.parquet`, etc.), so universes can coexist on disk without swapping.
4. **Read context** (narrow — don't flood your window): `strategy.py` is ~50 lines, read it in full. `prepare.py` is 800+ lines; do NOT read it whole — `grep` for the specific constant or helper you need (e.g. `grep -n 'TIME_BUDGET_S\|MAX_DRAWDOWN_HARD' prepare.py`). `program.md` you've already read. `README.md`, `log_result.py`, and `running_best.py` only if a specific question arises; don't re-derive their rules from scratch.
5. **Baseline first**: the very first commit on this branch anchors the permanent baseline. Make a behavior-preserving algebraic rewrite (see "First iteration" note at the bottom) — do NOT put a real idea here. `results.tsv` does not need to be pre-seeded; `log_result.py` writes the header automatically on first append.

### Universe selection

The experiment loop defaults to `UNIVERSE_TAG=sp100_2024`. If the human names a different universe in the launch prompt (e.g. "on SP500", "with UNIVERSE_TAG=sp500_2024"):

- Verify `universe_<tag>.json` exists at the repo root.
- Verify `~/.cache/karpathy-quant-auto-research/prices_<tag>.parquet` exists. Each universe has its own cache file — no swapping needed. If missing, stop and tell the human to `UNIVERSE_TAG=<tag> uv run prepare.py` (no `--refresh` needed; fresh filename, no stale cache to fight). Do NOT re-download autonomously.
- Export `UNIVERSE_TAG=<tag>` on EVERY call to `strategy.py`, `log_result.py`, `running_best.py`, etc. — they all read it at import time.

### Parallel experiments

Two or more worktrees can run concurrently when each has a unique timestamped tag. But:

- Parallel runs on **different** `UNIVERSE_TAG`s are safe — each universe has its own cache file (`prices_<tag>.parquet`) so they don't contend. Same-universe parallel runs share the cache read-only, also safe.
- Each worktree has its own `results.tsv` / `oos_results.tsv` / `run.log`, so the grader and `running_best.py` see only that worktree's trials — they do NOT pool across parallel experiments. That's intentional: each run is a clean 20-trial branch.
- Don't reach into a sibling worktree's files from inside your loop. If the human wants to compare across parallel branches, that's a morning-review job.

## Step 2 — The loop

Run every command from **inside the worktree** (`worktrees/<tag>/`). Repeat until the grader exits 4 or the human interrupts:

```bash
# 1. Form a hypothesis (one line, economic intuition, not a knob-twist)
# 2. Edit strategy.py — real code change (comments/whitespace-only is auto-rejected)
git add strategy.py
git commit -m "<short imperative summary of the change>"

# 3. Backtest in strict-honesty mode — ALWAYS redirect, never tee/stream.
#    Include UNIVERSE_TAG if non-default.
SHOW_OOS=0 uv run strategy.py > run.log 2>&1
# (or: SHOW_OOS=0 UNIVERSE_TAG=sp500_2024 uv run strategy.py > run.log 2>&1)

# 4. Extract IS-only headline metrics (OOS lines will be masked <hidden, SHOW_OOS=0>)
grep "^is_sharpe:\|^max_drawdown:\|^turnover_annual:\|^num_trades:\|^status_hint:" run.log
# If empty → crash. tail -n 50 run.log to read the trace.

# 5. Log the row (grader writes status, not you).
#    CRITICAL: log_result.py leaks OOS-sensitive numbers on both streams:
#      - stdout: "logged: <commit> <oos_sharpe> <max_dd> <turnover> ..." (always written)
#      - stderr: "grader: <status> (oos_sharpe 0.4231 > hurdle 0.5912 ...)" (exit 0 ONLY)
#    Mute stdout to a shell var (grep out only the `status=` trailer).
#    Capture stderr to a file and surface it ONLY on non-zero exit —
#    exits 2/3/4 print safe diagnostics ("ERROR: trial cap reached", etc.)
#    that we need to see; exit 0's stderr is the OOS-leaking "grader:" line
#    and must stay hidden.
out=$(uv run log_result.py "thesis: <one-line rationale>" 2>_grader.err); rc=$?
echo "$out" | grep '^status=' || true
if [ "$rc" -ne 0 ]; then
  cat _grader.err >&2
fi
rm -f _grader.err
echo "exit=$rc"

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

# results.tsv is tab-separated (cols: commit oos_sharpe max_dd turnover status description).
# NEVER cat it whole and NEVER grep line-start — cols 2/3/4 leak OOS-sensitive numbers.
# Only read the commit (col 1) and description (col 6) via awk:
awk -F'\t' 'NR>1 {print $1, $6}' results.tsv          # full hypothesis history
awk -F'\t' 'NR>1 && $5=="keep" {print $1, $6}' results.tsv     # survivors so far
```

Do NOT run `cat oos_results.tsv` during the loop. Do NOT `grep oos_sharpe_2` or any per-year OOS. If you catch yourself about to peek, stop.

### First iteration (baseline)

`log_result.py` requires a real AST-level code change against `HEAD~1` (it strips docstrings before comparing, so docstring/whitespace/comment edits are rejected as exit 3 no-op). The baseline therefore needs a tiny commit that is **AST-different but behavior-identical** — anchoring on pure 12-1 momentum without altering any computed value.

**Recommended recipe: an algebraically-identical numeric rewrite inside `generate_weights`.** Pick one and commit it verbatim:

- `(ranks >= 0.9)` → `(ranks >= 1 - 0.1)` — different AST (`Constant` vs `BinOp`), identical value.
- `pct_change(252).shift(21)` → `pct_change(252).shift(21 + 0)` — adds a no-op arithmetic node.
- Introduce an unused local: `_baseline_anchor = 0` at the top of `generate_weights`, then leave everything else untouched.

**Avoid** anything that could shift even one output cell: don't change thresholds (`0.9` → `0.85`), don't reorder operations that might produce different float dust, don't add a "small" guard (a `dropna()` you didn't have before *does* change behavior on edge rows). The goal is a provably identical weight panel with a different AST.

**The first non-crash commit on the branch becomes the permanent baseline anchor.** Every subsequent keep is judged against it, not the running max. That means:

- Your first iteration must be **strategy-neutral** — do NOT put a real idea in trial #1. If it happens to score well by luck, the hurdle for every later idea is inflated forever.
- If trial #1 crashes (exit 5 → `git reset --hard HEAD~1`), trial #2 becomes the effective first trial and anchors the baseline. That's fine, but it means you get at most one retry before the anchor is locked — make trial #2 just as neutral.
- Do not try to "tune" the baseline by running variants until one feels right. The very first non-crash commit wins.

## Hypothesis discipline

- **Review prior theses before forming a new one.** Before editing `strategy.py`, run `awk -F'\t' 'NR>1 {print $1, $6}' results.tsv` (safe under SHOW_OOS=0 — commit + description only). Scan for what you've already tried. Because each discard resets to baseline, nothing stops you from re-exploring the same tiny region of idea-space twenty times; this review is the only thing that does.
- **Name the axis in the thesis line.** Every `thesis:` must declare which dimension of the design it moves along — signal family (trend / reversal / vol / quality / regime / composite), horizon (days / weeks / months / years), sizing (equal / inverse-vol / rank-tilted), rebalance cadence, or universe/leverage. Format: `thesis: [axis] <rationale>`, e.g. `thesis: [reversal/21d/equal/monthly] one-month losers revert via flow pressure`. Near-duplicates become visible at a glance; every new thesis should move on an axis that prior trials haven't saturated.
- Frame the thesis **before** editing. Write it as the `thesis:` line first; if you can't, skip the idea.
- Prefer changes with economic intuition (why a market would pay for this edge) over parameter sweeps.
- A 5-line change with a thesis beats a 10-hyperparam grid search. Simpler is better. Deleting code that works equally well is a win.
- "Nothing beat baseline" is the most likely correct outcome on a survivorship-biased 100-name universe. Do not pad the count to reach 20 — fewer honest hypotheses beats knob-twist churn.

## Idea seeds (from program.md — pick ones you can defend, don't sweep them)

Momentum variants (3-1 / 6-1 / 12-1; risk-adjusted; residual) · short-horizon reversal (5d / 21d) · z-score ranks vs decile cutoffs · sector / beta neutralization · inverse-vol sizing · regime gate (SPY drawdown or equal-weighted universe drawdown — no VIX in cache) · combination of two previously-kept signals with a complementarity thesis · long-only vs long-short · gross leverage / per-name caps.

## Stop conditions (the only three)

On a **graceful** stop (cases 1 and 3 below), run the **Archive + push + cleanup** sequence (next section) before returning to the human. On a human interrupt (case 2), do nothing — you can't clean up reliably mid-signal.

1. `log_result.py` returns exit 4 → trial cap reached. Print a one-screen summary: the worktree path, branch name, `UNIVERSE_TAG`, count of keep / discard / crash rows, best kept Sharpe from `running_best.py`, baseline from `running_best.py --baseline`, `thesis:` lines grouped by status. Then run **Archive + push + cleanup**.
2. Human interrupts (Ctrl-C or explicit "stop"). Leave the worktree and branch as-is; do not tidy up. The human has taken over.
3. You cannot articulate a defensible non-micro-variant hypothesis. Write a one-paragraph summary to chat (not to a file) explaining what's been tried and why you're stopping. Then run **Archive + push + cleanup**. Do NOT fabricate a filler trial.

## Archive + push + cleanup

`results.tsv` and `oos_results.tsv` are gitignored, so removing the worktree destroys them. The archive step folds their content into a committed **per-run** summary at `summaries/<tag>.md` so the branch on origin is self-describing. The path is tag-scoped — never a shared `SUMMARY.md` at the root — so parallel branches can be merged or compared without file-level conflicts. Do NOT maintain a rollup/index file in the loop; the morning-review step regenerates that on demand from the per-run files (see the hint at the bottom).

```bash
# (from inside worktrees/$TAG — $TAG exported back in Step 1)

# 0. Compute everything that goes into summaries/$TAG.md / commit message up-front.
#    No `<placeholder>` literals should survive past this block — if you see
#    `<...>` in the committed file, a substitution was missed.
BRANCH="quant-research/$TAG"
SUMMARY_PATH="summaries/$TAG.md"
UNIV="${UNIVERSE_TAG:-sp100_2024 (default)}"
BASELINE_LINE=$(uv run running_best.py --baseline --verbose 2>/dev/null || echo "n/a")
RUNNING_LINE=$(uv run running_best.py --verbose 2>/dev/null || echo "no kept rows")
TRIALS_LINE=$(uv run running_best.py --trials 2>/dev/null || echo "0")
N_KEEP=$(awk -F'\t' 'NR>1 && $5=="keep" {n++} END {print n+0}' results.tsv)
N_TRIAL=$(awk -F'\t' 'NR>1              {n++} END {print n+0}' results.tsv)
STOP_REASON="trial-cap"   # set manually: "trial-cap" | "no-defensible-hypothesis"

# 1. Build summaries/$TAG.md — capture the full audit trail in a committed file.
#    Per-run path (not SUMMARY.md) so parallel branches don't conflict on merge.
#    Build in pieces (NOT a single unquoted heredoc): thesis strings in results.tsv
#    are agent-authored and may contain `$(...)`, backticks, or `\` that would be
#    re-evaluated by bash inside `<<EOF`. Here they pass through cat/awk only.
mkdir -p summaries
{
  printf '# %s\n\n' "$BRANCH"
  printf -- '- **UNIVERSE_TAG**: %s\n' "$UNIV"
  printf -- '- **Baseline (seed)**: %s\n' "$BASELINE_LINE"
  printf -- '- **Running best**:   %s\n' "$RUNNING_LINE"
  printf -- '- **Trials logged**:  %s\n' "$TRIALS_LINE"
  printf -- '- **Stop reason**:    %s\n\n' "$STOP_REASON"
  printf '## results.tsv\n\n'
  printf '```\n'
  cat results.tsv
  printf '```\n\n'
  printf '## Theses by status\n\n'
  printf '### keep\n'
  awk -F'\t' 'NR>1 && $5=="keep"    {print "- " $6}' results.tsv
  printf '\n### discard\n'
  awk -F'\t' 'NR>1 && $5=="discard" {print "- " $6}' results.tsv
  printf '\n### crash\n'
  awk -F'\t' 'NR>1 && $5=="crash"   {print "- " $6}' results.tsv
} > "$SUMMARY_PATH"

# Sanity-check: no unresolved <...> placeholders snuck through.
if grep -q '<[a-z-]*>' "$SUMMARY_PATH"; then
  echo "ERROR: unresolved <placeholder> in $SUMMARY_PATH — fix before committing"
  grep -n '<[a-z-]*>' "$SUMMARY_PATH"
  exit 1
fi

# 2. Commit the summary.
git add "$SUMMARY_PATH"
git commit -m "summary: $BRANCH ($N_KEEP/$N_TRIAL)"

# 3. Push the branch — only if a remote exists. Do not force-push.
if git remote get-url origin >/dev/null 2>&1; then
  git push -u origin "$BRANCH" || echo "push failed — leaving worktree in place for manual recovery"
else
  echo "no origin remote — skipping push, leaving worktree in place"
fi

# 4. Only remove the worktree if the push succeeded (or no remote was expected).
#    If push failed, STOP and tell the human — do not silently lose the branch state.
cd ../..    # back to repo root
# Exact-match check — `grep -q origin/$BRANCH` would prefix-match a sibling
# branch (e.g. 0419-2237 vs 0419-223742) and nuke the wrong worktree.
if git rev-parse --verify --quiet "refs/remotes/origin/$BRANCH" >/dev/null; then
  git worktree remove "worktrees/$TAG"

  # 5. Branch on outcome:
  #    - real improvement kept (non-seed keep) → open a PR so the human reviews
  #      the candidate strategy (walk-forward + deflated Sharpe) before merge.
  #    - seed-only (no trial beat the hurdle) → delete the local branch ref.
  #      The branch stays on origin as an audit trail but doesn't clutter
  #      `git branch` locally. N_KEEP counts the seed, so N_KEEP > 1 is the test.
  if [ "$N_KEEP" -gt 1 ]; then
    if command -v gh >/dev/null 2>&1; then
      PR_BODY="Autoresearch run on \`$UNIV\` kept $((N_KEEP - 1)) non-seed improvement(s) across $N_TRIAL trials.

- Baseline: $BASELINE_LINE
- Running best: $RUNNING_LINE
- Full audit: \`summaries/$TAG.md\` on this branch

**Do NOT merge without review.** Before accepting: \`git checkout $BRANCH && uv run walkforward.py\`, then open \`analysis.ipynb\` to check deflated Sharpe. A green run here is a hypothesis, not a verdict — see README \"Where the self fooling still wins\"."
      gh pr create --base master --head "$BRANCH" \
        --title "autoresearch: $BRANCH ($((N_KEEP - 1)) improvements / $N_TRIAL trials)" \
        --body "$PR_BODY" \
        || echo "gh pr create failed — branch is on origin, open the PR manually"
    else
      echo "gh CLI not installed — $BRANCH is pushed; open PR manually at origin"
    fi
    echo "archived with PR: $BRANCH (real improvement, local branch kept for review)"
  else
    git branch -D "$BRANCH" 2>/dev/null \
      || echo "local branch $BRANCH not found (already cleaned or never checked out here)"
    echo "archived seed-only: $BRANCH pushed to origin, local branch removed"
  fi
else
  echo "worktree preserved at worktrees/$TAG — manual cleanup required"
fi
```

Rules:
- Never `--force` on push. If origin rejects (somehow the branch exists upstream), STOP and report — do not overwrite.
- Never `git worktree remove --force` if the remote is missing the commits; that loses work.
- Delete the local branch (`git branch -D "$BRANCH"`) **only** on seed-only runs — the origin copy is the audit trail, the local copy is dead weight. On real-keep runs the local branch stays so the human can `git checkout` it without refetching.
- Never force-push, never delete a branch on origin. Seed-only branches stay on origin as an audit trail of what didn't work.
- If there is no `origin` remote configured, skip push and preserve the worktree. Tell the human. Do NOT try to add a remote.
- If `gh` CLI isn't available, skip PR creation and say so. Do NOT try to install it.

## Morning-review hint for the human (do NOT act on this during the loop)

After the human wakes up and the cleanup has run, they review via the pushed branch:

```bash
git fetch origin
git log origin/quant-research/<tag> --oneline                  # trial commits + summary
git show origin/quant-research/<tag>:summaries/<tag>.md        # the full archived summary

# Cross-run rollup: generate on demand from the per-run files (not committed).
git for-each-ref --format='%(refname:short)' refs/remotes/origin/quant-research/ \
  | while read ref; do
      tag="${ref##*/}"
      git show "$ref:summaries/$tag.md" 2>/dev/null | head -10
      echo "---"
    done

# to sanity-check a specific kept commit:
git checkout <commit> && uv run walkforward.py
```

If the loop was Ctrl-C'd (stop condition 2), the worktree is still at `worktrees/<tag>/` and results.tsv / oos_results.tsv are intact there — review locally before deciding whether to archive.

Walk-forward is the human's job, not yours. You do not run `walkforward.py` inside the loop — it is a post-hoc OOS check.
