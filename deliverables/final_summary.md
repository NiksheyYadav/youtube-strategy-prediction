# AI-Based YouTube Analytics and Content Strategy Prediction — TA4 Summary

## Objective

Build an AI/ML system that estimates a YouTube video’s relative performance before publishing and turns learned patterns into transparent content-strategy discussion points.

## Data and preparation

We used the India file from Kaggle’s *Trending YouTube Video Statistics* dataset. The raw file contains 37,352 daily appearances on the Trending list. Because one video can appear on multiple days, the project parses dates, keeps each video’s latest snapshot, and retains 16,307 unique videos. The analysis is therefore scoped to videos that already reached Trending in India.

## Inputs, targets, and leakage control

The model only uses fields a creator knows before upload: category, title text, tags, description, and intended publication day/hour in IST. Views are modelled on a `log1p` scale. Engagement rate is `(likes + comment_count) / views`. Views, likes, dislikes, comments, video ID, and channel fields are excluded from inputs.

## TA4 enhancements

**Model.** The original metadata features were extended with student-explainable signals: title punctuation, emoji and digit counts, urgency/how-to keyword counts, a simple sentiment score, tag length and multiword-tag ratio, description word/link/hashtag/call-to-action counts, a weekend flag and circular time encoding. Regression tests now guard these features (an audit found that hashtags and `www.` links were previously never counted and that training tags carried quote characters live input never had; both were fixed and the model retrained).

**Explainable decision tools (all in the live app).**

1. *Why this forecast*: exact Shapley values over five feature groups (title, tags, description, timing, category) that add up to forecast minus a typical trending video.
2. *Calibrated uncertainty*: split-conformal 80 % intervals, with coverage measured on later uploads (79.7 % views, 80.9 % engagement).
3. *Best time*: the same draft scored in all 168 weekly slots (IST) as a heatmap.
4. *Title lab*: about twelve programmatic edits re-scored by the model and ranked, with one-click apply.
5. *Similar videos*: TF-IDF look-alike trending videos as an independent second opinion.
6. *Keyword radar*: median views of trending videos by title word (words used by 25+ channels only).
7. *Scenario lab*: A/B comparison with an interval-overlap check, plus a category what-if.
8. Percentile benchmark against trending videos and a downloadable strategy brief.

## Results

The original Linear Regression baseline achieved R² of 0.197 for log views and 0.384 for engagement. The first Random Forest achieved held-out R² of 0.378 and 0.612. With the TA4 feature set, Random Forest achieved five-fold CV R² of **0.419** (log views) and **0.637** (engagement). A later-in-time holdout was harder, at **0.368** and **0.529**, which is an important result because platform patterns change. The 80 % prediction intervals cover 80.0 % of out-of-fold cases and 79.7 % / 80.9 % (views / engagement) of later uploads; a views forecast is typically within x0.29 to x3.5 of the truth.

## Responsible interpretation

Feature importances identify signals used by the model; they do not prove cause and effect. The model does not observe thumbnail quality, subscriber base, retention, content meaning, or YouTube’s internal ranking system. Its output should support discussion and pre-publication comparisons, not guarantee views.

## Run locally

```powershell
.\run_demo.ps1
```

Then open `http://localhost:8501`, or use the deployed Render service (see the repository README).
