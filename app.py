"""Signal Studio - explainable pre-publication forecasts for YouTube content strategy."""

from __future__ import annotations

import json
import re
import time
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

from src.advanced_model import non_latin_share
from src.channel_history import HistoryError, parse_upload, summarise
from src.history_model import HISTORY_MODELS_PATH, load_history_models
from src.inference import BUNDLE_PATH, global_feature_groups, headline_accuracy, load_bundle, predict_video
from src.insights import (
    DAYS,
    SIMILARITY_PATH,
    Draft,
    build_brief_markdown,
    category_what_if,
    explain_groups,
    forecast_percentile,
    keyword_signals,
    load_similarity_index,
    similar_videos,
    suggest_edits,
    time_grid,
    top_keywords,
)

from src.env_file import load_env_file
from src.personal_forecast import personal_forecast
from src.platform_knowledge import SOURCE_TYPES, date_label, load_timeline
from src.recommendations import generate_recommendation, resolve_runtime
from src.ui_text import escape_markdown
from src.youtube_api import YouTubeAPIError, fetch_channel_history
from src.youtube_oauth import OAuthError, PendingLogins, begin_login, finish_login, oauth_config_from_env, revoke

load_env_file()  # optional ./.env settings (LLM model, Google sign-in); real environment variables always win

st.set_page_config(
    page_title="Signal Studio | YouTube Strategy",
    page_icon="▶",
    layout="wide",
    initial_sidebar_state="auto",  # open on wide screens, closed on phones (an open sidebar covers the whole page there)
)

TEAL, CORAL, SAND, INK = "#00BFA6", "#FF725E", "#F4EEE5", "#071116"

REAL_EXAMPLES_PATH = Path(__file__).resolve().parent / "knowledge" / "real_examples.json"


def load_real_examples() -> dict[str, dict[str, object]]:
    """Real India-trending videos, taken unchanged from the dataset (chosen by scripts/pick_real_examples.py)."""
    try:
        videos = json.loads(REAL_EXAMPLES_PATH.read_text(encoding="utf-8"))["videos"]
    except (OSError, ValueError, KeyError):
        return {}
    return {f"{video['category']}: {str(video['title'])[:46]}": video for video in videos}


EXAMPLES: dict[str, dict[str, object]] = load_real_examples()


# --------------------------------------------------------------------------- #
# Style
# --------------------------------------------------------------------------- #
def apply_style() -> None:
    st.markdown(
        """
        <style>
        .stApp {
            background:
                radial-gradient(circle at 86% 2%, rgba(255,114,94,.16), transparent 25rem),
                radial-gradient(circle at 8% 22%, rgba(0,191,166,.12), transparent 28rem),
                #071116;
        }
        .stApp, .stApp * { font-family: "Palatino Linotype", "Book Antiqua", Georgia, serif; }
        .stApp [data-testid="stIconMaterial"], .stApp [class*="material-symbols"] {
            font-family: "Material Symbols Rounded", "Material Symbols Outlined" !important;
        }
        .main .block-container { max-width: 1240px; padding-top: 2.3rem; padding-bottom: 4rem; }
        [data-testid="stSidebar"] { background: #091A20; border-right: 1px solid rgba(164,208,201,.16); }
        .masthead { border-bottom: 1px solid rgba(234,245,242,.18); padding: .4rem 0 1.7rem; margin-bottom: 1.1rem; }
        .eyebrow, .section-kicker { color: #67D8C7; font-family: "Courier New", monospace !important; font-size: .75rem; letter-spacing: .16em; font-weight: 700; margin-top: 1.1rem; }
        .masthead h1 { font-size: clamp(2.35rem, 5.2vw, 4.8rem); letter-spacing: -.065em; line-height: .94; margin: .45rem 0 .8rem; color: #F4EEE5; }
        .masthead h1 span { color: #FF8C7B; font-style: italic; font-weight: 400; }
        .masthead p { color: #B7CFCB; font-size: 1.05rem; max-width: 52rem; margin: 0; }
        /* Tab bar (Streamlit 1.65 markup: [role=tablist] > [data-testid=stTab]). All nine tabs stay visible: on a narrow
           window they wrap onto a second row instead of being clipped behind a tiny scroll arrow. */
        [role="tablist"] { flex-wrap: wrap; overflow: visible !important; gap: .15rem 1.7rem; padding-bottom: .15rem; }
        [data-testid="stTab"] { height: auto; padding: .8rem .1rem .75rem; white-space: nowrap; }
        [data-testid="stTab"] p { font-size: 1.04rem; font-weight: 700; letter-spacing: .01em; color: #C3D8D3; transition: color .15s; }
        [data-testid="stTab"]:hover p { color: #F4EEE5; }
        [data-testid="stTab"][aria-selected="true"] p { color: #FF9C8C; }
        [data-testid="stTab"] .react-aria-SelectionIndicator { background-color: #FF725E; height: 3px; }
        @media (max-width: 640px) {
            [role="tablist"] { gap: 0 1.2rem; }
            [data-testid="stTab"] { padding: .5rem .1rem .45rem; }
            [data-testid="stTab"] p { font-size: 1rem; }
        }
        [data-testid="stMetric"] { background: rgba(15,35,42,.78); border: 1px solid rgba(164,208,201,.18); border-radius: 2px; padding: 1.1rem 1.2rem; }
        [data-testid="stMetricLabel"] { color: #9FBAB5; }
        [data-testid="stMetricValue"] { color: #F4EEE5; }
        .signal-note { border-left: 3px solid #FF725E; background: rgba(255,114,94,.08); color: #D4E2DF; padding: 1rem 1.1rem; min-height: 6.7rem; }
        .why-note { border-left: 3px solid #00BFA6; background: rgba(0,191,166,.07); color: #D4E2DF; padding: .9rem 1.1rem; margin: .4rem 0 1rem; }
        .tip { border-top: 1px solid rgba(164,208,201,.13); color: #C8D9D5; padding: .65rem .2rem; font-size: .96rem; }
        .muted { color: #A9C2BD; margin-top: 0; }
        .edit-card { border: 1px solid rgba(164,208,201,.16); background: rgba(15,35,42,.55); padding: .8rem 1rem; margin-bottom: .55rem; }
        .edit-card b { color: #F4EEE5; }
        .up { color: #4EE0C6; font-weight: 700; } .down { color: #FF8C7B; font-weight: 700; }
        .stButton > button, [data-testid="stFormSubmitButton"] > button, .stDownloadButton > button {
            border: 0; border-radius: 0; background: #FF725E; color: #111A1D; font-weight: 800;
            letter-spacing: .02em; box-shadow: 5px 5px 0 #00BFA6;
        }
        .stButton > button:hover, [data-testid="stFormSubmitButton"] > button:hover, .stDownloadButton > button:hover { background: #FFA091; color: #071116; transform: translate(1px, 1px); box-shadow: 3px 3px 0 #00BFA6; }
        div[data-baseweb="input"] > div, div[data-baseweb="select"] > div, textarea {
            background: rgba(8,25,30,.9) !important; border-radius: 0 !important; border-color: rgba(164,208,201,.28) !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


# --------------------------------------------------------------------------- #
# Cached model access (the leading underscore tells Streamlit not to hash the bundle).
# Every cache is keyed on the model files' modification time, so retraining takes effect without restarting the app
# (before this, a running app kept the old model in memory while the code expected the new one).
# --------------------------------------------------------------------------- #
def file_stamp(path: Path) -> int:
    try:
        return path.stat().st_mtime_ns
    except OSError:
        return 0


@st.cache_resource(show_spinner="Loading the explainable model…")
def _load_bundle_cached(stamp: int) -> dict[str, object]:
    bundle = load_bundle()
    bundle["file_stamp"] = stamp
    return bundle


def get_bundle() -> dict[str, object]:
    return _load_bundle_cached(file_stamp(BUNDLE_PATH))


@st.cache_resource(show_spinner=False)
def _load_similarity_cached(stamp: int) -> dict[str, object]:
    return load_similarity_index()


def get_similarity_index() -> dict[str, object]:
    return _load_similarity_cached(file_stamp(SIMILARITY_PATH))


@st.cache_resource(show_spinner=False)
def get_pending_logins() -> PendingLogins:
    """Shared by all sessions of this server: the browser leaves for Google and comes back as a brand-new session."""
    return PendingLogins()


@st.cache_resource(show_spinner=False)
def _load_history_cached(stamp: int) -> dict[str, object] | None:
    return load_history_models()


def get_history_models() -> dict[str, object] | None:
    """The models that use a creator's own history; None if the file is missing or out of date (the app then forecasts without history)."""
    return _load_history_cached(file_stamp(HISTORY_MODELS_PATH))


@st.cache_data(show_spinner=False, max_entries=64)
def _cached_explanation(_bundle, draft: Draft, stamp: int):
    return explain_groups(_bundle, draft)


@st.cache_data(show_spinner=False, max_entries=64)
def _cached_time_grid(_bundle, draft: Draft, stamp: int):
    return time_grid(_bundle, draft)


@st.cache_data(show_spinner=False, max_entries=64)
def _cached_suggestions(_bundle, draft: Draft, stamp: int):
    return suggest_edits(_bundle, draft)


@st.cache_data(show_spinner=False, max_entries=64)
def _cached_categories(_bundle, draft: Draft, stamp: int):
    return category_what_if(_bundle, draft)


def cached_explanation(bundle, draft: Draft):
    return _cached_explanation(bundle, draft, bundle.get("file_stamp", 0))


def cached_time_grid(bundle, draft: Draft):
    return _cached_time_grid(bundle, draft, bundle.get("file_stamp", 0))


def cached_suggestions(bundle, draft: Draft):
    return _cached_suggestions(bundle, draft, bundle.get("file_stamp", 0))


def cached_categories(bundle, draft: Draft):
    return _cached_categories(bundle, draft, bundle.get("file_stamp", 0))


# --------------------------------------------------------------------------- #
# Formatting helpers
# --------------------------------------------------------------------------- #
def compact_number(value: float) -> str:
    if value >= 1_000_000:
        return f"{value / 1_000_000:.2f}M"
    if value >= 1_000:
        return f"{value / 1_000:.1f}K"
    return f"{value:,.0f}"


def as_percent(value: float) -> str:
    if value is None or value != value:  # NaN: ratings or comments were switched off, so there is no engagement rate to show
        return "n/a"
    return f"{value * 100:.2f}%"


def signed(value: float, suffix: str = "%") -> str:
    css = "up" if value >= 0 else "down"
    return f"<span class='{css}'>{value:+.1f}{suffix}</span>"


def kicker(text: str) -> None:
    st.markdown(f"<div class='section-kicker'>{text}</div>", unsafe_allow_html=True)


def ordinal(value: float) -> str:
    number = int(round(value))
    suffix = "th" if 10 <= number % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(number % 10, "th")
    return f"{number}{suffix}"


def draft_tips(feature_row: pd.DataFrame, summary: dict[str, dict[str, float]]) -> list[str]:
    """Describe input position in the training distribution without causal claims."""
    row = feature_row.iloc[0]
    tips: list[str] = []
    if row["description_length"] < summary["description_length"]["p50"]:
        tips.append("The description is shorter than the training-set median. Try a clear summary and useful context.")
    if row["tag_count"] < summary["tag_count"]["p50"]:
        tips.append("The tag count is below the training-set median. Add only relevant, specific tags.")
    if row["title_length"] > summary["title_length"]["p95"]:
        tips.append("The title is unusually long for this training sample. Check that the key idea appears early.")
    if row["caps_ratio"] > summary["caps_ratio"]["p95"]:
        tips.append("The capitalization level is unusual in the training sample. Review readability before using all caps.")
    if not tips:
        tips.append("This draft sits within typical ranges for the main editable metadata fields in the training sample.")
    return tips[:3]


# --------------------------------------------------------------------------- #
# Session state: one source of truth for the current draft
# --------------------------------------------------------------------------- #
def init_state(categories: list[str]) -> None:
    example = next(iter(EXAMPLES.values()), {"title": "", "category": categories[0], "day": 0, "hour": 12, "tags": "", "description": ""})
    st.session_state.setdefault("real_example", example if example.get("video_id") else None)
    defaults = {
        "main_title": example["title"],
        "main_category": example["category"] if example["category"] in categories else categories[0],
        "main_day": DAYS[int(example["day"])],
        "main_hour": int(example["hour"]),
        "main_tags": example["tags"],
        "main_description": example["description"],
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)
    st.session_state.setdefault("proposal", read_form("main"))


def read_form(prefix: str) -> dict[str, object]:
    return {
        "title": st.session_state[f"{prefix}_title"],
        "category_name": st.session_state[f"{prefix}_category"],
        "day_of_week": DAYS.index(st.session_state[f"{prefix}_day"]),
        "publish_hour": int(st.session_state[f"{prefix}_hour"]),
        "tags": st.session_state[f"{prefix}_tags"],
        "description": st.session_state[f"{prefix}_description"],
    }


def load_example(categories: list[str]) -> None:
    example = EXAMPLES[st.session_state["example_choice"]]
    st.session_state["real_example"] = example
    st.session_state.update(
        main_title=example["title"],
        main_category=example["category"] if example["category"] in categories else categories[0],
        main_day=DAYS[int(example["day"])],
        main_hour=int(example["hour"]),
        main_tags=example["tags"],
        main_description=example["description"],
    )
    st.session_state["proposal"] = read_form("main")


def apply_draft(draft: Draft) -> None:
    """Callback: copy an edited draft back into the main form and make it current."""
    st.session_state.update(
        main_title=draft.title,
        main_category=draft.category_name,
        main_day=DAYS[draft.day_of_week],
        main_hour=draft.publish_hour,
        main_tags=draft.tags,
        main_description=draft.description,
    )
    st.session_state["proposal"] = read_form("main")


def proposal_inputs(prefix: str, categories: list[str]) -> dict[str, object]:
    """Render the proposal form; widget values live in session state under ``prefix``."""
    st.text_area(
        "Video title", max_chars=120, height=74, key=f"{prefix}_title",
        help="Use a real draft title. The model extracts text-style features locally.",
    )
    left, right = st.columns(2)
    with left:
        st.selectbox("Category", categories, key=f"{prefix}_category")
        st.selectbox("Publish day (IST)", DAYS, key=f"{prefix}_day")
    with right:
        st.slider("Publish hour (IST)", 0, 23, key=f"{prefix}_hour", help="24-hour clock. 18 means 6:00 PM IST.")
        st.text_input("Tags", key=f"{prefix}_tags", help="Separate tags with commas, semicolons, or vertical bars.")
    st.text_area("Description", height=104, max_chars=5000, key=f"{prefix}_description")
    return read_form(prefix)


def to_draft(values: dict[str, object]) -> Draft:
    return Draft(
        title=str(values["title"]), tags=str(values["tags"]), description=str(values["description"]),
        category_name=str(values["category_name"]), day_of_week=int(values["day_of_week"]),
        publish_hour=int(values["publish_hour"]),
    )


# --------------------------------------------------------------------------- #
# Tab: Forecast studio
# --------------------------------------------------------------------------- #
def explanation_chart(table: pd.DataFrame) -> alt.Chart:
    data = table.assign(change=(table["views_multiplier"] - 1) * 100)
    data["label"] = data["change"].map(lambda value: f"{value:+.0f}%")
    base = alt.Chart(data).encode(
        y=alt.Y("group:N", sort=alt.EncodingSortField("change", order="descending"), title=None),
        x=alt.X("change:Q", title="Effect on forecast views vs a typical trending video (%)"),
    )
    bars = base.mark_bar().encode(
        color=alt.condition(alt.datum.change > 0, alt.value(TEAL), alt.value(CORAL)),
        tooltip=[alt.Tooltip("group:N"), alt.Tooltip("views_multiplier:Q", format=".2f", title="Views multiplier"),
                 alt.Tooltip("engagement_effect_pp:Q", format="+.2f", title="Engagement (pp)")],
    )
    text = base.mark_text(align="left", dx=4, color=SAND).encode(text="label:N")
    return (bars + text).properties(height=210).configure_view(strokeWidth=0).configure_axis(
        labelColor="#C8D9D5", titleColor="#9FBAB5", gridColor="#1B3038"
    )


def render_real_outcome(draft: Draft) -> None:
    """When the draft is one of the real example videos, show what really happened to it (it is in the training data: not a fair test)."""
    example = st.session_state.get("real_example")
    if not example or not example.get("video_id") or draft.title.strip() != str(example["title"]).strip():
        return
    st.info(
        f"**This is a real video** ({esc(str(example['channel']))}). It actually got **{compact_number(example['actual_views'])}** views and "
        f"**{as_percent(example['actual_engagement'])}** engagement. It is part of the training data, so this is not a fair test of the model. "
        f"[Open it on YouTube](https://www.youtube.com/watch?v={example['video_id']})"
    )


def render_personal_panel(bundle: dict[str, object], draft: Draft) -> None:
    """Forecast for the creator's own channel (needs the earlier videos from the My channel tab)."""
    kicker("FOR YOUR CHANNEL · EXPERIMENTAL")
    channel = st.session_state.get("channel")
    if channel is None:
        st.markdown(
            "<div class='signal-note'>The numbers above compare your draft with a <b>typical trending video</b>. Add your own earlier "
            "videos in the <b>My channel</b> tab (upload a YouTube Studio export, or connect your channel) to see what the model expects "
            "for <b>your</b> channel.</div>", unsafe_allow_html=True,
        )
        return
    models = get_history_models()
    result = personal_forecast(bundle, models, draft, channel)
    if result.prediction is None:
        if result.reason == "no_models":
            st.info("The history model file is missing or out of date on this server, so only the trending-video forecast is available.")
        else:
            st.info(f"Only {result.usable_videos} of your videos have views that have settled (the model needs at least 3 videos "
                    "that are 14 days old or older). Add more videos, or wait until recent ones settle.")
        return
    prediction = result.prediction
    first, second, third, fourth = st.columns(4)
    with first:
        st.metric("Expected views for your channel", compact_number(prediction.expected_views))
        st.caption(f"80% interval: {compact_number(prediction.views_ci_low)} to {compact_number(prediction.views_ci_high)}")
    with second:
        st.metric("Your usual video", compact_number(prediction.channel_level_views))
        st.caption(f"typical of your last {prediction.n_videos_used} settled videos")
    with third:
        st.metric("This draft vs your usual", f"{(prediction.lift_multiplier - 1) * 100:+.0f}%")
        st.caption("what the model expects the draft to add or lose")
    with fourth:
        st.metric("Expected engagement", as_percent(prediction.engagement_rate))
        st.caption(f"80% interval: {as_percent(prediction.engagement_ci_low)} to {as_percent(prediction.engagement_ci_high)}"
                   + (" · from the trending-video model (your file has no likes or comments)"
                      if prediction.engagement_source == "trending" else ""))
    tested = models["metrics"]
    unseen, cover = tested["unseen_channels"], tested["interval_coverage_80"]
    st.caption(
        f"Experimental. Built from {prediction.n_videos_used} of your earlier videos (views settled for 14+ days). On channels the model "
        f"had never seen, history raised the views score (R²) from {unseen['log_views_r2_cold_start_model']:.2f} to "
        f"{unseen['log_views_r2_history_model']:.2f}, and the 80% interval held {cover['views_unseen_channels']:.0%} of the time. "
        "The model was trained on videos that trended, so for small channels treat the numbers as a guide, not a promise."
    )


def render_forecast(bundle: dict[str, object], draft: Draft) -> None:
    try:
        result = predict_video(
            bundle, title=draft.title, tags=draft.tags, description=draft.description,
            category_name=draft.category_name, day_of_week=draft.day_of_week, publish_hour=draft.publish_hour,
        )
    except ValueError as error:
        st.info(str(error))
        return

    percentiles = forecast_percentile(bundle, draft.category_name, result.views_log, result.engagement_rate)

    kicker("MODEL OUTPUT")
    first, second, third = st.columns([1.1, 1.1, 1.25])
    with first:
        st.metric("Expected views", compact_number(result.expected_views))
        st.caption(
            f"80% interval: {compact_number(result.views_ci_low)} to {compact_number(result.views_ci_high)} "
            f"(checked on channels the model had not seen; width set from {result.interval_basis})"
        )
    with second:
        st.metric("Expected engagement", as_percent(result.engagement_rate))
        st.caption(f"80% interval: {as_percent(result.engagement_ci_low)} to {as_percent(result.engagement_ci_high)}")
    with third:
        category_line = (
            f" Within {draft.category_name} (n={percentiles['category_n']}) it is the "
            f"<b>{ordinal(percentiles['views_category'])}</b> percentile."
            if percentiles["views_category"] is not None else ""
        )
        st.markdown(
            f"<div class='signal-note'><b>Where it sits</b><br>Views forecast: <b>{ordinal(percentiles['views_overall'])}</b> "
            f"percentile of all trending videos.{category_line} Engagement: "
            f"<b>{ordinal(percentiles['engagement_overall'])}</b> percentile.</div>",
            unsafe_allow_html=True,
        )

    st.caption("These numbers compare your draft with other videos that reached India's Trending list, so they are higher than what an "
               "ordinary upload gets. Use them to compare drafts with each other, not as a promise of views.")
    if len(draft.title.split()) < 3:
        st.warning("The title has fewer than three words, so the model has very little to read. Short titles give unreliable forecasts.")
    if result.interval_basis == "all trending videos":
        st.caption(f"{draft.category_name} has too few trending videos in the data to set its own interval width, so the overall width is used.")
    script_accuracy = (bundle["metrics"]["views_log"].get("unseen_channel_by_title_script") or {}).get("non_latin_titles")
    if script_accuracy and non_latin_share(draft.title) >= 0.5:
        st.warning(f"This title is mostly in a script other than the Latin alphabet (Hindi, Tamil, Telugu and so on). On channels the model "
                   f"had not seen, its views score for such titles was only R² {script_accuracy['r2']:.2f} (against "
                   f"{headline_accuracy(bundle)['views_r2']:.2f} overall), so the forecast is rough. Category and timing are the parts to trust.")

    render_real_outcome(draft)
    render_personal_panel(bundle, draft)

    if result.out_of_range_features:
        names = ", ".join(name.replace("_", " ") for name in result.out_of_range_features[:4])
        st.warning(f"Calibration note: this draft is outside the central 90% of the training sample for {names}. "
                   "Treat the estimate as less stable.")

    explanation = cached_explanation(bundle, draft)
    kicker("WHY THIS FORECAST · EXACT SHAPLEY VALUES")
    st.markdown(
        f"<div class='why-note'>A typical trending video would be forecast at <b>{compact_number(explanation.baseline_views)}</b> views. "
        f"Your draft is forecast at <b>{compact_number(explanation.forecast_views)}</b>. The bars show how much each group of "
        "choices pushes that number up or down; together they account for the whole difference.</div>",
        unsafe_allow_html=True,
    )
    st.altair_chart(explanation_chart(explanation.table), width="stretch")
    st.caption(
        "Category is often the longest bar because audience size differs a lot between categories (it says nothing about quality), "
        "and it is fixed once you know what you are making. The title, tags, description and timing bars are the ones you can still change."
    )
    with st.expander("How is this calculated? (plain-language version)"):
        st.markdown(
            "1. Start from a **typical trending video** (an average over 80 real videos).\n"
            "2. Swap in your draft's **title packaging** and see how the forecast changes; then do the same for tags, "
            "description, publish time and category.\n"
            "3. The order matters (a long title may only help once the category is right), so we try **every possible order** "
            "(5 groups → 32 combinations) and average each group's effect. That average is the **Shapley value**.\n"
            "4. Because we use all orders, the effects add up exactly to *forecast − typical*, and a group the model ignores gets zero.\n\n"
            "Read the bars as *associations the model learned*, not guaranteed causes."
        )

    kicker("KEYWORD RADAR")
    keywords = keyword_signals(bundle, draft.title)
    if keywords.empty:
        st.caption("None of the title words is common enough for a reliable statistic (a word needs 25+ videos from 25+ different channels).")
    else:
        shown = keywords.assign(
            **{"Videos": keywords["n"], "Median views": keywords["median_views"].map(compact_number),
               "Views vs typical": keywords["views_lift"].map(lambda value: f"x{value:.2f}"),
               "Engagement vs typical": keywords["engagement_lift"].map(lambda value: f"x{value:.2f}")}
        ).rename(columns={"word": "Word"})[["Word", "Videos", "Median views", "Views vs typical", "Engagement vs typical"]]
        st.dataframe(shown, hide_index=True, width="stretch")
        st.caption("Median views of past trending videos whose title contains the word. Popular words often mark big channels, so treat this as context, not a recipe.")

    kicker("EDITABLE SIGNAL CHECK")
    for tip in draft_tips(result.feature_row, bundle["numeric_summary"]):
        st.markdown(f"<div class='tip'>› {tip}</div>", unsafe_allow_html=True)

    with st.expander("Show every feature calculated from this draft"):
        st.dataframe(result.feature_row.T.rename(columns={0: "value"}).astype(str), width="stretch")

    grid = cached_time_grid(bundle, draft)
    brief = build_brief_markdown(draft, result, explanation, grid, cached_suggestions(bundle, draft))
    st.download_button("Download strategy brief (.md)", data=brief, file_name="strategy_brief.md", mime="text/markdown")


# --------------------------------------------------------------------------- #
# Tab: Best time
# --------------------------------------------------------------------------- #
def render_best_time(bundle: dict[str, object], draft: Draft) -> None:
    kicker("WHEN TO PUBLISH · 168 WEEKLY SLOTS (IST)")
    st.markdown(
        "<p class='muted'>The same draft is forecast in every day-and-hour slot of the week. Forecasts are averaged with the "
        "neighbouring hours so one noisy slot cannot masquerade as the best time.</p>", unsafe_allow_html=True,
    )
    if not draft.title.strip():
        st.info("Enter a title in the Forecast studio first.")
        return
    grid = cached_time_grid(bundle, draft)
    table = grid.table.copy()
    table["slot"] = table["day_name"] + " " + table["hour"].map(lambda hour: f"{hour:02d}:00")
    table["views_label"] = table["views"].map(compact_number)
    table["chosen"] = (table["day"] == draft.day_of_week) & (table["hour"] == draft.publish_hour)

    heat = alt.Chart(table).mark_rect().encode(
        x=alt.X("hour:O", title="Hour of day (IST)"),
        y=alt.Y("day_name:N", sort=DAYS, title=None),
        color=alt.Color("views:Q", scale=alt.Scale(scheme="tealblues"), legend=alt.Legend(title="Forecast views")),
        tooltip=["slot:N", alt.Tooltip("views_label:N", title="Views"),
                 alt.Tooltip("engagement:Q", format=".2%", title="Engagement")],
    )
    outline = alt.Chart(table[table["chosen"]]).mark_rect(fill=None, stroke=CORAL, strokeWidth=3).encode(
        x="hour:O", y=alt.Y("day_name:N", sort=DAYS)
    )
    st.altair_chart((heat + outline).properties(height=290).configure_view(strokeWidth=0).configure_axis(
        labelColor="#C8D9D5", titleColor="#9FBAB5"), width="stretch")
    st.caption("Orange outline = your planned slot.")

    best = grid.best_slots
    columns = st.columns(len(best) + 1)
    for position, (_, row) in enumerate(best.iterrows()):
        with columns[position]:
            st.metric(f"Best slot #{position + 1}", f"{row['day_name'][:3]} {int(row['hour']):02d}:00",
                      f"{compact_number(row['views'])} views", delta_color="off")
            st.button("Use this slot", key=f"slot_{position}", on_click=apply_draft,
                      args=(draft.with_changes(day_of_week=int(row["day"]), publish_hour=int(row["hour"])),))
    with columns[-1]:
        gap = (grid.chosen_views / max(float(best.iloc[0]["views"]), 1.0) - 1) * 100
        st.metric("Your slot vs best", compact_number(grid.chosen_views), f"{gap:+.1f}%", delta_color="off")
    st.info(
        f"Timing swing: the best slot is forecast **{grid.swing_pct:+.0f}%** above the median slot. "
        "In this dataset, what you publish matters more than when; use timing as a tiebreaker."
    )


# --------------------------------------------------------------------------- #
# Tab: Title lab
# --------------------------------------------------------------------------- #
def render_title_lab(bundle: dict[str, object], draft: Draft) -> None:
    kicker("TITLE & METADATA LAB")
    st.markdown(
        "<p class='muted'>Each idea below is one small edit to your draft. The trained model re-scores the edited draft and we "
        "rank the changes. Click <b>Apply</b> to load an edit into the Forecast studio.</p>", unsafe_allow_html=True,
    )
    if not draft.title.strip():
        st.info("Enter a title in the Forecast studio first.")
        return
    suggestions = cached_suggestions(bundle, draft)
    helpful = [item for item in suggestions if item.views_change_pct > 0.5]
    harmful = [item for item in suggestions if item.views_change_pct <= 0.5]

    if not helpful:
        st.success("None of the tested edits is forecast to raise views; the draft is already in a good place by this model.")
    for item in helpful[:6]:
        card, action = st.columns([5, 1])
        with card:
            st.markdown(
                f"<div class='edit-card'><b>{item.label}</b><br>{item.why}<br>"
                f"Views {signed(item.views_change_pct)} → {compact_number(item.views)} · "
                f"Engagement {signed(item.engagement_change_pp, ' pp')}</div>",
                unsafe_allow_html=True,
            )
        with action:
            st.button("Apply", key=f"apply_{item.key}", on_click=apply_draft, args=(item.draft,))
    if harmful:
        with st.expander(f"Edits associated with lower or flat views ({len(harmful)})"):
            for item in harmful:
                st.markdown(f"- **{item.label}**: views {signed(item.views_change_pct)}, "
                            f"engagement {signed(item.engagement_change_pp, ' pp')}", unsafe_allow_html=True)
    st.caption("Associations from India-trending videos, not causal promises: apply only edits that keep the title honest and useful.")

    kicker("WORDS THAT TEND TO TRAVEL WITH HIGH / LOW VIEWS")
    best, worst = top_keywords(bundle)
    left, right = st.columns(2)
    for column, frame, heading in ((left, best, "Higher-view words"), (right, worst, "Lower-view words")):
        with column:
            st.markdown(f"**{heading}**")
            view = frame.assign(Word=frame["word"], Videos=frame["n"].astype(int),
                                **{"Median views": frame["median_views"].map(compact_number),
                                   "Vs typical": frame["views_lift"].map(lambda value: f"x{value:.2f}")})
            st.dataframe(view[["Word", "Videos", "Median views", "Vs typical"]], hide_index=True, width="stretch")


# --------------------------------------------------------------------------- #
# Tab: Similar videos
# --------------------------------------------------------------------------- #
def render_similar(bundle: dict[str, object], draft: Draft) -> None:
    kicker("SECOND OPINION · NEAREST TRENDING VIDEOS")
    st.markdown(
        "<p class='muted'>A completely different method: find trending videos whose title and tags read like yours (TF-IDF cosine "
        "similarity) and look at what they got. If the two methods agree, confidence goes up.</p>", unsafe_allow_html=True,
    )
    if not draft.title.strip():
        st.info("Enter a title in the Forecast studio first.")
        return
    try:
        index = get_similarity_index()
    except FileNotFoundError as error:
        st.error(str(error))
        return
    result = similar_videos(index, draft.title, draft.tags)
    if result.table.empty:
        st.info("No trending video is similar enough to this draft's wording. Try adding descriptive keywords to the title or tags.")
        return
    forecast = predict_video(bundle, title=draft.title, tags=draft.tags, description=draft.description,
                             category_name=draft.category_name, day_of_week=draft.day_of_week,
                             publish_hour=draft.publish_hour)
    left, middle, right = st.columns(3)
    left.metric("Model forecast", compact_number(forecast.expected_views))
    middle.metric(f"Look-alike median ({result.analogs_used} videos)", compact_number(result.analog_median_views))
    ratio = max(forecast.expected_views, result.analog_median_views) / max(min(forecast.expected_views, result.analog_median_views), 1)
    right.metric("Agreement", "Consistent" if ratio <= 2 else "Differ", f"x{ratio:.1f} apart", delta_color="off")
    st.caption("Consistent = within a factor of two. Look-alikes are chosen by wording only, so they can include much larger channels.")

    shown = result.table.assign(
        Title=result.table["title"], Category=result.table["category"],
        Views=result.table["views"].map(compact_number), Engagement=result.table["engagement"].map(as_percent),
        Similarity=result.table["similarity"].map(lambda value: f"{value:.0%}"), Link=result.table["url"],
    )[["Title", "Category", "Views", "Engagement", "Similarity", "Link"]]
    st.dataframe(shown, hide_index=True, width="stretch",
                 column_config={"Link": st.column_config.LinkColumn("Watch", display_text="open")})


# --------------------------------------------------------------------------- #
# Tab: Scenario lab
# --------------------------------------------------------------------------- #
def render_comparison(base: Draft, alternative: Draft, bundle: dict[str, object]) -> None:
    results = [
        predict_video(bundle, title=d.title, tags=d.tags, description=d.description, category_name=d.category_name,
                      day_of_week=d.day_of_week, publish_hour=d.publish_hour)
        for d in (base, alternative)
    ]
    a, b = results
    st.dataframe(
        pd.DataFrame({
            "Metric": ["Expected views", "80% interval", "Expected engagement"],
            "Draft A": [compact_number(a.expected_views), f"{compact_number(a.views_ci_low)} - {compact_number(a.views_ci_high)}", as_percent(a.engagement_rate)],
            "Draft B": [compact_number(b.expected_views), f"{compact_number(b.views_ci_low)} - {compact_number(b.views_ci_high)}", as_percent(b.engagement_rate)],
            "Change (B vs A)": [f"{((b.expected_views / max(a.expected_views, 1)) - 1) * 100:+.1f}%", "",
                                f"{(b.engagement_rate - a.engagement_rate) * 100:+.2f} pp"],
        }),
        hide_index=True, width="stretch",
    )
    overlap = min(a.views_ci_high, b.views_ci_high) - max(a.views_ci_low, b.views_ci_low)
    if overlap > 0:
        st.info("The two 80% intervals overlap heavily, so this change is **within the model's uncertainty**; do not over-read the difference.")
    else:
        st.success("The 80% intervals do not overlap: the model sees a clear difference between the drafts.")
    st.caption("A scenario comparison of patterns in the data, not proof that changing one field causes the outcome.")


def render_scenario(bundle: dict[str, object], categories: list[str], draft: Draft) -> None:
    kicker("A/B WHAT-IF TEST")
    st.markdown("<p class='muted'>Draft A is your current proposal. Change Draft B and compare the model outputs.</p>", unsafe_allow_html=True)
    left, right = st.columns(2, gap="large")
    with left:
        st.markdown("#### Draft A · current proposal")
        st.code(draft.title[:80] + ("…" if len(draft.title) > 80 else ""), language=None)
        st.caption(f"{draft.category_name} · {DAYS[draft.day_of_week]} · {draft.publish_hour:02d}:00 IST")
    with right:
        st.markdown("#### Draft B · alternate proposal")
        from_a = {"compare_title": draft.title, "compare_category": draft.category_name,
                  "compare_day": DAYS[draft.day_of_week], "compare_hour": draft.publish_hour,
                  "compare_tags": draft.tags, "compare_description": draft.description}
        previous_a = st.session_state.get("compare_origin")
        if previous_a is not None and previous_a != from_a and all(st.session_state.get(k) == v for k, v in previous_a.items()):
            st.session_state.update(from_a)  # Draft B was never edited, so it follows Draft A instead of going stale
        st.session_state["compare_origin"] = from_a
        for key, value in from_a.items():
            st.session_state.setdefault(key, value)
        alternative = to_draft(proposal_inputs("compare", categories))
        st.button("Reset Draft B to Draft A", on_click=lambda: st.session_state.update(
            compare_title=draft.title, compare_category=draft.category_name, compare_day=DAYS[draft.day_of_week],
            compare_hour=draft.publish_hour, compare_tags=draft.tags, compare_description=draft.description))
    if st.button("Compare Draft A and Draft B", width="stretch"):
        try:
            render_comparison(draft, alternative, bundle)
        except ValueError as error:
            st.info(str(error))

    kicker("CATEGORY WHAT-IF")
    st.markdown("<p class='muted'>How would the model read the <i>same wording</i> in another category? Only categories with at least "
                "30 trending videos are shown. This is for understanding the model, not for mislabelling a video.</p>", unsafe_allow_html=True)
    if not draft.title.strip():
        return
    table = cached_categories(bundle, draft)
    chart = alt.Chart(table).mark_bar().encode(
        x=alt.X("views:Q", title="Forecast views"),
        y=alt.Y("category:N", sort="-x", title=None),
        color=alt.condition(alt.datum.is_selected, alt.value(CORAL), alt.value(TEAL)),
        tooltip=["category:N", alt.Tooltip("views:Q", format=",.0f"), alt.Tooltip("engagement:Q", format=".2%"),
                 alt.Tooltip("videos_in_data:Q", title="Videos in data")],
    ).properties(height=26 * len(table) + 20).configure_view(strokeWidth=0).configure_axis(labelColor="#C8D9D5", titleColor="#9FBAB5", gridColor="#1B3038")
    st.altair_chart(chart, width="stretch")
    st.caption("Orange = your category.")


# --------------------------------------------------------------------------- #
# Tab: Model brief
# --------------------------------------------------------------------------- #
def render_method(bundle: dict[str, object]) -> None:
    metrics, calibration = bundle["metrics"], bundle["calibration"]
    check = calibration["coverage_check"]
    left, right = st.columns(2)
    with left:
        st.markdown("#### Validation at a glance")
        views_metrics, engagement_metrics = metrics["views_log"], metrics["engagement_rate"]
        rows, notes = [], []
        if "unseen_channel_cv" in views_metrics:
            rows.append(("Unseen channels (honest)", views_metrics["unseen_channel_cv"]["r2_mean"],
                         engagement_metrics["unseen_channel_cv"]["r2_mean"]))
            notes.append("Unseen channels: the model is tested on channels it never saw while learning. A new creator is such a channel, so that row is the one to trust.")
        rows.append(("Later uploads", views_metrics["chronological_holdout"]["r2"], engagement_metrics["chronological_holdout"]["r2"]))
        rows.append(("Shuffled 5-fold", views_metrics["five_fold_cv"]["r2_mean"], engagement_metrics["five_fold_cv"]["r2_mean"]))
        table = pd.DataFrame(rows, columns=["Test", "Views R²", "Engagement R²"])
        st.dataframe(table.style.format({"Views R²": "{:.2f}", "Engagement R²": "{:.2f}"}), hide_index=True, width="stretch")
        st.caption(" ".join(notes + ["Later uploads: trained on earlier videos, tested on later ones. Shuffled 5-fold reads highest because it lets the model see the same channel while learning and while being tested."]))
        by_script = views_metrics.get("unseen_channel_by_title_script") or {}
        if "latin_titles" in by_script and "non_latin_titles" in by_script:
            st.caption(f"On unseen channels, views R² is {by_script['latin_titles']['r2']:.2f} for titles in the Latin alphabet and "
                       f"{by_script['non_latin_titles']['r2']:.2f} for titles in Hindi, Tamil, Telugu and other scripts "
                       f"({by_script['non_latin_titles']['n']:,} videos).")
    with right:
        st.markdown("#### What each strategy group contributes (global importance)")
        groups = global_feature_groups(bundle)
        st.bar_chart(groups.pivot(index="group", columns="target", values="importance").fillna(0))

    st.markdown("#### Honest uncertainty: do the 80% intervals really hold?")
    coverage = pd.DataFrame({
        "Check": ["Out-of-fold, channels never seen in training", "Later-in-time holdout (some channels already seen)"],
        "Views intervals": [f"{check['views_out_of_fold']:.1%}", f"{check['views_chronological_holdout']:.1%}"],
        "Engagement intervals": [f"{check['engagement_out_of_fold']:.1%}", f"{check['engagement_chronological_holdout']:.1%}"],
        "Target": ["80%", "80%"],
    })
    st.dataframe(coverage, hide_index=True, width="stretch")
    st.caption(
        f"Split-conformal calibration: a views forecast is typically within x{calibration['views_multiplier_low']:.2f} to "
        f"x{calibration['views_multiplier_high']:.2f} of the truth. Intervals that are wide are the honest answer when the signal is weak."
    )

    with st.expander("How the whole system works (for the viva)"):
        st.markdown(
            "**Data** → India trending snapshots, de-duplicated to one row per video (16,307).  \n"
            "**Features** → only things known before upload: title style, tags, description, category, IST publish time.  \n"
            "**Models** → two Random Forests (log-views and engagement rate).  \n"
            "**Evaluation** → three tests: channels the model never saw (the honest one), a later-in-time holdout, and shuffled 5-fold CV.  \n"
            "**Explanation** → exact Shapley values over five feature groups.  \n"
            "**Uncertainty** → split-conformal intervals, with coverage measured on later uploads.  \n"
            "**Second opinion** → TF-IDF nearest-neighbour look-alike videos.  \n"
            "**Decision tools** → 168-slot timing map, edit ranking, category what-if."
        )
    st.markdown("#### Honest limits")
    st.warning(
        "The dataset contains only videos that already trended in India (2017-2018). The app estimates relative performance in that "
        "population. It cannot predict whether an arbitrary upload will go viral, and it does not observe thumbnails, channel "
        "reputation, retention or YouTube's internal ranking signals. Every effect shown is an association, not a cause."
    )


# --------------------------------------------------------------------------- #
# Tab: AI coach (on-device language model with an evidence-checked, rule-based fallback)
# --------------------------------------------------------------------------- #
esc = escape_markdown


def get_runtime():
    """Probe the local model server at most every 45 s per session."""
    cached = st.session_state.get("runtime_cache")
    if cached is None or time.time() - cached[0] > 45:
        cached = (time.time(), resolve_runtime())
        st.session_state["runtime_cache"] = cached
    return cached[1]


def _cites(evidence: list[str]) -> str:
    return " · evidence " + ", ".join(evidence) if evidence else ""


def render_coach(bundle: dict[str, object], draft: Draft) -> None:
    kicker("AI COACH · ON-DEVICE")
    st.markdown(
        "<p class='muted'>Turns the model's numbers and dataset evidence into a few prioritised, explained suggestions. "
        "The language model only writes advice; every number you see comes from the trained ML model.</p>",
        unsafe_allow_html=True,
    )
    runtime = get_runtime()
    st.caption(f"This device: {runtime.profile.describe()}")
    if runtime.ready:
        st.success(f"Local model **{runtime.choice.name}** via {runtime.backend} ({runtime.choice.reason}). "
                   "Your draft is processed on this computer and is not sent to any online service.")
    else:
        hint = f" To enable the AI coach on this device: install Ollama and run `{runtime.choice.pull_hint}`." if runtime.choice.pull_hint else ""
        st.info(f"Rule-based mode: {runtime.choice.reason}.{hint} Nothing leaves the app in this mode.")
    if not draft.title.strip():
        st.info("Enter a title in the Forecast studio first.")
        return
    if st.session_state.get("channel") is not None:
        st.caption("Your channel data is included: the advice can use your usual level and patterns in your own videos.")
    else:
        st.caption("Tip: add your own videos in the My channel tab to get advice based on your own history.")

    if st.button("Generate recommendations", key="coach_generate", width="stretch"):
        try:
            index = get_similarity_index()
        except FileNotFoundError:
            index = None
        channel = st.session_state.get("channel")
        personal = personal_forecast(bundle, get_history_models(), draft, channel) if channel is not None else None
        with st.spinner("Collecting evidence and writing recommendations…"):
            st.session_state["coach_result"] = (draft, generate_recommendation(
                bundle, draft, runtime=runtime, similarity_index=index, personal=personal, channel=channel))
    stored = st.session_state.get("coach_result")
    if not stored:
        return
    shown_draft, result = stored
    if shown_draft != draft:
        st.caption("Your draft changed since these were generated. Press the button to refresh.")
    recommendation = result.recommendation

    if result.source == "llm":
        lite = " (lite fallback model)" if result.tier == "lite" else ""
        st.markdown(f"**AI coach** · local model `{esc(result.model)}`{lite} · {result.seconds:.0f}s · every claim checked against the evidence")
    else:
        st.markdown("**Rule-based recommendations** · computed directly from the model's scored edits")
    if result.notice:
        st.warning(result.notice)
    first, second = st.columns(2)
    first.metric("Expected views (ML model)", compact_number(result.forecast.expected_views))
    second.metric("Expected engagement (ML model)", as_percent(result.forecast.engagement_rate))
    st.caption("These numbers come from the trained Random Forest and are never changed by the language model.")

    st.markdown(esc(recommendation["summary"]))
    kicker("TOP PRIORITIES")
    for number, item in enumerate(recommendation["priorities"], start=1):
        st.markdown(f"**{number}. {esc(item['action'])}** · confidence {item['confidence']}{_cites(item['evidence'])}")
        st.caption(item["why"])
    if recommendation["weaknesses"]:
        kicker("POSSIBLE WEAKNESSES")
        for item in recommendation["weaknesses"]:
            st.markdown(f"**{esc(item['field']).capitalize()}**: {esc(item['issue'])}{_cites(item['evidence'])}")
            st.caption(item["why"])

    kicker("TITLE AND TAG IDEAS · RE-SCORED BY THE ML MODEL")
    if not result.rescored:
        st.caption("No title or tag change passed the evidence checks.")
    for position, row in enumerate(result.rescored):
        text, action = st.columns([5, 1])
        with text:
            st.markdown(f"**{esc(row['label'])}**")
            st.caption(f"Model-scored: views {row['views_change_pct']:+.1f}% → {compact_number(row['expected_views'])}, "
                       f"engagement {row['engagement_change_pp']:+.2f} pp (an association, not a guarantee)")
        with action:
            st.button("Apply", key=f"coach_apply_{position}", on_click=apply_draft, args=(row["draft"],))
    tags = recommendation["tag_suggestions"]
    if tags["add"]:
        st.markdown("**Suggested tags:** " + ", ".join(f"`{esc(tag)}`" for tag in tags["add"]))
        st.caption(tags["rationale"])
    if recommendation["description_advice"]:
        kicker("DESCRIPTION")
        for item in recommendation["description_advice"]:
            st.markdown(f"**{esc(item['change'])}**{_cites(item['evidence'])}")
            st.caption(item["why"])
    advice = recommendation["timing_category_advice"]
    if advice["advice"]:
        kicker("TIMING")
        st.markdown(esc(advice["advice"]) + _cites(advice["evidence"]))
    kicker("LIMITS")
    for limitation in recommendation["limitations"]:
        st.caption(limitation)
    with st.expander("Evidence the recommendations may cite"):
        for fact in result.packet.facts:
            st.markdown(f"**{fact.id}** · {fact.kind}: {esc(fact.text)}")


# --------------------------------------------------------------------------- #
# Tab: YouTube timeline (sourced knowledge)
# --------------------------------------------------------------------------- #
def render_platform_timeline() -> None:
    kicker("WHAT HAS CHANGED ON YOUTUBE · EVERY ENTRY SOURCED")
    st.markdown(
        "<p class='muted'>Documented changes and statements about how YouTube recommends and counts videos, collected from YouTube's own pages "
        "and research papers. This is what has been <b>published</b>: YouTube does not publish its ranking formula, so none of this is "
        "'the algorithm'. Entries from news reports are marked as lower confidence.</p>", unsafe_allow_html=True,
    )
    try:
        entries = load_timeline()
    except (OSError, ValueError):
        st.info("The knowledge file is not available on this server.")
        return
    first, second = st.columns([2, 1])
    with first:
        topics = st.multiselect("Topic", sorted({entry.topic for entry in entries}), key="kb_topics", placeholder="All topics")
    with second:
        hide_press = st.checkbox("Hide press reports", key="kb_hide_press")
    shown = [e for e in entries if (not topics or e.topic in topics) and not (hide_press and e.source_type == "press_report")]
    st.caption(f"{len(shown)} of {len(entries)} entries · last checked against the sources on {max(e.verified['on'] for e in entries)}")
    for entry in shown:
        st.markdown(
            f"**{date_label(entry)} · {esc(entry.title)}**  \n{esc(entry.what_changed)}  \n"
            f"*For creators:* {esc(entry.creator_takeaway)}  \n"
            f"Source: [{esc(entry.source['publisher'])}: {esc(entry.source['title'])}]({entry.source['url']}) · "
            f"{SOURCE_TYPES[entry.source_type]} · {esc(entry.verified['how'])}"
        )
        st.divider()


# --------------------------------------------------------------------------- #
# Tab: My channel
# --------------------------------------------------------------------------- #
def clear_channel() -> None:
    """Callback: forget the creator's data (it only ever lived in this session)."""
    for key in ("channel", "channel_file_id"):
        st.session_state.pop(key, None)


def start_google_login() -> None:
    """Callback for the 'Connect with Google' button: prepare the Google address to continue to."""
    config = oauth_config_from_env()
    if config is not None:
        st.session_state["google_auth_url"] = begin_login(config, get_pending_logins())


def handle_google_callback() -> None:
    """Google sends the creator back here with ?code=...&state=...: read their videos once, then cancel the access."""
    params = st.query_params
    if "state" not in params or ("code" not in params and "error" not in params):
        return
    values = {key: str(params[key]) for key in ("code", "state", "error") if key in params}
    st.query_params.clear()  # the code is single-use; do not leave it in the address bar
    config = oauth_config_from_env()
    if config is None:
        st.session_state["google_message"] = ("error", "Google sign-in is not set up on this server.")
        return
    try:
        token = finish_login(config, get_pending_logins(), values)
        history, channel = fetch_channel_history(token)
    except (OAuthError, YouTubeAPIError) as error:
        st.session_state["google_message"] = ("error", str(error))
        return
    revoke(token)  # the videos are copied into this session; the access itself is not needed any more
    st.session_state["channel"] = history
    st.session_state.pop("channel_file_id", None)
    st.session_state["google_message"] = ("success", f"Connected to {escape_markdown(str(channel['title']))}: "
                                                    f"{len(history.videos)} videos were read, and the app's access was cancelled again.")


def _render_google_connect() -> None:
    kicker("CONNECT DIRECTLY TO YOUTUBE")
    message = st.session_state.pop("google_message", None)
    if message:
        (st.success if message[0] == "success" else st.error)(message[1])
    if oauth_config_from_env() is None:
        st.caption("Direct connection is not set up on this server. It needs a Google Cloud client (free, about 10 minutes); "
                   "see docs/CONNECT_YOUTUBE.md. Uploading your Studio export works without it.")
        return
    st.markdown("<p class='muted'>Sign in with Google and the app reads the titles, dates and view counts of your own videos once, then "
                "cancels its access straight away. It can only <b>read</b>; it cannot change anything on your channel.</p>", unsafe_allow_html=True)
    first, second = st.columns([1, 2])
    with first:
        st.button("Connect with Google", on_click=start_google_login, key="google_connect", width="stretch")
    with second:
        if st.session_state.get("google_auth_url"):
            st.link_button("Continue to Google →", st.session_state["google_auth_url"])
    st.caption("Google may show an 'unverified app' notice while this app is in testing; only accounts listed as test users can continue.")


def render_my_channel() -> None:
    kicker("YOUR OWN YOUTUBE DATA")
    st.markdown(
        "<p class='muted'>The Forecast studio compares a draft with a typical <b>trending</b> video. Add your own earlier videos and "
        "it also shows what the model expects for <b>your</b> channel: your usual level, plus how much this draft should add or lose.</p>",
        unsafe_allow_html=True,
    )
    left = st.container()
    with left:
        uploaded = st.file_uploader(
            "Upload a YouTube Studio export (the CSV, or the zipped export folder)", type=["csv", "zip"], key="channel_upload",
            help="Needs a video title, a publish date and a view count for each video. Maximum 5 MB.",
        )
        if uploaded is not None and st.session_state.get("channel_file_id") != uploaded.file_id:
            parsed = False
            try:
                st.session_state["channel"] = parse_upload(uploaded.name, uploaded.getvalue())
                st.session_state["channel_file_id"] = uploaded.file_id
                parsed = True
            except HistoryError as error:
                st.error(str(error))
            if parsed:
                st.rerun()  # the Forecast tab was already drawn in this run; redraw it with the new data

    _render_google_connect()

    channel = st.session_state.get("channel")
    if channel is None:
        with st.expander("How do I get my data from YouTube Studio?", expanded=True):
            st.markdown(
                "1. Open **YouTube Studio**, then **Analytics**, then **Advanced mode**.\n"
                "2. Choose the **Lifetime** date range and the **Content** tab.\n"
                "3. Use **Export current view** and pick **CSV**. The file called **Table data.csv** is the one this app reads. "
                "You can also upload the whole zipped export.\n\n"
                "Menu names can differ a little between Studio versions. Any CSV with a title, a publish date and a view count also works."
            )
        _privacy_note()
        return

    summary = summarise(channel)
    first, second, third, fourth = st.columns(4)
    first.metric("Videos loaded", f"{summary['videos']}")
    second.metric("With settled views", f"{summary['settled_videos']}", help="Videos that are 14+ days old; younger videos are still gaining views.")
    third.metric("Median views", compact_number(summary["median_views"]))
    fourth.metric("Typical video (geometric mean)", compact_number(summary["typical_views"]) if summary["settled_videos"] else "n/a")
    for note in channel.notes:
        st.caption(note)

    shown = channel.videos.sort_values("publish_time", ascending=False).head(200)
    table = pd.DataFrame({"Video": shown["title"], "Published": shown["publish_time"].dt.strftime("%Y-%m-%d"), "Views": shown["views"].astype(int)})
    st.dataframe(table, hide_index=True, width="stretch", height=260)
    st.button("Remove my data", on_click=clear_channel, key="clear_channel_main")
    with st.expander("How is this used?"):
        st.markdown(
            "- Your earlier videos give the model your **usual level** (the geometric mean of their views) and how steady or uneven you are.\n"
            "- The model then predicts a **lift**: how much better or worse than your usual video this draft is likely to do, from its title, "
            "tags, description, category and timing. Expected views = your usual level × that lift.\n"
            "- A video only counts once its views have had **14 days** to settle, and you need **at least 3** such videos.\n"
            "- The 80% interval comes from tests on channels the model had never seen."
        )
    _privacy_note()


def _privacy_note() -> None:
    st.caption(
        "Privacy: your file or channel data is read in memory for this browser session only. It is not saved to disk and not written to any log. "
        "On the online demo it is processed in that server's memory; run the app on your own computer if you want it never to leave it."
    )


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def main() -> None:
    apply_style()
    try:
        bundle = get_bundle()
    except (FileNotFoundError, ValueError) as error:
        st.error(str(error))
        st.code(".\\venv\\Scripts\\python.exe src\\advanced_model.py --train", language="powershell")
        st.stop()

    categories = list(bundle["categories"])
    init_state(categories)
    handle_google_callback()

    st.markdown(
        """
        <div class="masthead">
          <div class="eyebrow">AI / ML • EXPLAINABLE FORECASTING</div>
          <h1>Signal Studio<span> / YouTube strategy before publish</span></h1>
          <p>Turn a proposed title, tags, description and launch time into a transparent forecast, then see why, when to publish,
          what to edit, and how sure the model really is.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    metrics = bundle["metrics"]
    with st.sidebar:
        st.markdown("### Try a real video")
        st.selectbox("Load a real trending video", list(EXAMPLES), key="example_choice",
                     help="Real India-trending videos from the dataset, unchanged. They are part of the training data.")
        st.button("Load this video", on_click=load_example, args=(categories,), width="stretch", disabled=not EXAMPLES)
        st.markdown("### About this demo")
        st.write(f"**{bundle['training_rows']:,}** unique India-trending videos")
        accuracy = headline_accuracy(bundle)
        st.write(f"Views R² **{accuracy['views_r2']:.2f}** · engagement R² **{accuracy['engagement_r2']:.2f}**")
        st.caption(f"Measured on {accuracy['basis']}. R² is the share of the spread in the results that the model explains; "
                   "1.0 would be perfect and 0 means no better than guessing the average.")
        st.info("The trending-video forecast uses no likes, comments, views, channel information or thumbnail data as inputs. "
                "If you add your own earlier videos (My channel tab), their view counts are used to personalise it.")
        if st.session_state.get("channel") is not None:
            st.markdown("### Your channel")
            channel_loaded = st.session_state["channel"]
            st.write(f"**{len(channel_loaded.videos)}** videos loaded")
            st.button("Remove my data", on_click=clear_channel, width="stretch", key="clear_channel_sidebar")
        st.caption("Flow for the demo: Forecast → My channel → Best time → Title lab → AI coach → Similar videos → Scenario lab → YouTube timeline.")

    studio, mine, timing, lab, coach, similar, scenario, platform, method = st.tabs(
        ["Forecast studio", "My channel", "Best time", "Title lab", "AI coach", "Similar videos", "Scenario lab", "YouTube timeline", "Model brief"]
    )

    with studio:
        with st.form("proposal_form", clear_on_submit=False):
            proposal = proposal_inputs("main", categories)
            submitted = st.form_submit_button("Generate pre-publication forecast", width="stretch")
        if submitted:
            st.session_state["proposal"] = proposal
        draft = to_draft(st.session_state["proposal"])
        render_forecast(bundle, draft)

    with mine:
        render_my_channel()
    draft = to_draft(st.session_state["proposal"])
    with timing:
        render_best_time(bundle, draft)
    with lab:
        render_title_lab(bundle, draft)
    with coach:
        render_coach(bundle, draft)
    with similar:
        render_similar(bundle, draft)
    with scenario:
        render_scenario(bundle, categories, draft)
    with platform:
        render_platform_timeline()
    with method:
        render_method(bundle)


if __name__ == "__main__":
    main()
