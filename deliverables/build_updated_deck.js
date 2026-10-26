// Builds Updated_Presentation_Review2.docx-style deck in the visual style of TA1_Presentation.pptx
// run:  set NODE_PATH=C:\tmpdeck\node_modules  &&  node build_updated_deck.js
const pptxgen = require('pptxgenjs');
const fs = require('fs');
const path = require('path');

const ASSETS = path.join(__dirname, 'assets');
const OUT = path.join(__dirname, 'Updated_Presentation_Review2.pptx');
const C = { navy: '1A2B4C', paper: 'F7F8FA', ink: '1F2937', gray: '6B7280', green: '0E9F6E', gold: 'D4A72C', soft: '9FB0CC', pale: 'F2F5FA', line: 'D9DEE7', coral: 'E4572E' };
const read = (f) => { try { return JSON.parse(fs.readFileSync(path.join(ASSETS, f), 'utf8')); } catch { return null; } };
const runsInfo = read('ai_coach_runs.json');
const testsTotal = (read('diagrams/tests_total.json') || { total: 131 }).total;

const pptx = new pptxgen();
pptx.defineLayout({ name: 'W', width: 13.333, height: 7.5 });
pptx.layout = 'W';
pptx.title = 'AI-Based YouTube Analytics and Content Strategy Prediction: Review 2';
pptx.company = 'SGT University';

const slides = [];
function newSlide(dark = false) {
  const s = pptx.addSlide();
  s.background = { color: dark ? C.navy : C.paper };
  slides.push({ s, dark });
  return s;
}
function chrome(s, dark, label, title) {
  const muted = dark ? C.soft : C.gray;
  s.addText([{ text: 'SGT UNIVERSITY', options: { bold: true } }, { text: '  ·  DEPT. OF COMPUTER SCIENCE & ENGINEERING, SOET', options: { bold: true } }], { x: 0.45, y: 0.18, w: 9, h: 0.25, fontSize: 9, color: muted, fontFace: 'Calibri', charSpacing: 1 });
  s.addText('Computer Science & Engineering, SOET — SGT University', { x: 0.45, y: 7.1, w: 7, h: 0.25, fontSize: 8, color: muted, fontFace: 'Calibri' });
  if (label) s.addText(label, { x: 0.55, y: 0.6, w: 8, h: 0.3, fontSize: 11, bold: true, color: C.green, fontFace: 'Calibri', charSpacing: 2 });
  if (title) s.addText(title, { x: 0.55, y: 0.88, w: 12.2, h: 0.7, fontSize: 30, bold: true, color: dark ? 'FFFFFF' : C.ink, fontFace: 'Cambria' });
}
function bullet(s, text, x, y, w, size = 16, color = C.ink) {
  s.addShape(pptx.ShapeType.ellipse, { x, y: y + 0.07, w: 0.2, h: 0.2, fill: { color: C.paper }, line: { color: C.green, width: 1.5 } });
  s.addText(text, { x: x + 0.38, y: y - 0.04, w, h: 0.62, fontSize: size, color, fontFace: 'Calibri', valign: 'top' });
}
function fit(s, file, x, y, w, h) {
  const b = fs.readFileSync(path.join(ASSETS, file));
  const iw = b.readUInt32BE(16), ih = b.readUInt32BE(20);
  const r = Math.min(w / iw, h / ih);
  const pw = iw * r, ph = ih * r;
  s.addImage({ path: path.join(ASSETS, file), x: x + (w - pw) / 2, y: y + (h - ph) / 2, w: pw, h: ph });
}
function stat(s, label, from, to, x, y, color = C.gold) {
  s.addText(label, { x, y, w: 4.6, h: 0.3, fontSize: 10, bold: true, color: C.gray, fontFace: 'Calibri', charSpacing: 1 });
  s.addShape(pptx.ShapeType.line, { x, y: y + 0.35, w: 4.6, h: 0, line: { color: C.green, width: 1.2 } });
  s.addText([{ text: `${from}  →  `, options: { fontSize: 26, color: C.gray } }, { text: to, options: { fontSize: 54, bold: true, color } }], { x, y: y + 0.45, w: 5.4, h: 1.1, fontFace: 'Cambria', valign: 'middle' });
}
const D = (f) => `diagrams/${f}.png`;
const P = (f) => `screens/parts/${f}.png`;

// 1 ------------------------------------------------------------------ title
{
  const s = newSlide(true);
  chrome(s, true);
  s.addText('THEMATIC ASSESSMENT — REVIEW 2 (UPDATED)', { x: 0.6, y: 1.15, w: 9, h: 0.3, fontSize: 11, bold: true, color: C.gold, fontFace: 'Calibri', charSpacing: 2 });
  s.addText('AI-Based YouTube Analytics and Content Strategy Prediction', { x: 0.6, y: 1.6, w: 10.5, h: 1.6, fontSize: 38, bold: true, color: 'FFFFFF', fontFace: 'Cambria', valign: 'top' });
  s.addText('Signal Studio: explainable forecasts, honest uncertainty and an on-device AI Coach', { x: 0.6, y: 3.3, w: 10.5, h: 0.5, fontSize: 18, color: C.soft, fontFace: 'Calibri' });
  const team = [['Vishal Kumar Upadhyay', '231302157'], ['Nikshey Yadav', '231302221'], ['Aditya Chauhan', '231302230'], ['Arpit Gupta', '231302216'], ['Yuvraj Singh Yadav', '231302221']];
  team.forEach(([n, r], i) => s.addText([{ text: n, options: { bold: true, color: C.pale } }, { text: `   ·   ${r}`, options: { color: C.soft } }], { x: 0.6, y: 4.3 + i * 0.4, w: 8, h: 0.35, fontSize: 14, fontFace: 'Calibri' }));
  s.addNotes('Review 2 builds on Review 1. In Review 1 we cleaned the data and trained the model. Now we explain the predictions, measure uncertainty, add an AI Coach that runs on the laptop, and package everything so it runs anywhere.');
}

// 2 ------------------------------------------------------------------ problem
{
  const s = newSlide();
  chrome(s, false, 'MOTIVATION', 'Problem Statement and What Is New');
  s.addText('Can we predict how a YouTube video will perform before it is published?', { x: 0.55, y: 1.75, w: 12, h: 0.5, fontSize: 20, color: C.ink, fontFace: 'Cambria', italic: true });
  bullet(s, 'Using only metadata a creator already controls: title, tags, description, category, timing', 0.6, 2.55, 11.5);
  bullet(s, 'Goal: turn model findings into practical, explained content-strategy advice', 0.6, 3.15, 11.5);
  s.addShape(pptx.ShapeType.roundRect, { x: 0.55, y: 4.0, w: 12.2, h: 2.6, fill: { color: C.pale }, line: { color: C.line }, rectRadius: 0.1 });
  s.addText('NEW SINCE REVIEW 1', { x: 0.85, y: 4.15, w: 6, h: 0.3, fontSize: 11, bold: true, color: C.green, fontFace: 'Calibri', charSpacing: 2 });
  const items = ['Why this forecast: exact Shapley explanations', 'How sure are we: tested 80% ranges', 'Best time, Title lab and look-alike videos', 'AI Coach: real on-device language model', 'One-command setup for any laptop', `${testsTotal} automated tests and an online version`];
  items.forEach((t, i) => s.addText('•  ' + t, { x: 0.85 + (i % 2) * 6.0, y: 4.6 + Math.floor(i / 2) * 0.62, w: 5.8, h: 0.5, fontSize: 15, color: C.ink, fontFace: 'Calibri' }));
  s.addNotes('Say the problem in one sentence, then list what is new. The rest of the deck follows this order.');
}

// 3 ------------------------------------------------------------------ dataset
{
  const s = newSlide();
  chrome(s, false, 'DATA', 'Dataset');
  s.addText('UNIQUE VIDEOS AFTER DEDUP', { x: 0.55, y: 1.8, w: 6, h: 0.3, fontSize: 10, bold: true, color: C.gray, fontFace: 'Calibri', charSpacing: 1 });
  s.addText([{ text: '37,352  →  ', options: { fontSize: 30, color: C.gray } }, { text: '16,307', options: { fontSize: 66, bold: true, color: C.green } }], { x: 0.55, y: 2.1, w: 7, h: 1.2, fontFace: 'Cambria', valign: 'middle' });
  bullet(s, 'Trending YouTube Video Statistics, Kaggle, India subset (2017-2018)', 0.6, 3.7, 7);
  bullet(s, 'One row = one video on one trending day, so the same video repeats; we keep the latest snapshot', 0.6, 4.3, 7);
  bullet(s, 'Limitation: only videos that already trended, so no failed-video comparison', 0.6, 5.1, 7);
  fit(s, D('funnel'), 8.0, 1.7, 4.8, 4.2);
  s.addNotes('The dataset repeats each video once per trending day. Counting all 37,352 rows would over-weight videos that trended longer, so we keep each video once: 16,307 unique videos.');
}

// 4 ------------------------------------------------------------------ pipeline
{
  const s = newSlide();
  chrome(s, false, 'METHOD', 'Pipeline Overview');
  fit(s, D('pipeline'), 0.5, 1.9, 12.3, 3.0);
  bullet(s, 'Every step is a real script with automated tests', 0.6, 5.3, 11.5);
  bullet(s, 'Leakage firewall: likes, dislikes and comments are outcomes only, never inputs', 0.6, 5.95, 11.5);
  s.addNotes('Eight steps from raw data to an online app. The important rule: likes and comments are never inputs, only part of the engagement target.');
}

// 5 ------------------------------------------------------------------ features
{
  const s = newSlide();
  chrome(s, false, 'METHOD', 'Features and Targets');
  s.addText('Features (30 inputs, known before publishing)', { x: 0.55, y: 1.8, w: 6.3, h: 0.4, fontSize: 18, bold: true, color: C.ink, fontFace: 'Cambria' });
  ['Title packaging: length, digits, ?, !, capitals, emoji, how-to and urgency words', 'Tags: count, length, multi-word share', 'Description: length, links, hashtags, call to action', 'Timing: day and hour in IST, weekend, circular hour', 'Category (one-hot)'].forEach((t, i) => bullet(s, t, 0.6, 2.4 + i * 0.62, 6.2, 14));
  s.addText('Targets (outputs)', { x: 7.4, y: 1.8, w: 5.3, h: 0.4, fontSize: 18, bold: true, color: C.ink, fontFace: 'Cambria' });
  bullet(s, 'Target 1: views, log-transformed', 7.45, 2.4, 5.2, 15);
  bullet(s, 'Target 2: engagement rate = (likes + comments) / views', 7.45, 3.0, 5.2, 15);
  s.addShape(pptx.ShapeType.roundRect, { x: 7.4, y: 4.0, w: 5.3, h: 1.6, fill: { color: C.pale }, line: { color: C.line }, rectRadius: 0.1 });
  s.addText('Audit fixes since Review 1: hashtags and www links were never counted, tag quote marks differed between training and live input, and category 29 showed as "Unknown". All fixed, tested and the model retrained.', { x: 7.6, y: 4.1, w: 4.95, h: 1.4, fontSize: 13, color: C.ink, fontFace: 'Calibri', valign: 'middle' });
  s.addNotes('We audited our own code and found three hidden mistakes. They are fixed and each has a regression test.');
}

// 6 ------------------------------------------------------------------ results
{
  const s = newSlide();
  chrome(s, false, 'RESULTS', 'Model Results');
  stat(s, 'VIEWS R²', '0.20', '0.42', 0.55, 1.8);
  stat(s, 'ENGAGEMENT RATE R²', '0.38', '0.64', 0.55, 3.7);
  s.addText('Baseline linear regression to the final Random Forest (5-fold cross-validation). On later-in-time videos: 0.37 and 0.53.', { x: 0.55, y: 5.55, w: 5.6, h: 0.9, fontSize: 13, color: C.gray, italic: true, fontFace: 'Calibri' });
  fit(s, D('r2_progress'), 6.6, 1.7, 6.3, 4.8);
  s.addNotes('R squared goes from 0.20 to 0.42 for views and from 0.38 to 0.64 for engagement. We also report the harder later-in-time test: 0.37 and 0.53.');
}

// 7 ------------------------------------------------------------------ importance
{
  const s = newSlide();
  chrome(s, false, 'RESULTS', 'What the Model Pays Attention To');
  fit(s, D('feature_groups'), 0.5, 1.7, 7.0, 4.9);
  bullet(s, 'Title packaging, description and tags are things a creator controls', 7.9, 2.0, 4.9, 15);
  bullet(s, 'Category matters a lot for audience size but cannot be changed once the content is decided', 7.9, 3.0, 4.9, 15);
  bullet(s, 'Views and engagement depend on partly different factors', 7.9, 4.1, 4.9, 15);
  s.addNotes('Global importance by group. Remember these are associations learned from data, not proof of cause and effect.');
}

// 8 ------------------------------------------------------------------ shapley
{
  const s = newSlide();
  chrome(s, false, 'NEW · EXPLAINABILITY', 'Why This Forecast? Exact Shapley Values');
  fit(s, D('shapley_waterfall'), 0.5, 1.7, 7.4, 4.8);
  bullet(s, 'Five groups of choices: title, tags, description, timing, category', 8.2, 2.0, 4.4, 15);
  bullet(s, 'Each group\'s fair share, found by trying every order (only 32 combinations)', 8.2, 3.0, 4.4, 15);
  bullet(s, 'Bars add up exactly to forecast minus a typical video (tested)', 8.2, 4.0, 4.4, 15);
  bullet(s, 'Real example: title +32%, tags -13%, description -10%', 8.2, 5.0, 4.4, 15);
  s.addNotes('Shapley idea: share credit fairly by averaging over every order. With five groups it is exact. Category is the biggest bar, but it is about audience size, not quality.');
}

// 9 ------------------------------------------------------------------ conformal
{
  const s = newSlide();
  chrome(s, false, 'NEW · UNCERTAINTY', 'How Sure Are We? Tested 80% Ranges');
  fit(s, D('conformal'), 0.5, 1.7, 8.0, 3.3);
  [['80.0%', 'out-of-fold'], ['79.7%', 'later uploads, views'], ['80.9%', 'later uploads, engagement']].forEach(([n, l], i) =>
    { s.addText(n, { x: 0.8 + i * 2.7, y: 5.1, w: 2.5, h: 0.8, fontSize: 40, bold: true, color: C.green, fontFace: 'Cambria' }); s.addText(l, { x: 0.8 + i * 2.7, y: 5.85, w: 2.6, h: 0.4, fontSize: 12, color: C.gray, fontFace: 'Calibri' }); });
  bullet(s, 'Range from split-conformal prediction on out-of-fold errors', 8.9, 2.0, 4.0, 14);
  bullet(s, 'The promise was measured, not assumed', 8.9, 2.9, 4.0, 14);
  bullet(s, 'Typical views forecast: x0.29 to x3.5 of the truth, wide because metadata is a moderate signal', 8.9, 3.7, 4.0, 14);
  s.addNotes('We do not only claim an 80 percent range, we tested it on later videos: 79.7 and 80.9 percent.');
}

// 10 ----------------------------------------------------------------- tools
{
  const s = newSlide();
  chrome(s, false, 'NEW · DECISION TOOLS', 'Best Time, Title Lab and Look-alikes');
  fit(s, D('best_time'), 0.4, 1.7, 6.4, 2.6);
  bullet(s, 'Best time: the same draft forecast in all 168 weekly slots (IST)', 0.6, 4.6, 6.2, 14);
  bullet(s, 'Title lab: ~12 edits re-scored by the model and ranked, one-click Apply', 0.6, 5.35, 6.2, 14);
  bullet(s, 'Look-alikes: TF-IDF similar trending videos as a second opinion', 0.6, 6.0, 6.2, 14);
  fit(s, P('title_lab'), 6.9, 1.7, 6.1, 5.0);
  s.addNotes('Timing changes the forecast only about 9 percent, so what you post matters more than when you post. All edits are associations, not promises.');
}

// 11 ----------------------------------------------------------------- app
{
  const s = newSlide();
  chrome(s, false, 'NEW · THE APP', 'Signal Studio in Action');
  fit(s, P('forecast_inputs_output'), 0.5, 1.65, 6.3, 5.3);
  fit(s, P('forecast_why'), 7.0, 1.65, 5.9, 5.3);
  s.addNotes('Live demo order: load an example, generate the forecast, read the Shapley chart, then show best time and title lab.');
}

// 12 ----------------------------------------------------------------- ai coach
{
  const s = newSlide();
  chrome(s, false, 'NEW · AI COACH', 'An On-device AI That Cannot Change the Numbers');
  fit(s, D('ai_coach_flow'), 0.4, 1.7, 12.5, 3.7);
  bullet(s, 'ML model owns every number; re-scores any title or tag the AI proposes', 0.6, 5.6, 6.1, 14);
  bullet(s, 'AI sees only numbered evidence facts (E1, E2, ...)', 0.6, 6.2, 6.1, 14);
  bullet(s, 'Runs on the laptop with Ollama: free, private, no API key', 7.0, 5.6, 5.3, 14);
  bullet(s, 'Fallback chain: main AI, lite AI, rule-based advice', 7.0, 6.2, 5.3, 14);
  s.addNotes('The hybrid design: rules decide what to improve, the AI only writes the wording, checkers test every sentence.');
}

// 13 ----------------------------------------------------------------- safety
{
  const s = newSlide();
  chrome(s, false, 'NEW · SAFETY', 'Catching Hallucinations');
  fit(s, D('hallucination'), 0.4, 1.7, 6.6, 3.5);
  fit(s, D('hybrid_design'), 7.0, 1.7, 6.0, 2.6);
  bullet(s, 'Real case: the AI wrote 8.69% engagement; the ML model said 4.69%. The sentence was removed.', 0.6, 5.5, 6.2, 14);
  bullet(s, 'Each sentence is tested alone: numbers, promises, links, title quality', 7.2, 4.6, 5.6, 14);
  bullet(s, 'If nothing survives the checks, we step down to the next model', 7.2, 5.5, 5.6, 14);
  s.addNotes('This is a real example from our own testing, which is why we never let the AI touch numbers.');
}

// 14 ----------------------------------------------------------------- ai screenshots
{
  const s = newSlide();
  chrome(s, false, 'NEW · REAL RESULT', 'AI Coach Running the Real qwen2.5:3b Model');
  fit(s, P('ai_coach_a'), 0.4, 1.65, 6.3, 5.35);
  fit(s, P('ai_coach_b'), 6.9, 1.65, 6.0, 5.35);
  s.addNotes('This screenshot is from the real model on our laptop (no graphics card), about 40 seconds. Notice the ML numbers on top, the re-scored titles, and the removed sentence notice.');
}

// 15 ----------------------------------------------------------------- real evaluation + devices
{
  const s = newSlide();
  chrome(s, false, 'NEW · EVALUATION', 'Real Model Runs and Device-aware Choice');
  if (runsInfo && runsInfo.runs) {
    s.addText(`Real runs on ${runsInfo.device}`, { x: 0.55, y: 1.7, w: 6.5, h: 0.35, fontSize: 13, bold: true, color: C.gray, fontFace: 'Calibri' });
    const head = (t) => ({ text: t, options: { bold: true, color: 'FFFFFF', fill: { color: C.navy }, fontSize: 12, fontFace: 'Calibri' } });
    const rows = [[head('Draft'), head('Written by'), head('Time'), head('Removed')],
      ...runsInfo.runs.map((r) => [r.draft, r.source === 'llm' ? `${r.tier} AI (${r.model})` : 'rules', `${r.seconds} s`, String(r.dropped)].map((t) => ({ text: t, options: { fontSize: 12, fontFace: 'Calibri', color: C.ink } })))];
    s.addTable(rows, { x: 0.55, y: 2.15, w: 6.5, colW: [1.2, 3.0, 1.0, 1.3], border: { type: 'solid', color: C.line, pt: 0.75 }, fill: { color: 'FFFFFF' }, rowH: 0.45 });
    s.addText('Removed = model-written sentences discarded by the evidence checks.', { x: 0.55, y: 4.7, w: 6.5, h: 0.4, fontSize: 11, italic: true, color: C.gray, fontFace: 'Calibri' });
  }
  fit(s, D('device_tiers'), 7.2, 1.7, 5.8, 3.4);
  bullet(s, 'App detects RAM and NVIDIA GPU memory and picks the model size', 0.6, 5.4, 12, 14);
  bullet(s, 'RTX 5050 8 GB laptop: plans qwen2.5:7b (planned, not tested here); this CPU laptop: 3B', 0.6, 6.0, 12, 14);
  s.addNotes('Be honest: the 7B model for the RTX 5050 laptop is planned but untested because we do not have that laptop.');
}

// 16 ----------------------------------------------------------------- engineering
{
  const s = newSlide();
  chrome(s, false, 'ENGINEERING', `${testsTotal} Automated Tests and a One-command Launcher`);
  fit(s, D('tests'), 0.4, 1.7, 6.2, 4.9);
  bullet(s, 'Golden test: forecasts for 7 drafts identical before and after the AI Coach', 6.9, 2.0, 5.4, 14);
  bullet(s, 'Tests call the real local AI when it is available', 6.9, 3.0, 5.4, 14);
  bullet(s, 'GitHub Actions runs every test on each push; secret-scan test', 6.9, 3.9, 5.4, 14);
  bullet(s, 'run.ps1 / run.sh: sets up, detects the device, installs Ollama, pulls the model, starts the app', 6.9, 4.9, 5.4, 14);
  s.addNotes('The golden test is the key: it proves the AI layer cannot secretly change a forecast.');
}

// 17 ----------------------------------------------------------------- run anywhere
{
  const s = newSlide();
  chrome(s, false, 'DEPLOYMENT', 'Run Anywhere and Online');
  fit(s, D('run_steps'), 0.4, 1.7, 7.3, 2.1);
  fit(s, D('cold_start'), 0.4, 3.9, 7.3, 2.9);
  bullet(s, 'Needs only Python 3.10+ and git; first run downloads Ollama and a model after asking', 8.0, 2.0, 4.5, 14);
  bullet(s, 'If the AI cannot start, the app still works with rule-based advice', 8.0, 3.2, 4.5, 14);
  bullet(s, 'Online: youtube-strategy-predictor.onrender.com (rule-based mode)', 8.0, 4.2, 4.5, 14);
  bullet(s, 'Keep-warm ping every 10 minutes to avoid the free-tier cold start', 8.0, 5.2, 4.5, 14);
  s.addNotes('Open the online site a minute before the demo. The free server sleeps when idle.');
}

// 18 ----------------------------------------------------------------- limitations
{
  const s = newSlide();
  chrome(s, false, 'LIMITATIONS', 'Limitations and Honest Caveats');
  s.addText('VARIANCE EXPLAINED BY PRE-PUBLISH METADATA', { x: 0.55, y: 1.8, w: 8, h: 0.3, fontSize: 10, bold: true, color: C.gray, fontFace: 'Calibri', charSpacing: 1 });
  s.addShape(pptx.ShapeType.roundRect, { x: 0.55, y: 2.2, w: 8.6, h: 0.5, fill: { color: 'E6EAF0' }, line: { color: 'E6EAF0' }, rectRadius: 0.05 });
  s.addShape(pptx.ShapeType.roundRect, { x: 0.55, y: 2.2, w: 8.6 * 0.64, h: 0.5, fill: { color: C.green }, line: { color: C.green }, rectRadius: 0.05 });
  s.addShape(pptx.ShapeType.roundRect, { x: 0.55, y: 2.2, w: 8.6 * 0.42, h: 0.5, fill: { color: C.gold }, line: { color: C.gold }, rectRadius: 0.05 });
  s.addText('42% (views) to 64% (engagement)', { x: 9.3, y: 2.2, w: 3.6, h: 0.5, fontSize: 16, bold: true, color: C.ink, fontFace: 'Cambria', valign: 'middle' });
  s.addShape(pptx.ShapeType.rect, { x: 0.55, y: 2.85, w: 0.18, h: 0.18, fill: { color: C.gold }, line: { color: C.gold } });
  s.addText('views 42%', { x: 0.8, y: 2.78, w: 2, h: 0.3, fontSize: 11, color: C.gray, fontFace: 'Calibri' });
  s.addShape(pptx.ShapeType.rect, { x: 2.4, y: 2.85, w: 0.18, h: 0.18, fill: { color: C.green }, line: { color: C.green } });
  s.addText('engagement 64%', { x: 2.65, y: 2.78, w: 2.4, h: 0.3, fontSize: 11, color: C.gray, fontFace: 'Calibri' });
  ['Thumbnails, channel reputation and YouTube\'s ranking are not in the data', 'Only videos that already trended (India, 2017-2018): not a viral vs non-viral study', 'Shapley, keywords and edit rankings are associations, not causes', 'CPU laptop: AI answers take about 30 to 80 seconds; the 7B GPU path is untested', 'The online site runs without the AI model (free tier is too small)'].forEach((t, i) => bullet(s, t, 0.6, 3.4 + i * 0.68, 12, 15));
  s.addNotes('Say the limits out loud. Honest limits make the project more credible.');
}

// 19 ----------------------------------------------------------------- next
{
  const s = newSlide(true);
  chrome(s, true, 'NEXT STEPS', 'Where We Go From Here');
  [['STEP 1', 'Test on the RTX 5050 laptop', 'compare the 7B model with the 3B model'], ['STEP 2', 'Thumbnail and channel features', 'add the missing strong signals'], ['STEP 3', 'Broader data', 'include non-trending videos'], ['STEP 4', 'Creator study', 'check whether the advice is actually useful']].forEach(([a, b, c], i) => {
    const x = 0.7 + i * 3.1;
    s.addShape(pptx.ShapeType.roundRect, { x, y: 2.4, w: 2.8, h: 2.8, fill: { color: '22365E' }, line: { color: '2F4574' }, rectRadius: 0.1 });
    s.addText(a, { x: x + 0.2, y: 2.6, w: 2.4, h: 0.3, fontSize: 11, bold: true, color: C.gold, fontFace: 'Calibri', charSpacing: 2 });
    s.addText(b, { x: x + 0.2, y: 3.0, w: 2.4, h: 0.9, fontSize: 18, bold: true, color: 'FFFFFF', fontFace: 'Cambria', valign: 'top' });
    s.addText(c, { x: x + 0.2, y: 4.0, w: 2.4, h: 0.9, fontSize: 13, color: C.soft, fontFace: 'Calibri', valign: 'top' });
  });
  s.addText('Thank you. Questions?', { x: 0.7, y: 5.9, w: 8, h: 0.6, fontSize: 24, bold: true, color: C.gold, fontFace: 'Cambria' });
}

// page numbers ---------------------------------------------------------
slides.forEach(({ s, dark }, i) => s.addText(`${String(i + 1).padStart(2, '0')} / ${slides.length}`, { x: 11.9, y: 7.1, w: 1.0, h: 0.25, fontSize: 9, align: 'right', color: dark ? C.soft : C.gray, fontFace: 'Calibri' }));

pptx.writeFile({ fileName: OUT }).then(() => console.log('wrote', OUT)).catch((e) => { console.error(e); process.exit(1); });
