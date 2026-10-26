const pptxgen = require('pptxgenjs');
const path = require('path');

const root = path.resolve(__dirname, '..');
const out = path.join(__dirname, 'TA4_YouTube_Content_Strategy_Prediction.pptx');
const featureImportance = path.join(root, 'reports', 'feature_importance.png');
const correlationHeatmap = path.join(root, 'reports', 'eda_corr.png');

const pptx = new pptxgen();
pptx.layout = 'LAYOUT_WIDE';
pptx.author = 'AI/ML Thematic Assessment Team';
pptx.company = 'SGT University';
pptx.subject = 'AI-Based YouTube Analytics and Content Strategy Prediction';
pptx.title = 'AI-Based YouTube Analytics and Content Strategy Prediction — TA4';
pptx.lang = 'en-IN';
pptx.theme = {
  headFontFace: 'Georgia',
  bodyFontFace: 'Aptos',
  lang: 'en-IN'
};
pptx.defineLayout({ name: 'CUSTOM_WIDE', width: 13.333, height: 7.5 });
pptx.layout = 'CUSTOM_WIDE';

const C = {
  navy: '091420',
  navy2: '12283A',
  ink: '132433',
  paper: 'F5F7F8',
  white: 'FFFFFF',
  mint: '27D7B5',
  teal: '009F93',
  coral: 'FF6D55',
  gold: 'FFC857',
  blue: '3D7EFF',
  slate: '607383',
  pale: 'DCE7EC',
  fog: 'E9EFF2',
  red: 'D94A4A'
};

function shadow() {
  return { type: 'outer', color: '00111A', opacity: 0.16, blur: 2, angle: 45, distance: 1.3 };
}

function rect(slide, x, y, w, h, fill, opts = {}) {
  slide.addShape(pptx.ShapeType.roundRect, {
    x, y, w, h, rectRadius: opts.radius || 0.1,
    fill: { color: fill, transparency: opts.transparency || 0 },
    line: opts.line || { color: fill, transparency: 100 },
    shadow: opts.shadow ? shadow() : undefined
  });
}

function text(slide, value, x, y, w, h, options = {}) {
  slide.addText(value, {
    x, y, w, h, margin: options.margin === undefined ? 0 : options.margin,
    fontFace: options.fontFace || 'Aptos', fontSize: options.fontSize || 16,
    color: options.color || C.ink, bold: options.bold || false,
    italic: options.italic || false, align: options.align || 'left',
    valign: options.valign || 'mid', breakLine: false,
    fit: 'shrink', paraSpaceAfterPt: options.paraSpaceAfterPt || 0,
    charSpacing: options.charSpacing || 0, bullet: options.bullet,
    transparency: options.transparency || 0
  });
}

function base(slide, dark = false, index = '') {
  slide.background = { color: dark ? C.navy : C.paper };
  if (dark) {
    slide.addShape(pptx.ShapeType.arc, { x: 9.75, y: -1.65, w: 5.0, h: 5.0, adjustPoint: 0.25,
      line: { color: C.mint, transparency: 60, width: 1.2 }, fill: { color: C.navy, transparency: 100 } });
    slide.addShape(pptx.ShapeType.arc, { x: 10.3, y: -1.15, w: 3.7, h: 3.7, adjustPoint: 0.25,
      line: { color: C.coral, transparency: 72, width: 1.2 }, fill: { color: C.navy, transparency: 100 } });
  }
  text(slide, 'AI / ML • THEMATIC ASSESSMENT 4', 0.55, 0.35, 5.4, 0.24,
    { fontSize: 8.7, color: dark ? C.mint : C.teal, bold: true, charSpacing: 1.3 });
  text(slide, index, 12.15, 0.35, 0.6, 0.24,
    { fontSize: 9, color: dark ? C.pale : C.slate, bold: true, align: 'right' });
}

function title(slide, value, subtitle = '', dark = false) {
  text(slide, value, 0.55, 0.72, 11.9, 0.62,
    { fontFace: 'Georgia', fontSize: 28, color: dark ? C.white : C.ink, bold: true, valign: 'top' });
  if (subtitle) text(slide, subtitle, 0.57, 1.37, 11.5, 0.34,
    { fontSize: 11.8, color: dark ? C.pale : C.slate, valign: 'top' });
}

function footer(slide, label, dark = false) {
  slide.addShape(pptx.ShapeType.line, { x: 0.55, y: 7.05, w: 12.2, h: 0,
    line: { color: dark ? '365164' : 'C9D8DE', width: 0.6 } });
  text(slide, label, 0.55, 7.16, 10.6, 0.17, { fontSize: 7.5, color: dark ? C.pale : C.slate });
  text(slide, 'Kaggle India trending-video snapshot • project results', 9.2, 7.16, 3.55, 0.17,
    { fontSize: 7.5, color: dark ? C.pale : C.slate, align: 'right' });
}

function badge(slide, label, x, y, color, dark = false) {
  rect(slide, x, y, 0.72, 0.32, color, { radius: 0.16 });
  text(slide, label, x, y + 0.02, 0.72, 0.25, { fontSize: 8.3, color: dark ? C.navy : C.white, bold: true, align: 'center' });
}

function numberedCard(slide, n, heading, body, x, y, w, h, accent, dark = false) {
  rect(slide, x, y, w, h, dark ? C.navy2 : C.white, { shadow: !dark, line: { color: dark ? '24445A' : C.fog, width: 0.7 } });
  rect(slide, x + 0.22, y + 0.22, 0.48, 0.48, accent, { radius: 0.24 });
  text(slide, n, x + 0.22, y + 0.27, 0.48, 0.25, { fontSize: 12, color: C.navy, bold: true, align: 'center' });
  text(slide, heading, x + 0.82, y + 0.2, w - 1.02, 0.35, { fontSize: 14.2, color: dark ? C.white : C.ink, bold: true });
  text(slide, body, x + 0.22, y + 0.82, w - 0.44, h - 1.02, { fontSize: 11, color: dark ? C.pale : C.slate, valign: 'top' });
}

// 1. Title
{
  const slide = pptx.addSlide();
  base(slide, true, '01');
  rect(slide, 0.55, 1.0, 0.16, 4.95, C.mint, { radius: 0.08 });
  text(slide, 'AI-Based YouTube\nAnalytics & Content\nStrategy Prediction', 1.0, 1.18, 7.1, 2.3,
    { fontFace: 'Georgia', fontSize: 31, color: C.white, bold: true, valign: 'top' });
  text(slide, 'Can pre-publication metadata help a creator make a better upload decision?', 1.02, 3.73, 6.65, 0.6,
    { fontSize: 16.5, color: C.pale, valign: 'top' });
  rect(slide, 1.02, 4.72, 5.75, 0.82, C.navy2, { line: { color: '2D5268', width: 0.7 } });
  text(slide, 'TA4 FINAL EVALUATION', 1.28, 4.9, 2.42, 0.18, { fontSize: 9, color: C.mint, bold: true, charSpacing: 1.2 });
  text(slide, 'Regression • Explainability • Live demo', 1.28, 5.12, 4.6, 0.2, { fontSize: 12, color: C.white, bold: true });
  // abstract predictive diagram
  rect(slide, 8.75, 1.3, 3.55, 4.7, C.navy2, { line: { color: '31506A', width: 0.8 } });
  const labels = [
    ['TITLE', 1.65, C.mint], ['TAGS', 2.5, C.gold], ['TIMING', 3.35, C.coral], ['CATEGORY', 4.2, C.blue]
  ];
  labels.forEach(([label, y, color]) => {
    rect(slide, 9.07, y, 1.38, 0.48, color, { radius: 0.12 });
    text(slide, label, 9.07, y + 0.13, 1.38, 0.16, { fontSize: 8.5, color: C.navy, bold: true, align: 'center' });
    slide.addShape(pptx.ShapeType.line, { x: 10.47, y: y + 0.24, w: 0.48, h: 0, line: { color: C.pale, width: 1.2, endArrowType: 'triangle' } });
  });
  rect(slide, 11.15, 2.62, 0.84, 1.62, C.white, { radius: 0.14 });
  text(slide, 'ML\nMODEL', 11.25, 2.98, 0.65, 0.7, { fontSize: 11, color: C.navy, bold: true, align: 'center' });
  slide.addShape(pptx.ShapeType.line, { x: 11.57, y: 4.28, w: 0, h: 0.63, line: { color: C.mint, width: 1.35, endArrowType: 'triangle' } });
  text(slide, 'views + engagement\nwith honest limits', 9.05, 5.15, 3.2, 0.45, { fontSize: 10.3, color: C.pale, align: 'center' });
  footer(slide, 'A decision-support model for already trending videos', true);
}

// 2. Problem and scope
{
  const slide = pptx.addSlide();
  base(slide, false, '02');
  title(slide, 'The decision happens before the video goes live', 'Creators choose metadata first, then receive feedback only after the key distribution window has passed.');
  numberedCard(slide, '1', 'Creator-controlled choices', 'Title, description, tags, category and publish time are known before upload.', 0.62, 2.0, 3.78, 2.15, C.mint);
  numberedCard(slide, '2', 'Prediction task', 'Estimate relative views and engagement from only those pre-publication signals.', 4.78, 2.0, 3.78, 2.15, C.gold);
  numberedCard(slide, '3', 'Strategy output', 'Translate model patterns into a transparent checklist and a live draft comparison.', 8.94, 2.0, 3.78, 2.15, C.coral);
  rect(slide, 0.62, 4.7, 12.1, 1.5, C.navy, { shadow: true });
  text(slide, 'The claim we can defend', 0.98, 5.0, 2.45, 0.25, { fontSize: 12, color: C.mint, bold: true });
  text(slide, 'Among videos that already trended in India, metadata helps estimate relative performance. It does not tell us whether an arbitrary upload will become viral.', 3.26, 4.88, 8.87, 0.58, { fontSize: 16, color: C.white, bold: true, valign: 'top' });
  footer(slide, 'Scope is explicit: decision support, not a viral/non-viral classifier');
}

// 3. Dataset and dedup
{
  const slide = pptx.addSlide();
  base(slide, true, '03');
  title(slide, 'A real India dataset — cleaned at the video level', 'Trending YouTube Video Statistics (Kaggle), India subset; each raw record is one daily trending snapshot.', true);
  rect(slide, 0.68, 2.08, 3.65, 3.72, C.navy2, { line: { color: '2C566F', width: 0.8 } });
  text(slide, 'RAW SNAPSHOTS', 1.0, 2.45, 2.6, 0.25, { fontSize: 10, color: C.pale, bold: true, charSpacing: 1.0 });
  text(slide, '37,352', 0.98, 2.83, 2.8, 0.78, { fontFace: 'Georgia', fontSize: 40, color: C.white, bold: true });
  text(slide, 'A video can appear on the trending list on several days.', 1.0, 3.82, 2.76, 0.72, { fontSize: 12.2, color: C.pale, valign: 'top' });
  for (let i = 0; i < 5; i++) rect(slide, 1.0 + (i * 0.44), 5.1, 0.35, 0.35, i < 3 ? C.coral : C.gold, { radius: 0.08 });
  slide.addShape(pptx.ShapeType.line, { x: 4.63, y: 3.8, w: 3.03, h: 0, line: { color: C.mint, width: 2.1, endArrowType: 'triangle' } });
  rect(slide, 4.95, 3.13, 2.22, 1.22, C.mint, { radius: 0.1 });
  text(slide, 'DE-DUPLICATE\nBY VIDEO ID', 5.15, 3.44, 1.84, 0.45, { fontSize: 13, color: C.navy, bold: true, align: 'center' });
  rect(slide, 8.93, 2.08, 3.72, 3.72, C.white, { shadow: true });
  text(slide, 'UNIQUE VIDEOS', 9.25, 2.45, 2.4, 0.25, { fontSize: 10, color: C.teal, bold: true, charSpacing: 1.0 });
  text(slide, '16,307', 9.23, 2.83, 3.0, 0.78, { fontFace: 'Georgia', fontSize: 40, color: C.ink, bold: true });
  text(slide, 'Latest snapshot retained per video; no required-field rows were lost.', 9.25, 3.82, 2.86, 0.72, { fontSize: 12.2, color: C.slate, valign: 'top' });
  text(slide, 'Why it matters: avoids over-weighting videos simply because they trended longer.', 0.74, 6.3, 11.9, 0.3, { fontSize: 13, color: C.pale, bold: true, align: 'center' });
  footer(slide, 'Date parsing precedes sorting so the retained record is truly the latest snapshot', true);
}

// 4. Pipeline
{
  const slide = pptx.addSlide();
  base(slide, false, '04');
  title(slide, 'A reproducible AI/ML workflow', 'The project is a clear supervised-regression pipeline, from raw evidence to creator-facing guidance.');
  const pipeline = [
    ['01', 'Clean', 'Parse dates\nDeduplicate'],
    ['02', 'Engineer', 'Pre-publish\nfeatures only'],
    ['03', 'Compare', 'Linear, RF\nand XGBoost'],
    ['04', 'Validate', '5-fold CV +\nheld-out test'],
    ['05', 'Explain', 'Importance +\nstrategy advice']
  ];
  pipeline.forEach((item, i) => {
    const x = 0.65 + i * 2.52;
    rect(slide, x, 2.33, 2.06, 2.72, C.white, { shadow: true });
    rect(slide, x + 0.23, 2.58, 0.53, 0.53, i === 3 ? C.gold : (i === 4 ? C.coral : C.mint), { radius: 0.265 });
    text(slide, item[0], x + 0.23, 2.73, 0.53, 0.18, { fontSize: 9.5, color: C.navy, bold: true, align: 'center' });
    text(slide, item[1], x + 0.23, 3.38, 1.6, 0.3, { fontSize: 17, color: C.ink, bold: true });
    text(slide, item[2], x + 0.23, 3.88, 1.56, 0.62, { fontSize: 11.6, color: C.slate, valign: 'top' });
    if (i < 4) slide.addShape(pptx.ShapeType.line, { x: x + 2.08, y: 3.7, w: 0.39, h: 0, line: { color: C.teal, width: 1.5, endArrowType: 'triangle' } });
  });
  rect(slide, 0.65, 5.63, 12.02, 0.77, C.navy, { radius: 0.12 });
  text(slide, 'Leakage firewall: likes, dislikes and comment count are outcomes only — never inputs.', 0.95, 5.86, 11.42, 0.22, { fontSize: 14, color: C.white, bold: true, align: 'center' });
  footer(slide, 'Scripts: clean.py → features.py → train.py → evaluate.py');
}

// 5. Features and leakage
{
  const slide = pptx.addSlide();
  base(slide, false, '05');
  title(slide, 'Feature engineering answers one question: what is known before publication?', 'Inputs are transparent enough to explain in a viva and practical enough for a creator to change.');
  const groups = [
    ['PACKAGING', 'Title length • word count • number • question mark • capitals', C.mint],
    ['DISCOVERY', 'Tag count • category • description length', C.gold],
    ['TIMING', 'Publish day and hour, converted from UTC to IST', C.coral]
  ];
  groups.forEach((g, i) => {
    const y = 2.02 + i * 1.16;
    rect(slide, 0.7, y, 7.23, 0.85, C.white, { shadow: true });
    rect(slide, 0.7, y, 1.55, 0.85, g[2], { radius: 0.1 });
    text(slide, g[0], 0.87, y + 0.29, 1.2, 0.19, { fontSize: 9.5, color: C.navy, bold: true, align: 'center' });
    text(slide, g[1], 2.58, y + 0.26, 4.95, 0.28, { fontSize: 13.1, color: C.ink, bold: true });
  });
  rect(slide, 8.53, 2.02, 4.08, 3.2, C.navy, { shadow: true });
  text(slide, 'TARGETS', 8.88, 2.42, 2.2, 0.18, { fontSize: 9.5, color: C.mint, bold: true, charSpacing: 1.1 });
  text(slide, 'Views', 8.88, 2.85, 1.4, 0.26, { fontSize: 18, color: C.white, bold: true });
  text(slide, 'trained as log1p(views)', 10.0, 2.91, 2.05, 0.2, { fontSize: 10.5, color: C.pale });
  text(slide, 'Engagement rate', 8.88, 3.58, 2.35, 0.26, { fontSize: 18, color: C.white, bold: true });
  text(slide, '(likes + comments) / views', 8.88, 3.98, 2.9, 0.2, { fontSize: 11, color: C.pale });
  rect(slide, 8.84, 4.47, 3.45, 0.43, C.coral, { radius: 0.08 });
  text(slide, 'post-publication counts excluded from inputs', 8.94, 4.58, 3.25, 0.14, { fontSize: 8.7, color: C.white, bold: true, align: 'center' });
  rect(slide, 0.7, 5.63, 12.0, 0.77, C.fog, { radius: 0.12 });
  text(slide, 'This protects the model from “cheating” and makes the live demo valid before upload.', 0.96, 5.86, 11.5, 0.22, { fontSize: 13.7, color: C.ink, bold: true, align: 'center' });
  footer(slide, 'Feature table preserves a strict separation between metadata and outcomes');
}

// 6. Model performance
{
  const slide = pptx.addSlide();
  base(slide, true, '06');
  title(slide, 'Random Forest delivered the strongest held-out performance', 'A simple linear baseline sets the floor; tree ensembles capture non-linear interactions among metadata signals.', true);
  const bars = [
    ['Views R²', '0.20', '0.38', 0.38 / 0.65],
    ['Engagement R²', '0.38', '0.61', 0.61 / 0.65]
  ];
  bars.forEach((b, i) => {
    const y = 2.12 + i * 1.8;
    text(slide, b[0], 0.82, y, 2.45, 0.25, { fontSize: 16.5, color: C.white, bold: true });
    text(slide, 'Linear', 0.82, y + 0.49, 0.7, 0.2, { fontSize: 10.3, color: C.pale, bold: true });
    rect(slide, 1.62, y + 0.48, 2.1, 0.28, '41637A', { radius: 0.14 });
    rect(slide, 1.62, y + 0.48, i === 0 ? 0.65 : 1.25, 0.28, C.slate, { radius: 0.14 });
    text(slide, b[1], 3.88, y + 0.47, 0.52, 0.23, { fontSize: 12, color: C.white, bold: true });
    text(slide, 'Random Forest', 0.82, y + 0.94, 1.4, 0.2, { fontSize: 10.3, color: C.mint, bold: true });
    rect(slide, 2.3, y + 0.93, 3.4, 0.28, '41637A', { radius: 0.14 });
    rect(slide, 2.3, y + 0.93, i === 0 ? 1.98 : 3.18, 0.28, C.mint, { radius: 0.14 });
    text(slide, b[2], 5.86, y + 0.92, 0.55, 0.23, { fontSize: 12, color: C.mint, bold: true });
  });
  rect(slide, 7.55, 1.96, 4.9, 3.97, C.navy2, { line: { color: '2A556F', width: 0.8 } });
  text(slide, '5-FOLD CROSS-VALIDATION', 7.96, 2.35, 3.3, 0.2, { fontSize: 9.5, color: C.gold, bold: true, charSpacing: 0.9 });
  text(slide, 'Views', 7.96, 2.82, 1.2, 0.21, { fontSize: 14, color: C.white, bold: true });
  text(slide, 'RF R² 0.367 ± 0.012\nXGBoost R² 0.337 ± 0.016', 7.96, 3.15, 3.7, 0.57, { fontSize: 12.3, color: C.pale, valign: 'top' });
  text(slide, 'Engagement', 7.96, 4.08, 1.8, 0.21, { fontSize: 14, color: C.white, bold: true });
  text(slide, 'RF R² 0.598 ± 0.025\nXGBoost R² 0.569 ± 0.050', 7.96, 4.41, 3.7, 0.57, { fontSize: 12.3, color: C.pale, valign: 'top' });
  text(slide, 'The final saved models are size-tuned Random Forests.', 0.82, 5.98, 11.75, 0.3, { fontSize: 13.5, color: C.pale, italic: true, align: 'center' });
  footer(slide, 'Evaluation: 80/20 held-out test plus five-fold cross-validation', true);
}

// 7. Explainability
{
  const slide = pptx.addSlide();
  base(slide, false, '07');
  title(slide, 'Explainability turns a model score into discussion-ready evidence', 'Random Forest feature importance identifies signals the model relied on. These are associations, not causal guarantees.');
  rect(slide, 0.67, 1.96, 7.42, 4.68, C.white, { shadow: true });
  if (require('fs').existsSync(featureImportance)) {
    slide.addImage({ path: featureImportance, x: 0.92, y: 2.2, w: 6.92, h: 3.98, sizing: { type: 'contain', x: 0.92, y: 2.2, w: 6.92, h: 3.98 }, altText: 'Random Forest feature importances for views and engagement' });
  } else {
    text(slide, 'Feature-importance visual is generated by src/evaluate.py.', 1.0, 3.9, 6.5, 0.3, { fontSize: 15, color: C.slate, align: 'center' });
  }
  text(slide, 'Strongest signals in this fitted model', 8.65, 2.1, 3.5, 0.28, { fontSize: 16, color: C.ink, bold: true });
  const takeaways = [
    ['01', 'Description length', 'A proxy for how much searchable/contextual detail is provided.', C.mint],
    ['02', 'Capitalisation style', 'A title-packaging signal that the model uses alongside other metadata.', C.gold],
    ['03', 'Category signals', 'Context matters, but it is not the only driver of performance.', C.coral]
  ];
  takeaways.forEach((t, i) => numberedCard(slide, t[0], t[1], t[2], 8.57, 2.62 + i * 1.15, 3.75, 0.93, t[3]));
  footer(slide, 'Feature importance describes the model’s behaviour; it does not prove causation');
}

// 8. Insights
{
  const slide = pptx.addSlide();
  base(slide, false, '08');
  title(slide, 'From analytics to creator-facing recommendations', 'Each recommendation is tied to observed data patterns and is presented with its confidence boundary.');
  const insights = [
    ['01', 'Write the description deliberately', 'Description length is the strongest feature in both fitted models.', C.mint],
    ['02', 'Make title style intentional', 'Capitalisation and title structure matter, but overuse is not a guaranteed win.', C.gold],
    ['03', 'Use consistent tags', 'Tag count has a small positive correlation with views in this sample (r = 0.05).', C.coral],
    ['04', 'Treat timing as a testable hypothesis', 'Saturday 01:00 IST had the highest eligible median view count; timing effect is modest.', C.blue]
  ];
  insights.forEach((x, i) => {
    const col = i % 2;
    const row = Math.floor(i / 2);
    numberedCard(slide, x[0], x[1], x[2], 0.7 + col * 6.05, 2.02 + row * 1.75, 5.55, 1.32, x[3]);
  });
  rect(slide, 0.72, 5.83, 11.98, 0.56, C.navy, { radius: 0.1 });
  text(slide, 'Evidence note: “Shows” has the highest median views among categories with at least 30 videos in this data (about 621,739; n = 121).', 0.96, 6.01, 11.5, 0.18, { fontSize: 10.4, color: C.white, align: 'center' });
  footer(slide, 'Recommendations support choices before upload; real audience testing still matters');
}

// 9. Explainable decision tools
{
  const slide = pptx.addSlide();
  base(slide, false, '09');
  title(slide, 'Six explainable tools turn one forecast into decisions', 'Every tool re-uses the same trained model and the same leakage-safe features; none needs the raw dataset at run time.');
  const tools = [
    ['01', 'Why this forecast', 'Exact Shapley values over five feature groups. The effects add up to forecast minus a typical trending video.', C.mint],
    ['02', 'Best time to post', 'The same draft is scored in all 168 weekly slots (IST) and shown as a heatmap with the best three.', C.gold],
    ['03', 'Title lab', 'About twelve programmatic edits are re-scored by the model and ranked; one click applies an edit.', C.coral],
    ['04', 'Similar videos', 'TF-IDF look-alike trending videos give an independent second opinion on the forecast.', C.blue],
    ['05', 'Keyword radar', 'Median views by title word, using only words that appear across 25+ different channels.', C.mint],
    ['06', 'Scenario lab', 'A/B comparison with an interval-overlap check, plus a category what-if chart.', C.gold]
  ];
  tools.forEach((t, i) => {
    const col = i % 3;
    const row = Math.floor(i / 3);
    numberedCard(slide, t[0], t[1], t[2], 0.66 + col * 4.1, 2.0 + row * 2.4, 3.85, 2.15, t[3]);
  });
  footer(slide, 'All outputs are associations learned from data, not causal promises');
}

// 10. Measured uncertainty
{
  const slide = pptx.addSlide();
  base(slide, true, '10');
  title(slide, 'How sure is the model? We measured it, not assumed it', 'Split-conformal 80% intervals are calibrated on out-of-fold errors, then tested on later uploads the calibration never saw.', true);
  const stats = [
    ['80.0%', 'Out-of-fold coverage', 'views and engagement intervals'],
    ['79.7%', 'Later-upload coverage', 'views interval (chronological holdout)'],
    ['80.9%', 'Later-upload coverage', 'engagement interval (chronological holdout)']
  ];
  stats.forEach((st, i) => {
    const x = 0.72 + i * 4.1;
    rect(slide, x, 2.1, 3.7, 2.4, C.navy2, { line: { color: '2C566F', width: 0.8 } });
    text(slide, st[0], x + 0.3, 2.4, 3.1, 0.95, { fontFace: 'Georgia', fontSize: 44, color: [C.mint, C.gold, C.coral][i], bold: true });
    text(slide, st[1], x + 0.3, 3.5, 3.1, 0.3, { fontSize: 14, color: C.white, bold: true });
    text(slide, st[2], x + 0.3, 3.9, 3.1, 0.3, { fontSize: 11.2, color: C.pale });
  });
  rect(slide, 0.72, 4.85, 11.9, 1.5, C.white, { shadow: true });
  text(slide, 'Honest reading: a views forecast is typically within x0.29 to x3.5 of the truth. The interval is wide because pre-publication metadata is a moderate signal (R\u00b2 0.42 in cross-validation, 0.37 on later uploads). A wide, correct interval is better than a narrow, wrong one.', 1.05, 5.02, 11.25, 1.15, { fontSize: 14, color: C.ink, bold: true, valign: 'top' });
  footer(slide, '33 automated tests \u2022 GitHub Actions CI \u2022 deployed as a Streamlit web service', true);
}

// 11. TA4 demo
{
  const slide = pptx.addSlide();
  base(slide, true, '11');
  title(slide, 'TA4 live demo: compare draft decisions before upload', 'The interactive application makes the model tangible without hiding its limitations.', true);
  rect(slide, 0.72, 2.0, 5.25, 3.95, C.navy2, { line: { color: '31506A', width: 0.8 } });
  text(slide, '1  ENTER A DRAFT', 1.06, 2.37, 2.2, 0.18, { fontSize: 9.4, color: C.mint, bold: true, charSpacing: 0.9 });
  const fields = ['Title', 'Category', 'Tags / description', 'Publish day and hour (IST)'];
  fields.forEach((f, i) => {
    rect(slide, 1.06, 2.83 + i * 0.57, 4.52, 0.38, '193A50', { radius: 0.06 });
    text(slide, f, 1.2, 2.95 + i * 0.57, 4.0, 0.13, { fontSize: 9.8, color: C.pale });
  });
  slide.addShape(pptx.ShapeType.line, { x: 6.25, y: 3.98, w: 1.15, h: 0, line: { color: C.mint, width: 2.0, endArrowType: 'triangle' } });
  rect(slide, 7.67, 2.0, 4.93, 3.95, C.white, { shadow: true });
  text(slide, '2  GET A TRANSPARENT ESTIMATE', 8.05, 2.37, 3.25, 0.18, { fontSize: 9.4, color: C.teal, bold: true, charSpacing: 0.75 });
  text(slide, 'Predicted views', 8.05, 2.93, 1.72, 0.18, { fontSize: 11.5, color: C.slate, bold: true });
  rect(slide, 10.35, 2.82, 1.75, 0.48, C.mint, { radius: 0.1 });
  text(slide, 'expm1()', 10.35, 2.98, 1.75, 0.14, { fontSize: 9, color: C.navy, bold: true, align: 'center' });
  text(slide, 'Predicted engagement', 8.05, 3.69, 2.1, 0.18, { fontSize: 11.5, color: C.slate, bold: true });
  rect(slide, 10.35, 3.58, 1.75, 0.48, C.gold, { radius: 0.1 });
  text(slide, 'as a %', 10.35, 3.74, 1.75, 0.14, { fontSize: 9, color: C.navy, bold: true, align: 'center' });
  text(slide, '3  COMPARE DRAFTS AND EXPLAIN THE INPUTS', 8.05, 4.48, 3.75, 0.18, { fontSize: 9.4, color: C.coral, bold: true, charSpacing: 0.55 });
  text(slide, 'Use estimates as a decision aid — not a promise.', 8.05, 4.9, 3.72, 0.28, { fontSize: 12, color: C.ink, bold: true });
  footer(slide, 'Demo workflow: draft → feature row → saved model → human-readable result', true);
}

// 12. Limits
{
  const slide = pptx.addSlide();
  base(slide, false, '12');
  title(slide, 'What the model cannot see is as important as what it can', 'A strong presentation states the boundaries of its evidence clearly.');
  const limits = [
    ['TRENDING-ONLY SAMPLE', 'The dataset has no non-trending comparison group, so we estimate relative performance among videos that already succeeded.', C.coral],
    ['MISSING HIGH-IMPACT SIGNALS', 'Thumbnail quality, channel reputation, audience retention and platform ranking signals are not available.', C.gold],
    ['MODEL FIT', 'Pre-publication metadata explains about 42% of log-view variation (37% on later uploads) and 64% of engagement variation (53% on later uploads).', C.mint]
  ];
  limits.forEach((l, i) => {
    const x = 0.68 + i * 4.12;
    rect(slide, x, 2.08, 3.58, 3.65, C.white, { shadow: true });
    rect(slide, x + 0.28, 2.37, 0.5, 0.5, l[2], { radius: 0.25 });
    text(slide, String(i + 1), x + 0.28, 2.5, 0.5, 0.16, { fontSize: 10.8, color: C.navy, bold: true, align: 'center' });
    text(slide, l[0], x + 0.3, 3.22, 2.94, 0.24, { fontSize: 11, color: C.ink, bold: true, charSpacing: 0.55 });
    text(slide, l[1], x + 0.3, 3.76, 2.88, 1.3, { fontSize: 12.4, color: C.slate, valign: 'top' });
  });
  rect(slide, 0.68, 6.14, 11.98, 0.45, C.fog, { radius: 0.1 });
  text(slide, 'Responsible conclusion: the system supports better questions and comparisons, not certainty about a future audience.', 0.95, 6.28, 11.45, 0.15, { fontSize: 10.8, color: C.ink, bold: true, align: 'center' });
  footer(slide, 'Limitations are part of the result, not an afterthought');
}

// 13. Future-ready enhancements
{
  const slide = pptx.addSlide();
  base(slide, true, '13');
  title(slide, 'How the project can grow from a strong baseline', 'The current system is deliberately interpretable; the next version can expand the evidence without sacrificing clarity.', true);
  const future = [
    ['01', 'Richer title semantics', 'Readability, sentiment and topic features can add nuance beyond simple length and capitalisation.', C.mint],
    ['02', 'Thumbnail intelligence', 'Computer-vision features can capture visual packaging, a major missing signal today.', C.gold],
    ['03', 'Better outcome dataset', 'Collect fixed-age performance for trending and non-trending uploads to reduce survivorship bias.', C.coral],
    ['04', 'Creator feedback loop', 'Compare predicted versus actual outcomes, then retrain with newer data and real experiments.', C.blue]
  ];
  future.forEach((f, i) => {
    const col = i % 2;
    const row = Math.floor(i / 2);
    numberedCard(slide, f[0], f[1], f[2], 0.72 + col * 6.1, 2.04 + row * 1.7, 5.57, 1.26, f[3], true);
  });
  footer(slide, 'Future work is a roadmap, not a claim about the current fitted model', true);
}

// 14. Closing
{
  const slide = pptx.addSlide();
  base(slide, true, '14');
  text(slide, 'The takeaway', 0.72, 1.32, 3.2, 0.32, { fontSize: 14, color: C.mint, bold: true, charSpacing: 1.1 });
  text(slide, 'A student-built,\nexplainable ML system\nthat makes upload\nchoices discussable.', 0.72, 1.82, 7.15, 2.45,
    { fontFace: 'Georgia', fontSize: 30, color: C.white, bold: true, valign: 'top' });
  rect(slide, 8.62, 1.55, 3.48, 3.95, C.navy2, { line: { color: '32536D', width: 0.8 } });
  const close = [
    ['DATA', '16,307 unique videos'],
    ['MODEL', 'Random Forest + calibrated intervals'],
    ['DEMO', 'Explain, time, edit, compare'],
    ['LIVE', 'youtube-strategy-predictor.onrender.com']
  ];
  close.forEach((c, i) => {
    text(slide, c[0], 9.03, 1.85 + i * 0.82, 1.0, 0.16, { fontSize: 9.5, color: [C.mint, C.gold, C.coral, C.blue][i], bold: true, charSpacing: 0.9 });
    text(slide, c[1], 9.03, 2.13 + i * 0.82, 2.95, 0.22, { fontSize: i === 3 ? 10.2 : 13, color: C.white, bold: true });
  });
  text(slide, 'Thank you', 0.72, 5.48, 3.1, 0.36, { fontFace: 'Georgia', fontSize: 20, color: C.gold, bold: true });
  text(slide, 'Questions, model walkthrough, or live demo?', 0.72, 5.96, 6.1, 0.26, { fontSize: 14, color: C.pale });
  footer(slide, 'AI-Based YouTube Analytics and Content Strategy Prediction', true);
}

async function writeDeck() {
  await pptx.writeFile({ fileName: out });
  console.log(`Wrote ${out}`);
}

writeDeck().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});

