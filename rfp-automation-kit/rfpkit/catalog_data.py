"""Source-of-truth catalog for the RFP Automation Kit.

Defines the fictional vendor, its product lines and offerings, and a reusable
"response library" of answer blocks. Everything here is invented for
demonstration.

This module is the single place to edit the catalog. `generate.py export`
serializes it to `data/catalog.json` for machine consumption by a downstream
automation implementation.
"""

# ---------------------------------------------------------------------------
# Vendor identity (fictional)
# ---------------------------------------------------------------------------

VENDOR = {
    "name": "Aventra Software Group",
    "tagline": "Custom software that fits the way your organization actually works.",
    "founded": 2009,
    "headquarters": "Austin, Texas",
    "employees": "240",
    "website": "www.aventrasoftware.example",
    "email": "proposals@aventrasoftware.example",
    "phone": "(512) 555-0182",
    "certifications": [
        "SOC 2 Type II",
        "ISO/IEC 27001:2022",
        "HIPAA-aligned engineering practices",
        "AWS Advanced Consulting Partner",
        "Microsoft Solutions Partner (Digital & App Innovation)",
    ],
}


# ---------------------------------------------------------------------------
# Product lines. Each groups a set of offerings.
# ---------------------------------------------------------------------------

PRODUCT_LINES = {
    "custom-apps": {
        "name": "Custom Application Development",
        "summary": "Bespoke web and mobile applications and modernization of legacy systems.",
    },
    "data-analytics": {
        "name": "Data & Analytics",
        "summary": "Data platforms, pipelines, and analytics that turn scattered data into decisions.",
    },
    "cloud-platform": {
        "name": "Cloud & Platform Engineering",
        "summary": "Cloud migration and the automation that keeps modern platforms reliable.",
    },
    "integration": {
        "name": "Integration & APIs",
        "summary": "Connecting the systems an organization already runs.",
    },
    "industry-solutions": {
        "name": "Industry Solutions",
        "summary": "Configurable, vertical products for regulated industries.",
    },
    "managed-services": {
        "name": "Managed Services & Security",
        "summary": "Ongoing operation, support, and security of delivered software.",
    },
}


# ---------------------------------------------------------------------------
# Reusable answer library. These blocks answer RFP questions that recur across
# nearly every proposal. A downstream automation matches an incoming RFP
# question to a topic key and pulls the block. Offerings can override any of
# these with an entry in their own `snippets`.
#
# `keywords` drive the simple automated matcher in rfpkit/automation.py.
# ---------------------------------------------------------------------------

RESPONSE_LIBRARY = {
    "company_overview": {
        "title": "About Aventra Software Group",
        "keywords": ["company", "about", "background", "overview", "who are you", "history", "experience firm"],
        "answer": (
            "Aventra Software Group has designed, built, and operated custom software for "
            "mid-market and enterprise organizations since 2009, delivering more than 300 "
            "engagements across healthcare, government, education, financial services, and "
            "manufacturing. We specialize in modernizing legacy systems, unifying fragmented "
            "data, and shipping applications that teams adopt without a fight."
        ),
    },
    "methodology": {
        "title": "Delivery methodology",
        "keywords": ["methodology", "approach", "process", "agile", "sprint", "how do you deliver", "sdlc"],
        "answer": (
            "We deliver in short, fixed-length sprints, each ending with a working, "
            "demonstrable increment and a stakeholder review. Every engagement begins with a "
            "fixed-scope discovery sprint that confirms requirements, design, and a detailed "
            "plan before any build commitment, so scope and pricing reflect a shared "
            "understanding of the work."
        ),
    },
    "security": {
        "title": "Security",
        "keywords": ["security", "encryption", "penetration", "vulnerability", "secure", "threat", "cyber"],
        "answer": (
            "Security is reviewed every sprint, not bolted on before launch. All data is "
            "encrypted in transit (TLS 1.2+) and at rest (AES-256), privileged access requires "
            "multi-factor authentication, and security-relevant events are audit-logged with "
            "retention. We follow a secure SDLC with mandatory code review, run annual "
            "third-party penetration tests, and maintain a documented vulnerability-management "
            "and patching process. Aventra is SOC 2 Type II and ISO/IEC 27001:2022 aligned."
        ),
    },
    "data_privacy": {
        "title": "Data privacy",
        "keywords": ["privacy", "pii", "gdpr", "data protection", "personal data", "retention", "hipaa", "ferpa"],
        "answer": (
            "We handle personal and sensitive data on a least-privilege, need-to-know basis, "
            "with role-based access control and full audit logging. Data classification, "
            "retention, and disposal are defined per engagement to meet the applicable "
            "framework (e.g. HIPAA, FERPA, GLBA). We support data residency requirements and "
            "provide data export and deletion on request."
        ),
    },
    "accessibility": {
        "title": "Accessibility",
        "keywords": ["accessibility", "wcag", "508", "ada", "screen reader", "accessible"],
        "answer": (
            "All user interfaces are designed and tested to WCAG 2.1 AA (and Section 508 where "
            "applicable). Accessibility is validated each sprint with automated tooling and "
            "manual screen-reader testing, not deferred to a pre-launch audit."
        ),
    },
    "hosting": {
        "title": "Hosting and infrastructure",
        "keywords": ["hosting", "infrastructure", "cloud", "aws", "azure", "gcp", "uptime", "availability", "sla hosting"],
        "answer": (
            "Solutions are cloud-hosted on AWS, Azure, or GCP (your choice), deployed with "
            "infrastructure-as-code so environments are reproducible and auditable. We target "
            "99.9% uptime during business hours, with automated backups and a documented "
            "recovery objective. You retain ownership of the cloud accounts and all "
            "infrastructure code."
        ),
    },
    "sso": {
        "title": "Authentication and single sign-on",
        "keywords": ["sso", "single sign-on", "authentication", "saml", "oauth", "oidc", "login", "identity"],
        "answer": (
            "We integrate with your existing identity provider using SAML 2.0 or OpenID "
            "Connect for single sign-on, with role-based access control and least-privilege "
            "defaults. Multi-factor authentication is enforced for privileged accounts."
        ),
    },
    "integration_approach": {
        "title": "Integration approach",
        "keywords": ["integration", "integrate", "api", "interface", "connect", "interoperability", "middleware"],
        "answer": (
            "Each integration is delivered through documented, versioned REST APIs with a clear "
            "contract and explicit error handling. We prove every integration end-to-end in a "
            "test environment before it reaches production, and we document assumptions and "
            "data mappings for each connected system."
        ),
    },
    "quality_assurance": {
        "title": "Quality assurance and testing",
        "keywords": ["quality", "qa", "testing", "test", "automation testing", "defect", "uat"],
        "answer": (
            "Quality is built in: automated tests run in CI on every change, all code is peer "
            "reviewed, and each release passes a security review before go-live. We support a "
            "formal user-acceptance testing phase with your team and track defects to closure "
            "against agreed severity and response targets."
        ),
    },
    "support_sla": {
        "title": "Support and service levels",
        "keywords": ["support", "sla", "maintenance", "warranty", "help desk", "post-launch", "service level", "response time"],
        "answer": (
            "Every launch includes a defined post-launch care plan with a named support lead "
            "and tiered service levels: critical issues acknowledged within 1 business hour, "
            "high within 4, and standard within 1 business day. The care plan covers "
            "monitoring, patching, and enhancements, and is quoted separately as an optional, "
            "renewable service."
        ),
    },
    "training": {
        "title": "Training and knowledge transfer",
        "keywords": ["training", "knowledge transfer", "onboarding", "documentation", "adoption", "change management"],
        "answer": (
            "We deliver role-based training (administrators, staff, and end users), written and "
            "video documentation, and a live knowledge-transfer session with your technical "
            "team. Full source code, infrastructure-as-code, and documentation are handed over "
            "so your organization is self-sufficient — no vendor lock-in."
        ),
    },
    "pricing_approach": {
        "title": "Pricing approach",
        "keywords": ["pricing", "price", "cost", "fee", "budget", "payment", "rate", "invoice"],
        "answer": (
            "We propose a fixed price against the scope confirmed in discovery, itemized by "
            "workstream, and invoiced on milestone completion. Change requests are handled "
            "through a lightweight change-control process so cost and scope stay aligned. "
            "Third-party license and hosting fees are called out separately and are not marked "
            "up."
        ),
    },
    "references": {
        "title": "References",
        "keywords": ["reference", "referral", "past clients", "customer references", "testimonial"],
        "answer": (
            "We provide at least three references from comparable engagements — matched by "
            "industry and project type — on request, along with a summary of the work "
            "delivered and outcomes achieved."
        ),
    },
    "assumptions": {
        "title": "Assumptions, exclusions, and risks",
        "keywords": ["assumption", "exclusion", "risk", "dependency", "out of scope", "constraint"],
        "answer": (
            "Our pricing assumes the scope described in the RFP, timely access to stakeholders "
            "and source/target systems, and availability of test environments at project "
            "start. Third-party licenses, ongoing hosting, and hardware are excluded from the "
            "fixed fee. Integration unknowns are surfaced early in discovery and managed "
            "through change control; a named support lead owns post-launch stability."
        ),
    },
    "why_aventra": {
        "title": "Why Aventra",
        "keywords": ["why", "differentiator", "why choose", "what makes you", "unique", "advantage"],
        "answer": (
            "Fixed-scope discovery before any build commitment; dedicated delivery pods where "
            "the people who scope your project are the people who build it; accessibility and "
            "security reviewed every sprint; and full handover of code, infrastructure, and "
            "documentation with a defined post-launch care plan. You are never locked in."
        ),
    },
}


# ---------------------------------------------------------------------------
# Offerings. Each belongs to a product line and carries the content needed to
# generate both a sample RFP request (what a buyer would ask for) and a sample
# RFP response (assembled from `snippets` plus the shared RESPONSE_LIBRARY).
# ---------------------------------------------------------------------------

OFFERINGS = [
    # ----- Custom Application Development ---------------------------------
    {
        "id": "web-app-platform",
        "line": "custom-apps",
        "name": "Custom Web Application Platform",
        "tagline": "A tailored web application built around your workflows.",
        "summary": (
            "design and delivery of a custom, cloud-hosted web application built around the "
            "organization's specific workflows, users, and data"
        ),
        "target_industries": ["financial services", "manufacturing", "nonprofit", "government", "education"],
        "capabilities": [
            "Custom workflow and business-process automation",
            "Role-based dashboards for staff, managers, and executives",
            "Configurable forms, records, and approval flows",
            "Reporting and data export",
            "Responsive design for desktop and tablet",
            "Full audit trail of records and changes",
        ],
        "typical_requirements": [
            "Replace manual or spreadsheet-based processes with a single web application",
            "Role-based access for different user groups",
            "Configurable approval workflows",
            "Reporting and export for leadership",
            "Audit trail of all changes",
            "Integration with the existing system of record",
        ],
        "integrations": ["the existing system of record", "the identity provider (SSO)", "a reporting / BI tool"],
        "compliance": ["SOC 2", "WCAG 2.1 AA"],
        "differentiators": [
            "Built around your actual workflows, not a rigid off-the-shelf template",
            "You own the source code and infrastructure outright",
        ],
        "pricing_model": "Fixed price by workstream, invoiced on milestones",
        "price_low": 220_000,
        "price_high": 550_000,
        "timeline_months": 7,
        "success_metrics": [
            "manual/spreadsheet processes replaced by a single application",
            "reporting cycle time reduced from days to minutes",
            "adoption by the majority of intended users within one quarter",
        ],
        "snippets": {
            "understanding": (
                "You need a single, purpose-built web application that replaces manual and "
                "spreadsheet-based work, gives each role the view it needs, and produces "
                "reliable reporting for leadership."
            ),
            "solution": (
                "We will design and build a custom web application shaped around your workflows: "
                "configurable forms and approval flows, role-based dashboards, a complete audit "
                "trail, and reporting your team can run without IT. It is cloud-hosted and "
                "integrates with your existing system of record."
            ),
        },
    },
    {
        "id": "mobile-app-suite",
        "line": "custom-apps",
        "name": "Mobile Application Suite",
        "tagline": "Field-ready mobile apps that work even offline.",
        "summary": (
            "design and delivery of native-quality mobile applications for frontline and field "
            "staff, with reliable offline operation and sync"
        ),
        "target_industries": ["manufacturing", "government", "retail", "nonprofit"],
        "capabilities": [
            "Offline-capable data capture with automatic sync",
            "Task and work-order assignment and tracking",
            "Photo, signature, and barcode/QR capture",
            "GPS and location tagging of records",
            "Push notifications for new assignments",
            "Supervisor dashboard for field activity",
        ],
        "typical_requirements": [
            "Mobile app for field or frontline staff",
            "Reliable operation with no or intermittent connectivity",
            "Capture of photos, signatures, and scanned codes",
            "Real-time visibility of field activity for supervisors",
            "Sync of field data into the core system of record",
            "Secure sign-in for staff devices",
        ],
        "integrations": ["the core work-order / system of record", "the asset or inventory system", "the identity provider (SSO)"],
        "compliance": ["SOC 2", "WCAG 2.1 AA"],
        "differentiators": [
            "Offline-first architecture proven in low-connectivity environments",
            "One codebase deployed to both iOS and Android",
        ],
        "pricing_model": "Fixed price by workstream, invoiced on milestones",
        "price_low": 260_000,
        "price_high": 600_000,
        "timeline_months": 8,
        "success_metrics": [
            "paper forms eliminated for core field workflows",
            "field data available in core systems in near real time",
            "reduction in data-entry errors and rework",
        ],
        "snippets": {
            "understanding": (
                "Your field teams need tools that work wherever they are — including with no "
                "signal — and that get clean data back into your core systems without manual "
                "re-entry."
            ),
            "solution": (
                "We will deliver an offline-first mobile suite for iOS and Android: field staff "
                "capture data, photos, signatures, and scans on-device, and everything syncs "
                "automatically when connectivity returns. Supervisors get a live dashboard of "
                "field activity."
            ),
        },
    },
    {
        "id": "legacy-modernization",
        "line": "custom-apps",
        "name": "Legacy Application Modernization",
        "tagline": "Retire risky legacy systems without a big-bang rewrite.",
        "summary": (
            "incremental modernization of an aging, hard-to-maintain application onto a "
            "supported, cloud-native architecture with no loss of business function"
        ),
        "target_industries": ["government", "financial services", "healthcare", "manufacturing", "education"],
        "capabilities": [
            "Assessment of the existing system and modernization roadmap",
            "Incremental re-platforming (strangler-fig approach)",
            "Data migration with validation and reconciliation",
            "Preservation and improvement of existing business rules",
            "Cloud-native, supportable target architecture",
            "Parallel-run and cutover planning",
        ],
        "typical_requirements": [
            "Replace an unsupported or high-risk legacy application",
            "Preserve existing business rules and data",
            "Minimize disruption during transition",
            "Migrate historical data with validation",
            "Move to a supportable, cloud-hosted platform",
            "Reduce ongoing maintenance cost and risk",
        ],
        "integrations": ["the legacy database", "downstream systems that consume legacy data", "the identity provider (SSO)"],
        "compliance": ["SOC 2", "WCAG 2.1 AA"],
        "differentiators": [
            "Incremental strangler-fig approach avoids risky big-bang cutovers",
            "Business rules are re-verified, not blindly copied",
        ],
        "pricing_model": "Fixed price per phase, invoiced on milestones",
        "price_low": 400_000,
        "price_high": 1_200_000,
        "timeline_months": 12,
        "success_metrics": [
            "legacy system retired with no loss of function",
            "historical data migrated and reconciled",
            "measurable reduction in maintenance cost and risk",
        ],
        "snippets": {
            "understanding": (
                "You are carrying an aging system that is expensive and risky to maintain, and "
                "you need to modernize it without disrupting the business or losing years of "
                "data and hard-won business rules."
            ),
            "solution": (
                "We modernize incrementally using a strangler-fig approach: new, cloud-native "
                "components take over function piece by piece behind a stable interface, so the "
                "old system is retired gradually and safely. Data is migrated with validation "
                "and reconciliation, and every business rule is re-verified as it moves."
            ),
        },
    },

    # ----- Data & Analytics ----------------------------------------------
    {
        "id": "data-warehouse",
        "line": "data-analytics",
        "name": "Enterprise Data Warehouse",
        "tagline": "One governed source of truth for your data.",
        "summary": (
            "consolidation of data from multiple source systems into a governed cloud data "
            "warehouse with a documented, trustworthy data model"
        ),
        "target_industries": ["healthcare", "financial services", "manufacturing", "retail", "education", "government"],
        "capabilities": [
            "Automated data pipelines from all major source systems",
            "Governed, documented data model and definitions",
            "Role-based access to sensitive data",
            "Data-quality monitoring and alerting",
            "Historical and point-in-time reporting",
            "Foundation for BI, analytics, and AI",
        ],
        "typical_requirements": [
            "Consolidate data from many disconnected systems",
            "Establish a governed single source of truth",
            "Automate slow, manual reporting pulls",
            "Enforce role-based access to sensitive data",
            "Monitor and alert on data quality",
            "Support historical and point-in-time analysis",
        ],
        "integrations": ["each core operational system", "the identity provider (SSO)", "the BI / dashboard tool"],
        "compliance": ["SOC 2", "data-governance and retention policies"],
        "differentiators": [
            "Governed, documented model — analysts trust the numbers",
            "Cloud-native warehouse scales without re-platforming",
        ],
        "pricing_model": "Fixed price by workstream, invoiced on milestones",
        "price_low": 300_000,
        "price_high": 900_000,
        "timeline_months": 9,
        "success_metrics": [
            "at least eight source systems consolidated",
            "reporting time reduced from days to minutes",
            "a single, documented source of truth adopted across teams",
        ],
        "snippets": {
            "understanding": (
                "Your data is spread across many systems, reporting is slow and manual, and "
                "teams argue about whose numbers are right. You need one governed source of "
                "truth."
            ),
            "solution": (
                "We will build a cloud-native data warehouse fed by automated pipelines from "
                "your source systems, on a documented and governed data model with role-based "
                "access and data-quality monitoring — the trustworthy foundation for reporting, "
                "analytics, and AI."
            ),
        },
    },
    {
        "id": "bi-dashboards",
        "line": "data-analytics",
        "name": "Business Intelligence & Dashboards",
        "tagline": "Self-service dashboards your business teams actually use.",
        "summary": (
            "design and delivery of governed, self-service dashboards and reporting that give "
            "business users answers without waiting on IT"
        ),
        "target_industries": ["retail", "financial services", "manufacturing", "healthcare", "education", "government", "nonprofit"],
        "capabilities": [
            "Executive and operational dashboards",
            "Self-service reporting for business users",
            "Governed metric definitions everyone shares",
            "Scheduled and ad-hoc report export",
            "Drill-down from summary to detail",
            "Role-based access to sensitive views",
        ],
        "typical_requirements": [
            "Replace static reports with interactive dashboards",
            "Let business users answer their own questions",
            "Agree on shared, governed metric definitions",
            "Support scheduled and ad-hoc exports",
            "Enforce role-based access to sensitive data",
            "Connect to existing data sources",
        ],
        "integrations": ["the data warehouse or source systems", "the identity provider (SSO)", "email/scheduling for report delivery"],
        "compliance": ["SOC 2", "WCAG 2.1 AA"],
        "differentiators": [
            "Governed metrics prevent duplicate, conflicting definitions",
            "Designed for adoption — business users, not just analysts",
        ],
        "pricing_model": "Fixed price by workstream, invoiced on milestones",
        "price_low": 150_000,
        "price_high": 400_000,
        "timeline_months": 5,
        "success_metrics": [
            "static reports replaced by interactive dashboards",
            "self-service adoption by business teams",
            "a shared, governed set of metric definitions in use",
        ],
        "snippets": {
            "understanding": (
                "Leaders wait on IT for static reports, and different teams define the same "
                "metric differently. You want governed, self-service dashboards people trust "
                "and actually use."
            ),
            "solution": (
                "We will deliver executive and operational dashboards on a governed set of "
                "metric definitions, with self-service exploration, drill-down, and scheduled "
                "exports — designed for adoption by business users, with role-based access to "
                "sensitive views."
            ),
        },
    },
    {
        "id": "data-integration",
        "line": "data-analytics",
        "name": "Data Integration & Pipelines",
        "tagline": "Move data reliably between the systems that need it.",
        "summary": (
            "design and delivery of reliable, monitored data pipelines that move and transform "
            "data between systems, eliminating manual exports and dual entry"
        ),
        "target_industries": ["healthcare", "financial services", "manufacturing", "retail", "education", "government"],
        "capabilities": [
            "Automated extract, transform, and load (ETL/ELT) pipelines",
            "Scheduled and event-driven data movement",
            "Data validation and reconciliation",
            "Error handling, retries, and alerting",
            "Data lineage and processing audit trail",
            "Secure handling of sensitive fields",
        ],
        "typical_requirements": [
            "Eliminate manual data exports and dual entry",
            "Move data automatically between systems on a schedule or event",
            "Validate and reconcile data in flight",
            "Alert on failures with clear diagnostics",
            "Maintain lineage and an audit trail",
            "Handle sensitive fields securely",
        ],
        "integrations": ["each source and destination system", "the identity provider (SSO)", "monitoring/alerting channels"],
        "compliance": ["SOC 2", "data-governance and retention policies"],
        "differentiators": [
            "Reconciliation built in — you know the data arrived intact",
            "Observable pipelines with lineage and clear failure alerts",
        ],
        "pricing_model": "Fixed price by workstream, invoiced on milestones",
        "price_low": 160_000,
        "price_high": 450_000,
        "timeline_months": 6,
        "success_metrics": [
            "manual exports and dual entry eliminated",
            "data moved reliably with reconciliation",
            "failures surfaced and resolved via alerting",
        ],
        "snippets": {
            "understanding": (
                "Your teams manually export and re-key data between systems, and errors slip "
                "through unnoticed. You need automated, monitored pipelines you can trust."
            ),
            "solution": (
                "We will build automated ETL/ELT pipelines — scheduled or event-driven — that "
                "move and transform data between your systems with validation, reconciliation, "
                "lineage, and clear failure alerting, so manual exports and dual entry go away."
            ),
        },
    },

    # ----- Cloud & Platform Engineering ----------------------------------
    {
        "id": "cloud-migration",
        "line": "cloud-platform",
        "name": "Cloud Migration",
        "tagline": "Move to the cloud with a plan, not a leap of faith.",
        "summary": (
            "assessment, planning, and execution of a migration from on-premises or legacy "
            "hosting to a modern, cost-efficient cloud environment"
        ),
        "target_industries": ["financial services", "healthcare", "government", "manufacturing", "education", "retail"],
        "capabilities": [
            "Migration assessment and readiness roadmap",
            "Landing-zone and network design",
            "Infrastructure-as-code environment build",
            "Application migration and validation",
            "Cost optimization and right-sizing",
            "Cutover and rollback planning",
        ],
        "typical_requirements": [
            "Move applications off on-premises or legacy hosting",
            "Design a secure, well-architected cloud landing zone",
            "Migrate with minimal downtime",
            "Optimize and forecast cloud cost",
            "Provide infrastructure-as-code for repeatability",
            "Plan cutover and rollback",
        ],
        "integrations": ["existing on-prem systems during transition", "the identity provider (SSO)", "monitoring and cost-management tooling"],
        "compliance": ["SOC 2", "ISO/IEC 27001"],
        "differentiators": [
            "Well-architected landing zone from day one, not retrofitted",
            "Cost modeling so the cloud bill holds no surprises",
        ],
        "pricing_model": "Fixed price per phase, invoiced on milestones",
        "price_low": 200_000,
        "price_high": 700_000,
        "timeline_months": 8,
        "success_metrics": [
            "applications migrated with minimal downtime",
            "a secure, repeatable landing zone in infrastructure-as-code",
            "cloud cost forecasted and optimized",
        ],
        "snippets": {
            "understanding": (
                "You are moving off aging on-premises or legacy hosting and need a migration "
                "that is secure, low-risk, and cost-predictable — not a leap of faith."
            ),
            "solution": (
                "We start with an assessment and readiness roadmap, design a well-architected "
                "landing zone, build it as infrastructure-as-code, and migrate applications in "
                "planned waves with validation, cost optimization, and rollback plans at each "
                "cutover."
            ),
        },
    },
    {
        "id": "devops-automation",
        "line": "cloud-platform",
        "name": "DevOps & Platform Automation",
        "tagline": "Ship faster and sleep better with automated delivery.",
        "summary": (
            "establishment of CI/CD pipelines, infrastructure-as-code, and observability so "
            "software ships frequently, safely, and repeatably"
        ),
        "target_industries": ["financial services", "healthcare", "manufacturing", "retail", "government", "education"],
        "capabilities": [
            "CI/CD pipeline design and implementation",
            "Infrastructure-as-code for all environments",
            "Automated testing and quality gates",
            "Monitoring, logging, and alerting (observability)",
            "Secrets management and secure deployment",
            "Release and rollback automation",
        ],
        "typical_requirements": [
            "Automate build, test, and deployment",
            "Make environments reproducible with infrastructure-as-code",
            "Add quality and security gates to releases",
            "Establish monitoring and alerting",
            "Reduce release risk and manual steps",
            "Enable frequent, low-drama deployments",
        ],
        "integrations": ["the source-control and CI system", "the cloud environment", "monitoring/alerting channels"],
        "compliance": ["SOC 2", "ISO/IEC 27001"],
        "differentiators": [
            "Quality and security gates baked into the pipeline",
            "Observability from day one, not after the first outage",
        ],
        "pricing_model": "Fixed price by workstream, invoiced on milestones",
        "price_low": 150_000,
        "price_high": 400_000,
        "timeline_months": 5,
        "success_metrics": [
            "build, test, and deploy fully automated",
            "environments reproducible from code",
            "release risk and manual steps sharply reduced",
        ],
        "snippets": {
            "understanding": (
                "Releases are manual, risky, and slow, and problems are found in production "
                "instead of before it. You want automated, observable delivery."
            ),
            "solution": (
                "We will implement CI/CD pipelines with automated testing and security gates, "
                "define every environment as infrastructure-as-code, and stand up monitoring "
                "and alerting — so your team ships frequently and safely, with fast rollback."
            ),
        },
    },

    # ----- Integration & APIs --------------------------------------------
    {
        "id": "api-platform",
        "line": "integration",
        "name": "API Development & Management",
        "tagline": "Turn your systems and data into governed, reusable APIs.",
        "summary": (
            "design, build, and management of secure, documented APIs that expose the "
            "organization's systems and data for internal and partner use"
        ),
        "target_industries": ["financial services", "healthcare", "retail", "government", "manufacturing"],
        "capabilities": [
            "RESTful API design following clear standards",
            "API gateway, authentication, and rate limiting",
            "Interactive, versioned API documentation",
            "Developer onboarding and access management",
            "Usage monitoring and analytics",
            "Backward-compatible versioning",
        ],
        "typical_requirements": [
            "Expose internal systems and data through secure APIs",
            "Govern access with authentication and rate limiting",
            "Provide clear, versioned documentation",
            "Onboard internal or partner developers",
            "Monitor API usage and performance",
            "Support backward-compatible versioning",
        ],
        "integrations": ["the systems of record being exposed", "the identity provider (SSO / OAuth)", "the API gateway and monitoring tools"],
        "compliance": ["SOC 2", "data-governance and retention policies"],
        "differentiators": [
            "Standards-based, versioned APIs partners can build on",
            "Governance and monitoring built into the gateway",
        ],
        "pricing_model": "Fixed price by workstream, invoiced on milestones",
        "price_low": 170_000,
        "price_high": 450_000,
        "timeline_months": 6,
        "success_metrics": [
            "systems exposed through secure, documented APIs",
            "developer onboarding self-service and governed",
            "API usage monitored and performant",
        ],
        "snippets": {
            "understanding": (
                "You want to unlock the data and functions trapped in your systems — for "
                "internal teams or partners — through secure, well-governed APIs rather than "
                "one-off point integrations."
            ),
            "solution": (
                "We will design standards-based REST APIs, front them with a gateway that "
                "handles authentication, rate limiting, and monitoring, and publish interactive, "
                "versioned documentation with self-service developer onboarding."
            ),
        },
    },
    {
        "id": "systems-integration",
        "line": "integration",
        "name": "Enterprise Systems Integration",
        "tagline": "Make the systems you already own work together.",
        "summary": (
            "integration of disparate enterprise systems into coordinated, automated workflows "
            "that eliminate manual hand-offs and dual data entry"
        ),
        "target_industries": ["healthcare", "financial services", "manufacturing", "retail", "education", "government"],
        "capabilities": [
            "Point-to-point and hub-based integration",
            "Automated cross-system workflows",
            "Data mapping and transformation",
            "Reliable messaging with retries and dead-letter handling",
            "Monitoring and reconciliation across systems",
            "Documentation of every interface",
        ],
        "typical_requirements": [
            "Connect disparate systems into coordinated workflows",
            "Eliminate manual hand-offs and dual data entry",
            "Map and transform data between systems",
            "Guarantee reliable delivery with retries",
            "Monitor and reconcile cross-system data",
            "Document all interfaces",
        ],
        "integrations": ["each system being connected", "the identity provider (SSO)", "monitoring/alerting channels"],
        "compliance": ["SOC 2", "data-governance and retention policies"],
        "differentiators": [
            "Reliable messaging with retries and reconciliation, not fragile scripts",
            "Every interface documented and monitored",
        ],
        "pricing_model": "Fixed price by workstream, invoiced on milestones",
        "price_low": 190_000,
        "price_high": 550_000,
        "timeline_months": 7,
        "success_metrics": [
            "manual hand-offs and dual entry eliminated",
            "cross-system workflows automated and monitored",
            "every interface documented and reconciled",
        ],
        "snippets": {
            "understanding": (
                "Your systems don't talk to each other, so staff re-key data and coordinate by "
                "email and spreadsheet. You need them integrated into reliable, automated "
                "workflows."
            ),
            "solution": (
                "We will integrate your systems with reliable messaging, data mapping and "
                "transformation, and automated cross-system workflows — with retries, "
                "reconciliation, monitoring, and full interface documentation so the "
                "integrations stay dependable."
            ),
        },
    },

    # ----- Industry Solutions --------------------------------------------
    {
        "id": "patient-portal",
        "line": "industry-solutions",
        "name": "Patient Engagement Portal",
        "tagline": "Self-service scheduling, intake, and messaging for patients.",
        "summary": (
            "a secure, HIPAA-aligned patient portal for scheduling, digital intake, secure "
            "messaging, and access to records, integrated with the EHR"
        ),
        "target_industries": ["healthcare"],
        "capabilities": [
            "Online appointment scheduling and rescheduling",
            "Digital intake and consent forms",
            "Secure two-way patient–care-team messaging",
            "Access to visit summaries, results, and medications",
            "Automated appointment reminders (SMS/email)",
            "Online bill review and payment",
        ],
        "typical_requirements": [
            "Give patients self-service scheduling and intake",
            "Reduce call-center volume and no-shows",
            "Provide secure messaging with care teams",
            "Let patients view records and pay bills online",
            "Integrate with the EHR via HL7/FHIR",
            "Meet HIPAA and accessibility requirements",
        ],
        "integrations": ["the EHR via HL7/FHIR", "the practice-management/scheduling system", "a payment processor"],
        "compliance": ["HIPAA", "WCAG 2.1 AA"],
        "differentiators": [
            "HIPAA-aligned engineering with FHIR expertise",
            "Configurable to your specialties and workflows",
        ],
        "pricing_model": "Fixed price by workstream, invoiced on milestones",
        "price_low": 300_000,
        "price_high": 800_000,
        "timeline_months": 9,
        "success_metrics": [
            "20% reduction in no-show rate within 12 months",
            "40% of appointments booked online within 6 months",
            "measurable reduction in inbound scheduling calls",
        ],
        "snippets": {
            "understanding": (
                "Your patients expect the same self-service they get everywhere else, and your "
                "staff are buried in scheduling calls and paper intake. You need a secure "
                "portal integrated with your EHR."
            ),
            "solution": (
                "We will deliver a HIPAA-aligned patient portal — online scheduling, digital "
                "intake and consent, secure messaging, records access, reminders, and online "
                "bill pay — integrated with your EHR via HL7/FHIR and your scheduling and "
                "payment systems."
            ),
        },
    },
    {
        "id": "constituent-portal",
        "line": "industry-solutions",
        "name": "Constituent Services & Permitting Portal",
        "tagline": "Move permits, licensing, and requests online.",
        "summary": (
            "a public-facing portal that moves permitting, licensing, and service requests "
            "online, with case tracking and configurable review workflows for staff"
        ),
        "target_industries": ["government"],
        "capabilities": [
            "Online application submission for permits and licenses",
            "Document upload and applicant status tracking",
            "Configurable staff review and approval workflows",
            "Online fee payment and receipts",
            "Public dashboard of status and processing times",
            "Notifications for status changes and actions needed",
        ],
        "typical_requirements": [
            "Move paper and counter processes online",
            "Let constituents apply, pay, and track status online",
            "Give staff configurable review workflows",
            "Publish processing times transparently",
            "Meet Section 508 / accessibility requirements",
            "Integrate with GIS, payments, and records systems",
        ],
        "integrations": ["the GIS / land-management system", "the municipal payment gateway", "the records-management system"],
        "compliance": ["Section 508", "WCAG 2.1 AA", "state records-retention rules"],
        "differentiators": [
            "Accessibility and transparency built in for public sector",
            "Configurable workflows for many permit and license types",
        ],
        "pricing_model": "Fixed price per phase, invoiced on milestones",
        "price_low": 350_000,
        "price_high": 950_000,
        "timeline_months": 10,
        "success_metrics": [
            "at least 15 paper workflows moved fully online",
            "average permit processing time reduced by 30%",
            "self-service adoption by a majority of applicants",
        ],
        "snippets": {
            "understanding": (
                "Your constituents still fill out paper and stand in line, and staff track "
                "cases by hand. You need a transparent, accessible portal that moves these "
                "workflows online."
            ),
            "solution": (
                "We will deliver a public portal for permits, licensing, and service requests: "
                "online applications and payments, document upload and status tracking, "
                "configurable staff review workflows, and a public dashboard of processing "
                "times — meeting Section 508 and your records-retention rules."
            ),
        },
    },
    {
        "id": "loan-origination",
        "line": "industry-solutions",
        "name": "Loan Origination & Member Servicing Platform",
        "tagline": "Faster loan decisions and a modern member experience.",
        "summary": (
            "a digital loan-application and decisioning workflow with a member self-service "
            "portal and staff underwriting and servicing tools"
        ),
        "target_industries": ["financial services"],
        "capabilities": [
            "Online loan application with document upload",
            "Automated pre-qualification and decisioning rules",
            "Member self-service portal for status and payments",
            "Staff underwriting and servicing workspace",
            "Configurable approval workflows and audit trail",
            "E-signature for closing documents",
        ],
        "typical_requirements": [
            "Digitize loan applications and decisioning",
            "Shorten loan decision times",
            "Give members self-service status and payments",
            "Provide staff underwriting and servicing tools",
            "Maintain a full audit trail for compliance",
            "Integrate with core banking and credit data",
        ],
        "integrations": ["the core banking system", "a credit-bureau / decisioning data provider", "document-management and e-signature systems"],
        "compliance": ["SOC 2", "GLBA", "WCAG 2.1 AA"],
        "differentiators": [
            "Configurable decisioning rules with a complete audit trail",
            "Experience designed for both members and back-office staff",
        ],
        "pricing_model": "Fixed price per phase, invoiced on milestones",
        "price_low": 400_000,
        "price_high": 1_100_000,
        "timeline_months": 11,
        "success_metrics": [
            "average loan decision time reduced from days to hours",
            "majority of applications submitted digitally",
            "a full audit trail available for regulatory reporting",
        ],
        "snippets": {
            "understanding": (
                "Your members expect a fast, digital lending experience, while your staff need "
                "reliable underwriting tools and a defensible audit trail for regulators."
            ),
            "solution": (
                "We will deliver a digital loan-origination platform: online applications with "
                "document upload, configurable pre-qualification and decisioning rules, a member "
                "self-service portal, a staff underwriting and servicing workspace, and "
                "e-signature — integrated with your core banking and credit-data providers, with "
                "a complete audit trail."
            ),
        },
    },

    # ----- Managed Services & Security -----------------------------------
    {
        "id": "managed-services",
        "line": "managed-services",
        "name": "Application Managed Services",
        "tagline": "We keep your software healthy so your team can focus.",
        "summary": (
            "ongoing operation, support, monitoring, and enhancement of an existing application "
            "under a defined service-level agreement"
        ),
        "target_industries": ["healthcare", "financial services", "government", "manufacturing", "retail", "education", "nonprofit"],
        "capabilities": [
            "24/7 monitoring and incident response",
            "Tiered support with defined SLAs",
            "Patching, updates, and dependency management",
            "Backlog of enhancements and small changes",
            "Performance and cost optimization",
            "Regular service reviews and reporting",
        ],
        "typical_requirements": [
            "Ongoing support and maintenance of an application",
            "Defined service levels and response times",
            "Proactive monitoring and incident response",
            "Regular patching and updates",
            "A path for enhancements and small changes",
            "Transparent reporting on service performance",
        ],
        "integrations": ["the application's cloud environment", "monitoring/alerting and ticketing tools", "the identity provider (SSO)"],
        "compliance": ["SOC 2", "ISO/IEC 27001"],
        "differentiators": [
            "A named support lead who knows your system",
            "Enhancements included, not just break-fix",
        ],
        "pricing_model": "Monthly retainer by service tier",
        "price_low": 120_000,
        "price_high": 480_000,
        "timeline_months": 12,
        "success_metrics": [
            "service levels met or exceeded each period",
            "incidents resolved within target response times",
            "a steady stream of enhancements delivered",
        ],
        "snippets": {
            "understanding": (
                "You have software that needs to stay reliable, secure, and improving, but you "
                "don't want to staff a full team to run it. You need a dependable managed-service "
                "partner with real service levels."
            ),
            "solution": (
                "We will operate and support your application under a defined SLA: 24/7 "
                "monitoring and incident response, regular patching, tiered support with a named "
                "lead, and a running backlog of enhancements — with transparent service reviews "
                "and reporting."
            ),
        },
    },
    {
        "id": "security-compliance",
        "line": "managed-services",
        "name": "Security & Compliance Services",
        "tagline": "Find and fix risk before it finds you.",
        "summary": (
            "assessment and hardening of applications and infrastructure against security risk, "
            "with support for compliance frameworks such as SOC 2 and HIPAA"
        ),
        "target_industries": ["healthcare", "financial services", "government", "manufacturing", "retail", "education"],
        "capabilities": [
            "Security assessment of applications and infrastructure",
            "Penetration testing and remediation guidance",
            "Secure architecture and code review",
            "Compliance readiness (SOC 2, HIPAA, and similar)",
            "Identity, access, and secrets hardening",
            "Security monitoring and incident-response planning",
        ],
        "typical_requirements": [
            "Assess applications and infrastructure for security risk",
            "Perform penetration testing and remediation",
            "Review architecture and code for vulnerabilities",
            "Prepare for a compliance framework (e.g. SOC 2, HIPAA)",
            "Harden identity, access, and secrets management",
            "Establish security monitoring and incident response",
        ],
        "integrations": ["the application and cloud environment under review", "the identity provider (SSO)", "security monitoring / SIEM tooling"],
        "compliance": ["SOC 2", "ISO/IEC 27001", "HIPAA-aligned practices"],
        "differentiators": [
            "Findings come with prioritized, actionable remediation — not just a report",
            "Engineering-led: the people who assess can help you fix",
        ],
        "pricing_model": "Fixed price per assessment, or retainer",
        "price_low": 90_000,
        "price_high": 350_000,
        "timeline_months": 4,
        "success_metrics": [
            "critical and high findings remediated",
            "compliance readiness demonstrably improved",
            "security monitoring and incident response in place",
        ],
        "snippets": {
            "understanding": (
                "You need confidence that your applications and infrastructure can withstand "
                "attack and stand up to a compliance audit — with a clear, prioritized path to "
                "fix whatever is found."
            ),
            "solution": (
                "We will assess your applications and infrastructure, run penetration testing, "
                "review architecture and code, and deliver prioritized, actionable remediation. "
                "We support readiness for frameworks such as SOC 2 and HIPAA and help stand up "
                "security monitoring and incident response."
            ),
        },
    },
]
