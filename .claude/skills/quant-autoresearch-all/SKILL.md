---
name: quant-autoresearch-all
description: Use when the user asks to run autoresearch across ALL universes (sp100, sp400, sp500, sp600, ndx100, xbi_2026, xlk_2026, gdxj_2026) or any multi-universe subset in parallel. Spawns one general-purpose subagent per universe, each running the `quant-autoresearch` skill end-to-end in its own git worktree with a pre-assigned unique timestamp tag. Default is all eight known universes; pass a comma-separated subset to narrow. Triggers on phrases like "all possible universes", "run autoresearch on all universes", "every universe in parallel", "sp100/sp400/sp500/sp600/ndx100/xbi/xlk/gdxj".
---

# quant-autoresearch-all

Fan out the `quant-autoresearch` skill across multiple universes in parallel. One subagent per universe, each with a pre-assigned unique timestamp tag so their worktrees don't collide. Strict-honesty `SHOW_OOS=0`. Each subagent runs the full 20-trial loop and archives to its own branch on origin.

## Default universes

Unless the invoker names a subset, run all eight:

- `sp100_2024` — large-cap US equities
- `sp400_2024` — mid-cap US equities
- `sp500_2024` — broad large-cap US equities
- `sp600_2024` — small-cap US equities
- `ndx100_2024` — Nasdaq 100 (mega-cap tech-heavy)
- `xbi_2026` — biotech (SPDR S&P Biotech ETF holdings, event-driven)
- `xlk_2026` — technology sector (SPDR Technology Select Sector ETF holdings)
- `gdxj_2026` — junior gold miners (VanEck Junior Gold Miners ETF holdings, commodity-linked)

The canonical list is whatever `universe_*.json` files are present in the repo root — if the human adds a new universe JSON + price cache, treat it as part of the default set going forward.

A subset can be passed as a comma-separated list (e.g. `sp100,sp500`). Normalize to the full `<tag>_<year>` form using the `universe_<tag>.json` files present in the repo root — if the bare name is ambiguous (e.g. `sp400` → `sp400_2024`), always prefer the most recent year present.

## Step 1 — Preflight

From the repo root (main checkout), verify:

```bash
git status                                    # should be clean-ish (worktrees/ is gitignored)
git rev-parse --abbrev-ref HEAD               # note the starting branch; worktrees branch from master
ls ~/.cache/karpathy-quant-auto-research/     # see which prices_<tag>.parquet files exist
ls universe_*.json                            # confirm all requested universes have a json
grep -q '^worktrees/' .gitignore && echo ok   # required — else parallel worktrees pollute main tree
```

**Missing price caches** — if any requested universe lacks `~/.cache/karpathy-quant-auto-research/prices_<tag>.parquet`, you have two choices:

1. Ask the human for permission to download (each missing universe takes 1–5 minutes of yfinance fetch).
2. If the launch prompt was explicit ("run all universes, download anything missing" or similar), download serially up front using `UNIVERSE_TAG=<tag> uv run prepare.py > /tmp/prep_<tag>.log 2>&1` (can be backgrounded in parallel — yfinance fetches are IO-bound and don't contend with each other in practice).

Do NOT spawn the autoresearch subagents until every requested universe has a cache. A subagent that hits a missing cache will waste a worktree + branch.

## Step 2 — Assign unique tags

The `quant-autoresearch` skill requires each run to have a unique numeric `MMDD-HHMMSS` tag, and two concurrent runs with the same tag will collide on the worktree path. Crucially, another Claude Code instance may be running this same skill simultaneously — so tags must be second-precision AND cross-checked against local branches, existing worktrees, AND origin refs before spawning.

Build N tags by incrementing the current epoch one second at a time, then formatting with GNU `date -d @<epoch>`:

```bash
git fetch origin --prune                          # pull remote branches so collision check sees sister CC instances
BASE_EPOCH=$(date +%s)
N=8                                               # replace with actual number of universes requested (default 8)
TAGS=()
for i in $(seq 0 $((N-1))); do
  TAGS+=("$(date -d "@$((BASE_EPOCH + i))" +%m%d-%H%M%S)")
done
# e.g. TAGS=(0421-212759 0421-212800 0421-212801 0421-212802 0421-212803)
# Minute/hour rollover is handled by date(1) — no manual carry logic needed.
```

Verify every candidate is free across all three collision surfaces:

```bash
COLLIDED=()
for TAG in "${TAGS[@]}"; do
  if git branch --list "quant-research/$TAG" | grep -q .; then COLLIDED+=("$TAG(local)"); fi
  if [ -d "worktrees/$TAG" ]; then COLLIDED+=("$TAG(worktree)"); fi
  if git ls-remote --heads origin "quant-research/$TAG" | grep -q .; then COLLIDED+=("$TAG(origin)"); fi
done
if [ ${#COLLIDED[@]} -gt 0 ]; then
  echo "COLLISION: ${COLLIDED[@]} — add 10s to BASE_EPOCH and retry"
  exit 1
fi
```

**If any collision:** bump `BASE_EPOCH=$((BASE_EPOCH + 10))`, regenerate TAGS, re-check. Typical cause is another CC instance launched within the same ~5-second window on the same universe set. 10-second bump clears it.

Do not drop the seconds suffix — the `quant-autoresearch` skill insists on full `MMDD-HHMMSS`, and the seconds are what make cross-instance invocation safe.

## Step 3 — Spawn parallel subagents

Spawn one `general-purpose` subagent per universe, all in a single message (multiple Agent tool calls in one response so they launch concurrently). Each subagent's prompt must be self-contained — it has no memory of this conversation.

Required prompt content per subagent (adapt fields in angle brackets):

- Path to the skill: `C:/Users/honsf/DEVELOP/karpathy-quant-auto-research/.claude/skills/quant-autoresearch/SKILL.md` — tell the subagent to **read it in full before starting**.
- Working directory: `C:\Users\honsf\DEVELOP\karpathy-quant-auto-research`.
- `UNIVERSE_TAG=<tag>_<year>` — emphasize it must be exported on every invocation of `strategy.py`, `log_result.py`, `running_best.py`, `prepare.py` (all read it at import time).
- The **pre-assigned** timestamp tag from Step 2 (e.g. `0421-070001`). State explicitly: "do not generate your own tag — it's been pre-assigned to avoid collisions with N parallel sister runs."
- Worktree path: `worktrees/<tag>`.
- Branch: `quant-research/<tag>`.
- `SHOW_OOS=0` reminder.
- Baseline iteration must be a behavior-preserving algebraic rewrite (e.g. `(ranks >= 0.9)` → `(ranks >= 1 - 0.1)`).
- Full "Archive + push + cleanup" on graceful stop.
- Windows cleanup note: the skill's Archive block falls back from `git worktree remove` (which routinely errors "Filename too long" / "Invalid argument" on MAX_PATH) to an unconditional `rm -rf worktrees/$TAG` once `origin/$BRANCH` is confirmed. Do NOT skip or short-circuit that fallback — leaving the directory stranded is no longer acceptable.
- Explicit isolation rule: do not reach into sibling worktrees; the other N-1 runs are concurrent.
- Ask for a brief end-of-run summary (branch, keep/trial counts, baseline oos_sharpe, running_best oos_sharpe, push status).

Spawn all agents with `run_in_background: true` so they run concurrently and you're notified as each finishes.

**Domain hints**: if a universe has known characteristics, pass a one-line hint to the relevant subagent (e.g. "xbi_2026 is biotech — highly event-driven, classic 12-1 momentum tends to work poorly; short-horizon reversal and regime-gating are more plausible edges; still form theses from economic intuition, not sweeps"). Keep it one sentence — don't over-specify, the subagent is autonomous.

## Step 4 — Aggregate

As each subagent reports completion, record: branch, baseline oos_sharpe, running_best oos_sharpe, keep/trial counts, push status. Do NOT Read the subagent's output JSONL file (it's the full transcript and will overflow context).

When all N are done, emit a single cross-universe summary table to the human:

```
| Universe | Baseline OOS Sharpe | Running Best | Branch |
|---|---|---|---|
| <tag>    | <baseline>           | <best>       | quant-research/<tag> |
...
```

Call out any universe where running_best > baseline (a trial cleared the hurdle — the interesting case). The typical outcome across all universes is 1 keep (baseline anchor) / 19 discards — this is the honest null result, not a failure.

## Step 5 — Worktree cleanup (handled by each subagent)

Each subagent runs the `quant-autoresearch` skill's **Archive + push + cleanup** block, which unconditionally `rm -rf`s its worktree directory once `origin/<branch>` is confirmed — `git worktree remove` is attempted first for metadata hygiene, but the forced filesystem removal is the real cleanup step (Windows' MAX_PATH routinely breaks the `git` variant). You should therefore expect `worktrees/` to be empty after all subagents report success.

If, after all subagents complete, any `worktrees/<tag>/` directory still exists:

- The only safe reason is that subagent's push to origin failed — meaning the worktree is the last copy of the work. Tell the human; do NOT `rm -rf` it yourself, and do NOT `git worktree prune` aggressively (that would desync the registry from the stranded work).
- Confirm with `git ls-remote --heads origin quant-research/<tag>` before considering any further action.

## Common pitfalls

- **Same-tag collisions**: if two subagents somehow get the same tag (e.g. spawned from distinct skill invocations or from a sister CC instance running this same skill), their `git worktree add` races. Step 2's second-precision epoch-increment scheme plus the three-surface collision check (local branch, worktree dir, origin ref) prevents this — but only if you actually `git fetch origin` first so the origin check sees sister-instance branches.
- **Downloading caches in parallel with running agents**: don't. A subagent that boots while its cache is still being written will see a partial parquet. Always finish all downloads before spawning.
- **Passing the skill content instead of a path**: the `quant-autoresearch` skill is ~270 lines. Pasting it into every subagent prompt wastes tokens. Just hand them the absolute path and tell them to read it.
- **Waiting synchronously**: do not sleep-poll for background agents. You are automatically notified when each completes — continue other work or respond to the user in the meantime.
- **Summarizing before all are done**: report each universe's result as its notification arrives. Produce the cross-universe table only after the last one reports.
