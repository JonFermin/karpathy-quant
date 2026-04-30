---
name: deep-autoresearch
description: Use when the user asks to run many parallel autoresearch experiments on the SAME universe to explore a wider hypothesis space — "deep autoresearch", "N parallel runs on sp500", "fan out 5 agents on sp100", "deep dive on ndx100", "run a bunch of experiments on xbi". Spawns N general-purpose subagents, all with the same UNIVERSE_TAG but distinct pre-assigned MMDD-HHMMSS tags, each executing the full `quant-autoresearch` skill (20-trial loop) in its own git worktree. Cross-branch AST dedup and pooled sigma_n/N deflation are already handled by `log_result.py`'s shared per-universe trial cache, so parallelism is safe by construction.
---

# deep-autoresearch

Parallelize the `quant-autoresearch` skill **within a single universe**. Sister skill to `quant-autoresearch-all` (which fans across universes, one agent each). Here we fan N agents across one universe to explore a wider hypothesis space — total effective trials = 20 × N, cross-branch AST-deduped and pooled for deflation via the shared `trial_cache_<UNIVERSE_TAG>.tsv`.

Strict-honesty `SHOW_OOS=0` applies to every subagent. Each subagent runs the full `quant-autoresearch` loop and archives to its own branch on origin.

## Arguments

Parse from the invocation:

- **Universe** (required). Accepts bare (`sp500`) or tagged (`sp500_2024`). Normalize to `<tag>_<year>` by checking `universe_<tag>.json` at repo root; prefer the most recent year present. Default `sp100_2024` if nothing named.
- **N** (default `5`, clamp to `[2, 20]`). Number of parallel subagents. Each runs a 20-trial branch.
- **Cap override** (optional). If the invoker says "deep + tall" or passes `TRIAL_CAP=<n>`, export `AUTORESEARCH_TRIAL_CAP=<n>` in every subagent's environment. Leave unset by default — 20 × N is usually plenty.

If either is ambiguous ("run a bunch of experiments on xbi" → N unclear), pick a reasonable default (N=5) and state it explicitly in the ack before spawning.

## Parallelism tradeoffs the invoker should know

State these once, in one or two sentences, before spawning — not after.

- **Deflation hurdle tightens over time.** `log_result.py` pools `sigma_n` and `N` across every non-crash trial on this universe (any branch). As agents finish and their rows pool in, the multiple-hypothesis hurdle (`expected_max_sharpe_null`) grows. Later-finishing branches face a taller bar than earlier ones — intentional, but expect the later cohort to report more discards.
- **AST collision rate rises with N.** All N agents explore ideas against the same shared cache. With N=5 on a small universe like SP100, expect 10–20% of trials to hit exit 3 (AST duplicate) — the agent resets and tries a different hypothesis. Not wasted, but counts against the 20-trial cap.
- **API concurrency.** N subagents run concurrently. Each is a full Claude loop doing edits + backtests. Don't set N > ~8 without reason — diminishing returns once AST collisions dominate.

## Step 1 — Preflight

From the repo root (main checkout):

```bash
git status                                    # should be clean-ish (worktrees/ is gitignored)
git rev-parse --abbrev-ref HEAD               # note the starting branch; worktrees branch from master
ls "universe_<tag>.json"                      # confirm the requested universe exists
ls ~/.cache/karpathy-quant-auto-research/prices_<tag>.parquet   # confirm cache
grep -q '^worktrees/' .gitignore && echo ok   # required — else parallel worktrees pollute main tree
```

**Missing cache** — stop and ask the human whether to `UNIVERSE_TAG=<tag> uv run prepare.py` up front (one download, all N agents share the read-only parquet). Do NOT spawn subagents if the cache is missing; each would separately try to deal with it and waste a worktree.

**Missing universe JSON** — stop; the human has mistyped the universe or it doesn't exist yet.

## Step 2 — Assign unique tags

The `quant-autoresearch` skill requires each run to have a unique numeric `MMDD-HHMMSS` tag, and two concurrent runs with the same tag collide on the worktree path. Pre-assign N tags with small second-offsets:

```bash
BASE_MINUTE=$(date +%m%d-%H%M)                # e.g. 0421-1530
# Build N tags: "${BASE_MINUTE}01" ... "${BASE_MINUTE}NN"
# For N > 59, wrap into the next minute — but you should not be at N > 59.
```

Verify none of the candidate branches already exist:

```bash
for TAG in "${TAGS[@]}"; do
  if git branch --list "quant-research/$TAG" | grep -q .; then
    echo "COLLISION on $TAG — increment minute base and retry"
    exit 1
  fi
done
```

If any collision (previous minute's deep-autoresearch left stragglers), increment the minute base and retry. Do not drop the seconds suffix.

## Step 3 — Spawn parallel subagents

Spawn N `general-purpose` subagents in a single message (multiple Agent tool calls in one response so they launch concurrently). All agents use the SAME `UNIVERSE_TAG`; each gets a distinct pre-assigned tag.

Required prompt content per subagent (identical template for all N — only `TAG` varies):

- Path to the skill: `C:/Users/honsf/DEVELOP/karpathy-quant-auto-research/.claude/skills/quant-autoresearch/SKILL.md` — read in full before starting.
- Working directory: `C:\Users\honsf\DEVELOP\karpathy-quant-auto-research`.
- `UNIVERSE_TAG=<tag>_<year>` — must be exported on every invocation of `strategy.py`, `log_result.py`, `running_best.py`, `prepare.py`.
- The **pre-assigned** timestamp tag. State explicitly: "do not generate your own tag — it's been pre-assigned to avoid collisions with N−1 parallel sister runs **on the same universe**."
- Worktree path: `worktrees/<tag>`.
- Branch: `quant-research/<tag>`.
- `SHOW_OOS=0` reminder.
- Baseline iteration must be a behavior-preserving algebraic rewrite (e.g. `(ranks >= 0.9)` → `(ranks >= 1 - 0.1)`).
- **Same-universe cohort note (unique to this skill)**: "N−1 sister runs are exploring this same universe concurrently. The shared `trial_cache_<UNIVERSE_TAG>.tsv` deduplicates AST across all of them — if `log_result.py` returns exit 3, your hypothesis collided with a sister run, not your own prior trial. `git reset --hard HEAD~1` and pick a genuinely different axis from the thesis list (see `quant-autoresearch` skill's hypothesis discipline section)."
- Full "Archive + push + cleanup" on graceful stop.
- Windows cleanup note: the skill's Archive block falls back from `git worktree remove` to unconditional `rm -rf worktrees/$TAG` once `origin/$BRANCH` is confirmed — do NOT skip.
- Explicit isolation rule: do not reach into sibling worktrees.
- Ask for a brief end-of-run summary (branch, keep/trial counts, baseline oos_sharpe, running_best oos_sharpe, count of exit-3 AST collisions observed, push status).

Spawn all subagents with `run_in_background: true` so they run concurrently and you're notified as each finishes.

## Step 4 — Aggregate

As each subagent reports, record: branch, baseline oos_sharpe, running_best oos_sharpe, keep/trial counts, exit-3 count, push status. Do NOT Read subagent output JSONL files — they overflow context.

When all N are done, emit a single cohort summary table to the human:

```
Deep autoresearch on <UNIVERSE_TAG> — N=<N> parallel runs

| Branch                         | Baseline OOS | Running Best | Keeps | Trials | AST collisions |
|---|---|---|---|---|---|
| quant-research/<tag_1>         | <baseline>   | <best>       | <k>   | <t>    | <c>            |
| quant-research/<tag_2>         | ...          | ...          | ...   | ...    | ...            |
...

Total non-baseline keeps across cohort: <N>
Best oos_sharpe in cohort:              <value> (branch quant-research/<tag>)
```

Call out any branch where `running_best > baseline + 0.15` (a trial cleared the hurdle — the interesting case). The typical cohort outcome on a survivorship-biased universe is 0–1 non-baseline keeps across all N branches; more than 2 is noteworthy and the human should walk-forward each before trusting.

## Step 5 — Worktree cleanup

Each subagent runs the `quant-autoresearch` skill's Archive + push + cleanup block. Expect `worktrees/` to be empty after all subagents succeed.

If any `worktrees/<tag>/` remains after completion, the push to origin failed for that agent — tell the human, do NOT `rm -rf` yourself, and do NOT `git worktree prune` aggressively. Confirm with `git ls-remote --heads origin quant-research/<tag>`.

## Common pitfalls

- **Spawning before the cache exists**: a missing `prices_<tag>.parquet` will cause every one of N subagents to waste a worktree. Finish the download first.
- **Picking N > 8 without reason**: AST collisions dominate, diminishing returns. If the human wants more throughput, prefer raising `AUTORESEARCH_TRIAL_CAP` over raising N — same cross-branch dedup, fewer concurrent processes.
- **Reusing the same minute base across back-to-back invocations**: if the human runs `/deep-autoresearch` twice within the same minute, the second invocation's tag candidates collide with the first's. The Step 2 collision check catches this — bump the minute base, don't force through.
- **Conflating with `quant-autoresearch-all`**: that skill fans ONE agent per universe across N universes (different `UNIVERSE_TAG` each). This skill fans N agents within ONE universe (same `UNIVERSE_TAG`). If the human says "deep run on all universes", that's `deep-autoresearch` × `autoresearch-all` — ask whether they mean N per universe (expensive) or just the `autoresearch-all` default.
- **Waiting synchronously**: you're notified when background agents complete — do not sleep-poll.
- **Summarizing before all are done**: report each branch as its notification arrives; the cohort table comes only after the last one.
