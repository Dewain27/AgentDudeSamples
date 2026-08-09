"""Render an offering's sample RFP *response* (the vendor's proposal).

The response is assembled from the offering's own `snippets` plus shared blocks
in the response library — the same assembly a downstream automation would
perform. This keeps the sample and the automation output structurally identical.
"""

from .catalog_data import VENDOR
from . import models

DISCLAIMER = (
    "> **Sample document.** This proposal is fictional and was generated for "
    "demonstration purposes. The vendor, prices, team, and all details are "
    "invented."
)

TEAM = [
    ("Priya Raman", "Engagement Director", "single point of accountability for the program"),
    ("Marcus Bell", "Solution Architect", "owns the architecture and integration approach"),
    ("Elena Duarte", "Lead Engineer", "owns technical delivery and code quality"),
    ("Sofia Nguyen", "UX Designer", "runs user research and accessible interface design"),
    ("David Okafor", "Project Manager", "your point of contact for schedule, scope, and status"),
    ("Grace Kim", "QA & Security Lead", "owns test strategy and the pre-release security review"),
]


def _bullets(items):
    return "\n".join(f"- {i}" for i in items)


def _date(d):
    return d.strftime("%B %d, %Y")


def _money(v):
    return f"${v:,}"


def _round5k(v):
    return int(round(v / 5000.0)) * 5000


def _phases(months: int):
    weights = [
        ("Discovery & Design", 0.20),
        ("Foundation & Integrations", 0.25),
        ("Core Build", 0.30),
        ("Testing & Hardening", 0.15),
        ("Launch & Stabilization", 0.10),
    ]
    split = [max(1, round(months * w)) for _, w in weights]
    split[2] = max(1, split[2] + (months - sum(split)))
    rows, cursor = [], 1
    for (name, _), mo in zip(weights, split):
        span = f"Month {cursor}" if mo == 1 else f"Months {cursor}–{cursor + mo - 1}"
        rows.append(f"| {name} | {span} |")
        cursor += mo
    return "\n".join(rows)


def _price_table(offering: dict):
    target = _round5k((offering["price_low"] + offering["price_high"]) / 2)
    allocation = [
        ("Discovery & solution design", 0.14),
        ("Development & configuration", 0.42),
        ("Integrations", 0.16),
        ("Data migration & setup", 0.08),
        ("Quality assurance & security testing", 0.10),
        ("Training, documentation & launch", 0.06),
        ("Project management", 0.04),
    ]
    rows, running = [], 0
    for i, (label, pct) in enumerate(allocation):
        amount = (target - running) if i == len(allocation) - 1 else _round5k(target * pct)
        running += amount if i < len(allocation) - 1 else 0
        rows.append((label, amount))
    total = sum(a for _, a in rows)
    table = "\n".join(f"| {label} | {_money(a)} |" for label, a in rows)
    return table, total


def render(offering: dict) -> str:
    ctx = models.derive_context(offering)
    line = models.product_line(offering["line"])
    lib = models.library_block

    price_table, price_total = _price_table(offering)
    phase_table = _phases(offering["timeline_months"])
    team_table = "\n".join(f"| {n} | {r} | {note} |" for n, r, note in TEAM)
    compliance = ", ".join(offering["compliance"])

    understanding = offering["snippets"]["understanding"]
    solution = offering["snippets"]["solution"]
    capabilities = _bullets(offering["capabilities"])
    differentiators = _bullets(offering["differentiators"])
    integrations = _bullets(f"Integration with {i} via documented, versioned APIs." for i in offering["integrations"])

    return f"""{DISCLAIMER}

# Proposal in Response to {ctx['rfp_id']}
## {offering['name']}

**Submitted by {VENDOR['name']}** — {line['name']}
Prepared for **{ctx['buyer_name']}**

| | |
| --- | --- |
| **RFP reference** | {ctx['rfp_id']} |
| **Submitted** | {_date(ctx['proposals_due'])} |
| **Vendor** | {VENDOR['name']} |
| **Contact** | {VENDOR['email']} · {VENDOR['phone']} |
| **Proposed fee** | {_money(price_total)} (fixed price) |
| **Proposed duration** | {offering['timeline_months']} months |

---

## 1. Cover letter

{_date(ctx['proposals_due'])}

{ctx['contact_name']}, {ctx['contact_title']}
{ctx['buyer_name']}

Dear {ctx['contact_name']},

Thank you for the opportunity to respond to {ctx['rfp_id']} for
**{offering['name']}**. {lib('company_overview')['answer']}

We have structured this proposal to address each of your requirements directly.
The fixed price quoted is **{_money(price_total)}**, within your stated budget.
This proposal is valid for 90 days.

Sincerely,

**Priya Raman**
Engagement Director, {VENDOR['name']}
{VENDOR['email']} · {VENDOR['phone']}

## 2. Executive summary

{VENDOR['name']} proposes to deliver **{offering['name']}** for {ctx['buyer_name']}
— {offering['summary']}. We will deliver in **{offering['timeline_months']} months**
for a **fixed fee of {_money(price_total)}**, meeting your **{compliance}**
requirements.

## 3. Understanding of your needs

{understanding}

## 4. Proposed solution

{solution}

The solution provides the following capabilities:

{capabilities}

### Integrations

{integrations}

## 5. Technical approach

**Methodology.** {lib('methodology')['answer']}

**Hosting.** {lib('hosting')['answer']}

**Security.** {lib('security')['answer']}

**Authentication.** {lib('sso')['answer']}

**Integration.** {lib('integration_approach')['answer']}

**Quality assurance.** {lib('quality_assurance')['answer']}

**Accessibility.** {lib('accessibility')['answer']}

## 6. Project plan and timeline

We will deliver in five phases over **{offering['timeline_months']} months**,
each ending with a working, demonstrable increment and a stakeholder review:

| Phase | Timeline |
| --- | --- |
{phase_table}

## 7. Project team

We staff dedicated delivery pods — the people who scope your project are the
people who build it. Proposed key personnel:

| Name | Role | Focus |
| --- | --- | --- |
{team_table}

## 8. Relevant experience

{lib('company_overview')['answer']} We will provide at least three references
from comparable **{offering['name']}** engagements, matched by industry and
project type, on request.

## 9. Pricing

We propose a **fixed fee of {_money(price_total)}** ({offering['pricing_model']}),
within your estimated budget of {_money(offering['price_low'])} –
{_money(offering['price_high'])}.

| Line item | Amount |
| --- | ---: |
{price_table}
| **Total (fixed price)** | **{_money(price_total)}** |

**Pricing approach.** {lib('pricing_approach')['answer']}

## 10. Support and service levels

{lib('support_sla')['answer']}

## 11. Why {VENDOR['name']}

{lib('why_aventra')['answer']}

Specific to this offering:

{differentiators}

**Certifications:** {", ".join(VENDOR['certifications'])}.

## 12. Assumptions, exclusions, and risks

{lib('assumptions')['answer']}

---

*Prepared for demonstration by the RFP Automation Kit. {VENDOR['name']} and all
details herein are fictional.*
"""
