# Advanced Model Card

## Purpose

Estimate relative performance among videos that already reached India’s Trending list. The app is a pre-publication decision aid, not a promise of views or a viral/non-viral classifier.

## Training data

16,307 unique India-trending video snapshots after de-duplication. Every input is available before publishing. Likes, dislikes, comments, views, video ID, and channel fields are excluded from model inputs.

## Student-explainable additions

The advanced version retains the original title, tag, category, description and timing fields, then adds transparent counts and ratios: punctuation, emoji, digit, urgency and how-to wording in the title; tag length and multiword-tag ratio; description links, hashtags and call-to-action words; and weekend/cyclical time fields. These are descriptive associations, not causal rules.

## Validation

- Log views, 5-fold CV R²: 0.419 ± 0.014
- Engagement rate, 5-fold CV R²: 0.637 ± 0.024
- Log views, chronological holdout R²: 0.368
- Engagement rate, chronological holdout R²: 0.529

## Honest uncertainty (split-conformal intervals)

Intervals are calibrated on out-of-fold errors so that about 80% of true values fall inside. Measured coverage: 80.0% (views) and 80.0% (engagement) out-of-fold; on the later-in-time holdout 79.7% and 80.9%. A views interval is the forecast times 0.29 to 3.48.

## Limits

The source contains only videos that trended, so it cannot answer whether an arbitrary upload will trend. It also lacks thumbnails, channel history, audience retention and YouTube ranking signals. Feature importance is not proof that changing one field will cause the predicted outcome.
