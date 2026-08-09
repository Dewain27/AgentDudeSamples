# Aventra product & services knowledge base

The documents an agent grounds against when writing a proposal. Point
**Copilot Studio → Knowledge** or **Cowork → Sources** at this set (via
SharePoint or OneDrive), and the `rfp-response` skill will search it for
offering detail, case studies, and current pricing.

Everything here is **generated from the catalog** in
`rfp-automation-kit/rfpkit/catalog_data.py`, which stays the single source of
truth, so these documents cannot disagree with the skill or the sample proposals.

```bash
python tools/export_knowledge_data.py     # catalog -> dist/knowledge-data.json
node   tools/build_knowledge_base.js      # -> .docx
# then, to refresh the PDFs:
cd knowledge-base && soffice --headless --convert-to pdf --outdir . *.docx \
  && soffice --headless --convert-to pdf --outdir offerings offerings/*.docx
```

## What's here

| Document | Answers |
| --- | --- |
| `Aventra-Service-Catalog` | What do we sell? Which offering fits this RFP? |
| `Aventra-Past-Performance-and-References` | What comparable work have we done? What can we claim? |
| `Aventra-Pricing-and-Engagement-Models` | What does it cost, what's included, what if their budget is short? |
| `offerings/Aventra-<Offering>-Datasheet` (×15) | Full capabilities, integrations, differentiators, success measures |

Both `.docx` and `.pdf` are provided — Word for editing and circulation, PDF for
reading and for knowledge sources that prefer it.

## Why these live outside the skill

The skill package carries the **method** and the language that must be reused
word for word (the offering index and the answer library). Product content sits
here instead, for three reasons:

- **It changes on a different clock.** Pricing and offerings move monthly;
  how to write a bid does not. Bundling them means a price change forces a skill
  repackage and re-upload.
- **It has a different owner.** Product marketing owns the catalog; the bid team
  owns the method.
- **It doesn't fit.** A skill package allows 20 companion files. Fifteen
  offerings alone consumed all 20 before a single case study was added.

## The one thing to watch

Retrieval always returns *something*. A semantically close chunk is not the same
as an answer to the requirement in front of you, so the skill is written to check
relevance and to flag an uncovered requirement rather than stretch the nearest
match. That guardrail matters more with a knowledge base than without one — keep
it in mind if you edit the skill.

For the same reason, commitment language — SLAs, certifications, security posture
— deliberately stayed **inside** the skill as verbatim text rather than moving
here. A paraphrased service level is a contractual problem.

## Note

Aventra Software Group is fictional and every figure, client, and outcome in
these documents is invented. Each document carries a sample notice saying so.
Replace the catalog with real content before any of this represents a real
vendor.
