// Builds Project_Report_Experiments_8_9_10.docx  (run: node build_report.js)
// Style: no cover page, all text black, Times New Roman, justified, simple wording, footer = name (left) and roll number (right).
const L = require('./lib_docx');
const K = L.kit({ font: 'Times New Roman', size: 24, accent: '000000', dark: '000000', plain: true });
const { p, heading: h, bullets, numbered, figure, callout, table, gap, pageBreak } = K;
const runsInfo = (() => { try { return JSON.parse(L.fs.readFileSync(L.path.join(L.ASSETS, 'ai_coach_runs.json'), 'utf8')); } catch { return null; } })();
const testsTotal = (() => { try { return JSON.parse(L.fs.readFileSync(L.path.join(L.ASSETS, 'diagrams_report', 'tests_total.json'), 'utf8')).total; } catch { return 133; } })();
const D = (f) => `diagrams_report/${f}.png`; // black-text, Times New Roman versions of the figures (make_report_assets.py --plain)
const S = (f) => `screens/parts/${f}.png`;

function experimentHeader(no, title, aim, tools) {
  return [
    new L.Paragraph({ alignment: L.AlignmentType.CENTER, spacing: { before: 0, after: 80 }, children: [new L.TextRun({ text: `EXPERIMENT ${no}`, bold: true, size: 40, font: 'Times New Roman', color: '000000' })] }),
    new L.Paragraph({ alignment: L.AlignmentType.CENTER, spacing: { after: 200 }, children: [new L.TextRun({ text: title, bold: true, size: 30, font: 'Times New Roman', color: '000000' })] }),
    table(['Item', 'Details'], [['Project', 'AI-Based YouTube Analytics and Content Strategy Prediction (Signal Studio)'], ['Aim', aim], ['Tools used', tools]], [1.2, 5]),
    gap(160),
  ];
}

const children = [];

// ------------------------------------------------------------------ Experiment 8
children.push(...experimentHeader(8, 'Introduction and Literature Review',
  'To understand the problem of predicting how a YouTube video will perform before it is posted, to set the objectives and scope of the project, and to study the earlier research that this work builds on.',
  'Kaggle dataset (Trending YouTube Video Statistics, India), research papers, Python.'));

children.push(
  h(1, '8.1 Introduction'),
  p('Millions of people make videos for YouTube. Before a video goes live, the creator has to decide the **title**, the **tags**, the **description**, the **category** and the **day and time** of posting. The results (views, likes and comments) are known only after the video is live, and by then it is too late to change the first impression. So the creator has to guess which choices will work.'),
  p('This project asks one simple question: **can a computer model estimate how a video will do, using only things that are known before posting, and can it explain its answer so that a creator can act on it?** We built a working system called **Signal Studio**. It estimates the likely number of views and the engagement rate of a planned video. (Engagement rate = likes plus comments, divided by views. It shows how many viewers reacted.) It shows which choices push the estimate up or down, and it shows how sure or unsure the estimate is. Finally, it gives short, fact-based advice using a small AI language model that runs on the user\'s own computer.'),
  h(1, '8.2 Problem statement'),
  callout('Problem statement', 'A creator knows only the title, tags, description, category and planned posting time of a video. Using only this information, estimate (a) the number of views and (b) the engagement rate of the video, explain the estimate, show how uncertain it is, and suggest improvements. No information that exists only after posting may be used.'),
  gap(100),
  h(1, '8.3 Objectives'),
  ...numbered([
    'Collect a real YouTube dataset and clean it by removing the repeated rows.',
    'Make input features that are known before posting. Likes and comments are kept only as the answers to predict (the targets).',
    'Train and compare models (Linear Regression, Random Forest and XGBoost) and test them honestly, including on newer videos.',
    'Explain each prediction in simple words and show how uncertain it is.',
    'Turn the model\'s findings into practical advice using a local language model, without letting it make up numbers.',
    'Make the project easy to install and run on any laptop with one command, and put a version online.',
  ]),
  h(1, '8.4 Scope and dataset'),
  p('The project uses the public Kaggle dataset **Trending YouTube Video Statistics** [16], India file. Each row is one video on one day on which it was on India\'s Trending list. So the same video can appear in many rows.'),
  table(['Property', 'Value'], [
    ['Source', 'Kaggle, Trending YouTube Video Statistics (INvideos.csv), data from 2017-2018'],
    ['Raw rows', '37,352 (one row per video per trending day)'],
    ['Unique videos after cleaning', '16,307 (the latest trending row of each video)'],
    ['Inputs used (known before posting)', 'Title, tags, description, category, posting day and hour (converted to Indian Standard Time)'],
    ['Targets (what is predicted)', 'Views (on a log scale) and engagement rate = (likes + comments) / views'],
    ['Never used as inputs', 'Likes, dislikes, comment count, views, channel details, video ID'],
    ['Important limit', 'Only videos that trended are in the data. So the project compares videos that already became popular. It cannot say whether any random upload will go viral.'],
  ], [2, 4.2]),
  gap(),
  ...figure(D('funnel'), 4.6, 'Figure 8.1: The raw data has one row per video per day. Keeping each video once gives 16,307 unique videos.'),

  h(1, '8.5 Literature review'),
  h(2, '8.5.1 How popular online videos become'),
  p('Cha et al. [1] studied YouTube on a very large scale. They found that a few videos get most of the views and most videos get very few. Because of this uneven spread, we predict views on a **log scale**. A log scale squeezes very big numbers, so small and huge videos can be compared fairly. Szabo and Huberman [2] showed that the later popularity of online content can be predicted from its early popularity. Figueiredo et al. [3] studied how the views of YouTube videos grow over time. Pinto et al. [4] used the early views of a video to predict its later views. All these studies need **data collected after the video is posted** (early views). Our project works one step earlier. It uses only the information that a creator can still change.'),
  h(2, '8.5.2 Models for data in tables'),
  p('A **Random Forest** [5] is a group of many decision trees. Each tree learns from a different random part of the data, and the final answer is the average of all the trees. This way the answer does not depend on one tree, and it works well when the link between the inputs and the answer is not a straight line. **XGBoost** [6] also uses trees, but it builds them one after another, and each new tree fixes the mistakes of the earlier ones. Both are common choices for data in tables. We used scikit-learn [7] and compared them with a simple **Linear Regression** (a straight-line model) as the starting point. In our tests the Random Forest gave the best results for both targets.'),
  h(2, '8.5.3 Explaining a prediction'),
  p('The **Shapley value** [8] comes from game theory. It is a fair way to share the total gain of a team among its members. It checks how much each member adds in every possible order in which the team can be formed, and then takes the average. Lundberg and Lee [9] showed that this idea can explain the predictions of machine learning models (the method is called SHAP). We use the same idea, but for **five groups of choices** (title, tags, description, timing and category) instead of single features. With only five groups, the exact answer can be found by checking 2^5 = 32 combinations, so no approximation is needed.'),
  h(2, '8.5.4 Showing how sure the model is'),
  p('A single predicted number can be misleading, so we also give a **range**. **Conformal prediction** [10] is a method for building such ranges, and it works with any model. Lei et al. [11] describe a simple version for regression, called split conformal prediction. The idea is to check the model\'s errors on data it did not train on, and use them to decide how wide the range must be, so that a chosen share (for example 80 percent) of the true values falls inside it. We use this idea, and we also test the promise on newer videos.'),
  h(2, '8.5.5 Finding similar text and using language models'),
  p('**TF-IDF** [12] turns a text into numbers by giving rare, useful words more weight than very common words. Two texts can then be compared to see how similar they are (this is called cosine similarity). We use it to find videos with similar titles. Language models can write smooth text, but sometimes they state things that are not true. This is called **hallucination** [14]. **Retrieval-augmented generation** [13] reduces this by giving the model real facts to work from. Our AI Coach works in the same spirit. It gets a numbered list of facts from the project\'s own model and data, and everything it writes is checked against those facts. The language models we use are from the Qwen2.5 family [15].'),
  h(2, '8.5.6 Summary of related work'),
  table(['Work', 'What it gives', 'How this project is different'], [
    ['Cha et al. [1]', 'Large study of YouTube; a few videos get most of the views', 'Only describes the data; does not predict from title and tags'],
    ['Szabo & Huberman [2]', 'Predicts later popularity from early popularity', 'Needs views after posting'],
    ['Figueiredo et al. [3]', 'How the views of YouTube videos grow over time', 'Studies growth after posting'],
    ['Pinto et al. [4]', 'Predicts later views from early views', 'Needs early views'],
    ['Breiman [5], Chen & Guestrin [6]', 'Random Forest and XGBoost', 'Used as tools and compared fairly here'],
    ['Lundberg & Lee [9]', 'SHAP explanations', 'We use exact Shapley values for five groups of choices'],
    ['Lei et al. [11]', 'Prediction ranges that work with any model', 'We test how often the range is right on newer videos'],
    ['Lewis et al. [13]', 'Give language models real facts to work from', 'We also check every sentence and have backup plans, all on the user\'s own computer'],
  ], [1.6, 2.4, 2.4]),
  gap(),
  h(1, '8.6 Gap in earlier work and our contribution'),
  ...bullets([
    '**Gap 1:** earlier predictors need information that exists only after posting. Creators need help **before** posting.',
    '**Gap 2:** a predicted number alone does not tell a creator what to change. We add explanations (Shapley), a best-time map, a ranked list of edits and similar videos.',
    '**Gap 3:** predictions are rarely shown with an honest, tested range. We give ranges and measure how often they are right on newer videos.',
    '**Gap 4:** language models can make up numbers. We let the model write only the wording, check every sentence against the facts, and use rules as a backup.',
  ]),
  h(1, '8.7 Conclusion of Experiment 8'),
  p('Earlier research shows that the popularity of online videos can be predicted, but mostly after posting. This project uses only the things a creator controls before posting. It also adds explanations, a tested range and fact-checked advice, so it fills a practical gap. Experiment 9 explains the method used to build the system.'),
  pageBreak(),
);

// ------------------------------------------------------------------ Experiment 9
children.push(...experimentHeader(9, 'Methodology and Applications',
  'To explain the complete method of Signal Studio (data cleaning, features, models, testing, explanation, uncertainty, AI Coach and putting it online) and to list its practical uses.',
  'Python 3.10, pandas, scikit-learn, XGBoost, matplotlib, Streamlit, Ollama with Qwen2.5 models, git and GitHub Actions, Render.'));

children.push(
  h(1, '9.1 System overview'),
  p('The system is a pipeline of eight steps. The raw data is cleaned, features are made, two Random Forest models are trained, they are tested in two ways (5-fold cross-validation and a test on newer videos), the predictions are explained, everything is put into a web app, and the app is put online. Each step is a real script in the project and has automated tests.'),
  ...figure(D('pipeline'), 6.5, 'Figure 9.1: The eight-step pipeline of the project.'),
  ...figure(D('architecture'), 6.5, 'Figure 9.2: How the parts fit together: data, ML models, insight tools, AI Coach and the app, supported by tests, GitHub Actions, online hosting and the local AI program.'),

  h(1, '9.2 Data cleaning'),
  ...numbered([
    '**Fix the dates.** The dataset writes the trending date as text in an unusual order (year.day.month). We change it into a real date before sorting. If we sorted the text itself, some videos would keep the wrong row.',
    '**Remove repeated rows.** The rows are sorted by date, and for each video ID only the latest row is kept. This turns 37,352 rows into 16,307 unique videos. No row had to be removed because of missing important values.',
    '**Give names to categories.** Category numbers are changed into names using YouTube\'s category list. The list stores the numbers as text, but the data stores them as numbers, so both are first changed to text. Category 29 is missing from the supplied list, so we named it "Nonprofits & Activism" using YouTube\'s official list.',
  ]),
  h(1, '9.3 Making the input features'),
  p('Only information that is known before posting is used. The final model has 30 input columns, in five groups.'),
  table(['Group', 'Examples of features'], [
    ['Title packaging', 'Length, number of words, digits, question marks and exclamation marks, share of capital letters, number of emojis, urgent words and how-to words, a simple positive or negative score, and how many different words are used'],
    ['Tags', 'Number of tags, total and average tag length, share of tags with more than one word (a tag list of "[none]" counts as zero tags)'],
    ['Description', 'Length, number of words, number of links, hashtags and call-to-action words (such as "subscribe")'],
    ['Posting time', 'Day of the week and hour in Indian Standard Time, weekend or not, and the hour stored in a circular way so that 23:00 is close to 00:00'],
    ['Category', 'Category name (turned into 0/1 columns, one column for each category)'],
  ], [1.4, 4.8]),
  gap(),
  callout('Avoiding data leakage (no peeking at the answer)', 'Likes, dislikes and comment counts are never used as inputs. Likes and comments are used only to calculate the engagement rate, which is the **target** (the answer we want to predict). The same function makes the features for training and for the live app, and a test checks the list of columns.'),
  gap(100),
  p('A check of the first version found three mistakes. They were fixed and the model was trained again. (1) Hashtags and "www." links were never counted because of a mistake in the search pattern. (2) The training tags kept quotation marks that user input never has. (3) Category 29 was shown as "Unknown". Tests now guard against each of them.'),

  h(1, '9.4 Training the models'),
  p('Two things are predicted: **log(1 + views)** and the **engagement rate**. Linear Regression is the starting point. We compared Random Forest and XGBoost using 5-fold cross-validation, and the Random Forest was better on both. The first Random Forest was over 200 MB because its trees could grow without any limit. We limited the depth of the trees and the size of the leaves. This made the model more than 90 percent smaller and cost less than 3 percentage points of R-squared.'),
  table(['Item', 'Setting'], [
    ['Final model', 'Random Forest, 180 trees, maximum depth 16, at least 5 samples in each leaf, 80 percent of the features tried at each split'],
    ['Number of models', 'One for log-views and one for engagement rate'],
    ['Scores used', 'R-squared (how much of the ups and downs the model explains; 1 is perfect) and mean absolute error (the average size of the mistake)'],
    ['Test 1: 5-fold cross-validation', 'The data is split into five parts. The model is trained on four parts and tested on the fifth. This is repeated five times and the scores are averaged.'],
    ['Test 2: newer videos (hold-out)', 'Train on the oldest 80 percent of the videos and test on the newest 20 percent. This is harder and closer to real use.'],
  ], [1.7, 4.5]),
  gap(),

  h(1, '9.5 Explaining a prediction (Shapley values)'),
  p('To explain why a draft gets its forecast, the five groups of choices are revealed one at a time, starting from a typical trending video. The Shapley value of a group is its average effect over all the possible orders:'),
  p('phi_i = sum over S not containing i of  [ |S|! (n - |S| - 1)! / n! ] * ( v(S + i) - v(S) )', { align: L.AlignmentType.CENTER, run: { italics: true } }),
  p('Here n = 5 is the number of groups, S is any set of groups that does not include group i, and v(S) is the model\'s forecast when only the groups in S use the values of the draft (the other groups stay typical). The formula averages the extra effect of adding group i. With five groups, only 32 combinations are needed, so the answer is exact. The effects of all the groups add up exactly to (forecast minus typical forecast), and an automated test checks this. The app also has a **keyword radar**. It shows the median views of trending videos that contain each title word. Only words used in at least 25 videos from at least 25 different channels are shown, so channel names do not appear.'),

  h(1, '9.6 Showing how sure the model is (prediction ranges)'),
  p('First we collect the model\'s errors on videos it did not train on. In cross-validation, each video is predicted by a model that never saw it. For views, the size of the error on the log scale is used. For engagement, the error as a share of the predicted value is used. The error that is bigger than 80 percent of all errors (the 80th percentile) becomes the half-width of the range. So about 80 percent of the true values should fall inside the range. We then check this promise on newer videos, so the range is not just an assumption.'),

  h(1, '9.7 Decision tools'),
  ...bullets([
    '**Best-time map:** the same draft is forecast for all 168 weekly slots (7 days x 24 hours, IST). Nearby hours are averaged, so one noisy slot cannot look like the best time.',
    '**Title lab:** about twelve automatic edits (add a number, use a question, start with "How to", add hashtags, add a call to action, reuse title words as tags, and so on). The trained model scores each edit and the edits are ranked.',
    '**Similar videos:** TF-IDF finds trending videos with similar titles and tags. Their median views give a second opinion.',
    '**Category what-if and A/B comparison:** the same draft in other categories, or two drafts side by side, with a check whether their ranges overlap.',
  ]),

  h(1, '9.8 AI Coach: an AI on your own computer that cannot change the numbers'),
  p('The AI Coach turns the model\'s numbers into a few clear suggestions, in order of importance. It is built on five safety ideas.'),
  ...figure(D('ai_coach_flow'), 6.5, 'Figure 9.3: The AI Coach pipeline and its backup steps.'),
  ...numbered([
    '**The numbers stay with the ML model.** The language model never makes the forecast. Every number shown, including the effect of any title or tag it suggests, is scored again by the trained Random Forest.',
    '**A list of facts.** The language model gets only a numbered list of facts (E1, E2, ...) made by the project\'s own code: the forecast and its range, percentiles, Shapley effects, ranked edits, keyword statistics, the best time slot and the limits of the data.',
    '**Hybrid design.** Rules decide what to improve and which facts support it. The language model only writes the wording: explanations, new title ideas, tags and description tips.',
    '**Checking sentence by sentence.** A sentence is rejected if it quotes a number that is not in the facts, promises results ("will go viral"), or contains links or HTML. A suggested title is rejected if it repeats the draft, is mostly capital letters, or moves far away from the draft\'s own words. A rejected sentence is dropped on its own, and the rest is kept.',
    '**Backup plan.** If the main model fails, it gets one retry. Then a smaller "lite" model is tried, and then plain rule-based advice, so the coach always gives an answer. Small formatting slips, such as a list of tags returned as one comma-separated text, are repaired before checking.',
  ]),
  ...figure(D('hybrid_design'), 6.0, 'Figure 9.4: Rules decide, the AI writes, the checkers filter.'),
  p('**Runs on your own computer and stays private.** The models run through Ollama (a free program that runs AI models on your own computer). Only local addresses (loopback) are accepted, so the draft is not sent to any online service. No API key is needed, and prompts and answers are never saved in logs.'),
  p('**The model is chosen to fit the device.** The app checks the computer\'s RAM and NVIDIA GPU memory and picks the best installed model that fits. A bigger model is used on a GPU with 8 GB of memory, a 3-billion-parameter model on a laptop without a GPU, and rule-based advice on very small computers. Nothing is downloaded without asking.'),
  ...figure(D('device_tiers'), 5.8, 'Figure 9.5: Model choice by device. The lite model (0.5 billion parameters) is always the safety net.'),

  h(1, '9.9 Software engineering'),
  ...bullets([
    '**Testing:** ' + testsTotal + ' automated tests. They include a "golden" test that saves the forecasts of seven drafts and proves they are the same before and after the AI Coach was added, a scan that checks that no password or key is saved in the code, and tests that run the real local model.',
    '**One-command launcher:** run.ps1 (Windows) or run.sh (macOS and Linux) creates the environment, installs the required packages, checks the device, installs and starts Ollama, downloads the right models after asking, and starts the app.',
    '**Putting it online:** GitHub Actions runs the tests on every push. The app is hosted on Render in rule-based mode (the free plan has too little memory for a language model). A scheduled request is set up to ping the app every 10 minutes, so visitors do not wait long for it to wake up.',
  ]),
  h(1, '9.10 Technology used'),
  table(['Purpose', 'Tool'], [
    ['Language and data', 'Python 3.10, pandas, NumPy'],
    ['Machine learning', 'scikit-learn (Linear Regression, Random Forest), XGBoost, SciPy'],
    ['Charts and diagrams', 'matplotlib, Altair'],
    ['Web app', 'Streamlit'],
    ['Local language models', 'Ollama; Qwen2.5 3B (main) and 0.5B (lite); jsonschema (checks the format of the AI\'s answer)'],
    ['Quality and delivery', 'pytest, git, GitHub Actions, Render'],
  ], [2, 4.2]),
  gap(),

  h(1, '9.11 Applications'),
  table(['Who', 'How the system helps'], [
    ['Individual creators', 'Compare drafts of the title, tags and description and choose a posting time before uploading; see which choice matters most'],
    ['Social-media agencies and brands', 'A repeatable checklist before posting, with explanations that can be shown to clients'],
    ['Students and teachers', 'A complete example of machine learning that explains itself and shows its uncertainty, with a safe use of language models'],
    ['Other platforms', 'The same method (features from the metadata, Shapley groups, prediction ranges, fact-checked advice) can be reused for other content platforms if data is available'],
    ['Users who care about privacy', 'The AI runs on their own computer, so drafts never leave it'],
  ], [1.8, 4.4]),
  gap(),
  h(1, '9.12 Conclusion of Experiment 9'),
  p('The method combines careful data cleaning, features without leakage, a fair comparison of models, exact explanations, a tested range and a fact-checked AI on the user\'s own computer. Experiment 10 gives the results and shows the working system.'),
  pageBreak(),
);

// ------------------------------------------------------------------ Experiment 10
children.push(...experimentHeader(10, 'Results, Screenshots and Conclusion',
  'To present the measured results of the models, the explanation and range tools and the AI Coach, to show the working app through screenshots, and to conclude the project.',
  'The Signal Studio app, pytest, a local Ollama server with Qwen2.5 models, Google Chrome for screenshots.'));

children.push(
  h(1, '10.1 Experiment setup'),
  table(['Item', 'Value'], [
    ['Computer', 'Intel Core i5-1240P (16 threads), 15.7 GB RAM, no separate GPU, Windows 11'],
    ['Software', 'Python 3.10.11, scikit-learn 1.7.2, Streamlit 1.65.0, Ollama 0.40.11'],
    ['Language models', 'qwen2.5:3b (main, 1.9 GB) and qwen2.5:0.5b (lite, 0.4 GB), both run on the CPU'],
    ['Data', '16,307 unique India-trending videos (2017-2018)'],
  ], [1.4, 4.8]),
  gap(),

  h(1, '10.2 Model results'),
  table(['Model and test', 'Views R-squared', 'Engagement R-squared'], [
    ['Linear Regression (starting point)', '0.197', '0.384'],
    ['First Random Forest (tested on 20 percent of the data)', '0.378', '0.612'],
    ['**Final Random Forest, 5-fold cross-validation**', '**0.419**', '**0.637**'],
    ['Final Random Forest, test on newer videos', '0.368', '0.529'],
  ], [3.2, 1.5, 1.5]),
  gap(),
  ...figure(D('r2_progress'), 5.6, 'Figure 10.1: R-squared of the starting model and the Random Forests. Newer videos are harder to predict, which is expected.'),
  p('R-squared tells how much of the ups and downs in the real values is explained by the model (0 means nothing, 1 means everything). The final model explains about 42 percent of the changes in log-views and 64 percent of the changes in engagement rate under cross-validation. The rest is probably due to things that are not in the data: thumbnails, how well known the channel is, how long people watch, and YouTube\'s own recommendations.'),

  h(1, '10.3 What the model learned'),
  ...figure(D('feature_groups'), 5.4, 'Figure 10.2: Share of the model\'s attention for each group of choices.'),
  ...figure(D('keywords'), 5.4, 'Figure 10.3: Title words that go with small (red) and big (green) audiences in the trending data. These are links in the data, not proof of cause.'),
  ...figure(D('shapley_waterfall'), 5.4, 'Figure 10.4: Exact Shapley explanation of one real draft. Category is the biggest bar, but it cannot be changed once the content is decided. Title, tags, description and timing can be changed.'),

  h(1, '10.4 How sure is the forecast?'),
  table(['Check (80 percent ranges)', 'Views', 'Engagement'], [
    ['Cross-validation (videos mixed randomly)', '80.0 %', '80.0 %'],
    ['Test on newer videos', '79.7 %', '80.9 %'],
  ], [3.2, 1.5, 1.5]),
  gap(),
  ...figure(D('conformal'), 6.2, 'Figure 10.5: The 80 percent range for one draft (left) and how often the range was right (right). The real views usually fall between about 0.29 times and 3.5 times the forecast.'),

  h(1, '10.5 Screenshots of the working system'),
  p('All screenshots were taken from the running app on the example draft "5 Study Tips That Actually Work for Students" (category Education, Saturday 18:00 IST).'),
  ...figure(S('forecast_inputs_output'), 6.4, 'Figure 10.6: Forecast studio: the draft form, expected views and engagement with 80 percent ranges, the percentile and a note on how reliable the range is.'),
  ...figure(S('forecast_why'), 6.4, 'Figure 10.7: "Why this forecast": exact Shapley effects for each group, with a plain-language explanation.'),
  ...figure(S('best_time'), 6.4, 'Figure 10.8: Best-time map of 168 weekly slots with the three best slots and a "Use this slot" button.'),
  ...figure(S('title_lab'), 6.4, 'Figure 10.9: Title lab: edits ranked by the effect scored by the model, each with an Apply button.'),
  ...figure(S('ai_coach_a'), 6.4, 'Figure 10.10: AI Coach (top part): device check, the local model in use and the unchanged ML forecast.'),
  ...figure(S('ai_coach_b'), 6.4, 'Figure 10.11: AI Coach (bottom part): ranked actions, title and tag ideas scored again by the ML model, description tips, timing advice and limits.'),
  ...figure(S('similar'), 6.4, 'Figure 10.12: Similar videos: a second opinion from videos with similar titles (TF-IDF).'),
  ...figure(S('scenario'), 6.4, 'Figure 10.13: Scenario lab: A/B comparison and category what-if.'),
  ...figure(S('model_brief'), 6.4, 'Figure 10.14: Model brief: test scores, importance of each group, how often the ranges were right, and the honest limits.'),

  h(1, '10.6 AI Coach test with a real model'),
  p('The AI Coach was built by running the **real** local model, not a pretend one. In the first try, the 3-billion-parameter model was asked to write the whole answer. It took 102 seconds on this CPU, and the answer failed the fact checks because the model left the required evidence fields empty. After we improved the instructions, it took 81 seconds, and the checks correctly rejected a made-up figure ("8.69 percent engagement" when the ML forecast was 4.69 percent). In a full run, the lite model then returned an empty but correctly formatted answer after 161 seconds. These results led to the **hybrid design**: rules fix the structure, the model writes only the wording, every sentence is checked on its own, and an answer in which nothing survives counts as a failure. A later test showed that the 3B model sometimes returned the tag list as one comma-separated text. This broke a length rule even though the advice was fine. We now repair such harmless slips and give the main model one retry. After that, all four example drafts worked on the main model, taking 37 to 38 seconds each (table below).'),
  ...figure(D('hallucination'), 5.4, 'Figure 10.15: A real example: the number checker blocks a sentence whose figure is not in the facts.'),
);

if (runsInfo && runsInfo.runs && runsInfo.runs.length) {
  const rows = runsInfo.runs.map((r) => [
    r.draft, r.source === 'llm' ? `${r.model} (${r.tier})` : 'rule-based', `${r.seconds} s`, String(r.dropped),
    (r.rescored && r.rescored.length ? r.rescored.map((v) => `${v > 0 ? '+' : ''}${v}%`).join(', ') : '-'),
  ]);
  children.push(
    p(`Final test of the hybrid AI Coach on four example drafts (${runsInfo.device}; main model ${runsInfo.main}, lite model ${runsInfo.lite}):`),
    table(['Draft', 'Model that wrote the advice', 'Time', 'Sentences removed by the checks', 'Effect of the suggested titles on views (scored by the ML model)'], rows, [1.1, 2, 0.8, 1.2, 2.1]),
    gap(),
    p('Every suggested title is scored again by the Random Forest, so some ideas raise the forecast and some lower it. The user sees the effect scored by the model and decides. "Sentences removed" counts the sentences that were thrown away because they failed a fact check.'),
  );
}

children.push(
  h(1, '10.7 Software quality and putting it online'),
  ...figure(D('tests'), 5.2, `Figure 10.16: ${testsTotal} automated tests, grouped by what they check.`),
  ...bullets([
    '**Forecasts unchanged:** a "golden" test of seven drafts confirms that the ML outputs are the same before and after the AI Coach was added.',
    '**Real-model tests:** tests that call the real Ollama models run automatically when Ollama is available and are skipped otherwise (for example on GitHub Actions).',
    '**Automatic testing:** GitHub Actions runs the tests on every push.',
    '**Online version:** https://youtube-strategy-predictor.onrender.com (rule-based mode). A request every 10 minutes is set up to reduce the waiting time after idle periods.',
  ]),
  ...figure(D('cold_start'), 5.6, 'Figure 10.17: Why a regular ping helps on the free hosting plan.'),
  ...figure(D('run_steps'), 6.2, 'Figure 10.18: Running the project on another computer takes three steps.'),

  h(1, '10.8 Discussion and limits'),
  ...bullets([
    'The data has only videos that already trended (2017-2018, India). The system compares videos within that group. It cannot say whether a random upload will go viral.',
    'Thumbnails, channel size, how long people watch, and YouTube\'s ranking are not in the data. The model explains about 42 to 64 percent of the changes, not all of them.',
    'Shapley effects, keyword statistics and the ranked edits show **links found in the data**. They do not prove cause and effect.',
    'On a CPU, the 3B model needs about 30 to 80 seconds for one answer (about 38 seconds in the final test). A computer with an 8 GB NVIDIA GPU should be faster with a bigger model, but this was **not tested** in this project.',
    'The online version runs without a language model because the free hosting plan has too little memory.',
  ]),
  h(1, '10.9 Conclusion'),
  p('This project shows that a model using only information known before posting can give useful and honest estimates of YouTube video performance (R-squared 0.42 for log-views and 0.64 for engagement under cross-validation), and that these estimates can be turned into advice that is easy to understand. The key results are: (1) cleaning the repeated rows reduced 37,352 rows to 16,307 unique videos; (2) exact Shapley explanations show which choices of the creator matter; (3) the 80 percent ranges were tested on newer videos and were right 79.7 and 80.9 percent of the time; (4) a real AI model on the user\'s own computer writes advice that is checked against facts, with a lite model and rules as backup; and (5) the whole system can be installed with one command and is checked by ' + testsTotal + ' automated tests.'),
  h(1, '10.10 Future work'),
  ...bullets([
    'Add thumbnail features and the history of the channel, which are missing now.',
    'Collect fresh data, including videos that did not trend, so that the data is not limited to popular videos only.',
    'Test the bigger 7B model on an 8 GB NVIDIA GPU and compare the quality and speed of the answers.',
    'Run a small study with real creators to find out whether the advice is useful.',
  ]),

  h(1, '10.11 Simple meaning of the technical words'),
  p('This table gives the plain meaning of the technical words used in this report.'),
  table(['Word', 'Simple meaning'], [
    ['Feature', 'One piece of information given to the model, such as the length of the title.'],
    ['Target', 'The answer the model learns to predict (here: views and engagement rate).'],
    ['Engagement rate', 'Likes plus comments, divided by views. It shows how many viewers reacted.'],
    ['Log scale', 'A scale in which each step multiplies the number. It lets us compare very small and very big numbers.'],
    ['Decision tree', 'A set of yes/no questions that leads to an answer.'],
    ['Random Forest', 'Many decision trees whose answers are averaged.'],
    ['Linear Regression', 'A simple straight-line model, used as the starting point.'],
    ['R-squared', 'How much of the ups and downs in the real values the model explains. 0 means nothing, 1 means everything.'],
    ['Cross-validation', 'Split the data into five parts. Train on four, test on the fifth, repeat five times and average the scores.'],
    ['Test on newer videos (hold-out)', 'Train on the oldest videos and test on the newest ones, which the model has never seen. It is closer to real use.'],
    ['Median', 'The middle value when all the numbers are sorted. A few huge values do not change it much.'],
    ['Percentile', 'A position among many values. At the 80th percentile, a value is bigger than 80 percent of the others.'],
    ['Pipeline', 'A series of steps in which the output of one step is the input of the next.'],
    ['Data leakage', 'Accidentally giving the model information about the answer, which makes the results look better than they really are.'],
    ['Shapley value', 'A fair way to share credit among a team. Here it shows how much each group of choices moves the forecast.'],
    ['Prediction range (conformal)', 'A range in which the real value should fall a chosen share of the time (here 80 percent).'],
    ['TF-IDF', 'A way to turn text into numbers in which rare words count more. It is used to find videos with similar titles.'],
    ['Language model', 'An AI program that writes text.'],
    ['Hallucination', 'When an AI states something that is not supported by facts, such as a made-up number.'],
    ['Fallback (backup plan)', 'A second way of doing the job that is used when the first way fails.'],
    ['Ollama', 'A free program that runs AI models on your own computer.'],
    ['Cold start', 'The delay when a sleeping online app has to wake up before it can answer.'],
    ['Link, not cause', 'Two things appear together in the data, but one does not necessarily cause the other.'],
  ], [1.7, 4.5]),
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

L.save(L.buildDocument({
  font: 'Times New Roman', size: 24, accent: '000000', plain: true, children,
  title: 'Project Report: Experiments 8, 9 and 10', footerText: 'Project Report (Experiments 8, 9, 10)',
  footer: { left: 'Nikshey Yadav', right: '231302221' },
}), L.path.join(__dirname, 'Project_Report_Experiments_8_9_10.docx'));
