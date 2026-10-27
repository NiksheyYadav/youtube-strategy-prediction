# Audit report: what was found, what was fixed, how it was re-tested

*This is for you, not for your evaluation. It follows [AUDIT_PLAN.md](AUDIT_PLAN.md) item by item (same numbers). Dates: audit 27 October 2026.*

**Result in one paragraph.** Nothing fake is left in the product. The headline accuracy was overstated (0.42 / 0.64) and is now the honest 0.19 / 0.38 for a new channel, read from the model file instead of typed in. Every high-severity finding is fixed and re-tested, most of them in a real browser. Eight things are still open and need you (section 4). Nothing has been pushed: the live website still runs the old code.

## 1. Status of every finding

**Fixed and re-tested** = I changed it and a test or a real-browser run now proves it. **Documented** = it cannot be fixed, so the app or the guide now says so.

### A. Fake or placeholder pieces

| # | Status | What happened |
| --- | --- | --- |
| A1 | Fixed | The made-up sample channel (26 invented videos), its button, files and tests are gone |
| A2 | Fixed | The edit that inserted `https://www.youtube.com/@yourchannel` is gone |
| A3 | Fixed | The edits that invented "- Part 1", "Latest:" and a broken "How to ..." are gone; the AI coach no longer promotes them |
| A4 | Fixed, then removed | I first replaced the invented examples with four real videos. You then asked for the loader to go entirely, so the form now **starts empty** and every tab says "Start with your draft". No example loader, no pre-filled video, no "demo" or "viva" wording, no Deploy button. The four real videos now live only in the tests as realistic drafts |
| A5 | Partly open | Tests of Google sign-in and the YouTube reader still use a **simulated** Google (they check the protocol: PKCE, one-time state, the access being cancelled). A real test needs **your** Google account. The model and upload tests now use real channels and real videos from the data (and, optionally, your own export via `SIGNAL_STUDIO_EXPORT`) |

### B. Wrong or misleading claims

| # | Status | What happened |
| --- | --- | --- |
| B1 | Fixed in the app, **open in the documents** | Training now measures accuracy on channels it never saw and stores it in the model. The sidebar, Model brief, README, guide, summary and viva answers read or quote it. The **Word report, notes and slide deck still contain the old numbers** (section 4) |
| B2 | Improved, not perfect | Eleven categories with 120+ videos get their own interval width. On later uploads the old single width covered 69% to 97% by category; the new widths cover 78% to 97%, a small average gain. Gaming has 20 videos and a few others are tiny, so they keep the overall width and the app says so |
| B3 | Fixed | README rewritten; new [PROJECT_GUIDE.md](PROJECT_GUIDE.md) |
| B4 | Documented | The GitHub keep-warm job is best-effort and unreliable. The guide says so and gives the steps for a free outside pinger (needs your account) |
| B5 | Fixed | Warnings for one- and two-word titles, titles mostly in non-Latin scripts, and categories too small for their own interval; a note that forecasts are relative to trending videos |

### C. Data and model

| # | Status | What happened |
| --- | --- | --- |
| C1 | Fixed | 782 videos (4.8%) with ratings or comments switched off are left out of the engagement model (they still count for views) |
| C2 | Partly fixed | Titles in any script are now read as words and there is a script feature. But the views score for those titles on unseen channels is only **R² 0.02** (it was about 0.10 under the easier test). The model cannot read the meaning of Hindi words; adding word features did not help in my earlier experiment. The app now **warns** instead of pretending |
| C3 | Fixed | Impossible history (future dates, dates before YouTube existed, absurd view counts) is dropped with a note |
| C4 | Open | The history model was learned from trending channels. It is untested on small, non-trending channels. Your own channel gives plausible numbers, which is not proof |
| C5 | Fixed today | Dates such as 25/03/2024 are read day-first, 03/25/2024 month-first. If every date could be either, they are read month-first **and the app tells you** |

### D. Security

| # | Status | What happened |
| --- | --- | --- |
| D1 | Fixed | `enableCORS=false` removed. Proof: a page on another website could open a connection to the old setting and is refused by the new one |
| D2 | Fixed | The app listens on this computer only; `--lan` is an explicit switch |
| D3 | Open (blocked) | pillow 12.3.0 advisories: the trial of Streamlit 1.66.1 with pillow 13 |
| D4 | Documented | Render's free plan does not let us add security headers |

### E. Reliability and usability

| # | Status | What happened |
| --- | --- | --- |
| E1 | Fixed | The sidebar starts closed on a phone; checked in real Chrome at 390 px (no sideways scroll) |
| E2 | Fixed | Draft B follows Draft A until you edit it |
| E3 | Fixed, **not built** | The Dockerfile now copies the history model, knowledge base and config, and a test checks it. Docker's engine is switched off on this computer, so a real build has never run |
| E4, E5, E6 | Fixed | Helpful busy-port message; `py` fallback in `run.ps1`; plain upload error messages |
| E7 | Open | About 300 MB of memory after heavy use against Render's 512 MB limit |
| E8 | Fixed | Your reported crash (`unexpected=['title_non_latin_share']`): the code gained a feature while the saved model did not have it, and a running app kept the old model in memory. Now the loader refuses a mismatch with a plain message and the retrain command, and every model cache follows the file's modification time. A test reproduces your exact failure |

### F. Gaps in the tests

| # | Status | What happened |
| --- | --- | --- |
| F1 | Fixed | New `tests/test_training_pipeline.py` runs the training on 700 real videos and checks the shipped model's reported accuracy, data-quality counts, script handling and interval widths |
| F2 | Fixed | The PKCE test is independent (the RFC 7636 test vector) and the publish-hour range is tested; I re-ran the deliberate-breakage test and both were caught |
| F3 | Fixed | `tests/e2e/` drives the real app in real Chrome (see section 2) |

### G. Housekeeping

| # | Status | What happened |
| --- | --- | --- |
| G1 | Documented | Four unused modules are kept (they were part of the course work) and labelled as such in the guide |
| G2 | Documented | The two 35 MB `.pkl` files are your stage-4 deliverables, kept and labelled |
| G3 | Open | No LICENSE file yet: you must choose the licence (MIT is the common choice). The documents are not refreshed (section 4) |

## 2. New problems found while fixing (not in the first plan)

| Problem | Found by | Fixed |
| --- | --- | --- |
| **"Remove my data" did not remove an uploaded file.** It forgot the channel but not the file, so the next rerun silently loaded it again. This matters because the app promises that removal forgets your data | The new real-browser test (the headless test has no upload box and could not see it) | Yes: removal now resets the upload box too |
| Training run as a plain script saved the word splitter under the wrong module name, so the app could not load the look-alike index | The full test suite | Yes, plus a test that loads it in a clean process |
| One interval test was written as "must be 74% to 86%" and treated too-wide like too-narrow. After the intervals were calibrated on harder (unseen) channels, later uploads were covered 88%, which is safe, not a defect | The full test suite | I rewrote the test to demand "never under-covered, never absurdly wide" and wrote the reason into it |

## 3. Numbers, before and after

| Measure | Before | After |
| --- | ---: | ---: |
| Views R², headline | 0.42 (shuffled CV) | **0.19** (channels never seen) |
| Engagement R², headline | 0.64 (shuffled CV) | **0.38** (channels never seen) |
| Later uploads, views / engagement | 0.37 / 0.53 | 0.38 / 0.55 |
| Own-history model, unseen channels, views / engagement | 0.58 / 0.73 | 0.57 / 0.72 (same within noise; cleaner target) |
| Views interval width (overall) | x0.29 to x3.5 | x0.22 to x4.6 (wider because it is now calibrated on harder cases) |
| Videos used for engagement | 16,307 | 15,525 |
| Tests | 249 | 313 (312 pass; 1 optional test skips unless you point it at your own Studio export) |

The accuracy numbers got *lower*, not because the model got worse but because the test got honest. The model itself is unchanged apart from the engagement clean-up and one new feature.

**Streamlit 1.66.1 with pillow 13 (D3):** tried in a throw-away environment and **blocked**: Streamlit 1.66.x requires Python 3.11 or newer, and the project (this computer's setup, CI, Render, Docker) is on Python 3.10, so pillow 13 cannot be installed with it. The advisories are low risk because the app never opens user-supplied images. Moving the whole project to Python 3.11 would fix it but means changing Render, Docker, CI and the pinned packages and retesting everything; that is your decision (section 4, item 7).

## 4. What still needs you

1. **Choose a licence** for the repository (G3), or tell me to use MIT.
2. **Refresh the Word report, notes and slide deck.** They are generated by scripts in `deliverables/` and still contain the old R² (0.42 / 0.64), the old test count and none of the new features. The summary text, viva answers and walkthrough script are already updated. Say the word and I will regenerate them in your agreed format (no cover page, footer with your name and number, black Times New Roman, justified, simple words).
3. **Push and deploy.** About 15 commits are local only. The live website is the old version until you tell me to push (a push triggers an automatic Render deploy).
4. **A real Google sign-in test (A5):** needs your Google account and a Google Cloud client (steps in CONNECT_YOUTUBE.md). Until then the protocol is tested against a simulated Google only.
5. **An outside pinger** for the live site (UptimeRobot, free, needs your account) (B4).
6. **Docker** (E3): start Docker Desktop and I will run the real build.
7. **Python version (D3):** moving to Python 3.11 would allow the pillow security update (see section 3). Optional; low risk today.
8. **The Illinois dataset** (you chose to skip it): one 26.4 GB archive for 104 countries (licence CC BY, no likes column). Worth revisiting only if you want a check of how the model ages on 2022-25 videos.

## 5. How I tested

- **Real Chrome driving the real app**, started the way a user starts it: first visit, a written draft, all nine tabs, hostile titles (script tags, markdown links, emoji floods, right-to-left override), a Hindi title, a phone-sized screen, a rejected fake CSV, a real creator's file from the data (upload, personalised forecast, removal, a second visitor seeing nothing), and the strategy-brief download. These are `tests/e2e/` and run with the rest of the tests.
- **Headless runs** of the app for every tab and button, with real videos as drafts.
- **Training on real data:** the full pipeline on a 700-video sample, and the full retrain on all 16,307 videos (twice, to check it is repeatable).
- **Deliberate breakage:** 15 important behaviours broken one at a time on a throw-away copy; all are now caught.
- **Fuzzing, reproducibility and a fresh clone** in a folder with spaces, as listed in the plan.

Everything in `tests/` that involves the model, the data or the browser is real. The only simulated parts are Google's servers (see A5) and the two deliberately damaged model files used to prove the mismatch message.
