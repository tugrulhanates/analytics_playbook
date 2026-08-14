# CUPED Calculation for Variance Reduction

Companion files for *Analytics Playbook — How to Run a CUPED Calculation for Variance Reduction in Data Experiments*.

This folder walks through Controlled-experiment Using Pre-Experiment Data (CUPED) step by step on a small, fully worked dataset, and reproduces every number and figure quoted in the article.

## Files

| File | Description |
|---|---|
| `cuped_examples.py` | Seven functions matching the article step for step, plus two plotting functions. Run directly to reproduce every number and figure in the issue. |
| `data/cuped_streaming_sessions.csv` | Generated dummy dataset — 20 rows. |
| `output/` | Where the two figures are saved when you run the script. |

## Quickstart

```bash
pip install numpy pandas scipy matplotlib
python cuped_examples.py
```

## What the dataset models

Every user's pre-experiment session count (X) is identical between arms — 4, 8, 3, 10, 5, 7, 2, 9, 6, 6 — assigned to 10 control users and repeated for 10 treatment users. Post-experiment sessions (Y) follow the same pattern plus a constant **+2** for every treatment user. This means the true effect is known exactly (+2), so you can watch CUPED go from "can't detect it" to "detects it clearly" on data where you already know the right answer.

## Functions

| Function | What it does (article step) |
|---|---|
| `covariate_grand_mean(df)` | Step 1 — E[X], the grand mean of the covariate across both arms. |
| `covariance_and_variance(df, x_mean)` | Step 2 — Cov(Y,X), Var(X), Var(Y). |
| `compute_theta(cov_xy, var_x)` | Step 3 — theta = Cov(Y,X) / Var(X), the CUPED adjustment coefficient. |
| `pearson_r_and_variance_reduction(cov_xy, var_x, var_y)` | Step 4 — Pearson r and the variance reduction (r²) CUPED will achieve. |
| `adjust_outcome(df, theta, x_mean)` | Step 5 — computes Y̅ = Y − theta×(X−E[X]) for every user. |
| `compare_raw_vs_adjusted(df)` | Step 6 — two-sample t-test on raw Y and on adjusted Y̅, side by side. |
| `run_cuped(df)` | Runs all six steps end to end and returns the full result set. |
| `plot_covariate_scatter(df, r)` | Y vs. X scatter with the pooled regression line — why the covariate works. |
| `plot_raw_vs_adjusted(df)` | Before/after strip plot of raw Y vs. adjusted Y̅ by arm — the visual payoff. |

## Real output from this dataset

```
Step 1: E[X] = 6.000
Step 2: E[Y] = 7.800, Cov(Y,X) = 6.100, Var(X) = 6.000, Var(Y) = 7.360
Step 3: theta = 1.0167
Step 4: r = 0.918, variance reduction = 84.3%

Step 6 — Raw vs. adjusted:
                     Raw Y      Adjusted Y
Control mean         6.800      6.800
Treatment mean       8.800      8.800
Effect               2.000      2.000
Within-arm variance  7.067      0.176
t-statistic          1.682      10.662
p-value              0.1098     ~0.0000
```

The raw t-test can't distinguish the true +2-session effect from noise (p ≈ 0.11). After CUPED, the same effect is overwhelmingly significant (p ≪ 0.0001) — with the point estimate completely unchanged. That's the whole method: same signal, far less noise around it.

## Adapting this to a real experiment

- Swap `x_pre_sessions` / `y_post_sessions` for your own pre-period and experiment-period metrics — ideally the same metric, one period apart.
- Always compute `theta` on pooled data across both arms (as `covariance_and_variance()` and `compute_theta()` do here) — never fit it separately per arm.
- Check `pearson_r_and_variance_reduction()` before adopting a covariate for a new metric. A rule of thumb: r > 0.3 (≥9% variance reduction) is usually worth it; this example's r = 0.918 is unusually strong because it was built to make the mechanism obvious.
- Decide explicitly how to handle users with no pre-experiment history (new signups, etc.) before you run this on real data — `adjust_outcome()` assumes every row has a valid `x_pre_sessions` value.
