"""Turn a creator's own YouTube data into a clean table of earlier videos (upload path; the API path reuses ``clean_videos``).

Accepted uploads: the YouTube Studio "Table data.csv" export, the whole zipped export folder, or any CSV that has a
title, a publish date and a view count.  Everything happens in memory: nothing is written to disk, nothing is logged.

Text from a creator's channel is untrusted: titles are sanitised here before they are shown or given to a language model.
"""

from __future__ import annotations

import io
import re
import unicodedata
import zipfile
from dataclasses import dataclass

import numpy as np
import pandas as pd

MAX_UPLOAD_BYTES = 5_000_000
MAX_UNZIPPED_BYTES = 20_000_000
MAX_ZIP_RATIO = 200          # a CSV that expands more than this is treated as a zip bomb
MAX_ROWS_READ = 20_000
MAX_VIDEOS_KEPT = 2_000      # the newest videos are kept
TITLE_LIMIT = 120
YOUTUBE_FOUNDED = pd.Timestamp("2005-04-01", tz="UTC")  # the first video was uploaded in April 2005
MAX_PLAUSIBLE_VIEWS = 50_000_000_000
SETTLE_DAYS = 14             # views of a video younger than this are still growing, so they do not count as history

CANONICAL = ["video_id", "title", "publish_time", "views", "likes", "comments", "tags", "description", "category_name", "duration_s"]
_SYNONYMS = {
    "video_id": ["content", "videoid", "id", "video"],
    "title": ["videotitle", "title", "contenttitle", "name"],
    "publish_time": ["videopublishtime", "publishtime", "publishedat", "published", "publishdate", "datepublished", "videopublishdate", "date"],
    "views": ["views", "viewcount", "totalviews"],
    "likes": ["likes", "likecount"],
    "comments": ["comments", "commentcount", "commentsadded"],
    "tags": ["tags", "videotags", "keywords"],
    "description": ["description", "videodescription"],
    "category_name": ["category", "videocategory", "categoryname"],
    "duration_s": ["duration", "durationseconds", "durations", "length", "approxduration"],
}
_CONTROL = re.compile(r"[\x00-\x08\x0b-\x1f\x7f-\x9f​-‏‪-‮⁦-⁩﻿]")


class HistoryError(ValueError):
    """A problem with the uploaded data, worded for the person who uploaded it."""


@dataclass(frozen=True)
class ChannelHistory:
    videos: pd.DataFrame      # canonical columns, newest last
    source: str               # "studio_csv" | "generic_csv" | "api" | "sample"
    hour_known: bool          # False when the export has dates only
    notes: tuple[str, ...] = ()


def sanitise_text(value: object, limit: int = TITLE_LIMIT) -> str:
    """Printable, single-line, length-capped text (titles are untrusted input)."""
    text = unicodedata.normalize("NFKC", "" if value is None or (isinstance(value, float) and np.isnan(value)) else str(value))
    text = _CONTROL.sub(" ", text).replace("\r", " ").replace("\n", " ")
    text = re.sub(r"\s+", " ", text).strip()
    return text[:limit]


def _normal(name: object) -> str:
    return re.sub(r"[^a-z0-9]", "", str(name).lower())


def _read_bytes(name: str, content: bytes) -> tuple[bytes, str]:
    if len(content) > MAX_UPLOAD_BYTES:
        raise HistoryError(f"That file is larger than {MAX_UPLOAD_BYTES // 1_000_000} MB. Upload only the Studio 'Table data.csv'.")
    if not content[:4] == b"PK\x03\x04" and not name.lower().endswith(".zip"):
        return content, name
    try:
        archive = zipfile.ZipFile(io.BytesIO(content))
    except zipfile.BadZipFile as error:
        raise HistoryError("That zip file could not be opened.") from error
    members = [m for m in archive.infolist() if not m.is_dir() and m.filename.lower().endswith(".csv")]
    preferred = [m for m in members if m.filename.lower().rsplit("/", 1)[-1].replace("_", " ") == "table data.csv"]
    chosen = (preferred or members or [None])[0]
    if chosen is None:
        raise HistoryError("No CSV file was found inside the zip. YouTube Studio exports contain 'Table data.csv'.")
    if chosen.flag_bits & 0x1:
        raise HistoryError("That zip file is password protected.")
    if chosen.file_size > MAX_UNZIPPED_BYTES or chosen.file_size > max(chosen.compress_size, 1) * MAX_ZIP_RATIO:
        raise HistoryError("That zip file expands to an unreasonable size and was not opened.")
    with archive.open(chosen) as handle:
        data = handle.read(MAX_UNZIPPED_BYTES + 1)
    if len(data) > MAX_UNZIPPED_BYTES:
        raise HistoryError("That zip file expands to an unreasonable size and was not opened.")
    return data, chosen.filename


def _decode(data: bytes) -> str:
    for encoding in ("utf-8-sig", "utf-16", "latin-1"):
        try:
            return data.decode(encoding)
        except UnicodeError:
            continue
    raise HistoryError("The file could not be read as text.")  # latin-1 never fails; kept for clarity


def _read_table(text: str) -> pd.DataFrame:
    for separator in (",", "\t", ";"):
        try:
            frame = pd.read_csv(io.StringIO(text), sep=separator, nrows=MAX_ROWS_READ, dtype=str, keep_default_na=False)
        except (pd.errors.ParserError, pd.errors.EmptyDataError, ValueError):
            continue
        if frame.shape[1] > 1:
            return frame
    raise HistoryError("That does not look like a CSV table (no columns were found).")


def _map_columns(frame: pd.DataFrame) -> dict[str, str]:
    found: dict[str, str] = {}
    normalised = {_normal(column): column for column in frame.columns}
    for canonical, names in _SYNONYMS.items():
        for name in names:
            if name in normalised and normalised[name] not in found.values():
                found[canonical] = normalised[name]
                break
    return found


def _number(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series.astype(str).str.replace(r"[,\s]", "", regex=True), errors="coerce")


def clean_videos(frame: pd.DataFrame, *, source: str) -> ChannelHistory:
    """Validate a table that already uses (some of) the canonical column names; used for uploads and for API results."""
    notes: list[str] = []
    missing = [name for name in ("title", "publish_time", "views") if name not in frame.columns]
    if missing:
        names = {"title": "a video title", "publish_time": "a publish date", "views": "a view count"}
        raise HistoryError("The file has no column for " + " or ".join(names[m] for m in missing) + ". Each video needs a title, a publish date "
                           "and a view count (the YouTube Studio file called 'Table data.csv' has all three).")
    out = pd.DataFrame({name: frame[name] if name in frame.columns else np.nan for name in CANONICAL})
    out = out[out["video_id"].astype(str).str.strip().str.lower() != "total"]
    out["title"] = out["title"].map(sanitise_text)
    out["views"] = _number(out["views"])
    for column in ("likes", "comments", "duration_s"):
        out[column] = _number(out[column])
    raw_dates = out["publish_time"].astype(str)
    out["publish_time"] = pd.to_datetime(raw_dates, errors="coerce", utc=True, format="mixed")
    if out["publish_time"].isna().mean() > 0.2:
        out["publish_time"] = pd.to_datetime(raw_dates, errors="coerce", utc=True, dayfirst=True, format="mixed")
    before = len(out)
    out = out[(out["title"] != "") & out["views"].notna() & (out["views"] >= 0) & out["publish_time"].notna()]
    if before - len(out):
        notes.append(f"{before - len(out)} row(s) without a title, a valid date or a view count were skipped.")
    # impossible history is dropped, not trusted: a video cannot be published before YouTube existed or in the future,
    # and no video has ever had tens of billions of views (a typo or a unit mix-up would otherwise distort the whole forecast)
    latest_possible = pd.Timestamp.now(tz="UTC") + pd.Timedelta(days=1)
    possible = (out["publish_time"] >= YOUTUBE_FOUNDED) & (out["publish_time"] <= latest_possible) & (out["views"] <= MAX_PLAUSIBLE_VIEWS)
    if (~possible).any():
        notes.append(f"{int((~possible).sum())} video(s) with a publish date before YouTube existed, a date in the future or an impossible "
                     "number of views were skipped.")
        out = out[possible]
    key = out["video_id"].astype(str).where(out["video_id"].astype(str).str.len() > 3, out["title"] + out["publish_time"].astype(str))
    deduplicated = out.loc[~key.duplicated(keep="last")]
    if len(deduplicated) < len(out):
        notes.append(f"{len(out) - len(deduplicated)} duplicate row(s) were skipped.")
    out = deduplicated.sort_values("publish_time")
    if len(out) > MAX_VIDEOS_KEPT:
        out = out.tail(MAX_VIDEOS_KEPT)
        notes.append(f"Only the newest {MAX_VIDEOS_KEPT} videos are used.")
    if out.empty:
        raise HistoryError("No usable videos were found (each row needs a title, a publish date and a view count).")
    for column in ("tags", "description", "category_name"):
        out[column] = out[column].map(lambda v: "" if v is None or (isinstance(v, float) and np.isnan(v)) else sanitise_text(v, 2000))
    hour_known = bool((out["publish_time"].dt.hour + out["publish_time"].dt.minute).gt(0).any())
    if not hour_known:
        notes.append("The file has publish dates but no publish times, so the hour of posting cannot be learned from it.")
    return ChannelHistory(out.reset_index(drop=True), source, hour_known, tuple(notes))


def parse_upload(name: str, content: bytes) -> ChannelHistory:
    """Parse an uploaded Studio export (csv or zip) or any CSV with title / publish date / views."""
    data, _ = _read_bytes(name, content)
    frame = _read_table(_decode(data))
    studio = {"Content", "Video title", "Video publish time", "Views"}.issubset(set(frame.columns))
    summed = False
    if studio and "Date" in frame.columns:
        # Studio "Chart data.csv": one row per video per day, so add the daily views up per video
        frame = frame.assign(Views=_number(frame["Views"]))
        columns = {"Video title": "first", "Video publish time": "first", "Views": "sum"}
        frame = frame.groupby("Content", as_index=False, sort=False).agg(columns)
        summed = True
    mapping = _map_columns(frame)
    renamed = frame[list(mapping.values())].rename(columns={v: k for k, v in mapping.items()})
    history = clean_videos(renamed, source="studio_csv" if studio else "generic_csv")
    if summed:
        history = ChannelHistory(history.videos, history.source, history.hour_known,
                                 history.notes + ("Daily chart data was added up per video (views inside the exported date range only).",))
    return history


def history_table(history: ChannelHistory, *, settle_days: int = SETTLE_DAYS) -> pd.DataFrame:
    """The columns ``history_features.history_row`` needs; a video counts once its views have had ``settle_days`` to settle."""
    videos = history.videos
    reactions = (videos["likes"].fillna(0) + videos["comments"].fillna(0)) / videos["views"].replace(0, np.nan)
    has_reactions = videos["likes"].notna() & videos["comments"].notna()  # a hidden like count would understate engagement
    return pd.DataFrame({
        "publish_time": videos["publish_time"],
        "known_at": videos["publish_time"] + pd.Timedelta(days=settle_days),
        "views": videos["views"],
        "engagement": reactions.where(has_reactions),
    })


def summarise(history: ChannelHistory) -> dict[str, object]:
    videos = history.videos
    settled = videos[videos["publish_time"] <= pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=SETTLE_DAYS)]
    top = videos.sort_values("views", ascending=False).head(3)
    return {
        "videos": int(len(videos)),
        "settled_videos": int(len(settled)),
        "first_published": videos["publish_time"].min(),
        "last_published": videos["publish_time"].max(),
        "median_views": float(videos["views"].median()),
        "typical_views": float(np.expm1(np.log1p(settled["views"]).mean())) if len(settled) else float("nan"),
        "top_titles": [(row.title, float(row.views)) for row in top.itertuples()],
    }
