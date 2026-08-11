/**
 * Build the Aventra product & services knowledge base as Word documents.
 *
 * These are the documents you point Copilot Studio "Knowledge" or Cowork
 * "Sources" at. They carry the content that changes often and doesn't belong
 * inside a skill package: full offering datasheets, past performance and
 * references, and pricing/engagement models.
 *
 * Content is generated from build/knowledge-data.json, which is exported from
 * the catalog in rfp-automation-kit — the single source of truth — so these
 * documents cannot drift from what the skill and the samples use.
 *
 *   node build/tools/build_knowledge_base.js [outputDir]
 */

const fs = require("fs");
const path = require("path");
const {
  Document, Packer, Paragraph, TextRun, HeadingLevel, AlignmentType,
  Table, TableRow, TableCell, WidthType, ShadingType, BorderStyle,
  PageOrientation, LevelFormat, PageBreak, Header, Footer, PageNumber,
} = require("docx");

const SAMPLE = path.resolve(__dirname, "..", "..");
const REPO = SAMPLE;
const DATA = JSON.parse(fs.readFileSync(path.join(SAMPLE, "build", "knowledge-data.json"), "utf8"));
const OUT = path.resolve(process.argv[2] || path.join(SAMPLE, "knowledge-base"));

const ACCENT = "0B5D51";
const MUTED = "4A5568";
const LETTER = { width: 12240, height: 15840 }; // DXA, US Letter
const CONTENT_W = 12240 - 1440 - 1440;          // page width less 1" margins

// ---------------------------------------------------------------------------
// Building blocks
// ---------------------------------------------------------------------------

const bullets = {
  config: [{
    reference: "bullets",
    levels: [{
      level: 0, format: LevelFormat.BULLET, text: "•",
      alignment: AlignmentType.LEFT,
      style: { paragraph: { indent: { left: 460, hanging: 240 } } },
    }],
  }],
};

const P = (text, opts = {}) => new Paragraph({
  spacing: { after: opts.after ?? 120, line: 276 },
  alignment: opts.align,
  children: [new TextRun({
    text, bold: opts.bold, italics: opts.italic,
    color: opts.color, size: opts.size ?? 21, // half-points => 10.5pt
  })],
});

const Bullet = (text) => new Paragraph({
  numbering: { reference: "bullets", level: 0 },
  spacing: { after: 60, line: 276 },
  children: [new TextRun({ text, size: 21 })],
});

const H = (text, level) => new Paragraph({
  heading: level,
  spacing: { before: 260, after: 120 },
  children: [new TextRun({ text, bold: true, color: ACCENT, size: level === HeadingLevel.HEADING_1 ? 30 : 24 })],
});

const Rule = () => new Paragraph({
  spacing: { before: 60, after: 160 },
  border: { bottom: { style: BorderStyle.SINGLE, size: 6, color: "DDE3EA" } },
  children: [new TextRun({ text: "", size: 2 })],
});

/** Two-column label/value table. */
function factTable(rows) {
  const w = [Math.round(CONTENT_W * 0.32), Math.round(CONTENT_W * 0.68)];
  return new Table({
    columnWidths: w,
    width: { size: CONTENT_W, type: WidthType.DXA },
    rows: rows.map(([label, value], i) => new TableRow({
      children: [
        new TableCell({
          width: { size: w[0], type: WidthType.DXA },
          shading: i % 2 ? undefined : { type: ShadingType.CLEAR, fill: "F4F7F6" },
          margins: { top: 80, bottom: 80, left: 120, right: 120 },
          children: [new Paragraph({ children: [new TextRun({ text: label, bold: true, size: 19, color: MUTED })] })],
        }),
        new TableCell({
          width: { size: w[1], type: WidthType.DXA },
          shading: i % 2 ? undefined : { type: ShadingType.CLEAR, fill: "F4F7F6" },
          margins: { top: 80, bottom: 80, left: 120, right: 120 },
          children: [new Paragraph({ children: [new TextRun({ text: value, size: 19 })] })],
        }),
      ],
    })),
  });
}

/** Header-row table from a 2D array. */
function gridTable(headers, rows, weights) {
  const w = weights.map((f) => Math.round(CONTENT_W * f));
  const cell = (text, { head = false, width } = {}) => new TableCell({
    width: { size: width, type: WidthType.DXA },
    shading: head ? { type: ShadingType.CLEAR, fill: "EAF3F1" } : undefined,
    margins: { top: 80, bottom: 80, left: 120, right: 120 },
    children: [new Paragraph({
      children: [new TextRun({ text, bold: head, size: 18, color: head ? ACCENT : undefined })],
    })],
  });
  return new Table({
    columnWidths: w,
    width: { size: CONTENT_W, type: WidthType.DXA },
    rows: [
      new TableRow({ tableHeader: true, children: headers.map((h, i) => cell(h, { head: true, width: w[i] })) }),
      ...rows.map((r) => new TableRow({ children: r.map((c, i) => cell(String(c), { width: w[i] })) })),
    ],
  });
}

const money = (n) => "$" + n.toLocaleString("en-US");
const cap = (s) => s.charAt(0).toUpperCase() + s.slice(1);

function docShell(title, subtitle, children) {
  return new Document({
    numbering: bullets,
    styles: {
      default: { document: { run: { font: "Calibri", size: 21 } } },
    },
    sections: [{
      properties: {
        page: { size: { ...LETTER, orientation: PageOrientation.PORTRAIT },
                margin: { top: 1080, bottom: 1080, left: 1440, right: 1440 } },
      },
      headers: {
        default: new Header({
          children: [new Paragraph({
            alignment: AlignmentType.RIGHT,
            spacing: { after: 120 },
            border: { bottom: { style: BorderStyle.SINGLE, size: 6, color: "DDE3EA" } },
            children: [new TextRun({ text: `${DATA.vendor.name} · ${subtitle}`, size: 16, color: MUTED })],
          })],
        }),
      },
      footers: {
        default: new Footer({
          children: [new Paragraph({
            alignment: AlignmentType.CENTER,
            children: [
              new TextRun({ text: "Internal reference document · fictional sample content · page ", size: 15, color: MUTED }),
              new TextRun({ children: [PageNumber.CURRENT], size: 15, color: MUTED }),
            ],
          })],
        }),
      },
      children,
    }],
  });
}

function titleBlock(title, subtitle) {
  return [
    new Paragraph({
      spacing: { after: 60 },
      children: [new TextRun({ text: subtitle.toUpperCase(), bold: true, size: 17, color: ACCENT })],
    }),
    new Paragraph({
      spacing: { after: 80 },
      children: [new TextRun({ text: title, bold: true, size: 44, color: ACCENT })],
    }),
    Rule(),
  ];
}

const SAMPLE_NOTE = () => new Paragraph({
  spacing: { before: 200, after: 160 },
  shading: { type: ShadingType.CLEAR, fill: "FDF8E8" },
  border: { left: { style: BorderStyle.SINGLE, size: 18, color: "C9A227" } },
  children: [new TextRun({
    text: "Sample content. Aventra Software Group is a fictional company used for "
        + "demonstration. Every organization, figure, client, and outcome in this "
        + "document is invented and does not describe any real entity or engagement.",
    size: 16, color: "5C4813", italics: true,
  })],
});

// ---------------------------------------------------------------------------
// Documents
// ---------------------------------------------------------------------------

function serviceCatalog() {
  const c = [...titleBlock("Service Catalog", "Products & Services")];
  c.push(SAMPLE_NOTE());
  c.push(H("About " + DATA.vendor.name, HeadingLevel.HEADING_1));
  c.push(P(DATA.vendor.overview));
  c.push(factTable([
    ["Founded", String(DATA.vendor.founded)],
    ["Headquarters", DATA.vendor.headquarters],
    ["Employees", DATA.vendor.employees],
    ["Certifications", DATA.vendor.certifications.join(", ")],
    ["Proposals contact", `${DATA.vendor.email} · ${DATA.vendor.phone}`],
  ]));

  c.push(H("Core capabilities", HeadingLevel.HEADING_2));
  DATA.vendor.capabilities.forEach((x) => c.push(Bullet(x)));

  c.push(H("All offerings at a glance", HeadingLevel.HEADING_1));
  c.push(P("Indicative ranges describe a typical full-scope engagement. Actual "
         + "pricing is fixed against the scope confirmed in discovery.", { italic: true, color: MUTED }));
  c.push(gridTable(
    ["Offering", "Product line", "Indicative range", "Months"],
    DATA.offerings.map((o) => [
      o.name, DATA.product_lines[o.line].name,
      `${money(o.price_low)} – ${money(o.price_high)}`, String(o.timeline_months),
    ]),
    [0.34, 0.28, 0.26, 0.12],
  ));

  Object.entries(DATA.product_lines).forEach(([key, line]) => {
    c.push(H(line.name, HeadingLevel.HEADING_1));
    c.push(P(line.summary, { italic: true, color: MUTED }));
    DATA.offerings.filter((o) => o.line === key).forEach((o) => {
      c.push(H(o.name, HeadingLevel.HEADING_2));
      c.push(P(o.tagline, { italic: true, color: MUTED }));
      c.push(P(cap(o.summary) + "."));
      c.push(factTable([
        ["Best fit for", o.target_industries.join(", ")],
        ["Compliance", o.compliance.join(", ")],
        ["Pricing", `${o.pricing_model} · ${money(o.price_low)} – ${money(o.price_high)}`],
        ["Typical duration", `${o.timeline_months} months`],
      ]));
      c.push(P("See the dedicated datasheet for full capabilities, integrations, "
             + "and positioning.", { italic: true, color: MUTED, size: 18 }));
    });
  });

  c.push(new Paragraph({ children: [new PageBreak()] }));
  c.push(H("Choosing between close matches", HeadingLevel.HEADING_1));
  [
    "An RFP naming a system the buyer's own customers use — patients, constituents, members, students — usually wants an Industry Solutions offering rather than a generic custom application.",
    "“Reporting is slow / our numbers disagree” points to Enterprise Data Warehouse when the organization needs one governed source of truth; to Business Intelligence & Dashboards when the warehouse already exists and the gap is the front end; to Data Integration & Pipelines when the ask is moving data rather than analysing it.",
    "“Connect our systems” points to Enterprise Systems Integration for internal workflows, and to API Development & Management when the buyer wants reusable, governed APIs for internal or partner developers.",
    "“Replace our old system” points to Legacy Application Modernization when the existing system must keep running through the transition, and to Custom Web Application Platform for a clean-sheet build.",
    "An RFP mostly about running software that already exists points to Application Managed Services; one mostly about assessment and hardening points to Security & Compliance Services.",
    "A large RFP can legitimately span two offerings. Lead with the primary one and present the second as a named, separately priced workstream.",
  ].forEach((x) => c.push(Bullet(x)));

  return { name: "Aventra-Service-Catalog.docx", doc: docShell("Service Catalog", "Service Catalog", c) };
}

function datasheet(o) {
  const line = DATA.product_lines[o.line];
  const c = [...titleBlock(o.name, "Offering Datasheet")];
  c.push(P(o.tagline, { italic: true, color: MUTED, size: 24 }));
  c.push(SAMPLE_NOTE());

  c.push(factTable([
    ["Offering ID", o.id],
    ["Product line", line.name],
    ["Best fit for", o.target_industries.join(", ")],
    ["Compliance frameworks", o.compliance.join(", ")],
    ["Pricing model", o.pricing_model],
    ["Indicative range", `${money(o.price_low)} – ${money(o.price_high)}`],
    ["Typical duration", `${o.timeline_months} months`],
  ]));

  c.push(H("Scope", HeadingLevel.HEADING_1));
  c.push(P(cap(o.summary) + "."));

  c.push(H("Capabilities delivered", HeadingLevel.HEADING_1));
  c.push(P("Describe these in the proposed-solution section of a response.", { italic: true, color: MUTED, size: 18 }));
  o.capabilities.forEach((x) => c.push(Bullet(x)));

  c.push(H("Requirements this offering answers", HeadingLevel.HEADING_1));
  c.push(P("If an RFP asks for these, this offering is the right match.", { italic: true, color: MUTED, size: 18 }));
  o.typical_requirements.forEach((x) => c.push(Bullet(x)));

  c.push(H("Integrations", HeadingLevel.HEADING_1));
  c.push(P("Name the buyer's actual systems when the RFP identifies them; these are "
         + "the fallback.", { italic: true, color: MUTED, size: 18 }));
  o.integrations.forEach((x) => c.push(Bullet(cap(x))));

  c.push(H("Differentiators", HeadingLevel.HEADING_1));
  o.differentiators.forEach((x) => c.push(Bullet(x)));

  c.push(H("Success measures buyers care about", HeadingLevel.HEADING_1));
  c.push(P("Mirror these in an executive summary when the RFP states similar goals.", { italic: true, color: MUTED, size: 18 }));
  o.success_metrics.forEach((x) => c.push(Bullet(cap(x))));

  c.push(H("Approved positioning language", HeadingLevel.HEADING_1));
  c.push(P("Adapt the wording to the buyer's own terms; keep the substance intact.", { italic: true, color: MUTED, size: 18 }));
  c.push(P("Understanding of needs", { bold: true }));
  c.push(P(o.snippets.understanding));
  c.push(P("Proposed solution", { bold: true }));
  c.push(P(o.snippets.solution));

  const safe = o.name.replace(/[^A-Za-z0-9]+/g, "-").replace(/^-|-$/g, "");
  return { name: `offerings/Aventra-${safe}-Datasheet.docx`, doc: docShell(o.name, "Offering Datasheet", c) };
}

function pastPerformance() {
  const c = [...titleBlock("Past Performance & References", "Qualifications")];
  c.push(SAMPLE_NOTE());
  c.push(P("Representative engagements, organised by industry. Use these to answer "
         + "relevant-experience questions, which typically carry 15–25% of an "
         + "evaluation scorecard. Client names are withheld here; named references "
         + "are released on request under the policy below."));

  Object.entries(DATA.vendor.case_studies).forEach(([industry, studies]) => {
    c.push(H(cap(industry), HeadingLevel.HEADING_1));
    studies.forEach((s) => c.push(Bullet(s)));
  });

  c.push(H("Reference policy", HeadingLevel.HEADING_1));
  [
    "We provide at least three references from comparable engagements, matched by industry and project type, on request.",
    "References are released only with the client's prior consent, so allow five business days when a submission requires named contacts.",
    "Each reference is supplied with a summary of the work delivered and the outcomes achieved.",
    "If a solicitation requires named references at submission rather than on request, raise it with the bid lead before drafting — it changes the timeline.",
  ].forEach((x) => c.push(Bullet(x)));

  c.push(H("Certifications", HeadingLevel.HEADING_1));
  DATA.vendor.certifications.forEach((x) => c.push(Bullet(x)));
  c.push(P("This list is exhaustive. Any certification not named here is one Aventra "
         + "does not hold — say so plainly in a response rather than implying "
         + "equivalence.", { bold: true }));

  return { name: "Aventra-Past-Performance-and-References.docx",
           doc: docShell("Past Performance & References", "Qualifications", c) };
}

function pricingGuide() {
  const c = [...titleBlock("Pricing & Engagement Models", "Commercial Reference")];
  c.push(SAMPLE_NOTE());
  c.push(P("Indicative ranges for a typical full-scope engagement. A proposal quotes "
         + "a fixed fee against the scope confirmed in discovery, which may sit "
         + "anywhere in — or, with a reduced scope, below — these ranges."));

  c.push(H("Indicative ranges by offering", HeadingLevel.HEADING_1));
  c.push(gridTable(
    ["Offering", "Pricing model", "Indicative range", "Months"],
    DATA.offerings.map((o) => [o.name, o.pricing_model,
      `${money(o.price_low)} – ${money(o.price_high)}`, String(o.timeline_months)]),
    [0.30, 0.30, 0.28, 0.12],
  ));

  c.push(H("How a fixed fee is built up", HeadingLevel.HEADING_1));
  c.push(P("Standard allocation across workstreams. Adjust when the solicitation "
         + "gives a reason — a data-heavy engagement carries more migration, a "
         + "greenfield build carries less."));
  c.push(gridTable(
    ["Workstream", "Share of fee"],
    [["Discovery & solution design", "14%"], ["Development & configuration", "42%"],
     ["Integrations", "16%"], ["Data migration & setup", "8%"],
     ["Quality assurance & security testing", "10%"],
     ["Training, documentation & launch", "6%"], ["Project management", "4%"]],
    [0.72, 0.28],
  ));

  c.push(H("Delivery phases", HeadingLevel.HEADING_1));
  c.push(gridTable(
    ["Phase", "Share of schedule"],
    [["Discovery & Design", "20%"], ["Foundation & Integrations", "25%"],
     ["Core Build", "30%"], ["Testing & Hardening", "15%"],
     ["Launch & Stabilization", "10%"]],
    [0.72, 0.28],
  ));
  c.push(P("Each phase ends with a working, demonstrable increment and a stakeholder review."));

  c.push(H("Included in the fixed fee", HeadingLevel.HEADING_1));
  ["Discovery, design, build, integration, and testing as scoped",
   "Data migration where identified in scope",
   "Accessibility and security review each sprint",
   "Role-based training, written and video documentation, knowledge transfer",
   "Handover of source code, infrastructure-as-code, and documentation in full",
  ].forEach((x) => c.push(Bullet(x)));

  c.push(H("Excluded, and quoted separately", HeadingLevel.HEADING_1));
  ["Third-party software licences and subscriptions, passed through without markup",
   "Ongoing cloud hosting and run costs",
   "Hardware and end-user devices",
   "Post-launch care plan — optional, renewable, quoted as a separate annual figure",
   "Scope added after discovery, handled through change control",
  ].forEach((x) => c.push(Bullet(x)));

  c.push(H("When a buyer's budget sits below the range", HeadingLevel.HEADING_1));
  c.push(P("Do not compress full scope to fit a number. Propose a reduced or phased "
         + "scope at a price that is genuinely deliverable, state plainly which "
         + "functionality is deferred, and price the later phase indicatively so the "
         + "buyer can see the whole path. Underbidding to win is how engagements fail.",
         { bold: true }));

  return { name: "Aventra-Pricing-and-Engagement-Models.docx",
           doc: docShell("Pricing & Engagement Models", "Commercial Reference", c) };
}

// ---------------------------------------------------------------------------

async function main() {
  const docs = [serviceCatalog(), pastPerformance(), pricingGuide(),
                ...DATA.offerings.map(datasheet)];

  fs.mkdirSync(path.join(OUT, "offerings"), { recursive: true });
  for (const { name, doc } of docs) {
    const buf = await Packer.toBuffer(doc);
    const dest = path.join(OUT, name);
    fs.mkdirSync(path.dirname(dest), { recursive: true });
    fs.writeFileSync(dest, buf);
    console.log(`  ${(buf.length / 1024).toFixed(0).padStart(4)} KB  ${name}`);
  }
  console.log(`\nwrote ${docs.length} documents to ${path.relative(REPO, OUT)}/`);
}

main().catch((e) => { console.error(e); process.exit(1); });
