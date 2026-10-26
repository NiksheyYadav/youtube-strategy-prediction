const pptxgen = require("pptxgenjs");
const path = require("path");
const fs = require("fs");

const ROOT = path.resolve(__dirname, "..");
const OUT = path.join(ROOT, "deliverables", "TA4_Final_Presentation.pptx");
const reportImage = path.join(ROOT, "reports", "advanced_feature_importance.png");
const corrImage = path.join(ROOT, "reports", "eda_corr.png");

const pptx = new pptxgen();
pptx.layout = "LAYOUT_WIDE";
pptx.author = "AI/ML Project Team";
pptx.company = "SGT University";
pptx.subject = "AI-Based YouTube Analytics and Content Strategy Prediction";
pptx.title = "TA4 Final Presentation";
pptx.lang = "en-IN";
pptx.theme = {
  headFontFace: "Georgia",
  bodyFontFace: "Aptos",
  lang: "en-IN",
};
pptx.defineLayout({ name: "WIDE", width: 13.333, height: 7.5 });

const C = {
  ink: "071116", panel: "10232A", panel2: "15343C", cream: "F4EEE5",
  muted: "B9CFCA", mint: "67D8C7", teal: "00BFA6", coral: "FF725E",
  coralPale: "FFD0C7", amber: "FFC857", line: "31545A", white: "FFFFFF",
};
const W = 13.333;
const H = 7.5;

function rect(slide, x, y, w, h, fill, line = fill) {
  slide.addShape(pptx.ShapeType.rect, { x, y, w, h, fill: { color: fill }, line: { color: line, transparency: 100 } });
}

function text(slide, value, x, y, w, h, options = {}) {
  slide.addText(value, {
    x, y, w, h, margin: 0, fontFace: "Aptos", fontSize: 18, color: C.cream,
    breakLine: false, fit: "shrink", valign: "mid", ...options,
  });
}

function label(slide, value, x, y, w = 3) {
  text(slide, value.toUpperCase(), x, y, w, 0.22, { fontFace: "Courier New", fontSize: 8.5, bold: true, charSpacing: 2.2, color: C.mint });
}

function heading(slide, title, subtitle = "") {
  label(slide, "AI / ML • TA4", 0.62, 0.38, 3.4);
  text(slide, title, 0.62, 0.73, 11.8, 0.62, { fontFace: "Georgia", fontSize: 29, bold: true, color: C.cream, fit: "shrink" });
  if (subtitle) text(slide, subtitle, 0.64, 1.42, 11.7, 0.35, { fontSize: 11.5, color: C.muted });
  rect(slide, 0.62, 1.94, 12.08, 0.015, C.line);
}

function footer(slide, page, source = "Kaggle India Trending dataset • 2017–2018 snapshot") {
  rect(slide, 0.62, 7.08, 12.08, 0.015, C.line);
  text(slide, source, 0.62, 7.18, 8.8, 0.16, { fontSize: 7.6, color: "85A49F" });
  text(slide, String(page).padStart(2, "0"), 12.05, 7.14, 0.64, 0.2, { fontFace: "Courier New", fontSize: 9, bold: true, color: C.mint, align: "right" });
}

function card(slide, x, y, w, h, title, body, accent = C.mint) {
  rect(slide, x, y, w, h, C.panel);
  rect(slide, x, y, 0.07, h, accent);
  text(slide, title, x + 0.24, y + 0.18, w - 0.42, 0.31, { fontSize: 13.5, bold: true, color: C.cream });
  text(slide, body, x + 0.24, y + 0.62, w - 0.42, h - 0.78, { fontSize: 10.5, color: C.muted, breakLine: false, valign: "top", fit: "shrink" });
}

function bigStat(slide, x, y, w, number, labelText, accent = C.coral) {
  text(slide, number, x, y, w, 0.7, { fontFace: "Georgia", fontSize: 37, bold: true, color: accent, align: "center" });
  text(slide, labelText.toUpperCase(), x, y + 0.76, w, 0.25, { fontFace: "Courier New", fontSize: 8.5, bold: true, charSpacing: 1.4, color: C.muted, align: "center" });
}

function bulletList(slide, items, x, y, w, h, color = C.muted) {
  slide.addText(items.map((item, index) => ({ text: item, options: { bullet: true, breakLine: index < items.length - 1, hanging: 3, paraSpaceAfterPt: 10 } })), {
    x, y, w, h, margin: 0, fontFace: "Aptos", fontSize: 13.5, color, breakLine: false, fit: "shrink", valign: "top",
  });
}

function baseSlide(titleText, subtitle, page) {
  const slide = pptx.addSlide();
  slide.background = { color: C.ink };
  heading(slide, titleText, subtitle);
  footer(slide, page);
  return slide;
}

// 01 — title
{
  const s = pptx.addSlide();
  s.background = { color: C.ink };
  rect(s, 0, 0, W, H, C.ink);
  rect(s, 9.95, 0, 3.38, H, C.coral);
  rect(s, 9.95, 4.45, 3.38, 3.05, C.teal);
  s.addShape(pptx.ShapeType.ellipse, { x: 9.18, y: 1.12, w: 2.35, h: 2.35, fill: { color: C.cream, transparency: 8 }, line: { color: C.cream, transparency: 100 } });
  s.addShape(pptx.ShapeType.triangle, { x: 10.04, y: 1.83, w: 0.8, h: 0.85, rotate: 90, fill: { color: C.coral }, line: { color: C.coral, transparency: 100 } });
  label(s, "Thematic Assessment 4 • Final Review", 0.76, 0.83, 5.7);
  text(s, "AI-Based YouTube\nAnalytics & Content\nStrategy Prediction", 0.76, 1.35, 8.35, 2.65, { fontFace: "Georgia", fontSize: 36, bold: true, color: C.cream, valign: "top", breakLine: true, fit: "shrink" });
  text(s, "A pre-publication ML decision tool for title, tags, description, category and publishing time.", 0.8, 4.42, 7.6, 0.55, { fontSize: 16, color: C.muted, valign: "top" });
  text(s, "AI / ML", 0.8, 6.15, 1.3, 0.32, { fontFace: "Courier New", fontSize: 11, bold: true, color: C.mint });
  text(s, "Final model • Explainability • Live scenario demo", 2.18, 6.15, 5.8, 0.32, { fontSize: 11, color: C.muted });
  footer(s, 1, "TA4 final presentation");
}

// 02 — problem
{
  const s = baseSlide("The decision happens before the upload", "Creators choose packaging before the first recommendation signal exists.", 2);
  text(s, "Question", 0.75, 2.42, 2, 0.4, { fontFace: "Georgia", fontSize: 23, italic: true, color: C.coral });
  text(s, "Can we estimate relative video performance using only metadata a creator controls before publishing?", 0.75, 2.87, 6.45, 1.1, { fontFace: "Georgia", fontSize: 25, bold: true, color: C.cream, valign: "top" });
  card(s, 7.73, 2.36, 2.08, 2.55, "INPUTS", "Title\nTags\nDescription\nCategory\nTime in IST", C.mint);
  card(s, 10.1, 2.36, 2.08, 2.55, "OUTPUTS", "Expected views\nEngagement rate\nFeature audit\nScenario comparison", C.coral);
  s.addShape(pptx.ShapeType.chevron, { x: 9.82, y: 3.34, w: 0.2, h: 0.4, fill: { color: C.amber }, line: { color: C.amber, transparency: 100 } });
  card(s, 0.75, 5.25, 11.43, 1.05, "Project objective", "Build an interpretable AI/ML tool that supports a creator’s pre-publication choices, then explain the model’s learned patterns honestly.", C.teal);
}

// 03 — data
{
  const s = baseSlide("One video can appear many times in Trending", "The raw file records daily snapshots, so de-duplication is essential before training.", 3);
  bigStat(s, 0.8, 2.35, 3.2, "37,352", "raw daily snapshots", C.cream);
  text(s, "→", 4.18, 2.55, 1.05, 0.65, { fontFace: "Georgia", fontSize: 44, color: C.coral, align: "center" });
  bigStat(s, 5.3, 2.35, 3.2, "16,307", "unique videos", C.mint);
  card(s, 9.25, 2.25, 3, 2.3, "WHAT CHANGED?", "Parse dates\nSort by trending date\nKeep latest record per video ID\nDrop no valid rows for missing data", C.amber);
  bulletList(s, ["Source: Kaggle’s India subset of Trending YouTube Video Statistics.", "Scope: videos that already reached Trending in India; this is not a viral vs. non-viral dataset."], 0.85, 5.4, 7.45, 1.0);
  text(s, "DATA INTEGRITY", 9.25, 5.56, 2.5, 0.22, { fontFace: "Courier New", fontSize: 8.5, bold: true, charSpacing: 1.6, color: C.mint });
  text(s, "Every video gets one vote in training.", 9.25, 5.9, 2.7, 0.5, { fontFace: "Georgia", fontSize: 16, bold: true, color: C.cream });
}

// 04 — pipeline
{
  const s = baseSlide("A pipeline designed to avoid data leakage", "Only fields known before publication reach the model.", 4);
  const steps = [
    ["01", "Clean", "Parse dates and remove repeat video snapshots."],
    ["02", "Engineer", "Turn pre-upload metadata into measurable signals."],
    ["03", "Train", "Compare baseline and tree-based regressors."],
    ["04", "Validate", "5-fold CV plus a chronological holdout."],
    ["05", "Explain", "Feature groups, scenario lab and range warnings."],
  ];
  steps.forEach(([n, t, b], i) => {
    const x = 0.67 + i * 2.52;
    rect(s, x, 2.58, 2.15, 2.22, i === 4 ? C.coral : C.panel);
    text(s, n, x + 0.18, 2.78, 0.44, 0.25, { fontFace: "Courier New", fontSize: 10, bold: true, color: i === 4 ? C.ink : C.mint });
    text(s, t, x + 0.18, 3.24, 1.75, 0.3, { fontFace: "Georgia", fontSize: 18, bold: true, color: i === 4 ? C.ink : C.cream });
    text(s, b, x + 0.18, 3.78, 1.75, 0.7, { fontSize: 10.2, color: i === 4 ? C.ink : C.muted, valign: "top" });
    if (i < 4) text(s, "→", x + 2.15, 3.44, 0.34, 0.25, { fontSize: 17, color: C.amber, align: "center" });
  });
  card(s, 0.8, 5.42, 11.4, 0.72, "Leakage guard", "Views, likes, dislikes, comments, channel details and video ID never enter the input feature table.", C.coral);
}

// 05 — features
{
  const s = baseSlide("TA4 adds richer features that students can explain", "Each signal is visible in the app and is computable before publishing.", 5);
  card(s, 0.75, 2.32, 2.75, 2.4, "TITLE PACKAGING", "Length and word count\nCapital ratio\nPunctuation, digits, emojis\nUrgency/how-to wording\nSimple sentiment score", C.coral);
  card(s, 3.76, 2.32, 2.75, 2.4, "TAGS", "Tag count\nTotal and average length\nMultiword-tag ratio\nConsistent local parsing", C.mint);
  card(s, 6.77, 2.32, 2.75, 2.4, "DESCRIPTION", "Length and word count\nLinks and hashtags\nCall-to-action words\nPre-upload text only", C.amber);
  card(s, 9.78, 2.32, 2.75, 2.4, "TIME + CATEGORY", "Day and hour in IST\nWeekend flag\nCyclic hour sin/cos\nYouTube category", C.teal);
  text(s, "No post-publication counts are used as features.", 0.75, 5.4, 7.2, 0.42, { fontFace: "Georgia", fontSize: 20, italic: true, color: C.cream });
  text(s, "Explainable does not mean causal: the model finds associations in the observed data.", 0.75, 5.95, 9.7, 0.32, { fontSize: 12, color: C.muted });
}

// 06 — models / validation
{
  const s = baseSlide("Validation answers two different questions", "Random folds show average fit; a time-ordered holdout checks how well later uploads generalise.", 6);
  card(s, 0.75, 2.3, 3.52, 2.55, "BASELINE", "Linear Regression\nSimple, interpretable benchmark\nR²: 0.197 views\nR²: 0.384 engagement", C.muted);
  card(s, 4.91, 2.3, 3.52, 2.55, "SELECTED FAMILY", "Random Forest Regression\nCaptures non-linear metadata patterns\nKeeps feature importances\nCompact model bundle for the demo", C.mint);
  card(s, 9.07, 2.3, 3.52, 2.55, "TA4 CHECK", "5-fold cross-validation\nChronological 80/20 holdout\nNo future timestamps seen while training the holdout model", C.coral);
  rect(s, 0.75, 5.4, 11.83, 0.62, C.panel2);
  text(s, "Why log views?", 0.98, 5.56, 1.65, 0.22, { fontFace: "Georgia", fontSize: 14.5, bold: true, color: C.amber });
  text(s, "Video views are heavily right-skewed. We train on log1p(views) and use expm1 to show expected views in the live app.", 2.75, 5.56, 9.1, 0.22, { fontSize: 11.5, color: C.muted });
}

// 07 — results
{
  const s = baseSlide("More signal, with a harder reality check", "TA4’s expanded pre-publication features improve mean 5-fold CV while time-aware testing keeps the claims honest.", 7);
  text(s, "Log views · R²", 0.83, 2.38, 2.3, 0.3, { fontFace: "Georgia", fontSize: 17, bold: true, color: C.cream });
  [
    ["Linear", 0.197, C.muted], ["Original RF", 0.367, C.teal], ["TA4 RF", 0.420, C.coral],
  ].forEach(([name, value, color], i) => {
    const y = 2.94 + i * 0.62; text(s, name, 0.84, y, 1.32, 0.18, { fontSize: 10.5, color: C.muted });
    rect(s, 2.18, y, Number(value) * 8, 0.23, color); text(s, Number(value).toFixed(3), 2.25 + Number(value) * 8, y + 0.01, 0.58, 0.18, { fontSize: 9.5, bold: true, color: C.cream });
  });
  text(s, "Engagement rate · R²", 0.83, 4.95, 2.7, 0.3, { fontFace: "Georgia", fontSize: 17, bold: true, color: C.cream });
  [
    ["Linear", 0.384, C.muted], ["Original RF", 0.598, C.teal], ["TA4 RF", 0.637, C.coral],
  ].forEach(([name, value, color], i) => {
    const y = 5.51 + i * 0.42; text(s, name, 0.84, y, 1.32, 0.18, { fontSize: 10.5, color: C.muted });
    rect(s, 2.18, y, Number(value) * 8, 0.23, color); text(s, Number(value).toFixed(3), 2.25 + Number(value) * 8, y + 0.01, 0.58, 0.18, { fontSize: 9.5, bold: true, color: C.cream });
  });
  card(s, 9.12, 2.5, 3.15, 2.3, "CHRONOLOGICAL HOLDOUT", "Log views R²: 0.370\nEngagement R²: 0.525\n\nLater uploads are harder to predict, which is more realistic than only random splits.", C.amber);
}

// 08 — importance
{
  const s = baseSlide("Explainability starts with global feature importance", "The model points to different signals for reach and engagement; the chart is evidence of association, not causation.", 8);
  if (fs.existsSync(reportImage)) s.addImage({ path: reportImage, x: 0.72, y: 2.2, w: 8.05, h: 4.42, altText: "Random Forest feature importance chart" });
  card(s, 9.18, 2.3, 3.1, 1.2, "VIEWS", "Title packaging and description signals carry substantial predictive weight alongside category.", C.coral);
  card(s, 9.18, 3.78, 3.1, 1.2, "ENGAGEMENT", "Category, title packaging, tags and descriptions combine differently for engagement rate.", C.mint);
  card(s, 9.18, 5.26, 3.1, 1.2, "HONEST READING", "Feature importance says what the model used. It does not prove that editing one field causes a result.", C.amber);
}

// 09 — EDA
{
  const s = baseSlide("Weak single correlations justify a non-linear model", "The heatmap shows why a simple one-feature rule is not enough for this problem.", 9);
  if (fs.existsSync(corrImage)) s.addImage({ path: corrImage, x: 0.78, y: 2.22, w: 5.55, h: 4.4, altText: "Correlation heatmap" });
  card(s, 7.02, 2.4, 4.85, 1.08, "OBSERVATION 1", "Most individual correlations with views are weak. Performance is shaped by combinations of metadata signals.", C.mint);
  card(s, 7.02, 3.82, 4.85, 1.08, "OBSERVATION 2", "The advanced feature set gives the forest more transparent combinations to test without introducing post-publish information.", C.coral);
  card(s, 7.02, 5.24, 4.85, 1.08, "DECISION", "Use Random Forest for non-linear patterns, retain a Linear Regression baseline for comparison, and report both random and chronological validation.", C.amber);
}

// 10 — live app
{
  const s = baseSlide("The live demo turns the model into a student-friendly tool", "The interface makes prediction, uncertainty and explanation visible in one flow.", 10);
  rect(s, 0.78, 2.3, 4.0, 3.8, C.panel);
  label(s, "01 • forecast studio", 1.05, 2.65, 2.5);
  text(s, "Enter a real draft", 1.05, 3.02, 3, 0.34, { fontFace: "Georgia", fontSize: 20, bold: true });
  text(s, "Title • category • tags\nDescription • IST day and time", 1.05, 3.62, 3, 0.75, { fontSize: 13, color: C.muted, valign: "top" });
  text(s, "Expected views\nEngagement rate\nTree-disagreement range", 1.05, 4.75, 3, 0.72, { fontSize: 13, color: C.coral, bold: true, valign: "top" });
  text(s, "→", 4.92, 3.88, 0.42, 0.25, { fontSize: 22, color: C.amber });
  rect(s, 5.5, 2.3, 3.05, 3.8, C.panel2);
  label(s, "02 • feature audit", 5.78, 2.65, 2.4);
  text(s, "Show what the\nmodel sees", 5.78, 3.02, 2.5, 0.65, { fontFace: "Georgia", fontSize: 19, bold: true, valign: "top" });
  text(s, "Editable signals are compared with the usual training range.", 5.78, 4.18, 2.35, 0.75, { fontSize: 12, color: C.muted, valign: "top" });
  text(s, "Range warning", 5.78, 5.28, 2.2, 0.25, { fontSize: 12.5, bold: true, color: C.mint });
  text(s, "→", 8.68, 3.88, 0.42, 0.25, { fontSize: 22, color: C.amber });
  rect(s, 9.26, 2.3, 3.02, 3.8, C.coral);
  label(s, "03 • scenario lab", 9.54, 2.65, 2.3);
  text(s, "Compare\nDraft A vs B", 9.54, 3.02, 2.34, 0.65, { fontFace: "Georgia", fontSize: 19, bold: true, color: C.ink, valign: "top" });
  text(s, "Change title, tags, description or timing; discuss the predicted difference as a scenario, not a promise.", 9.54, 4.18, 2.3, 1.05, { fontSize: 12, color: C.ink, valign: "top" });
}

// 11 — responsible interpretation
{
  const s = baseSlide("Useful predictions need responsible interpretation", "We state the boundaries of the data instead of overclaiming what the model knows.", 11);
  const limits = [
    ["Trending-only sample", "Cannot classify arbitrary uploads as viral/non-viral."],
    ["Missing signals", "No thumbnail, channel history, retention or YouTube ranking inputs."],
    ["Historical snapshot", "The India data covers 2017–2018, so patterns can change."],
    ["Association ≠ causation", "Feature importance guides discussion but does not prove an intervention."],
  ];
  limits.forEach(([t, b], i) => card(s, 0.78 + (i % 2) * 6.0, 2.35 + Math.floor(i / 2) * 1.82, 5.45, 1.35, t, b, [C.coral, C.amber, C.mint, C.teal][i]));
  text(s, "The app calls its output a forecast and its A/B result a scenario comparison.", 0.8, 6.22, 10.8, 0.35, { fontFace: "Georgia", fontSize: 17.5, italic: true, color: C.cream });
}

// 12 — conclusion
{
  const s = pptx.addSlide();
  s.background = { color: C.ink };
  rect(s, 0, 0, W, H, C.ink);
  rect(s, 0, 0, 3.15, H, C.teal);
  label(s, "Closing", 3.76, 0.95, 2);
  text(s, "From intuition to\na testable pre-publish\nconversation.", 3.76, 1.4, 7.92, 1.88, { fontFace: "Georgia", fontSize: 35, bold: true, color: C.cream, valign: "top" });
  text(s, "TA4 delivers a reproducible ML pipeline, improved explainable features, robust validation, a live Streamlit application and production deployment files.", 3.78, 3.72, 7.6, 0.62, { fontSize: 16, color: C.muted, valign: "top" });
  card(s, 3.78, 5.05, 2.48, 1.0, "NEXT", "Current, non-trending data", C.coral);
  card(s, 6.58, 5.05, 2.48, 1.0, "NEXT", "Thumbnail + channel features", C.amber);
  card(s, 9.38, 5.05, 2.48, 1.0, "NEXT", "Real creator validation", C.mint);
  footer(s, 12, "Thank you • Questions and live demo");
}

pptx.writeFile({ fileName: OUT });
