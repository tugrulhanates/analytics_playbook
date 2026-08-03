"""
Customer Segmentation Examples
===============================
Companion script for the Analytics Playbook newsletter issue on customer
segmentation. Three self-contained, clearly named examples, each reading its
own dummy CSV from /data:

    1. rule_based_segmentation()   -> data/rule_based_customers.csv
    2. rfm_segmentation()          -> data/rfm_customers.csv
    3. kmeans_segmentation()       -> data/kmeans_customers.csv

Run the whole file to execute all three examples in order:

    python customer_segmentation_examples.py

Each function can also be imported and run on its own, e.g.:

    from customer_segmentation_examples import rfm_segmentation
    result = rfm_segmentation()
"""

import os
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)


# ===========================================================================
# METHOD 1 — RULE-BASED (DEMOGRAPHIC) SEGMENTATION
# ===========================================================================
# The simplest segmentation method: no models, no scoring — just business
# rules applied directly to raw fields. Here we split customers into four
# groups using two thresholds: age (under/over 30) and annual spend
# (under/over £500). This is the method to reach for when you need something
# explainable in one sentence and don't have much historical behavioural data
# to work with yet.
# ===========================================================================
def rule_based_segmentation():
    df = pd.read_csv(os.path.join(DATA_DIR, "rule_based_customers.csv"))

    def assign_segment(row):
        young = row["age"] < 30
        high_value = row["annual_spend"] >= 500
        if young and high_value:
            return "Young High-Value"
        if young and not high_value:
            return "Young Low-Value"
        if not young and high_value:
            return "Mature High-Value"
        return "Mature Low-Value"

    df["segment"] = df.apply(assign_segment, axis=1)

    print("\n=== METHOD 1: Rule-Based Segmentation ===")
    print(df.head(8).to_string(index=False))
    print("\nSegment sizes:")
    print(df["segment"].value_counts())

    df.to_csv(os.path.join(OUTPUT_DIR, "rule_based_segmented.csv"), index=False)
    return df


# ===========================================================================
# METHOD 2 — RFM SEGMENTATION (Recency, Frequency, Monetary)
# ===========================================================================
# Scores each customer 1-3 on three dimensions:
#   Recency   -> how recently they purchased (lower days = better = higher score)
#   Frequency -> how often they purchase (higher = better = higher score)
#   Monetary  -> how much they've spent in total (higher = better = higher score)
#
# The three scores are summed (range 3-9) and mapped to a named segment.
# This simplified 3-level version is deliberately easier to follow by hand
# than the "classic" 5x5x5 RFM matrix — the same logic scales up by widening
# the score bands and the segment map below.
# ===========================================================================
def score_recency(days):
    if days <= 30:
        return 3
    if days <= 150:
        return 2
    return 1


def score_frequency(count):
    if count >= 10:
        return 3
    if count >= 4:
        return 2
    return 1


def score_monetary(spend):
    if spend >= 1000:
        return 3
    if spend >= 300:
        return 2
    return 1


def map_rfm_segment(total_score):
    if total_score >= 8:
        return "Champions"
    if total_score >= 6:
        return "Loyal Customers"
    if total_score >= 4:
        return "Needs Attention"
    return "Lost"


def rfm_segmentation():
    df = pd.read_csv(os.path.join(DATA_DIR, "rfm_customers.csv"))

    df["r_score"] = df["recency_days"].apply(score_recency)
    df["f_score"] = df["frequency"].apply(score_frequency)
    df["m_score"] = df["monetary"].apply(score_monetary)
    df["rfm_total"] = df["r_score"] + df["f_score"] + df["m_score"]
    df["segment"] = df["rfm_total"].apply(map_rfm_segment)

    print("\n=== METHOD 2: RFM Segmentation ===")
    print("Worked example (first 6 rows match the newsletter article):")
    print(df.head(6).to_string(index=False))
    print("\nSegment sizes (full dataset):")
    print(df["segment"].value_counts())

    df.to_csv(os.path.join(OUTPUT_DIR, "rfm_segmented.csv"), index=False)
    return df


# ===========================================================================
# METHOD 3 — K-MEANS CLUSTERING SEGMENTATION
# ===========================================================================
# An unsupervised method that groups customers by behavioural similarity
# without any predefined rules or score bands. We cluster on two features
# (annual_spend, purchase_frequency) after standardising them — required,
# since K-Means uses distance, and spend (hundreds/thousands) would otherwise
# swamp frequency (single digits). n_clusters=3 is chosen here for the
# newsletter example; in practice, choose it with the elbow method or a
# silhouette score instead of guessing.
# ===========================================================================
def kmeans_segmentation(n_clusters=3, save_plot=True):
    df = pd.read_csv(os.path.join(DATA_DIR, "kmeans_customers.csv"))

    features = df[["annual_spend", "purchase_frequency"]]
    scaled_features = StandardScaler().fit_transform(features)

    model = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    df["cluster"] = model.fit_predict(scaled_features)

    # Label clusters by average spend so names are meaningful, not arbitrary
    # cluster numbers (0/1/2 mean nothing on their own).
    cluster_order = (
        df.groupby("cluster")["annual_spend"].mean().sort_values().index.tolist()
    )
    label_map = {
        cluster_order[0]: "Budget Shoppers",
        cluster_order[1]: "Regular Shoppers",
        cluster_order[2]: "Big Spenders",
    }
    df["segment"] = df["cluster"].map(label_map)

    print("\n=== METHOD 3: K-Means Clustering Segmentation ===")
    print(df.head(8).to_string(index=False))
    print("\nSegment sizes:")
    print(df["segment"].value_counts())

    df.to_csv(os.path.join(OUTPUT_DIR, "kmeans_segmented.csv"), index=False)

    if save_plot:
        INK, MUTED, RULE = "#14181F", "#6B7480", "#DDE2E8"
        colors = {"Budget Shoppers": "#64748B", "Regular Shoppers": "#B4530A", "Big Spenders": "#0E7C6B"}
        segment_order = ["Budget Shoppers", "Regular Shoppers", "Big Spenders"]

        fig, ax = plt.subplots(figsize=(7.4, 4.4), dpi=140)
        fig.patch.set_facecolor("white")
        ax.set_facecolor("white")
        for gv in range(0, 20, 5):
            ax.axhline(gv, color=RULE, linewidth=0.8, zorder=0)

        for segment in segment_order:
            group = df[df["segment"] == segment]
            ax.scatter(group["annual_spend"], group["purchase_frequency"],
                       label=segment, color=colors[segment], alpha=0.85, s=42,
                       edgecolor="white", linewidth=0.6, zorder=3)

        ax.set_xlabel("annual spend (£)", fontsize=10, color=MUTED)
        ax.set_ylabel("purchase frequency (per year)", fontsize=10, color=MUTED)
        ax.set_title("K-Means Customer Segments", fontsize=13, color=INK, fontweight="bold", loc="left")
        for spine in ["top", "right", "left"]:
            ax.spines[spine].set_visible(False)
        ax.spines["bottom"].set_color(INK)
        ax.tick_params(axis="both", length=0, labelsize=9, colors=MUTED)
        ax.legend(frameon=False, fontsize=9.5, labelcolor=MUTED, loc="upper left")
        fig.tight_layout()
        plot_path = os.path.join(OUTPUT_DIR, "kmeans_cluster_plot.png")
        fig.savefig(plot_path, facecolor="white")
        plt.close(fig)
        print(f"\nCluster plot saved to: {plot_path}")

    return df


# ===========================================================================
if __name__ == "__main__":
    rule_based_segmentation()
    rfm_segmentation()
    kmeans_segmentation()
