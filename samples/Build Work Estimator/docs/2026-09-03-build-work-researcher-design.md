# Build Work Researcher — Design Spec

**Author:** Dewain Robinson
**Status:** Specified, not implemented
**Date:** 2026-09-03
**Skill:** `plugins/build-work-estimator/skills/build-work-researcher/`

---

## 1. Purpose

A companion skill that improves the **accuracy of the work breakdown** before
an estimate is produced — by researching approaches and challenging
completeness.

It exists because the estimator's own reports name its weakest input:

> *Turn counts per bucket are the weakest input. Everything else is arithmetic
> on measured values.*

That understates it. The turn medians are measured; what they get **applied
to** is not. Someone writes `size: medium, files: 11, unknowns: 2` and the
entire estimate rests on that judgment. Nothing in the estimator checks
whether the breakdown is complete, whether an item is plausibly sized, or
whether the specification is detailed enough to size from at all.

The researcher attacks that gap.

### 1.1 What it produces

**Structure and questions. Never numbers.**

It surfaces work the breakdown is missing, challenges the rationale behind a
size, names unknowns the specification does not, and cites approach patterns
worth considering. A human then decides the sizes.

### 1.2 Why this, and not the researcher first proposed

An earlier proposal was a researcher that verified **rates** and found **cost
factors**. That was wrong, and the reasoning is worth recording because it
constrains this design.

Rate verification has the worst possible profile for automation: it runs about
four times a year, and the material finding last time was a footnote under a
pricing table — that Claude Fable 5.1 reads cache at 0.025× rather than 0.1×.
An agent skimming that page would plausibly miss it or, worse, report a
confident wrong multiplier feeding every estimate. Low frequency, high stakes,
subtle reading. That belongs to a human prompted by the existing 90-day
staleness warning.

Finding **cost factors** is worse still. Asked what brownfield work costs, a
model will produce a plausible number with no basis. The estimator's entire
value is that it cannot fabricate; every input today is measured, published and
human-verified, or declared by someone who knows the answer.

This researcher is safe from that failure for one structural reason: **nothing
it produces is a number, so nothing it produces enters the arithmetic.**

### 1.3 Non-goals

- **Not a cost researcher.** No rates, no multipliers, no effort factors.
- **Not a rate verifier.** That stays human-driven.
- **Not a manifest writer.** It never edits the manifest; a human acts on its
  findings.
- **Not an estimator.** It has no access to calibration data and produces no
  figures.

---

## 2. The boundary

This is the safety-critical section. Everything else is detail.

### 2.1 It MAY

| Capability | Example finding |
| --- | --- |
| Propose a missing component | "The specification requires an immutable supervisory archive (§9 S7) but no work item covers the WORM retention policy or its verification." |
| Challenge a sizing rationale | "`C3 Review pack assembly` is sized `large` with 9 files, yet §3.2 marks it the only *very high* complexity capability and it spans four integrations. The rationale for the same size as C6 is not evident." |
| Name an unstated unknown | "§5 I7 notes KYC latency spikes to 4s, but no item declares an unknown for how that interacts with the p95 2.5s target in N1." |
| Flag a specification too thin to size | "`Client self-service portal` covers five modules (P1–P5) in one `large` item. P4 secure messaging has no defined routing model, so this item cannot be sized with confidence." |
| Cite an approach pattern | "Copilot Studio agent definitions are commonly version-controlled via the VS Code extension and `pac copilot pack`; the breakdown has no item for the ALM path. [source, retrieved date]" |
| Question scope boundaries | "Phases 1 and 2 are estimated together, but §10 assigns the client portal to phase 2 while §4.2 P1 depends on step-up auth introduced in phase 1. Is the split as stated?" |

### 2.2 It MUST NOT

| Prohibited | Why |
| --- | --- |
| Assign or suggest `size`, `files`, `unknowns`, `eval_cases` | These are the estimator's inputs. A suggested value is an anchor, and people accept defaults. |
| Assert turns, hours, days, or cost | Not measurable from a specification. Fabrication with extra steps. |
| Quantify an impact ("this adds roughly 30%") | Same. It may say *what* would change, never *by how much*. |
| Write to the manifest | A human decides what a finding means for the breakdown. |
| Present an external claim without a source | An uncited claim is indistinguishable from an invention. |

### 2.3 Why this boundary needs no new provenance class

The estimator classifies every input: measured, sourced, declared, judged.
A researcher-supplied **number** would need a fifth, weaker class threaded
through the provenance ledger.

A researcher-supplied **component name** needs nothing. It is scope, not a
figure. The human sizes it, and that size is `declared` exactly as it is
today. The provenance system stays untouched.

That is the strongest argument for this boundary: it keeps the machinery
simple rather than requiring new machinery to contain a new risk.

---

## 3. Finding types

| Type | Severity guidance |
| --- | --- |
| `missing-component` | high when the specification requires it; medium when implied |
| `thin-specification` | high when the item cannot be sized; medium when the range should widen |
| `unstated-unknown` | medium — it argues for raising an item's `unknowns` |
| `sizing-rationale` | medium — it questions a size without proposing one |
| `scope-question` | varies — an ambiguity that changes the breakdown |
| `approach-consideration` | low unless it implies missing work |

A finding is only worth raising if it would **change the breakdown**. A comment
that changes nothing is noise, and the review says so in its own summary.

---

## 4. Output

Two artifacts. Neither is a manifest.

### 4.1 `research-review.md`

For a human: findings ordered by severity, each stating what, why, where in
the specification, and what it would change in the breakdown.

### 4.2 `findings.yaml`

Machine-readable, and deliberately **has no numeric fields**:

```yaml
schema: 1
reviewed: 2026-09-03
specification: scenarios/kestrel-financial/specification.md
manifest: scenarios/kestrel-financial/kestrel-claude-code-manifest.yaml
mode: offline                  # offline | web-assisted
findings:
  - id: F-001
    type: missing-component
    severity: high
    title: No work item covers WORM retention policy verification
    rationale: >
      Section 9 control S7 requires an immutable supervisory archive with
      seven-year retention. The breakdown covers the archive integration
      (I9) but nothing covers defining or verifying the retention policy.
    spec_reference: "§9 S7, §7 archive_batch"
    breakdown_impact: >
      A new item is needed, or I9's scope must be stated to include it.
    source: null                # required when the claim is external
    retrieved: null
    status: open                # open | addressed | accepted-as-is
```

**There is no `suggested_size`, no `estimated_turns`, no `impact_percent`.**
The schema has nowhere to put a number, which is the primary enforcement —
a boundary the format cannot express is a boundary that cannot be crossed by
accident.

---

## 5. Integration with the estimator

The researcher runs **before** estimation and never inside it.

```
specification.md ─┐
                  ├─→ Researcher ─→ findings.yaml ─→ human judgment ─→ manifest
draft manifest ───┘                 research-review.md                    │
                                                                          ▼
                                                                     Estimator
```

The estimator gains one **declared** input recording that a review happened:

```yaml
research_review:
  reviewed: 2026-09-03
  findings_total: 14
  findings_addressed: 11
  findings_accepted_as_is: 3
```

This is a declared value like any other — the estimator does not verify the
review's quality, only records its existence. The report states it alongside
the specification status, because *"reviewed, 3 findings knowingly accepted"*
is a materially different confidence signal from *"never reviewed"*.

**Absent is allowed and reported**, the same way a missing specification is:
the report says the breakdown has not been challenged, and names doing so as
an available improvement.

---

## 6. Enforcement

The boundary is checked mechanically, not trusted.

| Gate | Mechanism |
| --- | --- |
| **No numeric fields** | `findings.yaml` schema rejects unknown keys. There is no field a size could occupy. |
| **No quantified prose** | `validate_findings()` rejects a finding whose text matches an effort or cost assertion — `\d+\s*(turns\|hours\|days\|weeks)`, `\$\d`, `\d+\s*%`, `size:\s*(trivial\|small\|medium\|large)`, `roughly \d`, `approximately \d`. |
| **Citations required** | A finding in `web-assisted` mode with an external claim and no `source` + `retrieved` is rejected. |
| **No manifest writes** | The researcher has no manifest-writing code path. A test asserts the module never opens a manifest for writing. |
| **Review is declared, not inferred** | `research_review` is a manifest block a human fills in. The estimator cannot detect a review on its own and does not pretend to. |

Defence in depth matters here because the schema stops structured assertions
but not prose. *"This component will take about 400 turns"* fits in a
`rationale` field, and the text scan is what catches it.

---

## 7. Where it lives

A **separate skill inside the existing plugin**:

```
plugins/build-work-estimator/
├── plugin.json
└── skills/
    ├── build-work-estimator/     existing
    └── build-work-researcher/    new
```

Three reasons:

1. **Different discipline, different failure modes.** The estimator is
   deterministic arithmetic; the researcher is a model reading prose. Keeping
   them separate keeps each one's contract legible.
2. **Companion-file budget is per skill.** The estimator sits at 18/20 against
   the documented ceiling. A second skill gets its own budget rather than
   competing for that headroom.
3. **They install together.** One plugin, so a user gets both without a second
   registration.

---

## 8. Testing

The estimator's suite is fast because it is deterministic. The researcher is
not, so its **outputs are fixture-able** and the boundary tests run offline.

- `test_findings_schema.py` — unknown keys rejected; no numeric field exists;
  a hand-authored finding with `suggested_size` fails.
- `test_boundary_enforced.py` — the security-critical suite. Planted prose
  asserting turns, hours, percentages, dollar figures and bare sizes must each
  be rejected. Written **before** the researcher is wired to a model.
- `test_no_manifest_writes.py` — asserts no write path to a manifest exists.
- `test_review_is_declared.py` — `research_review` is recorded as declared,
  absent is reported, and the estimator never infers a review.
- `test_citations.py` — web-assisted findings without source and retrieval
  date are rejected.

---

## 9. Known limits

1. **It cannot tell you a size.** By design. It tells you the size you chose
   is unsupported, or that a component is missing entirely.
2. **Offline mode reasons only against what it is given.** A thin
   specification yields thin findings — it can say *"this is too thin to size
   from"*, which is useful, but it cannot supply the missing detail.
3. **Web-assisted findings are citations, not measurements.** A reference
   architecture is evidence that an approach exists, not that it fits this
   organisation's constraints.
4. **Findings are not free.** A review that raises fourteen findings costs
   human time to triage. The review states how many would change the
   breakdown, so the noise is visible.
5. **It does not validate the specification against reality.** It checks
   internal consistency and completeness against the breakdown. Whether the
   specification describes a system that will work is a different question.
6. **No measured baseline for finding quality.** There is no calibration data
   saying how many findings a good review produces. Recording review outcomes
   over time is the obvious follow-up, and until then finding counts are
   descriptive rather than diagnostic.

---

## 10. Implementation sequence

1. `findings.yaml` schema and `validate_findings()` — pure deterministic work.
2. **`test_boundary_enforced.py`, passing** — before any model is invoked.
   Same rule that governed `contribute.py`: no path ships ahead of the test
   proving it cannot leak.
3. `research_review` as a declared manifest block, reported by the estimator.
4. `SKILL.md` for the researcher, leading with the boundary.
5. Review renderer for `research-review.md`.
6. Offline mode against the Kestrel specification — the honest first test is
   whether it finds anything real in a specification I wrote.
7. Web-assisted mode, with citations enforced.
8. Packaging as a second skill; companion budget verified independently.

Step 6 is the real gate. If a review of the Kestrel specification produces
only findings that change nothing, the skill does not earn its place and
should not ship.
