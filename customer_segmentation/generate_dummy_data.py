"""
Generates the three dummy CSV datasets used by customer_segmentation_examples.py.
Run this once to (re)create the /data files. Uses a fixed random seed so the
numbers in the newsletter article and the script always match.
"""

import numpy as np
import pandas as pd
import os

np.random.seed(42)
OUT_DIR = os.path.join(os.path.dirname(__file__), "data")
os.makedirs(OUT_DIR, exist_ok=True)


# ---------------------------------------------------------------------------
# 1. Rule-Based Segmentation data
#    Simple demographic + spend fields, no scoring math required.
# ---------------------------------------------------------------------------
def make_rule_based_data(n=40):
    ages = np.random.randint(18, 70, size=n)
    annual_spend = np.round(np.random.gamma(shape=2.2, scale=250, size=n), 2)
    df = pd.DataFrame({
        "customer_id": [f"C{i+1:03d}" for i in range(n)],
        "age": ages,
        "annual_spend": annual_spend,
    })
    return df


# ---------------------------------------------------------------------------
# 2. RFM Segmentation data
#    First 6 rows are the exact worked example used in the newsletter article
#    (kept fixed, not random) so readers can follow along by hand, then the
#    rest of the rows are randomly generated to give the script a realistic
#    dataset to run at scale.
# ---------------------------------------------------------------------------
def make_rfm_data(n_random=34):
    worked_example = pd.DataFrame({
        "customer_id": ["C001", "C002", "C003", "C004", "C005", "C006"],
        "recency_days": [5, 340, 20, 90, 10, 60],
        "frequency": [12, 1, 8, 2, 15, 5],
        "monetary": [1450, 60, 890, 150, 2100, 500],
    })

    random_ids = [f"C{i+7:03d}" for i in range(n_random)]
    random_rows = pd.DataFrame({
        "customer_id": random_ids,
        "recency_days": np.random.randint(1, 400, size=n_random),
        "frequency": np.random.randint(1, 20, size=n_random),
        "monetary": np.round(np.random.gamma(shape=2.0, scale=300, size=n_random), 2),
    })

    return pd.concat([worked_example, random_rows], ignore_index=True)


# ---------------------------------------------------------------------------
# 3. K-Means Segmentation data
#    Two features (annual_spend, purchase_frequency) generated from three
#    distinct underlying clusters, so the resulting plot has clearly
#    separated groups for teaching purposes.
# ---------------------------------------------------------------------------
def make_kmeans_data():
    n_per_cluster = 25

    budget = pd.DataFrame({
        "annual_spend": np.random.normal(220, 40, n_per_cluster).clip(min=20),
        "purchase_frequency": np.random.normal(3, 1, n_per_cluster).clip(min=1),
    })
    regular = pd.DataFrame({
        "annual_spend": np.random.normal(900, 90, n_per_cluster).clip(min=20),
        "purchase_frequency": np.random.normal(9, 1.5, n_per_cluster).clip(min=1),
    })
    big_spenders = pd.DataFrame({
        "annual_spend": np.random.normal(2200, 200, n_per_cluster).clip(min=20),
        "purchase_frequency": np.random.normal(14, 2, n_per_cluster).clip(min=1),
    })

    df = pd.concat([budget, regular, big_spenders], ignore_index=True)
    df.insert(0, "customer_id", [f"C{i+1:03d}" for i in range(len(df))])
    df["annual_spend"] = df["annual_spend"].round(2)
    df["purchase_frequency"] = df["purchase_frequency"].round(1)
    return df.sample(frac=1, random_state=42).reset_index(drop=True)  # shuffle


if __name__ == "__main__":
    make_rule_based_data().to_csv(os.path.join(OUT_DIR, "rule_based_customers.csv"), index=False)
    make_rfm_data().to_csv(os.path.join(OUT_DIR, "rfm_customers.csv"), index=False)
    make_kmeans_data().to_csv(os.path.join(OUT_DIR, "kmeans_customers.csv"), index=False)
    print("Dummy CSV files written to:", OUT_DIR)
