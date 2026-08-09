---
name: rfp-response
description: Draft a complete, submission-ready RFP response (proposal) for Aventra Software Group from an incoming RFP, RFI, RFQ, tender, or vendor questionnaire — matching the request to the right product offering, answering requirements from a library of pre-approved answers, and delivering Markdown plus a formatted PDF. Use this skill whenever someone shares a solicitation and wants a proposal, bid, or response drafted; whenever they say "respond to this RFP", "write a proposal", "draft our bid", "we're bidding on this", or "answer these vendor questions"; and whenever the work involves proposal writing, bid submission, or RFP response automation — even if they only paste an excerpt of the requirements, don't name the company, or don't mention a PDF.
---

# RFP Response

Turn an incoming solicitation into a proposal from **Aventra Software Group**,
grounded in what Aventra actually sells and the answers it has already approved.

Two facts about how proposals get judged should shape every decision below:

1. **Evaluators score against their own published criteria, in their own
   vocabulary.** They have a scoresheet with weights on it and often dozens of
   proposals to get through. Anything they have to hunt for loses points, so a
   response that mirrors the buyer's structure and words beats a more elegant one
   that doesn't.
2. **Every sentence is a commitment.** A proposal becomes a contract attachment.
   Claiming a certification the company doesn't hold, or a capability it can't
   staff, is worse than admitting a gap — bluffs get discovered at evaluation or,
   worse, after award.

Everything here follows from those two facts.

## Where the content lives

This skill carries the **method** and the language that must be reused word for
word. The **product content** lives in a separate knowledge base, because it
changes on a different clock and is owned by different people — pricing and
offerings move monthly under product marketing; how to write a bid does not.

| Source | Holds | Use it for |
| --- | --- | --- |
| `references/catalog.md` (bundled) | Every offering: scope, industries, compliance, commercials, approved positioning language | Matching the RFP to an offering, and drafting sections 3–4 |
| `references/answer-library.md` (bundled) | Pre-approved answers to recurring questions | Security, hosting, SSO, accessibility, SLAs, pricing approach |
| **Knowledge base** — `Aventra-<Offering>-Datasheet` | Full capabilities, integrations, differentiators, success measures | Depth in sections 4, 5, 11 |
| **Knowledge base** — `Aventra-Past-Performance-and-References` | Case studies by industry, named-reference policy, the exhaustive certification list | Section 8, and any experience question |
| **Knowledge base** — `Aventra-Pricing-and-Engagement-Models` | Current rates, what's included and excluded, under-budget guidance | Section 9 |

**Search the knowledge base for the offering you matched, plus the experience and
pricing documents, before you start writing.** Relevant experience is routinely
15–25% of the scorecard, and it's the section that most often comes out thin
because nobody looked up an actual case study.

Two rules make retrieval safe, and both matter more here than they would with
everything bundled:

- **Retrieval always returns something.** A semantically close chunk is not the
  same as an answer to the requirement in front of you. Read what comes back and
  ask whether it actually addresses the requirement; if it doesn't, treat the
  requirement as uncovered rather than stretching the nearest match.
- **If the knowledge base isn't connected or returns nothing**, keep going — the
  bundled index and answer library are enough for a sound draft. But say so in
  your closing summary and flag that experience claims are unevidenced, because a
  proposal citing no concrete past work reads very differently to an evaluator.

## Workflow

### 1. Read the solicitation and pull out the brief

Work through the document and capture a short working note. If the RFP is a PDF,
read it directly; if it's a URL, fetch it; if the user pasted an excerpt, use what
you have and note what's missing.

Capture:

- **Buyer** — name, what kind of organization, industry, size if stated
- **The ask** — what they want built, run, or fixed, in their words
- **Requirements** — every functional, technical, security, and compliance item,
  keeping their numbering so you can answer them one for one
- **Integrations** — every system they name
- **Budget** — a stated range, a cap, or nothing
- **Dates** — questions due, proposals due, anticipated award, project start
- **Evaluation criteria and weights** — this is the scoresheet; treat it as one
- **Submission constraints** — page limits, a required section order, file format,
  a reference number to quote

Missing information is normal and is not a reason to stall. Draft with a clearly
labelled assumption, then surface it in section 12 and in your closing summary so
the user can correct it before submission.

### 2. Match the request to an offering

Read `references/catalog.md` — the index of all 15 offerings, with guidance for
telling close matches apart (that guidance exists because the near-misses are
where this goes wrong: a data warehouse and a BI dashboard answer very different
RFPs). Pick the best fit.

Then pull that offering's **datasheet from the knowledge base** for the depth the
index doesn't carry: full capabilities, integrations, differentiators, and
success measures. Search for the offering by name — the documents are titled
`Aventra-<Offering Name>-Datasheet`.

A substantial RFP can legitimately span two offerings. Lead with the primary one
and present the second as a named, separately priced workstream, so the buyer can
see what each costs.

If nothing in the catalog genuinely fits, say so plainly instead of forcing a
match. A well-argued "this is adjacent to our Legacy Modernization practice, here
is what we would and wouldn't take on" is a real answer; a proposal for something
Aventra doesn't do is not.

### 3. Answer the requirements from the library

Read `references/answer-library.md` — pre-approved answers to the questions that
recur in nearly every RFP (security, hosting, SSO, accessibility, support SLAs,
pricing approach, and so on).

- **Reuse the substance exactly.** Keep every standard, timeframe, certification,
  and number as written. These are what Aventra can actually commit to; rewriting
  them from memory is how a proposal ends up promising a 15-minute SLA nobody
  agreed to.
- **Adapt the phrasing** to the buyer's vocabulary. If they say "members," don't
  say "customers." If they call it "the Permit Center," use that name.
- **Handle gaps honestly.** If a requirement isn't covered by a library block, an
  offering capability, or the knowledge base, do not invent an answer. Write
  what's true and mark it clearly, e.g. `> **[NEEDS SME INPUT]** The RFP requires
  FedRAMP Moderate authorization. No approved answer covers this — confirm status
  before submitting.` Then list every flag in your closing summary.

  Certifications deserve particular care: the list in `references/catalog.md` and
  in the past-performance document is **exhaustive**. A framework not named there
  is one Aventra does not hold, and the honest answer is to say so and let the bid
  team decide — not to imply equivalence with something adjacent.

### 4. Write the proposal

**If the RFP specifies its own required structure, section order, or page limit,
follow theirs.** Compliance with submission instructions is often scored, and
occasionally a threshold requirement — a beautifully written non-compliant
proposal can be discarded unread.

Otherwise use this default structure, which matches
`assets/example-rfp-response.md`:

Open with a cover block — an H1 title (`# Proposal in Response to <their reference
number>`), the offering name as an H2 subtitle, who it's submitted by and prepared
for, and a metadata table (their reference number, submission date, vendor,
contact, proposed fee, proposed duration). Then the numbered sections:

| # | Section | What earns points |
| --- | --- | --- |
| 1 | Cover letter | Addressed to their named contact, quotes their reference number, states the fee and that it's within budget |
| 2 | Executive summary | The whole bid in under a page: what, how long, how much, which compliance frameworks |
| 3 | Understanding of your needs | Their objectives played back in their words — proof you read it |
| 4 | Proposed solution | The capabilities you'll deliver, plus each integration they named |
| 5 | Technical approach | Methodology, hosting, security, authentication, integration, QA, accessibility |
| 6 | Project plan and timeline | Phases with month ranges and milestones |
| 7 | Project team | Named roles and what each owns |
| 8 | Relevant experience | Real case studies from `Aventra-Past-Performance-and-References`, matched to their industry, plus the reference policy |
| 9 | Pricing | An itemized table summing to the fixed fee, with assumptions |
| 10 | Support and service levels | What happens after launch |
| 11 | Why Aventra | Differentiators, including the offering-specific ones |
| 12 | Assumptions, exclusions, and risks | Everything you assumed, everything not included |

Before you finish, walk the evaluation criteria from step 1 and confirm each one
is visibly addressed somewhere. If "Relevant experience" carries 20% of the score,
section 8 needs real substance, not a sentence.

### 5. Render the PDF

```bash
python scripts/md_to_pdf.py proposal.md -o proposal.pdf
```

The script produces a cover page, styled tables, and running page numbers. It
needs `markdown` and `playwright` (`pip install markdown playwright`); if they're
missing it says so and exits, and the Markdown is still a complete deliverable.
Save both files and tell the user where they are.

### 6. Report back

Close with a short summary: which offering you matched and why, the fee and
duration, where the files are, and — most importantly — **every gap you flagged
and assumption you made**. That list is the difference between a draft someone can
safely submit and one that quietly commits the company to something.

## House patterns

These keep proposals consistent with each other and save you re-deriving them.
Adjust when the RFP gives you a reason to.

**Pricing.** Quote a fixed fee that sits inside both the buyer's stated budget and
the offering's indicative range. Itemize roughly:

| Line item | Share |
| --- | ---: |
| Discovery & solution design | 14% |
| Development & configuration | 42% |
| Integrations | 16% |
| Data migration & setup | 8% |
| Quality assurance & security testing | 10% |
| Training, documentation & launch | 6% |
| Project management | 4% |

If their budget sits below the offering's floor, don't quietly squeeze the number
to fit — propose a reduced or phased scope at a price that's deliverable, and say
plainly what's deferred to a later phase. Underbidding to win is how engagements
fail.

**Timeline.** Five phases: Discovery & Design (20% of the schedule), Foundation &
Integrations (25%), Core Build (30%), Testing & Hardening (15%), Launch &
Stabilization (10%). Each ends in a working, demonstrable increment.

**Team.** Engagement Director, Solution Architect, Lead Engineer, UX Designer,
Project Manager, QA & Security Lead — name each person and what they own.

**Sample-document notice.** Aventra is a fictional company used for demonstration,
so open each generated document with the notice used in
`assets/example-rfp-response.md`. It keeps a demo proposal from being mistaken for
a real bid. Drop it only if the user explicitly repoints this at a real vendor.

## Bundled files

| Path | Read it when |
| --- | --- |
| `references/catalog.md` | Always — to pick the offering, and for approved positioning language |
| `references/answer-library.md` | Always — the pre-approved answers |
| `assets/example-rfp-response.md` | To see the target format and depth end to end |
| `assets/example-rfp-request.md` | To see what a complete solicitation looks like |
| `scripts/md_to_pdf.py` | To render the finished Markdown as a PDF |

The example pair is one matched request and the response written to it — the
clearest illustration of how far a good answer goes beyond restating the question.

Everything else — offering datasheets, case studies, named references, current
pricing — comes from the knowledge base described at the top. If you find
yourself wanting a fact that isn't in the bundled files, search there before
assuming it doesn't exist.
