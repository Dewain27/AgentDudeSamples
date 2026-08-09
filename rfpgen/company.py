"""The fictional vendor whose RFP responses this tool generates.

Aventra Software Group is entirely made up. Edit anything here to reshape the
vendor's identity, capabilities, and boilerplate.
"""

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass(frozen=True)
class Vendor:
    name: str
    tagline: str
    founded: int
    headquarters: str
    employees: str
    website: str
    email: str
    phone: str
    overview: str
    capabilities: List[str] = field(default_factory=list)
    differentiators: List[str] = field(default_factory=list)
    certifications: List[str] = field(default_factory=list)
    tech_stack: List[str] = field(default_factory=list)
    # Fictional past-performance case studies, keyed by industry.
    case_studies: Dict[str, List[str]] = field(default_factory=dict)


VENDOR = Vendor(
    name="Aventra Software Group",
    tagline="Custom software that fits the way your organization actually works.",
    founded=2009,
    headquarters="Austin, Texas",
    employees="240",
    website="www.aventrasoftware.example",
    email="proposals@aventrasoftware.example",
    phone="(512) 555-0182",
    overview=(
        "Aventra Software Group designs, builds, and operates custom software "
        "for mid-market and enterprise organizations. Since 2009 we have "
        "delivered more than 300 engagements across healthcare, government, "
        "education, financial services, and manufacturing. We specialize in "
        "modernizing legacy systems, unifying fragmented data, and shipping "
        "user-friendly applications that teams adopt without a fight."
    ),
    capabilities=[
        "Custom web and mobile application development",
        "Legacy system modernization and re-platforming",
        "Cloud migration and cloud-native architecture (AWS, Azure, GCP)",
        "Data platforms, warehousing, and analytics",
        "Systems integration and API development",
        "UX research and accessible interface design (WCAG 2.1 AA)",
        "DevOps, CI/CD, and managed operations",
        "Security engineering and compliance support",
    ],
    differentiators=[
        "Fixed-scope discovery sprint before any build commitment, so pricing "
        "reflects a shared understanding of the work.",
        "Dedicated, co-located delivery pods — the people who scope your "
        "project are the people who build it.",
        "Accessibility and security reviewed at every sprint, not bolted on "
        "before launch.",
        "Source code, infrastructure-as-code, and documentation handed over in "
        "full; no vendor lock-in.",
        "Post-launch care plan with defined SLAs and a named support lead.",
    ],
    certifications=[
        "SOC 2 Type II",
        "ISO/IEC 27001:2022",
        "HIPAA-aligned engineering practices",
        "AWS Advanced Consulting Partner",
        "Microsoft Solutions Partner (Digital & App Innovation)",
    ],
    tech_stack=[
        "TypeScript / React / Next.js",
        "Python / Django / FastAPI",
        "Java / Spring Boot",
        ".NET / C#",
        "PostgreSQL, SQL Server, and Snowflake",
        "Kubernetes, Terraform, and GitHub Actions",
    ],
    case_studies={
        "healthcare": [
            "Built a patient intake and scheduling portal for a 6-clinic "
            "regional provider, cutting no-show rates by 22% in the first year.",
            "Modernized a HL7/FHIR integration layer connecting an EHR to three "
            "specialty systems, retiring 40,000 lines of legacy code.",
        ],
        "government": [
            "Delivered a public permits-and-licensing portal for a mid-size "
            "county, moving 18 paper workflows online.",
            "Rebuilt a benefits eligibility screening tool used by 400 "
            "caseworkers, meeting Section 508 accessibility standards.",
        ],
        "education": [
            "Developed a unified student services platform for a community "
            "college district serving 30,000 students.",
            "Integrated a learning management system with an SIS and financial "
            "aid system, eliminating dual data entry.",
        ],
        "financial services": [
            "Built a loan-origination workflow platform for a regional credit "
            "union, reducing average decision time from days to hours.",
            "Delivered a compliance reporting data warehouse consolidating 12 "
            "source systems.",
        ],
        "manufacturing": [
            "Created a plant-floor production tracking application replacing a "
            "spreadsheet-based process across 4 facilities.",
            "Integrated an ERP with shop-floor IoT sensors for real-time OEE "
            "dashboards.",
        ],
        "retail": [
            "Built an omnichannel inventory and order-management platform for a "
            "120-store specialty retailer.",
            "Delivered a customer loyalty and promotions engine integrated with "
            "the point-of-sale system.",
        ],
        "nonprofit": [
            "Developed a donor and grant management system for a national "
            "nonprofit, unifying three disconnected databases.",
            "Built a volunteer coordination and impact-reporting platform used "
            "across 60 chapters.",
        ],
    },
)


# A small fictional team roster the response generator can draw from.
TEAM_ROLES = [
    ("Engagement Director", "18 years delivering enterprise software programs"),
    ("Solution Architect", "designs the system architecture and integration approach"),
    ("Lead Engineer", "owns technical delivery and code quality"),
    ("UX Designer", "runs user research and accessible interface design"),
    ("Project Manager", "single point of contact for schedule, scope, and status"),
    ("QA Lead", "owns the test strategy, automation, and release readiness"),
    ("Security Engineer", "reviews architecture, code, and infrastructure for risk"),
]

# Fictional named team members (used to make responses feel concrete).
TEAM_NAMES = [
    "Priya Raman", "Marcus Bell", "Elena Duarte", "Sofia Nguyen",
    "David Okafor", "Hannah Weiss", "Omar Haddad", "Grace Kim",
    "Tomás Herrera", "Aisha Bello", "Liam O'Connor", "Rachel Stein",
]
