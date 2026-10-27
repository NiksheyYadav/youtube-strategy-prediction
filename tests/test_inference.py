import numpy as np
import pytest

from src.inference import load_bundle, normalise_tags, predict_video


def test_tag_normalisation_accepts_common_separators():
    assert normalise_tags("one, two; three|four") == "one|two|three|four"
    assert normalise_tags("") == "[none]"


def test_saved_model_predicts_with_exact_feature_schema():
    bundle = load_bundle()
    prediction = predict_video(
        bundle,
        title="How to Build a Better Study Routine in 5 Steps",
        tags="study tips, productivity, exam preparation",
        description="A practical student guide. Subscribe and share your routine in the comments.",
        category_name="Education",
        day_of_week=5,
        publish_hour=18,
    )

    assert list(prediction.feature_row.columns) == list(bundle["input_columns"])
    assert np.isfinite(prediction.expected_views)
    assert np.isfinite(prediction.engagement_rate)
    assert prediction.expected_views >= 0
    assert prediction.views_high >= prediction.views_low >= 0
    assert prediction.engagement_high >= prediction.engagement_low >= 0


@pytest.mark.parametrize("day, hour", [(-1, 12), (7, 12), (3, -1), (3, 24), (3, 99)])
def test_impossible_publish_day_or_hour_is_rejected_not_silently_forecast(day, hour):
    """Mutation check: removing these checks used to change no test, so a bad hour would be forecast as if it were real."""
    with pytest.raises(ValueError):
        predict_video(load_bundle(), title="A fine title", tags="a|b", description="d", category_name="Education", day_of_week=day, publish_hour=hour)


@pytest.mark.parametrize("title", ["", "   ", "\t\n"])
def test_a_blank_title_is_rejected(title):
    with pytest.raises(ValueError):
        predict_video(load_bundle(), title=title, tags="", description="", category_name="Education", day_of_week=3, publish_hour=12)
