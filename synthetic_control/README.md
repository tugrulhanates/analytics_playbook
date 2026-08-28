# How to Create a Synthetic Control

Companion files for *Analytics Playbook — Issue 11 — How to Create a Synthetic Control*.

This folder builds a synthetic control step by step on a small, toy dataset, and reproduces every number and figure quoted in the article.

## Files

| File | Description |
|---|---|
| `synthetic_control_examples.py` | Functions matching the article step for step, plus two plotting functions and a bonus general-purpose optimizer. Run directly to reproduce every number and figure in the issue. |
| `data/rideco_weekly_rides.csv` | Generated dummy dataset — 12 rows (weeks 1–12), Austin/Denver/Phoenix weekly rides in thousands. |
| `output/` | Where the two figures are saved when you run the script. |

## Quickstart

```bash
pip install numpy pandas scipy matplotlib
python synthetic_control_examples.py
```

## What the dataset models

Austin's pre-treatment (weeks 1–8) rides are constructed as an exact blend — 60% Denver, 40% Phoenix — so the grid search in the article has a single, clean answer to find (pre-period fit error hits exactly 0.0 at the true weight). Weeks 9–12 continue Denver's and Phoenix's own trends untouched, then add a real, **growing** treatment effect to Austin only (+2, +3, +4, +5 thousand rides across the four pilot weeks) — so you can watch the actual-vs-synthetic gap widen exactly the way a ramping intervention would in real data.

## Functions

| Function | What it does (article step) |
|---|---|
| `pre_period_fit(weight_denver, df)` | Steps 2–3 — builds a synthetic series for one candidate weight and scores it (sum of squared errors) against actual pre-period Austin. |
| `grid_search_weights(df, step=0.05)` | Step 3 — sweeps candidate weights from 0 to 1 and returns the full grid plus the best-fitting weight. |
| `solve_weights_general(df)` | Bonus — solves the same problem with `scipy.optimize` (SLSQP, weights constrained to be non-negative and sum to 1) instead of a grid search. This is what you'd actually use with more than two or three donors, where a manual sweep stops being practical. |
| `build_synthetic_series(df, weight_denver)` | Step 4 — applies the winning weight across all 12 weeks (pre and post) to build the full synthetic Austin counterfactual. |
| `compute_treatment_effect(df_with_synthetic)` | Step 5 — actual minus synthetic, post-treatment weeks only, plus the average and total effect. |
| `plot_weight_search(grid, best_weight)` | Fig. 1 — the U-shaped curve showing why weight_denver = 0.60 wins. |
| `plot_actual_vs_synthetic(df_with_synthetic)` | Fig. 2 — the classic synthetic-control chart: actual vs. synthetic Austin, with the post-period gap shaded. |

## Real output from this dataset

```
Grid search: best weight_denver = 0.60 (weight_phoenix = 0.40), SSE = 0.0000
General optimizer (scipy SLSQP): weight_denver = 0.6000, weight_phoenix = 0.4000, SSE = 0.000000

Treatment effect, post-pilot weeks:
 week  austin_actual  synthetic_austin  effect
    9           28.8              26.8     2.0
   10           30.9              27.9     3.0
   11           33.0              29.0     4.0
   12           35.1              30.1     5.0

Average weekly effect: 3.50k rides
Total effect across the pilot: 14.00k rides
```

The grid search and the general optimizer agree exactly, as they should — they're solving the same problem two different ways. The grid search is what the article walks through by hand because it's easy to picture; the optimizer is what you'd actually run once you have more than two or three donors, since sweeping every combination of weights stops being practical fast.

## Adapting this to a real synthetic control

- Swap in your own treated unit and donor pool — `solve_weights_general()` already generalizes to any number of donor columns, not just two.
- Real applications usually match on more than just the lagged outcome — add other pre-treatment predictors (demographics, other business metrics) as extra columns in the `donors` matrix inside `solve_weights_general()`.
- Always check the pre-period fit (the SSE at the best weight) before trusting the post-period gap. A poor fit here means a poor counterfactual, no matter how compelling the post-period gap looks.
- Run a placebo test before presenting results: relabel one of your donors as if it were "treated," rebuild its own synthetic control from the remaining units, and confirm it doesn't show a gap of similar size.
