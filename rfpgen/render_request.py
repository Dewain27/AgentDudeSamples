"""Render a Scenario as an RFP *request* — the buyer's document."""

from . import templates as t
from .company import VENDOR
from .scenario import Scenario


def render(s: Scenario) -> str:
    weighted = "\n".join(
        f"| {name} | {weight} |" for name, weight in s.evaluation
    )

    functional = t.numbered_list(s.functional_reqs)
    technical = t.bullet_list(s.technical_reqs)
    security = t.bullet_list(s.security_reqs)
    integrations = t.bullet_list(f"Integration with {i}." for i in s.integrations)
    compliance = ", ".join(s.compliance)
    drivers = t.bullet_list(s.drivers)
    success = t.bullet_list(s.success_measures)

    return f"""{t.DISCLAIMER}

# Request for Proposal — {s.project_label}

**{s.client_name}**

| | |
| --- | --- |
| **RFP number** | {s.rfp_id} |
| **Issued** | {t.date(s.issued_date)} |
| **Questions due** | {t.date(s.questions_due)} |
| **Proposals due** | {t.date(s.proposals_due)} by 5:00 PM local time |
| **Anticipated award** | {t.date(s.award_date)} |
| **Anticipated start** | {t.date(s.start_date)} |
| **Estimated budget** | {t.money_range(s.budget_low, s.budget_high)} |

---

## 1. Introduction

{s.client_name} ({s.client_descriptor}, based in {s.client_location}) is
seeking proposals from qualified software firms to deliver
**{s.project_label}** — {s.project_summary}.

This Request for Proposal (RFP) describes our needs, the requirements a
solution must meet, and the process for submitting a proposal. We invite
experienced vendors to respond with a proposal that demonstrates their
approach, qualifications, and pricing.

## 2. Background and objectives

{s.client_name} is undertaking this initiative to:

{drivers}

The selected vendor will partner with our team to design, build, and launch a
solution that meets the requirements below and delivers measurable results.

## 3. Scope of work

The vendor will be responsible for the full delivery lifecycle, including:

- Discovery and requirements refinement with our stakeholders.
- Solution and technical design.
- Development, configuration, and integration.
- Quality assurance and user-acceptance testing.
- Data migration from existing systems, where applicable.
- Training, documentation, and knowledge transfer.
- Deployment and post-launch support.

## 4. Functional requirements

The solution must provide, at minimum:

{functional}

## 5. Integration requirements

The solution must integrate with our existing systems, including:

{integrations}

Vendors should describe their approach to each integration and any assumptions
made.

## 6. Technical requirements

{technical}

## 7. Security and compliance requirements

The solution must adhere to **{compliance}** and meet the following security
requirements:

{security}

## 8. Success measures

We will consider this engagement successful if it achieves:

{success}

## 9. Proposal requirements

Proposals must include the following, in order:

1. **Cover letter** signed by an authorized representative.
2. **Executive summary** of the proposed solution.
3. **Understanding of our needs** and objectives.
4. **Proposed solution** and technical approach.
5. **Project plan**, timeline, and key milestones.
6. **Team** — roles, named key personnel, and relevant qualifications.
7. **Relevant experience** and at least three references for similar work.
8. **Pricing** — itemized, with assumptions clearly stated.
9. **Assumptions, exclusions, and risks.**

Proposals should not exceed 30 pages, excluding appendices.

## 10. Evaluation criteria

Proposals will be evaluated on a 100-point scale using the following weighting:

| Criterion | Weight |
| --- | ---: |
{weighted}

{s.client_name} reserves the right to request clarifications, interviews, or
product demonstrations from finalists.

## 11. Submission instructions

- Submit proposals electronically as a single PDF.
- Direct all questions in writing to the contact below by
  **{t.date(s.questions_due)}**. Answers will be shared with all vendors.
- Proposals are due no later than **{t.date(s.proposals_due)} at 5:00 PM local
  time**. Late submissions will not be considered.

## 12. Contact

| | |
| --- | --- |
| **Primary contact** | {s.contact_name} |
| **Title** | {s.contact_title} |
| **Organization** | {s.client_name} |
| **Reference** | {s.rfp_id} |

## 13. Terms and conditions

- This RFP does not commit {s.client_name} to award a contract or to pay any
  costs incurred in preparing a proposal.
- {s.client_name} may accept or reject any or all proposals, in whole or in
  part, and may cancel this RFP at any time.
- The selected vendor will be required to enter into a written agreement
  consistent with the terms outlined in this RFP.

---

*Prepared for demonstration by the RFP Sample Generator. Sample vendor for
reference: {VENDOR.name}.*
"""
