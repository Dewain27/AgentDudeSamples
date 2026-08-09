#!/usr/bin/env python3
"""RFP Automation Kit — command-line entry point.

A catalog of a fictional software vendor's product lines and offerings, with a
sample RFP request and RFP response for every offering, plus a starter
automation layer that assembles responses from a reusable answer library.

Commands
--------
    python generate.py list                 List product lines and offerings.
    python generate.py build                Generate samples for every offering.
    python generate.py build --offering ID  Generate samples for one offering.
    python generate.py pdf                  Render every sample as a formatted PDF.
    python generate.py pdf --offering ID    Render PDFs for one offering.
    python generate.py export               Write data/catalog.json (machine-readable).
    python generate.py answer "QUESTION"    Auto-match an RFP question to a library answer.
    python generate.py draft --offering ID  Assemble an automated draft from the offering's requirements.

Everything produced is fictional and for demonstration only.
"""

import argparse
import json
import sys
from pathlib import Path

from rfpkit import automation, models
from rfpkit.catalog_data import OFFERINGS, PRODUCT_LINES, RESPONSE_LIBRARY, VENDOR
from rfpkit.render_request import render as render_request
from rfpkit.render_response import render as render_response

ROOT = Path(__file__).resolve().parent


# ---------------------------------------------------------------------------
# list
# ---------------------------------------------------------------------------

def cmd_list(args):
    print(f"{VENDOR['name']} — product catalog\n")
    by_line = {}
    for o in OFFERINGS:
        by_line.setdefault(o["line"], []).append(o)
    for line_key, line in PRODUCT_LINES.items():
        offerings = by_line.get(line_key, [])
        print(f"■ {line['name']}")
        print(f"  {line['summary']}")
        for o in offerings:
            inds = ", ".join(o["target_industries"])
            print(f"    - {o['id']:<22} {o['name']}")
            print(f"      {' ':22} industries: {inds}")
        print()
    print(f"{len(OFFERINGS)} offerings across {len(PRODUCT_LINES)} product lines.")


# ---------------------------------------------------------------------------
# build
# ---------------------------------------------------------------------------

def _write(path: Path, content: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _offering_json(offering: dict) -> str:
    ctx = models.derive_context(offering)
    payload = {
        "offering": offering,
        "product_line": models.product_line(offering["line"]),
        "rfp_context": {
            "rfp_id": ctx["rfp_id"],
            "buyer_name": ctx["buyer_name"],
            "industry": ctx["industry"],
            "issued_date": ctx["issued_date"].isoformat(),
            "proposals_due": ctx["proposals_due"].isoformat(),
        },
    }
    return json.dumps(payload, indent=2)


def cmd_build(args):
    out = Path(args.out)
    targets = OFFERINGS
    if args.offering:
        targets = [models.offering_by_id(args.offering)]

    count = 0
    for o in targets:
        folder = out / o["line"] / o["id"]
        _write(folder / "rfp-request.md", render_request(o))
        _write(folder / "rfp-response.md", render_response(o))
        _write(folder / "offering.json", _offering_json(o))
        print(f"built {folder.relative_to(ROOT) if folder.is_relative_to(ROOT) else folder}/")
        count += 1
    print(f"\nGenerated request + response + offering.json for {count} offering(s) in {out}/")


# ---------------------------------------------------------------------------
# pdf
# ---------------------------------------------------------------------------

def cmd_pdf(args):
    from rfpkit import render_pdf

    out = Path(args.out)
    targets = [models.offering_by_id(args.offering)] if args.offering else OFFERINGS

    # Render the Markdown fresh so PDFs never lag behind the catalog.
    try:
        with render_pdf.PdfSession() as session:
            count = 0
            for o in targets:
                ctx = models.derive_context(o)
                folder = out / o["line"] / o["id"]
                for kind, renderer in (("request", render_request), ("response", render_response)):
                    label = f"{ctx['rfp_id']} · {o['name']}"
                    path = folder / f"rfp-{kind}.pdf"
                    session.render(renderer(o), path, kind, label)
                    count += 1
                print(f"pdf  {folder}/rfp-request.pdf, rfp-response.pdf")
            print(f"\nRendered {count} PDFs for {len(targets)} offering(s) in {out}/")
    except render_pdf.MissingPdfDependencies as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


# ---------------------------------------------------------------------------
# export (machine-readable catalog for the automation implementation)
# ---------------------------------------------------------------------------

def cmd_export(args):
    catalog = {
        "vendor": VENDOR,
        "product_lines": PRODUCT_LINES,
        "response_library": RESPONSE_LIBRARY,
        "offerings": OFFERINGS,
    }
    path = Path(args.out)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(catalog, indent=2), encoding="utf-8")
    print(f"wrote {path}  ({len(OFFERINGS)} offerings, {len(RESPONSE_LIBRARY)} library blocks)")


# ---------------------------------------------------------------------------
# answer (demo the automation matcher on a single question)
# ---------------------------------------------------------------------------

def cmd_answer(args):
    offering = models.offering_by_id(args.offering) if args.offering else None
    m = automation.match_question(args.question)
    print(f"Q: {args.question}")
    if m.matched:
        print(f"→ matched topic: {m.topic}  (score {m.score:g})")
        print(f"\n{automation.answer_question(args.question, offering)}")
    else:
        print("→ no confident library match — route to a subject-matter expert.")


# ---------------------------------------------------------------------------
# draft (assemble an automated draft from an offering's typical requirements)
# ---------------------------------------------------------------------------

def cmd_draft(args):
    offering = models.offering_by_id(args.offering)
    questions = args.questions or offering["typical_requirements"]
    print(f"Automated draft for '{offering['name']}' ({offering['id']})\n")
    cov = automation.coverage(questions)
    print(f"Coverage: {cov['answered']}/{cov['total']} auto-answered ({cov['coverage_pct']}%)\n")
    for m in automation.draft_response(offering, questions):
        print(f"• {m.question}")
        if m.matched:
            ans = automation.answer_question(m.question, offering)
            print(f"    [{m.topic}] {ans}\n")
        else:
            print("    [UNMATCHED — needs a human answer]\n")


# ---------------------------------------------------------------------------

def build_parser():
    p = argparse.ArgumentParser(
        description="RFP Automation Kit — catalog, samples, and response automation.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    sub = p.add_subparsers(dest="command", required=True)

    sub.add_parser("list", help="List product lines and offerings.")

    b = sub.add_parser("build", help="Generate sample request+response for offerings.")
    b.add_argument("--out", default="samples", help="Output directory (default: samples).")
    b.add_argument("--offering", help="Build only this offering id.")

    pf = sub.add_parser("pdf", help="Render samples as formatted PDFs (needs requirements-pdf.txt).")
    pf.add_argument("--out", default="samples", help="Output directory (default: samples).")
    pf.add_argument("--offering", help="Render only this offering id.")

    e = sub.add_parser("export", help="Write the machine-readable catalog JSON.")
    e.add_argument("--out", default="data/catalog.json", help="Output path (default: data/catalog.json).")

    a = sub.add_parser("answer", help="Auto-match a single RFP question to a library answer.")
    a.add_argument("question", help="The RFP question text.")
    a.add_argument("--offering", help="Prefer this offering's overrides where they apply.")

    d = sub.add_parser("draft", help="Assemble an automated draft for an offering.")
    d.add_argument("--offering", required=True, help="Offering id to draft for.")
    d.add_argument("--questions", nargs="*", help="Custom questions (default: the offering's typical requirements).")

    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    handlers = {
        "list": cmd_list,
        "build": cmd_build,
        "pdf": cmd_pdf,
        "export": cmd_export,
        "answer": cmd_answer,
        "draft": cmd_draft,
    }
    try:
        handlers[args.command](args)
    except (KeyError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
