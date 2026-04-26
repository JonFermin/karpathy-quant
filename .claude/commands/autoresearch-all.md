---
description: Fan out autoresearch across all universes (sp100/sp400/sp500/sp600/ndx100/xbi_2026/xlk_2026/gdxj_2026) in parallel — one subagent per universe
argument-hint: [optional comma-separated subset] — e.g. sp100,sp500 — leave blank for all eight
---

Spawn parallel quant-autoresearch runs via the `quant-autoresearch-all` skill.

Arguments passed to this command: $ARGUMENTS

Interpretation:
- If `$ARGUMENTS` is empty, run all eight known universes: `sp100_2024`, `sp400_2024`, `sp500_2024`, `sp600_2024`, `ndx100_2024`, `xbi_2026`, `xlk_2026`, `gdxj_2026`.
- If `$ARGUMENTS` is a comma-separated list (e.g. `sp100,sp500`), run only those. Normalize bare tags (`sp500` → `sp500_2024`) by matching against `universe_*.json` in the repo root.

Follow the `quant-autoresearch-all` skill end-to-end:
1. Preflight — verify universe JSON and price caches exist; download any missing caches up front.
2. Assign unique `MMDD-HHMMSS` tags (one per universe) to avoid worktree collisions.
3. Spawn one `general-purpose` subagent per universe in parallel, each running the `quant-autoresearch` skill.
4. Aggregate results into a single cross-universe summary table when all complete.

Strict-honesty `SHOW_OOS=0` is always on. Do not stop until every subagent completes or the human interrupts.
