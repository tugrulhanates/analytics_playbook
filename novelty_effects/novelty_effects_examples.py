"""Worked examples for the Novelty Effects article -- why a new game
feature's early A/B test results are almost always too good to be
true, and how comparing new players to existing players gives you an
accurate read without waiting weeks for the hype to fade.

Each function mirrors a section of the article. Run this file directly
to reproduce every number and figure quoted in the issue.
"""

import pandas as pd
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


def load_data(path="data/spin_wheel_daily.csv"):
    return pd.read_csv(path)


def compute_daily_lift(df, player_group, verbose=True):
    """Step 1 -- daily treatment effect for one player group, computed
    the same way every day: (treatment avg - control avg) / control avg."""
    sub = df[df.player_group == player_group]
    ctrl = sub[sub.arm == "control"].set_index("day")["avg_sessions"]
    trt = sub[sub.arm == "treatment"].set_index("day")["avg_sessions"]
    lift = ((trt - ctrl) / ctrl).rename("lift")

    if verbose:
        print(f"--- Daily lift, {player_group} players ---")
        for day in [1, 3, 7, 14, 21, 30]:
            if day in lift.index:
                print(f"day {day:>2}: {lift.loc[day]:.1%}")

    return lift.reset_index()


def compare_estimates(df, verbose=True):
    """Step 2 -- the three numbers that matter: the inflated early read,
    the accurate-but-slow late read, and the accurate-and-fast new-player
    read."""
    existing_lift = compute_daily_lift(df, "existing", verbose=False)
    new_sub = df[df.player_group == "new"]

    early = existing_lift[existing_lift.day <= 3]["lift"].mean()
    late = existing_lift[existing_lift.day >= 25]["lift"].mean()

    new_ctrl = new_sub[new_sub.arm == "control"]["avg_sessions"].mean()
    new_trt = new_sub[new_sub.arm == "treatment"]["avg_sessions"].mean()
    new_lift = (new_trt - new_ctrl) / new_ctrl

    result = pd.DataFrame([
        {"estimate": "Existing players, days 1-3 (early peek)", "lift": early, "wait_required_days": 3},
        {"estimate": "New players, any day (pooled)", "lift": new_lift, "wait_required_days": 1},
        {"estimate": "Existing players, days 25-30 (waited it out)", "lift": late, "wait_required_days": 30},
    ])

    if verbose:
        print("\n--- Step 2: Three ways to estimate the effect ---")
        for _, r in result.iterrows():
            print(f"{r['estimate']:<48} lift={r['lift']:>6.1%}  (needs ~{r['wait_required_days']} days of data)")

    return result


def plot_decay_curve(existing_lift, save_path="output/novelty_decay.png"):
    """Fig 1 -- the daily lift for existing players, decaying from the
    novelty-inflated early read down to the true steady-state effect."""
    fig, ax = plt.subplots(figsize=(9.0, 5.4), dpi=200)
    fig.patch.set_facecolor("white")

    x = existing_lift["day"]
    y = existing_lift["lift"] * 100

    ax.axvspan(1, 7, color=RULE, alpha=0.6, zorder=0, label="Danger zone: looks amazing, isn't real")
    ax.plot(x, y, color=TREAT, linewidth=2.4, marker="o", markersize=4, zorder=3)

    steady_state = existing_lift[existing_lift.day >= 25]["lift"].mean() * 100
    ax.axhline(steady_state, color=SURP, linewidth=1.8, linestyle=(0, (5, 3)), zorder=2,
               label=f"True steady-state effect (~{steady_state:.0f}%)")

    ax.annotate(f"Day 1: {y.iloc[0]:.0f}% lift\n(looks incredible)", xy=(1, y.iloc[0]),
                xytext=(9, y.iloc[0] - 4), fontsize=9.5, color=TREAT, fontweight="bold",
                arrowprops=dict(arrowstyle="-|>", color=TREAT, lw=1.4))
    ax.set_ylim(top=y.iloc[0] + 6)

    ax.set_xlabel("Day since the feature launched", fontsize=11, color=MUTED)
    ax.set_ylabel("Daily lift in sessions/player\n(treatment vs. control)", fontsize=10.5, color=MUTED)
    ax.set_title("The excitement fades. The real effect is\nless than a fifth the size of the day-1 number.",
                fontsize=13, color=INK, fontweight="bold", pad=14)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color(RULE)
    ax.spines["bottom"].set_color(RULE)
    ax.tick_params(colors=MUTED, labelsize=10)
    ax.legend(frameon=False, fontsize=9.5, loc="upper right")
    ax.yaxis.set_major_formatter(lambda v, pos: f"{v:.0f}%")
    ax.yaxis.grid(True, color=RULE, linewidth=0.8, zorder=0)
    ax.set_axisbelow(True)

    plt.tight_layout()
    plt.savefig(save_path, facecolor="white", bbox_inches="tight")
    plt.close(fig)
    print(f"Saved {save_path}")


def plot_estimate_comparison(result, save_path="output/estimate_comparison.png"):
    """Fig 2 -- three ways to estimate the effect, and how long each takes."""
    fig, ax = plt.subplots(figsize=(9.0, 5.2), dpi=200)
    fig.patch.set_facecolor("white")

    labels = ["Existing players\ndays 1-3\n(3 days)", "New players\nany day\n(1 day)",
              "Existing players\ndays 25-30\n(30 days)"]
    values = [v * 100 for v in result["lift"]]
    colors = [DEF, SURP, SURP]

    bars = ax.bar(labels, values, color=colors, width=0.55, zorder=3)
    for bar, v in zip(bars, values):
        ax.annotate(f"{v:.0f}%", xy=(bar.get_x() + bar.get_width() / 2, bar.get_height()),
                    xytext=(0, 6), textcoords="offset points", ha="center",
                    fontsize=13, fontweight="bold", color=INK)

    ax.set_ylabel("Estimated lift", fontsize=11, color=MUTED)
    ax.set_title("New players give you the accurate number\non day one -- no need to wait a month",
                fontsize=13, color=INK, fontweight="bold", pad=14)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color(RULE)
    ax.spines["bottom"].set_color(RULE)
    ax.tick_params(colors=MUTED, labelsize=10)
    ax.yaxis.set_major_formatter(lambda v, pos: f"{v:.0f}%")
    ax.yaxis.grid(True, color=RULE, linewidth=0.8, zorder=0)
    ax.set_axisbelow(True)
    ax.set_ylim(0, max(values) * 1.25)

    plt.tight_layout()
    plt.savefig(save_path, facecolor="white", bbox_inches="tight")
    plt.close(fig)
    print(f"Saved {save_path}")


if __name__ == "__main__":
    df = load_data()

    print("=" * 70)
    existing_lift = compute_daily_lift(df, "existing")

    print()
    print("=" * 70)
    new_lift_preview = compute_daily_lift(df, "new")

    print()
    print("=" * 70)
    result = compare_estimates(df)
    result.to_csv("data/estimate_comparison.csv", index=False)
    print("\nSaved data/estimate_comparison.csv")

    print()
    print("=" * 70)
    plot_decay_curve(existing_lift)
    plot_estimate_comparison(result)
