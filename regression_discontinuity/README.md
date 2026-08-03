# 🚦 Regression Discontinuity — Worked Example

Companion code for the **Analytics Playbook** newsletter issue on Regression Discontinuity Design (RDD) — the LoyaltyAir Gold-status case study. One dummy dataset, six clearly separated checks, matching the article section for section.

📬 Read the article: **[Analytics Playbook on LinkedIn](https://www.linkedin.com/newsletters/analytics-playbook-7488645039603101696/)**

---

## 📁 What's in this folder

```
03-regression-discontinuity/
├── README.md                     <- you are here
├── generate_dummy_data.py        <- (re)builds the CSV in /data
├── rdd_examples.py                <- the full worked example, 6 sections
├── data/
│   └── rdd_loyalty_customers.csv
└── output/                       <- created when you run the script
    ├── rdd_discontinuity_plot.png
    └── rdd_density_plot.png
```

All data is **synthetic** — randomly generated with a fixed seed (`generate_dummy_data.py`), calibrated so that, aggregated by points band, it reproduces the same average-spend figures published in the article's table. Nothing here is a real LoyaltyAir customer.

---

## ▶️ How to run it

```bash
pip install pandas numpy matplotlib

python rdd_examples.py
```

This runs the full analysis in order — band summary, the core estimate, the bunching check, the placebo test, the bandwidth sensitivity check, and the two plots — and prints each result to your terminal as it goes.

Want to run just one piece, or drop it into a notebook?

```python
from rdd_examples import load_data, discontinuity_estimate

df = load_data()
result = discontinuity_estimate(df, bandwidth=1000)
print(result["estimate"])   # ≈ £479 / year
```

If you ever want a fresh dataset, rerun `generate_dummy_data.py` — it prints the resulting band averages so you can confirm they still line up with the article.

---

## 🔍 The six sections, one by one

### 1. `band_summary()`
Reproduces the article's headline table — average annual spend by points band. This is the sense-check to run first: spend should rise gently within each status tier, then jump sharply exactly at 10,000 points.

### 2. `discontinuity_estimate()`
The core calculation. Restricts the data to a bandwidth around the cutoff (default ±1,000 points) and compares average spend just below vs. just above 10,000. The difference is the RDD estimate — around **+£479/year** on this dummy data, matching the article's **+£485/year** on the real (larger) dataset.

### 3. `density_bunching_check()`
Tests for the single biggest threat to validity: customers manipulating their score to land just over the line. Bins the running variable (`points_score`) around the cutoff and flags it if the bin just below the cutoff is unusually large relative to its neighbours — the signature of people timing a purchase to cross the threshold on purpose.

### 4. `placebo_cutoff_test()`
Reruns the exact same `discontinuity_estimate()` logic at points values where no rule exists (8,000 / 9,000 / 11,500 / 12,000 by default). A trustworthy design shows small jumps at every placebo cutoff — nowhere near the size of the real one at 10,000.

### 5. `bandwidth_sensitivity()`
Recomputes the estimate across several window sizes (±250 up to ±2,000). A real effect stays roughly stable as the window changes; on this dataset it holds between ~£459 and ~£547 — an estimate that swung wildly instead would mean the window size, not the treatment, was driving the result.

### 6. `simulate_bunching_demo()`
Not part of the main analysis — a teaching aid. Takes a clean copy of the data and artificially moves some customers from just above the cutoff back down to just below it, recreating the exact "spike below, dip above" pattern described in the article. Re-running `density_bunching_check()` on the output correctly flags it as suspicious — this is what section 3 is designed to catch.

```python
from rdd_examples import load_data, simulate_bunching_demo, density_bunching_check

manipulated = simulate_bunching_demo(load_data())
density_bunching_check(manipulated)   # -> flags "SUSPICIOUS"
```

---

## 📊 The plots

`plot_discontinuity()` reproduces Fig. 2 from the article — spend by points band, with the jump at the cutoff visible. `plot_density()` reproduces Fig. 1 — the bin counts used by the bunching check, colour-coded by status and titled in red if manipulation is detected.

---

<sub>Part of the <a href="https://www.linkedin.com/newsletters/analytics-playbook-7488645039603101696/">Analytics Playbook</a> newsletter companion repo.</sub>
