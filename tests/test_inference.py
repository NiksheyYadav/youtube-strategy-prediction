import numpy as np

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
