# quant-research/0421-093346

- **UNIVERSE_TAG**: sp600_2024
- **Baseline (seed)**: baseline: 0.543835  (commit 87e1aad)
- **Running best**:   running_best: 0.543835  (commit 87e1aad)
- **Trials logged**:  20
- **Stop reason**:    trial-cap

## results.tsv

```
commit	oos_sharpe	max_dd	turnover	status	description
87e1aad	0.543835	0.4939	6.72	keep	thesis: [baseline/12-1mom/decile/monthly] anchor — algebraic rewrite of pure 12-1 momentum
ca2f8f8	0.494846	0.4922	8.32	discard	thesis: [vol/12-1mom/inverse-vol/monthly] 63d inverse-vol sizing within top decile dampens blowups
7340e56	0.472368	0.4817	7.26	discard	thesis: [momentum/ra-12-1/decile/monthly] risk-adjust ranks by 252d vol to deprioritize lottery-ticket winners
0bd4450	0.182400	0.4059	12.87	discard	thesis: [regime/12-1mom/decile/monthly+DDgate] flat when EW universe DD>10% — avoids momentum-crash rebounds
54a0a1f	-0.568769	0.4174	6.43	discard	thesis: [momentum/12-1/L-S-decile/monthly] dollar-neutral long-short cuts market-beta drawdowns
4277321	0.549941	0.5085	9.01	discard	thesis: [momentum/12-1+6-1/decile/monthly] blend two lookbacks to reduce rank noise
1236531	0.664835	0.4715	3.74	discard	thesis: [momentum/12-1/decile/quarterly] quarterly rebalance — let small-cap signal play out, cut whipsaw cost
048941b	0.269918	0.3250	12.76	discard	thesis: [regime/12-1/decile/monthly+TSMgate] flat when EW universe 252d return negative (Moskowitz TSM)
b4f367b	0.649165	0.4838	12.46	discard	thesis: [momentum/3-1/decile/monthly] shorter lookback more responsive at regime turns on slow-diffusion small caps
b94efb0	0.598475	0.4690	10.77	discard	thesis: [momentum/3-1/quintile/monthly] 3-1 strong on small caps; quintile stabilizes membership to cut turnover
cd2f404	0.597625	0.5151	6.88	discard	thesis: [momentum/3-1/decile/quarterly] 3-1 responsive signal + quarterly reset cuts turnover into budget
892780b	0.335139	0.3845	12.91	discard	thesis: [momentum+regime/3-1/decile/quarterly+TSMgate] strong IS signal (T11) + TSM DD control (T8) combined
7d23c85	0.194492	0.5151	4.90	discard	thesis: [momentum+regime/3-1/decile/quarterly+TSMgate] gate locked at rebal dates to avoid daily whipsaw turnover
1f556c6	0.546077	0.5012	6.17	discard	thesis: [momentum/3-1/quintile/quarterly] 3-1 signal + broader quintile breadth + quarterly rebal
2c98b53	0.580120	0.4585	4.55	discard	thesis: [momentum/12-1/rank-tilt/monthly] linear rank weighting preserves continuous signal, smooths decile-edge whipsaw
ad43057	0.504067	0.2940	3.44	discard	thesis: [momentum/3-1/decile/quarterly/0.5gross] halve gross — Sharpe is scale-invariant, DD halves
a9262e1	0.488148	0.2805	3.25	discard	thesis: [momentum/3-1+12-1/decile/quarterly/0.5gross] two-horizon blend + scaled gross — diversify signal noise while keeping DD headroom
faf42ce	0.551550	0.2732	6.23	discard	thesis: [momentum/3-1/decile/monthly/0.5gross] monthly 3-1 + half gross — capture responsive signal with DD headroom
03b4d22	0.589068	0.5203	20.63	discard	thesis: [reversal/21d/decile/monthly] short-term mean reversion — retail flow pressure on small caps reverts over 21d
7215513	0.024983	0.2065	11.39	discard	thesis: [reversal+regime/21d/decile/monthly/0.5gross+TSMgate] STR flow alpha orthogonal to momentum; TSM gate + half gross control crash tail
```

## Theses by status

### keep
- thesis: [baseline/12-1mom/decile/monthly] anchor — algebraic rewrite of pure 12-1 momentum

### discard
- thesis: [vol/12-1mom/inverse-vol/monthly] 63d inverse-vol sizing within top decile dampens blowups
- thesis: [momentum/ra-12-1/decile/monthly] risk-adjust ranks by 252d vol to deprioritize lottery-ticket winners
- thesis: [regime/12-1mom/decile/monthly+DDgate] flat when EW universe DD>10% — avoids momentum-crash rebounds
- thesis: [momentum/12-1/L-S-decile/monthly] dollar-neutral long-short cuts market-beta drawdowns
- thesis: [momentum/12-1+6-1/decile/monthly] blend two lookbacks to reduce rank noise
- thesis: [momentum/12-1/decile/quarterly] quarterly rebalance — let small-cap signal play out, cut whipsaw cost
- thesis: [regime/12-1/decile/monthly+TSMgate] flat when EW universe 252d return negative (Moskowitz TSM)
- thesis: [momentum/3-1/decile/monthly] shorter lookback more responsive at regime turns on slow-diffusion small caps
- thesis: [momentum/3-1/quintile/monthly] 3-1 strong on small caps; quintile stabilizes membership to cut turnover
- thesis: [momentum/3-1/decile/quarterly] 3-1 responsive signal + quarterly reset cuts turnover into budget
- thesis: [momentum+regime/3-1/decile/quarterly+TSMgate] strong IS signal (T11) + TSM DD control (T8) combined
- thesis: [momentum+regime/3-1/decile/quarterly+TSMgate] gate locked at rebal dates to avoid daily whipsaw turnover
- thesis: [momentum/3-1/quintile/quarterly] 3-1 signal + broader quintile breadth + quarterly rebal
- thesis: [momentum/12-1/rank-tilt/monthly] linear rank weighting preserves continuous signal, smooths decile-edge whipsaw
- thesis: [momentum/3-1/decile/quarterly/0.5gross] halve gross — Sharpe is scale-invariant, DD halves
- thesis: [momentum/3-1+12-1/decile/quarterly/0.5gross] two-horizon blend + scaled gross — diversify signal noise while keeping DD headroom
- thesis: [momentum/3-1/decile/monthly/0.5gross] monthly 3-1 + half gross — capture responsive signal with DD headroom
- thesis: [reversal/21d/decile/monthly] short-term mean reversion — retail flow pressure on small caps reverts over 21d
- thesis: [reversal+regime/21d/decile/monthly/0.5gross+TSMgate] STR flow alpha orthogonal to momentum; TSM gate + half gross control crash tail

### crash
