# quant-research/0421-070001

- **UNIVERSE_TAG**: sp100_2024
- **Baseline (seed)**: baseline: 0.915293  (commit 5a1c775)
- **Running best**:   running_best: 0.915293  (commit 5a1c775)
- **Trials logged**:  20
- **Stop reason**:    trial-cap

## results.tsv

```
commit	oos_sharpe	max_dd	turnover	status	description
5a1c775	0.915293	0.3181	6.42	keep	thesis: [baseline/12-1/equal/monthly] algebraic rewrite anchor (0.9 -> 1-0.1), identical weights
e622f24	0.938553	0.3005	8.75	discard	thesis: [trend/6m/equal/monthly] shorter lookback better tracks regime shifts on large-cap names
e0c0c6a	0.911949	0.2862	6.72	discard	thesis: [trend/12-1/rank/monthly] risk-adjusted momentum normalizes by 126d vol to favor persistent winners
0e11fe7	0.899959	0.3021	8.07	discard	thesis: [trend/12-1/invvol/monthly] inverse-vol sizing reduces single-name DD on top-decile winners
d7ab53c	0.450613	0.4379	90.13	discard	thesis: [reversal/5d/equal/weekly] buy weekly losers expecting mean reversion on large-caps
aa11c1a	0.584056	0.4399	20.97	discard	thesis: [reversal/21d/equal/monthly] buy monthly losers for mean reversion on large-caps
a7c07b2	0.717152	0.3132	5.67	discard	thesis: [trend/12-1/equal/monthly] top-quintile basket improves diversification vs decile
60ff182	0.813759	0.2013	6.08	discard	thesis: [regime/12-1/equal/monthly] flat when eq-weight idx below 200d MA to reduce drawdown
b39a86f	-0.038893	0.2562	6.32	discard	thesis: [trend/12-1/longshort/monthly] market-neutral by shorting bottom decile of 12-1 momentum
d59393a	0.351769	0.2871	2.61	discard	thesis: [quality/vol-1y/equal/monthly] low-vol anomaly: bottom decile 252d vol outperforms risk-adjusted
848ccfc	0.708799	0.3296	4.48	discard	thesis: [trend/12-1/ranktilt/monthly] smooth rank-weighted tilt replaces hard decile cutoff
d761c75	0.664760	0.3173	9.72	discard	thesis: [composite/trend+quality/equal/monthly] top-decile momentum AND exclude top-vol quintile
fbe1825	1.126354	0.3318	11.92	discard	thesis: [trend/3-1/equal/monthly] 3-month momentum captures faster trend regime changes
fb5d97e	0.842665	0.3359	3.43	discard	thesis: [trend/12-1/equal/quarterly] quarterly rebalance reduces noise and costs
24b88f7	0.233406	0.3639	16.36	discard	thesis: [trend/52wk-hi/equal/monthly] names near 52w high exhibit continuation (G&H 2004)
3510bbe	0.704306	0.3205	7.89	discard	thesis: [composite/trend-blend/equal/monthly] average rank of 12-1 and 6-1 momentum smooths horizon choice
0d0a2ab	0.800485	0.1666	3.21	discard	thesis: [trend/12-1/equal/monthly] half-invested (gross 0.5) halves costs and drawdowns proportionally
1cee20e	0.931472	0.3181	6.84	discard	thesis: [composite/trend+dd/equal/monthly] exclude names with 126d dd > 25% to avoid post-crash dead-cat moves
1de6974	0.812555	0.3207	9.59	discard	thesis: [composite/trend+ob/equal/monthly] drop top 5% of 5d return from momentum winners to dodge short reversal
bf5ddb6	0.695432	0.3051	6.59	discard	thesis: [composite/trend/invvol/monthly] top-quintile basket inverse-vol sized combines breadth and risk balance
```

## Theses by status

### keep
- thesis: [baseline/12-1/equal/monthly] algebraic rewrite anchor (0.9 -> 1-0.1), identical weights

### discard
- thesis: [trend/6m/equal/monthly] shorter lookback better tracks regime shifts on large-cap names
- thesis: [trend/12-1/rank/monthly] risk-adjusted momentum normalizes by 126d vol to favor persistent winners
- thesis: [trend/12-1/invvol/monthly] inverse-vol sizing reduces single-name DD on top-decile winners
- thesis: [reversal/5d/equal/weekly] buy weekly losers expecting mean reversion on large-caps
- thesis: [reversal/21d/equal/monthly] buy monthly losers for mean reversion on large-caps
- thesis: [trend/12-1/equal/monthly] top-quintile basket improves diversification vs decile
- thesis: [regime/12-1/equal/monthly] flat when eq-weight idx below 200d MA to reduce drawdown
- thesis: [trend/12-1/longshort/monthly] market-neutral by shorting bottom decile of 12-1 momentum
- thesis: [quality/vol-1y/equal/monthly] low-vol anomaly: bottom decile 252d vol outperforms risk-adjusted
- thesis: [trend/12-1/ranktilt/monthly] smooth rank-weighted tilt replaces hard decile cutoff
- thesis: [composite/trend+quality/equal/monthly] top-decile momentum AND exclude top-vol quintile
- thesis: [trend/3-1/equal/monthly] 3-month momentum captures faster trend regime changes
- thesis: [trend/12-1/equal/quarterly] quarterly rebalance reduces noise and costs
- thesis: [trend/52wk-hi/equal/monthly] names near 52w high exhibit continuation (G&H 2004)
- thesis: [composite/trend-blend/equal/monthly] average rank of 12-1 and 6-1 momentum smooths horizon choice
- thesis: [trend/12-1/equal/monthly] half-invested (gross 0.5) halves costs and drawdowns proportionally
- thesis: [composite/trend+dd/equal/monthly] exclude names with 126d dd > 25% to avoid post-crash dead-cat moves
- thesis: [composite/trend+ob/equal/monthly] drop top 5% of 5d return from momentum winners to dodge short reversal
- thesis: [composite/trend/invvol/monthly] top-quintile basket inverse-vol sized combines breadth and risk balance

### crash
