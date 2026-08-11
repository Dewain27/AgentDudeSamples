"""Render an offering's sample RFP *request* (the buyer's document)."""

from .catalog_data import VENDOR
from . import models

DISCLAIMER = (
    "> **Sample document.** This RFP is fictional and was generated for "
    "demonstration purposes. All organizations, names, figures, and details are "
    "invented and do not represent any real entity, price, or agreement."
)


def _bullets(items):
    return "\n".join(f"- {i}" for i in items)


def _numbered(items):
    return "\n".join(f"{n}. {i}" for n, i in enumerate(items, 1))


def _date(d):
    return d.strftime("%B %d, %Y")


def _money(v):
    return f"${v:,}"


def render(offering: dict) -> str:
    ctx = models.derive_context(offering)
    line = models.product_line(offering["line"])

    functional = _numbered(offering["typical_requirements"])
    integrations = _bullets(f"Integration with {i}." for i in offering["integrations"])
    compliance = ", ".join(offering["compliance"])
    capabilities = _bullets(offering["capabilities"])
    success = _bullets(offering["success_metrics"])
    weighted = "\n".join(f"| {name} | {w} |" for name, w in ctx["evaluation"])

    return f"""{DISCLAIMER}

# Request for Proposal — {offering['name']}

**{ctx['buyer_name']}**

| | |
| --- | --- |
| **RFP number** | {ctx['rfp_id']} |
| **Product category** | {line['name']} |
| **Issued** | {_date(ctx['issued_date'])} |
| **Questions due** | {_date(ctx['questions_due'])} |
| **Proposals due** | {_date(ctx['proposals_due'])} by 5:00 PM local time |
| **Anticipated award** | {_date(ctx['award_date'])} |
| **Anticipated start** | {_date(ctx['start_date'])} |
| **Estimated budget** | {_money(offering['price_low'])} – {_money(offering['price_high'])} |

---

## 1. Introduction

{ctx['buyer_name']} ({ctx['buyer_descriptor']}, based in {ctx['buyer_location']})
is seeking proposals from qualified software firms to deliver **{offering['name']}**
— {offering['summary']}.

This Request for Proposal (RFP) describes our needs, the requirements a solution
must meet, and the process for submitting a proposal.

## 2. Scope of work

The vendor will be responsible for the full delivery lifecycle, including
discovery, design, development and configuration, integration, quality
assurance, data migration where applicable, training and documentation, and
deployment with post-launch support.

The capabilities we expect the solution to provide include:

{capabilities}

## 3. Requirements

At minimum, the solution must:

{functional}

## 4. Integration requirements

The solution must integrate with our existing systems, including:

{integrations}

Vendors should describe their approach to each integration and any assumptions.

## 5. Security and compliance requirements

The solution must adhere to **{compliance}**, and vendors must describe:

- How data is encrypted in transit and at rest.
- How access is controlled (authentication, single sign-on, and roles).
- Their approach to security testing and vulnerability management.
- How the solution meets the accessibility and compliance frameworks above.

## 6. Success measures

We will consider this engagement successful if it achieves:

{success}

## 7. Proposal requirements

Proposals must include, in order: (1) a cover letter, (2) an executive summary,
(3) your understanding of our needs, (4) the proposed solution and technical
approach, (5) a project plan and timeline, (6) the project team and key
personnel, (7) relevant experience and at least three references, (8) itemized
pricing with assumptions, and (9) assumptions, exclusions, and risks.

## 8. Evaluation criteria

Proposals will be scored on a 100-point scale:

| Criterion | Weight |
| --- | ---: |
{weighted}

## 9. Submission instructions

- Submit proposals electronically as a single PDF.
- Direct written questions to the contact below by **{_date(ctx['questions_due'])}**.
- Proposals are due by **{_date(ctx['proposals_due'])} at 5:00 PM local time**.
  Late submissions will not be considered.

## 10. Contact

| | |
| --- | --- |
| **Primary contact** | {ctx['contact_name']} |
| **Title** | {ctx['contact_title']} |
| **Organization** | {ctx['buyer_name']} |
| **Reference** | {ctx['rfp_id']} |

---

*Prepared for demonstration by the RFP Automation Kit. This RFP requests an
offering comparable to {VENDOR['name']}'s {offering['name']}.*
"""
