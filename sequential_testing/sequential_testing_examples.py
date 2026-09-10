"""Worked examples for the Sequential Testing article -- why peeking at a
running A/B test breaks your false-positive rate, and the simple fix
(a fixed number of pre-planned looks, Bonferroni-corrected) that lets
you peek safely.

Each function mirrors a section of the article. Run this file directly
to reproduce every number and figure quoted in the issue.
"""

import csv
import numpy as np
import pandas as pd
from scipy.stats import norm
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

INK = "#14181F"
MUTED = "#6B7480"
RULE = "#DDE2E8"
TREAT = "#B4530A"
CTRL = "#64748B"
SURP = "#0E7C6B"
DEF = "#C0392B"

ALPHA = 0.05
BASELINE_RATE = 0.20
DAILY_USERS_PER_ARM = 200
N_DAYS = 30


def two_prop_p_value(x1, n1, x2, n2):
    """Standard two-proportion z-test, two-sided."""
    p1, p2 = x1 / n1, x2 / n2
    p_pool = (x1 + x2) / (n1 + n2)
    se = np.sqrt(p_pool * (1 - p_pool) * (1 / n1 + 1 / n2))
    se = np.where(se == 0, np.nan, se)
    z = (p1 - p2) / se
    return 2 * (1 - norm.cdf(np.abs(z)))


def load_single_experiment(path="data/single_experiment_daily.csv"):
    return pd.read_csv(path)


def bonferroni_corrected_alpha(alpha, k_looks, verbose=True):
    """Step: split your alpha budget evenly across every planned look."""
    corrected = alpha / k_looks
    if verbose:
        print(f"--- Bonferroni correction for {k_looks} planned looks ---")
        print(f"corrected alpha = {alpha} / {k_looks} = {corrected:.4f}")
    return corrected


def simulate_strategies(n_simulations=20000, seed=42, verbose=True):
    """Monte Carlo: simulate many null-true experiments (no real effect),
    and compare how often each stopping strategy falsely declares a win."""
    rng = np.random.default_rng(seed)

    daily_a = rng.binomial(DAILY_USERS_PER_ARM, BASELINE_RATE, size=(n_simulations, N_DAYS))
    daily_b = rng.binomial(DAILY_USERS_PER_ARM, BASELINE_RATE, size=(n_simulations, N_DAYS))
    cum_a = np.cumsum(daily_a, axis=1)
    cum_b = np.cumsum(daily_b, axis=1)
    cum_n = np.arange(1, N_DAYS + 1) * DAILY_USERS_PER_ARM
    cum_n_matrix = np.tile(cum_n, (n_simulations, 1))

    p_values = two_prop_p_value(cum_a, cum_n_matrix, cum_b, cum_n_matrix)

    fpr_fixed = (p_values[:, -1] < ALPHA).mean()
    fpr_daily_naive = (p_values < ALPHA).any(axis=1).mean()

    look_days_idx = [5, 11, 17, 23, 29]  # days 6, 12, 18, 24, 30
    weekly_p = p_values[:, look_days_idx]
    k_looks = len(look_days_idx)
    fpr_weekly_naive = (weekly_p < ALPHA).any(axis=1).mean()

    alpha_corrected = bonferroni_corrected_alpha(ALPHA, k_looks, verbose=verbose)
    fpr_weekly_corrected = (weekly_p < alpha_corrected).any(axis=1).mean()

    results = pd.DataFrame([
        {"strategy": "Fixed horizon (1 look, day 30 only)", "n_looks": 1,
         "alpha_per_look": ALPHA, "false_positive_rate": round(fpr_fixed, 4)},
        {"strategy": "Daily peeking, naive (30 looks)", "n_looks": 30,
         "alpha_per_look": ALPHA, "false_positive_rate": round(fpr_daily_naive, 4)},
        {"strategy": "Weekly peeking, naive (5 looks)", "n_looks": 5,
         "alpha_per_look": ALPHA, "false_positive_rate": round(fpr_weekly_naive, 4)},
        {"strategy": "Weekly peeking, Bonferroni-corrected (5 looks)", "n_looks": 5,
         "alpha_per_look": round(alpha_corrected, 4), "false_positive_rate": round(fpr_weekly_corrected, 4)},
    ])

    if verbose:
        print(f"\n--- Monte Carlo: {n_simulations:,} simulated null-true experiments ---")
        print(results.to_string(index=False))
        print(f"\nDaily naive peeking inflation: {fpr_daily_naive / ALPHA:.2f}x the promised {ALPHA:.0%}")
        print(f"Weekly naive peeking inflation: {fpr_weekly_naive / ALPHA:.2f}x the promised {ALPHA:.0%}")
        print(f"Weekly corrected: {fpr_weekly_corrected:.2%}, safely at or below the promised {ALPHA:.0%}")

    return results


def plot_pvalue_trace(df, save_path="output/pvalue_trace.png"):
    """Fig 1 -- the p-value 'random walk' for one real (null-true) experiment."""
    fig, ax = plt.subplots(figsize=(9.0, 5.4), dpi=200)
    fig.patch.set_facecolor("white")

    ax.plot(df.day, df.p_value, color=CTRL, linewidth=2.2, marker="o", markersize=4.5, zorder=4)
    ax.axhline(0.05, color=DEF, linewidth=1.8, linestyle=(0, (5, 3)), zorder=3, label="Significance threshold (0.05)")

    below = df[df.p_value < 0.05]
    ax.scatter(below.day, below.p_value, color=DEF, s=90, zorder=5,
               edgecolor="white", linewidth=1.3, label="Days a naive peek would \"win\"")

    ax.annotate("Stop here on day 14 and you'd\nship a feature with NO real effect",
                xy=(14, 0.028), xytext=(15.5, 0.35),
                fontsize=9.5, color=DEF, fontweight="bold",
                arrowprops=dict(arrowstyle="-|>", color=DEF, lw=1.6))

    ax.set_xlabel("Day of the experiment", fontsize=11, color=MUTED)
    ax.set_ylabel("p-value (two-proportion z-test)", fontsize=11, color=MUTED)
    ax.set_title("Same experiment, no real effect at all --\nthe p-value still wanders below 0.05 five separate times",
                fontsize=13, color=INK, fontweight="bold", pad=14)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color(RULE)
    ax.spines["bottom"].set_color(RULE)
    ax.tick_params(colors=MUTED, labelsize=10)
    ax.legend(frameon=False, fontsize=9.5, loc="upper right")
    ax.yaxis.grid(True, color=RULE, linewidth=0.8, zorder=0)
    ax.set_axisbelow(True)
    ax.set_ylim(-0.03, 1.05)

    plt.tight_layout()
    plt.savefig(save_path, facecolor="white", bbox_inches="tight")
    plt.close(fig)
    print(f"Saved {save_path}")


def plot_strategy_comparison(results, save_path="output/strategy_comparison.png"):
    """Fig 2 -- observed false-positive rate by stopping strategy."""
    fig, ax = plt.subplots(figsize=(9.0, 5.4), dpi=200)
    fig.patch.set_facecolor("white")

    labels = ["Fixed horizon\n(1 look)", "Daily peeking\nnaive (30 looks)",
              "Weekly peeking\nnaive (5 looks)", "Weekly peeking\nBonferroni (5 looks)"]
    values = results["false_positive_rate"].tolist()
    colors = [SURP, DEF, TREAT, SURP]

    bars = ax.bar(labels, [v * 100 for v in values], color=colors, width=0.6, zorder=3)
    for bar, v in zip(bars, values):
        ax.annotate(f"{v:.1%}", xy=(bar.get_x() + bar.get_width() / 2, bar.get_height()),
                    xytext=(0, 6), textcoords="offset points", ha="center",
                    fontsize=11, fontweight="bold", color=INK)

    ax.axhline(5, color=INK, linewidth=1.6, linestyle=(0, (4, 3)), zorder=2)
    ax.annotate("Promised: 5%", xy=(3.35, 5), xytext=(0, 6), textcoords="offset points",
                fontsize=9.5, color=MUTED, fontweight="bold")

    ax.set_ylabel("False-positive rate observed\n(20,000 simulated experiments, no real effect)", fontsize=10.5, color=MUTED)
    ax.set_title("Peeking without correction breaks your 5% promise --\nBonferroni correction brings it back",
                fontsize=13, color=INK, fontweight="bold", pad=14)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color(RULE)
    ax.spines["bottom"].set_color(RULE)
    ax.tick_params(colors=MUTED, labelsize=10)
    ax.yaxis.grid(True, color=RULE, linewidth=0.8, zorder=0)
    ax.set_axisbelow(True)
    ax.set_ylim(0, max(values) * 100 * 1.25)

    plt.tight_layout()
    plt.savefig(save_path, facecolor="white", bbox_inches="tight")
    plt.close(fig)
    print(f"Saved {save_path}")


if __name__ == "__main__":
    df = load_single_experiment()

    print("=" * 70)
    print("--- Single illustrative experiment (no real effect) ---")
    print(df.to_string(index=False))

    print()
    print("=" * 70)
    results = simulate_strategies()
    results.to_csv("data/monte_carlo_results.csv", index=False)
    print("\nSaved data/monte_carlo_results.csv")

    print()
    print("=" * 70)
    plot_pvalue_trace(df)
    plot_strategy_comparison(results)
