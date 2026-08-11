# Aventra product & services documentation

> **Optional.** The `rfp-response` skill does not need these files — it carries
> its own copies of the offering detail, case studies, and pricing, and works
> with nothing else installed. These documents exist for two other reasons:
> human-readable sales collateral, and a growth path if the content ever
> outgrows the skill package.

Word and PDF versions of the whole catalog. Product marketing can read and
circulate them, and if you later want the agent to draw on a content library too
large to bundle, they can be attached as a knowledge source — **Copilot Studio →
Knowledge** or **Cowork → Sources**, both of which accept direct file upload, so
even that path needs no external service.

Everything here is **generated from the catalog** in
`build/rfp-automation-kit/rfpkit/catalog_data.py`, which stays the single source of
truth, so these documents cannot disagree with the skill or the sample proposals.

```bash
python build/tools/export_knowledge_data.py   # catalog -> build/knowledge-data.json
node   build/tools/build_knowledge_base.js    # -> .docx
# then, to refresh the PDFs:
cd knowledge-base && soffice --headless --convert-to pdf --outdir . *.docx \
  && soffice --headless --convert-to pdf --outdir offerings offerings/*.docx
```

## What's here

| Document | Answers | Skill equivalent |
| --- | --- | --- |
| `Aventra-Service-Catalog` | What do we sell? Which offering fits this RFP? | `references/catalog.md` |
| `Aventra-Past-Performance-and-References` | What comparable work have we done? What can we claim? | `references/past-performance.md` |
| `Aventra-Pricing-and-Engagement-Models` | What does it cost, what's included, what if their budget is short? | `references/pricing.md` |
| `offerings/Aventra-<Offering>-Datasheet` (×15) | Full capabilities, integrations, differentiators, success measures | `references/offerings-<line>.md` |

The right-hand column is the bundled copy the skill actually reads. Both are
generated from the same catalog, so they say the same things in different formats.

Both `.docx` and `.pdf` are provided — Word for editing and circulation, PDF for
reading and for knowledge sources that prefer it.

## When you'd actually switch to using these as knowledge

Bundling is the better default at this size: one artifact to upload, the agent
reads approved commitment language verbatim rather than a retrieved paraphrase,
and there's no "knowledge base unreachable" failure mode. Testing bore that out —
with the content bundled the skill cites concrete case studies; in a run where the
knowledge base was deliberately withheld it correctly flagged experience as
unevidenced, but the proposal was measurably thinner.

Reach for a knowledge source when the content stops fitting:

- **Volume.** A real content library — hundreds of past proposals, SIG/CAIQ
  security questionnaires, a live rate card — blows past 20 companion files and
  10 MB quickly.
- **Update cadence.** Bundled content means a price change requires rebuilding
  and re-uploading the skill.
- **Reuse.** Other agents (sales chat, pre-sales Q&A) can share a knowledge
  source; they can't share skill companions.

If you do switch, keep one thing in mind: **retrieval always returns something.**
A semantically close chunk is not the same as an answer to the requirement in
front of you, so the skill would need to check relevance and flag uncovered
requirements rather than stretch the nearest match. Commitment language — SLAs,
certifications, security posture — is best kept inside the skill as verbatim text
either way. A paraphrased service level is a contractual problem.

## Note

Aventra Software Group is fictional and every figure, client, and outcome in
these documents is invented. Each document carries a sample notice saying so.
Replace the catalog with real content before any of this represents a real
vendor.
