# Signal Studio: project guide

How to run the project, every command, and what each file does. Written for the person who owns the project, in plain words.

## 1. What this project is

Signal Studio predicts how a **new YouTube video may perform before it is published**. You give it a title, tags, a description, a category and a publish time. It returns an expected number of views and an expected engagement rate, each with an 80% range, then explains the forecast and suggests edits.

It learned from **16,307 India-trending videos (2017-2018)**. It also has a second model that, when you add your own earlier videos, forecasts **relative to your own usual level**. Your data can come from a YouTube Studio export or from signing in with Google.

What it cannot do: say whether an ordinary upload will trend, or see thumbnails, retention or YouTube's ranking signals. Every effect shown is an association the model learned, not a cause.

## 2. Start it (the quick way)

You need Python 3.10 or newer and git. Nothing else.

| System | Command | What happens |
| --- | --- | --- |
| Windows | `.\run.ps1` (or double-click `run.bat`) | Creates `venv`, installs the pinned packages, checks your hardware, offers to install Ollama and a language model, starts the app at http://localhost:8501 |
| macOS / Linux | `./run.sh` | Same |

Useful flags (the same on every system; PowerShell spells them `-Yes`, `-Check`, `-NoLlm`, `-NoBrowser`, `-Port 8502`):

| Flag | Meaning |
| --- | --- |
| `--check` | Show what it would do and change nothing. Run this first if you are unsure. |
| `--yes` | Accept every install and download without asking. |
| `--no-llm` | Skip the language model. The AI coach then gives rule-based advice only. |
| `--no-browser` | Do not open a browser tab. |
| `--port 8502` | Use another port (it also tells you if the port is busy). |
| `--model qwen2.5:3b` | Use a specific language model instead of the automatic choice. |
| `--lan` | Let other devices on your Wi-Fi open the app. **Off by default**: the app is reachable only from this computer. |

Manual start, if you prefer: `python -m venv venv`, install `requirements-app.txt`, then `streamlit run app.py`.

## 3. Every command and what it does

Run these from the project folder. On Windows the Python is `.\venv\Scripts\python.exe`; on macOS or Linux use `venv/bin/python`.

### Using the app

| Command | What it does |
| --- | --- |
| `streamlit run app.py` | Starts the app on port 8501. Use `--server.port 8502` for another port. |
| `python scripts/launch.py --check` | Prints the launcher's plan (what would be installed or downloaded). Changes nothing. |

### Rebuilding the models (only when you change the data or the features)

The raw data is not stored in git. Put `INvideos.csv` and `IN_category_id.json` in `data/` first (Kaggle: *Trending YouTube Video Statistics*, India file).

| Step | Command | What it does | Time |
| --- | --- | --- | --- |
| 1 | `python src/clean.py` | Keeps each video's latest snapshot, drops bad rows, writes `data/processed/clean.csv` | seconds |
| 2 | `python src/features.py` | Builds the stage-2 feature table | seconds |
| 3 | `python src/train.py` | Stage 3-4: baseline Linear Regression and the first Random Forest (`models/*.pkl`) | minutes |
| 4 | `python src/evaluate.py` | Stage 5: feature-importance plot and plain-English takeaways | seconds |
| 5 | `python src/advanced_model.py --train` | **Trains the model the app uses**: both Random Forests, the three accuracy tests, the 80% intervals, the look-alike index. Writes `models/advanced_model_bundle.joblib`, `models/similarity_index.joblib` and the files in `reports/` | about 3 minutes |
| 6 | `python -m src.history_model --train` | Trains the "your own history" model (`models/history_models.joblib`) | about 2 minutes |
| 7 | `python -m src.golden --record` | Re-records the saved numeric snapshot that tests compare against. Do this **only** after a deliberate model change | seconds |

If you change the features in `src/advanced_model.py`, run steps 5, 6 and 7 together. The app will refuse a model file that does not match the code and will tell you to retrain (it shows the command).

### Testing

| Command | What it does |
| --- | --- |
| `python -m pytest -q -p no:cacheprovider` | Everything: unit tests, headless runs of the app, and the real-browser tests |
| `python -m pytest -q -m "not browser"` | Everything except the real-browser tests (faster) |
| `python -m pytest tests/e2e -v` | Only the real-browser tests: starts the app, drives real Chrome or Edge |
| `SIGNAL_STUDIO_EXPORT=path/to/export.zip python -m pytest tests/e2e -k own_youtube` | Also loads **your own** YouTube Studio export in the browser (PowerShell: `$env:SIGNAL_STUDIO_EXPORT="C:\path\export.zip"`) |
| `python -m coverage run -m pytest -q -m "not browser"` then `python -m coverage report` | How much of the code the tests run |
| `pip-audit -r requirements-app.txt` | Checks the pinned packages for known security advisories |

Tests that need `data/processed/clean.csv` skip themselves, with the reason, on a machine that does not have it. Tests that need a language model skip when Ollama is not running. The browser tests skip when Playwright or Chrome is missing. Install the extras with `pip install -r requirements-dev.txt`.

### Reports and documents

| Command | What it does |
| --- | --- |
| `python scripts/make_report_assets.py` | Redraws the diagrams and charts used by the report and slides |
| `python scripts/eval_ai_coach.py` | Runs the real local language model on example drafts and records what it did |
| `python scripts/try_real_model.py` | Developer check of the real local model chain on one draft |
| `python scripts/eval_model_v2.py` | The research probe that compared model designs with and without channel history |
| `python scripts/capture_screens.py` | Screenshots of every tab of the running app |

### Docker

```powershell
docker build -t signal-studio .
docker run -p 8501:8501 signal-studio
```

The image holds `app.py`, `src/`, the three model files, `knowledge/` and `.streamlit/`. It does not hold the raw data. (Docker has not been built on this computer because it is switched off here; the Dockerfile is checked by a test for missing files.)

## 4. What each tab does

| Tab | What you get |
| --- | --- |
| **Forecast studio** | Write a draft, get expected views and engagement with an 80% range, where it sits among trending videos, why (exact Shapley values over five groups of choices), a keyword radar, and a downloadable strategy brief. Empty until you write a title. |
| **My channel** | Add your own earlier videos: upload a YouTube Studio export, or **Connect with Google** (read-only, once, then the access is cancelled). The Forecast tab then also shows what the model expects **for your channel**. |
| **Best time** | The same draft scored in all 168 weekly slots. |
| **Title lab** | About a dozen honest edits (add a number, a question, a hashtag and so on), each re-scored by the model and ranked. One click applies an edit. |
| **AI coach** | Written advice from a language model that runs on your computer (or rule-based advice when none is installed). Every number comes from the trained model; the language model only writes the explanation. |
| **Similar videos** | Real look-alike trending videos found by text similarity, compared with the model's forecast. |
| **Scenario lab** | Draft A against Draft B, and the same draft in other categories. |
| **YouTube timeline** | A sourced list of documented changes to how YouTube recommends and counts videos (2012 to 2026). Each entry links to its source and is labelled official, peer-reviewed or press report. This is public statements, not YouTube's secret formula. |
| **Model brief** | The honest accuracy numbers and the limits. |

## 5. How accurate is it? (read this before quoting numbers)

Measured on the 16,307 training videos, three ways. The honest one is the first.

| Test | Log-views R² | Engagement R² |
| --- | ---: | ---: |
| **Channels the model has never seen** (what a new creator gets) | **0.19** | **0.38** |
| Later uploads (train on earlier, test on later) | 0.38 | 0.55 |
| Shuffled 5-fold (the same channel is on both sides, so it flatters the model) | 0.43 | 0.64 |

With your own history (the second model), on channels it had never seen: views R² **0.57**, engagement R² **0.72**. This is the main reason to add your data.

R² is the share of the spread in results that the model explains. 1.0 is perfect; 0 is no better than guessing the average. For titles in Hindi, Tamil, Telugu and other non-Latin scripts the views score is close to 0 (the app says so when you type one). These numbers are stored in the model file and printed by the app; they are never typed in by hand.

## 6. Your own data, privacy and the Google connection

- **Upload**: works with no setup. The file is read in memory for your browser session, not saved to disk and not written to a log. **Remove my data** really forgets it (including the uploaded file).
- **Connect with Google**: needs a one-time setup in your Google Cloud account (about 10 minutes, free). Follow [CONNECT_YOUTUBE.md](CONNECT_YOUTUBE.md). It asks for read-only access (`youtube.readonly`), reads your videos once and cancels its own access straight away. On your own computer, **Keep me connected** (setting `GOOGLE_STAY_CONNECTED=1` in `.env`) saves only Google's read-only permission slip in your user folder so your channel loads automatically on every visit; **Disconnect from Google** removes it. It never works on the hosted website or for visitors from another device. Put the client ID and secret in a git-ignored `.env` file (copy `.env.example`), never in chat or in git.
- On the hosted website your data passes through that server's memory. If you want it never to leave your computer, run the app locally.
- YouTube's rules for API data: it may not be stored for more than 30 days or turned into a new dataset. The app keeps nothing, so it stays within that.

## 7. The language model (AI coach)

The launcher installs [Ollama](https://ollama.com) and downloads a model that suits your hardware (it asks first):

| Your computer | Model |
| --- | --- |
| NVIDIA GPU with 8 GB VRAM | `qwen2.5:7b` (about 4.7 GB) |
| CPU only, 12 GB+ RAM | `qwen2.5:3b` (about 1.9 GB) |
| CPU only, 6-12 GB RAM | `qwen2.5:1.5b` (about 1.0 GB) |
| Under 6 GB RAM | none: rule-based advice |

A small `qwen2.5:0.5b` is kept as a fallback. The chain is: main model, then the small model, then rule-based advice, so the coach always answers. The model talks only to a server on your own computer; no key and no online service. There is no pretend model anywhere: if none is running, the app says so and shows the rule-based advice.

Optional settings go in `.env` (see `.env.example`): `LLM_BACKEND`, `LLM_MODEL`, `LLM_TIMEOUT_S` and so on.

## 8. File map

```text
app.py                     the Streamlit app (all tabs)
run.ps1 run.bat run.sh     one-command start for Windows / macOS / Linux
scripts/launch.py          what those scripts run: sets up venv, Ollama, model, then starts the app
.streamlit/config.toml     theme and safety settings (origin check on, uploads capped at 10 MB, no developer toolbar)
.env.example               the optional settings you can copy to .env

src/                       the code
  clean.py features.py train.py evaluate.py   stages 1-5 of the original pipeline
  advanced_model.py        features, training, the three accuracy tests, intervals, model card (the model the app uses)
  insights_artifacts.py    build-time helpers: word splitter, interval maths, keyword statistics, look-alike index
  insights.py              run-time analytics: Shapley explanation, 168-slot map, edits, look-alike search
  inference.py             one safe function to predict a draft; checks the model file matches the code
  history_features.py      "what do your earlier videos say" features, with a rule that prevents look-ahead
  history_model.py         the model that forecasts relative to your own usual level
  channel_history.py       reads and cleans an uploaded or downloaded video list
  personal_forecast.py     one call that turns a draft plus your history into your forecast
  youtube_oauth.py         Google sign-in (OAuth with PKCE), read-only
  youtube_api.py           reads your videos through the YouTube Data API
  platform_knowledge.py    loads and checks the sourced YouTube timeline
  reco_evidence.py reco_schema.py recommendations.py   the AI coach: evidence packet, strict output checks, rule-based advice
  llm_client.py device_profile.py env_file.py          the local language model client, hardware detection, .env reader
  golden.py                the saved numeric snapshot used to prove the ML layer never changes by accident
  model_contract.py advanced_features.py advanced_train.py advanced_evaluate.py
                           an earlier, separate experiment; the app does not use these (kept because they were part of the course work)
models/                    advanced_model_bundle.joblib, similarity_index.joblib, history_models.joblib (used by the app);
                           views_model.pkl, engagement_rate_model.pkl (the stage-4 deliverables, not used by the app)
knowledge/                 youtube_platform_timeline.json: the sourced timeline shown in the app
reports/                   metrics, calibration report, model card, plots written by training
tests/                     the automated checks (tests/e2e = real browser; tests/real_videos.py = four real videos used as drafts)
docs/                      this guide, CONNECT_YOUTUBE.md, the audit plan and report
deliverables/              the report, notes, slides and viva material
data/                      raw and cleaned data (not in git)
Dockerfile render.yaml     deployment
.github/workflows/         ci.yml (tests on every push), keep-warm.yml (pings the hosted site)
```

## 9. Deployment (Render) and keeping it awake

The hosted site is https://youtube-strategy-predictor.onrender.com. It is built from this repository's `main` branch. **Changes made on this computer appear there only after you push them.**

Render's free plan puts the site to sleep after about 15 minutes without visitors, so the first page load can take 30 to 60 seconds. The repository has a GitHub Actions job (`keep-warm.yml`) that pings the site every 10 minutes. **GitHub runs scheduled jobs on a best-effort basis and often skips or delays them, so this does not guarantee the site is awake.**

For a reliable wake-up, use a free outside monitor (needs your own account):

1. Make a free account at https://uptimerobot.com.
2. Add a monitor: type **HTTP(s)**, URL `https://youtube-strategy-predictor.onrender.com/_stcore/health`, interval **5 minutes**.
3. Before a presentation, also open the site yourself a few minutes early.

## 10. If something goes wrong

| What you see | Why | What to do |
| --- | --- | --- |
| "The saved model was trained with a different set of features..." | The code and the model file are from different versions | Run `python src/advanced_model.py --train`, then `python -m src.history_model --train` |
| "Port 8501 is not available" | Another program (maybe an older copy of the app) uses it | Use `--port 8502`, or close the other copy |
| "Remove my data" seems to do nothing | Old browser tab | Reload the page. (A bug that kept an uploaded file after removal was fixed.) |
| The AI coach says no local model is running | Ollama is not running or no model is installed | `ollama pull qwen2.5:3b`, or run the launcher again |
| Sign in with Google says it is "not set up on this server" | No Google client settings | Follow CONNECT_YOUTUBE.md, or just upload a file instead |
| "Google no longer accepts your saved connection" | You removed it in your Google account, or Google's testing mode ended it (7 days) | Press Connect with Google again; to avoid the 7-day limit set the Google app to "In production" |
| Tests are skipped | The data file or Ollama or Playwright is missing | The skip reason says which; install it or ignore |
| Hindi or Tamil title shows a yellow warning | The model is weak on those scripts (R² about 0.02) | Trust category and timing, not the title forecast |
