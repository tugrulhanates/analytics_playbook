"""
Cohort Analysis Examples
==========================
Companion script for the Analytics Playbook newsletter issue on why grouping
hosts by signup vintage reveals retention problems a blended average hides.

Reads one dummy dataset (data/host_cohort_events.csv) and walks through
every calculation discussed in the article, each as its own clearly named
function:

    1. build_retention_matrix()      -> the classic cohort triangle
    2. retention_at_fixed_tenure()   -> comparing cohorts fairly, by tenure
    3. blended_active_rate()         -> the single number a dashboard shows
    4. flag_vintage_decline()        -> which cohort the problem started in
    5. simulate_recovery_scenario()  -> how a fix would show up (or not)

Run the whole file to execute the full analysis in order:

    python cohort_analysis_examples.py

Each function can also be imported and run on its own, e.g.:

    from cohort_analysis_examples import load_data, retention_at_fixed_tenure
    df = load_data()
    retention_at_fixed_tenure(df, tenure=1)
"""

import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.cm as cm

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

INK, MUTED, RULE = "#14181F", "#6B7480", "#DDE2E8"
TREAT, SURP, DEF = "#B4530A", "#0E7C6B", "#C0392B"

COHORTS = ["2026-01", "2026-02", "2026-03", "2026-04", "2026-05", "2026-06"]
MAX_OBSERVABLE_TENURE = {"2026-01": 6, "2026-02": 5, "2026-03": 4,
                          "2026-04": 3, "2026-05": 2, "2026-06": 1}
# Calendar month each tenure snapshot corresponds to, for the blended trend
CALENDAR_MONTHS = ["2026-01", "2026-02", "2026-03", "2026-04", "2026-05", "2026-06", "2026-07"]


def load_data():
    df = pd.read_csv(os.path.join(DATA_DIR, "host_cohort_events.csv"), dtype={"churned_month_offset": "object"})
    df["churned_month_offset"] = pd.to_numeric(df["churned_month_offset"], errors="coerce")
    return df


def _retention_pct(df, cohort, tenure):
    """% of a cohort still active at a given months-since-signup, or None if not yet observable."""
    if tenure > MAX_OBSERVABLE_TENURE[cohort]:
        return None
    sub = df[df["signup_month"] == cohort]
    churned_by_tenure = sub["churned_month_offset"].notna() & (sub["churned_month_offset"] <= tenure)
    return round(100 * (1 - churned_by_tenure.mean()), 1)


# ===========================================================================
# 1. RETENTION MATRIX (the classic cohort triangle)
# ===========================================================================
# Rows are signup cohorts, columns are months-since-signup. Cells are blank
# where a cohort hasn't reached that tenure yet -- that triangular shape is
# not a data quality issue, it's the correct, honest shape of cohort data.
# ===========================================================================
def build_retention_matrix(df, max_tenure=6):
    matrix = pd.DataFrame(index=COHORTS, columns=range(max_tenure + 1), dtype=float)
    for cohort in COHORTS:
        for t in range(max_tenure + 1):
            matrix.loc[cohort, t] = _retention_pct(df, cohort, t)

    print("\n=== 1. Retention Matrix ===")
    print(matrix.to_string())
    return matrix


# ===========================================================================
# 2. RETENTION AT FIXED TENURE (comparing cohorts fairly)
# ===========================================================================
# Pulls one column out of the matrix -- every cohort's retention at the same
# months-since-signup. This is the only fair way to compare vintages: Jan
# has had 6 months to churn and May has had 2, so comparing their raw
# "active today" numbers tells you nothing about which onboarding was
# actually better.
# ===========================================================================
def retention_at_fixed_tenure(df, tenure=1):
    print(f"\n=== 2. Retention at Month {tenure}, by Cohort ===")
    values = {}
    for cohort in COHORTS:
        pct = _retention_pct(df, cohort, tenure)
        if pct is not None:
            values[cohort] = pct
            print(f"  {cohort}: {pct}%")
    first, last = list(values.values())[0], list(values.values())[-1]
    print(f"\nDecline from first to most recent cohort: {first - last:.1f} points")
    return values


# ===========================================================================
# 3. BLENDED ACTIVE RATE (the number a dashboard actually shows)
# ===========================================================================
# The weighted-average "% of all hosts still active" as of each calendar
# month -- mixing cohorts of very different ages together. This is usually
# the only retention number that makes it onto a leadership dashboard.
# ===========================================================================
def blended_active_rate(df):
    print("\n=== 3. Blended Active Rate, by Calendar Month ===")
    results = {}
    for i, calendar_month in enumerate(CALENDAR_MONTHS):
        total, active = 0, 0
        for j, cohort in enumerate(COHORTS):
            tenure = i - j
            if tenure < 0:
                continue  # cohort doesn't exist yet
            sub = df[df["signup_month"] == cohort]
            n = len(sub)
            churned = (sub["churned_month_offset"].notna() & (sub["churned_month_offset"] <= tenure)).sum()
            total += n
            active += (n - churned)
        if total > 0:
            pct = round(100 * active / total, 1)
            results[calendar_month] = pct
            print(f"  {calendar_month}: {pct}%  ({active}/{total} hosts active)")
    return results


# ===========================================================================
# 4. FLAG VINTAGE DECLINE
# ===========================================================================
# Confirms the fixed-tenure decline is a real, sustained trend -- not one
# noisy cohort -- by checking that retention drops for at least
# `min_consecutive` cohorts in a row, and reports which cohort it started
# with. That's the actionable output: not "retention is down," but
# "the problem started with the April cohort."
# ===========================================================================
def flag_vintage_decline(df, tenure=1, min_consecutive=3, drop_threshold=1.0):
    values = retention_at_fixed_tenure(df, tenure=tenure)
    cohorts = list(values.keys())
    pcts = list(values.values())

    print(f"\n=== 4. Vintage Decline Check (tenure={tenure} months) ===")
    streak = 1
    decline_start = None
    for i in range(1, len(pcts)):
        if pcts[i] < pcts[i - 1] - drop_threshold:
            streak += 1
            if streak == 2:
                decline_start = cohorts[i - 1]
        else:
            streak = 1
            decline_start = None

        if streak >= min_consecutive and decline_start:
            print(f"Sustained decline confirmed: {streak} consecutive cohorts falling, "
                  f"starting with {decline_start}.")
            return {"confirmed": True, "started_at": decline_start, "streak": streak}

    print("No sustained decline meeting the threshold was found.")
    return {"confirmed": False}


# ===========================================================================
# 5. SIMULATE RECOVERY SCENARIO (a teaching aid, not part of the core analysis)
# ===========================================================================
# Not part of the main analysis. Models what happens if a fix shipped and
# a hypothetical July cohort recovered to the Jan cohort's original
# performance -- and shows how long it takes that recovery to visibly move
# the blended metric, given how much of the base is still older cohorts.
# The same lag that hides decline also hides recovery.
# ===========================================================================
def simulate_recovery_scenario(df, recovered_m1=96, new_cohort_size=800):
    values = retention_at_fixed_tenure(df, tenure=1)
    print(f"\n=== 5. Recovery Scenario (hypothetical July cohort recovers to {recovered_m1}% month-1 retention) ===")

    total_hosts = len(df)
    # crude approximation: blended M1-equivalent before vs after adding the recovered cohort
    before_avg = sum(values.values()) / len(values)
    after_avg = (before_avg * total_hosts + recovered_m1 * new_cohort_size) / (total_hosts + new_cohort_size)

    print(f"Blended month-1 retention across existing cohorts: {before_avg:.1f}%")
    print(f"Blended month-1 retention after adding one recovered cohort: {after_avg:.1f}%")
    print(f"Visible movement in the blended number from ONE good cohort: {after_avg - before_avg:.1f} points")
    print("...which is why one good month never looks like proof of a fix -- "
          "and one bad month shouldn't either.")
    return {"before": before_avg, "after": after_avg}


# ===========================================================================
# PLOTS
# ===========================================================================
def plot_blended_trend(df, save_path=None):
    results = blended_active_rate(df)

    fig, ax = plt.subplots(figsize=(7.2, 4.0), dpi=140)
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")
    for gv in range(70, 105, 5):
        ax.axhline(gv, color=RULE, linewidth=0.8, zorder=0)

    months = list(results.keys())
    values = list(results.values())
    ax.plot(months, values, color=TREAT, linewidth=2.6, marker="o",
            markersize=6, markerfacecolor=INK, markeredgecolor="white", zorder=3)

    ax.set_ylabel("% of all hosts still active", fontsize=9.5, color=MUTED)
    ax.set_title("What the Dashboard Shows: Blended Active Rate", fontsize=12.5, color=INK,
                 fontweight="bold", loc="left")
    ax.set_ylim(70, 102)
    for spine in ["top", "right", "left"]:
        ax.spines[spine].set_visible(False)
    ax.spines["bottom"].set_color(INK)
    ax.tick_params(axis="both", length=0, colors=MUTED, labelsize=9)
    fig.tight_layout()

    path = save_path or os.path.join(OUTPUT_DIR, "blended_trend.png")
    fig.savefig(path, facecolor="white")
    plt.close(fig)
    print(f"\nBlended trend plot saved to: {path}")


def plot_cohort_curves(df, save_path=None):
    matrix = build_retention_matrix(df)

    fig, ax = plt.subplots(figsize=(7.6, 4.6), dpi=140)
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")
    for gv in range(65, 105, 5):
        ax.axhline(gv, color=RULE, linewidth=0.8, zorder=0)

    colors = [SURP, "#3E8E8A", MUTED, "#A0764A", TREAT, DEF]
    for i, cohort in enumerate(COHORTS):
        row = matrix.loc[cohort].dropna()
        ax.plot(row.index, row.values, color=colors[i], linewidth=2.2, marker="o",
                markersize=5, markerfacecolor=colors[i], markeredgecolor="white",
                zorder=3, label=cohort)

    ax.set_xlabel("months since signup", fontsize=9.5, color=MUTED)
    ax.set_ylabel("% still active", fontsize=9.5, color=MUTED)
    ax.set_title("Cohort Retention Curves", fontsize=13, color=INK, fontweight="bold", loc="left")
    ax.set_ylim(65, 102)
    for spine in ["top", "right", "left"]:
        ax.spines[spine].set_visible(False)
    ax.spines["bottom"].set_color(INK)
    ax.tick_params(axis="both", length=0, colors=MUTED, labelsize=9)
    ax.legend(frameon=False, fontsize=8.5, labelcolor=MUTED, loc="lower left", ncol=2)
    fig.tight_layout()

    path = save_path or os.path.join(OUTPUT_DIR, "cohort_curves.png")
    fig.savefig(path, facecolor="white")
    plt.close(fig)
    print(f"Cohort curves plot saved to: {path}")


# ===========================================================================
if __name__ == "__main__":
    data = load_data()

    build_retention_matrix(data)
    retention_at_fixed_tenure(data, tenure=1)
    blended_active_rate(data)
    flag_vintage_decline(data, tenure=1)
    simulate_recovery_scenario(data)

    plot_blended_trend(data)
    plot_cohort_curves(data)
