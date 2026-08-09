"""Catalog access helpers and deterministic buyer/scenario derivation.

Rendering must be reproducible so committed samples stay stable. Instead of a
random generator, we derive each offering's fictional buyer and key dates
deterministically from the offering id.
"""

import datetime as _dt
import hashlib

from .catalog_data import OFFERINGS, PRODUCT_LINES, RESPONSE_LIBRARY, VENDOR

# ---------------------------------------------------------------------------
# Fictional buyer organizations by industry. One is chosen per offering,
# deterministically, so a given offering always renders the same buyer.
# ---------------------------------------------------------------------------

BUYERS = {
    "healthcare": [
        ("Riverside Health Partners", "a regional network of outpatient clinics", "Ohio"),
        ("Cascade Family Medicine", "a multi-specialty physician group", "Oregon"),
    ],
    "government": [
        ("Franklin County", "a county government of roughly 280,000 residents", "Pennsylvania"),
        ("City of Lakemont", "a mid-size municipal government", "Michigan"),
    ],
    "education": [
        ("Northgate Community College District", "a two-campus community college district", "California"),
        ("Meridian Unified School District", "a K-12 district serving 24,000 students", "Arizona"),
    ],
    "financial services": [
        ("Summit Ridge Credit Union", "a member-owned credit union", "Utah"),
        ("Harbor Point Bank", "a regional community bank", "Massachusetts"),
    ],
    "manufacturing": [
        ("Ironwood Manufacturing", "a precision metal-components manufacturer", "Indiana"),
        ("Pacific Coast Foods", "a food-processing company with four plants", "Washington"),
    ],
    "retail": [
        ("Trailhead Outfitters", "a specialty outdoor-gear retailer with 90 stores", "Colorado"),
        ("Maple & Main Home Goods", "a home-furnishings retail chain", "Minnesota"),
    ],
    "nonprofit": [
        ("Open Horizons Foundation", "a national education nonprofit", "New York"),
        ("Community Bridges Alliance", "a social-services nonprofit with 60 chapters", "Florida"),
    ],
}

CONTACTS = [
    ("Karen Alvarez", "Director of Information Technology"),
    ("James Whitfield", "Chief Operating Officer"),
    ("Denise Park", "Procurement Manager"),
    ("Robert Chen", "VP of Operations"),
    ("Michelle Torres", "Director of Digital Services"),
    ("Andrew Boyd", "Chief Information Officer"),
]

EVALUATION_CRITERIA = [
    ("Technical approach and solution fit", 30),
    ("Relevant experience and past performance", 20),
    ("Project team qualifications", 15),
    ("Cost and value", 20),
    ("Project plan and timeline", 10),
    ("References", 5),
]


def _seed(offering_id: str) -> int:
    """Stable integer seed derived from the offering id."""
    digest = hashlib.sha256(offering_id.encode("utf-8")).hexdigest()
    return int(digest[:8], 16)


def offering_by_id(offering_id: str) -> dict:
    for o in OFFERINGS:
        if o["id"] == offering_id:
            return o
    raise KeyError(f"Unknown offering '{offering_id}'. Options: {', '.join(o['id'] for o in OFFERINGS)}")


def all_offerings():
    return list(OFFERINGS)


def product_line(line_key: str) -> dict:
    return PRODUCT_LINES[line_key]


def derive_context(offering: dict) -> dict:
    """Build the deterministic buyer + dates + RFP metadata for an offering."""
    seed = _seed(offering["id"])
    industry = offering["target_industries"][0]
    buyers = BUYERS.get(industry, BUYERS["government"])
    buyer = buyers[seed % len(buyers)]
    contact = CONTACTS[seed % len(CONTACTS)]

    # Deterministic issue date within 2026.
    month = (seed % 9) + 1
    day = (seed % 27) + 1
    issued = _dt.date(2026, month, day)
    questions_due = issued + _dt.timedelta(days=10)
    proposals_due = issued + _dt.timedelta(days=30)
    award = proposals_due + _dt.timedelta(days=21)
    start = award + _dt.timedelta(days=14)

    rfp_id = f"RFP-2026-{offering['id'][:4].upper()}{seed % 1000:03d}"

    return {
        "rfp_id": rfp_id,
        "industry": industry,
        "buyer_name": buyer[0],
        "buyer_descriptor": buyer[1],
        "buyer_location": buyer[2],
        "contact_name": contact[0],
        "contact_title": contact[1],
        "issued_date": issued,
        "questions_due": questions_due,
        "proposals_due": proposals_due,
        "award_date": award,
        "start_date": start,
        "evaluation": EVALUATION_CRITERIA,
    }


def library_block(topic: str) -> dict:
    return RESPONSE_LIBRARY[topic]
