# 📈 Cohort Analysis — Worked Example

Companion code for the **Analytics Playbook** newsletter issue on why grouping hosts by signup vintage reveals retention problems a blended average hides. One dummy dataset, five functions, two charts.

📬 Read the article: **[Analytics Playbook on LinkedIn](https://www.linkedin.com/newsletters/analytics-playbook-7488645039603101696/)**

---

## 📁 What's in this folder

```
06-cohort-analysis/
├── README.md                        <- you are here        <- (re)builds the CSV in /data
├── cohort_analysis_examples.py      <- the full worked example, 5 sections
├── data/
│   └── host_cohort_events.csv
└── output/                          <- created when you run the script
    ├── blended_trend.png
    └── cohort_curves.png
```

All data is **synthetic** — six monthly signup cohorts (Jan–Jun 2026) simulated with a fixed seed, each with its own hidden survival curve. Nothing here is a real company's host data.

---

## ▶️ How to run it

```bash
pip install pandas numpy matplotlib

python cohort_analysis_examples.py
```

This runs the full analysis in order — the retention matrix, the fixed-tenure comparison, the blended trend, the decline check, and the recovery scenario — then saves both plots.

Want to run just one piece, or drop it into a notebook?

```python
from cohort_analysis_examples import load_data, retention_at_fixed_tenure

df = load_data()
retention_at_fixed_tenure(df, tenure=1)   # {'2026-01': 94.0, ..., '2026-06': 79.5}
```

If you ever want a fresh dataset, rerun `generate_dummy_data.py` — it prints month-1 retention by cohort so you can confirm the decline pattern still holds.

---

## 🔍 The five sections, one by one

### 1. `build_retention_matrix()`
Reproduces the classic cohort triangle: rows are signup cohorts, columns are months-since-signup, cells are % still active. Blank cells aren't missing data — they're tenure a cohort genuinely hasn't reached yet. That triangular shape is the correct, honest shape of cohort data.

### 2. `retention_at_fixed_tenure()`
Pulls one column out of the matrix: every cohort's retention at the same months-since-signup. This is the only fair way to compare vintages — on this data, month-1 retention holds roughly flat through February (94.0% → 94.5%), then drops every cohort after: 89.2% → 86.4% → 83.1% → 79.5%. A 14.5-point decline from the healthiest cohort to the most recent.

### 3. `blended_active_rate()`
The number that usually makes it onto a dashboard: the weighted-average "% of all hosts active" as of each calendar month, mixing cohorts of very different ages together. It declines too (100% → 75% over six months) — smoothly enough that it could pass for ordinary, expected aging rather than a new, worsening problem.

### 4. `flag_vintage_decline()`
Confirms the fixed-tenure decline is a real, sustained trend — not one noisy cohort — by checking for consecutive drops past a threshold. On this data it reports retention held steady through the **2026-02** cohort, then declined in every cohort since. That's the actionable output: not "retention is down," but *which vintage it started with*.

### 5. `simulate_recovery_scenario()`
Not part of the core analysis — a teaching aid. Models what happens to the blended metric if a hypothetical future cohort fully recovered to the best historical performance. On this data, one good cohort moves the blended number by about 1 point — which is exactly why one good (or bad) month is never enough evidence on its own; the same lag that hides decline also hides recovery.

```python
from cohort_analysis_examples import load_data, simulate_recovery_scenario

df = load_data()
simulate_recovery_scenario(df, recovered_m1=96)
```

---

## 📊 The plots

`plot_blended_trend()` reproduces Fig. 1 from the article — the single line a leadership dashboard usually shows. `plot_cohort_curves()` reproduces Fig. 2 — the cohort fan chart that reveals what the blended line can't: each vintage since March retaining worse than the one before it, at the same age.

---

<sub>Part of the <a href="https://www.linkedin.com/newsletters/analytics-playbook-7488645039603101696/">Analytics Playbook</a> newsletter companion repo.</sub>
