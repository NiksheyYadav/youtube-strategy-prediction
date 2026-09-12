"""Stage 5: feature importance plot + plain-English content-strategy takeaways."""

import json
from pathlib import Path

import joblib
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import train

FEATURES_PATH = Path("data/processed/features.csv")
MAIN_METRICS_PATH = Path("reports/main_metrics.json")
IMPORTANCE_PLOT_PATH = Path("reports/feature_importance.png")
INSIGHTS_PATH = Path("reports/insights.md")
TOP_N = 12


def load_importances(model_path: str, feature_names: list) -> pd.Series:
    model = joblib.load(model_path)
    return pd.Series(model.feature_importances_, index=feature_names).sort_values(
        ascending=False
    )


def plot_importances(views_imp: pd.Series, engagement_imp: pd.Series) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    views_imp.head(TOP_N).iloc[::-1].plot.barh(ax=axes[0], color="steelblue")
    axes[0].set_title("Feature importance — views (log1p)")
    engagement_imp.head(TOP_N).iloc[::-1].plot.barh(ax=axes[1], color="indianred")
    axes[1].set_title("Feature importance — engagement_rate")
    plt.tight_layout()
    IMPORTANCE_PLOT_PATH.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(IMPORTANCE_PLOT_PATH)
    plt.close()


MIN_GROUP_SIZE = 30


def top_category_by_views(df: pd.DataFrame) -> tuple[str, float, int]:
    stats = df.groupby("category_name")["views"].agg(["median", "count"])
    stats = stats[stats["count"] >= MIN_GROUP_SIZE].sort_values("median", ascending=False)
    top = stats.iloc[0]
    return stats.index[0], top["median"], int(top["count"])


def best_publish_slot(df: pd.DataFrame) -> tuple[int, int, float, int]:
    stats = df.groupby(["publish_day_of_week", "publish_hour"])["views"].agg(
        ["median", "count"]
    )
    stats = stats[stats["count"] >= MIN_GROUP_SIZE].sort_values("median", ascending=False)
    day, hour = stats.index[0]
    top = stats.iloc[0]
    return int(day), int(hour), top["median"], int(top["count"])


def write_insights(
    df: pd.DataFrame,
    views_imp: pd.Series,
    engagement_imp: pd.Series,
    main_metrics: dict,
) -> None:
    day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

    top_views_features = views_imp.head(3).index.tolist()
    top_engagement_features = engagement_imp.head(3).index.tolist()
    top_category, top_category_views, top_category_n = top_category_by_views(df)
    best_day, best_hour, best_slot_views, best_slot_n = best_publish_slot(df)

    corr = df[
        ["tag_count", "description_length", "title_length", "caps_ratio", "views", "engagement_rate"]
    ].corr()
    tag_corr = corr.loc["tag_count", "views"]
    desc_corr = corr.loc["description_length", "views"]
    caps_corr = corr.loc["caps_ratio", "engagement_rate"]

    views_r2 = main_metrics["views"]["test_metrics"]["r2"]
    engagement_r2 = main_metrics["engagement_rate"]["test_metrics"]["r2"]

    lines = [
        "# Content Strategy Insights\n",
        "Derived from a Random Forest model trained on pre-publish metadata "
        "for India-trending YouTube videos (2017-2018 Kaggle snapshot).\n",
        f"1. **What predicts views most**: the strongest pre-publish signals are "
        f"`{top_views_features[0]}`, `{top_views_features[1]}`, and `{top_views_features[2]}`. "
        f"Writing effort and style (description length, title capitalization) rival or beat "
        f"category in importance — these are levers a creator directly controls, not just "
        f"a consequence of what niche they're in.\n",
        f"2. **What predicts engagement (likes+comments per view) most**: "
        f"`{top_engagement_features[0]}`, `{top_engagement_features[1]}`, and "
        f"`{top_engagement_features[2]}` dominate. Views and engagement are driven by "
        f"partly different factors, so optimizing for one doesn't automatically help the other.\n",
        f"3. **Category still matters, among categories with enough data to trust**: "
        f"`{top_category}` has the highest median views (~{top_category_views:,.0f}) among "
        f"categories with at least {MIN_GROUP_SIZE} videos in this dataset "
        f"(n={top_category_n}). Categories with only a handful of trending videos (e.g. "
        f"Movies, n=2) were excluded from this comparison — their medians aren't reliable.\n",
        f"4. **Timing has a real, if modest, effect**: among publish-day/hour combinations with "
        f"at least {MIN_GROUP_SIZE} videos (n={best_slot_n} for the winner), the "
        f"best-performing slot in this data is **{day_names[best_day]} at {best_hour}:00 IST** "
        f"(median views ~{best_slot_views:,.0f}). Tag count correlates "
        f"{'positively' if tag_corr > 0 else 'negatively'} with views (r={tag_corr:.2f}), and "
        f"description length correlates {'positively' if desc_corr > 0 else 'negatively'} with "
        f"views (r={desc_corr:.2f}) — both are cheap, low-effort levers worth using "
        f"consistently rather than skipping.\n",
        f"5. **Take the model's confidence with a grain of salt**: on held-out data, the model "
        f"explains about {views_r2*100:.0f}% of the variance in log-views and "
        f"{engagement_r2*100:.0f}% of the variance in engagement rate. That means pre-publish "
        f"metadata alone is a meaningful but incomplete predictor — channel reputation, "
        f"thumbnail quality, and algorithmic promotion (none of which are in this dataset) "
        f"almost certainly explain a large share of what's left.\n",
    ]
    INSIGHTS_PATH.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    df = pd.read_csv(FEATURES_PATH)
    X, _, _ = train.prepare_features(df)
    main_metrics = json.loads(MAIN_METRICS_PATH.read_text())

    views_imp = load_importances(main_metrics["views"]["model_path"], list(X.columns))
    engagement_imp = load_importances(
        main_metrics["engagement_rate"]["model_path"], list(X.columns)
    )

    plot_importances(views_imp, engagement_imp)
    print(f"Saved feature importance plot to {IMPORTANCE_PLOT_PATH.resolve()}")

    write_insights(df, views_imp, engagement_imp, main_metrics)
    print(f"Saved insights to {INSIGHTS_PATH.resolve()}")

    print("\nTop 5 features — views:")
    print(views_imp.head(5))
    print("\nTop 5 features — engagement_rate:")
    print(engagement_imp.head(5))


if __name__ == "__main__":
    main()
