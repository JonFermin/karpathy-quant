# karpathy-quant-auto-research

Andrej Karpathy made a repo called [autoresearch](https://github.com/karpathy/autoresearch) where an AI agent edits one file, runs an experiment, keeps the change if it improved a score, and tries again. He used it for tweaking small language models. This repo does the same thing but for stock trading strategies.

The catch is that stock returns are extremely noisy. The original loop does not survive the move without a lot of extra safety rails.

## The big problem

Imagine you ask 200 friends to each pick 10 stocks at random. Some friends will get lucky and beat the market by a lot. If you then point at the lucky friend and say "this person is good at picking stocks," you have fooled yourself. That is exactly what happens when an AI tries 200 strategies and you keep the one with the best score. The score is real, the skill is not. This repo is mostly a list of tricks to make that kind of self fooling harder, plus an honest list of where it still happens.

A green row in the results file is not a green light. It is a signal that the row is worth a closer look — nothing more.

## What it actually does

You start the script. The AI picks a trading idea, writes it into `strategy.py`, runs a backtest on US stocks from 2010 to 2024, and checks whether it beat a fixed baseline on the 2020 to 2024 part by enough of a margin to count as more than luck. If yes, it keeps the change and picks another idea. If no, it throws the change away and tries something else. The loop is capped at 20 attempts per branch.

Three files matter:

- `prepare.py`: downloads stock prices and runs the backtest. The AI is not allowed to touch this.
- `strategy.py`: where the AI writes its trading idea. The only file it can edit.
- `program.md`: the rules the AI follows. You edit this between runs as you learn what works.

The score is called OOS Sharpe. Higher is better. Two safety rules: the strategy cannot lose more than 35% at its worst point, and it cannot trade more than 50 times its own size per year. Anything that breaks those rules gets thrown out no matter how good the score looks.

## Terms

A few terms come up a lot.

**In sample (IS) and out of sample (OOS).** We split the data into two pieces. The 2010 to 2019 piece is "in sample," which is the practice exam. The 2020 to 2024 piece is "out of sample," the real exam. The whole point is to invent a strategy using the practice exam and only check the real exam at the end. If you keep peeking at the real exam and tweaking your answer, the real exam stops being real.

**Sharpe ratio.** A number that goes up when a strategy makes more money for less risk. A Sharpe of 1 is good. A Sharpe of 2 is suspicious. A Sharpe of 5 means you made a mistake.

**Drawdown.** The biggest peak to bottom loss the strategy goes through. A 35% drawdown means at some point you were down 35% from your previous high.

**Turnover.** How much the strategy buys and sells. A turnover of 1 per year means it replaces its whole portfolio once a year. A turnover of 50 means it churns through everything 50 times a year, which is a lot.

## The starting strategy

The AI starts with something called 12-1 momentum. Plain English: every month, look at how each stock did over the past 12 months (but skip the most recent month), buy the 10 best, hold for a month, repeat.

Why skip the most recent month? Because over very short windows (a day to a month), winners tend to give back some of their gains. Mixing that in with the 12 month signal weakens it. Skipping one month separates the two effects.

This is one of the oldest and most studied patterns in finance. People have been writing papers about it since 1993 and it has kept working in live money for about 30 years after publication. It is the right answer for this kind of problem and it is hard to beat.

On our setup it gets an OOS Sharpe of about 0.92, a worst drawdown of about 32%, and trades roughly six times a year.

## Why beating the starter is hard

Three reasons.

First, momentum is real. So most "improvements" the AI invents are either fitting noise, or rediscovering the same signal in a different shape.

Second, the data is rigged in momentum's favor. We use the S&P 100 frozen at the end of 2024. Every name on the list is a company that survived all the way to 2024. Strategies that bet on "winners keep winning" get a free boost from this and there is no clean way to turn it off.

Third, the math has a lot of randomness in it. A "win" of 0.05 in OOS Sharpe is probably noise.

## What we do to fight self fooling

1. **Hide the answer from the AI.** Strict honesty mode (`SHOW_OOS=0`) is on by default when the loop runs through the skill. With it on, the AI cannot see any OOS metric. It only sees how the strategy did on 2010 to 2019. OOS numbers go to a separate file (`oos_results.tsv`) that only the human reads. The AI cannot keep tweaking until OOS looks good, because it does not know what OOS looks like.

2. **Require a real win, not a noise win.** A strategy is only kept if it clears the baseline by a margin that grows with the number of attempts already made on this universe (a deflation term, pooled across branches), AND the bottom of a 90% confidence interval around the OOS score clears the baseline, AND its walk-forward median across non-overlapping two-year folds clears the baseline's median by 0.10. The grader (`log_result.py`) decides keep or discard — the agent does not.

3. **Show the score year by year.** OOS Sharpe is reported separately for 2020, 2021, 2022, 2023, and 2024. A strategy that gets a high overall score because of one big year is easy to spot.

4. **Walk forward inside the loop.** Each backtest also reports the score on five non-overlapping two-year folds spanning 2014 to 2023. The keep gate uses the median across folds, not just the headline. A separate `walkforward.py` lets you re-run the same view on demand.

5. **Anchor to a fixed baseline, not a moving one.** The bar is the seed run's score, frozen for the life of the branch. It does not drift upward with each kept row, so later attempts compete against the same anchor as the first.

6. **AST-level deduplication.** Every commit's parsed strategy AST is hashed and checked against a per-universe trial cache shared across branches. An identical hypothesis already tried on this universe is auto-rejected before its score even competes.

7. **Hard rules up front.** Strategies that lose too much (>35% drawdown) or trade too much (>50× annual turnover) are thrown out before they can compete on score.

8. **Every attempt is a git commit.** You can see every idea the AI tried, not just the ones it kept. That is the audit trail that protects you from being shown only the survivors.

9. **A second-look notebook.** `analysis.ipynb` re-computes deflated Sharpe and lets you eyeball histograms across all trials. Deflation is already inside the keep gate; the notebook is where you confirm a kept row still looks real after a calmer second pass.

## Where the self fooling still wins

1. **The OOS slice never changes.** Strict honesty stops the AI. It does not stop you. You read the OOS results between runs, learn what is working, and edit `program.md` based on that. That leaks the OOS into the next run. There is no clean fix short of locking away a slice of data nobody ever looks at.

2. **Strict honesty is on the honor system.** A clever enough AI could in theory guess what is happening on OOS by looking at patterns in what it does see. The only thing stopping it is that it is not trying to.

3. **Deflation is enforced but not perfect.** The keep gate counts attempts and raises the bar accordingly. The math assumes the trials are independent draws — they are not, since the agent is steering on IS each time. Real protection, not airtight protection.

4. **The universe helps momentum strategies.** Only using stocks that survived to 2024 makes "buy the winners" easier. Across a 20-attempt branch, finding a flavor of momentum that scores well is not hard.

5. **The cost model is friendly.** We charge 5 basis points per side (so 0.05% each time you buy or sell) and 200 basis points a year to short. That is reasonable on average, but a real strategy would face worse costs and would be limited in how much money it could trade.

6. **We only test one kind of market.** 2010 to 2024 is mostly one long bull market with two short interruptions. A strategy that works here might fail in a different decade.

7. **You can cherry pick across runs.** Each session makes its own branch. If you run the loop ten times and only keep the prettiest result, you have added another layer of luck. The fix is to look at all the branches together (the notebook does this), not just the best one.

## What "passing" actually means

A green row in `results.tsv` means: this strategy beat a fixed baseline on one fixed slice of data, with a deflation buffer that scales with the number of attempts, while obeying the safety rules. That is it. It does not mean the strategy makes money. It means the row is worth a closer look.

## Run it

You need Python 3.10 or later, [uv](https://docs.astral.sh/uv/) (a Python package manager), and an internet connection for the first download.

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
uv sync
uv run prepare.py
uv run strategy.py
```

If those four commands run cleanly, the data and harness are wired up.

## Running the AI

Open this repo in Claude Code (or any agent harness you like). The repo ships three skills under `.claude/skills/`:

| Skill | What it does |
|---|---|
| `quant-autoresearch` | One run on one universe. Makes a fresh git worktree, runs the baseline plus up to 20 attempts under strict honesty, pushes a branch with a `SUMMARY.md`, removes the worktree. Slash alias: `/autoresearch`. |
| `quant-autoresearch-all` | Fans out one parallel agent per universe (defaults to all eight). Each gets its own worktree and timestamped tag. Slash alias: `/autoresearch-all`. |
| `deep-autoresearch` | Fans out N parallel agents on the *same* universe to cover more hypothesis ground. Cross-branch AST dedup and pooled deflation are handled by `log_result.py`'s shared per-universe trial cache. |

### Examples

| Command | What it does |
|---|---|
| `/autoresearch` | Default S&P 100. One worktree, baseline plus up to 20 attempts. |
| `/autoresearch sp500` | Same loop on the S&P 500. Needs `universe_sp500_2024.json` and the matching prices cache. |
| `/autoresearch-all` | All eight universes in parallel, one agent each. |
| `/autoresearch-all sp100,sp500` | Subset, comma-separated. |

The skills also fire on free-form prompts that match their descriptions — e.g. `kick off a new experiment`, `run program.md overnight on the ndx100 universe`, or `fan out 5 agents on xbi`.

### Switching universes manually

```bash
UNIVERSE_TAG=sp500_2024 uv run prepare.py
UNIVERSE_TAG=sp500_2024 uv run strategy.py > run.log 2>&1
```

To add a new universe, drop `universe_<tag>.json` in the repo root with a list of tickers, then run `prepare.py` with that tag.

### Available universes

The default S&P 100 is the most efficient universe in the repo — a hundred giant US companies watched by every analyst on earth, so any signal has been competed away long ago. Less efficient universes leave more room for a real edge to survive, at the cost of worse survivorship bias.

| Tag | Names | What it is | Where it cuts |
|---|---|---|---|
| `sp100_2024` (default) | 100 | S&P 100, biggest US large caps | Most efficient. Hardest to beat. Survivorship bias is real but moderate. |
| `sp500_2024` | 503 | S&P 500 | A bit less efficient than SP100. Good for sanity checking that an SP100 result is not single-name luck. |
| `sp400_2024` | 400 | S&P MidCap 400 | Mid caps. Less analyst coverage. Survivorship bias is bigger because mid caps churn more. |
| `sp600_2024` | 603 | S&P SmallCap 600 | Small caps. Least efficient cap-based universe in the repo. Also the most survivorship-biased of the SP family because small caps fail more often. |
| `ndx100_2024` | 101 | Nasdaq 100 | Tech and growth concentrated. A win here might just be loading on tech beta in a 14-year tech bull market. |
| `xbi_2026` | 148 | SPDR S&P Biotech ETF holdings | Single sector. Returns are driven by binary trial outcomes and FDA decisions, which barely correlate with broad market factors. Worst survivorship bias in the repo by a wide margin (most pre-2010 small biotechs are gone). |
| `xlk_2026` | 67 | SPDR Technology Select Sector ETF holdings | Tech sector cut narrower than NDX100. Same caveat about riding tech beta, sharper. |
| `gdxj_2026` | 42 | VanEck Junior Gold Miners ETF holdings | Commodity-linked, low correlation to broad equities. Small population, high single-name idiosyncratic risk. |

If a strategy looks great on `sp100_2024` only, it is probably overfit. If it survives the smaller / less efficient universes too, deflated Sharpe is still the test that matters — but at least the result is not just mega-cap beta.

### What the AI does in the loop

`program.md` is the actual instruction set. The skill is the wrapper. Each step: edit `strategy.py`, commit, run the backtest under strict honesty, hand the result to `log_result.py`, keep or reset based on the grader's exit code. Capped at 20 attempts per branch.

## File map

```
prepare.py                              constants, data loader, backtest engine (do not modify)
strategy.py                             the trading idea (the AI edits this)
program.md                              instructions for the AI
universe_sp100_2024.json                frozen S&P 100 ticker list (default)
universe_sp500_2024.json                frozen S&P 500 ticker list (503 tickers)
universe_sp400_2024.json                frozen S&P MidCap 400 ticker list (400 tickers)
universe_sp600_2024.json                frozen S&P SmallCap 600 ticker list (603 tickers)
universe_ndx100_2024.json               frozen Nasdaq 100 ticker list (101 tickers)
universe_xbi_2026.json                  XBI biotech ETF holdings (148 tickers, sector universe)
universe_xlk_2026.json                  XLK tech-sector holdings (67 tickers)
universe_gdxj_2026.json                 GDXJ junior gold miner holdings (42 tickers)
analysis.ipynb                          notebook for review, deflated Sharpe lives here
running_best.py                         CLI: shows the current best kept score
log_result.py                           CLI: grader — writes a row to results.tsv, returns exit code
walkforward.py                          CLI: per-fold sanity check for a strategy
test_lookahead.py                       regression test for the T+1 shift
pyproject.toml                          dependencies
.claude/skills/quant-autoresearch/      one-run skill
.claude/skills/quant-autoresearch-all/  one-agent-per-universe fan-out skill
.claude/skills/deep-autoresearch/       N-agents-on-one-universe fan-out skill
.claude/commands/                       slash command aliases for the skills
worktrees/                              per-experiment git worktrees (gitignored)
```

## Other things that are not realistic

1. The price data comes from yfinance, which is free and unaudited. Splits, dividends, and corporate actions follow yfinance conventions. Bugs in the data are not corrected.

2. The cost model is a flat 5 basis points per side and 200 basis points a year to short. There is no model for how much you move the market when you trade big, no bid ask spread, and no limit on how big the strategy can get before it stops working.

3. There is no broker connection, no paper trading, no live signal. A good score here is a hypothesis, not a trade.

4. The AI is not a quant. It pattern matches against ideas it has seen in textbooks. It does not know about microstructure, settlement, locate fees, or why a published anomaly might already be arbitraged away.

If you want to use any idea from this loop with real money, you owe it: a proper point in time universe (so you are not cheating with hindsight), a real cost study, an out of sample slice this loop has never touched, and a paper trading sandbox before any actual capital. None of that is here.

## Credit

This is a port of the loop from Andrej Karpathy's [karpathy/autoresearch](https://github.com/karpathy/autoresearch). The structure (one file, hard rules, git audit trail, AI in the driver seat) is his idea. Everything specifically about not fooling yourself in a noisy financial setting (strict honesty mode, bootstrap intervals, year by year breakdown, walk forward, deflation in the keep gate, AST dedup, the honest list of remaining problems) is what this fork adds.

## License

MIT
