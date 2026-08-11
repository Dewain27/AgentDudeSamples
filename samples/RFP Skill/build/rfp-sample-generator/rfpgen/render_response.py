"""Render a Scenario as an RFP *response* — the vendor's proposal.

The response is written to reply directly to the request built from the same
Scenario, so the two documents stay consistent.
"""

import random

from . import templates as t
from .company import TEAM_NAMES, TEAM_ROLES, VENDOR
from .scenario import Scenario


def _phases(duration_months: int):
    """Split the timeline into named phases summing to the total duration."""
    # Proportional split, then adjust so months sum exactly.
    weights = [
        ("Discovery & Design", 0.20),
        ("Foundation & Integrations", 0.25),
        ("Core Build", 0.30),
        ("Testing & Hardening", 0.15),
        ("Launch & Stabilization", 0.10),
    ]
    months = [max(1, round(duration_months * w)) for _, w in weights]
    # Reconcile rounding drift against the core build phase.
    drift = duration_months - sum(months)
    months[2] = max(1, months[2] + drift)
    return list(zip((n for n, _ in weights), months))


def _price_table(rng: random.Random, s: Scenario):
    """Build an itemized price table that lands inside the stated budget."""
    # Aim near the middle of the client's stated range.
    target = int((s.budget_low + s.budget_high) / 2)
    target = int(target * rng.uniform(0.92, 1.02))

    # Percent allocation across line items (sums to 1.0).
    allocation = [
        ("Discovery & solution design", 0.14),
        ("Development & configuration", 0.40),
        ("Integrations", 0.16),
        ("Data migration", 0.08),
        ("Quality assurance & security testing", 0.10),
        ("Training, documentation & launch", 0.07),
        ("Project management", 0.05),
    ]
    rows = []
    running = 0
    for i, (label, pct) in enumerate(allocation):
        if i == len(allocation) - 1:
            amount = target - running  # last line absorbs rounding
        else:
            amount = int(round(target * pct / 1000.0)) * 1000
            running += amount
        rows.append((label, amount))
    total = sum(a for _, a in rows)
    return rows, total


def _team(rng: random.Random):
    names = rng.sample(TEAM_NAMES, len(TEAM_ROLES))
    return [
        (name, role, note)
        for name, (role, note) in zip(names, TEAM_ROLES)
    ]


def render(s: Scenario, rng: random.Random = None) -> str:
    rng = rng or random.Random(s.rfp_id)

    phases = _phases(s.duration_months)
    price_rows, price_total = _price_table(rng, s)
    team = _team(rng)

    # The person who signs the cover letter is whoever the roster assigned as
    # Engagement Director, so the signature matches the team table.
    signer_name = next(
        (name for name, role, _ in team if role == "Engagement Director"),
        team[0][0],
    )

    # Past performance drawn from the vendor's case studies for this industry,
    # falling back to a general set.
    case_studies = VENDOR.case_studies.get(
        s.industry,
        VENDOR.case_studies.get("healthcare"),
    )

    understanding = t.bullet_list(
        f"You want to {d}." for d in s.drivers
    )
    functional_response = t.bullet_list(
        f"**{req.split(' with ')[0].split(',')[0]}** — delivered in "
        f"{'Phase 2' if i % 2 else 'Phase 3'}."
        for i, req in enumerate(s.functional_reqs)
    )
    integration_response = t.bullet_list(
        f"Integration with {i} via documented, versioned APIs."
        for i in s.integrations
    )
    compliance = ", ".join(s.compliance)

    phase_rows = []
    cursor = 1
    for name, mo in phases:
        span = f"Month {cursor}" if mo == 1 else f"Months {cursor}–{cursor + mo - 1}"
        phase_rows.append(f"| {name} | {span} |")
        cursor += mo
    phase_table = "\n".join(phase_rows)

    price_table = "\n".join(
        f"| {label} | {t.money(amount)} |" for label, amount in price_rows
    )

    team_table = "\n".join(
        f"| {name} | {role} | {note} |" for name, role, note in team
    )

    case_study_list = t.bullet_list(case_studies)

    differentiators = t.bullet_list(VENDOR.differentiators)
    capabilities = t.bullet_list(VENDOR.capabilities)

    return f"""{t.DISCLAIMER}

# Proposal in Response to {s.rfp_id}
## {s.project_label}

**Submitted by {VENDOR.name}**
Prepared for **{s.client_name}**

| | |
| --- | --- |
| **RFP reference** | {s.rfp_id} |
| **Submitted** | {t.date(s.proposals_due)} |
| **Vendor** | {VENDOR.name} |
| **Contact** | {VENDOR.email} · {VENDOR.phone} |
| **Proposed fee** | {t.money(price_total)} (fixed price) |
| **Proposed duration** | {s.duration_months} months |

---

## 1. Cover letter

{t.date(s.proposals_due)}

{s.contact_name}
{s.contact_title}
{s.client_name}

Dear {s.contact_name},

Thank you for the opportunity to respond to {s.rfp_id} for the
**{s.project_label}**. {VENDOR.name} builds custom software for organizations
like {s.client_name}, and this engagement is squarely in the work we do best.

We have read your requirements carefully and structured this proposal to
address each one directly. Our approach begins with a short, fixed-scope
discovery sprint so that our plan and pricing reflect a shared understanding of
the work — no surprises later. The fixed price quoted in this proposal is
**{t.money(price_total)}**, within your stated budget.

We would be glad to walk your team through this proposal in a demonstration or
interview. This proposal is valid for 90 days.

Sincerely,

**{signer_name}**
Engagement Director, {VENDOR.name}
{VENDOR.email} · {VENDOR.phone}

## 2. Executive summary

{VENDOR.name} proposes to design, build, integrate, and launch
**{s.project_label}** for {s.client_name} — {s.project_summary}.

We will deliver the solution in **{s.duration_months} months** for a **fixed
fee of {t.money(price_total)}**, meeting your **{compliance}** requirements and
the functional, technical, and security requirements set out in {s.rfp_id}.

Our proposal is built around three commitments:

- **Deliver measurable outcomes**, not just software — tied to the success
  measures in your RFP.
- **Integrate cleanly** with your existing systems using documented APIs.
- **Leave you self-sufficient** — full source code, infrastructure-as-code, and
  documentation are yours, with a defined post-launch support plan.

## 3. Understanding of your needs

We understand that {s.client_name}, {s.client_descriptor}, is pursuing this
initiative to achieve the following:

{understanding}

The requirements in your RFP point to a solution that is easy for your people
to adopt, connects to the systems you already run, and holds up to your
**{compliance}** obligations. Our proposed solution is organized around exactly
those priorities.

## 4. Proposed solution

We propose a cloud-hosted, {compliance}-aligned solution delivering the
capabilities you requested. Key functional requirements map to our delivery
plan as follows:

{functional_response}

### Integrations

{integration_response}

### Why this approach

{VENDOR.name}'s relevant capabilities for this engagement:

{capabilities}

## 5. Technical approach

- **Architecture.** Cloud-native and modular, deployed with
  infrastructure-as-code so environments are reproducible and auditable.
- **Security by default.** Encryption in transit and at rest, SSO, role-based
  access control, and audit logging — reviewed every sprint, not bolted on
  before launch. The solution is designed to meet your **{compliance}**
  requirements.
- **Integration.** Documented, versioned REST APIs for each system in scope,
  with a clear contract and error handling.
- **Quality.** Automated testing in CI, code review on every change, and a
  security review before release.
- **Accessibility.** Designed and tested to WCAG 2.1 AA.

Representative technologies we expect to use: {", ".join(VENDOR.tech_stack)}.
Final choices are confirmed during discovery.

## 6. Project plan and timeline

We will deliver in five phases over **{s.duration_months} months**:

| Phase | Timeline |
| --- | --- |
{phase_table}

Each phase ends with a working, demonstrable increment and a stakeholder
review. You see progress continuously rather than waiting for a big-bang
launch.

**Key milestones**

1. Discovery sign-off — agreed scope, design, and detailed plan.
2. Integrations proven end-to-end in a test environment.
3. Feature-complete build ready for user-acceptance testing.
4. Security review and go-live readiness sign-off.
5. Production launch and stabilization.

## 7. Project team

We staff dedicated delivery pods — the people who scope your project are the
people who build it. Proposed key personnel:

| Name | Role | Focus |
| --- | --- | --- |
{team_table}

Résumés for named personnel are available in the appendix on request.

## 8. Relevant experience and past performance

{VENDOR.name} has delivered more than 300 engagements since {VENDOR.founded}.
Representative work relevant to {s.client_name}:

{case_study_list}

Three references for comparable engagements will be provided on request, in
accordance with your RFP.

## 9. Pricing

We propose a **fixed fee of {t.money(price_total)}**, itemized below. This
figure is within the estimated budget of
{t.money_range(s.budget_low, s.budget_high)} stated in {s.rfp_id}.

| Line item | Amount |
| --- | ---: |
{price_table}
| **Total (fixed price)** | **{t.money(price_total)}** |

**Assumptions**

- Pricing assumes the scope and integrations described in {s.rfp_id}.
- The discovery sprint confirms detailed requirements; material changes are
  handled through a lightweight change-control process.
- {s.client_name} provides timely access to stakeholders, systems, and test
  data.
- First-year post-launch support is quoted separately as an optional care plan.

## 10. Why {VENDOR.name}

{differentiators}

**Certifications:** {", ".join(VENDOR.certifications)}.

## 11. Assumptions, exclusions, and risks

- **Assumptions:** access to source/target systems for integrations; a
  designated product owner from {s.client_name}; test environments available at
  project start.
- **Exclusions:** third-party license fees, ongoing hosting costs, and
  hardware are not included in the fixed fee.
- **Risks & mitigations:** integration unknowns are surfaced early in
  discovery; scope is managed through change control; a named support lead owns
  post-launch stability.

---

*Prepared for demonstration by the RFP Sample Generator. {VENDOR.name} and all
details herein are fictional.*
"""
