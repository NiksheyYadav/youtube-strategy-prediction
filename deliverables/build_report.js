// Builds Project_Report_Experiments_8_9_10.docx  (run: node build_report.js)
const L = require('./lib_docx');
const K = L.kit({ font: 'Times New Roman', size: 24, accent: '1A2B4C', dark: '1F2937' });
const { p, heading: h, bullets, numbered, figure, callout, table, gap, pageBreak } = K;
const runsInfo = (() => { try { return JSON.parse(L.fs.readFileSync(L.path.join(L.ASSETS, 'ai_coach_runs.json'), 'utf8')); } catch { return null; } })();
const testsTotal = (() => { try { return JSON.parse(L.fs.readFileSync(L.path.join(L.ASSETS, 'diagrams', 'tests_total.json'), 'utf8')).total; } catch { return 131; } })();
const D = (f) => `diagrams/${f}.png`;
const S = (f) => `screens/parts/${f}.png`;

function experimentHeader(no, title, aim, tools) {
  return [
    new L.Paragraph({ alignment: L.AlignmentType.CENTER, spacing: { before: 0, after: 80 }, children: [new L.TextRun({ text: `EXPERIMENT ${no}`, bold: true, size: 40, font: 'Times New Roman', color: '1A2B4C' })] }),
    new L.Paragraph({ alignment: L.AlignmentType.CENTER, spacing: { after: 200 }, children: [new L.TextRun({ text: title, bold: true, size: 30, font: 'Times New Roman' })] }),
    table(['Item', 'Details'], [['Project', 'AI-Based YouTube Analytics and Content Strategy Prediction (Signal Studio)'], ['Aim', aim], ['Tools used', tools]], [1.2, 5]),
    gap(160),
  ];
}

const children = [];

// ------------------------------------------------------------------ cover
children.push(
  gap(1400),
  new L.Paragraph({ alignment: L.AlignmentType.CENTER, spacing: { after: 100 }, children: [new L.TextRun({ text: 'SGT UNIVERSITY', bold: true, size: 32, font: 'Times New Roman', color: '1A2B4C' })] }),
  p('Department of Computer Science & Engineering, SOET', { align: L.AlignmentType.CENTER, after: 600 }),
  new L.Paragraph({ alignment: L.AlignmentType.CENTER, spacing: { after: 200 }, children: [new L.TextRun({ text: 'AI-Based YouTube Analytics and Content Strategy Prediction', bold: true, size: 44, font: 'Times New Roman' })] }),
  p('AI & ML Thematic Assessment: Project Report', { align: L.AlignmentType.CENTER, after: 120, run: { size: 28, color: '0E9F6E' } }),
  p('Experiments 8, 9 and 10', { align: L.AlignmentType.CENTER, after: 500, run: { size: 28, bold: true } }),
  table(['Experiment', 'Content'], [
    ['Experiment 8', 'Introduction and literature review'],
    ['Experiment 9', 'Methodology and applications'],
    ['Experiment 10', 'Results, screenshots and conclusion'],
  ], [1.4, 4]),
  gap(500),
  table(['Team member', 'Roll number'], [
    ['Vishal Kumar Upadhyay', '231302157'], ['Nikshey Yadav', '231302221'], ['Aditya Chauhan', '231302230'],
    ['Arpit Gupta', '231302216'], ['Yuvraj Singh Yadav', '231302221'],
  ], [3, 2]),
  gap(400),
  p('October 2026', { align: L.AlignmentType.CENTER }),
  pageBreak(),
);

// ------------------------------------------------------------------ Experiment 8
children.push(...experimentHeader(8, 'Introduction and Literature Review',
  'To understand the problem of predicting YouTube video performance before publication, to define the objectives and scope of the project, and to review the existing research that this work builds on.',
  'Kaggle dataset (Trending YouTube Video Statistics, India), research papers, Python.'));

children.push(
  h(1, '8.1 Introduction'),
  p('Millions of people create videos for YouTube. Before a video is published, the creator makes a set of decisions: the **title**, the **tags**, the **description**, the **category** and the **day and time** of publishing. The results of these decisions (views, likes, comments) are visible only after the video is live, when it is too late to change the early impression it makes. A creator therefore has to guess which choices will work.'),
  p('This project asks a simple question: **can a machine learning model estimate how a video will perform using only information that is known before publishing, and can it explain its estimate in a way a creator can act on?** We built a working system, called **Signal Studio**, that predicts the likely number of views and the engagement rate of a proposed video, explains which of the creator\'s choices push the estimate up or down, tells the creator how uncertain the estimate is, and finally writes short, evidence-based suggestions using a language model that runs on the user\'s own computer.'),
  h(1, '8.2 Problem statement'),
  callout('Problem statement', 'Given only what a creator knows before uploading (title, tags, description, category and planned publishing time), estimate (a) the number of views and (b) the engagement rate of the video, explain the estimate, state how uncertain it is, and suggest improvements, without using any information that only exists after publishing.'),
  gap(100),
  h(1, '8.3 Objectives'),
  ...numbered([
    'Collect and clean a real dataset of YouTube videos and remove the repetition it contains.',
    'Create input features that are available before publishing and keep the outcomes (likes, comments) strictly as targets.',
    'Train and compare machine learning models (Linear Regression, Random Forest, XGBoost) and evaluate them honestly, including on later-in-time videos.',
    'Explain each prediction in plain terms and measure how uncertain it is.',
    'Convert the model\'s findings into practical advice using a local language model, without allowing the language model to invent numbers.',
    'Package the project so that it can be installed and run on any laptop with one command, and put a version online.',
  ]),
  h(1, '8.4 Scope and dataset'),
  p('The project uses the public Kaggle dataset **Trending YouTube Video Statistics** [16], India file. Each row is one video on one day on which it appeared on India\'s Trending list. The same video can therefore appear on several rows.'),
  table(['Property', 'Value'], [
    ['Source', 'Kaggle, Trending YouTube Video Statistics (INvideos.csv), data from 2017-2018'],
    ['Raw rows', '37,352 (one per video per trending day)'],
    ['Unique videos after cleaning', '16,307 (latest trending snapshot of each video)'],
    ['Inputs used (known before publishing)', 'Title, tags, description, category, publishing day and hour (converted to Indian Standard Time)'],
    ['Targets (what is predicted)', 'Views (log scale) and engagement rate = (likes + comments) / views'],
    ['Never used as inputs', 'Likes, dislikes, comment count, views, channel details, video ID'],
    ['Important limitation', 'Only videos that already trended are present, so the project estimates relative performance among trending videos. It does not claim to predict whether any upload will go viral.'],
  ], [2, 4.2]),
  gap(),
  ...figure(D('funnel'), 4.6, 'Figure 8.1: The raw data contains one row per video per day; keeping each video once gives 16,307 unique videos.'),

  h(1, '8.5 Literature review'),
  h(2, '8.5.1 Popularity of online videos'),
  p('Early measurement work by Cha et al. [1] studied YouTube at large scale and showed that video popularity is highly skewed: a small number of videos receive most of the views. This skew is the reason we model views on a logarithmic scale. Szabo and Huberman [2] showed that the long-term popularity of online content can be predicted from its early popularity, and Figueiredo et al. [3] characterised how the popularity of YouTube videos grows over time. Pinto et al. [4] used the early view pattern of a video to predict its later popularity. These studies are valuable but all of them need **observations made after the video is published** (early views). Our project deliberately works one step earlier: it uses only the metadata a creator can still change.'),
  h(2, '8.5.2 Tree-based models for tabular data'),
  p('Random Forests [5] combine many decision trees trained on random samples of the data and average their answers, which reduces over-fitting and handles non-linear relationships between inputs. Gradient-boosted trees such as XGBoost [6] build trees one after another, each correcting the previous errors. Both are standard choices for tabular data. We implemented the models with scikit-learn [7] and compared them with a Linear Regression baseline. In our experiments the Random Forest gave the best results on both targets.'),
  h(2, '8.5.3 Explaining model predictions'),
  p('The Shapley value [8] comes from cooperative game theory: it shares the total gain of a team fairly among its players by averaging each player\'s contribution over every possible order in which the team could be assembled. Lundberg and Lee [9] showed that this idea gives a unified and principled way to explain machine learning predictions (SHAP). We use the same principle but apply it to **five groups of choices** (title, tags, description, timing and category). Because there are only five groups, the exact value can be computed from 2^5 = 32 combinations without approximation.'),
  h(2, '8.5.4 Measuring uncertainty'),
  p('A single predicted number can be misleading. Conformal prediction [10] builds prediction intervals with a statistical coverage guarantee that does not depend on the model type, and Lei et al. [11] describe its split version for regression. In split conformal prediction the model\'s errors on data it did not train on are used to decide how wide the interval must be so that a chosen share (for example 80 percent) of true values falls inside. We use this idea and, importantly, test the promise on later-in-time videos.'),
  h(2, '8.5.5 Text similarity and language models'),
  p('TF-IDF weighting [12] represents a text as a vector in which rare, informative words count more than common ones; the cosine of the angle between two vectors measures how similar two texts are. We use it to find look-alike trending videos. Large language models can write fluent advice but can also produce statements that are not supported by the data, a problem known as hallucination [14]. Retrieval-augmented generation [13] reduces this by giving the model retrieved evidence to work from. Our AI Coach follows the same spirit: it receives a numbered list of facts from the project\'s own model and data, and everything it writes is checked against those facts. The local model family used is Qwen2.5 [15].'),
  h(2, '8.5.6 Summary of related work'),
  table(['Work', 'What it contributes', 'Difference from this project'], [
    ['Cha et al. [1]', 'Large-scale study of YouTube popularity; popularity is very skewed', 'Descriptive study; no prediction from metadata'],
    ['Szabo & Huberman [2]', 'Predicts later popularity from early popularity', 'Needs views after publishing'],
    ['Figueiredo et al. [3]', 'Popularity growth patterns of YouTube videos', 'Studies growth after publishing'],
    ['Pinto et al. [4]', 'Regression on early view patterns', 'Needs early views'],
    ['Breiman [5], Chen & Guestrin [6]', 'Random Forest and XGBoost', 'Used as tools; compared fairly here'],
    ['Lundberg & Lee [9]', 'SHAP explanations', 'We use exact Shapley values over five creator-controlled groups'],
    ['Lei et al. [11]', 'Distribution-free prediction intervals', 'We measure coverage on later-in-time videos'],
    ['Lewis et al. [13]', 'Ground language models in retrieved evidence', 'We add per-sentence evidence checks and a fallback chain, on-device'],
  ], [1.6, 2.4, 2.4]),
  gap(),
  h(1, '8.6 Research gap and contribution'),
  ...bullets([
    '**Gap 1:** earlier popularity predictors need information that exists only after publishing. Creators need help **before** publishing.',
    '**Gap 2:** a predicted number alone does not tell a creator what to change. We add explanations (Shapley), a timing map, edit ranking and look-alike videos.',
    '**Gap 3:** predictions are rarely shown with honest, tested uncertainty. We report intervals whose coverage was measured on later uploads.',
    '**Gap 4:** language models can invent figures. We make the model write only the wording, check every sentence against evidence, and fall back to rules if needed.',
  ]),
  h(1, '8.7 Conclusion of Experiment 8'),
  p('The literature shows that online video popularity can be predicted, but mostly after publication. By restricting inputs to what a creator controls before upload, and by adding explanation, uncertainty and evidence-checked advice, this project addresses a practical gap. Experiment 9 describes the methodology used to build the system.'),
  pageBreak(),
);

// ------------------------------------------------------------------ Experiment 9
children.push(...experimentHeader(9, 'Methodology and Applications',
  'To describe the complete methodology of Signal Studio (data preparation, features, models, evaluation, explanation, uncertainty, AI Coach and deployment) and to identify its practical applications.',
  'Python 3.10, pandas, scikit-learn, XGBoost, matplotlib, Streamlit, Ollama with Qwen2.5 models, git and GitHub Actions, Render.'));

children.push(
  h(1, '9.1 System overview'),
  p('The system is a pipeline of eight steps. Raw data is cleaned, features are engineered, two Random Forest models are trained, they are checked with cross-validation and a later-in-time test, the predictions are explained, everything is wrapped in a web application, and the application is put online. Each step is a real script in the repository and is covered by automated tests.'),
  ...figure(D('pipeline'), 6.5, 'Figure 9.1: The eight-step pipeline of the project.'),
  ...figure(D('architecture'), 6.5, 'Figure 9.2: Architecture: data, ML models, insight tools, AI Coach and the app, supported by tests, CI, hosting and the local AI runtime.'),

  h(1, '9.2 Data preparation'),
  ...numbered([
    '**Parse dates.** The dataset stores trending dates in an unusual text format (year.day.month). They are converted to real dates before sorting, because sorting the raw text would pick the wrong snapshot for some videos.',
    '**Remove repetition.** Rows are sorted by trending date and, for each video ID, only the latest snapshot is kept. This turns 37,352 rows into 16,307 unique videos. No row had to be dropped for missing important values.',
    '**Name the categories.** Numeric category IDs are mapped to names using YouTube\'s category list. The list stores IDs as text while the data stores numbers, so both are converted to text first. Category 29, which is missing from the supplied list, is named "Nonprofits & Activism" from YouTube\'s official list.',
  ]),
  h(1, '9.3 Feature engineering'),
  p('Only information available before publishing is used. The final model has 30 input columns, grouped as follows.'),
  table(['Group', 'Examples of features'], [
    ['Title packaging', 'Length, word count, digits, question and exclamation marks, capital-letter ratio, emoji count, urgency and how-to words, simple sentiment score, lexical diversity'],
    ['Tags', 'Number of tags, total and average tag length, share of multi-word tags (a tag list of "[none]" counts as zero tags)'],
    ['Description', 'Length, word count, number of links, hashtags and call-to-action words'],
    ['Publish timing', 'Day of week and hour in Indian Standard Time, weekend flag, circular hour encoding so that 23:00 is close to 00:00'],
    ['Category', 'Category name (one-hot encoded)'],
  ], [1.4, 4.8]),
  gap(),
  callout('Leakage control', 'Likes, dislikes and comment counts are never used as inputs; likes and comments are used only to compute the engagement-rate **target**. The same feature function is used for training and for the live application, and a test checks the column list.'),
  gap(100),
  p('An audit of the first version found three defects, which were corrected and the model retrained: (1) hashtags and "www." links were never counted because of an escaping mistake in the pattern; (2) training tags kept literal quotation marks that user input never has; (3) category 29 appeared as "Unknown". Regression tests now guard each of them.'),

  h(1, '9.4 Modelling'),
  p('Two targets are predicted: **log(1 + views)** and the **engagement rate**. A Linear Regression is the baseline. Random Forest and XGBoost were compared with 5-fold cross-validation, and the Random Forest was better on both targets. The first Random Forest was over 200 MB because its trees were allowed to grow without limit, so tree depth and leaf size were constrained, shrinking the model by more than 90 percent at a cost of under 3 percentage points of R-squared.'),
  table(['Item', 'Setting'], [
    ['Final model', 'Random Forest Regressor, 180 trees, maximum depth 16, minimum 5 samples per leaf, 80 percent of features per split'],
    ['Models', 'One for log-views, one for engagement rate'],
    ['Metrics', 'R-squared and mean absolute error'],
    ['Evaluation 1', '5-fold cross-validation (data split five ways, tested five times, averaged)'],
    ['Evaluation 2', 'Chronological hold-out: train on the earliest 80 percent of videos and test on the latest 20 percent (harder, more realistic)'],
  ], [1.5, 4.7]),
  gap(),

  h(1, '9.5 Explaining a prediction (Shapley values)'),
  p('To explain why a draft receives its forecast, the five groups of choices are "revealed" one at a time, starting from a typical trending video. The Shapley value of a group is its average effect over all possible orders:'),
  p('phi_i = sum over S not containing i of  [ |S|! (n - |S| - 1)! / n! ] * ( v(S + i) - v(S) )', { align: L.AlignmentType.CENTER, run: { italics: true } }),
  p('where n = 5 groups and v(S) is the model\'s forecast when only the groups in S take the draft\'s values. With five groups this needs only 32 combinations, so the result is exact. The effects add up exactly to (forecast - typical forecast), which is verified by an automated test. The application also provides a keyword radar (median views of trending videos containing each title word, using only words that appear in at least 25 videos from at least 25 different channels so that channel names are excluded).'),

  h(1, '9.6 Measuring uncertainty (split-conformal intervals)'),
  p('The model\'s errors on videos it did not train on (out-of-fold predictions) are collected. For views, the absolute error in log space is used; for engagement the error relative to the prediction size is used. The 80th-percentile error becomes the half-width of the interval, so about 80 percent of true values should fall inside. Because the project then tests this promise on later-in-time videos, the interval is not just an assumption.'),

  h(1, '9.7 Decision tools'),
  ...bullets([
    '**Best-time map:** the same draft is forecast in all 168 weekly slots (7 days x 24 hours, IST); neighbouring hours are averaged so that one noisy slot cannot look like the best time.',
    '**Title lab:** about twelve programmatic edits (add a number, use a question, start with "How to", add hashtags, add a call to action, reuse title words as tags, and so on) are re-scored by the trained model and ranked.',
    '**Similar videos:** TF-IDF similarity over titles and tags finds look-alike trending videos; their median views give an independent second opinion.',
    '**Category what-if and A/B comparison:** the same draft in other categories, or two drafts side by side with an interval-overlap check.',
  ]),

  h(1, '9.8 AI Coach: an on-device language model that cannot change the numbers'),
  p('The AI Coach turns the model\'s numbers into a few prioritised, explained suggestions. Its design has five safety ideas.'),
  ...figure(D('ai_coach_flow'), 6.5, 'Figure 9.3: The AI Coach pipeline and its fallback chain.'),
  ...numbered([
    '**Numbers stay with the ML model.** The language model never produces the forecast. Every number shown, including the effect of any title or tag it proposes, is re-scored by the trained Random Forest.',
    '**Evidence packet.** The model receives only a numbered list of facts (E1, E2, ...) computed by the project\'s own code: the forecast and its interval, percentiles, Shapley effects, ranked edits, keyword statistics, the best time slot and the dataset limitation.',
    '**Hybrid design.** Rules decide what to improve and which evidence supports it. The language model only writes the wording: explanations, new title ideas, tags and description tips.',
    '**Sentence-by-sentence checking.** Each passage is rejected if it quotes a number that is not in the evidence, promises results ("will go viral"), contains links or HTML, or proposes a title that repeats the draft, is mostly capital letters or drifts away from the draft\'s own words. A rejected sentence is dropped alone; the rest is kept.',
    '**Fallback chain.** Main model (with one automatic retry after a formatting failure), then a lite model, then rule-based advice, so the coach always answers. Harmless formatting slips of small models, such as a list of tags returned as one comma-separated string, are repaired before checking.',
  ]),
  ...figure(D('hybrid_design'), 6.0, 'Figure 9.4: Rules decide, the AI writes, the checkers filter.'),
  p('**On-device and private.** The models run through Ollama on the user\'s own computer and only loopback addresses are accepted, so the draft is not sent to any online service. No API key is needed, and prompts and answers are never written to logs.'),
  p('**Device-aware model choice.** The application detects the amount of RAM and the NVIDIA GPU memory and picks the best installed model that suits the device. A larger model is used on a GPU with 8 GB of memory, a 3-billion-parameter model on a CPU-only laptop, and rule-based advice on very small machines. Nothing is downloaded without asking.'),
  ...figure(D('device_tiers'), 5.8, 'Figure 9.5: Model choice by device. The lite model (0.5 billion parameters) is always the safety net.'),

  h(1, '9.9 Software engineering'),
  ...bullets([
    '**Testing:** ' + testsTotal + ' automated tests, including a golden-snapshot test that proves forecasts are identical before and after the AI Coach was added, a scan that no credential is committed, and tests that run the real local model.',
    '**One-command launcher:** run.ps1 (Windows) or run.sh (macOS and Linux) creates the environment, installs pinned requirements, detects the device, installs and starts Ollama, downloads the right models after asking, and starts the app.',
    '**Deployment:** GitHub Actions runs the tests on every push; the application is hosted on Render (rule-based mode, because the free tier cannot host a language model); a scheduled keep-warm request is sent every 10 minutes to reduce cold starts.',
  ]),
  h(1, '9.10 Technology stack'),
  table(['Purpose', 'Tool'], [
    ['Language, data', 'Python 3.10, pandas, NumPy'],
    ['Machine learning', 'scikit-learn (Linear Regression, Random Forest), XGBoost, SciPy'],
    ['Charts and diagrams', 'matplotlib, Altair'],
    ['Application', 'Streamlit'],
    ['Local language models', 'Ollama; Qwen2.5 3B (main) and 0.5B (lite); jsonschema for answer validation'],
    ['Quality and delivery', 'pytest, git, GitHub Actions, Render'],
  ], [2, 4.2]),
  gap(),

  h(1, '9.11 Applications'),
  table(['Who', 'How the system helps'], [
    ['Individual creators', 'Compare title, tag and description drafts and choose a publishing time before uploading; understand which choice matters most'],
    ['Social-media agencies and brands', 'A repeatable pre-publication checklist with explanations that can be shown to clients'],
    ['Students and teachers', 'A complete example of explainable, uncertainty-aware machine learning with a safe use of language models'],
    ['Other platforms', 'The same method (metadata features, Shapley groups, conformal intervals, evidence-checked advice) can be reused for other content platforms if data is available'],
    ['Privacy-sensitive users', 'The on-device AI means drafts never leave the computer'],
  ], [1.8, 4.4]),
  gap(),
  h(1, '9.12 Conclusion of Experiment 9'),
  p('The methodology combines careful data preparation, leakage-safe features, fair model comparison, exact explanations, tested uncertainty and an evidence-checked on-device language model. Experiment 10 reports the results and shows the working system.'),
  pageBreak(),
);

// ------------------------------------------------------------------ Experiment 10
children.push(...experimentHeader(10, 'Results, Screenshots and Conclusion',
  'To present the measured results of the models, the explanation and uncertainty tools and the AI Coach, to show the working application through screenshots, and to conclude the project.',
  'The Signal Studio application, pytest, a local Ollama server with Qwen2.5 models, Google Chrome for screenshots.'));

children.push(
  h(1, '10.1 Experimental setup'),
  table(['Item', 'Value'], [
    ['Computer', 'Intel Core i5-1240P (16 threads), 15.7 GB RAM, no dedicated GPU, Windows 11'],
    ['Software', 'Python 3.10.11, scikit-learn 1.7.2, Streamlit 1.65.0, Ollama 0.40.11'],
    ['Language models', 'qwen2.5:3b (main, 1.9 GB) and qwen2.5:0.5b (lite, 0.4 GB), both on the CPU'],
    ['Data', '16,307 unique India-trending videos (2017-2018)'],
  ], [1.4, 4.8]),
  gap(),

  h(1, '10.2 Model results'),
  table(['Model / evaluation', 'Views R-squared', 'Engagement R-squared'], [
    ['Linear Regression (baseline)', '0.197', '0.384'],
    ['First Random Forest (held-out 20 percent)', '0.378', '0.612'],
    ['**Final Random Forest, 5-fold cross-validation**', '**0.419**', '**0.637**'],
    ['Final Random Forest, later-in-time hold-out', '0.368', '0.529'],
  ], [3.2, 1.5, 1.5]),
  gap(),
  ...figure(D('r2_progress'), 5.6, 'Figure 10.1: R-squared of the baseline and the models. Later uploads are harder to predict, which is expected.'),
  p('The final model explains roughly 42 percent of the variation in log-views and 64 percent of the variation in engagement rate under cross-validation. The remainder is likely due to factors that are not in the data: thumbnails, channel reputation, audience retention and YouTube\'s own recommendation system.'),

  h(1, '10.3 What the model learned'),
  ...figure(D('feature_groups'), 5.4, 'Figure 10.2: Share of the model\'s attention per group of choices.'),
  ...figure(D('keywords'), 5.4, 'Figure 10.3: Title words that travel with small (red) and big (green) audiences in the trending data (associations, not causes).'),
  ...figure(D('shapley_waterfall'), 5.4, 'Figure 10.4: Exact Shapley explanation of one real draft. Category is the largest bar but cannot be changed once the content is decided; title, tags, description and timing can.'),

  h(1, '10.4 Honest uncertainty'),
  table(['Check (80 percent intervals)', 'Views', 'Engagement'], [
    ['Out-of-fold (shuffled)', '80.0 %', '80.0 %'],
    ['Later-in-time hold-out', '79.7 %', '80.9 %'],
  ], [3.2, 1.5, 1.5]),
  gap(),
  ...figure(D('conformal'), 6.2, 'Figure 10.5: The 80 percent range for one draft (left) and the measured coverage (right). A views forecast is typically within about x0.29 to x3.5 of the truth.'),

  h(1, '10.5 Screenshots of the working system'),
  p('All screenshots were taken from the running application on the example draft "5 Study Tips That Actually Work for Students" (category Education, Saturday 18:00 IST).'),
  ...figure(S('forecast_inputs_output'), 6.4, 'Figure 10.6: Forecast studio: the draft form, expected views and engagement with 80 percent intervals, percentile and a calibration note.'),
  ...figure(S('forecast_why'), 6.4, 'Figure 10.7: "Why this forecast": exact Shapley effects per group, with a plain-language explanation.'),
  ...figure(S('best_time'), 6.4, 'Figure 10.8: Best-time map over 168 weekly slots with the three best slots and a "Use this slot" button.'),
  ...figure(S('title_lab'), 6.4, 'Figure 10.9: Title lab: edits ranked by the model-scored effect, each with an Apply button.'),
  ...figure(S('ai_coach_a'), 6.4, 'Figure 10.10: AI Coach (top): device detection, the local model in use and the unchanged ML forecast.'),
  ...figure(S('ai_coach_b'), 6.4, 'Figure 10.11: AI Coach (bottom): prioritised actions, title and tag ideas re-scored by the ML model, description tips, timing advice and limits.'),
  ...figure(S('similar'), 6.4, 'Figure 10.12: Similar videos: an independent second opinion from TF-IDF look-alikes.'),
  ...figure(S('scenario'), 6.4, 'Figure 10.13: Scenario lab: A/B comparison and category what-if.'),
  ...figure(S('model_brief'), 6.4, 'Figure 10.14: Model brief: validation scores, group importance, measured interval coverage and honest limits.'),

  h(1, '10.6 AI Coach evaluation with a real model'),
  p('The AI Coach was developed by running the **real** local model, not a simulation. The first attempt asked the 3-billion-parameter model to write the whole structured answer. It took 102 seconds on this CPU and failed the evidence checks because the model left required evidence fields empty. After tightening the instructions it took 81 seconds and the checks correctly rejected a made-up figure ("8.69 percent engagement" when the ML forecast was 4.69 percent). In a full-chain run the lite model then returned an empty but formally valid answer after 161 seconds. These observations led to the **hybrid design** (rules fix the structure, the model writes wording, every sentence is checked alone, and an answer in which nothing survives counts as a failure). An evaluation then showed that the 3B model sometimes returned a tag list as one comma-separated string, which broke a length rule although the advice itself was fine. Repairing such harmless formatting slips and giving the main model one retry made all four example drafts succeed on the main model in 37 to 38 seconds each (table below).'),
  ...figure(D('hallucination'), 5.4, 'Figure 10.15: A real example: the number checker blocks a sentence whose figure is not in the evidence.'),
);

if (runsInfo && runsInfo.runs && runsInfo.runs.length) {
  const rows = runsInfo.runs.map((r) => [
    r.draft, r.source === 'llm' ? `${r.model} (${r.tier})` : 'rule-based', `${r.seconds} s`, String(r.dropped),
    (r.rescored && r.rescored.length ? r.rescored.map((v) => `${v > 0 ? '+' : ''}${v}%`).join(', ') : '-'),
  ]);
  children.push(
    p(`Final evaluation of the hybrid AI Coach on four example drafts (${runsInfo.device}; main model ${runsInfo.main}, lite model ${runsInfo.lite}):`),
    table(['Draft', 'Model that wrote the advice', 'Time', 'Passages removed by checks', 'ML-scored effect of proposed titles on views'], rows, [1.1, 2, 0.8, 1.2, 2.1]),
    gap(),
    p('Every proposed title is re-scored by the Random Forest, so some ideas raise and some lower the forecast; the user sees the model-scored effect and decides. "Passages removed" counts sentences discarded because they failed an evidence check.'),
  );
}

children.push(
  h(1, '10.7 Software quality and deployment'),
  ...figure(D('tests'), 5.2, `Figure 10.16: ${testsTotal} automated tests by area.`),
  ...bullets([
    '**Forecasts unchanged:** a golden-snapshot test of seven drafts confirms that the ML outputs are identical before and after the AI Coach was added.',
    '**Real-model tests:** tests that call the real Ollama models run automatically when Ollama is available and are skipped otherwise (for example on GitHub Actions).',
    '**Continuous integration:** GitHub Actions runs the tests on every push.',
    '**Online version:** https://youtube-strategy-predictor.onrender.com (rule-based mode). A keep-warm request every 10 minutes reduces the waiting time after idle periods.',
  ]),
  ...figure(D('cold_start'), 5.6, 'Figure 10.17: Why a keep-warm request helps on the free hosting tier.'),
  ...figure(D('run_steps'), 6.2, 'Figure 10.18: Running the project on another computer takes three steps.'),

  h(1, '10.8 Discussion and limitations'),
  ...bullets([
    'The data contains only videos that already trended (2017-2018, India). The system estimates relative performance in that group and cannot say whether an arbitrary upload will go viral.',
    'Thumbnails, channel size, audience retention and YouTube\'s ranking are not in the data. The model explains about 42 to 64 percent of the variation, not all of it.',
    'Shapley effects, keyword statistics and edit rankings are **associations** learned from data, not proof of cause and effect.',
    'On a CPU the 3B model needs about 30 to 80 seconds per answer (about 38 seconds in the final evaluation). A computer with an 8 GB NVIDIA GPU should be faster with a larger model, but this was **not tested** in this project.',
    'The online version runs without a language model because the free hosting tier has too little memory.',
  ]),
  h(1, '10.9 Conclusion'),
  p('This project shows that a metadata-only model can give useful, honestly bounded estimates of YouTube video performance (R-squared 0.42 for log-views and 0.64 for engagement under cross-validation) and that these estimates can be turned into understandable advice. The key results are: (1) cleaning the repeated snapshots reduced 37,352 rows to 16,307 unique videos; (2) exact Shapley explanations show which creator-controlled choices matter; (3) the 80 percent intervals were tested on later uploads and held at 79.7 and 80.9 percent; (4) a real on-device language model writes advice that is checked against evidence, with a lite model and rules as fallbacks; and (5) the whole system can be installed with one command and is verified by ' + testsTotal + ' automated tests.'),
  h(1, '10.10 Future scope'),
  ...bullets([
    'Add thumbnail features and channel history, which are currently missing.',
    'Collect fresh data, including videos that did not trend, to remove the survivorship limitation.',
    'Evaluate the larger 7B model on an 8 GB NVIDIA GPU and compare answer quality and speed.',
    'Run a small user study with real creators to measure whether the advice is useful.',
  ]),
  pageBreak(),
  h(1, 'References'),
);

const refs = [
  'M. Cha, H. Kwak, P. Rodriguez, Y.-Y. Ahn and S. Moon, "I Tube, You Tube, Everybody Tubes: Analyzing the World\'s Largest User Generated Content Video System," Proc. ACM Internet Measurement Conference (IMC), 2007.',
  'G. Szabo and B. A. Huberman, "Predicting the popularity of online content," Communications of the ACM, vol. 53, no. 8, 2010.',
  'F. Figueiredo, F. Benevenuto and J. M. Almeida, "The Tube over Time: Characterizing Popularity Growth of YouTube Videos," Proc. ACM WSDM, 2011.',
  'H. Pinto, J. M. Almeida and M. A. Goncalves, "Using Early View Patterns to Predict the Popularity of YouTube Videos," Proc. ACM WSDM, 2013.',
  'L. Breiman, "Random Forests," Machine Learning, vol. 45, no. 1, 2001.',
  'T. Chen and C. Guestrin, "XGBoost: A Scalable Tree Boosting System," Proc. ACM KDD, 2016.',
  'F. Pedregosa et al., "Scikit-learn: Machine Learning in Python," Journal of Machine Learning Research, vol. 12, 2011.',
  'L. S. Shapley, "A Value for n-Person Games," in Contributions to the Theory of Games II, Princeton University Press, 1953.',
  'S. M. Lundberg and S.-I. Lee, "A Unified Approach to Interpreting Model Predictions," Advances in Neural Information Processing Systems (NeurIPS), 2017.',
  'V. Vovk, A. Gammerman and G. Shafer, Algorithmic Learning in a Random World, Springer, 2005.',
  'J. Lei, M. G\'Sell, A. Rinaldo, R. J. Tibshirani and L. Wasserman, "Distribution-Free Predictive Inference for Regression," Journal of the American Statistical Association, vol. 113, no. 523, 2018.',
  'G. Salton and C. Buckley, "Term-weighting approaches in automatic text retrieval," Information Processing & Management, vol. 24, no. 5, 1988.',
  'P. Lewis et al., "Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks," Advances in Neural Information Processing Systems (NeurIPS), 2020.',
  'Z. Ji et al., "Survey of Hallucination in Natural Language Generation," ACM Computing Surveys, vol. 55, no. 12, 2023.',
  'Qwen Team, "Qwen2.5 Technical Report," arXiv:2412.15115, 2024.',
  'Mitchell J., "Trending YouTube Video Statistics," Kaggle dataset, https://www.kaggle.com/datasets/datasnaek/youtube-new (accessed 2026).',
];
refs.forEach((r, i) => children.push(p(`[${i + 1}]  ${r}`, { after: 80, indent: { left: 540, hanging: 540 } })));

L.save(L.buildDocument({ font: 'Times New Roman', size: 24, accent: '1A2B4C', children, footerText: 'Signal Studio: Project Report (Experiments 8, 9, 10)' }),
  L.path.join(__dirname, 'Project_Report_Experiments_8_9_10.docx'));
