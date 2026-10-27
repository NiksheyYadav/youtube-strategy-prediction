# Advanced Model Card

## Purpose

Estimate relative performance among videos that already reached India’s Trending list. The app is a pre-publication decision aid, not a promise of views or a viral/non-viral classifier.

## Training data

16,307 unique India-trending video snapshots after de-duplication from 1,422 channels. Every input is available before publishing. Likes, dislikes, comments, views, video ID, and channel fields are excluded from model inputs.

782 videos had ratings or comments switched off, so their engagement rate cannot be measured (YouTube stores 0 likes). They are left out of the engagement model but still count for views.

## Student-explainable additions

The advanced version retains the original title, tag, category, description and timing fields, then adds transparent counts and ratios: punctuation, emoji, digit, urgency and how-to wording in the title; tag length and multiword-tag ratio; description links, hashtags and call-to-action words; weekend/cyclical time fields; and the share of the title written in a non-Latin script (Hindi, Tamil, Telugu and so on). These are descriptive associations, not causal rules.

## Validation (three tests, from easiest to most honest)

- Shuffled 5-fold CV, log views R²: 0.433 ± 0.015; engagement R²: 0.642 ± 0.020. The same channel can be on both sides of this split, so it flatters the model.
- Later-in-time holdout, log views R²: 0.380; engagement R²: 0.553.
- **Channels never seen in training (the first-time-user case), log views R²: 0.187 ± 0.048; engagement R²: 0.378 ± 0.046.** This is the number to quote.
- On unseen channels, by title script (log views R²): latin titles 0.19 (n=14,008), non latin titles 0.02 (n=2,299).

## Honest uncertainty (split-conformal intervals)

Intervals are calibrated on out-of-fold errors for channels the model had not seen, so that about 80% of true values fall inside. Measured coverage: 80.0% (views) and 80.0% (engagement) out-of-fold; on the later-in-time holdout 85.9% and 87.7% (that holdout includes channels the model has seen, so it is expected to be somewhat higher). A views interval is the forecast times 0.22 to 4.56. 11 categories with enough videos get their own interval width.

## Limits

The source contains only videos that trended, so it cannot answer whether an arbitrary upload will trend; a forecast is relative to other trending videos. It also lacks thumbnails, channel history (the separate history model adds that), audience retention and YouTube ranking signals. Feature importance is not proof that changing one field will cause the predicted outcome.
