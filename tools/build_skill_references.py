#!/usr/bin/env python3
"""Regenerate the skill's bundled reference files from the catalog.

The skill is deliberately thin on product data. Under the hybrid split:

- **The skill carries** what it needs to *match* an RFP to an offering, plus the
  approved language that must be reused verbatim (positioning snippets and the
  answer library). These are small, stable, and fidelity-critical — a paraphrased
  SLA or certification claim is a contractual problem, so they can't come back
  through semantic retrieval.
- **The knowledge base carries** what's large, volatile, or evidence-bearing:
  full offering datasheets, past performance and named references, and pricing
  guides. Those are Word/PDF documents under `knowledge-base/`, pointed at
  Copilot Studio "Knowledge" or Cowork "Sources".

Run after editing `rfp-automation-kit/rfpkit/catalog_data.py`, which remains the
single source of truth for both halves:

    python tools/build_skill_references.py
"""

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SKILL = REPO / ".claude" / "skills" / "rfp-response"
sys.path.insert(0, str(REPO / "rfp-automation-kit"))


def build_index() -> str:
    from rfpkit.catalog_data import OFFERINGS, PRODUCT_LINES, VENDOR

    out = ["# Aventra Software Group — offering index\n"]
    out.append(
        "Enough about every offering to match an incoming RFP to the right one and "
        "to write a grounded first draft. **Full detail lives in the knowledge "
        "base** — see `Aventra-<Offering>-Datasheet` for complete capabilities, "
        "integrations, differentiators, and success measures; "
        "`Aventra-Past-Performance-and-References` for case studies and named "
        "references; `Aventra-Pricing-and-Engagement-Models` for current "
        "commercial terms.\n"
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
        "requirement isn't covered here, by an offering's positioning language, or "
        "by the knowledge base, flag it rather than inventing an answer.\n"
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


def main():
    refs = SKILL / "references"
    refs.mkdir(parents=True, exist_ok=True)

    # The per-offering files are superseded by knowledge-base datasheets.
    legacy = refs / "offerings"
    if legacy.exists():
        import shutil
        shutil.rmtree(legacy)
        print("removed references/offerings/ (now knowledge-base datasheets)")

    (refs / "catalog.md").write_text(build_index(), encoding="utf-8")
    (refs / "answer-library.md").write_text(build_answer_library(), encoding="utf-8")

    companions = [p for p in SKILL.rglob("*")
                  if p.is_file() and p.name != "SKILL.md" and "evals" not in p.parts]
    print(f"wrote references/catalog.md ({len(build_index().splitlines())} lines)")
    print(f"wrote references/answer-library.md")
    print(f"skill companion files (excl. evals/): {len(companions)} / 20")


if __name__ == "__main__":
    main()
