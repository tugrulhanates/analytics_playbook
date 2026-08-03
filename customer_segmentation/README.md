# 🧩 Customer Segmentation — Worked Examples

Companion code for the **Analytics Playbook** newsletter issue on customer segmentation. Three self-contained, clearly separated segmentation methods, each with its own dummy dataset, so you can run every technique end to end and see exactly how the numbers turn into segments.

📬 Read the article: **[Analytics Playbook on LinkedIn](https://www.linkedin.com/newsletters/analytics-playbook-7488645039603101696/)**

---

## 📁 What's in this folder

```
04-customer-segmentation/
├── README.md                          <- you are here
├── generate_dummy_data.py             <- (re)builds the 3 CSVs in /data
├── customer_segmentation_examples.py  <- the 3 worked examples
├── data/
│   ├── rule_based_customers.csv
│   ├── rfm_customers.csv
│   └── kmeans_customers.csv
└── output/                            <- created when you run the script
    ├── rule_based_segmented.csv
    ├── rfm_segmented.csv
    ├── kmeans_segmented.csv
    └── kmeans_cluster_plot.png
```

All data is **synthetic** — randomly generated with a fixed seed (`generate_dummy_data.py`) purely for learning purposes. Nothing here is a real customer.

---

## ▶️ How to run it

```bash
pip install pandas scikit-learn matplotlib

python customer_segmentation_examples.py
```

This runs all three methods in sequence, prints a preview + segment counts for each to your terminal, and writes the labelled results (plus one chart) to `/output`.

Want to run just one method, or drop it into a notebook?

```python
from customer_segmentation_examples import rfm_segmentation

result = rfm_segmentation()
result.head()
```

If you ever want a fresh/different dummy dataset, rerun `generate_dummy_data.py` — it regenerates all three CSVs from scratch (edit the random seed or the cluster parameters inside it to change the data).

---

## 🔍 The three methods, section by section

### 1. Rule-Based (Demographic) Segmentation
**Data:** `data/rule_based_customers.csv` — `customer_id`, `age`, `annual_spend`
**Function:** `rule_based_segmentation()`

The simplest possible method: no model, no scoring — just an `if/else` on raw fields. Customers are split into four groups by crossing two thresholds (age under/over 30, spend under/over £500). No library beyond `pandas` is needed. This is the method to reach for when you need something you can explain in one sentence, or when you don't have enough purchase history yet for anything behavioural.

### 2. RFM Segmentation (Recency, Frequency, Monetary)
**Data:** `data/rfm_customers.csv` — `customer_id`, `recency_days`, `frequency`, `monetary`
**Function:** `rfm_segmentation()`

Each customer gets a 1–3 score on three dimensions (how recently they bought, how often, how much), the three scores are summed (range 3–9), and the sum maps to a named segment — `Champions`, `Loyal Customers`, `Needs Attention`, or `Lost`. The scoring thresholds and the segment map both live as plain functions at the top of the file (`score_recency`, `score_frequency`, `score_monetary`, `map_rfm_segment`) — edit them directly to match your own business's thresholds.

> The first 6 rows of `rfm_customers.csv` are the exact worked example walked through step by step in the newsletter article — everything after row 6 is extra randomly generated data so you have a realistic-sized dataset to run the method on.

### 3. K-Means Clustering Segmentation
**Data:** `data/kmeans_customers.csv` — `customer_id`, `annual_spend`, `purchase_frequency`
**Function:** `kmeans_segmentation(n_clusters=3, save_plot=True)`

An unsupervised method: instead of predefined rules or score bands, it finds natural groupings in the data by distance. Two steps matter more than the clustering call itself:

1. **Standardise the features first** (`StandardScaler`) — without this, `annual_spend` (hundreds/thousands) completely dominates `purchase_frequency` (single digits) in the distance calculation, and the clusters come out wrong.
2. **Choose `n_clusters` deliberately** — this example hardcodes `3` for teaching purposes. In a real project, use the elbow method or a silhouette score instead of guessing, and sanity-check that the resulting segment sizes are actually usable.

Clusters are relabelled from arbitrary numbers (`0`, `1`, `2`) to meaningful names (`Budget Shoppers`, `Regular Shoppers`, `Big Spenders`) by sorting on mean spend — cluster *numbers* are never stable or meaningful on their own, so never ship them to a stakeholder unlabelled. Running this function also saves `output/kmeans_cluster_plot.png`, the same chart used in the newsletter article.

---

## 🙋 Why three methods, not one

Each one trades off explainability against how well it actually reflects behaviour:

| Method | Explainability | Reflects real behaviour | Needs |
|---|---|---|---|
| Rule-Based | Very high — one sentence | Low | Just the raw fields |
| RFM | High — a documented score table | Medium-high | Purchase history |
| K-Means | Lower — "the model found this group" | Highest | Enough clean, scaled data |

Start with the method that matches how much data you have and how defensible the segments need to be to the people who'll act on them — not with whichever method sounds most sophisticated.

---

<sub>Part of the <a href="https://www.linkedin.com/newsletters/analytics-playbook-7488645039603101696/">Analytics Playbook</a> newsletter companion repo.</sub>
