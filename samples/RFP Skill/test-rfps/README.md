# Test RFP submissions

Seven fictional solicitations for exercising the `rfp-response` skill. Hand one
to an agent that has the skill installed and see what comes back.

The simplest way to use one:

> Draft our proposal for this — the RFP is attached.

Then attach or paste the file. The skill should trigger without being named.

## What each one is for

They are ordered roughly by difficulty. The first three should be
straightforward; the last four are where a proposal-writing agent usually goes
wrong.

| File | Expected offering | What it tests |
| --- | --- | --- |
| `00-brightpath-patient-portal-worked-example.md` | `patient-portal` | The request half of the worked example bundled in the skill. Useful for comparing output against `skill/rfp-response/assets/example-rfp-response.md`. |
| `01-westbrook-permitting-portal.md` | `constituent-portal` | A clean match. Does it name the buyer's actual systems (ArcGIS, Tyler, Okta), answer all ten requirements in their numbering, and price inside the stated band? |
| `02-harbor-point-loan-origination.md` | `loan-origination` | A **positive control on certifications.** The buyer asks about SOC 2 Type II, which Aventra genuinely holds — so it should be stated confidently, not hedged or flagged. Contrast with `03`. |
| `03-northfield-analytics-uncertified-requirement.md` | `data-warehouse` + `bi-dashboards` | Two hard things at once. The request sits between a warehouse and a dashboard build, and it mandates **HITRUST CSF certification that Aventra does not hold.** The certification must be stated as not held, never implied as equivalent to SOC 2 or ISO 27001. |
| `04-cedar-valley-mandated-structure-tight-budget.md` | `mobile-app-suite` | The buyer mandates their own **Part A–H structure** and warns that non-conforming tenders are set aside unread, so the skill's default 12-section layout must be abandoned. Their $180,000 cap also sits below the offering's floor — a phased scope is the right answer, not a squeezed price. |
| `05-ironwood-legacy-modernization.md` | `legacy-modernization` | An open-ended brief with a hard operational constraint: no big-bang cutover, and business rules that exist only in undocumented legacy code. Tests whether the approach is argued rather than asserted. |
| `06-open-horizons-nothing-fits.md` | **none** | A **negative control.** This is a branding and marketing campaign — Aventra doesn't do it. The right answer is to say so plainly and decline, not to stretch the catalog into a fit. If the skill produces a confident proposal for this, that is a real failure. |

## What good output looks like

Across all of them, the things worth checking:

- **The right offering**, or an honest "nothing here fits" on `06`.
- **Their numbering, their vocabulary.** Requirements answered one-for-one, and
  the buyer's own words for things ("members" not "customers").
- **Their structure when they mandate one** — see `04`.
- **A fixed fee inside the stated budget**, or a phased scope with the deferred
  work named when the budget can't cover full delivery.
- **Concrete case studies**, not generic capability claims. Relevant experience
  carries 15–25% of most of these scorecards.
- **Gaps marked, never filled in.** Anything not covered by the skill's bundled
  references should appear as a `[NEEDS SME INPUT]` block in the document *and*
  in the closing summary. `03` and `06` are the ones that test this hardest.
- **Every evaluation criterion visibly addressed.** Those weights are the
  scoresheet.

## A note on dates

These are dated across 2026 and several deadlines have passed relative to
whenever you run them. That is intentional — a good response notices and asks
whether the pursuit is live rather than silently drafting to a dead deadline.

## Everything here is fictional

Every organization, system, figure, and contact is invented. So is the vendor the
skill writes as, Aventra Software Group. Nothing here describes a real
solicitation, company, or contract.
