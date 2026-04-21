# quant-research/0420-220115

- **UNIVERSE_TAG**: sp600_2024
- **Baseline (seed)**: baseline: 0.543835  (commit c198d25)
- **Running best**:   running_best: 0.543835  (commit c198d25)
- **Trials logged**:  20
- **Stop reason**:    trial-cap

## results.tsv

```
commit	oos_sharpe	max_dd	turnover	status	description
c198d25	0.543835	0.4939	6.72	keep	thesis: [trend/252d-skip21d/equal/monthly] 12-1 momentum baseline — SP600 survivorship anchor
31b4ad1	0.494846	0.4922	8.32	discard	thesis: [trend/252d-skip21d/inv-vol/monthly] equalize risk contribution across small caps — heterogeneous vol makes equal-weight top-shop
ab4e80d	0.472368	0.4817	7.26	discard	thesis: [trend/risk-adj-252d/equal/monthly] return/vol ranking avoids tiny-float high-vol winners dominating raw-return top decile on small caps
e6c3f84	0.759379	0.4796	9.02	discard	thesis: [trend/126d-skip21d/equal/monthly] 6-1 lookback captures small-cap momentum before flow-driven decay — less analyst coverage accelerates turnover
244f0e1	0.111343	0.4616	11.69	discard	thesis: [regime/EW-DD-15pct/trend/monthly] flatten when EW universe 15pct below trailing peak — small caps compound losses in bear phases
01c1b44	0.449721	0.2792	3.36	discard	thesis: [sizing/gross-0.5/trend/monthly] halve gross exposure — scale-invariant Sharpe under linear costs, DD and turnover halve to fit hard caps
b193884	0.604816	0.4561	5.61	discard	thesis: [trend/252d-skip21d/equal/monthly/quintile] top quintile on 600 names = 120 holdings — dilute idiosyncratic DD from concentrated decile
85a90be	-0.568769	0.4174	6.43	discard	thesis: [sizing/long-short/trend/monthly] market-neutral top-vs-bottom decile spread — eliminate bear-market DD driver on small caps
6be4eac	0.726652	0.6354	44.58	discard	thesis: [reversal/21d/equal/weekly] long worst-21d performers — thin small caps see flow-pressure sells that revert on weekly horizon
ded2f54	0.593130	0.5142	20.60	discard	thesis: [reversal/21d/equal/monthly] monthly rebalance on 21d losers — keeps flow-reversal edge while fitting turnover cap
27a75fb	0.275452	0.3289	18.82	discard	thesis: [reversal/21d/equal/monthly+regime-10pct] gate reversal book off in trending crashes — falling-knife risk dominates in downtrends
d575eb6	0.211058	0.2172	8.53	discard	thesis: [reversal/21d/vol-target-20pct/monthly] scale gross down when realized vol spikes — cap DD growth without hard flatten
6567022	0.253133	0.2565	7.96	discard	thesis: [reversal/21d/vol-target-20pct/monthly-only] scale at month-end not daily — avoid daily cost drag from scale drift
5d425f6	0.515145	0.5087	18.36	discard	thesis: [composite/trend+reversal/equal/monthly] sum-of-rank combines long-horizon trend with short-horizon flow reversal — orthogonal edges smooth return stream
4525b14	0.583065	0.5211	18.44	discard	thesis: [reversal/21d/equal/monthly/quintile] wider basket of 120 reversal names — diversification reduces DD from single-name blowups
66ab11f	0.529467	0.5339	21.74	discard	thesis: [composite/reversal+filter/equal/monthly] 21d losers excluding bottom-quintile 12-1 momentum — separate flow pressure from real decline
509573b	0.593130	0.5142	20.60	discard	thesis: [reversal/21d-residual/equal/monthly] cross-section demean 21d returns — isolate idiosyncratic flow pressure, market-driven moves dont revert at 1mo
fd91e9e	0.511069	0.2939	10.30	discard	thesis: [sizing/gross-0.5/reversal-21d/monthly] bring strongest-IS signal into DD compliance by halving gross — trades RF drag for cap compliance
534a066	0.749555	0.4790	12.33	discard	thesis: [reversal/63d/equal/monthly] medium-horizon mean reversion — slower signal cuts turnover and vol vs 21d
382ce3d	0.363355	0.4213	21.59	discard	thesis: [reversal/21d/soft-regime-15pct/monthly] half gross in drawdowns preserves signal while capping crash-phase DD contribution
```

## Theses by status

### keep
- thesis: [trend/252d-skip21d/equal/monthly] 12-1 momentum baseline — SP600 survivorship anchor

### discard
- thesis: [trend/252d-skip21d/inv-vol/monthly] equalize risk contribution across small caps — heterogeneous vol makes equal-weight top-shop
- thesis: [trend/risk-adj-252d/equal/monthly] return/vol ranking avoids tiny-float high-vol winners dominating raw-return top decile on small caps
- thesis: [trend/126d-skip21d/equal/monthly] 6-1 lookback captures small-cap momentum before flow-driven decay — less analyst coverage accelerates turnover
- thesis: [regime/EW-DD-15pct/trend/monthly] flatten when EW universe 15pct below trailing peak — small caps compound losses in bear phases
- thesis: [sizing/gross-0.5/trend/monthly] halve gross exposure — scale-invariant Sharpe under linear costs, DD and turnover halve to fit hard caps
- thesis: [trend/252d-skip21d/equal/monthly/quintile] top quintile on 600 names = 120 holdings — dilute idiosyncratic DD from concentrated decile
- thesis: [sizing/long-short/trend/monthly] market-neutral top-vs-bottom decile spread — eliminate bear-market DD driver on small caps
- thesis: [reversal/21d/equal/weekly] long worst-21d performers — thin small caps see flow-pressure sells that revert on weekly horizon
- thesis: [reversal/21d/equal/monthly] monthly rebalance on 21d losers — keeps flow-reversal edge while fitting turnover cap
- thesis: [reversal/21d/equal/monthly+regime-10pct] gate reversal book off in trending crashes — falling-knife risk dominates in downtrends
- thesis: [reversal/21d/vol-target-20pct/monthly] scale gross down when realized vol spikes — cap DD growth without hard flatten
- thesis: [reversal/21d/vol-target-20pct/monthly-only] scale at month-end not daily — avoid daily cost drag from scale drift
- thesis: [composite/trend+reversal/equal/monthly] sum-of-rank combines long-horizon trend with short-horizon flow reversal — orthogonal edges smooth return stream
- thesis: [reversal/21d/equal/monthly/quintile] wider basket of 120 reversal names — diversification reduces DD from single-name blowups
- thesis: [composite/reversal+filter/equal/monthly] 21d losers excluding bottom-quintile 12-1 momentum — separate flow pressure from real decline
- thesis: [reversal/21d-residual/equal/monthly] cross-section demean 21d returns — isolate idiosyncratic flow pressure, market-driven moves dont revert at 1mo
- thesis: [sizing/gross-0.5/reversal-21d/monthly] bring strongest-IS signal into DD compliance by halving gross — trades RF drag for cap compliance
- thesis: [reversal/63d/equal/monthly] medium-horizon mean reversion — slower signal cuts turnover and vol vs 21d
- thesis: [reversal/21d/soft-regime-15pct/monthly] half gross in drawdowns preserves signal while capping crash-phase DD contribution

### crash
