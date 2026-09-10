# Sequential Testing — How to Peek at a Running Experiment Without Breaking It

Companion files for *Analytics Playbook — Sequential Testing: How to Peek at a Running Experiment Without Breaking It*.

This folder reproduces every number and figure in the article: the "p-value random walk" on a single no-real-effect experiment, and a 20,000-run Monte Carlo comparison showing exactly how much peeking inflates your false-positive rate — and how a simple Bonferroni correction brings it back under control.

## Files

| File | Description |
|---|---|
| `sequential_testing_examples.py` | Functions matching the article step for step, plus two plotting functions and the full Monte Carlo simulation. Run directly to reproduce every number and figure in the issue. |
| `data/single_experiment_daily.csv` | The single illustrative experiment — 30 rows, one per day. |
| `data/monte_carlo_results.csv` | Generated when you run `sequential_testing_examples.py` — the 4-strategy false-positive-rate comparison table. |
| `output/` | Where the two figures are saved when you run the script. |

## Quickstart

```bash
pip install numpy pandas scipy matplotlib
python sequential_testing_examples.py
```

## What the simulation models

- **The single experiment (Fig. 1)**: 200 new users/day per arm, both arms converting at a true 20% rate — there is no real effect, by construction. A two-proportion z-test is run on the *cumulative* data after every day. The seed (4) was picked deliberately (by searching seeds in the original exploration script) because it produces a clean, intuitive story: the p-value dips under 0.05 on days 14, 17, 18, 19, and 20, then climbs back to a non-significant 0.106 by day 30.
- **The Monte Carlo comparison (Fig. 2)**: the exact same setup — 200 users/day/arm, true 20% conversion in both arms — repeated 20,000 times with fresh random data each time, testing four different stopping strategies against each other.

## Functions

| Function | What it does (article step) |
|---|---|
| `two_prop_p_value(x1, n1, x2, n2)` | Standard two-proportion z-test, two-sided — the same test run at every look. |
| `bonferroni_corrected_alpha(alpha, k_looks)` | Step 2 — splits the significance budget evenly across the planned number of looks. |
| `simulate_strategies(n_simulations=20000)` | The full Monte Carlo: simulates that many null-true experiments and scores four stopping strategies (fixed horizon, daily naive, weekly naive, weekly Bonferroni-corrected) by how often each falsely declares a winner. |
| `plot_pvalue_trace(df)` | Fig. 1 — the p-value random walk for the single illustrative experiment. |
| `plot_strategy_comparison(results)` | Fig. 2 — false-positive rate by strategy, against the promised 5% line. |

## Real output from this run

```
Strategy                                          Looks   Threshold/look   False "win" rate
Fixed horizon (1 look, day 30 only)                   1        0.05             5.0%
Daily peeking, naive (30 looks)                      30        0.05            27.9%
Weekly peeking, naive (5 looks)                       5        0.05            13.9%
Weekly peeking, Bonferroni-corrected (5 looks)        5        0.01             3.1%
```

Daily naive peeking inflates the false-positive rate to **5.6×** the promised 5%. Even checking just once a week without correcting still triples it. The Bonferroni-corrected version comes back to 3.1% — a little conservative (looks on cumulative data aren't fully independent, so Bonferroni tends to undershoot slightly), but safely under the 5% you're promising, which is the direction you want to be wrong in.

## Adapting this to a real experiment

- Swap `BASELINE_RATE`, `DAILY_USERS_PER_ARM`, and `N_DAYS` in `sequential_testing_examples.py` for your own metric and traffic volume.
- Change `look_days_idx` inside `simulate_strategies()` to match your own planned look schedule — it doesn't have to be weekly.
- For experiments that genuinely need frequent monitoring (fraud, safety, ramping rollouts), look past Bonferroni to purpose-built sequential methods — alpha-spending functions (O'Brien-Fleming, Pocock) or always-valid p-values — which spend the significance budget more efficiently across looks. Bonferroni is the simplest correct method here, not the most powerful one.
- Sample size planning (see Issue 10) and peeking correction are separate problems — this script assumes you've already sized the experiment appropriately; it only fixes how you're allowed to look at it along the way.
