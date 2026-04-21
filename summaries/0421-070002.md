# quant-research/0421-070002

- **UNIVERSE_TAG**: sp400_2024
- **Baseline (seed)**: baseline: 0.960896  (commit 3972c2c)
- **Running best**:   running_best: 0.960896  (commit 3972c2c)
- **Trials logged**:  20
- **Stop reason**:    trial-cap

## results.tsv

```
commit	oos_sharpe	max_dd	turnover	status	description
3972c2c	0.960896	0.4356	6.07	keep	thesis: [baseline/12-1/equal/monthly] algebraic rewrite — anchors SP400 12-1 momentum top-decile baseline
c4b54af	0.841164	0.4245	7.54	discard	thesis: [momentum/12-1/inv-vol/monthly] IV-size top-decile to damp mid-cap vol dispersion
ba3e20f	0.835573	0.4892	9.31	discard	thesis: [momentum/6-1/equal/monthly] shorter lookback captures faster mid-cap trend
65ff5a3	0.833633	0.4329	5.38	discard	thesis: [momentum/12-1/equal/monthly] top-quintile vs top-decile for broader basket breadth
6d523fa	-0.460088	3.4757	6.17	discard	thesis: [momentum/12-1/L-S/monthly] dollar-neutral L/S on decile spread
c2a9463	0.859631	0.4406	6.71	discard	thesis: [momentum/12-1/equal/monthly/risk-adj] rank by ret/vol to penalize noisy trends
ba8c510	0.771396	0.2495	9.81	discard	thesis: [momentum/12-1/equal/monthly/regime] EW-universe DD > 10pct gate to avoid momentum crashes
62bdc55	0.345133	0.4239	2.38	discard	thesis: [low-vol/252d/equal/monthly] bottom-decile realized vol captures low-vol anomaly
0ac3e48	0.531651	0.5683	20.86	discard	thesis: [reversal/21d/equal/monthly] long bottom-decile 21d losers via flow pressure
62e37c8	0.314458	0.4128	5.07	discard	thesis: [composite/low-vol+trend/equal/monthly] low-vol quintile filtered by positive 12-1 momentum
aae300f	0.862727	0.2402	3.04	discard	thesis: [momentum/12-1/equal/monthly/half-lev] 0.5 gross leverage to dampen drawdown
2491031	0.993863	0.4194	3.45	discard	thesis: [momentum/12-1/equal/quarterly] quarterly rebalance to cut turnover drag
7bb894e	1.008475	0.4893	12.25	discard	thesis: [momentum/3-1/equal/monthly] shorter 63d lookback bridges reversal and classical mom
7e34d88	0.831311	0.4273	8.67	discard	thesis: [composite/mom+novol/equal/monthly] momentum top-decile ex top-vol-decile lottery filter
3175b57	0.784695	0.4357	4.36	discard	thesis: [momentum/12-1/rank-tilt/monthly] soft rank-tilt above median captures cross-section smoothly
670679f	0.935819	0.4167	7.70	discard	thesis: [composite/mom+sma/equal/monthly] 12-1 momentum gated by per-name 200d SMA trend filter
9efb5a8	0.768924	0.4442	0.04	discard	thesis: [beta/EW/equal/daily] passive equal-weight market-beta sanity probe
9383dc5	0.822000	0.5071	18.61	discard	thesis: [composite/mom+rev/equal/monthly] 50/50 blend of 12-1 mom and 21d reversal ranks
76fd286	0.613660	0.2238	6.44	discard	thesis: [beta/EW/regime/monthly] regime-gated passive EW; flat to cash on 10pct EW-universe DD
d3a611a	0.960896	0.4356	6.07	discard	thesis: [momentum/12-1/resid/equal/monthly] xs-demeaned z-score to isolate idiosyncratic trend
```

## Theses by status

### keep
- thesis: [baseline/12-1/equal/monthly] algebraic rewrite — anchors SP400 12-1 momentum top-decile baseline

### discard
- thesis: [momentum/12-1/inv-vol/monthly] IV-size top-decile to damp mid-cap vol dispersion
- thesis: [momentum/6-1/equal/monthly] shorter lookback captures faster mid-cap trend
- thesis: [momentum/12-1/equal/monthly] top-quintile vs top-decile for broader basket breadth
- thesis: [momentum/12-1/L-S/monthly] dollar-neutral L/S on decile spread
- thesis: [momentum/12-1/equal/monthly/risk-adj] rank by ret/vol to penalize noisy trends
- thesis: [momentum/12-1/equal/monthly/regime] EW-universe DD > 10pct gate to avoid momentum crashes
- thesis: [low-vol/252d/equal/monthly] bottom-decile realized vol captures low-vol anomaly
- thesis: [reversal/21d/equal/monthly] long bottom-decile 21d losers via flow pressure
- thesis: [composite/low-vol+trend/equal/monthly] low-vol quintile filtered by positive 12-1 momentum
- thesis: [momentum/12-1/equal/monthly/half-lev] 0.5 gross leverage to dampen drawdown
- thesis: [momentum/12-1/equal/quarterly] quarterly rebalance to cut turnover drag
- thesis: [momentum/3-1/equal/monthly] shorter 63d lookback bridges reversal and classical mom
- thesis: [composite/mom+novol/equal/monthly] momentum top-decile ex top-vol-decile lottery filter
- thesis: [momentum/12-1/rank-tilt/monthly] soft rank-tilt above median captures cross-section smoothly
- thesis: [composite/mom+sma/equal/monthly] 12-1 momentum gated by per-name 200d SMA trend filter
- thesis: [beta/EW/equal/daily] passive equal-weight market-beta sanity probe
- thesis: [composite/mom+rev/equal/monthly] 50/50 blend of 12-1 mom and 21d reversal ranks
- thesis: [beta/EW/regime/monthly] regime-gated passive EW; flat to cash on 10pct EW-universe DD
- thesis: [momentum/12-1/resid/equal/monthly] xs-demeaned z-score to isolate idiosyncratic trend

### crash
