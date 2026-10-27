# Signal Studio: forecast a YouTube video before you publish it

Signal Studio forecasts the **views** and **engagement rate** of a proposed YouTube video from its title, tags, description, category and publish time. It then explains the forecast, shows how sure it is, and suggests what to change. If you add your own earlier videos, it forecasts relative to **your** channel.

Live site: https://youtube-strategy-predictor.onrender.com (free hosting: the first load after a quiet period can take 30 to 60 seconds).

> **Scope.** The model learned from videos that reached India's Trending list (2017-2018). It estimates performance *relative to trending videos*; it cannot say whether an ordinary upload will trend, and it cannot see thumbnails, retention or YouTube's ranking signals.

**New here? Read [docs/PROJECT_GUIDE.md](docs/PROJECT_GUIDE.md)**: how to run everything, every command, and what each file does.

## Run it

Needs Python 3.10+ and git.

```powershell
git clone https://github.com/NiksheyYadav/youtube-strategy-prediction.git
cd youtube-strategy-prediction
.\run.ps1            # Windows (or double-click run.bat)
./run.sh             # macOS / Linux
```

The launcher creates a virtual environment, installs the pinned packages, offers to install a local language model for the AI coach, and opens http://localhost:8501. The app is reachable only from your own computer unless you pass `--lan`. Flags: `--check` (preview, change nothing), `--yes`, `--no-llm`, `--no-browser`, `--port N`, `--model NAME`.

## What you can do

| Tab | What it gives you |
| --- | --- |
| **Forecast studio** | Expected views and engagement with an 80% range, the draft's place among trending videos, the reasons behind the forecast (exact Shapley values over five groups of choices), a keyword radar and a downloadable strategy brief |
| **My channel** | Upload a YouTube Studio export or sign in with Google (read-only, read once, access cancelled straight away). Forecasts then start from your own usual views |
| **Best time** | The draft scored in all 168 weekly slots |
| **Title lab** | Honest edits (a number, a question, a hashtag...) re-scored by the model; one click applies one |
| **AI coach** | Advice written by a language model on your own computer, checked against the evidence; rule-based advice when no model is installed |
| **Similar videos** | Real look-alike trending videos, compared with the forecast |
| **Scenario lab** | Draft A against Draft B, and other categories |
| **YouTube timeline** | Sourced, dated changes to how YouTube recommends and counts videos (public statements, not a secret formula) |
| **Model brief** | The honest accuracy numbers and the limits |

## How accurate is it?

Measured on 16,307 training videos, three ways. The first is the honest one: it tests on channels the model never saw while learning, which is what a new creator gets.

| Test | Log-views R² | Engagement R² |
| --- | ---: | ---: |
| **Channels never seen in training** | **0.19** | **0.38** |
| Later uploads (train on earlier, test on later) | 0.38 | 0.55 |
| Shuffled 5-fold (same channel on both sides; flatters the model) | 0.43 | 0.64 |
| **With your own history** (second model, unseen channels) | **0.57** | **0.72** |

R² is the share of the spread in results that the model explains (1.0 perfect, 0 = no better than the average). Titles in Hindi, Tamil, Telugu and other non-Latin scripts get a views R² near 0, and the app says so. The 80% ranges are calibrated on unseen channels; an interval is wide (a views forecast is typically within a factor of about 0.2 to 4.6), which is the honest answer when pre-publish metadata is only a moderate signal. All of these numbers are saved in the model file and read by the app.

## Honest design choices

- **No look-ahead:** an earlier video only counts as history for a new one if its views were already known when the new one was published.
- **No leakage:** views, likes, comments, channel and video ID are never inputs (likes and comments only build the engagement target; videos with ratings or comments switched off are left out of that target).
- **Private by default:** your data lives in memory for the browser session only. It is not written to disk or logs.
- **No pretend model:** the language model is real and local, or absent; the app says which.

## Tests

```powershell
.\venv\Scripts\python.exe -m pytest -q -p no:cacheprovider      # everything, including real-browser tests
.\venv\Scripts\python.exe -m pytest -q -m "not browser"         # without the browser tests
```

They cover the feature code, the training run on real data, the intervals, the Google sign-in protocol, the upload parser, the AI coach's safety checks, headless runs of the app, and real Chrome driving the real app. Install the extras with `pip install -r requirements-dev.txt`. Tests that need the dataset or a local language model skip themselves with a stated reason when it is missing. GitHub Actions runs the tests that need neither.

## Retrain

Put the Kaggle India files in `data/`, then:

```powershell
.\venv\Scripts\python.exe src\clean.py
.\venv\Scripts\python.exe src\advanced_model.py --train     # the model the app uses
.\venv\Scripts\python.exe -m src.history_model --train      # the "your own history" model
.\venv\Scripts\python.exe -m src.golden --record            # only after a deliberate model change
```

## Layout

See the file map in [docs/PROJECT_GUIDE.md](docs/PROJECT_GUIDE.md#8-file-map). In short: `app.py` is the app, `src/` the code, `models/` the trained models, `reports/` the measured results, `tests/` the checks, `knowledge/` the sourced YouTube timeline, `deliverables/` the report and slides.

## Data and credits

Training data: Kaggle *Trending YouTube Video Statistics* (India file). To connect a channel see [docs/CONNECT_YOUTUBE.md](docs/CONNECT_YOUTUBE.md). Student project by Nikshey Yadav.
