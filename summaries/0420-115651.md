# quant-research/0420-115651

- **UNIVERSE_TAG**: ndx100_2024
- **Baseline (seed)**: baseline: 0.941195  (commit 6d43765)
- **Running best**:   running_best: 0.941195  (commit 6d43765)
- **Trials logged**:  20
- **Stop reason**:    trial-cap

## results.tsv

```
commit	oos_sharpe	max_dd	turnover	status	description
6d43765	0.941195	0.4223	6.79	keep	thesis: baseline 12-1 momentum top decile equal-weight (AST-neutral anchor)
bdb26a3	0.998624	0.2899	6.99	discard	thesis: risk-adjusted momentum (mom / 252d vol) filters out one-off spikes that tend to mean-revert
bf31694	1.062077	0.3422	8.22	discard	thesis: 6-1 momentum captures faster tech cycles better than 12-1 on NDX
58fd624	0.868214	0.3736	8.37	discard	thesis: inverse-vol sizing within decile stabilizes risk allocation given NDX vol dispersion
a26ae14	0.837947	0.3618	5.60	discard	thesis: top quintile diversifies single-stock noise vs. decile on 100-name universe
e06bf41	1.020104	0.3978	5.87	discard	thesis: universe-DD regime gate at 10% sits out momentum crashes (risk-off shields capital)
0b8a20f	0.998198	0.3976	91.13	discard	thesis: 5d reversal captures liquidity-provision premium on crowded index names (weekly rebal)
793ccc6	0.871137	0.4751	20.75	discard	thesis: 21d reversal on monthly losers captures short-horizon mispricing from flow pressure
192f005	0.552748	0.3114	1.80	discard	thesis: low-vol anomaly (leverage-constrained investors overpay for high-beta) on NDX
2132391	0.979095	0.5060	4.97	discard	thesis: 2y momentum captures structural secular winners with less noise than 12-1
00d8a32	0.992898	0.3932	8.24	discard	thesis: require both 12-1 momentum rank and price above 200d SMA (active uptrend)
f7b2703	0.923680	0.3528	9.22	discard	thesis: consensus across 3/6/12-month momentum horizons filters out lucky single-window winners
ad023d5	-0.078821	0.3792	6.76	discard	thesis: long-short 12-1 captures cross-sectional spread with beta neutrality
893d5e6	0.923980	0.3921	3.88	discard	thesis: quarterly rebal cuts turnover cost on slow 12-1 signal without losing information
404917c	0.941195	0.4223	6.79	discard	thesis: residual (demeaned) momentum isolates idiosyncratic winners in broad-rally regimes
ecef2db	0.502610	0.3323	10.30	discard	thesis: low-vol gate on momentum filters meme/narrative winners, keeps structural compounders
1dfcce2	0.509758	0.3383	16.38	discard	thesis: 52w high proximity (George-Hwang) captures anchor-based attention bias; dominates raw momentum
06b2d4f	1.258982	0.3028	11.90	discard	thesis: acceleration (6-1 rank rising vs 12-1 rank) flags emerging winners over faded past-winners
2bba7a1	0.755991	0.3393	5.97	discard	thesis: wider top-30% portfolio with inverse-vol sizing reduces concentration risk at portfolio scale
8d45002	0.948308	0.4232	6.79	discard	thesis: rank-tilted weights within top decile — ordering inside the winning cohort still carries signal
```

## Theses by status

### keep
- thesis: baseline 12-1 momentum top decile equal-weight (AST-neutral anchor)

### discard
- thesis: risk-adjusted momentum (mom / 252d vol) filters out one-off spikes that tend to mean-revert
- thesis: 6-1 momentum captures faster tech cycles better than 12-1 on NDX
- thesis: inverse-vol sizing within decile stabilizes risk allocation given NDX vol dispersion
- thesis: top quintile diversifies single-stock noise vs. decile on 100-name universe
- thesis: universe-DD regime gate at 10% sits out momentum crashes (risk-off shields capital)
- thesis: 5d reversal captures liquidity-provision premium on crowded index names (weekly rebal)
- thesis: 21d reversal on monthly losers captures short-horizon mispricing from flow pressure
- thesis: low-vol anomaly (leverage-constrained investors overpay for high-beta) on NDX
- thesis: 2y momentum captures structural secular winners with less noise than 12-1
- thesis: require both 12-1 momentum rank and price above 200d SMA (active uptrend)
- thesis: consensus across 3/6/12-month momentum horizons filters out lucky single-window winners
- thesis: long-short 12-1 captures cross-sectional spread with beta neutrality
- thesis: quarterly rebal cuts turnover cost on slow 12-1 signal without losing information
- thesis: residual (demeaned) momentum isolates idiosyncratic winners in broad-rally regimes
- thesis: low-vol gate on momentum filters meme/narrative winners, keeps structural compounders
- thesis: 52w high proximity (George-Hwang) captures anchor-based attention bias; dominates raw momentum
- thesis: acceleration (6-1 rank rising vs 12-1 rank) flags emerging winners over faded past-winners
- thesis: wider top-30% portfolio with inverse-vol sizing reduces concentration risk at portfolio scale
- thesis: rank-tilted weights within top decile — ordering inside the winning cohort still carries signal

### crash
