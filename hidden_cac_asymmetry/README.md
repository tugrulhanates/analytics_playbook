# 💸 The Hidden Asymmetry in CAC — Worked Example

Companion code for the **Analytics Playbook** newsletter issue on why supply-side (host) customer acquisition cost is quietly much higher than the number on most marketplace dashboards. One core idea, six functions, two dummy datasets.

📬 Read the article: **[Analytics Playbook on LinkedIn](https://www.linkedin.com/newsletters/analytics-playbook-7488645039603101696/)**

---

## 📁 What's in this folder

```
05-hidden-cac-asymmetry/
├── README.md                        <- you are here         <- (re)builds the CSVs in /data
├── cac_asymmetry_examples.py        <- the full worked example, 6 sections
├── data/
│   ├── marketing_spend_acquisitions.csv
│   └── host_ramp_productivity.csv
└── output/                          <- created when you run the script
    ├── cac_ramp_curve.png
    └── cac_comparison.png
```

All data is **synthetic** — randomly generated with a fixed seed (`generate_dummy_data.py`). Nothing here is a real company's spend or revenue figures.

---

## ▶️ How to run it

```bash
pip install pandas matplotlib

python cac_asymmetry_examples.py
```

This runs the full analysis in order and prints each result as it goes — nominal CAC, the ramp curve, the shortfall, the effective CAC, the churn replacement cost, and the faster-ramp scenario — then saves both plots.

Want to run just one piece, or drop it into a notebook?

```python
from cac_asymmetry_examples import load_data, effective_cac

spend_df, ramp_df = load_data()
result = effective_cac(spend_df, ramp_df)
print(result["effective"])   # {'guest': 30.11, 'host': 534.38}
```

If you ever want a fresh dataset, rerun `generate_dummy_data.py` — it prints the resulting nominal CAC so you can confirm it still lands near £30 (guest) and £150 (host).

---

## 🔍 The six sections, one by one

### 1. `nominal_cac()`
The number everyone already tracks: total spend ÷ total acquisitions, by side. On this dummy data, guest CAC is ~£30 and host CAC is ~£149 — a 4.9x gap that already looks meaningful, before you've found the part that's actually hidden.

### 2. `host_ramp_curve()`
Average host revenue by month-since-signup, expressed as a % of steady state. Steady state is **estimated empirically** from months 4–6 of the data, not assumed — a new host doesn't reach full productivity until roughly month 4 on this dataset.

### 3. `ramp_shortfall_per_host()`
The £ value given up during those first four months: steady-state revenue minus what was actually earned, summed. This is the part a nominal-CAC dashboard never shows — about **£386 per host** here.

### 4. `effective_cac()`
Nominal CAC + ramp shortfall, side by side. Guests don't ramp, so their effective CAC equals their nominal CAC. Hosts do — pushing effective host CAC to roughly **£534**, and the real gap from **4.9x to 17.7x**.

### 5. `churn_replacement_cost()`
What it actually costs to replace one churned, already-productive host: the full effective CAC has to be paid again, because the replacement starts the ramp from zero — before counting the booking gap while the listing sits vacant, or the trust signals (reviews, ranking) the departing host took with them.

### 6. `faster_ramp_scenario()`
Not part of the core analysis — a teaching aid. Models what happens to the shortfall if a hypothetical onboarding improvement compressed the ramp period by half. On this data it unlocks roughly **£252 of value per host** — the kind of number that turns "onboarding support" from a cost center into an investment case.

```python
from cac_asymmetry_examples import load_data, faster_ramp_scenario

_, ramp_df = load_data()
faster_ramp_scenario(ramp_df, compression=0.5)
```

---

## 📊 The plots

`plot_ramp_curve()` reproduces Fig. 1 from the article — host productivity as a % of steady state over time, with the ramp period shaded and a flat guest line for comparison. `plot_cac_comparison()` reproduces Fig. 2 — nominal CAC stacked against the hidden ramp cost, for both sides.

---

<sub>Part of the <a href="https://www.linkedin.com/newsletters/analytics-playbook-7488645039603101696/">Analytics Playbook</a> newsletter companion repo.</sub>
