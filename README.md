# Signal Studio — Explainable YouTube Content-Strategy Forecasting

An AI/ML project that forecasts the **relative views** and **engagement rate** of a proposed YouTube video *before it is published*, then explains the forecast, quantifies its uncertainty, and suggests what to change.

It uses only information a creator controls before upload: title, tags, description, category, and publish time (IST). Data: the India subset of Kaggle's *Trending YouTube Video Statistics* (37,352 daily snapshots → **16,307 unique videos** after keeping each video's latest snapshot).

**Live demo:** https://youtube-strategy-predictor.onrender.com  
*(Render free tier: the service sleeps after ~15 minutes idle, so the first load can take 30-60 seconds. Open it a minute before presenting.)*

> **Scope.** The data contains only videos that already trended, so this is a regression on *relative performance among trending videos*. It does not classify an arbitrary upload as viral / not viral.

## What the app does

| Tab | Question it answers | How it works (student-level) |
| --- | --- | --- |
| **Forecast studio** | How many views / what engagement should I expect? | Two Random Forests (log-views, engagement rate). Shown with an **80 % calibrated interval** and the draft's **percentile** among trending videos. |
| *(inside the studio)* **Why this forecast** | Which of my choices help or hurt? | **Exact Shapley values over five feature groups** (title, tags, description, timing, category): reveal the groups one by one in all 2⁵ = 32 orders and average each group's effect. Contributions add up exactly to *forecast − typical video*. |
| *(inside the studio)* **Keyword radar** | Do my title words travel with big or small audiences? | Median views of trending videos containing each word (only words used by 25+ different channels, so channel names are filtered out). |
| **Best time** | When should I publish? | The same draft is scored in all **168 weekly slots**, smoothed over neighbouring hours, shown as a heatmap with the best three slots. |
| **Title lab** | What small edits does the model associate with more views? | ~12 programmatic edits (add a number, question, "How to", hashtags, call-to-action, title keywords as tags…) are re-scored by the model and ranked. One click **applies** an edit. |
| **Similar videos** | Does a completely different method agree? | TF-IDF cosine similarity finds look-alike trending videos; their median is compared with the model forecast. |
| **Scenario lab** | A vs B? Same draft in another category? | Side-by-side forecast with an interval-overlap check ("within the model's uncertainty?"), plus a category what-if chart. |
| **Model brief** | How good is it, honestly? | R², chronological holdout, **measured interval coverage**, feature-group importance, limits. |

A downloadable **strategy brief** (Markdown) summarises one draft.

## Verified results

| Evaluation | Log-views R² | Engagement R² |
| --- | ---: | ---: |
| Linear Regression baseline (stage 3) | 0.197 | 0.384 |
| First Random Forest, held-out test (stage 4) | 0.378 | 0.612 |
| **Advanced Random Forest, mean 5-fold CV** | **0.419** | **0.637** |
| Advanced Random Forest, chronological holdout (train on earlier, test on later uploads) | 0.368 | 0.529 |

**Do the uncertainty intervals hold?** Intervals are split-conformal: calibrated on out-of-fold errors so that ~80 % of true values fall inside, then tested on later uploads they never saw.

| Check | Views | Engagement |
| --- | ---: | ---: |
| Out-of-fold coverage | 80.0 % | 80.0 % |
| Later-in-time holdout coverage | 79.7 % | 80.9 % |

A views forecast is typically within ×0.29 to ×3.5 of the truth — wide, which is the honest answer when pre-publish metadata is only a moderate signal.

## Leakage control

Views, likes, dislikes, comment count, channel details and video ID are never model inputs (likes + comments are used only to build the engagement *target*). Training and the live app call the **same** feature function (`build_demo_features`), and a test asserts the schema and the exclusion list.

## Run it

```powershell
cd C:\youtube-strategy-prediction
python -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements.txt
.\run_demo.ps1            # http://localhost:8501
```

Regenerate everything (needs the Kaggle files in `data/`):

```powershell
.\venv\Scripts\python.exe src\clean.py
.\venv\Scripts\python.exe src\features.py
.\venv\Scripts\python.exe src\train.py                    # baseline + first RF (stages 3-4)
.\venv\Scripts\python.exe src\evaluate.py
.\venv\Scripts\python.exe src\advanced_model.py --train   # advanced model + calibration + app artifacts
```

## Test

```powershell
.\venv\Scripts\python.exe -m pytest -q      # 33 tests, ~30 s
```

Covers feature correctness (regression tests for hashtag/link/tag-quote bugs), schema/leakage, Shapley axioms (efficiency), interval coverage, similarity search, and **headless end-to-end runs of the Streamlit app** (every tab, example drafts, apply buttons, blank-title handling). The same suite runs in GitHub Actions on every push.

## Deployment

Deployed on Render (Singapore, free plan) from this repository's `main` branch with auto-deploy on every push: https://youtube-strategy-predictor.onrender.com. GitHub Actions runs the test suite on every push.

`render.yaml` (Render Blueprint), `Dockerfile` and `requirements-app.txt` define one Streamlit web service with a health check at `/_stcore/health`. The deployed image contains only `app.py`, `src/`, and two model files (`models/advanced_model_bundle.joblib`, `models/similarity_index.joblib`); the raw Kaggle data is not needed to serve predictions.

```powershell
docker build -t signal-studio . ; docker run -p 8501:8501 signal-studio
```

## Layout

```text
app.py                         Streamlit app (7 views)
src/advanced_model.py          features, training, evaluation, calibration, artifacts
src/insights.py                runtime analytics: Shapley, time grid, edits, similar videos
src/insights_artifacts.py      build-time helpers (conformal, keyword stats, TF-IDF index)
src/inference.py               safe single/batch prediction helpers
src/clean.py features.py train.py evaluate.py   stages 1-5 of the original pipeline
models/                        deployable bundle + similarity index (+ stage-4 baselines)
reports/                       metrics, calibration report, model card, plots
tests/                         33 automated checks
deliverables/                  slide deck, summary, viva Q&A, demo script
```

`src/model_contract.py`, `src/advanced_features.py`, `src/advanced_train.py` and `src/advanced_evaluate.py` are an earlier, separate feature-contract experiment; the deployed app does not use them.

## Limits (say these out loud in the viva)

The data is India-trending content from 2017–2018. It lacks non-trending uploads, thumbnails, channel history, retention and YouTube's ranking signals. Shapley values, keyword statistics and edit rankings describe **associations the model learned**, not causal effects; a title edit that "helps" in the model may not help a real video.
