# TA4 Viva Q&A — AI-Based YouTube Analytics and Content Strategy Prediction

## 30-second project explanation

We built a supervised machine-learning system that estimates relative views and engagement before a YouTube video is published. It uses only metadata a creator controls before upload: the title, tags, description, category, and intended time in IST. The training data is the India subset of Kaggle’s Trending YouTube Video Statistics. We removed repeated daily appearances of the same video, leaving 16,307 unique videos. Our TA4 version adds transparent text, tag, and timing features and provides an interactive scenario comparison for draft videos.

## Likely questions

### What is the actual AI/ML part?

Two Random Forest regression models learn non-linear patterns between pre-publication metadata and two outcomes: `log1p(views)` and engagement rate `(likes + comments) / views`. We first used Linear Regression as a baseline, compared tree models, and selected Random Forest. The final app loads saved models and scores a new draft in real time.

### Why regression instead of classification?

The outputs are continuous quantities: view count and engagement rate. Classification would need an arbitrary cutoff such as “viral” or “not viral,” which is not supported by this trending-only dataset.

### Are you predicting whether a video will go viral?

No. The dataset contains only videos that already reached the India Trending list. We predict relative performance within that population. A future version needs a comparison set of non-trending uploads to answer a true virality question.

### How did you remove duplicate videos?

The raw dataset records one row per video per day on Trending. We parsed the unusual `trending_date` format, sorted by it, grouped by `video_id`, and retained the latest snapshot for each video. This changed 37,352 daily snapshots into 16,307 unique videos.

### How did you prevent data leakage?

Views, likes, dislikes, comment count, channel metadata, and video ID are not features. Likes and comments are used only after publishing to calculate the engagement-rate target. Every app input is something the creator knows before upload.

### Why transform views with `log1p`?

View counts are strongly right-skewed: a small number of videos have very high values. `log1p(views)` reduces that skew, stabilises regression, and still allows the app to convert the result back to views using `expm1`.

### Why Random Forest?

The feature relationships are not purely linear, as the correlation analysis suggests. Random Forest captured non-linear combinations such as title style with category and time. It also provides interpretable feature importances and a practical saved-model size.

### What did the TA4 model add?

It adds explainable fields that are still available before upload: title punctuation, digits, emojis, urgency/how-to wording, tag length and multiword-tag ratio, description links, hashtags, call-to-action wording, weekend flag, and cyclic hour features. It also adds a chronological holdout evaluation, Shapley explanations, calibrated intervals, a 168-slot timing map, a title-edit ranking, a similar-video second opinion and an A/B Scenario Lab.

### What do the accuracy results mean?

The advanced model achieved mean five-fold CV R² of 0.419 for log views and 0.637 for engagement rate. On a harder chronological holdout, R² was 0.368 and 0.529. The gap is expected: predicting later uploads is harder because YouTube patterns change over time. These scores show useful signal but are not guarantees for individual videos.

### Is feature importance causal?

No. It shows which inputs the model used most while fitting this dataset. It does not prove that changing one field will cause more views. The app therefore calls A/B output a scenario comparison, not a guaranteed recommendation.

### Why does the app show a range, and can I trust it?

The app shows an 80 % **split-conformal** interval. We calibrate on the model's out-of-fold errors (the 80th percentile of the absolute error), so about 80 % of true values should fall inside. We do not just assert this: coverage was 80.0 % out-of-fold and 79.7 % (views) / 80.9 % (engagement) on a chronological holdout the calibration never saw. The honest reading is that the interval is wide (a views forecast is typically within x0.29 to x3.5) because metadata alone is a moderate signal. The earlier tree-disagreement spread is not a probability, so it is no longer the headline.

### How does the "Why this forecast" chart work?

It uses **Shapley values**, from cooperative game theory. We start from a typical trending video and "reveal" the draft's feature groups (title, tags, description, timing, category) one at a time in every possible order, averaging how much each group moves the forecast. With five groups that is only 2^5 = 32 combinations, so we compute it exactly with no extra library. Two properties are tested automatically: the effects add up to forecast minus typical (efficiency), and the contributions are finite and reproducible. They are associations learned from data, not causes.

### Why is "Category" often the biggest bar?

Audience size differs a lot between categories (for example Education videos have lower median views than Music in this data). It says nothing about quality, and category is fixed once you know what you are making, so the title/tags/description/timing bars are the actionable ones.

### How do the Title lab suggestions work, and are they advice?

Each suggestion is one programmatic edit (add a number, phrase as a question, add hashtags, and so on). The same trained model re-scores the edited draft and we rank by predicted change. They show what the model *associates* with higher views; they are not proof that the edit would help a real video, and the app says so.

### How is the "Similar videos" tab a second opinion?

It uses a different method with no model: TF-IDF vectors of title and tags, cosine similarity to every trending video, and the weighted median views of the closest ones. If it agrees with the Random Forest within a factor of two the app says "Consistent"; otherwise "Differ", which is useful information in itself (look-alikes may be much bigger channels).

### How does the AI coach avoid making things up?

The model never produces numbers. It receives a packet of ID-tagged facts computed by the existing ML code, must cite those ids, and its JSON is rejected unless every figure it quotes exists in the evidence, it makes no promises, titles stay close to the draft's own words, and timing advice is allowed by the data. Proposed titles and tags are re-scored by the trained Random Forest, so the displayed changes are model estimates, not language-model guesses. If anything fails, a rule-based recommender built from the same evidence is shown instead. It runs on-device (Ollama), and the app picks a model size that fits the laptop's RAM and GPU.

### What are the main limitations?

The data is from 2017–2018 and includes only India-trending videos. It lacks thumbnails, channel subscribers, audience retention, video topic semantics, and YouTube’s internal recommendation signals. The observations are associations and do not support causal claims.

### What would you improve next?

Collect current uploads from the YouTube Data API at a fixed age, including non-trending videos; add thumbnail embeddings and title semantics; include channel history; and validate predictions against real creator uploads over time.

## Key numbers to remember

| Item | Value |
| --- | ---: |
| Raw daily trending snapshots | 37,352 |
| Unique videos after de-duplication | 16,307 |
| Original Linear Regression R²: log views / engagement | 0.197 / 0.384 |
| Original Random Forest held-out R²: log views / engagement | 0.378 / 0.612 |
| TA4 advanced model 5-fold CV R²: log views / engagement | 0.419 / 0.637 |
| TA4 chronological holdout R²: log views / engagement | 0.368 / 0.529 |
| 80 % interval coverage, later uploads: views / engagement | 79.7 % / 80.9 % |
