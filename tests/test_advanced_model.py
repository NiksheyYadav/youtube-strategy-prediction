from pathlib import Path

import numpy as np
import pandas as pd

import json

from src.advanced_model import build_demo_features, category_mapping, model_columns, normalise_tags


def test_demo_features_are_prepublication_only_and_complete():
    frame = build_demo_features(
        title="5 Study Tips! How to Prepare?",
        tags="study tips, exam prep|productivity",
        description="Subscribe for more study tips. https://example.com #students",
        category_name="Education",
        day_of_week=5,
        publish_hour=18,
    )

    forbidden = {"views", "likes", "dislikes", "comment_count", "video_id", "channel_title"}
    assert forbidden.isdisjoint(frame.columns)
    assert frame.loc[0, "title_digit_count"] == 1
    assert frame.loc[0, "title_exclamation_count"] == 1
    assert frame.loc[0, "title_question_count"] == 1
    assert frame.loc[0, "tag_count"] == 3
    assert frame.loc[0, "description_link_count"] == 1
    assert frame.loc[0, "description_hashtag_count"] == 1
    assert frame.loc[0, "is_weekend"] == 1


def test_model_columns_exclude_targets_and_time_reference():
    frame = build_demo_features("Title", "tag", "description", "Education", 0, 12)
    frame["views"] = [100]
    frame["engagement_rate"] = [0.1]
    frame["publish_timestamp"] = pd.Timestamp("2018-01-01", tz="UTC")
    numeric, categorical = model_columns(frame)

    assert categorical == ["category_name"]
    assert "views" not in numeric
    assert "engagement_rate" not in numeric
    assert "publish_timestamp" not in numeric
    assert "title_length" in numeric


def test_category_29_is_named_even_though_the_kaggle_json_omits_it(tmp_path):
    path = tmp_path / "categories.json"
    path.write_text(json.dumps({"items": [{"id": "10", "snippet": {"title": "Music"}}]}), encoding="utf-8")
    mapping = category_mapping(path)
    assert mapping["10"] == "Music"
    assert mapping["29"] == "Nonprofits & Activism"


def test_tag_quotes_from_the_training_data_match_live_input():
    """Kaggle tags carry literal quotes; users type none. Both must give identical tags."""
    training_style = 'study tips|"exam prep"|"productivity"'
    live_style = "study tips, exam prep, productivity"
    a = build_demo_features("T", training_style, "d", "Education", 1, 9).iloc[0]
    b = build_demo_features("T", live_style, "d", "Education", 1, 9).iloc[0]
    assert a["tag_count"] == b["tag_count"] == 3
    assert a["tag_total_characters"] == b["tag_total_characters"]
    assert normalise_tags("") == "[none]" and normalise_tags(None) == "[none]"


def test_hashtags_and_www_links_are_counted():
    row = build_demo_features("T", "a", "See www.example.com and #one #two", "Education", 1, 9).iloc[0]
    assert row["description_link_count"] == 1
    assert row["description_hashtag_count"] == 2
