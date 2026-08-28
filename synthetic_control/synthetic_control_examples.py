"""Worked examples for the Synthetic Control article -- how to build a
"fake" version of a treated unit out of untreated donors, and use it
as the counterfactual.

Each function mirrors one step of the article. Run this file directly
to reproduce every number and figure quoted in the issue.
"""

import numpy as np
import pandas as pd
from scipy.optimize import minimize
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

TREATMENT_START_WEEK = 9


def load_data(path="data/rideco_weekly_rides.csv"):
    return pd.read_csv(path)


def pre_period_fit(weight_denver, df, verbose=False):
    """Step 2/3 -- for one candidate weight, build the synthetic pre-period
    series and score it by sum of squared errors (SSE) against actual Austin."""
    pre = df[~df.post_treatment]
    weight_phoenix = 1 - weight_denver
    synthetic = weight_denver * pre.denver_rides_k + weight_phoenix * pre.phoenix_rides_k
    errors = pre.austin_rides_k - synthetic
    sse = (errors ** 2).sum()

    if verbose:
        print(f"--- Pre-period fit for weight_denver={weight_denver:.2f}, weight_phoenix={weight_phoenix:.2f} ---")
        out = pd.DataFrame({
            "week": pre.week, "austin_actual": pre.austin_rides_k.round(2),
            "synthetic": synthetic.round(2), "error": errors.round(2), "error_sq": (errors ** 2).round(3),
        })
        print(out.to_string(index=False))
        print(f"SSE = {sse:.4f}")

    return sse


def grid_search_weights(df, step=0.05, verbose=True):
    """Step 3 -- sweep candidate weights from 0 to 1, score each by
    pre-period fit, and return the full grid plus the best weight."""
    weights = np.round(np.arange(0.0, 1.0 + step / 2, step), 2)
    sse_values = [pre_period_fit(w, df) for w in weights]
    grid = pd.DataFrame({"weight_denver": weights, "sse": sse_values})
    best_row = grid.loc[grid.sse.idxmin()]

    if verbose:
        print("--- Grid search over candidate weights ---")
        print(grid.to_string(index=False))
        print(f"\nBest weight_denver = {best_row.weight_denver:.2f} "
              f"(weight_phoenix = {1 - best_row.weight_denver:.2f}), SSE = {best_row.sse:.4f}")

    return grid, best_row.weight_denver


def solve_weights_general(df, verbose=True):
    """Bonus -- how you'd actually solve this with a real optimizer (needed
    once you have more than a couple of donors). Constrained to weights
    that are non-negative and sum to 1, exactly like the grid search, just
    solved directly instead of by trial and error."""
    pre = df[~df.post_treatment]
    donors = np.column_stack([pre.denver_rides_k, pre.phoenix_rides_k])
    target = pre.austin_rides_k.values

    def objective(w):
        synthetic = donors @ w
        return np.sum((target - synthetic) ** 2)

    n_donors = donors.shape[1]
    w0 = np.repeat(1 / n_donors, n_donors)
    constraints = {"type": "eq", "fun": lambda w: np.sum(w) - 1}
    bounds = [(0, 1)] * n_donors

    result = minimize(objective, w0, method="SLSQP", bounds=bounds, constraints=constraints)

    if verbose:
        print("--- General optimizer (scipy SLSQP) ---")
        print(f"weight_denver = {result.x[0]:.4f}, weight_phoenix = {result.x[1]:.4f}, "
              f"SSE = {result.fun:.6f}")

    return result.x


def build_synthetic_series(df, weight_denver, verbose=True):
    """Step 4 -- apply the winning weight across ALL weeks, pre and post,
    to build the full synthetic Austin counterfactual."""
    weight_phoenix = 1 - weight_denver
    synthetic = weight_denver * df.denver_rides_k + weight_phoenix * df.phoenix_rides_k
    out = df.copy()
    out["synthetic_austin_rides_k"] = synthetic.round(3)

    if verbose:
        print(f"--- Synthetic Austin, all 12 weeks (weight_denver={weight_denver:.2f}) ---")
        print(out[["week", "post_treatment", "austin_rides_k", "synthetic_austin_rides_k"]]
              .to_string(index=False))

    return out


def compute_treatment_effect(df_with_synthetic, verbose=True):
    """Step 5 -- actual minus synthetic, post-treatment weeks only."""
    post = df_with_synthetic[df_with_synthetic.post_treatment].copy()
    post["effect"] = (post.austin_rides_k - post.synthetic_austin_rides_k).round(3)
    avg_effect = post.effect.mean()
    total_effect = post.effect.sum()

    if verbose:
        print("--- Treatment effect, post-pilot weeks ---")
        print(post[["week", "austin_rides_k", "synthetic_austin_rides_k", "effect"]].to_string(index=False))
        print(f"\nAverage weekly effect: {avg_effect:.2f}k rides")
        print(f"Total effect across the pilot: {total_effect:.2f}k rides")

    return {"post": post, "avg_effect": avg_effect, "total_effect": total_effect}


def plot_weight_search(grid, best_weight, save_path="output/weight_search.png"):
    """Fig 1 -- the U-shaped curve showing why weight_denver=0.6 wins."""
    fig, ax = plt.subplots(figsize=(8.4, 5.2), dpi=200)
    fig.patch.set_facecolor("white")

    ax.plot(grid.weight_denver, grid.sse, color=CTRL, linewidth=2.2, zorder=2)
    ax.scatter(grid.weight_denver, grid.sse, color=CTRL, s=28, zorder=3)

    best_sse = grid.loc[grid.weight_denver == best_weight, "sse"].values[0]
    ax.scatter([best_weight], [best_sse], color=SURP, s=170, zorder=5,
               edgecolor="white", linewidth=1.5)
    ax.annotate(f"Best fit\nweight_denver = {best_weight:.2f}",
                xy=(best_weight, best_sse), xytext=(best_weight - 0.02, best_sse + max(grid.sse) * 0.12),
                fontsize=10.5, color=SURP, fontweight="bold", ha="center")

    ax.set_xlabel("Candidate weight on Denver (weight on Phoenix = 1 minus this)", fontsize=11, color=MUTED)
    ax.set_ylabel("Pre-period fit error (sum of squared errors)", fontsize=11, color=MUTED)
    ax.set_title("Trying every blend of Denver and Phoenix,\nand keeping the one that fits Austin's past best",
                 fontsize=13, color=INK, fontweight="bold", pad=14)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color(RULE)
    ax.spines["bottom"].set_color(RULE)
    ax.tick_params(colors=MUTED, labelsize=10)
    ax.yaxis.grid(True, color=RULE, linewidth=0.8, zorder=0)
    ax.set_axisbelow(True)

    plt.tight_layout()
    plt.savefig(save_path, facecolor="white", bbox_inches="tight")
    plt.close(fig)
    print(f"Saved {save_path}")


def plot_actual_vs_synthetic(df_with_synthetic, save_path="output/actual_vs_synthetic.png"):
    """Fig 2 -- the classic synthetic control chart: actual vs. synthetic
    Austin, pre-period overlapping almost perfectly, post-period gap
    is the estimated treatment effect."""
    fig, ax = plt.subplots(figsize=(9.0, 5.6), dpi=200)
    fig.patch.set_facecolor("white")

    df = df_with_synthetic
    ax.plot(df.week, df.austin_rides_k, color=TREAT, linewidth=2.4, marker="o",
           markersize=5, label="Actual Austin", zorder=4)
    ax.plot(df.week, df.synthetic_austin_rides_k, color=CTRL, linewidth=2.2,
           linestyle=(0, (5, 3)), marker="o", markersize=5, label="Synthetic Austin", zorder=3)

    post = df[df.post_treatment]
    ax.fill_between(post.week, post.synthetic_austin_rides_k, post.austin_rides_k,
                    color=SURP, alpha=0.18, zorder=2, label="Estimated pilot effect")

    ax.axvline(TREATMENT_START_WEEK - 0.5, color=INK, linewidth=1.4, linestyle=(0, (1, 2)), zorder=1)
    ax.annotate("Bonus\npilot starts", xy=(TREATMENT_START_WEEK - 0.5, 34.5),
               ha="center", fontsize=9.5, color=MUTED)

    ax.set_xlabel("Week", fontsize=11, color=MUTED)
    ax.set_ylabel("Weekly rides (thousands)", fontsize=11, color=MUTED)
    ax.set_title("Actual Austin pulls away from Synthetic Austin\nthe moment the bonus pilot starts",
                fontsize=13.5, color=INK, fontweight="bold", pad=14)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color(RULE)
    ax.spines["bottom"].set_color(RULE)
    ax.tick_params(colors=MUTED, labelsize=10)
    ax.legend(frameon=False, fontsize=10, loc="upper left")
    ax.yaxis.grid(True, color=RULE, linewidth=0.8, zorder=0)
    ax.set_axisbelow(True)
    ax.set_xticks(df.week)

    plt.tight_layout()
    plt.savefig(save_path, facecolor="white", bbox_inches="tight")
    plt.close(fig)
    print(f"Saved {save_path}")


if __name__ == "__main__":
    df = load_data()

    print("=" * 70)
    pre_period_fit(0.5, df, verbose=True)

    print()
    print("=" * 70)
    grid, best_weight = grid_search_weights(df)

    print()
    print("=" * 70)
    solve_weights_general(df)

    print()
    print("=" * 70)
    df_synth = build_synthetic_series(df, best_weight)

    print()
    print("=" * 70)
    compute_treatment_effect(df_synth)

    print()
    print("=" * 70)
    plot_weight_search(grid, best_weight)
    plot_actual_vs_synthetic(df_synth)
