"""The training pipeline, run for real on a sample of the real data (before this file nothing tested retraining).

Covers the fixes from the audit: engagement is only learned from videos where it can be measured, titles in any script are
read as words, accuracy is measured on channels the model has never seen, and interval widths follow the category.
"""

from __future__ import annotations

import json

import numpy as np
import pandas as pd
import pytest

from src.advanced_model import (
    CLEAN_PATH,
    build_bundle,
    engagement_rates,
    engagement_valid_mask,
    non_latin_share,
)
from src.inference import headline_accuracy, interval_widths, load_bundle
from src.insights import _weighted_median
from src.insights_artifacts import word_tokens
from tests.real_data import requires_data


# --------------------------------------------------------------------------- #
# Words in any script
# --------------------------------------------------------------------------- #
def test_hindi_tamil_and_english_titles_are_split_into_words():
    assert word_tokens("Salman Khan का नया गाना") == ["salman", "khan", "का", "नया", "गाना"]
    assert word_tokens("தமிழ் படம் trailer") == ["தமிழ்", "படம்", "trailer"]
    assert word_tokens("Don't miss IPL 2018!") == ["don't", "miss", "ipl", "2018"]
    assert word_tokens("!!! ??? ...") == []


def test_share_of_non_latin_letters():
    assert non_latin_share("Salman Khan new song") == 0.0
    assert non_latin_share("सलमान खान") == 1.0
    assert 0.0 < non_latin_share("Salman सलमान") < 1.0
    assert non_latin_share("123 !!!") == 0.0


@requires_data
def test_real_hindi_titles_are_no_longer_read_as_empty():
    data = pd.read_csv(CLEAN_PATH)
    shares = data["title"].fillna("").map(non_latin_share)
    hindi_like = data.loc[shares >= 0.5, "title"]
    assert len(hindi_like) > 500, "the India data should contain many titles in other scripts"
    assert (hindi_like.map(lambda title: len(word_tokens(title))) > 0).mean() > 0.99


# --------------------------------------------------------------------------- #
# Engagement is only measurable when ratings and comments are on
# --------------------------------------------------------------------------- #
@requires_data
def test_videos_with_ratings_or_comments_off_have_no_engagement_rate():
    data = pd.read_csv(CLEAN_PATH)
    mask = engagement_valid_mask(data)
    rates = engagement_rates(data)
    off = data["ratings_disabled"].astype(str).str.lower().eq("true") | data["comments_disabled"].astype(str).str.lower().eq("true")
    assert off.sum() > 100, "the real data contain videos with ratings or comments switched off"
    assert np.isnan(rates[off.to_numpy()]).all()
    assert not mask[off.to_numpy()].any()
    on = ~off.to_numpy()
    expected = (data.loc[on, "likes"] + data.loc[on, "comment_count"]) / data.loc[on, "views"]
    assert np.allclose(rates[on], expected.to_numpy())
    assert (rates[on] > 0).mean() > 0.99, "an enabled video with exactly zero reactions is the rare exception, not the rule"


def test_look_alike_median_skips_videos_without_a_rate():
    weights = np.array([1.0, 1.0, 1.0, 1.0])
    assert _weighted_median(np.array([0.01, np.nan, 0.03, 0.02]), weights) == pytest.approx(0.02)
    assert _weighted_median(np.array([np.nan, np.nan]), np.array([1.0, 1.0])) is None


# --------------------------------------------------------------------------- #
# The training run itself, on real videos
# --------------------------------------------------------------------------- #
@pytest.fixture(scope="module")
def trained():
    if not CLEAN_PATH.exists():
        pytest.skip("needs data/processed/clean.csv (run: python src/clean.py)")
    data = pd.read_csv(CLEAN_PATH).sample(700, random_state=11).reset_index(drop=True)
    bundle, similarity, table = build_bundle(data, n_estimators=25)
    return data, bundle, similarity, table


def test_training_run_produces_a_complete_bundle(trained):
    data, bundle, similarity, table = trained
    assert bundle["version"] == "ta4-explainable-v3"
    assert bundle["training_rows"] == len(data) == len(table)
    assert set(bundle["models"]) == {"views_log", "engagement_rate"}
    for key in ("input_columns", "numeric_summary", "categories", "metrics", "calibration", "reference", "word_stats", "background"):
        assert key in bundle
    assert "title_non_latin_share" in bundle["input_columns"]
    json.dumps(bundle["calibration"])  # the report written next to the model must be serialisable
    json.dumps(bundle["metrics"])
    assert len(similarity["video_id"]) == len(data)


def test_data_quality_counts_match_the_data(trained):
    data, bundle, _, _ = trained
    quality = bundle["data_quality"]
    assert quality["videos"] == len(data)
    assert quality["engagement_not_measurable"] == int((~engagement_valid_mask(data)).sum())
    assert quality["channels"] == data["channel_title"].nunique()
    assert 0 < quality["engagement_not_measurable"] < len(data)


def test_engagement_model_never_saw_unmeasurable_videos(trained):
    """No NaN reaches the learner and the similarity index keeps the gap visible instead of inventing a rate."""
    _, bundle, similarity, table = trained
    assert table["engagement_rate"].isna().sum() == bundle["data_quality"]["engagement_not_measurable"]
    assert np.isnan(similarity["engagement"]).sum() == bundle["data_quality"]["engagement_not_measurable"]
    assert np.isfinite(bundle["calibration"]["engagement_q"])
    assert all(np.isfinite(bundle["reference"]["engagement_oof_sorted"]))


def test_three_tests_are_reported_and_the_shuffled_one_reads_highest(trained):
    _, bundle, _, _ = trained
    for target in ("views_log", "engagement_rate"):
        metrics = bundle["metrics"][target]
        assert set(metrics) >= {"five_fold_cv", "chronological_holdout", "unseen_channel_cv", "unseen_channel_by_title_script"}
        assert metrics["unseen_channel_cv"]["r2_mean"] < metrics["five_fold_cv"]["r2_mean"], \
            "with the same channel on both sides of the split the model should look better than on unseen channels"


def test_intervals_are_calibrated_on_unseen_channels(trained):
    _, bundle, _, _ = trained
    calibration = bundle["calibration"]
    assert calibration["calibrated_on"] == "out-of-fold predictions for channels never seen in training"
    assert 0.7 <= calibration["coverage_check"]["views_out_of_fold"] <= 0.9
    assert calibration["views_log_q"] > 0 and calibration["engagement_q"] > 0


# --------------------------------------------------------------------------- #
# The shipped model (what the app really uses)
# --------------------------------------------------------------------------- #
@pytest.fixture(scope="module")
def shipped():
    return load_bundle()


def test_shipped_model_reports_accuracy_on_unseen_channels(shipped):
    accuracy = headline_accuracy(shipped)
    assert accuracy["basis"] == "channels the model had never seen"
    assert accuracy["views_r2"] < accuracy["shuffled_views_r2"]
    assert accuracy["engagement_r2"] < accuracy["shuffled_engagement_r2"]
    assert 0.0 < accuracy["views_r2"] < 1.0 and 0.0 < accuracy["engagement_r2"] < 1.0


def test_shipped_model_left_out_videos_without_a_measurable_engagement(shipped):
    quality = shipped["data_quality"]
    assert quality["engagement_not_measurable"] > 100
    assert quality["videos"] == shipped["training_rows"]


def test_shipped_model_reads_titles_in_other_scripts(shipped):
    scripts = shipped["metrics"]["views_log"]["unseen_channel_by_title_script"]
    assert scripts["non_latin_titles"]["n"] > 500
    assert scripts["non_latin_titles"]["r2"] > 0.0, "titles in Hindi, Tamil and the rest must be better than guessing the average"


def test_a_category_with_enough_videos_gets_its_own_interval_width(shipped):
    calibration = shipped["calibration"]
    own = calibration["views_log_q_by_category"]
    assert len(own) >= 5
    name = sorted(own)[0]
    q_views, _, basis = interval_widths(calibration, name)
    assert q_views == own[name] and basis == name
    q_views, _, basis = interval_widths(calibration, "A category that does not exist")
    assert q_views == calibration["views_log_q"] and basis == "all trending videos"


def test_category_widths_cover_later_uploads_at_least_as_evenly_as_one_global_width(shipped):
    """The audit found one global width covering only half of Gaming videos and almost all of Shows."""
    rows = shipped["calibration"]["coverage_check"]["views_later_videos_by_category"]
    assert len(rows) >= 4
    miss_global = np.mean([abs(row["global_width_coverage"] - 0.8) for row in rows.values()])
    miss_category = np.mean([abs(row["category_width_coverage"] - 0.8) for row in rows.values()])
    assert miss_category <= miss_global + 0.01, (miss_category, miss_global)


def test_shipped_models_match_the_feature_code(shipped):
    from src.history_model import load_history_models
    from src.inference import feature_mismatch

    assert feature_mismatch(shipped["input_columns"]) == ""
    assert load_history_models() is not None, "the shipped history model must not be refused"


def test_a_model_trained_with_other_features_is_refused_with_a_plain_message(shipped, tmp_path):
    """Reproduces the reported crash: code that has a feature the saved model does not, and the reverse."""
    import joblib

    old = dict(shipped)
    old["input_columns"] = [name for name in shipped["input_columns"] if name != "title_non_latin_share"]
    path = tmp_path / "old.joblib"
    joblib.dump(old, path)
    with pytest.raises(ValueError, match="different set of features.*title_non_latin_share.*advanced_model.py --train"):
        load_bundle(path)

    newer = dict(shipped)
    newer["input_columns"] = list(shipped["input_columns"]) + ["a_feature_this_code_never_builds"]
    joblib.dump(newer, path)
    with pytest.raises(ValueError, match="a_feature_this_code_never_builds"):
        load_bundle(path)


def test_the_saved_look_alike_index_loads_in_a_clean_interpreter():
    """Training run as a plain script once saved the word splitter under a bare module name, so the app could not load it."""
    import subprocess
    import sys
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    code = ("from src.insights import load_similarity_index; i = load_similarity_index(); "
            "print(i['vectorizer'].tokenizer.__module__, len(i['video_id']))")
    result = subprocess.run([sys.executable, "-c", code], cwd=root, capture_output=True, text=True, timeout=120)
    assert result.returncode == 0, result.stderr[-500:]
    assert result.stdout.split()[0] == "src.insights_artifacts"
