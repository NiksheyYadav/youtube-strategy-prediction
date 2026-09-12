# Content Strategy Insights

Derived from a Random Forest model trained on pre-publish metadata for India-trending YouTube videos (2017-2018 Kaggle snapshot).

1. **What predicts views most**: the strongest pre-publish signals are `description_length`, `caps_ratio`, and `category_name_Education`. Writing effort and style (description length, title capitalization) rival or beat category in importance — these are levers a creator directly controls, not just a consequence of what niche they're in.

2. **What predicts engagement (likes+comments per view) most**: `description_length`, `category_name_Science & Technology`, and `caps_ratio` dominate. Views and engagement are driven by partly different factors, so optimizing for one doesn't automatically help the other.

3. **Category still matters, among categories with enough data to trust**: `Shows` has the highest median views (~621,739) among categories with at least 30 videos in this dataset (n=121). Categories with only a handful of trending videos (e.g. Movies, n=2) were excluded from this comparison — their medians aren't reliable.

4. **Timing has a real, if modest, effect**: among publish-day/hour combinations with at least 30 videos (n=38 for the winner), the best-performing slot in this data is **Saturday at 1:00 IST** (median views ~459,179). Tag count correlates positively with views (r=0.05), and description length correlates positively with views (r=0.10) — both are cheap, low-effort levers worth using consistently rather than skipping.

5. **Take the model's confidence with a grain of salt**: on held-out data, the model explains about 38% of the variance in log-views and 61% of the variance in engagement rate. That means pre-publish metadata alone is a meaningful but incomplete predictor — channel reputation, thumbnail quality, and algorithmic promotion (none of which are in this dataset) almost certainly explain a large share of what's left.
