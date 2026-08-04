"""
The Hidden Asymmetry in CAC -- Worked Examples
=================================================
Companion script for the Analytics Playbook newsletter issue on why supply-side
(host) CAC is quietly much higher than it looks on a standard dashboard.

Reads two dummy datasets from /data and walks through every calculation
discussed in the article, each as its own clearly named function:

    1. nominal_cac()              -> the CAC everyone already reports
    2. host_ramp_curve()          -> % of steady-state productivity by month
    3. ramp_shortfall_per_host()  -> the £ value hidden by that ramp curve
    4. effective_cac()            -> nominal CAC + ramp shortfall, compared
    5. churn_replacement_cost()   -> what replacing a churned host really costs
    6. faster_ramp_scenario()     -> "what if onboarding cut ramp time in half"

Run the whole file to execute the full analysis in order:

    python cac_asymmetry_examples.py

Each function can also be imported and run on its own, e.g.:

    from cac_asymmetry_examples import effective_cac, load_data
    spend_df, ramp_df = load_data()
    result = effective_cac(spend_df, ramp_df)
"""

import os
import pandas as pd
import matplotlib.pyplot as plt

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

INK, MUTED, RULE = "#14181F", "#6B7480", "#DDE2E8"
CTRL, TREAT, SURP = "#64748B", "#B4530A", "#0E7C6B"

RAMP_MONTHS = 4          # months counted as "ramping up" for a new host
STEADY_STATE_MONTHS = (4, 5, 6)  # months used to estimate steady-state revenue


def load_data():
    spend_df = pd.read_csv(os.path.join(DATA_DIR, "marketing_spend_acquisitions.csv"))
    ramp_df = pd.read_csv(os.path.join(DATA_DIR, "host_ramp_productivity.csv"))
    return spend_df, ramp_df


# ===========================================================================
# 1. NOMINAL CAC (the number everyone already tracks)
# ===========================================================================
# Total spend divided by total acquisitions, by side. This is what shows up
# on most marketplace dashboards -- and it's the number that makes host
# acquisition look "only" ~5x more expensive than guest acquisition.
# ===========================================================================
def nominal_cac(spend_df, verbose=True):
    totals = spend_df.groupby("side")[["spend", "acquisitions"]].sum()
    totals["nominal_cac"] = (totals["spend"] / totals["acquisitions"]).round(2)

    if verbose:
        print("\n=== 1. Nominal CAC ===")
        print(totals)
    return totals["nominal_cac"].to_dict()


# ===========================================================================
# 2. HOST RAMP CURVE
# ===========================================================================
# Average host revenue by month-since-signup, expressed as a % of the
# empirically estimated steady state (the average of months 4-6, rather than
# an assumed target -- estimate it from the data you actually have).
# ===========================================================================
def host_ramp_curve(ramp_df, verbose=True):
    by_month = ramp_df.groupby("month_since_signup")["monthly_revenue"].mean()
    steady_state = by_month.loc[list(STEADY_STATE_MONTHS)].mean()
    pct_of_steady_state = (by_month / steady_state * 100).round(1)

    if verbose:
        print("\n=== 2. Host Ramp Curve ===")
        print(f"Estimated steady-state monthly revenue per host: £{steady_state:.2f}")
        for month, pct in pct_of_steady_state.items():
            print(f"  Month {month}: £{by_month[month]:.2f}  ({pct}% of steady state)")

    return {"by_month": by_month, "steady_state": steady_state, "pct_of_steady_state": pct_of_steady_state}


# ===========================================================================
# 3. RAMP SHORTFALL PER HOST
# ===========================================================================
# The £ value given up during the ramp period: for each of the first
# RAMP_MONTHS months, steady-state revenue minus what was actually earned,
# summed. This is the hidden cost a nominal-CAC dashboard never shows.
# ===========================================================================
def ramp_shortfall_per_host(ramp_df, verbose=True):
    curve = host_ramp_curve(ramp_df, verbose=False)
    by_month, steady_state = curve["by_month"], curve["steady_state"]

    shortfall = sum(max(steady_state - by_month[m], 0) for m in range(1, RAMP_MONTHS + 1))

    if verbose:
        print(f"\n=== 3. Ramp Shortfall per Host (first {RAMP_MONTHS} months) ===")
        print(f"Total revenue given up per host while ramping: £{shortfall:.2f}")
    return shortfall


# ===========================================================================
# 4. EFFECTIVE CAC
# ===========================================================================
# Nominal CAC + ramp shortfall, side by side. This is the number that
# actually belongs on the dashboard next to marketing spend -- and it's the
# number that changes the budget conversation.
# ===========================================================================
def effective_cac(spend_df, ramp_df, verbose=True):
    nominal = nominal_cac(spend_df, verbose=verbose)
    shortfall = ramp_shortfall_per_host(ramp_df, verbose=verbose)

    effective = {
        "guest": nominal["guest"],                 # guests: no ramp, no shortfall
        "host": round(nominal["host"] + shortfall, 2),
    }

    if verbose:
        print("\n=== 4. Effective CAC (nominal + hidden ramp cost) ===")
        print(f"Guest: nominal £{nominal['guest']:.2f}  ->  effective £{effective['guest']:.2f}  (no change)")
        print(f"Host:  nominal £{nominal['host']:.2f}  ->  effective £{effective['host']:.2f}"
              f"  (+£{shortfall:.2f} hidden ramp cost)")
        print(f"\nNominal gap (host / guest):   {nominal['host'] / nominal['guest']:.1f}x")
        print(f"Effective gap (host / guest): {effective['host'] / effective['guest']:.1f}x")

    return {"nominal": nominal, "effective": effective, "shortfall": shortfall}


# ===========================================================================
# 5. CHURN REPLACEMENT COST
# ===========================================================================
# What it actually costs to replace one churned, already-productive host:
# not just the acquisition spend for a new host, but the full ramp shortfall
# again, since the replacement starts from zero. Losing an experienced host
# and "replacing" them with a new signup is not a like-for-like swap.
# ===========================================================================
def churn_replacement_cost(spend_df, ramp_df):
    result = effective_cac(spend_df, ramp_df, verbose=False)
    replacement_cost = result["effective"]["host"]

    print("\n=== 5. Cost to Replace One Churned Host ===")
    print(f"Full effective CAC must be paid again: £{replacement_cost:.2f}")
    print("...before counting the booking gap while the listing sits vacant, "
          "or the lost trust signals (reviews, ranking) the departing host took with them.")
    return replacement_cost


# ===========================================================================
# 6. FASTER RAMP SCENARIO (a teaching aid, not part of the core analysis)
# ===========================================================================
# What happens to effective CAC if a hypothetical onboarding improvement cut
# the ramp period in half -- i.e., hosts reach steady state by month 2
# instead of month 4. Approximated by compressing the observed ramp curve.
# ===========================================================================
def faster_ramp_scenario(ramp_df, compression=0.5):
    curve = host_ramp_curve(ramp_df, verbose=False)
    by_month, steady_state = curve["by_month"], curve["steady_state"]

    compressed_shortfall = 0
    for m in range(1, RAMP_MONTHS + 1):
        source_month = min(m / compression, 6)
        revenue_at_source = by_month.get(round(source_month), steady_state)
        compressed_shortfall += max(steady_state - revenue_at_source, 0)

    original_shortfall = ramp_shortfall_per_host(ramp_df, verbose=False)

    print(f"\n=== 6. Faster Ramp Scenario (ramp period cut by {int((1 - compression) * 100)}%) ===")
    print(f"Original ramp shortfall per host: £{original_shortfall:.2f}")
    print(f"Shortfall under faster ramp:       £{compressed_shortfall:.2f}")
    print(f"Value unlocked per host:           £{original_shortfall - compressed_shortfall:.2f}")
    return compressed_shortfall


# ===========================================================================
# PLOTS
# ===========================================================================
def plot_ramp_curve(ramp_df, save_path=None):
    curve = host_ramp_curve(ramp_df, verbose=False)
    pct = curve["pct_of_steady_state"]

    fig, ax = plt.subplots(figsize=(7.4, 4.2), dpi=140)
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")
    for gv in range(0, 120, 20):
        ax.axhline(gv, color=RULE, linewidth=0.8, zorder=0)

    ax.plot(pct.index, pct.values, color=TREAT, linewidth=2.4, marker="o",
            markersize=6.5, markerfacecolor=TREAT, markeredgecolor="white", zorder=3, label="Host")
    ax.axhline(100, color=CTRL, linewidth=2.2, linestyle=(0, (5, 3)), zorder=2, label="Guest (instant)")
    ax.axvspan(1, RAMP_MONTHS, color=TREAT, alpha=0.06, zorder=0)
    ax.annotate("ramp period", xy=(2.5, 15), ha="center", fontsize=9, color=MUTED)

    ax.set_xlabel("months since signup", fontsize=9.5, color=MUTED)
    ax.set_ylabel("% of steady-state productivity", fontsize=9.5, color=MUTED)
    ax.set_title("The Host Ramp Curve", fontsize=13, color=INK, fontweight="bold", loc="left")
    ax.set_ylim(0, 115)
    for spine in ["top", "right", "left"]:
        ax.spines[spine].set_visible(False)
    ax.spines["bottom"].set_color(INK)
    ax.tick_params(axis="both", length=0, colors=MUTED)
    ax.legend(frameon=False, fontsize=9.5, labelcolor=MUTED, loc="lower right")
    fig.tight_layout()

    path = save_path or os.path.join(OUTPUT_DIR, "cac_ramp_curve.png")
    fig.savefig(path, facecolor="white")
    plt.close(fig)
    print(f"\nRamp curve plot saved to: {path}")


def plot_cac_comparison(spend_df, ramp_df, save_path=None):
    result = effective_cac(spend_df, ramp_df, verbose=False)
    nominal, shortfall = result["nominal"], result["shortfall"]

    sides = ["Guest", "Host"]
    nominal_vals = [nominal["guest"], nominal["host"]]
    shortfall_vals = [0, shortfall]

    fig, ax = plt.subplots(figsize=(6.4, 4.4), dpi=140)
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")
    for gv in range(0, 600, 100):
        ax.axhline(gv, color=RULE, linewidth=0.8, zorder=0)

    x = [0, 1]
    ax.bar(x, nominal_vals, width=0.5, color=CTRL, zorder=3, label="Nominal CAC")
    ax.bar(x, shortfall_vals, width=0.5, bottom=nominal_vals, color=TREAT, zorder=3,
           label="Hidden ramp cost")

    for i, (n, s) in enumerate(zip(nominal_vals, shortfall_vals)):
        ax.annotate(f"£{n:.0f}", xy=(i, n / 2), ha="center", va="center",
                    fontsize=10, color="white", fontweight="bold")
        if s > 0:
            ax.annotate(f"£{s:.0f}", xy=(i, n + s / 2), ha="center", va="center",
                        fontsize=10, color="white", fontweight="bold")
            ax.annotate(f"= £{n + s:.0f}", xy=(i, n + s + 15), ha="center",
                        fontsize=11, color=SURP, fontweight="bold")

    ax.set_xticks(x)
    ax.set_xticklabels(sides, fontsize=11, color=INK, fontweight="bold")
    ax.set_ylabel("effective CAC (£)", fontsize=9.5, color=MUTED)
    ax.set_title("Nominal vs. Effective CAC", fontsize=13, color=INK, fontweight="bold", loc="left")
    for spine in ["top", "right", "left"]:
        ax.spines[spine].set_visible(False)
    ax.spines["bottom"].set_color(INK)
    ax.tick_params(axis="both", length=0, colors=MUTED)
    ax.legend(frameon=False, fontsize=9.5, labelcolor=MUTED, loc="upper left")
    fig.tight_layout()

    path = save_path or os.path.join(OUTPUT_DIR, "cac_comparison.png")
    fig.savefig(path, facecolor="white")
    plt.close(fig)
    print(f"CAC comparison plot saved to: {path}")


# ===========================================================================
if __name__ == "__main__":
    spend_data, ramp_data = load_data()

    nominal_cac(spend_data)
    host_ramp_curve(ramp_data)
    ramp_shortfall_per_host(ramp_data)
    effective_cac(spend_data, ramp_data)
    churn_replacement_cost(spend_data, ramp_data)
    faster_ramp_scenario(ramp_data)

    plot_ramp_curve(ramp_data)
    plot_cac_comparison(spend_data, ramp_data)
