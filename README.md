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

| **AI coach** | What should I change first, and why? | Evidence-grounded, schema-validated advice from an on-device model (or the rule-based fallback); proposed titles/tags are re-scored by the ML model. |

A downloadable **strategy brief** (Markdown) summarises one draft.

## AI coach (on-device language model)

The **AI coach** tab turns the model's numbers into a few prioritised, explained suggestions. The language model only *writes advice*; every number shown (forecast, re-scored titles and tags) comes from the trained Random Forest, and the forecast is never altered by the language model (a golden-snapshot test proves the ML outputs are unchanged).

```text
draft -> ML forecast (untouched) -> evidence packet (ID-tagged facts) -> local model -> validation -> app
                                          \-> rule-based recommender (always available, used as the fallback)
```

- **Grounded:** the model may only use the packet's facts and must cite their ids. Output is rejected unless it matches a strict JSON schema, quotes only numbers present in the evidence, avoids promises ("will go viral"), keeps title ideas close to the draft's own words, and only gives timing advice when the data supports it. One repair retry, then the rule-based advice is shown with the reason.
- **On-device and private:** talks only to a loopback server (Ollama or any OpenAI-compatible local server); no API key, no online service. Prompts and answers are never logged.
- **Device-aware:** the app detects RAM, CPU threads and NVIDIA VRAM and picks the best *installed* model that suits it (about 7B on an 8 GB GPU such as an RTX 5050 laptop, 3B on a 16 GB CPU-only laptop, 1.5B on 8 GB RAM, rule-based below that). Nothing is downloaded automatically.

The launcher (above) installs Ollama and pulls the models for your device; or do it by hand with `ollama pull qwen2.5:7b` (8 GB GPU; RTX 50-series needs a recent Ollama and NVIDIA driver) or `ollama pull qwen2.5:3b` (CPU laptop).

Settings are optional environment variables (see `.env.example`). The hosted Render service has no model, so it runs in rule-based mode; run locally to use the language model. There is no fake model anywhere: `tests/test_real_model.py` runs against the real local model whenever Ollama is running and skips otherwise (for example on GitHub Actions).

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

## Run it on any device (one command)

Needs only Python 3.10+ and git. The launcher creates `venv`, installs the pinned requirements, detects your hardware, installs and starts [Ollama](https://ollama.com), downloads the right language models (asking first), then starts the app at http://localhost:8501.

```powershell
git clone https://github.com/NiksheyYadav/youtube-strategy-prediction.git
cd youtube-strategy-prediction
.\run.ps1            # Windows (or double-click run.bat)
./run.sh             # macOS / Linux
```

Flags: `-Yes` / `--yes` accept every install and download without asking, `-Check` / `--check` preview the plan and change nothing, `-NoLlm` / `--no-llm` skip the language model (rule-based advice), `-Port N` / `--port N`.

| Device | Model the launcher plans |
| --- | --- |
| NVIDIA GPU with 8 GB VRAM (e.g. RTX 5050 laptop) | `qwen2.5:7b` (~4.7 GB) + lite fallback |
| CPU only, 12 GB+ RAM | `qwen2.5:3b` (~1.9 GB) + lite fallback |
| CPU only, 6-12 GB RAM | `qwen2.5:1.5b` (~1.0 GB) + lite fallback |
| Under 6 GB RAM | none: rule-based advice |

The lite fallback is `qwen2.5:0.5b` (~0.4 GB). A literal million-parameter model cannot follow the JSON format, so 0.5B is the smallest practical choice. The chain is: main model, then lite model, then the rule-based recommender, so the AI coach always answers.

Manual setup (if you prefer): `python -m venv venv`, install `requirements-app.txt`, then `streamlit run app.py`.

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
