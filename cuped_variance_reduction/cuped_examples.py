"""Worked examples for the CUPED (Controlled-experiment Using Pre-Experiment
Data) article -- a step-by-step how-to for variance reduction.

Each function mirrors one step of the article's calculation walkthrough.
Run this file directly to reproduce every number and figure quoted in
the article.
"""

import numpy as np
import pandas as pd
from scipy import stats
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


def load_data(path="data/cuped_streaming_sessions.csv"):
    return pd.read_csv(path)


def covariate_grand_mean(df, verbose=True):
    """Step 1 -- grand mean of the covariate X, across BOTH arms."""
    x_mean = df["x_pre_sessions"].mean()
    if verbose:
        print("--- Step 1: Grand mean of covariate X ---")
        print(f"E[X] = {x_mean:.3f}  (n={len(df)} users, both arms combined)")
    return x_mean


def covariance_and_variance(df, x_mean, verbose=True):
    """Step 2 -- Cov(Y, X) and Var(X), both computed across all users."""
    y_mean = df["y_post_sessions"].mean()
    x_dev = df["x_pre_sessions"] - x_mean
    y_dev = df["y_post_sessions"] - y_mean

    cov_xy = (x_dev * y_dev).sum() / len(df)
    var_x = (x_dev ** 2).sum() / len(df)
    var_y = (y_dev ** 2).sum() / len(df)

    if verbose:
        print("--- Step 2: Covariance(Y, X) and Variance(X) ---")
        print(f"E[Y] = {y_mean:.3f}")
        print(f"Cov(Y,X) = {cov_xy:.3f}")
        print(f"Var(X)   = {var_x:.3f}")
        print(f"Var(Y)   = {var_y:.3f}")

    return {"y_mean": y_mean, "cov_xy": cov_xy, "var_x": var_x, "var_y": var_y}


def compute_theta(cov_xy, var_x, verbose=True):
    """Step 3 -- theta = Cov(Y,X) / Var(X), the CUPED adjustment coefficient."""
    theta = cov_xy / var_x
    if verbose:
        print("--- Step 3: Theta (CUPED coefficient) ---")
        print(f"theta = Cov(Y,X) / Var(X) = {cov_xy:.3f} / {var_x:.3f} = {theta:.4f}")
    return theta


def pearson_r_and_variance_reduction(cov_xy, var_x, var_y, verbose=True):
    """Step 4 -- Pearson r and the variance reduction CUPED will achieve (r^2)."""
    sd_x, sd_y = np.sqrt(var_x), np.sqrt(var_y)
    r = cov_xy / (sd_x * sd_y)
    variance_reduction = r ** 2

    if verbose:
        print("--- Step 4: Pearson r and variance reduction ---")
        print(f"SD(X) = {sd_x:.3f}   SD(Y) = {sd_y:.3f}")
        print(f"r = Cov(Y,X) / (SD(X)*SD(Y)) = {r:.3f}")
        print(f"Variance reduction = r^2 = {variance_reduction:.1%}")

    return {"r": r, "variance_reduction": variance_reduction}


def adjust_outcome(df, theta, x_mean, verbose=True):
    """Step 5 -- Y_tilde_i = Y_i - theta * (X_i - E[X]) for every user."""
    df = df.copy()
    df["adjustment"] = theta * (df["x_pre_sessions"] - x_mean)
    df["y_adjusted"] = df["y_post_sessions"] - df["adjustment"]

    if verbose:
        print("--- Step 5: Adjusted outcome Y-tilde ---")
        print(df[["user", "arm", "y_post_sessions", "adjustment", "y_adjusted"]]
              .to_string(index=False, float_format=lambda v: f"{v:.3f}"))

    return df


def two_sample_ttest(control_vals, treatment_vals):
    t_stat, p_value = stats.ttest_ind(treatment_vals, control_vals, equal_var=True)
    return {
        "control_mean": control_vals.mean(),
        "treatment_mean": treatment_vals.mean(),
        "effect": treatment_vals.mean() - control_vals.mean(),
        "control_var": control_vals.var(ddof=1),
        "treatment_var": treatment_vals.var(ddof=1),
        "t_stat": t_stat,
        "p_value": p_value,
    }


def compare_raw_vs_adjusted(df, verbose=True):
    """Step 6 -- two-sample t-test on raw Y vs. CUPED-adjusted Y-tilde."""
    ctrl = df[df.arm == "Control"]
    trt = df[df.arm == "Treatment"]

    raw = two_sample_ttest(ctrl["y_post_sessions"], trt["y_post_sessions"])
    adjusted = two_sample_ttest(ctrl["y_adjusted"], trt["y_adjusted"])

    if verbose:
        print("--- Step 6: Raw vs. CUPED-adjusted t-test ---")
        print(f"{'Metric':<20}{'Raw Y':>12}{'Adjusted Y':>14}")
        print(f"{'Control mean':<20}{raw['control_mean']:>12.3f}{adjusted['control_mean']:>14.3f}")
        print(f"{'Treatment mean':<20}{raw['treatment_mean']:>12.3f}{adjusted['treatment_mean']:>14.3f}")
        print(f"{'Effect':<20}{raw['effect']:>12.3f}{adjusted['effect']:>14.3f}")
        print(f"{'Control var':<20}{raw['control_var']:>12.3f}{adjusted['control_var']:>14.3f}")
        print(f"{'Treatment var':<20}{raw['treatment_var']:>12.3f}{adjusted['treatment_var']:>14.3f}")
        print(f"{'t-stat':<20}{raw['t_stat']:>12.3f}{adjusted['t_stat']:>14.3f}")
        print(f"{'p-value':<20}{raw['p_value']:>12.4f}{adjusted['p_value']:>14.6f}")

    return {"raw": raw, "adjusted": adjusted}


def run_cuped(df, verbose=True):
    """Runs every step end to end and returns the full result set."""
    x_mean = covariate_grand_mean(df, verbose=verbose)
    if verbose:
        print()
    cov_var = covariance_and_variance(df, x_mean, verbose=verbose)
    if verbose:
        print()
    theta = compute_theta(cov_var["cov_xy"], cov_var["var_x"], verbose=verbose)
    if verbose:
        print()
    r_result = pearson_r_and_variance_reduction(
        cov_var["cov_xy"], cov_var["var_x"], cov_var["var_y"], verbose=verbose)
    if verbose:
        print()
    df_adjusted = adjust_outcome(df, theta, x_mean, verbose=verbose)
    if verbose:
        print()
    comparison = compare_raw_vs_adjusted(df_adjusted, verbose=verbose)

    return {
        "x_mean": x_mean, "theta": theta, "r": r_result["r"],
        "variance_reduction": r_result["variance_reduction"],
        "df_adjusted": df_adjusted, "comparison": comparison,
    }


def plot_covariate_scatter(df, r, save_path="output/covariate_scatter.png"):
    """Scatter of Y vs. X by arm, with the pooled regression line -- the
    visual reason CUPED works: a strong X-Y relationship means X predicts
    away a lot of Y's variance."""
    fig, ax = plt.subplots(figsize=(8.4, 5.4), dpi=200)
    fig.patch.set_facecolor("white")

    for arm, color in [("Control", CTRL), ("Treatment", TREAT)]:
        sub = df[df.arm == arm]
        ax.scatter(sub.x_pre_sessions, sub.y_post_sessions, color=color,
                   s=70, label=arm, zorder=3, edgecolor="white", linewidth=0.8)

    slope, intercept = np.polyfit(df.x_pre_sessions, df.y_post_sessions, 1)
    x_line = np.array([df.x_pre_sessions.min() - 0.5, df.x_pre_sessions.max() + 0.5])
    ax.plot(x_line, slope * x_line + intercept, color=INK, linewidth=1.8,
            linestyle=(0, (5, 3)), zorder=2, label="Pooled regression")

    ax.set_xlabel("X — pre-experiment sessions", fontsize=11, color=MUTED)
    ax.set_ylabel("Y — post-experiment sessions", fontsize=11, color=MUTED)
    ax.set_title(f"Pre-experiment sessions predict post-experiment sessions (r = {r:.2f})",
                fontsize=13, color=INK, fontweight="bold", pad=12)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color(RULE)
    ax.spines["bottom"].set_color(RULE)
    ax.tick_params(colors=MUTED, labelsize=10)
    ax.legend(frameon=False, fontsize=10, loc="upper left")
    ax.yaxis.grid(True, color=RULE, linewidth=0.8, zorder=0)
    ax.set_axisbelow(True)

    plt.tight_layout()
    plt.savefig(save_path, facecolor="white", bbox_inches="tight")
    plt.close(fig)
    print(f"Saved {save_path}")


def plot_raw_vs_adjusted(df, save_path="output/raw_vs_adjusted.png"):
    """Side-by-side strip plot of raw Y and adjusted Y-tilde by arm --
    the visual payoff: CUPED collapses within-arm spread and makes the
    two arms visibly separate."""
    fig, axes = plt.subplots(1, 2, figsize=(10.2, 5.0), dpi=200, sharey=False)
    fig.patch.set_facecolor("white")

    rng = np.random.default_rng(7)

    for ax, col, title in [
        (axes[0], "y_post_sessions", "Raw Y\n(before CUPED)"),
        (axes[1], "y_adjusted", "Adjusted Y-tilde\n(after CUPED)"),
    ]:
        for i, (arm, color) in enumerate([("Control", CTRL), ("Treatment", TREAT)]):
            vals = df[df.arm == arm][col]
            jitter = rng.uniform(-0.08, 0.08, size=len(vals))
            ax.scatter(np.full(len(vals), i) + jitter, vals, color=color,
                      s=60, zorder=3, edgecolor="white", linewidth=0.8)
            ax.plot([i - 0.15, i + 0.15], [vals.mean()] * 2, color=INK, linewidth=2.2, zorder=4)

        ax.set_xticks([0, 1])
        ax.set_xticklabels(["Control", "Treatment"], fontsize=10.5, color=MUTED)
        ax.set_title(title, fontsize=12.5, color=INK, fontweight="bold", pad=10)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.spines["left"].set_color(RULE)
        ax.spines["bottom"].set_color(RULE)
        ax.tick_params(colors=MUTED, labelsize=10)
        ax.yaxis.grid(True, color=RULE, linewidth=0.8, zorder=0)
        ax.set_axisbelow(True)
        ax.set_ylim(0, 14)

    axes[0].set_ylabel("Sessions", fontsize=11, color=MUTED)
    fig.suptitle("Same +2-session effect, same means — CUPED just removes the noise",
                fontsize=13, color=INK, fontweight="bold", y=1.02)

    plt.tight_layout()
    plt.savefig(save_path, facecolor="white", bbox_inches="tight")
    plt.close(fig)
    print(f"Saved {save_path}")


if __name__ == "__main__":
    df = load_data()
    print("=" * 70)
    result = run_cuped(df)

    print()
    print("=" * 70)
    plot_covariate_scatter(df, result["r"])
    plot_raw_vs_adjusted(result["df_adjusted"])
