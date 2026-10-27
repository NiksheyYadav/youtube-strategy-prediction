"""Read the signed-in creator's own videos through the YouTube Data API v3 (read-only, nothing is stored).

Quota cost is tiny: one call for the channel, one per 50 uploads for the list and one per 50 videos for their details,
so 200 videos use about 9 of the 10,000 units a project gets per day.  Calls use the Bearer header, so the access token
never appears in a URL, a log line or an error message.  Text from the channel is untrusted and is sanitised by
``channel_history.clean_videos``.
"""

from __future__ import annotations

import re
import time
from typing import Callable

import numpy as np
import pandas as pd
import requests

from src.youtube_oauth import TokenSet
from src.channel_history import ChannelHistory, clean_videos

API_ROOT = "https://www.googleapis.com/youtube/v3"
MAX_VIDEOS = 200
PAGE_SIZE = 50
RETRIES = 2            # a server error is retried twice, never more
TIMEOUT_S = 20
KEEP_PRIVACY = {"public", "unlisted"}
CATEGORY_NAMES = {
    "1": "Film & Animation", "2": "Autos & Vehicles", "10": "Music", "15": "Pets & Animals", "17": "Sports", "19": "Travel & Events",
    "20": "Gaming", "22": "People & Blogs", "23": "Comedy", "24": "Entertainment", "25": "News & Politics", "26": "Howto & Style",
    "27": "Education", "28": "Science & Technology", "29": "Nonprofits & Activism",
}
_DURATION = re.compile(r"^P(?:(\d+)D)?(?:T(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?)?$")


class YouTubeAPIError(Exception):
    """A problem talking to YouTube, worded for the creator (never contains the token)."""


def parse_duration(value: str | None) -> float:
    """ISO-8601 duration such as ``PT1H2M3S`` in seconds (NaN when missing or unreadable)."""
    match = _DURATION.match(value or "")
    if not match:
        return float("nan")
    days, hours, minutes, seconds = (int(part or 0) for part in match.groups())
    return float(days * 86400 + hours * 3600 + minutes * 60 + seconds)


def _reason(response: requests.Response) -> str:
    try:
        error = response.json().get("error", {})
        errors = error.get("errors") or [{}]
        return str(errors[0].get("reason") or error.get("status") or "")
    except (ValueError, AttributeError, IndexError):
        return ""


def _request(
    path: str,
    params: dict[str, str | int | bool],
    token: TokenSet,
    *,
    get: Callable[..., requests.Response] | None = None,
    sleep: Callable[[float], None] = time.sleep,
) -> dict:
    if token.expired():
        raise YouTubeAPIError("Your Google sign-in has expired. Please connect again.")
    get = get or requests.get
    response = None
    for attempt in range(RETRIES + 1):
        try:
            response = get(f"{API_ROOT}/{path}", params=params, headers={"Authorization": f"Bearer {token.access_token}"}, timeout=TIMEOUT_S)
        except requests.RequestException as error:
            if attempt < RETRIES:
                sleep(1.5 * (attempt + 1))
                continue
            raise YouTubeAPIError("Could not reach YouTube. Check the internet connection and try again.") from error
        if response.status_code >= 500 and attempt < RETRIES:
            sleep(1.5 * (attempt + 1))
            continue
        break
    assert response is not None
    if response.status_code == 200:
        try:
            return response.json()
        except ValueError as error:
            raise YouTubeAPIError("YouTube sent an unreadable answer. Please try again.") from error
    reason = _reason(response)
    if response.status_code == 401:
        raise YouTubeAPIError("Your Google sign-in has expired. Please connect again.")
    if reason in {"quotaExceeded", "rateLimitExceeded", "dailyLimitExceeded"}:
        raise YouTubeAPIError("YouTube's daily limit for this app has been reached. Please try again tomorrow.")
    if reason in {"accessNotConfigured", "SERVICE_DISABLED"}:
        raise YouTubeAPIError("The YouTube Data API is not enabled for this app's Google Cloud project.")
    if response.status_code == 403:
        raise YouTubeAPIError("YouTube did not allow access to this channel's videos.")
    if response.status_code >= 500:
        raise YouTubeAPIError("YouTube is having a problem right now. Please try again in a few minutes.")
    raise YouTubeAPIError(f"YouTube could not complete the request (error {response.status_code}).")


def fetch_channel(token: TokenSet, *, get: Callable[..., requests.Response] | None = None, sleep: Callable[[float], None] = time.sleep) -> dict[str, object]:
    body = _request("channels", {"part": "snippet,contentDetails,statistics", "mine": "true"}, token, get=get, sleep=sleep)
    items = body.get("items") or []
    if not items:
        raise YouTubeAPIError("No YouTube channel is linked to this Google account.")
    item = items[0]
    return {
        "id": item.get("id", ""),
        "title": str(item.get("snippet", {}).get("title", "")),
        "uploads_playlist": item["contentDetails"]["relatedPlaylists"]["uploads"],
        "video_count": int(item.get("statistics", {}).get("videoCount", 0) or 0),
    }


def fetch_upload_ids(token: TokenSet, playlist_id: str, limit: int = MAX_VIDEOS, *, get=None, sleep=time.sleep) -> list[str]:
    ids: list[str] = []
    page_token: str | None = None
    while len(ids) < limit:
        params: dict[str, str | int] = {"part": "contentDetails", "playlistId": playlist_id, "maxResults": PAGE_SIZE}
        if page_token:
            params["pageToken"] = page_token
        body = _request("playlistItems", params, token, get=get, sleep=sleep)
        ids += [item["contentDetails"]["videoId"] for item in body.get("items", []) if item.get("contentDetails", {}).get("videoId")]
        page_token = body.get("nextPageToken")
        if not page_token:
            break
    return ids[:limit]


def fetch_video_rows(token: TokenSet, ids: list[str], *, get=None, sleep=time.sleep) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for start in range(0, len(ids), PAGE_SIZE):
        chunk = ids[start:start + PAGE_SIZE]
        body = _request("videos", {"part": "snippet,statistics,contentDetails,status", "id": ",".join(chunk), "maxResults": PAGE_SIZE}, token, get=get, sleep=sleep)
        for item in body.get("items", []):
            snippet, stats = item.get("snippet", {}), item.get("statistics", {})
            if item.get("status", {}).get("privacyStatus") not in KEEP_PRIVACY:
                continue  # private and scheduled videos are not part of the public track record
            if snippet.get("liveBroadcastContent") in {"upcoming", "live"}:
                continue
            number = lambda key: float(stats[key]) if key in stats else np.nan  # noqa: E731 - hidden counts are simply missing
            rows.append({
                "video_id": item.get("id", ""), "title": snippet.get("title", ""), "publish_time": snippet.get("publishedAt", ""),
                "views": number("viewCount"), "likes": number("likeCount"), "comments": number("commentCount"),
                "tags": "|".join(snippet.get("tags", []) or []), "description": snippet.get("description", ""),
                "category_name": CATEGORY_NAMES.get(str(snippet.get("categoryId", "")), ""),
                "duration_s": parse_duration(item.get("contentDetails", {}).get("duration")),
            })
    return rows


def fetch_channel_history(
    token: TokenSet,
    limit: int = MAX_VIDEOS,
    *,
    get: Callable[..., requests.Response] | None = None,
    sleep: Callable[[float], None] = time.sleep,
) -> tuple[ChannelHistory, dict[str, object]]:
    """The signed-in creator's channel details and their latest videos as a clean ``ChannelHistory``."""
    channel = fetch_channel(token, get=get, sleep=sleep)
    ids = fetch_upload_ids(token, str(channel["uploads_playlist"]), limit, get=get, sleep=sleep)
    if not ids:
        raise YouTubeAPIError("This channel has no public videos yet, so there is no history to learn from.")
    frame = pd.DataFrame(fetch_video_rows(token, ids, get=get, sleep=sleep))
    if frame.empty:
        raise YouTubeAPIError("None of this channel's videos are public or unlisted, so there is no history to learn from.")
    return clean_videos(frame, source="api"), channel
