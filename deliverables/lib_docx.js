// Small helper layer over the `docx` library, shared by build_report.js and build_notes.js.
const fs = require('fs');
const path = require('path');
const {
  Document, Packer, Paragraph, TextRun, ImageRun, Table, TableRow, TableCell, WidthType, ShadingType, AlignmentType,
  HeadingLevel, BorderStyle, PageBreak, Footer, PageNumber, LevelFormat, VerticalAlign,
} = require('docx');

const ASSETS = path.join(__dirname, 'assets');
const PAGE = { width: 11906, height: 16838, margin: 1080 }; // A4
const CONTENT_DXA = PAGE.width - 2 * PAGE.margin;

function pngInfo(file) {
  const buffer = fs.readFileSync(file);
  return { buffer, width: buffer.readUInt32BE(16), height: buffer.readUInt32BE(20) };
}

function kit({ font, size, accent, dark }) {
  // inline markup: **bold**, __italic__
  const runs = (text, base = {}) =>
    String(text).split(/(\*\*[^*]+\*\*|__[^_]+__)/g).filter(Boolean).map((part) => {
      if (part.startsWith('**')) return new TextRun({ text: part.slice(2, -2), bold: true, font, size, ...base });
      if (part.startsWith('__')) return new TextRun({ text: part.slice(2, -2), italics: true, font, size, ...base });
      return new TextRun({ text: part, font, size, ...base });
    });

  const p = (text, o = {}) =>
    new Paragraph({
      alignment: o.align || AlignmentType.LEFT,
      spacing: { before: o.before ?? 0, after: o.after ?? 120, line: o.line ?? 300 },
      keepNext: o.keepNext, indent: o.indent,
      children: runs(text, o.run || {}),
    });

  const heading = (level, text) => {
    const sizes = { 1: size + 10, 2: size + 5, 3: size + 2 };
    return new Paragraph({
      heading: [null, HeadingLevel.HEADING_1, HeadingLevel.HEADING_2, HeadingLevel.HEADING_3][level],
      keepNext: true, spacing: { before: level === 1 ? 360 : 240, after: 120 },
      children: [new TextRun({ text, bold: true, font, size: sizes[level], color: level === 3 ? dark : accent })],
    });
  };

  let listCounter = 0;
  const bullets = (items, ref = 'bullets') =>
    items.map((t) => new Paragraph({ numbering: { reference: ref, level: 0 }, spacing: { after: 70, line: 290 }, children: runs(t) }));
  // each numbered list gets its own instance so numbering restarts at 1
  const numbered = (items) => {
    const instance = ++listCounter;
    return items.map((t) => new Paragraph({ numbering: { reference: 'numbers', level: 0, instance }, spacing: { after: 70, line: 290 }, children: runs(t) }));
  };

  const figure = (file, widthIn, caption) => {
    const info = pngInfo(path.join(ASSETS, file));
    const w = Math.round(widthIn * 96);
    const h = Math.round((w * info.height) / info.width);
    const out = [new Paragraph({
      alignment: AlignmentType.CENTER, keepNext: true, spacing: { before: 120, after: 60 },
      children: [new ImageRun({ type: 'png', data: info.buffer, transformation: { width: w, height: h },
        altText: { title: caption || file, description: caption || file, name: file } })],
    })];
    if (caption) out.push(new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 200 },
      children: [new TextRun({ text: caption, italics: true, font, size: size - 3, color: '555555' })] }));
    return out;
  };

  const border = (color, sz = 4) => ({ style: BorderStyle.SINGLE, size: sz, color });
  const noBorder = { style: BorderStyle.NONE, size: 0, color: 'FFFFFF' };

  const callout = (title, text, color = accent, fill = 'F2F8F5') =>
    new Table({
      width: { size: CONTENT_DXA, type: WidthType.DXA }, columnWidths: [CONTENT_DXA],
      rows: [new TableRow({ children: [new TableCell({
        width: { size: CONTENT_DXA, type: WidthType.DXA },
        shading: { fill, type: ShadingType.CLEAR, color: 'auto' },
        margins: { top: 100, bottom: 100, left: 180, right: 160 },
        borders: { top: noBorder, bottom: noBorder, right: noBorder, left: border(color, 24) },
        children: [
          new Paragraph({ spacing: { after: 40 }, children: [new TextRun({ text: title, bold: true, font, size: size - 1, color })] }),
          ...(Array.isArray(text) ? text : [text]).map((t) => new Paragraph({ spacing: { after: 40, line: 280 }, children: runs(t, { size: size - 1 }) })),
        ],
      })] })],
    });

  const table = (headers, rows, widths) => {
    const total = widths.reduce((a, b) => a + b, 0);
    const cols = widths.map((w) => Math.round((w / total) * CONTENT_DXA));
    const cell = (text, i, head) => new TableCell({
      width: { size: cols[i], type: WidthType.DXA }, verticalAlign: VerticalAlign.CENTER,
      shading: head ? { fill: accent, type: ShadingType.CLEAR, color: 'auto' } : undefined,
      margins: { top: 70, bottom: 70, left: 100, right: 100 },
      borders: { top: border('C9D1D9'), bottom: border('C9D1D9'), left: border('C9D1D9'), right: border('C9D1D9') },
      children: [new Paragraph({ spacing: { after: 0 }, children: runs(text, head ? { bold: true, color: 'FFFFFF', size: size - 1 } : { size: size - 1 }) })],
    });
    return new Table({
      width: { size: CONTENT_DXA, type: WidthType.DXA }, columnWidths: cols,
      rows: [new TableRow({ tableHeader: true, children: headers.map((h, i) => cell(h, i, true)) }),
        ...rows.map((r) => new TableRow({ cantSplit: true, children: r.map((c, i) => cell(c, i, false)) }))],
    });
  };

  const gap = (after = 120) => new Paragraph({ spacing: { after }, children: [] });
  const pageBreak = () => new Paragraph({ children: [new PageBreak()] });

  const banner = (text, fill = accent) =>
    new Paragraph({ spacing: { before: 300, after: 160 }, keepNext: true,
      shading: { fill, type: ShadingType.CLEAR, color: 'auto' }, indent: { left: 0 },
      children: [new TextRun({ text: `  ${text}  `, bold: true, font, size: size + 8, color: 'FFFFFF' })] });

  return { runs, p, heading, bullets, numbered, figure, callout, table, gap, pageBreak, banner, border };
}

function numberingConfig(font, size) {
  const level = (format, text) => ({ level: 0, format, text, alignment: AlignmentType.LEFT,
    style: { paragraph: { indent: { left: 540, hanging: 300 } }, run: { font, size } } });
  return { config: [
    { reference: 'bullets', levels: [level(LevelFormat.BULLET, '•')] },
    { reference: 'numbers', levels: [level(LevelFormat.DECIMAL, '%1.')] },
  ] };
}

function buildDocument({ font, size, accent, children, footerText }) {
  return new Document({
    creator: 'Signal Studio team', title: footerText,
    styles: { default: { document: { run: { font, size } } } },
    numbering: numberingConfig(font, size),
    sections: [{
      properties: { page: { size: { width: PAGE.width, height: PAGE.height }, margin: { top: PAGE.margin, bottom: PAGE.margin, left: PAGE.margin, right: PAGE.margin } } },
      footers: { default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.CENTER,
        children: [new TextRun({ text: `${footerText}   |   Page `, font, size: 18, color: '777777' }), new TextRun({ children: [PageNumber.CURRENT], font, size: 18, color: '777777' })] })] }) },
      children,
    }],
  });
}

async function save(doc, file) {
  fs.writeFileSync(file, await Packer.toBuffer(doc));
  console.log('wrote', file);
}

module.exports = { kit, buildDocument, save, ASSETS, AlignmentType, TextRun, Paragraph, Table, TableRow, TableCell, WidthType, ShadingType, BorderStyle, CONTENT_DXA, fs, path };
