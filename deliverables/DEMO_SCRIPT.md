# 4-Minute Walkthrough

**Before you start:** open https://youtube-strategy-predictor.onrender.com a minute early (free hosting sleeps when idle), or run `.\run.ps1` locally. Have a real draft title ready (or one of your own videos).

1. **Frame it.** "This app gives a pre-publication forecast. It only sees what a creator controls before uploading, and it tells you how sure it is."
2. **Write a draft.** Type the title (add tags and a description if you have them), choose the category and the publish time. Mention in the sidebar that the model learned from 16,307 India-trending videos and that the accuracy numbers come from channels it never saw (views R² 0.19, engagement R² 0.38).
3. **Forecast studio.** Press **Generate pre-publication forecast**. Point to the expected views with the **80 % interval** and say: "These intervals are calibrated on channels the model had not seen, and they were checked on later uploads." Show the percentile card and read the note that these numbers compare the draft with trending videos.
4. **Why this forecast.** Read the bar chart: "These are exact Shapley values. We reveal title, tags, description, timing and category in every order and average each group's effect; they add up to forecast minus a typical video." Category is usually the largest bar and is not editable.
5. **My channel.** Upload a YouTube Studio export (or sign in with Google), return to the studio and show **Expected views for your channel**. "With a creator's own history the model reaches R² 0.57 on channels it never saw." Press **Remove my data** to show nothing was kept.
6. **Best time.** Open the heatmap: "The same draft in all 168 weekly slots." Press **Use this slot** on the best one; the swing is modest, so content matters more than timing.
7. **Title lab and AI coach.** Show the ranked edits, press **Apply** on the top one and watch the forecast move: "associations the model learned, not guarantees." Then the AI coach: the language model only writes the advice; every number comes from the trained model.
8. **Similar videos and Scenario lab.** "A completely different method, TF-IDF look-alikes, as a second opinion." Then Draft A against Draft B and the overlap message: most small edits fall inside the model's uncertainty.
9. **Model brief.** Show the three accuracy tests (unseen channels, later uploads, shuffled) and say why the first one is the honest one.
10. **Close with the limit.** "The data only contains videos that already trended in India (2017-2018). It cannot decide whether an arbitrary upload will go viral, and for titles in Hindi or other scripts the forecast is weak; the app says so."
