// Builds YouTube_Project_Notes_Part2.docx  (run: node build_notes.js)
const L = require('./lib_docx');
const K = L.kit({ font: 'Calibri', size: 22, accent: '0E9F6E', dark: '1A2B4C' });
const { p, heading: h, bullets, numbered, figure, callout, table, gap, pageBreak, banner } = K;
const read = (f) => { try { return JSON.parse(L.fs.readFileSync(L.path.join(L.ASSETS, f), 'utf8')); } catch { return null; } };
const runsInfo = read('ai_coach_runs.json');
const testsTotal = (read('diagrams/tests_total.json') || { total: 131 }).total;
const D = (f) => `diagrams/${f}.png`;
const S = (f) => `screens/parts/${f}.png`;
const NAVY = '1A2B4C', GOLD = 'D4A72C', CORAL = 'E4572E', BLUE = '3B82F6';
const tip = (t, c) => callout('In one line', t, c || '0E9F6E', 'F2F8F5');
const eg = (t) => callout('Real-life example', t, GOLD, 'FBF6E6');
const say = (t) => callout('Say this in the viva', t, BLUE, 'EEF4FF');

const c = [];

// ---------------------------------------------------------------- title
c.push(
  gap(500),
  new L.Paragraph({ alignment: L.AlignmentType.LEFT, spacing: { after: 80 }, children: [new L.TextRun({ text: 'AI-Based YouTube Analytics and Content Strategy Prediction', bold: true, size: 44, font: 'Calibri', color: NAVY })] }),
  new L.Paragraph({ spacing: { after: 240 }, children: [new L.TextRun({ text: 'Progress Notes, Part 2: What We Built After the Model', size: 30, font: 'Calibri', color: '0E9F6E' })] }),
  p('Part 1 (sections 1 to 5) explained the data, the cleaning, the features, the first models and their results. **This Part 2 continues from section 6.** It explains, in very simple words, everything new: the explanations, the honest ranges, the AI Coach, how to run it on any laptop, the tests and the online version. Every section has a picture. Read slowly, look at the picture, then read the "In one line" box.'),
  gap(100),
  ...figure(D('architecture'), 6.6, 'The whole project on one page. We will go through it piece by piece.'),
  callout('How to use these notes', ['1. Read the section.  2. Look at the picture.  3. Say the "In one line" box in your own words.', '4. At the end (section 15) there is a cheat sheet, a glossary and a question-answer list for the review.'], NAVY, 'EEF1F6'),
  pageBreak(),
);

// ---------------------------------------------------------------- 6 big picture
c.push(
  banner('6. The Big Picture: What Did We Build?', NAVY),
  p('Before, we had **a model that gives a number** (expected views). That alone is not very useful. A YouTuber asks: __why this number? how sure are you? what should I change? when should I post?__ So we built a full app called **Signal Studio** that answers all of these questions.'),
  eg('Think of a **clinic**. Reception collects your details (the data). The test lab runs your tests (the ML model). The doctor explains the report (the explanations). Another doctor gives a second opinion (similar videos). Finally you get a prescription written in simple words (the AI Coach).'),
  gap(80),
  ...figure(D('pipeline'), 6.6, 'The eight steps of the project. Every step is a real script with tests.'),
  h(2, 'What the app can do (seven tabs)'),
  table(['Tab', 'The question it answers', 'In simple words'], [
    ['Forecast studio', 'How many views and how much engagement?', 'The ML model gives the number, with a range'],
    ['Best time', 'When should I post?', 'Tries all 168 hours of the week'],
    ['Title lab', 'What small change helps?', 'Tests 12 small edits and ranks them'],
    ['AI Coach', 'What should I change first and why?', 'A small AI on the laptop writes the advice'],
    ['Similar videos', 'Does a different method agree?', 'Finds look-alike trending videos'],
    ['Scenario lab', 'Draft A or Draft B?', 'Compares two drafts side by side'],
    ['Model brief', 'How good is it really?', 'Shows scores and honest limits'],
  ], [1.4, 2.4, 2.8]),
  gap(),
  tip('Signal Studio does not only predict. It **predicts, explains, measures its own doubt, and suggests changes**.'),
  pageBreak(),
);

// ---------------------------------------------------------------- 7 improvements
c.push(
  banner('7. We Fixed Hidden Mistakes and Improved the Model', NAVY),
  p('After Part 1 we checked our own code like a teacher checking homework. We found **three hidden mistakes**. This is a good thing to tell in the review: it shows we tested honestly.'),
  table(['Mistake we found', 'Simple explanation', 'What we did'], [
    ['Hashtags were never counted', 'We wrote the pattern with an extra backslash, so the computer was looking for a symbol nobody types. It is like searching for "#study" but typing "\\#study".', 'Fixed the pattern, added a test'],
    ['Tags had quotation marks', 'In the Kaggle data tags look like "study tips" (with quote marks). When a user types tags there are no quote marks. So the same tag looked different.', 'Cleaned both the same way'],
    ['Category 29 was "Unknown"', 'The category list we had did not contain number 29. YouTube\'s official list says it is "Nonprofits & Activism".', 'Added the name'],
  ], [1.7, 3.3, 1.6]),
  gap(),
  p('We also **added many new features** (still only things known before publishing): title punctuation and emoji, how many words are urgent or "how-to" words, tag length, links and hashtags in the description, weekend flag, and the time of day as a circle (so 11 PM and 12 AM are neighbours).'),
  h(2, 'The new scores'),
  ...figure(D('r2_progress'), 5.8, 'R² score: 0 means useless, 1 means perfect. Higher is better.'),
  table(['Test', 'Views', 'Engagement'], [
    ['Linear Regression (baseline)', '0.20', '0.38'],
    ['First Random Forest', '0.38', '0.61'],
    ['Final model, 5-fold test', '0.42', '0.64'],
    ['Final model, on LATER videos', '0.37', '0.53'],
  ], [3, 1.5, 1.5]),
  gap(),
  eg('The "later videos" test is like **practising with last year\'s papers and then writing this year\'s exam**. It is harder, so the score is a bit lower. But it is the more honest score.'),
  gap(80),
  tip('The model got a little better, and we reported the harder test too, so nobody can say we showed only good numbers.'),
  pageBreak(),
);

// ---------------------------------------------------------------- 8 shapley
c.push(
  banner('8. "Why This Forecast?" (Shapley Values)', NAVY),
  p('The model says **78.1K views**. A creator asks: __which of my choices caused that?__ Our app splits the answer into five groups: **title, tags, description, timing and category**.'),
  h(2, 'The idea with a group-project story'),
  eg('Three friends do a group project and get 90 marks together. How do we share the credit **fairly**? Maybe Asha is great at ideas, Ravi is great at writing. If we only look at who joined first, the credit changes! So we try **every possible joining order** and average each person\'s contribution. That fair share is the **Shapley value**.'),
  gap(80),
  p('We do the same with our five groups. We start from a "typical trending video" and add the draft\'s title, then tags, then description... in **every possible order**. Five groups give only 5 x 4 x 3 x 2 x 1 = 120 orders, which is just 32 different combinations, so the computer finds the exact answer quickly.'),
  ...figure(D('shapley_waterfall'), 5.8, 'A REAL result for our example draft. Green pushes views up, red pushes them down.'),
  h(2, 'How to read the picture'),
  ...bullets([
    'A typical trending video is forecast at about **234K** views. Our draft gets **78.1K**.',
    '**Title packaging +32%**: the title helps a lot (it starts with a number and has the word "tips").',
    '**Tags -13%** and **Description -10%**: both are shorter than usual, so they pull the forecast down. These are easy to fix!',
    '**Category -67%**: Education videos simply get fewer views than Music or Movies in this data. This does **not** mean our video is bad, and we cannot change the category once we know what we are making.',
  ]),
  callout('Remember', 'The bars always add up exactly to the difference between "typical" and "our forecast". We even wrote a test for this.', CORAL, 'FDF1EE'),
  gap(80),
  say('We use exact Shapley values over five groups of creator-controlled choices. They are associations that the model learned, not proof of cause and effect.'),
  pageBreak(),
);

// ---------------------------------------------------------------- 9 uncertainty
c.push(
  banner('9. "How Sure Are We?" (Honest Ranges)', NAVY),
  p('A single number like "78.1K" looks very sure. But no one can be sure about a video. So our app always shows a **range**.'),
  eg('A weather app says "70 percent chance of rain", not "it will rain". Our app says "views between 22.5K and 271.5K", not "exactly 78.1K".'),
  gap(80),
  h(2, 'How do we build the range?'),
  ...numbered([
    'The model makes predictions on videos it has **not** seen during training, and we note how wrong it was each time.',
    'We find the error size that covers **80 percent** of those cases.',
    'We draw the range around every new forecast with that size. So about 8 out of 10 real values should fall inside.',
  ]),
  p('This method is called **split-conformal prediction**. You can just say "a range with a tested promise".'),
  ...figure(D('conformal'), 6.5, 'Left: a range for our draft. Right: we TESTED the promise (target is 80 percent).'),
  h(2, 'The best part: we tested the promise'),
  p('Many projects only **claim** that their range is 80 percent. We **measured** it: on shuffled data it held **80.0 percent**, and on **later videos** it held **79.7 percent** (views) and **80.9 percent** (engagement). The promise was kept.'),
  callout('Why is the range so wide?', 'Because title, tags and description explain only part of what happens to a video. The rest (thumbnail, channel fame, YouTube\'s own push) is not in our data. A wide range that is correct is better than a narrow range that is wrong.', CORAL, 'FDF1EE'),
  gap(80),
  say('Our 80 percent intervals were calibrated on out-of-fold errors and their coverage was measured on a later-in-time hold-out: 79.7 and 80.9 percent.'),
  pageBreak(),
);

// ---------------------------------------------------------------- 10 decision tools
c.push(
  banner('10. The Decision Tools: Best Time, Title Lab, Keywords, Look-alikes', NAVY),
  h(2, '10.1 Best time to post'),
  p('We ask the model the same question 168 times: the same video, but posted at every hour of every day (7 days x 24 hours). The picture is a **heat map**: darker green means more forecast views. We also average neighbouring hours, so one strange hour cannot fool us.'),
  ...figure(D('best_time'), 6.3, 'Real heat map for our draft. Red boxes are the best three slots; the dashed box is our planned time.'),
  tip('Timing changes the forecast only a little (about 9 percent between the best slot and a normal slot). **What you post matters more than when you post.**'),
  gap(100),
  h(2, '10.2 Title lab'),
  p('The app makes about **12 small edits** to your draft: add a number, turn it into a question, start with "How to", add hashtags, add a "please subscribe" line, and so on. The ML model scores each edited version and ranks them. One click on **Apply** puts the edit into your draft.'),
  ...figure(S('title_lab'), 6.2, 'Title lab from the real app. Each idea shows the change the model expects.'),
  callout('Careful', 'These are patterns the model **noticed**. They are not promises. Always keep the title honest.', CORAL, 'FDF1EE'),
  gap(100),
  h(2, '10.3 Keyword radar'),
  p('For every word in your title we show what happened to past trending videos with that word. To avoid names of single channels, we only keep words that appear in **at least 25 videos from at least 25 different channels**.'),
  ...figure(D('keywords'), 5.6, 'Words like "trailer" and "song" travel with big audiences; "news" and "exam" with smaller ones.'),
  h(2, '10.4 Similar videos (a second opinion)'),
  p('This tool uses **no ML model at all**. It turns each title and its tags into a list of numbers (TF-IDF, which gives more importance to rare, meaningful words) and finds the trending videos that are closest to yours. If their median views are close to our forecast, we trust the forecast more. If they are far apart, it is a warning.'),
  ...figure(S('similar'), 6.0, 'Look-alike videos found for the example draft.'),
  pageBreak(),
);

// ---------------------------------------------------------------- 11 ai coach
c.push(
  banner('11. The AI Coach (the Most Exciting Part)', NAVY),
  h(2, '11.1 What is an LLM?'),
  p('An LLM (Large Language Model) is a computer program that has read a huge amount of text and learned to **continue sentences**. It is like the suggestion bar on your phone keyboard, but millions of times bigger. That is why it can write good advice in plain English.'),
  h(2, '11.2 The problem: AI can confidently lie'),
  p('The same skill that makes it fluent also makes it **make things up**. This is called **hallucination**. It happened to us for real:'),
  ...figure(D('hallucination'), 5.6, 'A REAL example from our testing. The AI wrote 8.69 percent. The ML model said 4.69 percent.'),
  p('A small typing mistake in a number could mislead a creator. So we never let the AI touch numbers.'),
  h(2, '11.3 Our solution: AI writes, ML counts, checkers verify'),
  ...figure(D('ai_coach_flow'), 6.6, 'The AI Coach pipeline. The AI only appears once, and its words are checked before you see them.'),
  eg('It is like an **open-book exam**. The AI may only use the "evidence sheet" we give it (facts numbered E1, E2, E3...). Then a strict teacher checks every sentence. A sentence with a wrong number is crossed out; the good sentences stay.'),
  gap(80),
  ...figure(D('hybrid_design'), 6.0, 'Rules decide what to improve. The AI writes the words. Checkers filter each sentence.'),
  h(2, '11.4 What exactly do the checkers test?'),
  ...bullets([
    '**Numbers:** every figure with %, K or M must exist in the evidence.',
    '**Promises:** words like "definitely" or "will go viral" are not allowed.',
    '**Links and HTML:** not allowed (safety).',
    '**Titles:** must not repeat your title, must not be ALL CAPS, and must reuse your own words (no unrelated clickbait).',
    '**Advice about timing:** allowed only when the data really supports it.',
  ]),
  h(2, '11.5 What if the AI fails? The step-down chain'),
  eg('Think of **a senior student, then a junior student, then the textbook**. First we ask the senior (main AI, 3 billion parameters). If the senior gives a bad answer or takes too long, we ask the junior (lite AI, 0.5 billion parameters). If even that fails, we just read the textbook (rule-based advice that needs no AI). You always get an answer.'),
  gap(80),
  h(2, '11.6 What really happened when we ran it'),
);
if (runsInfo && runsInfo.runs && runsInfo.runs.length) {
  c.push(
    p(`We ran the **real** AI on four example videos on our laptop (${runsInfo.device}, no graphics card):`),
    table(['Example video', 'Who wrote the advice', 'Time', 'Sentences removed by checkers'],
      runsInfo.runs.map((r) => [r.draft, r.source === 'llm' ? (r.tier === 'main' ? `main AI (${r.model})` : `lite AI (${r.model})`) : 'rules (no AI)', `${r.seconds} seconds`, String(r.dropped)]), [1.5, 2.2, 1, 1.7]),
    gap(),
  );
}
c.push(
  p('We also learned something important along the way. Our **first design** asked the AI to write the full structured answer. It took **102 seconds** and failed. So we redesigned it: the rules prepare the skeleton and the AI only fills in the words. After that, a good answer takes about **35 to 80 seconds** on a laptop without a graphics card. We also fixed one more thing the tests showed: sometimes the 3B AI wrote a whole tag list as one long string, and our strict checker rejected the answer for that tiny slip. Now small slips like that are repaired and the main AI gets one retry. After these fixes **all four example videos were answered by the main AI in about 37 seconds each**.'),
  callout('Remember', 'We did **not** use a fake AI. All the AI results come from a real model running on our own laptop.', NAVY, 'EEF1F6'),
  gap(80),
  ...figure(S('ai_coach_a'), 6.0, 'The AI Coach tab in the real app: it shows which device and which AI model are used.'),
  ...figure(S('ai_coach_b'), 6.0, 'The advice: priorities, title and tag ideas (re-scored by the ML model), description tips, timing and limits.'),
  say('The language model never produces numbers. It receives numbered evidence, writes only wording, and every sentence is checked. If it fails we step down to a lite model and then to rules.'),
  pageBreak(),
);

// ---------------------------------------------------------------- 12 local ai
c.push(
  banner('12. Running the AI on Our Own Laptops', NAVY),
  p('ChatGPT-like tools run on big company computers on the internet. Ours runs **on your own laptop**, using a free program called **Ollama**. Benefits: it is free, it works without internet after the download, and **your draft never leaves your computer**.'),
  h(2, 'Models and their sizes'),
  p('An AI model is a big file. "3b" means 3 billion numbers inside it. Bigger models are smarter but need more memory and are slower.'),
  table(['Model', 'Size on disk', 'Where it runs well'], [
    ['qwen2.5:0.5b (lite)', '0.4 GB', 'Anywhere; our safety net'],
    ['qwen2.5:1.5b', '1.0 GB', 'Laptops with 8 GB RAM'],
    ['qwen2.5:3b (main on our laptop)', '1.9 GB', 'CPU-only laptops with 16 GB RAM'],
    ['qwen2.5:7b', '4.7 GB', 'Laptops with an 8 GB NVIDIA graphics card'],
  ], [2.4, 1.2, 3]),
  gap(),
  h(2, 'The app picks the model by itself'),
  p('When the app starts, it checks your computer: how much RAM, and is there an NVIDIA graphics card (GPU) and how much memory does it have? Then it chooses the best model that will not make the computer struggle.'),
  ...figure(D('device_tiers'), 5.9, 'Device to model. The lite model is always kept as a backup.'),
  eg('A **CPU** is like one very smart worker. A **GPU** is like hundreds of simple workers who are excellent at the same kind of math that AI needs. So the friend\'s laptop with the RTX 5050 GPU can run a bigger model faster.'),
  gap(80),
  callout('Honest note', 'Our laptop has no graphics card, so we tested the 3B and 0.5B models here. The 7B model for the RTX 5050 laptop is **planned but not tested**, because we do not have that laptop here.', CORAL, 'FDF1EE'),
  pageBreak(),
);

// ---------------------------------------------------------------- 13 run anywhere
c.push(
  banner('13. Running the Project on ANY Laptop (Like Your Friend\'s)', NAVY),
  p('We made a **launcher script** so nobody has to remember many commands. It does the boring work for you.'),
  ...figure(D('run_steps'), 6.4, 'Three steps. The script does the rest.'),
  h(2, 'What you need first'),
  ...bullets(['**Python 3.10 or newer** (python.org, or on Windows: winget install Python.Python.3.11)', '**Git** (git-scm.com)', 'Internet for the first run (downloads).']),
  h(2, 'The steps'),
  ...numbered([
    'Open PowerShell and type: **git clone https://github.com/NiksheyYadav/youtube-strategy-prediction.git**',
    'Type: **cd youtube-strategy-prediction**',
    'Type: **.\\run.ps1** (Windows) or **./run.sh** (Mac or Linux). You can also double-click **run.bat**.',
    'The script creates a clean environment, installs the libraries, checks the laptop, installs Ollama and downloads the right AI model (it **asks first**), and opens the app in the browser.',
  ]),
  callout('Useful options', ['**.\\run.ps1 -Check** shows what would happen and changes nothing.', '**.\\run.ps1 -Yes** says yes to every question (good for unattended setup).', '**.\\run.ps1 -NoLlm** skips the AI; you still get rule-based advice.'], NAVY, 'EEF1F6'),
  gap(100),
  h(2, 'Will it be easy on the friend\'s laptop? An honest answer'),
  table(['Question', 'Answer'], [
    ['Will the app itself run?', 'Yes. It needs only Python and the libraries the script installs. The trained model is inside the project.'],
    ['Will the AI part work?', 'Very likely, because the script checks the device and falls back to smaller models or to rules. For the RTX 5050 it will plan the 7B model (4.7 GB). **We have not tested this on that laptop.**'],
    ['How long is the first run?', 'Mostly waiting for downloads: Ollama is about 1.7 GB and the 7B model about 4.7 GB. On slow Wi-Fi this can take a long time.'],
    ['Can we avoid the big download?', 'Idea (untested): copy the folder C:\\Users\\<name>\\.ollama\\models from our laptop on a pen drive. It contains the 3B and 0.5B models.'],
    ['What if the AI part fails?', 'The app still works with rule-based advice. Nothing breaks.'],
    ['NVIDIA graphics card note', 'Update the NVIDIA driver first. Very new cards (RTX 50 series) need a recent Ollama; the script installs the latest one.'],
  ], [1.9, 4.7]),
  pageBreak(),
);

// ---------------------------------------------------------------- 14 tests
c.push(
  banner('14. How Do We Know It Works? (Tests)', NAVY),
  p(`We wrote **${testsTotal} automatic tests**. A test is a small program that checks one thing and says pass or fail. Running all of them takes about two minutes.`),
  ...figure(D('tests'), 5.6, 'Tests by area. More tests means more things are protected.'),
  h(2, 'Three special tests'),
  ...bullets([
    '**Golden test ("photocopy test"):** before adding the AI Coach, we saved the model\'s answers for 7 drafts. After adding it, we check that the answers are **identical**. So the new AI part could not secretly change a forecast.',
    '**Real-model tests:** they call the real AI on the laptop. If the AI is not available (for example on GitHub\'s test machine), they are skipped.',
    '**Password test:** it scans the project to make sure no password or key was saved by mistake.',
  ]),
  eg('Tests are like a **teacher who corrects your homework automatically** every time you change something. If you break something, you know immediately.'),
  gap(80),
  tip('GitHub Actions is a robot that runs all tests every time we upload code. Our last run was green (all passed).'),
  pageBreak(),
);

// ---------------------------------------------------------------- 15 online
c.push(
  banner('15. Putting It Online (and the "Cold Start" Problem)', NAVY),
  p('The app is online at **youtube-strategy-predictor.onrender.com**. We used a free hosting service called **Render**.'),
  eg('The free plan is like a **shop that locks its doors if no customer comes for 15 minutes**. The next customer must wait 30 to 60 seconds while the shop opens again. That wait is called a **cold start**.'),
  gap(80),
  ...figure(D('cold_start'), 5.8, 'Our fix: a robot visits the shop every 10 minutes, so it never closes.'),
  ...bullets([
    'We added a **GitHub Action** that sends a small "hello" request every 10 minutes.',
    'GitHub is sometimes slow to start new schedules, so before a demo, open the website one minute early.',
    'The online version has **no AI model** (the free server is too small). It shows the rule-based advice. The AI Coach with the real model runs on our laptops.',
  ]),
  pageBreak(),
);

// ---------------------------------------------------------------- 16 cheat sheet
c.push(
  banner('16. Cheat Sheet for the Review', NAVY),
  h(2, 'Explain the whole project in 30 seconds'),
  callout('30-second version', 'We built a tool for YouTubers. You type a draft title, tags, description, category and time, and a machine learning model estimates the views and engagement. The tool then explains **why**, gives an **honest range**, suggests **when to post and what to change**, and an AI running on the laptop writes the advice. The AI cannot touch the numbers and every sentence is checked. It runs on any laptop with one command.', NAVY, 'EEF1F6'),
  gap(100),
  h(2, 'Numbers to remember'),
  table(['What', 'Number'], [
    ['Raw rows to unique videos', '37,352 to 16,307'],
    ['R² views / engagement (final, 5-fold)', '0.42 / 0.64'],
    ['R² on later videos', '0.37 / 0.53'],
    ['Range promise / measured', '80 percent / 79.7 and 80.9 percent'],
    ['Groups in the Shapley explanation', '5 (title, tags, description, timing, category)'],
    ['Time slots checked', '168 (7 days x 24 hours)'],
    ['Local AI models', '3B main, 0.5B lite (this laptop); 7B planned for 8 GB GPU'],
    ['Automatic tests', String(testsTotal)],
  ], [3.4, 3.2]),
  gap(100),
  h(2, 'Likely questions and short answers'),
  table(['Question', 'Short answer'], [
    ['What is new compared to Review 1?', 'Explanations (Shapley), tested ranges, best-time map, title lab, look-alike videos, an on-device AI Coach, one-command setup, tests and an online version.'],
    ['Can it predict if a video will go viral?', 'No. The data has only videos that already trended, so it estimates relative performance among them.'],
    ['Why not use likes as an input?', 'Likes are known only after publishing. Using them would be cheating.'],
    ['What does Shapley do?', 'Shares the forecast fairly among title, tags, description, timing and category by trying every order.'],
    ['Is your range real or just a claim?', 'Tested: 80.0 percent normally, 79.7 and 80.9 percent on later videos.'],
    ['Why not just use ChatGPT?', 'Ours runs on the laptop: free, private, works offline. And it cannot change the numbers.'],
    ['What if the AI lies?', 'Each sentence is checked against evidence; wrong sentences are removed. If the AI fails we use a smaller AI, then rules.'],
    ['Why is the AI slow?', 'A laptop CPU is slow for AI (about 35 to 80 seconds). A GPU is faster.'],
    ['What are the limits?', 'Only trending videos from 2017-2018; no thumbnails or channel data; advice shows associations, not causes.'],
    ['Did you test it on the RTX 5050 laptop?', 'Not yet. The app detects the GPU and plans the 7B model, but that part is untested.'],
  ], [2.4, 4.2]),
  gap(100),
  h(2, 'Glossary (simple words)'),
  table(['Word', 'Meaning'], [
    ['Feature', 'A clue we give the model, like title length.'],
    ['Target', 'The thing we want to predict (views, engagement).'],
    ['Random Forest', 'Many decision trees voting together.'],
    ['R²', 'Score from 0 to 1 for how much of the ups and downs the model explains.'],
    ['Cross-validation', 'Testing several times on different slices of data.'],
    ['Overfitting', 'Memorising the practice questions instead of learning.'],
    ['Shapley value', 'A fair share of credit, found by trying every order.'],
    ['Conformal range', 'A range with a promise that is tested.'],
    ['LLM', 'A program that writes text by predicting the next words.'],
    ['Hallucination', 'When an LLM confidently makes something up.'],
    ['Ollama', 'A free program that runs AI models on your own computer.'],
    ['GPU / VRAM', 'Graphics card and its memory; great for AI.'],
    ['Fallback', 'The backup that takes over when the first choice fails.'],
    ['Golden test', 'A test that proves an answer did not change.'],
    ['Cold start', 'The wait when a sleeping website wakes up.'],
  ], [1.6, 5]),
);

L.save(L.buildDocument({ font: 'Calibri', size: 22, accent: '0E9F6E', children: c, footerText: 'Signal Studio: Project Notes, Part 2' }),
  L.path.join(__dirname, 'YouTube_Project_Notes_Part2.docx'));
