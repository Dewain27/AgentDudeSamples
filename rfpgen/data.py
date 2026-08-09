"""Randomized data pools used to build RFP scenarios.

Everything here is fictional. Add or edit entries freely to change the variety
of documents the generator produces.
"""

# ---------------------------------------------------------------------------
# Client organizations, grouped by industry. Each is a fictional buyer that
# might issue an RFP for custom software.
# ---------------------------------------------------------------------------

CLIENTS = {
    "healthcare": [
        {"name": "Riverside Health Partners", "descriptor": "a regional network of outpatient clinics", "location": "Ohio"},
        {"name": "Cascade Family Medicine", "descriptor": "a multi-specialty physician group", "location": "Oregon"},
        {"name": "Brightpath Behavioral Health", "descriptor": "a nonprofit mental-health provider", "location": "Colorado"},
    ],
    "government": [
        {"name": "Franklin County", "descriptor": "a county government of roughly 280,000 residents", "location": "Pennsylvania"},
        {"name": "City of Lakemont", "descriptor": "a mid-size municipal government", "location": "Michigan"},
        {"name": "State Department of Workforce Services", "descriptor": "a state workforce agency", "location": "Nevada"},
    ],
    "education": [
        {"name": "Northgate Community College District", "descriptor": "a two-campus community college district", "location": "California"},
        {"name": "Meridian Unified School District", "descriptor": "a K-12 district serving 24,000 students", "location": "Arizona"},
        {"name": "Lakeshore State University", "descriptor": "a public regional university", "location": "Wisconsin"},
    ],
    "financial services": [
        {"name": "Summit Ridge Credit Union", "descriptor": "a member-owned credit union", "location": "Utah"},
        {"name": "Harbor Point Bank", "descriptor": "a regional community bank", "location": "Massachusetts"},
        {"name": "Cornerstone Insurance Group", "descriptor": "a mid-market property & casualty insurer", "location": "Georgia"},
    ],
    "manufacturing": [
        {"name": "Ironwood Manufacturing", "descriptor": "a precision metal-components manufacturer", "location": "Indiana"},
        {"name": "Pacific Coast Foods", "descriptor": "a food-processing company with four plants", "location": "Washington"},
        {"name": "Vector Industrial Supply", "descriptor": "an industrial parts distributor", "location": "Texas"},
    ],
    "retail": [
        {"name": "Trailhead Outfitters", "descriptor": "a specialty outdoor-gear retailer with 90 stores", "location": "Colorado"},
        {"name": "Maple & Main Home Goods", "descriptor": "a home-furnishings retail chain", "location": "Minnesota"},
        {"name": "Urban Pantry Markets", "descriptor": "a regional grocery cooperative", "location": "Illinois"},
    ],
    "nonprofit": [
        {"name": "Open Horizons Foundation", "descriptor": "a national education nonprofit", "location": "New York"},
        {"name": "GreenField Conservancy", "descriptor": "a land and water conservation nonprofit", "location": "Montana"},
        {"name": "Community Bridges Alliance", "descriptor": "a social-services nonprofit with 60 chapters", "location": "Florida"},
    ],
}


# ---------------------------------------------------------------------------
# Project types. Each defines the shape of the software the client wants built,
# along with tailored requirements and success measures.
# ---------------------------------------------------------------------------

PROJECTS = {
    "patient-portal": {
        "label": "Patient Engagement & Scheduling Portal",
        "industries": ["healthcare"],
        "summary": (
            "a secure, patient-facing web and mobile portal for appointment "
            "scheduling, intake forms, secure messaging, and access to records"
        ),
        "drivers": [
            "reduce call-center volume and manual scheduling work",
            "lower appointment no-show rates",
            "meet patients' expectations for self-service digital access",
        ],
        "functional": [
            "Online appointment scheduling and rescheduling with real-time availability",
            "Digital intake and consent forms with pre-visit completion",
            "Secure two-way messaging between patients and care teams",
            "Access to visit summaries, lab results, and medication lists",
            "Automated appointment reminders via SMS and email",
            "Bill review and online payment",
        ],
        "integrations": [
            "existing Electronic Health Record (EHR) system via HL7/FHIR",
            "the practice management / scheduling system",
            "a payment processor for online bill pay",
        ],
        "compliance": ["HIPAA", "WCAG 2.1 AA accessibility"],
        "success": [
            "20% reduction in no-show rate within 12 months",
            "40% of appointments booked online within 6 months of launch",
            "measurable reduction in inbound scheduling calls",
        ],
    },
    "erp": {
        "label": "ERP Modernization & Integration",
        "industries": ["manufacturing", "retail", "nonprofit"],
        "summary": (
            "modernization of core enterprise resource planning workflows and "
            "integration of disconnected operational systems into a unified "
            "platform"
        ),
        "drivers": [
            "eliminate duplicate data entry across disconnected systems",
            "replace brittle spreadsheet-based processes",
            "give leadership real-time operational visibility",
        ],
        "functional": [
            "Unified dashboard for operations, inventory, and finance",
            "Automated workflows replacing manual spreadsheet processes",
            "Role-based views for floor staff, managers, and executives",
            "Real-time inventory and order tracking",
            "Configurable reporting and data export",
            "Audit trail for all transactions and changes",
        ],
        "integrations": [
            "the existing ERP / accounting system",
            "inventory and warehouse management tools",
            "reporting and business-intelligence tools",
        ],
        "compliance": ["SOC 2", "WCAG 2.1 AA accessibility"],
        "success": [
            "elimination of dual data entry between core systems",
            "reporting cycle time reduced from days to minutes",
            "single source of truth for operational data",
        ],
    },
    "constituent-portal": {
        "label": "Constituent Services & Permitting Portal",
        "industries": ["government"],
        "summary": (
            "a public-facing portal that moves permitting, licensing, and "
            "service requests online with case tracking for staff"
        ),
        "drivers": [
            "move paper- and counter-based processes online",
            "reduce processing time and constituent wait times",
            "meet accessibility and transparency obligations",
        ],
        "functional": [
            "Online application submission for permits and licenses",
            "Document upload and status tracking for applicants",
            "Configurable review and approval workflows for staff",
            "Online fee payment and receipts",
            "Public dashboard of request status and processing times",
            "Notifications for status changes and required actions",
        ],
        "integrations": [
            "the existing GIS / land-management system",
            "the payment gateway used for municipal fees",
            "the records management / document system",
        ],
        "compliance": ["Section 508", "WCAG 2.1 AA accessibility", "state records-retention rules"],
        "success": [
            "at least 15 paper workflows moved fully online",
            "average permit processing time reduced by 30%",
            "self-service adoption by a majority of applicants",
        ],
    },
    "student-services": {
        "label": "Unified Student Services Platform",
        "industries": ["education"],
        "summary": (
            "a single platform unifying advising, financial aid, registration, "
            "and student support services with a shared student view"
        ),
        "drivers": [
            "eliminate the need for students to navigate multiple disconnected systems",
            "give advisors a single, complete view of each student",
            "improve retention through earlier intervention",
        ],
        "functional": [
            "Single sign-on student dashboard across services",
            "Advising appointment scheduling and case notes",
            "Financial aid status and document submission",
            "Early-alert flags for at-risk students",
            "Self-service registration and holds resolution",
            "Accessible design across web and mobile",
        ],
        "integrations": [
            "the Student Information System (SIS)",
            "the Learning Management System (LMS)",
            "the financial aid management system",
        ],
        "compliance": ["FERPA", "WCAG 2.1 AA accessibility"],
        "success": [
            "single sign-on across at least four student services",
            "reduction in duplicate data entry for staff",
            "measurable improvement in advising engagement",
        ],
    },
    "loan-origination": {
        "label": "Loan Origination & Member Servicing Platform",
        "industries": ["financial services"],
        "summary": (
            "a digital loan-application and decisioning workflow with a member "
            "self-service portal and staff servicing tools"
        ),
        "drivers": [
            "shorten loan decision times",
            "provide members a modern digital application experience",
            "reduce manual, error-prone back-office steps",
        ],
        "functional": [
            "Online loan application with document upload",
            "Automated pre-qualification and decisioning rules",
            "Member self-service portal for status and payments",
            "Staff underwriting and servicing workspace",
            "Configurable approval workflows and audit trail",
            "Notifications and e-signature for closing documents",
        ],
        "integrations": [
            "the core banking system",
            "a credit-bureau / decisioning data provider",
            "the document management and e-signature systems",
        ],
        "compliance": ["SOC 2", "GLBA", "WCAG 2.1 AA accessibility"],
        "success": [
            "average loan decision time reduced from days to hours",
            "majority of applications submitted digitally",
            "full audit trail for regulatory reporting",
        ],
    },
    "data-warehouse": {
        "label": "Enterprise Data Warehouse & Analytics",
        "industries": ["healthcare", "financial services", "manufacturing", "retail", "education", "government"],
        "summary": (
            "consolidation of data from multiple source systems into a governed "
            "data warehouse with self-service reporting and dashboards"
        ),
        "drivers": [
            "replace slow, manual reporting pulled from many systems",
            "establish a governed single source of truth",
            "enable self-service analytics for business users",
        ],
        "functional": [
            "Automated data pipelines from all major source systems",
            "Governed, documented data model and definitions",
            "Self-service dashboards and reporting for business users",
            "Scheduled and ad-hoc report export",
            "Role-based access to sensitive data",
            "Data-quality monitoring and alerting",
        ],
        "integrations": [
            "each of the organization's core operational systems",
            "the existing business-intelligence / dashboard tool",
            "the identity provider for access control",
        ],
        "compliance": ["SOC 2", "data-governance and retention policies"],
        "success": [
            "at least eight source systems consolidated",
            "reporting time reduced from days to minutes",
            "adoption of self-service dashboards by business teams",
        ],
    },
    "mobile-field-app": {
        "label": "Mobile Field Operations Application",
        "industries": ["manufacturing", "government", "nonprofit", "retail"],
        "summary": (
            "a mobile application for field and frontline staff to capture "
            "data, manage tasks, and work reliably offline"
        ),
        "drivers": [
            "replace paper forms and manual data re-entry in the field",
            "give field staff reliable tools that work offline",
            "get field data into core systems in real time",
        ],
        "functional": [
            "Offline-capable data capture with automatic sync",
            "Task and work-order assignment and tracking",
            "Photo, signature, and barcode/QR capture",
            "GPS and location tagging of records",
            "Push notifications for new assignments",
            "Supervisor dashboard for field activity",
        ],
        "integrations": [
            "the core system of record for work orders",
            "the asset or inventory management system",
            "the identity provider for staff sign-in",
        ],
        "compliance": ["SOC 2", "WCAG 2.1 AA accessibility"],
        "success": [
            "elimination of paper forms for core field workflows",
            "field data available in core systems in near real time",
            "reduction in data-entry errors and rework",
        ],
    },
}


# ---------------------------------------------------------------------------
# Cross-cutting requirement pools shared across most projects.
# ---------------------------------------------------------------------------

TECHNICAL_REQUIREMENTS = [
    "Cloud-hosted (AWS, Azure, or GCP) with infrastructure-as-code",
    "Responsive design supporting current versions of major browsers",
    "Single sign-on (SSO) via SAML 2.0 or OpenID Connect",
    "Role-based access control with least-privilege defaults",
    "RESTful APIs for all major integrations, with documentation",
    "Automated backups with a documented recovery objective",
    "99.9% uptime target during business hours",
    "Comprehensive logging, monitoring, and alerting",
]

SECURITY_REQUIREMENTS = [
    "Encryption of data in transit (TLS 1.2+) and at rest (AES-256)",
    "Multi-factor authentication for privileged accounts",
    "Annual third-party penetration testing and remediation",
    "Documented vulnerability-management and patching process",
    "Audit logging of security-relevant events with retention",
    "Data-handling practices consistent with the stated compliance framework",
    "Secure software development lifecycle with code review",
]

EVALUATION_CRITERIA = [
    ("Technical approach and solution fit", 30),
    ("Relevant experience and past performance", 20),
    ("Project team qualifications", 15),
    ("Cost and value", 20),
    ("Project plan and timeline", 10),
    ("References", 5),
]

# Plausible-but-invented budget ranges by project scale, in USD.
BUDGET_RANGES = {
    "small": (150_000, 350_000),
    "medium": (350_000, 750_000),
    "large": (750_000, 1_800_000),
}

# Typical delivery durations (months) by project scale.
DURATION_MONTHS = {
    "small": (4, 6),
    "medium": (6, 10),
    "large": (10, 16),
}

ORG_SIZES = ["small", "medium", "large"]
