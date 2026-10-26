"""Create explainability artifacts for the advanced v2 model."""

from __future__ import annotations

import json
from pathlib import Path

import joblib
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from model_contract import friendly_feature_name

ROOT = Path(__file__).resolve().parents[1]
FEATURES_PATH = ROOT / "data" / "processed" / "advanced_features.csv"
METRICS_PATH = ROOT / "reports" / "advanced_metrics.json"
SCHEMA_PATH = ROOT / "models" / "feature_schema_v2.json"
PLOT_PATH = ROOT / "reports" / "advanced_feature_importance.png"
CSV_PATH = ROOT / "reports" / "advanced_feature_importance.csv"
INSIGHTS_PATH = ROOT / "reports" / "advanced_insights.md"
TOP_N = 12


def _importance(model: object, columns: list[str]) -> pd.Series:
    if not hasattr(model, "feature_importances_"):
        raise TypeError("The selected model does not expose tree feature importances.")
    return pd.Series(model.feature_importances_, index=columns).sort_values(ascending=False)


def _friendly(series: pd.Series) -> pd.Series:
    copy = series.copy()
    copy.index = [friendly_feature_name(name) for name in copy.index]
    return copy


def main() -> None:
    metrics = json.loads(METRICS_PATH.read_text(encoding="utf-8"))
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    table = pd.read_csv(FEATURES_PATH)
    columns = schema["design_matrix_columns"]
    view_model = joblib.load(ROOT / schema["models"]["views"]["path"])
    engagement_model = joblib.load(ROOT / schema["models"]["engagement_rate"]["path"])
    views_importance = _importance(view_model, columns)
    engagement_importance = _importance(engagement_model, columns)

    importance_table = pd.DataFrame(
        {
            "feature": columns,
            "feature_label": [friendly_feature_name(item) for item in columns],
            "views_importance": views_importance.reindex(columns).to_numpy(),
            "engagement_importance": engagement_importance.reindex(columns).to_numpy(),
        }
    ).sort_values("views_importance", ascending=False)
    importance_table.to_csv(CSV_PATH, index=False)

    fig, axes = plt.subplots(1, 2, figsize=(15, 7))
    for axis, importances, color, label in [
        (axes[0], views_importance, "#F04D2E", "Views, log scale"),
        (axes[1], engagement_importance, "#1C9E9A", "Engagement rate"),
    ]:
        display = _friendly(importances.head(TOP_N).iloc[::-1])
        display.plot.barh(ax=axis, color=color)
        axis.set_title(f"Top v2 feature importance: {label}", weight="bold")
        axis.set_xlabel("Impurity-based importance")
        axis.set_ylabel("")
        axis.grid(axis="x", alpha=0.22)
    fig.suptitle("Explainable pre-publication signals", fontsize=16, weight="bold")
    fig.tight_layout()
    fig.savefig(PLOT_PATH, dpi=180, bbox_inches="tight")
    plt.close(fig)

    top_views = [_friendly(views_importance).index[index] for index in range(3)]
    top_engagement = [_friendly(engagement_importance).index[index] for index in range(3)]
    categories = table.groupby("category_name")["views"].agg(["median", "count"])
    trusted_categories = categories[categories["count"] >= 30].sort_values("median", ascending=False)
    category_name = trusted_categories.index[0]
    category_median = trusted_categories.iloc[0]["median"]
    day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    slots = table.groupby(["publish_day_of_week", "publish_hour"])["views"].agg(["median", "count"])
    trusted_slots = slots[slots["count"] >= 30].sort_values("median", ascending=False)
    day, hour = trusted_slots.index[0]
    slot_median = trusted_slots.iloc[0]["median"]
    views_r2 = metrics["views"]["held_out_test"]["r2"]
    engagement_r2 = metrics["engagement_rate"]["held_out_test"]["r2"]
    chrono_views_r2 = metrics["views"]["chronological_holdout"]["r2"]
    chrono_engagement_r2 = metrics["engagement_rate"]["chronological_holdout"]["r2"]

    lines = [
        "# Advanced Model v2: Explainable Insights",
        "",
        "These results use only metadata that a creator knows before publishing. Feature importance describes patterns in this historical, trending-only dataset; it does not prove a causal rule.",
        "",
        f"1. **Strongest view signals:** {', '.join(top_views)}. The model makes use of richer title, tags, description and publication-time signals rather than post-publication counts.",
        f"2. **Strongest engagement signals:** {', '.join(top_engagement)}. This differs from views, so a creator can discuss reach and audience reaction as separate objectives.",
        f"3. **Reference category:** `{category_name}` had the highest median views among categories with at least 30 records (median about {category_median:,.0f}). This is a benchmark from the sample, not a category recommendation for every creator.",
        f"4. **Reference publishing window:** the largest median view count among adequately represented day-hour slots was {day_names[int(day)]} at {int(hour):02d}:00 IST (about {slot_median:,.0f} median views). Time effects are modest and should be tested with a creator's own audience.",
        f"5. **Validation is intentionally shown two ways:** the random held-out R² is {views_r2:.3f} for log-views and {engagement_r2:.3f} for engagement. A stricter chronological test scores {chrono_views_r2:.3f} and {chrono_engagement_r2:.3f}, showing why a future-period test is useful when data can drift.",
        "",
        "## Limits to say in the viva",
        "",
        "The Kaggle data contains videos that were already trending in India during 2017–2018. It cannot estimate the probability that an arbitrary new upload will trend. Channel reputation, thumbnail quality, audience retention and YouTube’s internal recommendation signals are unavailable, so the application presents estimates and comparison signals, not guarantees.",
    ]
    INSIGHTS_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Saved {PLOT_PATH}")
    print(f"Saved {CSV_PATH}")
    print(f"Saved {INSIGHTS_PATH}")


if __name__ == "__main__":
    main()
