# quant-research/0421-070004

- **UNIVERSE_TAG**: ndx100_2024
- **Baseline (seed)**: baseline: 0.941195  (commit 40e6f62)
- **Running best**:   running_best: 0.941195  (commit 40e6f62)
- **Trials logged**:  20
- **Stop reason**:    trial-cap

## results.tsv

```
commit	oos_sharpe	max_dd	turnover	status	description
40e6f62	0.941195	0.4223	6.79	keep	thesis: [baseline/12-1mom/equal/monthly] algebraic rewrite anchor
a9522a2	0.888423	0.3642	8.31	discard	thesis: [momentum/12-1/inverse-vol/monthly] dampen tech-heavy whipsaw by downweighting high-vol names
37a694d	1.062077	0.3422	8.22	discard	thesis: [momentum/6-1/equal/monthly] shorter horizon captures faster info flow in tech names
2d9448f	0.871137	0.4751	20.75	discard	thesis: [reversal/21d/equal/monthly] ETF flow-driven mean reversion in overextended NDX names
fc7ec43	0.998624	0.2899	6.99	discard	thesis: [risk-adj-momentum/12-1/equal/monthly] reward quality of trend not magnitude
7b2b682	0.909986	0.3668	12.07	discard	thesis: [momentum/12-1/equal/weekly/quintile] faster rebalance + broader basket for tech trend compounding
0402a15	1.159972	0.3137	5.15	discard	thesis: [regime/12-1-mom+DD-gate/equal/monthly] avoid momentum crashes when tech basket in 10% drawdown
fdd19ef	-0.078821	0.3792	6.76	discard	thesis: [momentum/12-1/long-short/monthly] market-neutral spread captures pure momentum
52911da	1.033826	0.3963	6.54	discard	thesis: [momentum/12-0/equal/monthly] no skip for persistent tech uptrends
89631f6	0.520947	0.2938	2.88	discard	thesis: [low-vol/252d/equal/monthly] quality subset of NDX pays off on risk-adjusted basis
046f052	0.604705	0.4063	6.70	discard	thesis: [trend-consistency/252d/equal/monthly] fraction of up-days measures trend quality
84ce0d3	1.335636	0.3427	11.69	discard	thesis: [momentum/3-1/equal/monthly] intermediate horizon for tech trend compounding
c37fd90	0.856210	0.2204	3.40	discard	thesis: [leverage/12-1/equal/monthly/0.5gross] half-cash to dampen drawdown
e40e252	1.046857	0.4404	6.79	discard	thesis: [momentum/12-1/rank-tilted/monthly] linear tilt within decile captures cross-sectional gradient
b471e54	0.998198	0.3976	91.13	discard	thesis: [reversal/5d/equal/weekly] short-term flow-driven mean reversion in NDX names
7da3e96	0.460374	0.2891	6.83	discard	thesis: [composite/12-1mom+lowvol/equal/monthly] diversify signal sources for robustness
3328579	0.923980	0.3921	3.88	discard	thesis: [momentum/12-1/equal/quarterly] slower cadence captures longer-persistent trends, cuts turnover
2bd0ed3	0.909444	0.2589	16.21	discard	thesis: [proximity-to-high/252d/equal/monthly] 52w-high proximity as trend-persistence proxy
23fca4c	0.816785	0.3503	4.80	discard	thesis: [momentum/12-1/equal/monthly/3-decile] broader basket reduces tech concentration risk
bda8d6a	0.941195	0.4223	6.79	discard	thesis: [momentum/12-1/equal/monthly/abs-filter] require positive absolute mom to avoid bear-regime buys
```

## Theses by status

### keep
- thesis: [baseline/12-1mom/equal/monthly] algebraic rewrite anchor

### discard
- thesis: [momentum/12-1/inverse-vol/monthly] dampen tech-heavy whipsaw by downweighting high-vol names
- thesis: [momentum/6-1/equal/monthly] shorter horizon captures faster info flow in tech names
- thesis: [reversal/21d/equal/monthly] ETF flow-driven mean reversion in overextended NDX names
- thesis: [risk-adj-momentum/12-1/equal/monthly] reward quality of trend not magnitude
- thesis: [momentum/12-1/equal/weekly/quintile] faster rebalance + broader basket for tech trend compounding
- thesis: [regime/12-1-mom+DD-gate/equal/monthly] avoid momentum crashes when tech basket in 10% drawdown
- thesis: [momentum/12-1/long-short/monthly] market-neutral spread captures pure momentum
- thesis: [momentum/12-0/equal/monthly] no skip for persistent tech uptrends
- thesis: [low-vol/252d/equal/monthly] quality subset of NDX pays off on risk-adjusted basis
- thesis: [trend-consistency/252d/equal/monthly] fraction of up-days measures trend quality
- thesis: [momentum/3-1/equal/monthly] intermediate horizon for tech trend compounding
- thesis: [leverage/12-1/equal/monthly/0.5gross] half-cash to dampen drawdown
- thesis: [momentum/12-1/rank-tilted/monthly] linear tilt within decile captures cross-sectional gradient
- thesis: [reversal/5d/equal/weekly] short-term flow-driven mean reversion in NDX names
- thesis: [composite/12-1mom+lowvol/equal/monthly] diversify signal sources for robustness
- thesis: [momentum/12-1/equal/quarterly] slower cadence captures longer-persistent trends, cuts turnover
- thesis: [proximity-to-high/252d/equal/monthly] 52w-high proximity as trend-persistence proxy
- thesis: [momentum/12-1/equal/monthly/3-decile] broader basket reduces tech concentration risk
- thesis: [momentum/12-1/equal/monthly/abs-filter] require positive absolute mom to avoid bear-regime buys

### crash
