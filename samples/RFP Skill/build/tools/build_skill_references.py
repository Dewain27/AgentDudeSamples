#!/usr/bin/env python3
"""Regenerate the skill's bundled reference files from the catalog.

The skill is **self-contained**: everything it needs to write a grounded
proposal ships inside the package. No knowledge source, no connector, no
external service to stand up — upload one ZIP and it works.

That is a deliberate choice for a catalog this size. Fifteen offerings plus case
studies and pricing comes to 14 companion files and ~90 KB, comfortably inside
the 20-file / 10 MB packaging limits, and bundling buys two things retrieval
can't: the agent reads approved language *verbatim* rather than a paraphrase of
a retrieved chunk, and there is no "knowledge base unreachable" failure mode.

If the content ever outgrows the package — hundreds of past proposals, security
questionnaires, a live rate card — the same generator feeds the Word/PDF
documents under `knowledge-base/`, which can be attached as a knowledge source
instead. That's a build choice, not a redesign.

Run after editing `build/rfp-automation-kit/rfpkit/catalog_data.py`, the single
source of truth:

    python build/tools/build_skill_references.py
"""

import sys
from pathlib import Path

SAMPLE = Path(__file__).resolve().parents[2]
REPO = SAMPLE
SKILL = SAMPLE / "skill" / "rfp-response"
sys.path.insert(0, str(SAMPLE / "build" / "rfp-automation-kit"))


def build_index() -> str:
    from rfpkit.catalog_data import OFFERINGS, PRODUCT_LINES, VENDOR

    out = ["# Aventra Software Group — offering index\n"]
    out.append(
        "Enough about every offering to match an incoming RFP to the right one. "
        "Once you have picked one, open "
        "`references/offerings-<product-line>.md` for its full capabilities, "
        "integrations, differentiators, and success measures.\n"
    )
    out.append(
        f"**Vendor:** {VENDOR['name']} · founded {VENDOR['founded']} · "
        f"{VENDOR['headquarters']} · {VENDOR['employees']} staff  \n"
        f"**Contact:** {VENDOR['email']} · {VENDOR['phone']}  \n"
        f"**Certifications (exhaustive — anything not listed, Aventra does not "
        f"hold):** {', '.join(VENDOR['certifications'])}\n"
    )

    out.append("## All offerings\n")
    out.append("| Offering id | Name | Product line | Indicative range | Months |")
    out.append("| --- | --- | --- | --- | ---: |")
    for o in OFFERINGS:
        out.append(
            f"| `{o['id']}` | {o['name']} | {PRODUCT_LINES[o['line']]['name']} | "
            f"${o['price_low']:,}–${o['price_high']:,} | {o['timeline_months']} |"
        )
    out.append("")

    for line_key, line in PRODUCT_LINES.items():
        out.append(f"\n## {line['name']}\n")
        out.append(f"_{line['summary']}_\n")
        for o in [x for x in OFFERINGS if x["line"] == line_key]:
            out.append(f"### {o['name']} — `{o['id']}`\n")
            out.append(f"{o['tagline']}  ")
            out.append(f"**Scope:** {o['summary']}.  ")
            out.append(f"**Best fit:** {', '.join(o['target_industries'])}.  ")
            out.append(f"**Compliance:** {', '.join(o['compliance'])}.  ")
            out.append(
                f"**Commercials:** {o['pricing_model']} · "
                f"${o['price_low']:,}–${o['price_high']:,} · "
                f"{o['timeline_months']} months full scope.\n"
            )
            out.append("**Matches RFPs asking to:**\n")
            for r in o["typical_requirements"][:4]:
                out.append(f"- {r}")
            out.append("\n**Approved positioning language** — reuse the substance "
                       "verbatim, adapt wording to the buyer's terms.\n")
            out.append(f"- _Understanding:_ {o['snippets']['understanding']}")
            out.append(f"- _Solution:_ {o['snippets']['solution']}\n")

    out.append("\n## Telling close matches apart\n")
    out.append(
        "These are where offering selection goes wrong, so check here before "
        "committing to a match.\n\n"
        "- An RFP naming a system the buyer's own *customers* use — patients, "
        "constituents, members, students — usually wants an **Industry Solutions** "
        "offering, not a generic custom app.\n"
        "- \"Reporting is slow / our numbers disagree\" → `data-warehouse` when they "
        "need one governed source of truth; `bi-dashboards` when the warehouse "
        "exists and the gap is the front end; `data-integration` when the ask is "
        "moving data rather than analysing it.\n"
        "- \"Connect our systems\" → `systems-integration` for internal workflows; "
        "`api-platform` when they want reusable, governed APIs for internal or "
        "partner developers.\n"
        "- \"Replace our old system\" → `legacy-modernization` when the existing "
        "system must keep running during transition; `web-app-platform` for a "
        "clean-sheet build.\n"
        "- Mostly about running software someone already built → "
        "`managed-services`; mostly assessment and hardening → "
        "`security-compliance`.\n"
        "- A large RFP can legitimately span two offerings. Lead with the primary "
        "one and name the second as a separately priced workstream.\n"
    )
    return "\n".join(out) + "\n"


def build_answer_library() -> str:
    from rfpkit.catalog_data import RESPONSE_LIBRARY

    out = ["# Reusable answer library\n"]
    out.append(
        "Pre-approved answers to the questions that recur in almost every RFP. "
        "Reuse these rather than composing new ones — they are the vetted position "
        "Aventra can actually commit to, and rewriting them from memory is how a "
        "proposal ends up promising a service level nobody agreed to.\n\n"
        "Adapt wording to the buyer's phrasing, but keep every commitment "
        "(standards, timeframes, certifications) exactly as written. If a "
        "requirement isn't covered here, by an offering's detail file, or by the "
        "past-performance record, flag it rather than inventing an answer.\n"
    )
    out.append("| Topic key | Covers |")
    out.append("| --- | --- |")
    for k, b in RESPONSE_LIBRARY.items():
        out.append(f"| `{k}` | {b['title']} — {', '.join(b['keywords'][:6])} |")
    out.append("")
    for k, b in RESPONSE_LIBRARY.items():
        out.append(f"\n## {b['title']}  `{k}`\n")
        out.append(f"**Triggers on:** {', '.join(b['keywords'])}\n")
        out.append(f"{b['answer']}\n")
    return "\n".join(out) + "\n"


def build_offering_details() -> dict:
    """Full detail per offering, grouped one file per product line."""
    from rfpkit.catalog_data import OFFERINGS, PRODUCT_LINES

    files = {}
    for line_key, line in PRODUCT_LINES.items():
        out = [f"# {line['name']}\n", f"_{line['summary']}_\n"]
        out.append(
            "Full detail for the offerings in this line. Indicative ranges assume "
            "full scope; quote a fixed fee inside the range that reflects the "
            "scope the RFP actually describes.\n"
        )
        for o in [x for x in OFFERINGS if x["line"] == line_key]:
            out.append(f"\n---\n\n## {o['name']} — `{o['id']}`\n")
            out.append(f"_{o['tagline']}_\n")
            out.append(f"**Scope:** {o['summary']}.  ")
            out.append(f"**Best fit:** {', '.join(o['target_industries'])}.  ")
            out.append(f"**Compliance:** {', '.join(o['compliance'])}.  ")
            out.append(
                f"**Commercials:** {o['pricing_model']} · "
                f"${o['price_low']:,}–${o['price_high']:,} · "
                f"{o['timeline_months']} months.\n"
            )
            out.append("### Capabilities to describe in the proposed solution\n")
            out += [f"- {c}" for c in o["capabilities"]]
            out.append("\n### Requirements this offering answers\n")
            out += [f"- {r}" for r in o["typical_requirements"]]
            out.append("\n### Integrations\n")
            out.append("Name the buyer's actual systems when the RFP identifies "
                       "them; these are the fallback.\n")
            out += [f"- {i}" for i in o["integrations"]]
            out.append("\n### Differentiators\n")
            out += [f"- {d}" for d in o["differentiators"]]
            out.append("\n### Success measures buyers care about\n")
            out.append("Mirror these in the executive summary when the RFP states "
                       "similar goals — it shows you read their objectives.\n")
            out += [f"- {s}" for s in o["success_metrics"]]
            out.append("\n### Approved positioning language\n")
            out.append(f"**Understanding:** {o['snippets']['understanding']}\n")
            out.append(f"**Solution:** {o['snippets']['solution']}\n")
        files[f"offerings-{line_key}.md"] = "\n".join(out) + "\n"
    return files


def build_past_performance() -> str:
    """Case studies, reference policy, and the exhaustive certification list."""
    import sys as _s
    _s.path.insert(0, str(SAMPLE / "build" / "rfp-sample-generator"))
    from rfpgen.company import VENDOR as P
    from rfpkit.catalog_data import VENDOR

    out = ["# Past performance, references, and certifications\n"]
    out.append(
        "Use this for any relevant-experience question. Those typically carry "
        "15–25% of an evaluation scorecard and are the section that most often "
        "comes out thin, because generic capability claims read as having no "
        "actual track record behind them. Cite a concrete engagement instead.\n\n"
        "Match the industry where you can. Where you can't — the buyer is in an "
        "industry with no comparable engagement, or the closest work is the right "
        "industry but the wrong kind of project — say so plainly and lead with "
        "what genuinely is comparable. An evaluator forgives a candid gap far "
        "more readily than a stretched claim they can check.\n"
    )
    for industry, studies in P.case_studies.items():
        out.append(f"\n## {industry.capitalize()}\n")
        out += [f"- {s}" for s in studies]

    out.append("\n## Reference policy\n")
    out += [
        "- At least three references from comparable engagements, matched by "
        "industry and project type, are provided on request.",
        "- References are released only with the client's prior consent, so allow "
        "five business days when a submission requires named contacts.",
        "- Each reference comes with a summary of the work delivered and the "
        "outcomes achieved.",
        "- If a solicitation requires named references *at submission* rather "
        "than on request, flag it — that changes the timeline.",
    ]
    out.append("\n## Certifications\n")
    out += [f"- {c}" for c in VENDOR["certifications"]]
    out.append(
        "\n**This list is exhaustive.** A framework not named here is one Aventra "
        "does not hold. Say so plainly rather than implying equivalence with "
        "something adjacent — a stretched certification claim is the fastest way "
        "to lose a bid, and the slowest to recover from.\n"
    )
    out.append("\n## Company profile\n")
    out.append(P.overview + "\n")
    out.append(f"**Representative technologies:** {', '.join(P.tech_stack)}.\n")
    return "\n".join(out) + "\n"


def build_pricing() -> str:
    """Commercial reference: ranges, fee build-up, phases, inclusions."""
    from rfpkit.catalog_data import OFFERINGS

    out = ["# Pricing and engagement models\n"]
    out.append(
        "Quote a fixed fee that sits inside both the buyer's stated budget and "
        "the offering's indicative range.\n"
    )
    out.append("## Indicative ranges\n")
    out.append("| Offering | Pricing model | Range | Months |")
    out.append("| --- | --- | --- | ---: |")
    for o in OFFERINGS:
        out.append(f"| {o['name']} | {o['pricing_model']} | "
                   f"${o['price_low']:,}–${o['price_high']:,} | "
                   f"{o['timeline_months']} |")

    out.append("\n## How a fixed fee is built up\n")
    out.append("Adjust when the solicitation gives you a reason — a data-heavy "
               "engagement carries more migration, a greenfield build less.\n")
    out.append("| Workstream | Share |")
    out.append("| --- | ---: |")
    for label, pct in [("Discovery & solution design", "14%"),
                       ("Development & configuration", "42%"),
                       ("Integrations", "16%"), ("Data migration & setup", "8%"),
                       ("Quality assurance & security testing", "10%"),
                       ("Training, documentation & launch", "6%"),
                       ("Project management", "4%")]:
        out.append(f"| {label} | {pct} |")

    out.append("\n## Delivery phases\n")
    out.append("| Phase | Share of schedule |")
    out.append("| --- | ---: |")
    for label, pct in [("Discovery & Design", "20%"),
                       ("Foundation & Integrations", "25%"), ("Core Build", "30%"),
                       ("Testing & Hardening", "15%"),
                       ("Launch & Stabilization", "10%")]:
        out.append(f"| {label} | {pct} |")
    out.append("\nEach phase ends with a working, demonstrable increment and a "
               "stakeholder review.\n")

    out.append("## Included in the fixed fee\n")
    out += [f"- {x}" for x in [
        "Discovery, design, build, integration, and testing as scoped",
        "Data migration where identified in scope",
        "Accessibility and security review each sprint",
        "Role-based training, documentation, and knowledge transfer",
        "Handover of source code, infrastructure-as-code, and documentation in full",
    ]]
    out.append("\n## Excluded, and quoted separately\n")
    out += [f"- {x}" for x in [
        "Third-party licences and subscriptions, passed through without markup",
        "Ongoing cloud hosting and run costs",
        "Hardware and end-user devices",
        "Post-launch care plan — optional, renewable, quoted annually",
        "Scope added after discovery, handled through change control",
    ]]
    out.append(
        "\n## When the buyer's budget sits below the range\n"
        "Do not compress full scope to fit the number. Propose a reduced or "
        "phased scope at a price that is genuinely deliverable, state plainly "
        "which functionality is deferred, and price the later phase indicatively "
        "so the buyer can see the whole path. Underbidding to win is how "
        "engagements fail, and buyers who set a hard cap usually expect to be "
        "told what it buys.\n"
    )
    return "\n".join(out) + "\n"


def main():
    refs = SKILL / "references"
    refs.mkdir(parents=True, exist_ok=True)

    legacy = refs / "offerings"
    if legacy.exists():
        import shutil
        shutil.rmtree(legacy)

    (refs / "catalog.md").write_text(build_index(), encoding="utf-8")
    (refs / "answer-library.md").write_text(build_answer_library(), encoding="utf-8")
    for name, body in build_offering_details().items():
        (refs / name).write_text(body, encoding="utf-8")
    (refs / "past-performance.md").write_text(build_past_performance(), encoding="utf-8")
    (refs / "pricing.md").write_text(build_pricing(), encoding="utf-8")

    companions = [p for p in SKILL.rglob("*")
                  if p.is_file() and p.name != "SKILL.md" and "evals" not in p.parts]
    for f in sorted(refs.iterdir()):
        print(f"  {f.stat().st_size/1024:6.1f} KB  references/{f.name}")
    total = sum(p.stat().st_size for p in companions)
    print(f"\nskill is self-contained: {len(companions)} / 20 companion files, "
          f"{total/1024:.0f} KB / 10240 KB")


if __name__ == "__main__":
    main()
