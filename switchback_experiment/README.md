# Switchback Experiment (Time-Based Randomisation)

Companion files for *Analytics Playbook — The Switchback Experiment: Time-Based Randomisation for Marketplaces*.

This folder simulates a surge-pricing switchback test on a ride-sharing marketplace and reproduces every number and figure quoted in the article: the naive (biased) pooled analysis, the washout correction, the block-level analysis with the right unit of inference, the zone-level heterogeneity check, and the carry-over diagnostic.

## Files

| File | Description |
|---|---|
| `switchback_examples.py` | Six functions matching the article section for section, plus two plotting functions. Run directly to reproduce every number and figure in the issue. |
| `data/switchback_intervals.csv` | Generated dummy dataset — 24,192 rows (6 zones × 336 blocks × 12 five-minute intervals). |
| `output/` | Where the two figures are saved when you run the script. |

## Quickstart

```bash
pip install numpy pandas matplotlib
python switchback_examples.py
```

## What the simulation models

- **6 zones**, each with its own steady-state control wait time (3.7–6.1 min) and its own treatment effect (a −3% to −13% relative reduction in wait time), so the data has the same kind of cross-market heterogeneity a real switchback test would show.
- **336 one-hour blocks per zone** (14 days × 24 hours), with assignment to Treatment or Control drawn independently per block — not a fixed alternating pattern.
- **Carry-over**: whenever a block's assignment differs from the block before it, the first 15 minutes blend the previous block's steady-state wait time into the new one, decaying linearly to the new steady state. Blocks where the assignment didn't change show no transition effect. This is what makes the washout and carry-over diagnostic functions meaningful on the dummy data, not just decorative.

## Functions

| Function | What it does |
|---|---|
| `naive_pooled_lift(df)` | Pools every 5-minute interval, including carry-over-contaminated ones, and computes a treatment effect with an interval-level standard error. This is the analysis most teams run first — and it's biased twice over. |
| `apply_washout(df, washout_minutes=15)` | Drops the first N minutes of every block to remove carry-over contamination. |
| `block_level_lift(df_washed)` | Aggregates to one row per (zone, block) — the true unit of randomisation — and computes the effect with a block-level standard error. This is the number that should actually be reported. |
| `zone_level_heterogeneity(df_washed)` | Reproduces the per-zone lift table, showing how much the pooled effect can hide. |
| `carryover_diagnostic(df)` | For every block transition, compares the last 10 minutes of the old block to the first 10 minutes of the new one — the same check used to decide whether a washout is needed and how long it should be. |
| `plot_carryover_curve(df)` | Line chart of average wait time by minute-into-block, split by transition type — the visual version of the carry-over diagnostic. |
| `plot_zone_heterogeneity(zone_result)` | Bar chart of lift % by zone. |

## Real output from this dataset

```
Naive pooled:     control 4.80 min, treatment 4.47 min, lift -6.9%, t = -32.9  (n = 24,192 intervals)
Washout:          drops 6,048 of 24,192 intervals (25%)
Corrected:        control 4.84 min, treatment 4.43 min, lift -8.4%, t = -12.2  (n = 2,016 blocks)

Zone heterogeneity (lift vs. control):
  Phoenix  -13.1%      Austin  -11.1%      Miami  -10.0%
  Denver    -9.3%      Seattle  -4.0%      Boston   -3.2%

Carry-over diagnostic:
  Control -> Treatment: prev block last 10min = 4.90 min, new block first 10min = 4.79 min, gap = -0.11 min
  Treatment -> Control: prev block last 10min = 4.46 min, new block first 10min = 4.53 min, gap = +0.07 min
```

The gap between the naive (−6.9%) and corrected (−8.4%) lift is the carry-over bias described in the article: contamination in the un-washed data pulls the naive estimate toward zero. The gap between the naive t-stat (−32.9) and the block-level t-stat (−12.2) is the clustering correction — both are still statistically significant here, but the naive figure vastly overstates confidence by treating 24,192 correlated intervals as independent draws instead of the 2,016 blocks they actually come from.

## Adapting this to a real switchback test

- Swap `wait_time_min` for your own outcome metric, and `zone` for your actual market/geo unit.
- If your real transaction log doesn't come pre-aggregated into fixed intervals, aggregate it to whatever grain lets you see the carry-over decay clearly — 5-minute intervals worked well here for 60-minute blocks.
- Set `washout_minutes` based on how long your treatment mechanism actually takes to ramp up and down, not an arbitrary default — that's a design decision to make (and pre-register) before the test runs, not after looking at results.
- Always report `zone_level_heterogeneity()` (or your market-level equivalent) alongside the pooled number — see the article's Fig. 2 for why.
