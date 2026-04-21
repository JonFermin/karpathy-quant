# quant-research/0421-070003

- **UNIVERSE_TAG**: sp500_2024
- **Baseline (seed)**: baseline: 0.938614  (commit 538d56e)
- **Running best**:   running_best: 0.938614  (commit 538d56e)
- **Trials logged**:  20
- **Stop reason**:    trial-cap

## results.tsv

```
commit	oos_sharpe	max_dd	turnover	status	description
538d56e	0.938614	0.3833	6.09	keep	thesis: [baseline/12-1/equal/monthly] algebraic rewrite anchor
3c12bf1	0.842112	0.3791	7.68	discard	thesis: [momentum/12-1/inv-vol/monthly] inverse-63d-vol sizing reduces risk from highest-vol momentum names
92e52b0	0.956175	0.3568	8.88	discard	thesis: [momentum/6-1/equal/monthly] shorter 126d lookback captures fresher trend than 12-1
8e5b353	0.995690	0.3762	12.71	discard	thesis: [momentum/3-1/equal/monthly] 63d lookback for near-term trend strength
e4710f7	0.506544	0.5028	20.58	discard	thesis: [reversal/21d/equal/monthly] bottom-decile 1-month losers revert under liquidity/flow pressure
ba4f3d1	0.747038	0.3900	7.36	discard	thesis: [quality/12-1/equal/monthly] risk-adjusted momentum (return/formation-vol) favors persistent trends
63dcda0	0.808611	0.3690	5.38	discard	thesis: [momentum/12-1/equal/monthly/wide] top quintile diversifies idio noise vs top decile
65021b6	0.795632	0.2602	10.11	discard	thesis: [regime/12-1/equal/monthly] EW-universe drawdown gate zeros positions in >10% DD to dodge momentum crashes
6a16de3	1.049585	0.4061	6.42	discard	thesis: [momentum/12-1/rank-tilted/monthly] size by momentum rank within basket; higher conviction = larger weight
cff9122	-0.142733	0.2988	6.36	discard	thesis: [momentum/12-1/equal/monthly/LS] dollar-neutral L/S decile spread hedges beta
70edbe7	0.971121	0.3821	3.44	discard	thesis: [momentum/12-1/equal/quarterly] quarterly rebalance reduces cost drag; momentum signals persist
56b0446	0.969585	0.3729	6.06	discard	thesis: [residual/12-1/equal/monthly] beta-neutral momentum (rank by mean_ret - beta*mkt_mean)
cf5dbcb	0.374515	0.3531	6.05	discard	thesis: [composite/12-1+lowvol/equal/monthly] combine momentum rank with low-vol rank
39ce7c4	0.829967	0.2068	3.05	discard	thesis: [leverage/12-1/equal/monthly/half] 50% cash sleeve caps drawdowns; Sharpe invariant, risk metrics halved
0584de1	0.608859	0.3585	16.91	discard	thesis: [signal/52w-high/equal/monthly] George-Hwang 52w-high proximity as momentum proxy
958389c	0.854348	0.3885	10.63	discard	thesis: [composite/12-1/21d-filter/equal/monthly] exclude top-decile-recent-return names to avoid parabolic reversers
635c682	0.840432	0.3606	4.27	discard	thesis: [momentum/24-1/equal/monthly] longer 504d lookback for very persistent trends
02301f4	0.886175	0.3918	9.38	discard	thesis: [momentum/12-1/equal/biweekly] faster rebalance to capture decaying signal more promptly
512a8e2	0.827047	0.3910	7.48	discard	thesis: [composite/12-1+6-1/equal/monthly] averaged momentum ranks for horizon robustness
f7521c6	0.644683	0.3652	10.20	discard	thesis: [composite/12-1/low-beta/equal/monthly] filter top-mom basket to below-median-beta to dodge crash risk
```

## Theses by status

### keep
- thesis: [baseline/12-1/equal/monthly] algebraic rewrite anchor

### discard
- thesis: [momentum/12-1/inv-vol/monthly] inverse-63d-vol sizing reduces risk from highest-vol momentum names
- thesis: [momentum/6-1/equal/monthly] shorter 126d lookback captures fresher trend than 12-1
- thesis: [momentum/3-1/equal/monthly] 63d lookback for near-term trend strength
- thesis: [reversal/21d/equal/monthly] bottom-decile 1-month losers revert under liquidity/flow pressure
- thesis: [quality/12-1/equal/monthly] risk-adjusted momentum (return/formation-vol) favors persistent trends
- thesis: [momentum/12-1/equal/monthly/wide] top quintile diversifies idio noise vs top decile
- thesis: [regime/12-1/equal/monthly] EW-universe drawdown gate zeros positions in >10% DD to dodge momentum crashes
- thesis: [momentum/12-1/rank-tilted/monthly] size by momentum rank within basket; higher conviction = larger weight
- thesis: [momentum/12-1/equal/monthly/LS] dollar-neutral L/S decile spread hedges beta
- thesis: [momentum/12-1/equal/quarterly] quarterly rebalance reduces cost drag; momentum signals persist
- thesis: [residual/12-1/equal/monthly] beta-neutral momentum (rank by mean_ret - beta*mkt_mean)
- thesis: [composite/12-1+lowvol/equal/monthly] combine momentum rank with low-vol rank
- thesis: [leverage/12-1/equal/monthly/half] 50% cash sleeve caps drawdowns; Sharpe invariant, risk metrics halved
- thesis: [signal/52w-high/equal/monthly] George-Hwang 52w-high proximity as momentum proxy
- thesis: [composite/12-1/21d-filter/equal/monthly] exclude top-decile-recent-return names to avoid parabolic reversers
- thesis: [momentum/24-1/equal/monthly] longer 504d lookback for very persistent trends
- thesis: [momentum/12-1/equal/biweekly] faster rebalance to capture decaying signal more promptly
- thesis: [composite/12-1+6-1/equal/monthly] averaged momentum ranks for horizon robustness
- thesis: [composite/12-1/low-beta/equal/monthly] filter top-mom basket to below-median-beta to dodge crash risk

### crash
