import numpy as np
import pandas as pd
import pytest

from src.history_features import HISTORY_COLUMNS, MISSING_FILL, add_history_features, history_row


def _videos(rows):
    frame = pd.DataFrame(rows, columns=["channel_title", "publish_time", "known_at", "views", "engagement"])
    frame["publish_time"] = pd.to_datetime(frame["publish_time"], utc=True)
    frame["known_at"] = pd.to_datetime(frame["known_at"], utc=True)
    return frame


@pytest.fixture
def channel():
    return _videos([
        ("A", "2024-01-01", "2024-01-05", 1_000, 0.05),
        ("A", "2024-01-10", "2024-01-14", 3_000, 0.03),
        ("A", "2024-01-20", "2024-01-24", 9_000, 0.04),
        ("A", "2024-02-01", "2024-02-05", 5_000, 0.06),
        ("B", "2024-01-03", "2024-01-08", 100, 0.10),
    ])


def test_first_video_of_a_channel_has_no_history(channel):
    features = add_history_features(channel)
    first = features.iloc[0]
    assert first["prior_n"] == 0 and first["prior_missing"] == 1
    assert first["prior_mean_logviews"] == MISSING_FILL
    # a channel with a single video never has history either
    assert features.iloc[4]["prior_missing"] == 1


def test_history_values_are_computed_from_earlier_videos_only(channel):
    row = add_history_features(channel).iloc[3]  # A's 4th video, published 2024-02-01
    logs = np.log1p([1_000, 3_000, 9_000])
    assert row["prior_n"] == 3 and row["prior_missing"] == 0
    assert row["prior_mean_logviews"] == pytest.approx(logs.mean())
    assert row["prior_median_logviews"] == pytest.approx(np.median(logs))
    assert row["prior_last_logviews"] == pytest.approx(np.log1p(9_000))
    assert row["prior_max_logviews"] == pytest.approx(np.log1p(9_000))
    assert row["prior_std_logviews"] == pytest.approx(logs.std())
    assert row["prior_median_engagement"] == pytest.approx(0.04)
    assert row["prior_days_since_last"] == pytest.approx(12.0)


def test_no_look_ahead_video_is_ignored_until_its_views_are_known():
    frame = _videos([
        ("A", "2024-01-01", "2024-01-20", 50_000, 0.05),   # views only known on 20 Jan
        ("A", "2024-01-10", "2024-01-12", 2_000, 0.05),    # published 10 Jan: the first video's views are NOT known yet
        ("A", "2024-01-25", "2024-01-27", 4_000, 0.05),    # published 25 Jan: both are known
    ])
    features = add_history_features(frame)
    assert features.iloc[1]["prior_missing"] == 1, "a video whose views were unknown must not count"
    assert features.iloc[2]["prior_n"] == 2


def test_results_do_not_depend_on_row_order(channel):
    shuffled = channel.sample(frac=1.0, random_state=3)
    original = add_history_features(channel)
    again = add_history_features(shuffled).loc[original.index]
    pd.testing.assert_frame_equal(original, again)


def test_live_row_matches_training_row(channel):
    """The live app (history_row) must give exactly what training (add_history_features) gave for the same video."""
    trained = add_history_features(channel).iloc[3]
    live = history_row(channel[channel["channel_title"] == "A"].iloc[:3], channel.iloc[3]["publish_time"])
    for name in HISTORY_COLUMNS:
        assert live[name] == pytest.approx(trained[name])


def test_recent_window_keeps_only_the_newest_videos(channel):
    live = history_row(channel[channel["channel_title"] == "A"].iloc[:3], pd.Timestamp("2024-02-01", tz="UTC"), recent=2)
    assert live["prior_n"] == 2
    assert live["prior_mean_logviews"] == pytest.approx(np.log1p([3_000, 9_000]).mean())


def test_empty_or_unknown_history_gives_the_missing_row(channel):
    assert history_row(channel.iloc[:0], pd.Timestamp("2024-03-01", tz="UTC"))["prior_missing"] == 1
    assert history_row(None, pd.Timestamp("2024-03-01", tz="UTC"))["prior_n"] == 0
    # nothing published before the new video
    assert history_row(channel.iloc[:3], pd.Timestamp("2023-12-31", tz="UTC"))["prior_missing"] == 1


def test_missing_engagement_does_not_break_the_row():
    frame = _videos([("A", "2024-01-01", "2024-01-02", 10, np.nan), ("A", "2024-01-05", "2024-01-06", 20, np.nan),
                     ("A", "2024-01-09", "2024-01-10", 30, np.nan)])
    features = add_history_features(frame)
    assert features.iloc[2]["prior_median_engagement"] == MISSING_FILL
    assert features.iloc[2]["prior_n"] == 2


def test_naive_timestamps_are_treated_as_utc(channel):
    history = channel[channel["channel_title"] == "A"].iloc[:3].copy()
    history["publish_time"] = history["publish_time"].dt.tz_localize(None)
    history["known_at"] = history["known_at"].dt.tz_localize(None)
    assert history_row(history, pd.Timestamp("2024-02-01"))["prior_n"] == 3
