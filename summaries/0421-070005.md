# quant-research/0421-070005

- **UNIVERSE_TAG**: xbi_2026
- **Baseline (seed)**: baseline: 0.429526  (commit bcba0f3)
- **Running best**:   running_best: 0.429526  (commit bcba0f3)
- **Trials logged**:  20
- **Stop reason**:    trial-cap

## results.tsv

```
commit	oos_sharpe	max_dd	turnover	status	description
bcba0f3	0.429526	0.5784	6.84	keep	thesis: [baseline/12-1/topdecile/monthly] algebraic rewrite of decile cutoff, identical behavior
e79eb4f	1.056310	0.6062	20.86	discard	thesis: [reversal/21d/topdecile/monthly] 1-month losers revert in biotech due to event overshoots
2d2cfb5	1.040457	0.6475	6.22	discard	thesis: [reversal/63d/quartile/quarterly] slower mean reversion, quarterly rebal to cut turnover
15c1549	1.020798	0.6274	6.67	discard	thesis: [reversal/63d/invvol/quarterly] 1/vol sizing of losers to damp drawdown tail
3dd6315	0.226121	0.5240	4.74	discard	thesis: [regime/12-1/topdecile/monthly] gate mom off when EW universe in 15% drawdown to cap tail
fa62c18	0.644796	0.1833	1.09	discard	thesis: [lowvol/252d/decile/monthly] long lowest-vol names to avoid binary event losers in biotech
2852f48	0.982549	0.4664	9.03	discard	thesis: [mom/6-1/decile/monthly] shorter-horizon trend around clinical readouts
9b4be92	0.581881	0.2253	1.06	discard	thesis: [lowvol/252d/quintile/quarterly] widen + slow rebal to cut churn in low-vol selection
91aeeb9	0.392285	0.5348	7.26	discard	thesis: [mom/risk-adj-12-1/decile/monthly] rank by Sharpe-style score, prefer quality trenders
4d13f17	-0.880318	0.7557	2.29	discard	thesis: [bab/lowvol-highvol/decile/monthly] market-neutral BAB: short binary-outcome flyers, long stable names
f10b3ee	0.352451	0.4696	5.19	discard	thesis: [regime/mom/200dMA/monthly] MA-trend filter on EW index to sit out bear phases
14ed49a	0.891732	0.7872	3.49	discard	thesis: [highvol/252d/decile/monthly] lottery-premium: upside skew of speculative biotechs earns a risk premium
6cc4c98	0.503257	0.0945	0.55	discard	thesis: [lowvol/252d/decile/half-gross/monthly] halve leverage to pass DD while keeping low-vol signal
e552d4d	0.490613	0.3059	6.07	discard	thesis: [composite/mom+invvol/decile/monthly] quality-momentum picks mature biotech in uptrend
fc20ae4	0.467849	0.6494	1.77	discard	thesis: [mom/12-1/decile/annual] let biotech trenders run a full year, slash turnover
f71fe61	0.805868	0.5923	0.15	discard	thesis: [universe/EW/none/monthly] equal-weight all names - baseline for whether any tilt beats 1/N
f4915e1	0.596182	0.6384	5.12	discard	thesis: [midvol/252d/quintile/monthly] avoid low-alpha stable AND binary-outcome names
ad7e6b4	0.114950	0.3913	4.44	discard	thesis: [regime/mom/voltarget-15%/monthly] scale gross by 1/vol of EW index to tame DD
5396925	0.679586	0.5513	5.25	discard	thesis: [mom/12-1/quintile/monthly] wider selection halves per-name idiosyncratic tail
59ce3ad	0.702677	0.5275	4.31	discard	thesis: [mom/12-1/rank-tilted/long-only/monthly] continuous tilt vs decile cutoff, smoother turnover
```

## Theses by status

### keep
- thesis: [baseline/12-1/topdecile/monthly] algebraic rewrite of decile cutoff, identical behavior

### discard
- thesis: [reversal/21d/topdecile/monthly] 1-month losers revert in biotech due to event overshoots
- thesis: [reversal/63d/quartile/quarterly] slower mean reversion, quarterly rebal to cut turnover
- thesis: [reversal/63d/invvol/quarterly] 1/vol sizing of losers to damp drawdown tail
- thesis: [regime/12-1/topdecile/monthly] gate mom off when EW universe in 15% drawdown to cap tail
- thesis: [lowvol/252d/decile/monthly] long lowest-vol names to avoid binary event losers in biotech
- thesis: [mom/6-1/decile/monthly] shorter-horizon trend around clinical readouts
- thesis: [lowvol/252d/quintile/quarterly] widen + slow rebal to cut churn in low-vol selection
- thesis: [mom/risk-adj-12-1/decile/monthly] rank by Sharpe-style score, prefer quality trenders
- thesis: [bab/lowvol-highvol/decile/monthly] market-neutral BAB: short binary-outcome flyers, long stable names
- thesis: [regime/mom/200dMA/monthly] MA-trend filter on EW index to sit out bear phases
- thesis: [highvol/252d/decile/monthly] lottery-premium: upside skew of speculative biotechs earns a risk premium
- thesis: [lowvol/252d/decile/half-gross/monthly] halve leverage to pass DD while keeping low-vol signal
- thesis: [composite/mom+invvol/decile/monthly] quality-momentum picks mature biotech in uptrend
- thesis: [mom/12-1/decile/annual] let biotech trenders run a full year, slash turnover
- thesis: [universe/EW/none/monthly] equal-weight all names - baseline for whether any tilt beats 1/N
- thesis: [midvol/252d/quintile/monthly] avoid low-alpha stable AND binary-outcome names
- thesis: [regime/mom/voltarget-15%/monthly] scale gross by 1/vol of EW index to tame DD
- thesis: [mom/12-1/quintile/monthly] wider selection halves per-name idiosyncratic tail
- thesis: [mom/12-1/rank-tilted/long-only/monthly] continuous tilt vs decile cutoff, smoother turnover

### crash
