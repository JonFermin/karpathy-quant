# quant-research/0420-115114

- **UNIVERSE_TAG**: sp500_2024
- **Baseline (seed)**: baseline: 0.938614  (commit f39a0c0)
- **Running best**:   running_best: 0.938614  (commit f39a0c0)
- **Trials logged**:  20
- **Stop reason**:    trial-cap reached (20); no subsequent hypothesis beat baseline OOS on SP500 under strict-honesty

## results.tsv

```
commit	oos_sharpe	max_dd	turnover	status	description
f39a0c0	0.938614	0.3833	6.09	keep	thesis: baseline anchor — algebraic no-op over 12-1 momentum top decile on SP500
c73198f	0.757366	0.3843	7.35	discard	thesis: risk-adjusted momentum — score by 12-1 return / 12m vol to penalize choppy winners
4b1d71f	0.817523	0.3789	7.69	discard	thesis: inverse-vol sizing within top-decile to dampen choppy-winner drawdown contribution
0d3c2e9	0.884552	0.2573	8.48	discard	thesis: regime gate — flat when equal-weight breadth index >15% below trailing 252d peak; cheapest crash hedge for pro-cyclical momentum
1140670	0.814912	0.3716	10.07	discard	thesis: dual-horizon momentum — require persistence across 12-1 and 3-1 via average rank
30e5109	-0.142733	0.2988	6.36	discard	thesis: long-short market-neutral momentum to isolate cross-sectional premium (classic Jegadeesh-Titman)
a8d4d4a	0.798420	0.2548	12.25	discard	thesis: dual-horizon momentum combined with breadth-drawdown regime gate — signal quality plus tail-risk control
3708214	0.808611	0.3690	5.38	discard	thesis: widen top-decile to top-quintile for breadth — spread momentum premium across ~100 carriers to reduce single-name risk
8eaa9ed	0.956175	0.3568	8.88	discard	thesis: 6-1 momentum — faster 6m lookback catches sector-leadership rotation while preserving 1m reversal skip
b672d36	0.944464	0.2238	11.06	discard	thesis: 6-1 momentum plus breadth-drawdown regime gate — faster signal tamed by crash-regime filter
9ff3851	0.937899	0.3639	5.05	discard	thesis: 6-1 momentum with quarterly rebalance — cut turnover while signal decays slowly enough to preserve premium
4db0dc0	0.948363	0.3874	6.07	discard	thesis: residual momentum — rank 12-1 momentum on beta-neutralized (demeaned) returns to isolate idiosyncratic alpha
a6b1dde	0.908566	0.3790	9.50	discard	thesis: 12-1 momentum confirmed by positive 3m — drop names whose great year is rolling over
52e9b03	0.506544	0.5028	20.58	discard	thesis: 21d reversal — long bottom decile of last-month return; flow/liquidity overshoots mean-revert
1f9c173	0.702516	0.3961	18.65	discard	thesis: trend-and-dip — 12-1 momentum plus 21d reversal: long-term winners that pulled back recently
40c97a7	0.633982	0.3862	7.06	discard	thesis: 12-1 momentum restricted to lowest-vol 90% — drop lottery-tickets that add noise to the top decile
b318515	0.995690	0.3762	12.71	discard	thesis: 3-1 momentum — 3m lookback for faster continuation capture
06502af	0.999621	0.2666	14.68	discard	thesis: 3-1 momentum with breadth-dd regime gate — fast signal gated for crash regimes
2d5866a	0.952849	0.3716	10.91	discard	thesis: dual-fast-horizon momentum — average rank of 6-1 and 3-1 to extract shared continuation signal
6ae9df4	0.936882	0.2490	13.02	discard	thesis: dual-fast momentum (6+3 avg rank) combined with breadth-drawdown regime gate — best IS signal plus tail hedge
```

## Theses by status

### keep
- thesis: baseline anchor — algebraic no-op over 12-1 momentum top decile on SP500

### discard
- thesis: risk-adjusted momentum — score by 12-1 return / 12m vol to penalize choppy winners
- thesis: inverse-vol sizing within top-decile to dampen choppy-winner drawdown contribution
- thesis: regime gate — flat when equal-weight breadth index >15% below trailing 252d peak; cheapest crash hedge for pro-cyclical momentum
- thesis: dual-horizon momentum — require persistence across 12-1 and 3-1 via average rank
- thesis: long-short market-neutral momentum to isolate cross-sectional premium (classic Jegadeesh-Titman)
- thesis: dual-horizon momentum combined with breadth-drawdown regime gate — signal quality plus tail-risk control
- thesis: widen top-decile to top-quintile for breadth — spread momentum premium across ~100 carriers to reduce single-name risk
- thesis: 6-1 momentum — faster 6m lookback catches sector-leadership rotation while preserving 1m reversal skip
- thesis: 6-1 momentum plus breadth-drawdown regime gate — faster signal tamed by crash-regime filter
- thesis: 6-1 momentum with quarterly rebalance — cut turnover while signal decays slowly enough to preserve premium
- thesis: residual momentum — rank 12-1 momentum on beta-neutralized (demeaned) returns to isolate idiosyncratic alpha
- thesis: 12-1 momentum confirmed by positive 3m — drop names whose great year is rolling over
- thesis: 21d reversal — long bottom decile of last-month return; flow/liquidity overshoots mean-revert
- thesis: trend-and-dip — 12-1 momentum plus 21d reversal: long-term winners that pulled back recently
- thesis: 12-1 momentum restricted to lowest-vol 90% — drop lottery-tickets that add noise to the top decile
- thesis: 3-1 momentum — 3m lookback for faster continuation capture
- thesis: 3-1 momentum with breadth-dd regime gate — fast signal gated for crash regimes
- thesis: dual-fast-horizon momentum — average rank of 6-1 and 3-1 to extract shared continuation signal
- thesis: dual-fast momentum (6+3 avg rank) combined with breadth-drawdown regime gate — best IS signal plus tail hedge

### crash
