# karpathy-quant-auto-research

Andrej Karpathy made a repo called [autoresearch](https://github.com/karpathy/autoresearch) where an AI agent edits one file, runs an experiment, keeps the change if it improved a score, and tries again. He used it for tweaking small language models. This repo does the same thing but for stock trading strategies.

The catch is that stock returns are extremely noisy. The original loop does not survive the move without a lot of extra safety rails.

## The big problem, in one paragraph

Imagine you ask 200 friends to each pick 10 stocks at random. Some friends will get lucky and beat the market by a lot. If you then point at the lucky friend and say "this person is good at picking stocks," you have fooled yourself. That is exactly what happens when an AI tries 200 strategies and you keep the one with the best score. The score is real, the skill is not. This repo is mostly a list of tricks to make that kind of self fooling harder, plus an honest list of where it still happens.

If you take a green row in the results file at face value, the loop has tricked you. Sorry.

## What it actually does

You start the script. The AI picks a trading idea, writes it into `strategy.py`, runs a backtest on US stocks from 2010 to 2024, and checks if it beat the previous best on the 2020 to 2024 part. If yes, it keeps the change and tries to improve on it. If no, it throws the change away and tries something else. By morning you have a log of about 100 attempts and a current best.

Three files matter:

- `prepare.py`: downloads stock prices and runs the backtest. The AI is not allowed to touch this.
- `strategy.py`: where the AI writes its trading idea. The only file it can edit.
- `program.md`: the rules the AI follows. You edit this between runs as you learn what works.

The score is called OOS Sharpe. Higher is better. Two safety rules: the strategy cannot lose more than 35% at its worst point, and it cannot trade more than 50 times its own size per year. Anything that breaks those rules gets thrown out no matter how good the score looks.

## Some words you need to know

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

This is the part that matters.

1. **Hide the answer from the AI.** We have a mode called strict honesty. When it is on, the AI cannot see the OOS score at all. It only sees how the strategy did on 2010 to 2019. The OOS numbers go to a separate file that only the human reads. This means the AI literally cannot keep tweaking until OOS looks good, because it does not know what OOS looks like.

2. **Require a real win, not a noise win.** Every run also reports a confidence interval around the OOS score (basically a "the real number is probably somewhere in this range"). To count as an improvement, the bottom of that range has to clear the previous best minus 0.1. A small lucky bump does not pass.

3. **Show the score year by year.** We report OOS Sharpe separately for 2020, 2021, 2022, 2023, and 2024. A strategy that gets a high overall score because it had one amazing year is easy to spot.

4. **Walk forward check.** A separate script (`walkforward.py`) splits the data into five non overlapping two year chunks and runs the strategy on each. If it only works on one chunk, you find out.

5. **Deflated Sharpe.** A notebook (`analysis.ipynb`) runs a statistic called deflated Sharpe. It penalizes the headline score based on how many tries you made. This is the real test for "is this best of 200 actually meaningful." It is not part of the keep rule. You have to look at it yourself in the morning.

6. **Hard rules up front.** Strategies that lose too much or trade too much get thrown out before they can compete. This kills the obvious garbage.

7. **Every attempt is a git commit.** You can see every idea the AI tried, not just the ones it kept. This is your protection against being shown only the survivors.

## Where the self fooling still wins

Read this too.

1. **The OOS slice never changes.** Strict honesty stops the AI. It does not stop you. You read the OOS results between runs, learn what is working, and edit `program.md` based on that. That leaks the OOS into your next run. There is no clean fix short of locking away a slice of data nobody ever looks at.

2. **Strict honesty is on the honor system.** A clever enough AI could in theory guess what is happening on OOS by looking at patterns in what it does see. The only thing stopping it is that it is not trying to.

3. **Deflated Sharpe is shown but not enforced.** A strategy can pass the keep rule and still fail deflated Sharpe. You have to check by hand.

4. **The universe helps momentum strategies.** Only using stocks that survived to 2024 makes "buy the winners" easier. The AI gets 200 chances to find a flavor of it that scores well.

5. **The cost model is friendly.** We charge 5 basis points per side (so 0.05% each time you buy or sell) and 200 basis points a year to short. That is reasonable on average but a real strategy would face worse costs and would be limited in how much money it could trade.

6. **We only test one kind of market.** 2010 to 2024 is mostly one long bull market with two short interruptions. A strategy that works here might fail in a different decade.

7. **You can cherry pick across runs.** Each session makes its own branch. If you run the loop ten times and only keep the prettiest result, you have added another layer of luck. The fix is to look at all the branches in the notebook, not just the best one.

## What "passing" actually means

A green row in `results.tsv` means: this strategy beat the previous best on one fixed slice of data, with a small noise buffer, while obeying the safety rules. That is it. It does not mean the strategy makes money. It means it is worth a closer look in the morning.

## Run it

You need Python 3.10 or later, [uv](https://docs.astral.sh/uv/) (a Python package manager), and an internet connection for the first download.

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
uv sync
uv run prepare.py
uv run strategy.py
```

If those four commands work, you are ready to run the AI.

## Running the AI

Open this repo in Claude Code (or any agent harness you like). The repo ships with a Claude Code skill at `.claude/skills/quant-autoresearch/SKILL.md` that handles the boring parts: makes a fresh git worktree, turns on strict honesty mode, runs the loop, pushes the result branch, and cleans up. There is also a slash command at `.claude/commands/autoresearch.md` that calls the skill.

### Examples

| Command | What it does |
|---|---|
| `/autoresearch` | Default S&P 100. Makes a worktree, runs the baseline plus up to 20 attempts, pushes a branch with a `SUMMARY.md`, removes the worktree. |
| `/autoresearch sp500` | Same thing on the S&P 500 (503 tickers). Needs `universe_sp500_2024.json` and the matching prices cache. |
| `/autoresearch sp100` | Same as plain `/autoresearch`. |

### You can also just say it

The skill kicks in when your prompt matches its description. Any of these work:

```
kick off a new experiment
start the autoresearch loop
launch strict honesty mode on sp500
run program.md overnight on the sp100 universe
```

If you mention a universe in the prompt, the skill picks it up.

### Running multiple at once

Each kick off makes its own timestamped worktree so two sessions do not step on each other. Different universes use separate cache files so they do not fight over data either.

### Switching universes

```bash
UNIVERSE_TAG=sp500_2024 uv run prepare.py
UNIVERSE_TAG=sp500_2024 /autoresearch
```

To add a new universe, drop `universe_<tag>.json` in the repo root with a list of tickers, then run prepare with that tag.

### What the AI does in the loop

`program.md` is the actual instruction set. The skill is just a wrapper. Each step: edit `strategy.py`, commit, run the backtest with strict honesty on, log the result, keep or reset. Capped at 20 attempts per branch.

## File map

```
prepare.py                              constants, data loader, backtest engine (do not modify)
strategy.py                             the trading idea (the AI edits this)
program.md                              instructions for the AI
universe_sp100_2024.json                frozen S&P 100 ticker list (default)
universe_sp500_2024.json                frozen S&P 500 ticker list (503 tickers)
analysis.ipynb                          notebook for review, deflated Sharpe lives here
running_best.py                         CLI: shows the current best kept score
log_result.py                           CLI: writes a row to results.tsv from run.log
walkforward.py                          CLI: per fold sanity check for a strategy
test_lookahead.py                       regression test for the T+1 shift
pyproject.toml                          dependencies
.claude/skills/quant-autoresearch/      Claude Code skill wrapping program.md
.claude/commands/autoresearch.md        slash command alias for the skill
worktrees/                              per experiment git worktrees (gitignored)
```

## Other things that are not realistic

Beyond the multiple testing problem above:

1. The price data comes from yfinance, which is free and unaudited. Splits, dividends, and corporate actions follow yfinance conventions. Bugs in the data are not corrected.

2. The cost model is a flat 5 basis points per side and 200 basis points a year to short. There is no model for how much you move the market when you trade big, no bid ask spread, and no limit on how big the strategy can get before it stops working.

3. There is no broker connection, no paper trading, no live signal. A good score here is a hypothesis, not a trade.

4. The AI is not a quant. It pattern matches against ideas it has seen in textbooks. It does not know about microstructure, settlement, locate fees, or why a published anomaly might already be arbitraged away.

If you want to use any idea from this loop with real money, you owe it: a proper point in time universe (so you are not cheating with hindsight), a real cost study, an out of sample slice this loop has never touched, and a paper trading sandbox before any actual capital. None of that is here.

## Credit

This is a port of the loop from Andrej Karpathy's [karpathy/autoresearch](https://github.com/karpathy/autoresearch). The structure (one file, hard rules, git audit trail, AI in the driver seat) is his idea. Everything specifically about not fooling yourself in a noisy financial setting (strict honesty mode, bootstrap intervals, year by year breakdown, walk forward, deflated Sharpe in review, the honest list of remaining problems) is what this fork adds.

## License

MIT
