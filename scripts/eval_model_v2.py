"""Compare model designs with and without channel history (reproducible research probe for model v2).

    python scripts/eval_model_v2.py --sample 800   # quick smoke test (history is broken by sampling: ignore the numbers)
    python scripts/eval_model_v2.py                # full run, writes reports/model_v2_probe.json

Designs (all use the same Random Forest settings as the production model):
  cold       30 content features only (today's model; also the fallback for creators with < 3 usable videos)
  absolute   + channel-history features, target = log views
  lift       target = log views - the channel's mean log views of earlier videos, using level-free history features;
             prediction = baseline + predicted lift (a forest cannot extrapolate, but a lift transfers across channel sizes)
  lift+level lift, but the model may also see the channel's level

Tests: chronological (train on the earliest 80% of videos, test on the latest 20%) and unseen channels (5-fold
GroupKFold, no channel appears in both train and test).  Deployable rule: a design answers only when the video has at
least MIN_USABLE_VIDEOS usable earlier videos; otherwise the cold model answers.  Stress test: every test channel is
made ~20x smaller (history levels and truth shifted by -3 in log space).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import r2_score
from sklearn.model_selection import GroupKFold

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.advanced_model import CATEGORY_COLUMN, CLEAN_PATH, build_feature_table, make_model, model_columns  # noqa: E402
from src.history_features import MIN_USABLE_VIDEOS, add_history_features  # noqa: E402

LEVEL_SHIFT = -3.0  # log space: about 20x fewer views
DESIGNS = ("cold", "absolute", "lift", "lift+level")


def lift_features(history: pd.DataFrame, level: bool) -> pd.DataFrame:
    mean = history["prior_mean_logviews"]
    out = pd.DataFrame({
        "prior_n": history["prior_n"],
        "prior_std_logviews": history["prior_std_logviews"],
        "prior_last_minus_mean": history["prior_last_logviews"] - mean,
        "prior_max_minus_mean": history["prior_max_logviews"] - mean,
        "prior_median_minus_mean": history["prior_median_logviews"] - mean,
        "prior_median_engagement": history["prior_median_engagement"],
        "prior_days_since_last": history["prior_days_since_last"],
        "prior_missing": history["prior_missing"],
    })
    if level:
        out["prior_mean_logviews"] = mean
    return out


def fit(X: pd.DataFrame, y: np.ndarray):
    numeric = [column for column in X.columns if column != CATEGORY_COLUMN]
    model = make_model(numeric, [CATEGORY_COLUMN])
    model.fit(X, y)
    return model


def shift_levels(history: pd.DataFrame, delta: float) -> pd.DataFrame:
    shifted = history.copy()
    usable = shifted["prior_missing"] == 0
    for column in ("prior_mean_logviews", "prior_median_logviews", "prior_last_logviews", "prior_max_logviews"):
        shifted.loc[usable, column] = shifted.loc[usable, column] + delta
    return shifted


def evaluate_split(train: np.ndarray, test: np.ndarray, X0, H, log_views, engagement) -> dict[str, dict[str, float]]:
    usable = (H["prior_n"] >= MIN_USABLE_VIDEOS).to_numpy()
    train_h, test_h = train[usable[train]], test[usable[test]]
    baseline = H["prior_mean_logviews"].to_numpy()
    results: dict[str, dict[str, float]] = {}

    cold = fit(X0.iloc[train], log_views[train])
    cold_pred = cold.predict(X0.iloc[test])
    results["cold"] = {"deployable_r2": r2_score(log_views[test], cold_pred),
                       "history_rows_r2": r2_score(log_views[test_h], cold.predict(X0.iloc[test_h]))}

    def deployable(pred_for_history_rows: np.ndarray) -> dict[str, float]:
        pred = cold_pred.copy()
        pred[usable[test]] = pred_for_history_rows
        return {"deployable_r2": r2_score(log_views[test], pred),
                "history_rows_r2": r2_score(log_views[test_h], pred_for_history_rows)}

    features = {"absolute": pd.concat([X0, H], axis=1), "lift": pd.concat([X0, lift_features(H, False)], axis=1),
                "lift+level": pd.concat([X0, lift_features(H, True)], axis=1)}
    for name, X in features.items():
        is_lift = name.startswith("lift")
        target = log_views - baseline if is_lift else log_views
        model = fit(X.iloc[train_h], target[train_h])
        raw = model.predict(X.iloc[test_h])
        pred = raw + baseline[test_h] if is_lift else raw
        results[name] = deployable(pred)

        # stress test: the same videos from a channel ~20x smaller
        shifted_h = shift_levels(H, LEVEL_SHIFT)
        X_shift = pd.concat([X0, shifted_h if name == "absolute" else lift_features(shifted_h, name == "lift+level")], axis=1)
        raw_shift = model.predict(X_shift.iloc[test_h])
        shifted_baseline = shifted_h["prior_mean_logviews"].to_numpy()[test_h]
        pred_shift = raw_shift + shifted_baseline if is_lift else raw_shift
        results[name]["stress_r2_small_channel"] = r2_score(log_views[test_h] + LEVEL_SHIFT, pred_shift)

    # engagement: rate target, so only absolute-vs-cold is meaningful
    eng_cold = fit(X0.iloc[train], engagement[train])
    eng_abs = fit(features["absolute"].iloc[train_h], engagement[train_h])
    results["engagement"] = {
        "cold_r2": r2_score(engagement[test], eng_cold.predict(X0.iloc[test])),
        "absolute_history_rows_r2": r2_score(engagement[test_h], eng_abs.predict(features["absolute"].iloc[test_h])),
        "cold_history_rows_r2": r2_score(engagement[test_h], eng_cold.predict(X0.iloc[test_h])),
    }
    return results


def average(runs: list[dict[str, dict[str, float]]]) -> dict[str, dict[str, float]]:
    return {design: {metric: float(np.mean([run[design][metric] for run in runs])) for metric in runs[0][design]}
            for design in runs[0]}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample", type=int, default=0, help="use only N random videos (smoke test)")
    parser.add_argument("--out", default=str(ROOT / "reports" / "model_v2_probe.json"))
    args = parser.parse_args()

    data = pd.read_csv(CLEAN_PATH)
    if args.sample:
        data = data.sample(args.sample, random_state=42).reset_index(drop=True)
    table = build_feature_table(data)
    numeric, categorical = model_columns(table)
    X0 = table[numeric + categorical].reset_index(drop=True)
    log_views = np.log1p(table["views"].to_numpy(float))
    engagement = table["engagement_rate"].to_numpy(float)
    frame = pd.DataFrame({
        "channel_title": data["channel_title"].to_numpy(),
        "publish_time": pd.to_datetime(data["publish_time"], utc=True),
        "known_at": (pd.to_datetime(data["trending_date"]) + pd.Timedelta(days=1)).dt.tz_localize("UTC"),
        "views": data["views"].astype(float).to_numpy(),
        "engagement": engagement,
    })
    H = add_history_features(frame)
    usable = H["prior_n"] >= MIN_USABLE_VIDEOS
    print(f"{len(data):,} videos; {usable.mean():.1%} have >= {MIN_USABLE_VIDEOS} usable earlier videos")

    order = np.argsort(frame["publish_time"].to_numpy())
    cut = int(len(order) * 0.8)
    print("chronological test ...", flush=True)
    chronological = evaluate_split(order[:cut], order[cut:], X0, H, log_views, engagement)

    print("unseen-channel test (5 folds) ...", flush=True)
    folds = []
    for number, (train, test) in enumerate(GroupKFold(n_splits=5).split(X0, groups=data["channel_title"])):
        folds.append(evaluate_split(train, test, X0, H, log_views, engagement))
        print(f"  fold {number + 1}/5 done", flush=True)
    unseen = average(folds)

    report = {"videos": int(len(data)), "share_with_usable_history": float(usable.mean()), "min_usable_videos": MIN_USABLE_VIDEOS,
              "level_shift_log": LEVEL_SHIFT, "chronological": chronological, "unseen_channels": unseen,
              "note": "stress_r2_small_channel is a synthetic what-if (channel made ~20x smaller), not a measured accuracy."}
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(report, indent=2), encoding="utf-8")

    for title, block in (("CHRONOLOGICAL", chronological), ("UNSEEN CHANNELS", unseen)):
        print(f"\n{title} (log-views R2)")
        print(f"{'design':<12}{'deployable':>12}{'history rows':>14}{'stress: small':>15}")
        for design in DESIGNS:
            row = block[design]
            print(f"{design:<12}{row['deployable_r2']:>12.3f}{row['history_rows_r2']:>14.3f}{row.get('stress_r2_small_channel', float('nan')):>15.3f}")
        eng = block["engagement"]
        print(f"engagement R2 on history rows: cold {eng['cold_history_rows_r2']:.3f} -> with history {eng['absolute_history_rows_r2']:.3f}")
    print(f"\nwrote {args.out}")


if __name__ == "__main__":
    main()
