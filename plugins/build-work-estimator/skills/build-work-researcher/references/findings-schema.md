# The findings schema

**Author:** Dewain Robinson

A findings document is deliberately **closed**: unknown keys are rejected, and
there is no field a size, a turn count, or a cost could occupy. A boundary the
format cannot express cannot be crossed by accident.

## Document

| Key | Required | Meaning |
| --- | --- | --- |
| `schema` | yes | Always `1` |
| `reviewed` | yes | Date of the review |
| `specification` | no | Path or URL reviewed against |
| `manifest` | no | Path of the breakdown reviewed |
| `mode` | yes | `offline` or `web-assisted` |
| `findings` | yes | List of findings |

## A finding

| Key | Required | Meaning |
| --- | --- | --- |
| `id` | yes | `F-001`, unique within the document |
| `type` | yes | See types below |
| `severity` | yes | `high`, `medium`, `low` |
| `title` | yes | One line, what is wrong |
| `rationale` | yes | Why, referencing the specification |
| `spec_reference` | no | Where in the specification |
| `breakdown_impact` | no | What would change in the breakdown |
| `source` | conditional | Required for a web-assisted external claim |
| `retrieved` | conditional | Required alongside `source` |
| `status` | no | `open`, `addressed`, `accepted-as-is` |

**There is no `suggested_size`, no `estimated_turns`, no `impact_percent`, no
`files`, no `unknowns`.** Their absence is the primary enforcement.

## Types

| Type | Severity guidance |
| --- | --- |
| `missing-component` | high when the specification requires it; medium when implied |
| `thin-specification` | high when the item cannot be sized; medium when the range should widen |
| `unstated-unknown` | medium — it argues for raising an item's declared unknowns |
| `sizing-rationale` | medium — questions a size without proposing one |
| `scope-question` | varies — an ambiguity that changes the breakdown |
| `approach-consideration` | low unless it implies missing work |

## What the validator rejects

Beyond unknown keys, `scripts/findings.py` scans `title`, `rationale` and
`breakdown_impact` for assertions that belong to the estimator:

| Pattern | Example rejected |
| --- | --- |
| Effort | "about 400 turns", "3 days", "2 sprints" |
| Cost | "$4,000" |
| Quantified impact | "adds 30%" |
| A proposed size | "size: large" |
| Hedged quantity | "approximately 12", "~15 files" |
| Estimator inputs | "unknowns: 4", "files: 11" |

`spec_reference` is **not** scanned — a citation like `§9 S7` is not a claim.

If a requirement's magnitude matters, cite it by identifier: write "N4's
availability target", not the number itself.

## Worked example

`examples/kestrel-research-findings.yaml` is a complete review of the Kestrel
Financial specification, and `examples/kestrel-research-review.md` is what it
renders to. Four of its seven findings became work items in the Kestrel
breakdown; three remain open questions for a human.

```yaml
schema: 1
reviewed: "2026-09-04"
specification: scenarios/kestrel-financial/specification.md
manifest: scenarios/kestrel-financial/kestrel-claude-code-manifest.yaml
mode: offline

findings:
  - id: F-001
    type: missing-component
    severity: high
    title: No work item covers backup, restore, or disaster recovery
    rationale: >
      N5 states recovery point and recovery time objectives. The breakdown
      provisions the data stores but no item owns backup, restore rehearsal,
      or failover runbooks. Provisioning a data store is not the same as
      being able to recover it.
    spec_reference: "N5"
    breakdown_impact: >
      A new item is needed, or the landing-zone item's scope must state that
      recovery is inside it.
    status: addressed
```
