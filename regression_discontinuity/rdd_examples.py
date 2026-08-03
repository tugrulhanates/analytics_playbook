"""
Regression Discontinuity Examples
===================================
Companion script for the Analytics Playbook newsletter issue on Regression
Discontinuity Design (RDD) -- the LoyaltyAir Gold-status case study.

Reads one dummy dataset (data/rdd_loyalty_customers.csv) and walks through
every check discussed in the article, each as its own clearly named
function:

    1. band_summary()              -> reproduces the article's band table
    2. discontinuity_estimate()    -> the core +£485/year RDD calculation
    3. density_bunching_check()    -> tests for manipulation at the cutoff
    4. placebo_cutoff_test()       -> checks for false jumps elsewhere
    5. bandwidth_sensitivity()     -> tests how the estimate holds up
    6. simulate_bunching_demo()    -> shows what a FAILED check looks like

Run the whole file to execute the full analysis in order:

    python rdd_examples.py

Each function can also be imported and run on its own, e.g.:

    from rdd_examples import discontinuity_estimate, load_data
    result = discontinuity_estimate(load_data())
"""

import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

CUTOFF = 10000

INK, MUTED, RULE = "#14181F", "#6B7480", "#DDE2E8"
CTRL, TREAT, SURP, DEF = "#64748B", "#B4530A", "#0E7C6B", "#C0392B"


def load_data():
    return pd.read_csv(os.path.join(DATA_DIR, "rdd_loyalty_customers.csv"))


# ===========================================================================
# 1. BAND SUMMARY
# ===========================================================================
# Reproduces the article's headline table: average annual spend by points
# band. Useful as a sense check before running anything else -- the raw
# numbers should show a small, steady increase within each status tier, then
# a large jump exactly at the 10,000-point cutoff.
# ===========================================================================
def band_summary(df):
    bins = [7000, 8000, 9000, 9500, 10000, 10500, 11000, 12000, 15000]
    labels = ["7000-7999", "8000-8999", "9000-9499", "9500-9999",
              "10000-10499", "10500-10999", "11000-11999", "12000+"]
    df = df.copy()
    df["band"] = pd.cut(df["points_score"], bins=bins, labels=labels,
                         right=False, include_lowest=True)
    summary = df.groupby("band", observed=True)["annual_spend"].agg(
        n="count", avg_spend="mean"
    ).round(2)

    print("\n=== 1. Band Summary ===")
    print(summary)
    return summary


# ===========================================================================
# 2. DISCONTINUITY ESTIMATE (the core RDD calculation)
# ===========================================================================
# Restricts the data to a bandwidth around the cutoff, then compares the
# average spend just below vs. just above 10,000 points. The difference is
# the RDD estimate -- the Local Average Treatment Effect (LATE) of Gold
# status near the threshold. This mirrors the article's worked example
# exactly (Silver 9,000-9,999 vs. Gold 10,000-10,999 at bandwidth=1000).
# ===========================================================================
def discontinuity_estimate(df, bandwidth=1000, cutoff=CUTOFF, verbose=True):
    window = df[(df["points_score"] >= cutoff - bandwidth) &
                (df["points_score"] < cutoff + bandwidth)]
    below = window[window["points_score"] < cutoff]["annual_spend"]
    above = window[window["points_score"] >= cutoff]["annual_spend"]

    estimate = above.mean() - below.mean()

    if verbose:
        print(f"\n=== 2. Discontinuity Estimate (bandwidth = ±{bandwidth}) ===")
        print(f"Below cutoff:  n={len(below):>4}  avg spend=£{below.mean():.2f}")
        print(f"Above cutoff:  n={len(above):>4}  avg spend=£{above.mean():.2f}")
        print(f"RDD estimate (jump at cutoff): £{estimate:.2f} / year")

    return {"bandwidth": bandwidth, "below_mean": below.mean(),
            "above_mean": above.mean(), "estimate": estimate,
            "n_below": len(below), "n_above": len(above)}


# ===========================================================================
# 3. DENSITY / BUNCHING CHECK
# ===========================================================================
# The key threat to validity in RDD: customers manipulating their own score
# to land just above the cutoff. If that's happening, the bin just below the
# cutoff will hold noticeably fewer customers than expected, and/or the bin
# just above will hold noticeably more, relative to neighbouring bins.
#
# This is a simplified, teaching version of a formal density (McCrary) test:
# it compares the customer count in the bin immediately below the cutoff to
# the average count of its two neighbouring bins on the same side, and flags
# a result if the ratio looks suspicious.
# ===========================================================================
def density_bunching_check(df, bin_width=200, cutoff=CUTOFF, flag_ratio=1.5):
    edges = np.arange(cutoff - bin_width * 4, cutoff + bin_width * 4 + 1, bin_width)
    counts, _ = np.histogram(df["points_score"], bins=edges)
    bin_labels = [f"{edges[i]}-{edges[i+1]-1}" for i in range(len(edges) - 1)]

    just_below_idx = np.searchsorted(edges, cutoff) - 1
    neighbours = [c for i, c in enumerate(counts)
                  if i in (just_below_idx - 1, just_below_idx - 2) and i >= 0]
    neighbour_avg = np.mean(neighbours) if neighbours else np.nan
    just_below_count = counts[just_below_idx]
    ratio = just_below_count / neighbour_avg if neighbour_avg else np.nan

    suspicious = ratio > flag_ratio if not np.isnan(ratio) else False

    print("\n=== 3. Density / Bunching Check ===")
    for label, count in zip(bin_labels, counts):
        marker = "  <- just below cutoff" if label == bin_labels[just_below_idx] else ""
        print(f"{label:>15}: {count:>4} customers{marker}")
    print(f"\nRatio (bin just below cutoff vs. its neighbours): {ratio:.2f}")
    print("Result:", "SUSPICIOUS - possible manipulation, investigate further"
          if suspicious else "No sign of bunching.")

    return {"bin_labels": bin_labels, "counts": counts.tolist(),
            "ratio": ratio, "suspicious": suspicious}


# ===========================================================================
# 4. PLACEBO CUTOFF TEST
# ===========================================================================
# Reruns the exact same discontinuity_estimate() logic at points values
# where no rule exists. A trustworthy design should show a jump close to
# zero at every placebo cutoff -- if it doesn't, the method is picking up a
# pre-existing trend or noise, not the effect of Gold status.
# ===========================================================================
def placebo_cutoff_test(df, fake_cutoffs=(8000, 9000, 11500, 12000), bandwidth=500):
    print("\n=== 4. Placebo Cutoff Test ===")
    results = []
    for fake_cutoff in fake_cutoffs:
        result = discontinuity_estimate(df, bandwidth=bandwidth, cutoff=fake_cutoff, verbose=False)
        print(f"Placebo cutoff at {fake_cutoff:>6}: jump = £{result['estimate']:>7.2f}"
              f"  (real cutoff jump for comparison: see section 2)")
        results.append({"cutoff": fake_cutoff, **result})
    return results


# ===========================================================================
# 5. BANDWIDTH SENSITIVITY
# ===========================================================================
# Recomputes the RDD estimate across several bandwidths. A real effect stays
# roughly stable as the window changes; an estimate that swings wildly is a
# sign the window size -- not the treatment -- is driving the result.
# ===========================================================================
def bandwidth_sensitivity(df, bandwidths=(250, 500, 1000, 1500, 2000)):
    print("\n=== 5. Bandwidth Sensitivity ===")
    results = []
    for bw in bandwidths:
        result = discontinuity_estimate(df, bandwidth=bw, verbose=False)
        print(f"Bandwidth ±{bw:>5}: estimate = £{result['estimate']:>7.2f}"
              f"   (n_below={result['n_below']}, n_above={result['n_above']})")
        results.append(result)
    return results


# ===========================================================================
# 6. SIMULATE BUNCHING (demo of a FAILED check)
# ===========================================================================
# Not part of the main analysis -- a teaching aid, matching the "spike just
# below the cutoff, with a corresponding dip just after" pattern described
# in the article. Takes a copy of the clean dataset and artificially moves
# some customers who were *just about* to reach Gold (just above the cutoff)
# back down to just below it -- simulating customers who stalled right under
# the line while trying, unsuccessfully, to time a purchase to cross it.
# Re-running density_bunching_check() on this copy should now show a spike
# in the bin just below 10,000 and a dip in the bin just above it.
# ===========================================================================
def simulate_bunching_demo(df, n_to_move=25, seed=1):
    rng = np.random.default_rng(seed)
    df = df.copy()
    candidates = df[(df["points_score"] >= CUTOFF) & (df["points_score"] < CUTOFF + 150)].index
    move_idx = rng.choice(candidates, size=min(n_to_move, len(candidates)), replace=False)
    df.loc[move_idx, "points_score"] = rng.integers(CUTOFF - 100, CUTOFF, size=len(move_idx))
    df.loc[move_idx, "status"] = "Silver"
    return df


# ===========================================================================
# PLOTS
# ===========================================================================
def plot_discontinuity(df, save_path=None):
    summary = band_summary(df.copy()) if save_path else band_summary(df)
    x = list(range(len(summary)))
    spend = summary["avg_spend"].values
    silver_x, silver_y = x[:4], spend[:4]
    gold_x, gold_y = x[4:], spend[4:]

    fig, ax = plt.subplots(figsize=(7.4, 4.2), dpi=140)
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")
    for gv in np.arange(min(spend) - 100, max(spend) + 200, 200):
        ax.axhline(gv, color=RULE, linewidth=0.8, zorder=0)

    ax.plot(silver_x, silver_y, color=CTRL, linewidth=2.4, marker="o", markersize=6.5,
            markerfacecolor=CTRL, markeredgecolor="white", zorder=3, label="Silver")
    ax.plot(gold_x, gold_y, color=TREAT, linewidth=2.4, marker="o", markersize=6.5,
            markerfacecolor=TREAT, markeredgecolor="white", zorder=3, label="Gold")
    ax.axvline(3.5, color=INK, linewidth=1.1, linestyle=(0, (2, 3)), alpha=0.7)
    ax.set_xticks(x)
    ax.set_xticklabels(summary.index, fontsize=8, color=MUTED, rotation=20)
    ax.set_ylabel("avg. annual spend (£)", fontsize=9.5, color=MUTED)
    ax.set_title("RDD: Spend by Points Band", fontsize=13, color=INK, fontweight="bold", loc="left")
    for spine in ["top", "right", "left"]:
        ax.spines[spine].set_visible(False)
    ax.spines["bottom"].set_color(INK)
    ax.tick_params(axis="both", length=0, colors=MUTED)
    ax.legend(frameon=False, fontsize=9.5, labelcolor=MUTED)
    fig.tight_layout()

    path = save_path or os.path.join(OUTPUT_DIR, "rdd_discontinuity_plot.png")
    fig.savefig(path, facecolor="white")
    plt.close(fig)
    print(f"\nDiscontinuity plot saved to: {path}")


def plot_density(df, save_path=None):
    result = density_bunching_check(df)
    edges_mid = range(len(result["counts"]))
    just_below_idx = result["bin_labels"].index(
        [l for l in result["bin_labels"] if l.endswith(str(CUTOFF - 1))][0]
    )
    colors = [DEF if i == just_below_idx and result["suspicious"] else
              (CTRL if i <= 3 else TREAT) for i in edges_mid]

    fig, ax = plt.subplots(figsize=(7.4, 4.0), dpi=140)
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")
    ax.bar(edges_mid, result["counts"], color=colors, zorder=3)
    ax.set_xticks(list(edges_mid))
    ax.set_xticklabels(result["bin_labels"], fontsize=7.5, color=MUTED, rotation=35, ha="right")
    ax.set_ylabel("customers", fontsize=9.5, color=MUTED)
    title_color = DEF if result["suspicious"] else SURP
    ax.set_title("Density Check: Customers Near the Cutoff", fontsize=13,
                 color=title_color, fontweight="bold", loc="left")
    for spine in ["top", "right", "left"]:
        ax.spines[spine].set_visible(False)
    ax.spines["bottom"].set_color(INK)
    ax.tick_params(axis="both", length=0, colors=MUTED)
    fig.tight_layout()

    path = save_path or os.path.join(OUTPUT_DIR, "rdd_density_plot.png")
    fig.savefig(path, facecolor="white")
    plt.close(fig)
    print(f"Density plot saved to: {path}")


# ===========================================================================
if __name__ == "__main__":
    data = load_data()

    band_summary(data)
    discontinuity_estimate(data, bandwidth=1000)
    density_bunching_check(data)
    placebo_cutoff_test(data)
    bandwidth_sensitivity(data)

    plot_discontinuity(data)
    plot_density(data)

    print("\n=== 6. Bunching demo (teaching aid, not part of the main analysis) ===")
    manipulated = simulate_bunching_demo(data)
    density_bunching_check(manipulated)
