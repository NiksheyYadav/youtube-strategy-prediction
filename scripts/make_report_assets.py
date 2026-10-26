"""Generate the diagrams and charts used by the report, notes and presentation (real data where possible).

    python scripts/make_report_assets.py
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
OUT = ROOT / "deliverables" / "assets" / "diagrams"
OUT.mkdir(parents=True, exist_ok=True)

GREEN, DARK, GOLD, GRAY, LIGHT, BLUE, CORAL, WHITE = "#0E9F6E", "#1F2937", "#D4A72C", "#6B7280", "#F2F5FA", "#3B82F6", "#E4572E", "#FFFFFF"
plt.rcParams.update({"font.family": "DejaVu Sans", "axes.spines.top": False, "axes.spines.right": False, "figure.dpi": 100})


def save(fig, name):
    fig.savefig(OUT / f"{name}.png", dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print("saved", name)


def box(ax, x, y, w, h, text, color=GREEN, fg=WHITE, size=11, sub=None, bold=True):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.12", fc=color, ec="none"))
    if sub:
        ax.text(x + w / 2, y + h * 0.64, text, ha="center", va="center", color=fg, fontsize=size, fontweight="bold" if bold else "normal")
        ax.text(x + w / 2, y + h * 0.27, sub, ha="center", va="center", color=fg, fontsize=size - 3, alpha=0.92)
    else:
        ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", color=fg, fontsize=size, fontweight="bold" if bold else "normal", wrap=True)


def arrow(ax, x1, y1, x2, y2, color=GRAY, style="-|>", lw=2):
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle=style, mutation_scale=16, color=color, lw=lw))


def canvas(w, h, xlim, ylim):
    fig, ax = plt.subplots(figsize=(w, h))
    ax.set_xlim(*xlim)
    ax.set_ylim(*ylim)
    ax.axis("off")
    return fig, ax


# ------------------------------------------------------------------ simple diagrams
def pipeline():
    fig, ax = canvas(13, 3.2, (0, 13), (0, 3.2))
    steps = [("1 Raw data", "37,352 rows", GRAY), ("2 Clean", "16,307 videos", BLUE), ("3 Features", "30 signals", GREEN), ("4 Train", "2 forests", GREEN),
             ("5 Check", "5-fold + later", GOLD), ("6 Explain", "Shapley", GREEN), ("7 App", "Streamlit", BLUE), ("8 Online", "Render", DARK)]
    for i, (t, s, c) in enumerate(steps):
        x = 0.1 + i * 1.6
        box(ax, x, 1.0, 1.35, 1.2, t, c, size=10.5, sub=s)
        if i < len(steps) - 1:
            arrow(ax, x + 1.38, 1.6, x + 1.6, 1.6)
    ax.text(6.5, 0.35, "Every step is a real script in the project and is covered by automated tests", ha="center", color=GRAY, fontsize=11, style="italic")
    save(fig, "pipeline")


def funnel():
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.bar(["Raw rows\n(one per video per day)", "Unique videos\n(after cleaning)"], [37352, 16307], color=[GRAY, GREEN], width=0.55)
    for i, v in enumerate([37352, 16307]):
        ax.text(i, v + 700, f"{v:,}", ha="center", fontsize=14, fontweight="bold", color=DARK)
    ax.set_ylim(0, 43000)
    ax.set_ylabel("Count")
    ax.set_title("Same video appeared on many days, so we kept its latest row", fontsize=11, color=DARK)
    save(fig, "funnel")


def r2_progress():
    labels = ["Linear\n(baseline)", "First\nRandom Forest", "Final model\n(5-fold test)", "Final model\n(later uploads)"]
    views, eng = [0.197, 0.378, 0.419, 0.368], [0.384, 0.612, 0.637, 0.529]
    x = np.arange(4)
    fig, ax = plt.subplots(figsize=(9, 4.6))
    ax.bar(x - 0.19, views, 0.38, label="Views", color=GREEN)
    ax.bar(x + 0.19, eng, 0.38, label="Engagement", color=GOLD)
    for xi, v, e in zip(x, views, eng):
        ax.text(xi - 0.19, v + 0.012, f"{v:.2f}", ha="center", fontsize=10)
        ax.text(xi + 0.19, e + 0.012, f"{e:.2f}", ha="center", fontsize=10)
    ax.set_xticks(x, labels)
    ax.set_ylim(0, 0.75)
    ax.set_ylabel("R² score (higher = better)")
    ax.legend(frameon=False)
    ax.set_title("How well the models explain performance", color=DARK)
    save(fig, "r2_progress")


def ai_coach_flow():
    fig, ax = canvas(13, 5.2, (0, 13), (0, 5.2))
    row = [("Your draft", "title, tags,\ndescription, time", BLUE), ("ML model", "predicts views +\nengagement", GREEN), ("Evidence", "numbered facts\nE1, E2, E3...", GOLD), ("Rules", "decide what to\nimprove", GREEN),
           ("Local AI", "writes the\nwords only", BLUE), ("Checks", "numbers, promises,\nlinks, titles", CORAL), ("Your screen", "advice you\ncan trust", DARK)]
    for i, (t, s, c) in enumerate(row):
        x = 0.1 + i * 1.85
        box(ax, x, 2.9, 1.6, 1.5, t, c, size=11, sub=s)
        if i < len(row) - 1:
            arrow(ax, x + 1.63, 3.65, x + 1.85, 3.65)
    ax.text(6.5, 4.85, "AI Coach: the AI never touches the numbers", ha="center", fontsize=14, fontweight="bold", color=DARK)
    ax.add_patch(FancyBboxPatch((1.95, 0.2), 9.2, 1.9, boxstyle="round,pad=0.02,rounding_size=0.12", fc=LIGHT, ec="none"))
    ax.text(6.5, 1.85, "If something goes wrong we step down, so you always get an answer", ha="center", fontsize=11, color=DARK, fontweight="bold")
    for i, (t, s, c) in enumerate([("Main AI model", "qwen2.5 (3B or 7B)", GREEN), ("Lite AI model", "qwen2.5 (0.5B)", GOLD), ("Rule-based advice", "no AI needed", GRAY)]):
        x = 2.3 + i * 3.1
        box(ax, x, 0.45, 2.5, 0.95, t, c, size=10.5, sub=s)
        if i < 2:
            arrow(ax, x + 2.52, 0.92, x + 3.08, 0.92)
    save(fig, "ai_coach_flow")


def device_tiers():
    fig, ax = canvas(11, 4.6, (0, 11), (0, 4.6))
    rows = [("NVIDIA GPU, 8 GB\n(friend's RTX 5050)", "qwen2.5:7b", "~4.7 GB", GREEN), ("This laptop\nCPU only, 16 GB RAM", "qwen2.5:3b", "~1.9 GB", BLUE),
            ("CPU only\n8 GB RAM", "qwen2.5:1.5b", "~1.0 GB", GOLD), ("Under 6 GB RAM", "rule-based only", "no download", GRAY)]
    ax.text(0.2, 4.25, "Device", fontsize=11, fontweight="bold", color=DARK)
    ax.text(4.4, 4.25, "Main model the app picks", fontsize=11, fontweight="bold", color=DARK)
    ax.text(8.8, 4.25, "Download", fontsize=11, fontweight="bold", color=DARK)
    for i, (d, m, s, c) in enumerate(rows):
        y = 3.05 - i * 1.0
        box(ax, 0.1, y, 3.9, 0.82, d, LIGHT, fg=DARK, size=10.5, bold=False)
        arrow(ax, 4.05, y + 0.41, 4.35, y + 0.41)
        box(ax, 4.4, y, 3.6, 0.82, m, c, size=12)
        ax.text(8.8, y + 0.41, s, va="center", fontsize=11, color=DARK)
    ax.text(5.5, -0.15, "Every device also gets the tiny lite model (qwen2.5:0.5b, ~0.4 GB) as a safety net", ha="center", fontsize=10.5, color=GRAY, style="italic")
    save(fig, "device_tiers")


def architecture():
    fig, ax = canvas(13, 6.4, (0, 13), (0, 6.4))
    layers = [("DATA", "Kaggle India trending\n16,307 unique videos", GRAY, 0.2), ("ML MODELS", "2 Random Forests\nviews + engagement", GREEN, 2.75), ("INSIGHTS", "Shapley, best time, title lab,\nsimilar videos, keywords", BLUE, 5.3),
              ("AI COACH", "evidence -> local AI ->\nchecks -> fallback", GOLD, 7.85), ("APP", "Streamlit, 7 tabs\nrun.ps1 / run.sh", DARK, 10.4)]
    for t, s, c, x in layers:
        box(ax, x, 3.3, 2.35, 1.7, t, c, size=11.5, sub=s)
    for x in (2.57, 5.12, 7.67, 10.22):
        arrow(ax, x, 4.15, x + 0.18, 4.15)
    ax.text(6.5, 5.95, "Signal Studio: how the pieces fit together", ha="center", fontsize=15, fontweight="bold", color=DARK)
    side = [("131 automated tests", "golden numbers never change", GREEN, 0.7), ("GitHub Actions", "tests on every push", BLUE, 3.9), ("Render (online)", "rule-based mode + keep-warm", DARK, 7.1), ("Ollama (your laptop)", "real local AI models", GOLD, 10.1)]
    for t, s, c, x in side:
        box(ax, x, 0.7, 2.6, 1.3, t, c, size=10.5, sub=s)
        arrow(ax, x + 1.3, 2.05, x + 1.3, 3.2, color=GRAY, style="-")
    save(fig, "architecture")


def hallucination():
    fig, ax = canvas(10.5, 4.2, (0, 10.5), (0, 4.2))
    box(ax, 0.2, 2.4, 4.6, 1.3, "The AI wrote:", CORAL, size=11, sub='"...with 8.69% engagement"')
    box(ax, 5.7, 2.4, 4.6, 1.3, "The ML model says:", GREEN, size=11, sub="4.69% engagement")
    ax.text(5.25, 3.05, "≠", ha="center", va="center", fontsize=34, color=DARK, fontweight="bold")
    arrow(ax, 2.5, 2.35, 5.0, 1.6, color=CORAL)
    arrow(ax, 8.0, 2.35, 5.5, 1.6, color=GREEN)
    box(ax, 2.7, 0.35, 5.1, 1.1, "Number checker: BLOCKED", DARK, size=12, sub="8.69% is not in the evidence, so that sentence is removed")
    save(fig, "hallucination")


def run_steps():
    fig, ax = canvas(12, 3.4, (0, 12), (0, 3.4))
    items = [("1  Get the code", "git clone ...\ncd youtube-strategy-prediction", BLUE), ("2  Run one command", ".\\run.ps1  (Windows)\n./run.sh  (Mac/Linux)", GREEN), ("3  Use the app", "opens in the browser at\nlocalhost:8501", GOLD)]
    for i, (t, s, c) in enumerate(items):
        x = 0.2 + i * 4.0
        box(ax, x, 0.7, 3.5, 2.0, t, c, size=13, sub=s)
        if i < 2:
            arrow(ax, x + 3.55, 1.7, x + 3.95, 1.7)
    save(fig, "run_steps")


def cold_start():
    fig, ax = canvas(11, 4.4, (0, 11), (0, 4.4))
    ax.text(0.1, 4.0, "Without keep-warm", fontsize=12, fontweight="bold", color=CORAL)
    box(ax, 0.1, 3.0, 2.4, 0.7, "No visitors 15 min", GRAY, size=10)
    arrow(ax, 2.55, 3.35, 3.0, 3.35)
    box(ax, 3.05, 3.0, 2.4, 0.7, "Render sleeps", DARK, size=10)
    arrow(ax, 5.5, 3.35, 5.95, 3.35)
    box(ax, 6.0, 3.0, 4.8, 0.7, "Next visitor waits 30-60 s to wake it", CORAL, size=10)
    ax.text(0.1, 2.0, "With keep-warm (GitHub Action pings every 10 min)", fontsize=12, fontweight="bold", color=GREEN)
    for i in range(6):
        box(ax, 0.1 + i * 1.8, 1.0, 1.5, 0.7, "ping", GREEN, size=10)
    ax.text(5.5, 0.35, "Pings stop it from sleeping, so visitors get the page in a second or two", ha="center", fontsize=10.5, color=GRAY, style="italic")
    save(fig, "cold_start")


def hybrid_design():
    fig, ax = canvas(12, 4.4, (0, 12), (0, 4.4))
    box(ax, 0.2, 2.4, 3.6, 1.5, "RULES decide", GREEN, size=13, sub="what to improve + which\nevidence supports it")
    box(ax, 4.2, 2.4, 3.6, 1.5, "AI writes", BLUE, size=13, sub="plain-language explanation,\nnew titles, tags, tips")
    box(ax, 8.2, 2.4, 3.6, 1.5, "CHECKERS filter", CORAL, size=13, sub="each sentence is tested\none by one")
    arrow(ax, 3.85, 3.15, 4.15, 3.15)
    arrow(ax, 7.85, 3.15, 8.15, 3.15)
    ax.text(6, 1.6, "A bad sentence is dropped alone, the good ones are kept", ha="center", fontsize=12, color=DARK, fontweight="bold")
    ax.text(6, 0.9, "Result: faster (about 40 s instead of 100+ s), more reliable, and still personal", ha="center", fontsize=11, color=GRAY)
    save(fig, "hybrid_design")


def conformal_idea(cov):
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.2), gridspec_kw={"width_ratios": [1.2, 1]})
    ax = axes[0]
    low, mid, high, typical = 22.5, 78.1, 271.5, 234.0
    ax.set_xscale("log")
    ax.hlines(1, low, high, color=GREEN, lw=10, alpha=0.35)
    ax.plot([mid], [1], "o", color=GREEN, ms=14)
    ax.plot([typical], [1], "D", color=GOLD, ms=11)
    ax.text(mid, 1.18, "Forecast\n78.1K", ha="center", fontsize=10, color=DARK)
    ax.text(typical, 0.62, "Typical trending\nvideo 234.0K", ha="center", fontsize=9, color=GRAY)
    ax.text(low, 0.84, "22.5K", ha="center", fontsize=9, color=GRAY)
    ax.text(high, 1.1, "271.5K", ha="center", fontsize=9, color=GRAY)
    ax.set_ylim(0.4, 1.5)
    ax.set_yticks([])
    ax.set_xlabel("Views (thousands, log scale)")
    ax.set_title("An 80% range, not a single number", fontsize=11, color=DARK)
    ax.spines["left"].set_visible(False)
    ax = axes[1]
    names = ["Target", "Out-of-fold", "Later uploads\n(views)", "Later uploads\n(engagement)"]
    vals = [80.0, cov["views_out_of_fold"] * 100, cov["views_chronological_holdout"] * 100, cov["engagement_chronological_holdout"] * 100]
    ax.bar(names, vals, color=[GRAY, GREEN, GREEN, GOLD], width=0.6)
    for i, v in enumerate(vals):
        ax.text(i, v + 1, f"{v:.1f}%", ha="center", fontsize=10, fontweight="bold")
    ax.set_ylim(0, 100)
    ax.set_ylabel("% of real values inside the range")
    ax.set_title("We tested it: the promise holds", fontsize=11, color=DARK)
    ax.tick_params(axis="x", labelsize=8.5)
    fig.tight_layout()
    save(fig, "conformal")


# ------------------------------------------------------------------ data-driven charts
def data_charts():
    from src.golden import GOLDEN_DRAFTS
    from src.inference import global_feature_groups, load_bundle
    from src.insights import DAYS, explain_groups, time_grid
    bundle = load_bundle()
    draft = GOLDEN_DRAFTS["education"]

    explanation = explain_groups(bundle, draft)
    table = explanation.table.assign(change=(explanation.table["views_multiplier"] - 1) * 100).sort_values("change")
    fig, ax = plt.subplots(figsize=(9, 4.2))
    ax.barh(table["group"], table["change"], color=[GREEN if v > 0 else CORAL for v in table["change"]])
    for y, v in enumerate(table["change"]):
        ax.text(v + (1.5 if v > 0 else -1.5), y, f"{v:+.0f}%", va="center", ha="left" if v > 0 else "right", fontsize=11, fontweight="bold")
    ax.axvline(0, color=DARK, lw=1)
    ax.set_xlim(table["change"].min() - 14, table["change"].max() + 14)
    ax.set_xlabel("Effect on forecast views vs a typical trending video")
    ax.set_title(f"Why 78.1K and not {explanation.baseline_views / 1000:.0f}K? (real example)", color=DARK)
    save(fig, "shapley_waterfall")

    grid = time_grid(bundle, draft)
    values = grid.table.pivot(index="day", columns="hour", values="views").to_numpy() / 1000
    fig, ax = plt.subplots(figsize=(11, 3.8))
    image = ax.imshow(values, aspect="auto", cmap="YlGn")
    ax.set_yticks(range(7), DAYS)
    ax.set_xticks(range(24), [f"{h:02d}" for h in range(24)], fontsize=8)
    ax.set_xlabel("Hour of day (IST)")
    for _, row in grid.best_slots.iterrows():
        ax.add_patch(plt.Rectangle((row["hour"] - 0.5, row["day"] - 0.5), 1, 1, fill=False, ec=CORAL, lw=2.5))
    ax.add_patch(plt.Rectangle((draft.publish_hour - 0.5, draft.day_of_week - 0.5), 1, 1, fill=False, ec=DARK, lw=2.5, ls="--"))
    cbar = fig.colorbar(image, ax=ax, pad=0.01)
    cbar.set_label("Forecast views (K)")
    ax.set_title("Best time to post: red = best 3 slots, dashed = planned slot", color=DARK)
    save(fig, "best_time")

    groups = global_feature_groups(bundle)
    fig, ax = plt.subplots(figsize=(8.5, 4.2))
    pivot = groups.pivot(index="group", columns="target", values="importance").fillna(0).sort_values("views_log")
    y = np.arange(len(pivot))
    ax.barh(y - 0.2, pivot["views_log"] * 100, 0.4, color=GREEN, label="Views")
    ax.barh(y + 0.2, pivot["engagement_rate"] * 100, 0.4, color=GOLD, label="Engagement")
    ax.set_yticks(y, pivot.index)
    ax.set_xlabel("Share of the model's attention (%)")
    ax.legend(frameon=False)
    ax.set_title("What the model pays attention to", color=DARK)
    save(fig, "feature_groups")

    stats = sorted(bundle["word_stats"].items(), key=lambda kv: kv[1]["views_lift"])
    stats = [kv for kv in stats if kv[1]["n"] >= 40]
    picks = stats[:6] + stats[-6:]
    fig, ax = plt.subplots(figsize=(8.5, 4.6))
    ax.barh([w for w, _ in picks], [s["views_lift"] for _, s in picks], color=[CORAL] * 6 + [GREEN] * 6)
    ax.axvline(1, color=DARK, lw=1, ls="--")
    ax.set_xlabel("Median views vs a typical trending video (1.0 = typical)")
    ax.set_title("Title words that travel with small (red) and big (green) audiences", fontsize=11, color=DARK)
    save(fig, "keywords")
    cov = bundle["calibration"]["coverage_check"]
    conformal_idea(cov)


def tests_chart():
    result = subprocess.run([sys.executable, "-m", "pytest", "--collect-only", "-q"], cwd=ROOT, capture_output=True, text=True)
    counts: dict[str, int] = {}
    for line in result.stdout.splitlines():
        if "::" in line:
            counts[line.split("::")[0].replace("tests/", "").replace(".py", "")] = counts.get(line.split("::")[0].replace("tests/", "").replace(".py", ""), 0) + 1
    names = {"test_golden_predictions": "Numbers never change", "test_real_model": "Real AI model", "test_app": "Whole app", "test_insights": "Explain tools",
             "test_reco_schema": "Answer checkers", "test_reco_evidence": "Evidence", "test_device_and_llm_client": "Device + AI client", "test_launcher": "Launcher",
             "test_advanced_model": "Features", "test_inference": "Predictions", "test_model_contract": "Feature contract", "test_no_secrets": "No passwords", "test_workflows": "Keep-warm", "test_recommendations": "Recommendations"}
    items = sorted(((names.get(k, k), v) for k, v in counts.items()), key=lambda kv: kv[1])
    total = sum(counts.values())
    fig, ax = plt.subplots(figsize=(8.5, 5))
    ax.barh([n for n, _ in items], [v for _, v in items], color=GREEN)
    for y, (_, v) in enumerate(items):
        ax.text(v + 0.3, y, str(v), va="center", fontsize=10)
    ax.set_title(f"{total} automated tests protect the project", color=DARK)
    ax.set_xlabel("Number of tests")
    save(fig, "tests")
    (OUT / "tests_total.json").write_text(json.dumps({"total": total, "by_file": counts}))


if __name__ == "__main__":
    pipeline(); funnel(); r2_progress(); ai_coach_flow(); device_tiers(); architecture(); hallucination(); run_steps(); cold_start(); hybrid_design(); tests_chart(); data_charts()
