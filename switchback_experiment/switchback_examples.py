"""Worked examples for the Switchback Experiment article.

Each function mirrors a section of the article: the naive (biased) analysis,
the washout fix, the correct clustered-SE analysis, the zone-level
heterogeneity check, and the carry-over diagnostic. Run this file directly
to reproduce every number quoted in the article.
"""

import numpy as np
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

WASHOUT_MINUTES = 15


def load_data(path="data/switchback_intervals.csv"):
    return pd.read_csv(path)


def naive_pooled_lift(df, verbose=True):
    """Pools every 5-minute interval -- including carry-over-contaminated
    ones -- and treats each as an independent observation. This is the
    analysis most teams run first, and it's wrong twice over: it's biased
    by carry-over, and its standard error ignores that intervals within
    a block are not independent."""
    ctrl = df.loc[df.assignment == "Control", "wait_time_min"]
    trt = df.loc[df.assignment == "Treatment", "wait_time_min"]
    ctrl_mean, trt_mean = ctrl.mean(), trt.mean()
    lift = (trt_mean - ctrl_mean) / ctrl_mean
    naive_se = np.sqrt(ctrl.var() / len(ctrl) + trt.var() / len(trt))
    naive_t = (trt_mean - ctrl_mean) / naive_se

    if verbose:
        print("--- Naive pooled analysis (no washout, interval-level SE) ---")
        print(f"Control mean wait: {ctrl_mean:.3f} min  (n={len(ctrl):,} intervals)")
        print(f"Treatment mean wait: {trt_mean:.3f} min  (n={len(trt):,} intervals)")
        print(f"Naive lift: {lift:+.1%}")
        print(f"Naive t-stat (interval-level, ignores clustering): {naive_t:.1f}")

    return {"ctrl_mean": ctrl_mean, "trt_mean": trt_mean, "lift": lift, "naive_t": naive_t}


def apply_washout(df, washout_minutes=WASHOUT_MINUTES, verbose=True):
    """Drops the first `washout_minutes` of every block to remove
    carry-over contamination from the previous block's condition."""
    cleaned = df.loc[df.minutes_into_block >= washout_minutes].copy()

    if verbose:
        dropped = len(df) - len(cleaned)
        print("--- Applying washout ---")
        print(f"Dropped {dropped:,} of {len(df):,} intervals "
              f"({dropped / len(df):.1%}) as carry-over-contaminated.")

    return cleaned


def block_level_lift(df_washed, verbose=True):
    """Aggregates to one row per (zone, block_id) -- the true unit of
    randomisation -- then computes the treatment effect with a standard
    error built from block-level variance, not interval-level variance.
    This is the number that should actually be reported."""
    block_avg = (
        df_washed.groupby(["zone", "block_id", "assignment"])["wait_time_min"]
        .mean()
        .reset_index()
    )
    ctrl = block_avg.loc[block_avg.assignment == "Control", "wait_time_min"]
    trt = block_avg.loc[block_avg.assignment == "Treatment", "wait_time_min"]
    ctrl_mean, trt_mean = ctrl.mean(), trt.mean()
    lift = (trt_mean - ctrl_mean) / ctrl_mean
    block_se = np.sqrt(ctrl.var() / len(ctrl) + trt.var() / len(trt))
    block_t = (trt_mean - ctrl_mean) / block_se

    if verbose:
        print("--- Corrected analysis: washed out + block-level clustering ---")
        print(f"Control blocks: {len(ctrl):,}   Treatment blocks: {len(trt):,}")
        print(f"Control mean wait: {ctrl_mean:.3f} min")
        print(f"Treatment mean wait: {trt_mean:.3f} min")
        print(f"Corrected lift: {lift:+.1%}")
        print(f"Block-level t-stat: {block_t:.1f}")

    return {"ctrl_mean": ctrl_mean, "trt_mean": trt_mean, "lift": lift,
            "block_t": block_t, "block_avg": block_avg}


def zone_level_heterogeneity(df_washed, verbose=True):
    """Reproduces the per-zone lift table -- pooling hides how much the
    effect varies market to market."""
    block_avg = (
        df_washed.groupby(["zone", "block_id", "assignment"])["wait_time_min"]
        .mean()
        .reset_index()
    )
    rows = []
    for zone in block_avg.zone.unique():
        sub = block_avg[block_avg.zone == zone]
        ctrl = sub.loc[sub.assignment == "Control", "wait_time_min"]
        trt = sub.loc[sub.assignment == "Treatment", "wait_time_min"]
        lift = (trt.mean() - ctrl.mean()) / ctrl.mean()
        rows.append({
            "zone": zone,
            "control_blocks": len(ctrl),
            "treatment_blocks": len(trt),
            "avg_wait_control": round(ctrl.mean(), 2),
            "avg_wait_treatment": round(trt.mean(), 2),
            "lift": lift,
        })
    result = pd.DataFrame(rows).sort_values("lift")

    if verbose:
        print("--- Zone-level heterogeneity ---")
        for _, r in result.iterrows():
            print(f"{r.zone:>8}: {r.control_blocks} ctrl / {r.treatment_blocks} trt blocks, "
                  f"{r.avg_wait_control:.2f} -> {r.avg_wait_treatment:.2f} min "
                  f"({r.lift:+.1%})")

    return result


def carryover_diagnostic(df, verbose=True):
    """For every block transition, compares the first 10 minutes of the
    new block to the last 10 minutes of the block before it -- the same
    diagnostic used to decide whether (and how long) a washout is needed."""
    df = df.sort_values(["zone", "block_id", "minutes_into_block"]).reset_index(drop=True)
    results = {"Control -> Treatment": [], "Treatment -> Control": []}

    for zone in df.zone.unique():
        zdf = df[df.zone == zone]
        block_ids = sorted(zdf.block_id.unique())
        for i in range(1, len(block_ids)):
            prev_block = zdf[zdf.block_id == block_ids[i - 1]]
            curr_block = zdf[zdf.block_id == block_ids[i]]
            prev_assignment = prev_block.assignment.iloc[0]
            curr_assignment = curr_block.assignment.iloc[0]
            if prev_assignment == curr_assignment:
                continue

            prev_last10 = prev_block[prev_block.minutes_into_block >= 50].wait_time_min.mean()
            curr_first10 = curr_block[curr_block.minutes_into_block < 10].wait_time_min.mean()
            key = f"{prev_assignment} -> {curr_assignment}"
            results[key].append({"prev_last10": prev_last10, "curr_first10": curr_first10})

    summary = []
    for transition, records in results.items():
        rec_df = pd.DataFrame(records)
        prev_avg = rec_df.prev_last10.mean()
        curr_avg = rec_df.curr_first10.mean()
        gap = curr_avg - prev_avg
        summary.append({
            "transition": transition,
            "n_transitions": len(rec_df),
            "prev_block_last_10min": round(prev_avg, 2),
            "new_block_first_10min": round(curr_avg, 2),
            "gap": round(gap, 2),
        })

    result = pd.DataFrame(summary)

    if verbose:
        print("--- Carry-over diagnostic ---")
        for _, r in result.iterrows():
            print(f"{r.transition}: prev block last 10min = {r.prev_block_last_10min:.2f} min, "
                  f"new block first 10min = {r.new_block_first_10min:.2f} min, "
                  f"gap = {r.gap:+.2f} min  (n={r.n_transitions} transitions)")

    return result


def plot_carryover_curve(df, save_path="output/carryover_curve.png"):
    """Average wait time by minute-into-block, split by transition type --
    the visual version of the carry-over diagnostic table."""
    df = df.sort_values(["zone", "block_id", "minutes_into_block"]).reset_index(drop=True)
    curves = {"Control -> Treatment": [], "Treatment -> Control": []}

    for zone in df.zone.unique():
        zdf = df[df.zone == zone]
        block_ids = sorted(zdf.block_id.unique())
        for i in range(1, len(block_ids)):
            prev_block = zdf[zdf.block_id == block_ids[i - 1]]
            curr_block = zdf[zdf.block_id == block_ids[i]]
            prev_assignment = prev_block.assignment.iloc[0]
            curr_assignment = curr_block.assignment.iloc[0]
            if prev_assignment == curr_assignment:
                continue
            key = f"{prev_assignment} -> {curr_assignment}"
            curve = curr_block.sort_values("minutes_into_block").wait_time_min.values
            curves[key].append(curve)

    fig, ax = plt.subplots(figsize=(9.0, 5.2), dpi=200)
    fig.patch.set_facecolor("white")
    x = list(range(0, 60, 5))

    for key, color in [("Control -> Treatment", TREAT), ("Treatment -> Control", SURP)]:
        avg_curve = np.mean(curves[key], axis=0)
        ax.plot(x, avg_curve, color=color, linewidth=2.6, marker="o", markersize=5, label=key)

    ax.axvspan(0, WASHOUT_MINUTES, color=RULE, alpha=0.6, zorder=0, label="Washout window")
    ax.set_xlabel("Minutes into new block", fontsize=11, color=MUTED)
    ax.set_ylabel("Avg wait time (min)", fontsize=11, color=MUTED)
    ax.set_title("Carry-over decays within the first 15 minutes of a new block",
                 fontsize=13, color=INK, fontweight="bold", pad=12)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color(RULE)
    ax.spines["bottom"].set_color(RULE)
    ax.tick_params(colors=MUTED, labelsize=10)
    ax.legend(frameon=False, fontsize=10, loc="center right")
    ax.yaxis.grid(True, color=RULE, linewidth=0.8, zorder=0)
    ax.set_axisbelow(True)

    plt.tight_layout()
    plt.savefig(save_path, facecolor="white", bbox_inches="tight")
    plt.close(fig)
    print(f"Saved {save_path}")


def plot_zone_heterogeneity(zone_result, save_path="output/zone_heterogeneity.png"):
    """Bar chart of lift % by zone -- the visual version of the
    zone-level heterogeneity table."""
    fig, ax = plt.subplots(figsize=(9.0, 5.2), dpi=200)
    fig.patch.set_facecolor("white")

    zones = zone_result.sort_values("lift").zone.tolist()
    lifts = zone_result.sort_values("lift").lift.tolist()
    colors = [SURP if l <= -0.08 else (CTRL if l <= -0.05 else TREAT) for l in lifts]

    bars = ax.barh(zones, [l * 100 for l in lifts], color=colors, zorder=3)
    ax.set_xlim(min(l * 100 for l in lifts) - 2.5, 0.6)
    for bar, lift in zip(bars, lifts):
        ax.annotate(f"{lift:+.1%}", xy=(bar.get_width() + 0.35, bar.get_y() + bar.get_height() / 2),
                    va="center", ha="left", fontsize=10.5, fontweight="bold", color="white")

    ax.set_xlabel("Wait-time lift vs. control (%)", fontsize=11, color=MUTED)
    ax.set_title("The pooled -8% hides a -3% to -13% spread across zones",
                 fontsize=13, color=INK, fontweight="bold", pad=12)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color(RULE)
    ax.spines["bottom"].set_color(RULE)
    ax.tick_params(colors=MUTED, labelsize=10.5)
    ax.xaxis.grid(True, color=RULE, linewidth=0.8, zorder=0)
    ax.set_axisbelow(True)

    plt.tight_layout()
    plt.savefig(save_path, facecolor="white", bbox_inches="tight")
    plt.close(fig)
    print(f"Saved {save_path}")


if __name__ == "__main__":
    df = load_data()

    print("=" * 70)
    naive = naive_pooled_lift(df)

    print()
    print("=" * 70)
    df_washed = apply_washout(df)

    print()
    print("=" * 70)
    corrected = block_level_lift(df_washed)

    print()
    print("=" * 70)
    zone_result = zone_level_heterogeneity(df_washed)

    print()
    print("=" * 70)
    carryover = carryover_diagnostic(df)

    print()
    print("=" * 70)
    plot_carryover_curve(df)
    plot_zone_heterogeneity(zone_result)
