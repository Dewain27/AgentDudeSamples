"""Builds a single coherent RFP scenario.

A Scenario bundles everything the request and the response both need: the
client, the project, the selected requirements, budget, and key dates. Because
both documents render from the *same* Scenario, a matched pair always lines up.
"""

import datetime as _dt
import random
import uuid
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from . import data


@dataclass
class Scenario:
    rfp_id: str
    issued_date: _dt.date
    questions_due: _dt.date
    proposals_due: _dt.date
    award_date: _dt.date
    start_date: _dt.date

    industry: str
    client_name: str
    client_descriptor: str
    client_location: str

    project_key: str
    project_label: str
    project_summary: str
    drivers: List[str]

    functional_reqs: List[str]
    technical_reqs: List[str]
    security_reqs: List[str]
    integrations: List[str]
    compliance: List[str]
    success_measures: List[str]

    org_size: str
    budget_low: int
    budget_high: int
    duration_months: int

    contact_name: str
    contact_title: str

    evaluation: List[Tuple[str, int]] = field(default_factory=list)

    def slug(self) -> str:
        """Short filesystem-friendly identifier for this scenario."""
        client = _slugify(self.client_name)
        proj = _slugify(self.project_key)
        return f"{client}_{proj}_{self.rfp_id[-4:].lower()}"


def _slugify(text: str) -> str:
    out = []
    for ch in text.lower():
        if ch.isalnum():
            out.append(ch)
        elif ch in " -_":
            out.append("-")
    slug = "".join(out)
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug.strip("-")


_CONTACT_NAMES = [
    ("Karen Alvarez", "Director of Information Technology"),
    ("James Whitfield", "Chief Operating Officer"),
    ("Denise Park", "Procurement Manager"),
    ("Robert Chen", "VP of Operations"),
    ("Michelle Torres", "Director of Digital Services"),
    ("Andrew Boyd", "Chief Information Officer"),
    ("Latasha Green", "Director of Administration"),
]


def _pick_sample(rng: random.Random, seq, k: int):
    """Pick k items (or all, if fewer) preserving list order."""
    if k >= len(seq):
        return list(seq)
    idx = sorted(rng.sample(range(len(seq)), k))
    return [seq[i] for i in idx]


def build_scenario(
    rng: random.Random,
    industry: Optional[str] = None,
    project_key: Optional[str] = None,
) -> Scenario:
    """Construct one internally consistent Scenario.

    industry / project_key may be forced; otherwise they're chosen at random
    from compatible options.
    """
    # --- choose project first (it constrains valid industries) -------------
    if project_key:
        if project_key not in data.PROJECTS:
            raise ValueError(f"Unknown project '{project_key}'. Options: {', '.join(sorted(data.PROJECTS))}")
        proj = data.PROJECTS[project_key]
        valid_industries = proj["industries"]
        if industry and industry not in valid_industries:
            raise ValueError(
                f"Project '{project_key}' is not offered for industry "
                f"'{industry}'. Valid: {', '.join(valid_industries)}"
            )
        industry = industry or rng.choice(valid_industries)
    else:
        if industry:
            if industry not in data.CLIENTS:
                raise ValueError(f"Unknown industry '{industry}'. Options: {', '.join(sorted(data.CLIENTS))}")
            candidates = [k for k, p in data.PROJECTS.items() if industry in p["industries"]]
        else:
            industry = rng.choice(list(data.CLIENTS))
            candidates = [k for k, p in data.PROJECTS.items() if industry in p["industries"]]
        project_key = rng.choice(candidates)
        proj = data.PROJECTS[project_key]

    client = rng.choice(data.CLIENTS[industry])

    # --- size, budget, duration -------------------------------------------
    org_size = rng.choice(data.ORG_SIZES)
    b_low, b_high = data.BUDGET_RANGES[org_size]
    # Round to a tidy figure.
    budget_low = _round_money(rng.randint(b_low, int(b_low * 1.15)))
    budget_high = _round_money(rng.randint(int(b_high * 0.85), b_high))
    d_low, d_high = data.DURATION_MONTHS[org_size]
    duration = rng.randint(d_low, d_high)

    # --- requirements ------------------------------------------------------
    technical = _pick_sample(rng, data.TECHNICAL_REQUIREMENTS, rng.randint(5, 7))
    security = _pick_sample(rng, data.SECURITY_REQUIREMENTS, rng.randint(4, 6))

    # --- dates -------------------------------------------------------------
    issued = _dt.date(2026, rng.randint(1, 9), rng.randint(1, 28))
    questions_due = issued + _dt.timedelta(days=10)
    proposals_due = issued + _dt.timedelta(days=30)
    award = proposals_due + _dt.timedelta(days=21)
    start = award + _dt.timedelta(days=14)

    contact_name, contact_title = rng.choice(_CONTACT_NAMES)
    rfp_id = f"RFP-2026-{uuid.UUID(int=rng.getrandbits(128)).hex[:6].upper()}"

    return Scenario(
        rfp_id=rfp_id,
        issued_date=issued,
        questions_due=questions_due,
        proposals_due=proposals_due,
        award_date=award,
        start_date=start,
        industry=industry,
        client_name=client["name"],
        client_descriptor=client["descriptor"],
        client_location=client["location"],
        project_key=project_key,
        project_label=proj["label"],
        project_summary=proj["summary"],
        drivers=list(proj["drivers"]),
        functional_reqs=list(proj["functional"]),
        technical_reqs=technical,
        security_reqs=security,
        integrations=list(proj["integrations"]),
        compliance=list(proj["compliance"]),
        success_measures=list(proj["success"]),
        org_size=org_size,
        budget_low=budget_low,
        budget_high=budget_high,
        duration_months=duration,
        contact_name=contact_name,
        contact_title=contact_title,
        evaluation=list(data.EVALUATION_CRITERIA),
    )


def _round_money(value: int) -> int:
    """Round to the nearest $5,000 for tidy figures."""
    return int(round(value / 5000.0)) * 5000
