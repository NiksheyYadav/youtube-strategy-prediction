import numpy as np
import pytest
import requests

from src.history_features import history_row
from src.channel_history import history_table
from src.youtube_api import (
    MAX_VIDEOS,
    YouTubeAPIError,
    fetch_channel,
    fetch_channel_history,
    parse_duration,
)
from src.youtube_oauth import TokenSet

TOKEN = TokenSet("ya29.SECRET-ACCESS-TOKEN", float("inf"))


class Reply:
    def __init__(self, status=200, body=None):
        self.status_code = status
        self._body = body

    def json(self):
        if self._body is None:
            raise ValueError("no json")
        return self._body


class FakeYouTube:
    """Serves one channel with ``total`` uploads (newest first) and records every request it receives."""

    def __init__(self, total=80, private=(), hidden_likes=(), live=()):
        self.total, self.private, self.hidden_likes, self.live = total, set(private), set(hidden_likes), set(live)
        self.requests = []

    def __call__(self, url, params=None, headers=None, timeout=None):
        self.requests.append({"url": url, "params": dict(params or {}), "headers": dict(headers or {}), "timeout": timeout})
        path = url.rsplit("/", 1)[-1]
        if path == "channels":
            return Reply(200, {"items": [{"id": "UC1", "snippet": {"title": "My channel"}, "statistics": {"videoCount": str(self.total)},
                                          "contentDetails": {"relatedPlaylists": {"uploads": "UU1"}}}]})
        if path == "playlistItems":
            start = int(params.get("pageToken", "0"))
            size = int(params["maxResults"])
            ids = [f"vid{number:05d}" for number in range(start, min(start + size, self.total))]
            body = {"items": [{"contentDetails": {"videoId": vid}} for vid in ids]}
            if start + size < self.total:
                body["nextPageToken"] = str(start + size)
            return Reply(200, body)
        if path == "videos":
            items = []
            for vid in params["id"].split(","):
                number = int(vid[3:])
                stats = {"viewCount": str(1000 + number * 10), "commentCount": "5"}
                if number not in self.hidden_likes:
                    stats["likeCount"] = "50"
                items.append({
                    "id": vid,
                    "snippet": {"title": f"Video {number}\x00", "publishedAt": f"2025-{1 + number % 12:02d}-{1 + number % 27:02d}T10:30:00Z",
                                "tags": ["a", "b"], "description": "desc", "categoryId": "27",
                                "liveBroadcastContent": "live" if number in self.live else "none"},
                    "statistics": stats, "contentDetails": {"duration": "PT1H2M3S"},
                    "status": {"privacyStatus": "private" if number in self.private else "public"},
                })
            return Reply(200, {"items": items})
        return Reply(404, {})


def test_duration_parser():
    assert parse_duration("PT1H2M3S") == 3723 and parse_duration("PT45S") == 45 and parse_duration("P1DT2H") == 86400 + 7200
    assert parse_duration("P0D") == 0
    assert np.isnan(parse_duration(None)) and np.isnan(parse_duration("garbage"))


def test_full_fetch_pages_through_uploads_and_batches_video_details():
    fake = FakeYouTube(total=120)
    history, channel = fetch_channel_history(TOKEN, get=fake, sleep=lambda s: None)
    assert channel["title"] == "My channel" and channel["uploads_playlist"] == "UU1"
    assert len(history.videos) == 120 and history.source == "api"
    calls = [r["url"].rsplit("/", 1)[-1] for r in fake.requests]
    assert calls.count("channels") == 1 and calls.count("playlistItems") == 3 and calls.count("videos") == 3  # 3 x 50 per kind
    assert all(len(r["params"]["id"].split(",")) <= 50 for r in fake.requests if r["url"].endswith("/videos"))
    row = history.videos.iloc[0]
    assert row["category_name"] == "Education" and row["tags"] == "a|b" and row["duration_s"] == 3723
    assert "\x00" not in row["title"], "titles from the channel are sanitised"


def test_the_video_count_is_capped_to_limit_the_quota_used():
    fake = FakeYouTube(total=500)
    history, _ = fetch_channel_history(TOKEN, limit=MAX_VIDEOS, get=fake, sleep=lambda s: None)
    assert len(history.videos) == MAX_VIDEOS
    assert sum(r["url"].endswith("/videos") for r in fake.requests) == 4


def test_the_access_token_is_sent_only_as_a_bearer_header_never_in_the_url_or_params():
    fake = FakeYouTube(total=10)
    fetch_channel_history(TOKEN, get=fake, sleep=lambda s: None)
    for request in fake.requests:
        assert request["headers"] == {"Authorization": f"Bearer {TOKEN.access_token}"}
        assert TOKEN.access_token not in request["url"]
        assert TOKEN.access_token not in repr(request["params"])
        assert request["timeout"] and request["timeout"] > 0


def test_private_scheduled_and_live_videos_are_left_out_and_hidden_counts_stay_missing():
    fake = FakeYouTube(total=10, private={1, 2}, live={3}, hidden_likes={4})
    history, _ = fetch_channel_history(TOKEN, get=fake, sleep=lambda s: None)
    assert len(history.videos) == 7
    assert history.videos["likes"].isna().sum() == 1  # the video with hidden likes keeps NaN, not a made-up zero
    table = history_table(history)
    assert table["engagement"].isna().sum() == 1


def test_engagement_history_is_available_when_likes_and_comments_exist():
    history, _ = fetch_channel_history(TOKEN, get=FakeYouTube(total=12), sleep=lambda s: None)
    row = history_row(history_table(history), history.videos["publish_time"].max() + np.timedelta64(60, "D"))
    assert row["prior_n"] == 12 and row["prior_median_engagement"] > 0


def test_expired_token_is_refused_before_any_request():
    fake = FakeYouTube()
    with pytest.raises(YouTubeAPIError, match="expired"):
        fetch_channel(TokenSet("t", 0.0), get=fake)
    assert fake.requests == []


@pytest.mark.parametrize("status, body, message", [
    (401, {}, "expired"),
    (403, {"error": {"errors": [{"reason": "quotaExceeded"}]}}, "daily limit"),
    (403, {"error": {"errors": [{"reason": "accessNotConfigured"}]}}, "not enabled"),
    (403, {"error": {"errors": [{"reason": "other"}]}}, "did not allow"),
    (404, {}, "error 404"),
])
def test_http_errors_become_plain_messages_without_the_token(status, body, message):
    with pytest.raises(YouTubeAPIError, match=message) as caught:
        fetch_channel(TOKEN, get=lambda *a, **k: Reply(status, body), sleep=lambda s: None)
    assert TOKEN.access_token not in str(caught.value)


def test_server_errors_are_retried_twice_and_then_given_up():
    calls = []

    def flaky(*args, **kwargs):
        calls.append(1)
        return Reply(503, {})

    with pytest.raises(YouTubeAPIError, match="problem right now"):
        fetch_channel(TOKEN, get=flaky, sleep=lambda s: None)
    assert len(calls) == 3, "one try plus two retries, never more"


def test_a_server_error_that_clears_up_succeeds():
    fake = FakeYouTube(total=3)
    outcomes = [Reply(500, {}), None]

    def sometimes(url, **kwargs):
        reply = outcomes.pop(0) if outcomes else None
        return reply if reply is not None else fake(url, **kwargs)

    assert fetch_channel(TOKEN, get=sometimes, sleep=lambda s: None)["title"] == "My channel"


def test_network_errors_are_retried_then_reported_without_details():
    attempts = []

    def offline(*args, **kwargs):
        attempts.append(1)
        raise requests.ConnectionError(f"failed for {TOKEN.access_token}")

    with pytest.raises(YouTubeAPIError, match="Could not reach YouTube") as caught:
        fetch_channel(TOKEN, get=offline, sleep=lambda s: None)
    assert len(attempts) == 3 and TOKEN.access_token not in str(caught.value)


def test_accounts_without_a_channel_or_without_public_videos_get_clear_messages():
    with pytest.raises(YouTubeAPIError, match="No YouTube channel"):
        fetch_channel(TOKEN, get=lambda *a, **k: Reply(200, {"items": []}))
    with pytest.raises(YouTubeAPIError, match="no public videos"):
        fetch_channel_history(TOKEN, get=FakeYouTube(total=0), sleep=lambda s: None)
    with pytest.raises(YouTubeAPIError, match="public or unlisted"):
        fetch_channel_history(TOKEN, get=FakeYouTube(total=3, private={0, 1, 2}), sleep=lambda s: None)
