# Research review

**Author:** Dewain Robinson

| | |
| --- | --- |
| Reviewed | 2026-09-04 |
| Specification | `scenarios/kestrel-financial/specification.md` |
| Breakdown | `scenarios/kestrel-financial/kestrel-claude-code-manifest.yaml` |
| Mode | offline |

## What this review is, and is not

It reports **structure and questions, never numbers.** It names work the breakdown
appears to be missing, questions a size without proposing one, and points at
unknowns nobody declared. Every size stays a human's to set.

It does **not** validate the specification against reality. It checks the breakdown
against the specification. Whether that specification describes a system which
will work is a different question, asked elsewhere.

## Summary

**7 findings, of which 7 would change the breakdown.**

| Severity | Findings |
| --- | ---: |
| High | 3 |
| Medium | 4 |

## Findings

### F-001 — No work item covers backup, restore, or disaster recovery

*Missing component · high severity*

N5 states recovery point and recovery time objectives for the platform. The breakdown provisions Cosmos, Storage and the landing zone, but no item owns backup configuration, restore rehearsal, failover runbooks, or the drill that would demonstrate the objectives are met. Provisioning a data store is not the same as being able to recover it.

**Where:** N5, and the Azure platform items in the breakdown

**What it would change:** A new item is needed, or the landing-zone item's scope must state that recovery is inside it.

**Status:** addressed

### F-002 — Nothing covers load or performance testing

*Missing component · high severity*

N1 sets a first-token latency target and N6 sets a concurrency target for advisor sessions. No item covers building a load model, scripting the scenarios, running them, or tuning against the result. Evaluation cases test whether the agent answers correctly, which is a different question from whether it answers under load.

**Where:** N1, N6, and section 11 on the evaluation strategy

**What it would change:** A new item, distinct from the evaluation cases already declared.

**Status:** addressed

### F-003 — Customer-managed key setup is unowned

*Missing component · high severity*

N9 requires encryption at rest under customer-managed keys. Key Vault appears in the Azure consumption list, but provisioning a vault is not the same as wiring CMK into Cosmos and Storage, defining rotation, and verifying enforcement. The item that would own that work does not exist.

**Where:** N9, and the Cosmos and Storage platform items

**What it would change:** A new item, applied per environment rather than authored once.

**Status:** addressed

### F-004 — Region-pinned inference is required but nothing configures it

*Missing component · medium severity*

S10 and N8 require inference to stay within a named region for data residency. No item covers configuring the pinning, preventing cross-region egress, or producing the evidence a compliance reviewer would ask for.

**Where:** S10, N8

**What it would change:** A new item, or an explicit statement that the landing-zone item includes residency enforcement and its evidence.

**Status:** addressed

### F-005 — Segregation of duties may or may not sit inside the CI/CD item

*Scope question · medium severity*

S9 requires deploy approvals to be separate from authoring. The CI/CD and ALM item plausibly contains that work, but nothing says so. If it does, the item is carrying a control it does not name; if it does not, the control is unowned. Either way a reader cannot tell which.

**Where:** S9, and the CI/CD and ALM item

**What it would change:** Either the CI/CD item's scope statement names the control, or a separate item does.

### F-006 — KYC screening latency interacts with the agent latency target

*Unstated unknown · medium severity*

The integration section notes that KYC screening latency degrades under load, while N1 sets a first-token latency target for the agent. No item declares an unknown for how a slow downstream screening call is handled inside a latency-bound conversation. Whether the agent waits, streams around it, or degrades is undecided.

**Where:** the KYC integration entry, N1

**What it would change:** The integration item should carry an additional declared unknown, which widens its range.

### F-007 — The client portal covers five modules as a single item

*Specification too thin to size · medium severity*

P1 through P5 describe authentication with step-up, account views, documents, secure messaging and notifications. The breakdown carries one item for the whole portal. P4's routing model is not defined in the specification, so that part cannot be sized with confidence even by someone who knows the rest well.

**Where:** P1-P5, and the client self-service portal item

**What it would change:** Either split the item along the module boundaries, or record that P4 is undefined so the range widens to reflect it.

## What to do with this

Each finding is a question for a human, not an instruction. Decide whether it
changes the breakdown, then record the outcome in the manifest so the estimate
says the breakdown was challenged:

```yaml
research_review:
  reviewed: "2026-09-04"
  findings_total: 7
  findings_addressed: <how many changed the breakdown>
  findings_accepted_as_is: <how many you knowingly accepted>
```

The estimator records that block as **declared**. It does not verify the review's
quality, only that one happened — because "reviewed, three findings knowingly
accepted" is a materially different signal from "never reviewed".
