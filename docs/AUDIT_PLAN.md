# Audit plan: what I found when I tried to break the project

*This document is for you, not for your evaluation. It is written before any fixes, so you can see what was wrong and what I intend to do. A second document, `AUDIT_REPORT.md`, records what was actually fixed and re-tested.*

Date of audit: 27 October 2026. Code audited: commit `99bb1a9` (6 commits ahead of what is on GitHub).

## 1. How I tried to break it

| Method | What it covered |
| --- | --- |
| Real Chrome driven by Playwright | Every tab, hostile titles (script tags, emoji floods, Hindi, right-to-left), rapid clicking, reload, phone screen, real file uploads (**your real Studio export, zip and csv**), a second visitor, the real AI model, downloads |
| Fresh clone in a folder with spaces | `git clone` into `C:\tmp_audit\path with spaces`, then the one-command launcher on a clean machine state |
| Fuzzing | About 90 hostile inputs against prediction, the upload parser and the personalised forecast |
| Mutation test | Broke 15 important behaviours on purpose (one at a time, on a throw-away copy) to see if the tests notice |
| Data audit | Cleaned dataset checked for rows that would quietly distort the model; accuracy measured per segment |
| Rebuild from raw data | Re-ran cleaning and full training in a throw-away copy and compared with the committed results |
| Static checks | Coverage, unused code, dependency vulnerabilities (pip-audit), secrets in git history, accessibility (axe-core), security headers |
| Hosting | GitHub Actions history, Render deploy events, live-site response times |

## 2. What is fine (I tried hard and could not break it)

- No crash in about 90 hostile inputs; nothing slower than 2 seconds.
- No script from a hostile title or upload ever ran in the browser.
- Two visitors never see each other's data.
- Your real zipped export, `Table data.csv` and `Chart data.csv` all load correctly (5 videos from 8 rows: one "Total" row and one blank row are skipped, as designed).
- A fresh clone installs and runs with the one command, even in a path with spaces.
- **The model is reproducible.** Cleaning the raw data reproduces the saved `clean.csv` exactly, and a full retrain from raw data in a throw-away copy gave **identical results**: all 12 saved metrics match, and predictions agree with the committed model to 1e-14.
- No secrets anywhere in git history.
- No colour-contrast problems on the dark theme.
- The real local AI model works end to end (43 to 118 seconds depending on machine load).

*One suspected bug turned out not to be one:* the first zip upload in my browser test seemed to do nothing. Re-testing with proper waits showed it works in 1.3 seconds. It was my test reading the page too early.

## 3. Findings, most important first

Severity: **High** = could hurt your evaluation or mislead a user. **Medium** = real problem, limited impact. **Low** = polish.

### A. Mock, fake and placeholder pieces in the product (your main concern)

| # | Severity | Problem | Evidence |
| --- | --- | --- | --- |
| A1 | High | **"Try the sample channel"** loads a made-up channel of 26 invented videos. | `app.py`, `sample_data/`, `scripts/make_sample_channel.py` |
| A2 | High | The Title lab edit **"Link to your channel"** inserts the literal text `https://www.youtube.com/@yourchannel` into a real description when the user clicks Apply. | `src/insights.py` line 289 |
| A3 | High | Other Title lab edits **invent content**: "- Part 1" (a series that does not exist), "Latest:" (fake freshness), and "How to" glued onto a lower-cased title ("How to study tips for students"). The AI coach then promotes these as top priorities. | `src/insights.py`; seen in the real coach output |
| A4 | Medium | The built-in example drafts are invented (for example "Neon Nights" with a link to `example.com`). | `app.py` `EXAMPLES` |
| A5 | Medium | The tests of Google sign-in and the YouTube reader use a **simulated Google/YouTube**, and the model tests use **synthetic channels**. They are not shipped, but nothing tests those paths for real. | `tests/` |

### B. Claims that are wrong or misleading

| # | Severity | Problem | Evidence |
| --- | --- | --- | --- |
| B1 | High | The headline accuracy (R² 0.42 views, 0.64 engagement; "explains 38%") comes from tests where the **same channels are in both training and test data**. For a channel the model has never seen: **0.18 views, 0.34 engagement**. This number is in the app sidebar, the Model brief tab, README, `reports/insights.md`, the report, notes and deck. | Group-by-channel test, measured twice |
| B2 | High | The **"80% interval" is only 80% on average.** Per category it holds for 50% of Gaming videos, 68% of Music, 74% of Autos, but 93% of Education and 96% of Shows. The lowest-forecast fifth is covered 88%, the highest fifth 77%. | Out-of-fold test per segment |
| B3 | Medium | README is stale: says "33 tests, ~30 s" (it is 249 and about 4 minutes), "7 views" (9), that channel history is missing (it now exists), and describes the wrong files for deployment. | README |
| B4 | Medium | The **keep-warm job does not keep the site warm.** GitHub starts it every 3 to 5 hours, not every 10 minutes. The live site took **33 seconds** to answer, and 2 of 3 recent runs hit HTTP 502 while the site was waking. | `gh run list`, curl |
| B5 | Low | A forecast for a one-character title looks perfectly normal (138K views). | Browser test |

### C. Data and model defects

| # | Severity | Problem | Evidence |
| --- | --- | --- | --- |
| C1 | High | **Engagement target is corrupted for videos with ratings turned off.** 407 videos (2.5%) have likes stored as 0, so their engagement is about 0 (median 0.0000 against 0.0086 for others); 217 are exactly 0. The model learns from these. | `data/processed/clean.csv` |
| C2 | High | **Hindi and other non-Latin titles are mis-read.** They are 13.8% of the data (2,245 videos). The word counter only sees A to Z, so a Hindi title counts as **0 words**. For 984 titles the keyword and look-alike tools find nothing. Accuracy on these titles is **R² 0.10 against 0.44** for Latin-script titles. For an India-focused tool this is a large blind spot. | Feature check, per-segment accuracy |
| C3 | Medium | History is accepted even when it is impossible: a video dated 5 years in the future, one dated 1900, and `1e30` views (which gives an absurd forecast). | Fuzz test |
| C4 | Medium | The history model was learned from videos that trended. How well it transfers to ordinary, small channels is **untested**. Your own channel (5 videos, median 14 views) gets a plausible forecast, but plausible is not verified. | Design limit |
| C5 | Low | Slash dates such as `02/03/2024` are read month-first; many Indian users write day-first. Studio's own format (`Mar 24, 2025`) is unaffected. | Parser |

### D. Security and hardening

| # | Severity | Problem | Evidence |
| --- | --- | --- | --- |
| D1 | High | **`enableCORS = false`** in the Streamlit config makes the app accept connections **from any website** and send `Access-Control-Allow-Origin: *` (Streamlit prints a warning for it). | `.streamlit/config.toml`, startup log |
| D2 | Medium | The launcher serves on **all network interfaces**, so anyone on the same Wi-Fi (college network, hotspot) can open your app and use your local AI model. | Startup shows a "Network URL" |
| D3 | Low | `pillow 12.3.0` has 25 published advisories (fixed in 13.0.0). Streamlit 1.65 forbids pillow 13, Streamlit 1.66.1 allows it. The app never decodes user images, so it is not reachable today. | `pip-audit` |
| D4 | Low | The hosted site sends no anti-framing or content-security headers (a Render limit). | `curl -I` |

### E. Reliability and usability

| # | Severity | Problem | Evidence |
| --- | --- | --- | --- |
| E1 | High | **On a phone-sized screen the sidebar opens over the whole page and blocks every tab click** until the user finds the tiny close arrow. | Playwright at 390 px |
| E2 | Medium | **Scenario lab: Draft B goes stale.** After loading another example, Draft A changes but Draft B still holds the old draft. | Browser test |
| E3 | Medium | The **Dockerfile** copies only the two old model files, so a Docker build would lose the history model and the knowledge base. It has never been built (Docker is switched off here). | `Dockerfile` |
| E4 | Medium | If the port is busy the launcher only says "Port 8601 is not available" and exits. | Fresh-clone test |
| E5 | Low | `run.ps1` can pick the Microsoft Store "python" stub on some Windows machines instead of trying `py`. | Code read |
| E6 | Low | Upload errors use internal names ("Missing columns: title, publish_time"). | Browser test |
| E7 | Low | Memory use is about 307 MB after heavy use. Render's free tier has 512 MB, so several simultaneous users could be a problem. | Process measurement |

### F. Gaps in the tests

| # | Severity | Problem | Evidence |
| --- | --- | --- | --- |
| F1 | High | **The training pipeline has no tests** (`clean.py`, `features.py`, `train.py`, `evaluate.py`, most of `advanced_model.py` training and the calibration builders show 0 to 48% coverage). If retraining silently broke, nothing would notice. | Coverage report |
| F2 | Medium | Mutation test: **my PKCE test is circular** (it checks the code against the same function it tests), and **nothing tests the publish-hour check**. 13 of 15 deliberate breakages were caught. | Mutation run |
| F3 | Medium | There are **no real-browser tests** in the repository; `app.py` itself is outside the coverage measurement. | Repo |

### G. Housekeeping

| # | Severity | Problem |
| --- | --- | --- |
| G1 | Low | Four modules are an unused parallel pipeline (`advanced_features`, `advanced_train`, `advanced_evaluate`, `model_contract`) that the README still describes. |
| G2 | Low | The two 35 MB pickles in `models/` are the Stage 4 deliverables from your brief. The app uses the newer bundle. They are **kept**, but should be documented as such. |
| G3 | Low | No LICENSE file; the report, notes and deck still quote old numbers (133 tests, the old R², no new features). |

## 4. The plan

I will work in this order, committing after each phase and re-running the full test suite (gated on its real exit code).

**Phase 1: remove everything fake, close the security gaps, fix the quick UX bugs**
1. Delete the sample channel (A1): button, `sample_data/`, generator script, its tests.
2. Remove the placeholder-link edit and the three content-inventing edits (A2, A3); keep only honest edits (question mark, case, shorten, hashtags, call to action, tag keywords). Check the AI coach no longer promotes them.
3. Replace the invented example drafts with **real videos from the dataset**, labelled as such, showing what really happened (A4).
4. Security: `enableCORS` on (D1); launcher binds to this computer only, with an explicit `--lan` switch (D2).
5. Phone sidebar starts collapsed (E1); Draft B follows Draft A unless the user edited it (E2); friendly upload messages (E6); helpful busy-port handling (E4); `py` fallback in `run.ps1` (E5).
6. Validation of impossible history (C3). Fix the Dockerfile (E3). Try to start Docker and build it for real.

**Phase 2: fix the model and the numbers (retrain)**
7. Exclude ratings-disabled videos from the engagement target (C1).
8. Unicode-aware word handling plus a script feature, then retrain, and measure Hindi/regional titles before and after (C2).
9. Per-category interval calibration, with coverage measured per category (B2).
10. Compute the **unseen-channel accuracy inside the training script**, store it, and have the app, README and reports read it instead of hard-coding old numbers (B1). Add a plain warning that the forecast is relative to *trending* videos, and a "title too short" warning (B5).
11. Re-record the golden snapshot deliberately, with the reason written down.

**Phase 3: real tests**
12. Fix the circular PKCE test and add range-check tests (F2).
13. Add tests for the training pipeline using a **real 500-row sample** of the real data (F1), skipped only when the data is absent.
14. Add a real-browser suite to the repository (Playwright, real Chrome, real model when available, your own real export when you point it at one) (F3).
15. Replace synthetic and simulated test inputs with real data wherever real data is possible. For Google sign-in a real test needs **your** Google account, so the simulated-protocol tests stay, clearly labelled, and a manual checklist covers the real thing (A5).
16. Try Streamlit 1.66.1 with pillow 13 and keep it only if everything still passes (D3).

**Phase 4: documents**
17. Rewrite the README and write `PROJECT_GUIDE.md` (how to run each command, what each file does) (B3, G1, G2).
18. Keep-warm: state honestly what it does, and give you the steps for a free external pinger (needs your account) (B4).
19. Write `AUDIT_REPORT.md`: what was fixed, what was re-tested and how, what is still open.

## 5. What I cannot do for you

- **Real Google sign-in test:** needs your Google account and Google Cloud client.
- **Newer Kaggle data (2020 onward):** Claude in Chrome is still not connected; or download the file yourself.
- **External pinger for the live site:** needs an account in your name.
- **Pushing:** I will not push or redeploy until you say so. Phase 1 and 2 change the app, so deployment should be a deliberate step.

## 6. Decisions I made for you (tell me if you disagree)

- **Test code is not "mock data in the product".** I kept unit tests (they are what stop regressions) but removed anything fake from what the app shows and does. If you want even the simulated Google tests removed, say so.
- **The two 35 MB pickles stay**, because your brief asked for them.
- I used your real Studio export **only on this computer**, to test uploads. Nothing from it is stored or committed, and the audit documents contain no titles from it.
