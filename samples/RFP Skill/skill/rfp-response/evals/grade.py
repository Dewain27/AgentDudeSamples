#!/usr/bin/env python3
"""Grade eval runs against the assertions in evals.json.

Checks are deliberately mechanical (string/number/page-count) so the grade is
reproducible and re-runnable across iterations. Each result records evidence so
a human can audit the call rather than trust the boolean.
"""

import argparse
import json
import re
from pathlib import Path

import pypdfium2 as pdfium

# The run workspace is gitignored (large PDFs and viewer HTML); this harness
# lives with the evals so it stays version-controlled and re-runnable.
# <sample>/skill/rfp-response/evals/this.py -> parents[3] is the sample root.
DEFAULT_WS = Path(__file__).resolve().parents[3] / "build" / "eval-runs"
ROOT = DEFAULT_WS / "iteration-1"

# Distinctive fragments of the case studies in
# Aventra-Past-Performance-and-References. These were deliberately removed from
# the skill's bundled index, so their presence is hard evidence that the
# past-performance file was actually read rather than the index paraphrased.
CASE_MARKERS = {
    "eval-0": ["18 paper workflows", "400 caseworkers", "mid-size county",
               "benefits eligibility", "permits-and-licensing"],
    "eval-1": ["6-clinic", "no-show rates by 22", "22%", "40,000 lines",
               "three specialty systems", "patient intake and scheduling portal"],
    "eval-2": ["18 paper workflows", "400 caseworkers", "mid-size county",
               "4 facilities", "OEE", "plant-floor", "benefits eligibility"],
}

# Language used when experience can't be evidenced — the guardrail the skill
# is supposed to fall back on when it cannot evidence a claim.
UNEVIDENCED = re.compile(
    r"(no (named |specific )?(case stud|client reference|reference)"
    r"|references?[^.]{0,60}(not|cannot|unavailable|on request only)"
    r"|unevidenced|no concrete (case|example)|NEEDS SME|not evidenced"
    r"|knowledge base[^.]{0,40}(absent|unavailable|not (connected|available))"
    r"|without (a )?knowledge base|no case studies)", re.I)


def load(run_dir: Path):
    out = run_dir / "outputs"
    docs, resp, pdfs = [], "", []
    for f in out.glob("*"):
        if f.suffix == ".md":
            txt = f.read_text(encoding="utf-8", errors="replace")
            if f.name == "response.md":
                resp = txt
            else:
                docs.append(txt)
        elif f.suffix == ".pdf":
            pdfs.append(f)
    doc = "\n".join(docs)
    pages = 0
    if pdfs:
        try:
            pages = max(len(pdfium.PdfDocument(p)) for p in pdfs)
        except Exception:
            pages = -1
    return doc, resp, pdfs, pages


def money(text):
    """All dollar amounts >= $50k found in the text."""
    vals = []
    for m in re.finditer(r"\$\s?([\d,]{3,})", text):
        try:
            v = int(m.group(1).replace(",", ""))
            if v >= 50_000:
                vals.append(v)
        except ValueError:
            pass
    return vals


def headline_fee(text, lo, hi):
    """Amounts in range that appear near fee/price/total wording."""
    hits = []
    for m in re.finditer(r"\$\s?([\d,]{3,})", text):
        try:
            v = int(m.group(1).replace(",", ""))
        except ValueError:
            continue
        ctx = text[max(0, m.start() - 120): m.end() + 60].lower()
        if lo <= v <= hi and re.search(r"fixed|total|fee|price|proposed", ctx):
            hits.append(v)
    return hits


def has_all(text, terms):
    t = text.lower()
    return [x for x in terms if x.lower() not in t]


def grade(eval_name, run, iteration=1):
    doc, resp, pdfs, pages = load(run)
    both = doc + "\n" + resp
    R = []

    def add(text, passed, evidence):
        R.append({"text": text, "passed": bool(passed), "evidence": str(evidence)[:400]})

    def knowledge_assertions():
        """Added from iteration 2, when product content moved to the knowledge base."""
        key = eval_name[:6]
        hits = [m for m in CASE_MARKERS[key] if m.lower() in both.lower()]
        add("Cites a concrete case study from the knowledge base, not just generic "
            "capability claims", bool(hits), f"case-study markers found: {hits or 'none'}")

        flagged = UNEVIDENCED.search(both)
        add("Experience is either evidenced with a real case study, or explicitly "
            "flagged as unevidenced — never left silently generic",
            bool(hits) or bool(flagged),
            f"evidenced={bool(hits)}; gap flagged={(flagged.group(0)[:90] if flagged else 'no')}")

    if eval_name.startswith("eval-0"):
        add("Matches the request to the constituent-portal offering",
            re.search(r"constituent[- ]portal|Constituent Services|Permitting Portal", both, re.I),
            (re.search(r".{0,80}(constituent[- ]portal|Permitting Portal).{0,80}", both, re.I) or [""])[0] if re.search(r"constituent[- ]portal|Permitting Portal", both, re.I) else "not found")
        nums = [n for n in range(1, 11) if re.search(rf"(^|\|\s*|\b)R?{n}[\.\)\|]", doc, re.M)]
        add("Addresses all 10 numbered requirements", len(nums) >= 10, f"requirement markers found: {nums}")
        miss = has_all(doc, ["ArcGIS", "Tyler", "Okta"])
        add("Names Esri ArcGIS, Tyler Technologies, and Okta", not miss, f"missing: {miss or 'none'}")
        add("Quotes reference number WB-2026-031", "WB-2026-031" in doc, "found" if "WB-2026-031" in doc else "absent")
        add("Cover letter addressed to Rhonda Pike", "Pike" in doc, "found" if "Pike" in doc else "absent")
        fees = headline_fee(doc, 450_000, 900_000)
        add("Fixed fee inside $450,000-$900,000", bool(fees), f"in-range fee mentions: {sorted(set(fees))[:6]}")
        miss = has_all(doc, ["508", "WCAG 2.1 AA"])
        add("Addresses Section 508 and WCAG 2.1 AA", not miss, f"missing: {miss or 'none'}")
        crit = has_all(doc, ["technical approach", "experience", "cost", "team", "timeline"])
        add("Visibly addresses all 5 evaluation criteria", not crit, f"missing: {crit or 'none'}")
        add("A rendered PDF was produced", bool(pdfs), f"{len(pdfs)} pdf(s), {pages} pages")
        if iteration >= 2:
            knowledge_assertions()

    elif eval_name.startswith("eval-1"):
        dw = len(re.findall(r"data warehouse|data-warehouse", both, re.I))
        add("Leads with the data-warehouse offering", dw >= 3, f"'data warehouse' mentions: {dw}")
        # Only an *assertion* of certification counts. Questions and negations
        # ("whether we hold HITRUST", "we do not hold HITRUST") are the correct
        # behaviour, so exclude anything governed by an interrogative/negator.
        claims = []
        for m in re.finditer(
                r"(?:we|aventra)\s+(?:are|is|hold[s]?|maintain[s]?|possess(?:es)?)\s+[^.]{0,40}HITRUST",
                both, re.I):
            lead = both[max(0, m.start() - 60):m.start()].lower()
            if re.search(r"\b(whether|if|not|never|no|unclear|decide|confirm|question)\b", lead):
                continue
            claims.append(m.group(0).replace("\n", " "))
        add("Does NOT claim Aventra holds HITRUST CSF certification",
            not claims, f"affirmative claims: {claims or 'none'}")
        flagged = re.search(r"HITRUST", both, re.I) and re.search(
            r"(do(es)? not (hold|have|meet)|not certified|no HITRUST|NEEDS SME|does not meet|not currently)", both, re.I)
        add("Explicitly flags the HITRUST requirement as not covered", bool(flagged),
            (re.search(r".{0,100}(do(es)? not (hold|have|meet)|not certified|NEEDS SME).{0,100}", both, re.I) or [""])[0])
        add("HITRUST gap surfaced in the closing summary to the user",
            "HITRUST" in resp.upper(), "present in response.md" if "HITRUST" in resp.upper() else "absent from response.md")
        miss = has_all(doc, ["Epic", "Workday", "Kronos", "Premier", "Press Ganey"])
        add("Names all source systems from the RFP", not miss, f"missing: {miss or 'none'}")
        add("Addresses conflicting 'patient encounters' definitions",
            re.search(r"patient encounter", both, re.I), "found" if re.search(r"patient encounter", both, re.I) else "absent")
        fees = headline_fee(doc, 400_000, 850_000)
        add("Fixed fee inside $400,000-$850,000", bool(fees), f"in-range fee mentions: {sorted(set(fees))[:6]}")
        miss = has_all(doc, ["NRHS-2026-114", "Voss"])
        add("Quotes RFP #NRHS-2026-114 and addressed to Angela Voss", not miss, f"missing: {miss or 'none'}")
        add("Acknowledges the buyer's Azure preference",
            re.search(r"azure", both, re.I), "found" if re.search(r"azure", both, re.I) else "absent")
        add("A rendered PDF was produced", bool(pdfs), f"{len(pdfs)} pdf(s), {pages} pages")
        if iteration >= 2:
            knowledge_assertions()

    else:  # eval-2
        parts = [p for p in "ABCDEFGH" if re.search(rf"Part {p}\b", doc)]
        add("Follows the mandated Part A-H structure", len(parts) == 8, f"parts present: {''.join(parts)}")
        statuses = len(re.findall(r"(fully|partially|not)\s+compliant", doc, re.I))
        rs = [n for n in range(1, 12) if re.search(rf"\bR{n}\b", doc)]
        add("Part B compliance table covers R1-R11 with statuses",
            len(rs) == 11 and statuses >= 11, f"R-markers: {len(rs)}/11, compliance statuses: {statuses}")
        add("Matches the mobile-app-suite offering",
            re.search(r"mobile[- ]app[- ]suite|Mobile Application Suite", both, re.I),
            "found" if re.search(r"mobile[- ]app[- ]suite|Mobile Application Suite", both, re.I) else "absent")
        amts = [v for v in money(doc) if v <= 200_000]
        over = [v for v in headline_fee(doc, 180_001, 10_000_000)]
        add("Total quoted price is at or below the $180,000 cap",
            bool(amts) and not [v for v in amts if 180_000 < v <= 200_000],
            f"tender-total candidates <=200k: {sorted(set(amts))[:6]}; above-cap fee mentions: {sorted(set(over))[:4]}")
        ack = re.search(r"(below|under|tight|constrain|exceed).{0,80}(budget|cap|\$180)|(\$180,000|budget).{0,80}(below|under|does not (cover|permit)|insufficient)", both, re.I)
        add("Acknowledges budget is below full scope and proposes phased scope",
            bool(ack) and re.search(r"phase\s*(1|one|2|two)", both, re.I), (ack or [""])[0] if ack else "no acknowledgement found")
        add("States which functionality is deferred to a later phase",
            re.search(r"defer|phase 2|phase two|subsequent phase", both, re.I),
            (re.search(r".{0,90}(defer|Phase 2).{0,90}", both, re.I) or [""])[0])
        off = len(re.findall(r"offline", both, re.I))
        add("Treats mandatory offline operation (R2) as first-class", off >= 5, f"'offline' mentions: {off}")
        miss = has_all(doc, ["Cityworks"])
        ms = re.search(r"entra|microsoft account|microsoft 365|azure ad", both, re.I)
        add("Names Cityworks and Microsoft/Entra accounts", not miss and bool(ms),
            f"missing: {miss or 'none'}; microsoft-identity ref: {'yes' if ms else 'no'}")
        miss = has_all(doc, ["ITT 2026-07", "Nowak"])
        add("Quotes ITT 2026-07 and addressed to Derek Nowak", not miss, f"missing: {miss or 'none'}")
        add("A rendered PDF was produced", bool(pdfs), f"{len(pdfs)} pdf(s), {pages} pages")
        add("Respects the 20-page limit", 0 < pages <= 20, f"{pages} pages")
        if iteration >= 2:
            knowledge_assertions()

    return R


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--iteration", type=int, default=1)
    ap.add_argument("--workspace", default=str(DEFAULT_WS),
                    help="Run workspace holding iteration-<N>/ directories.")
    args = ap.parse_args()
    global ROOT
    ROOT = Path(args.workspace) / f"iteration-{args.iteration}"

    if not ROOT.is_dir():
        print(f"No run outputs at {ROOT}.\n"
              f"Run the evals first, collecting each run's files into\n"
              f"  {ROOT}/<eval-name>/<arm>/outputs/\n"
              f"then re-run this with --iteration {ROOT.name.split('-')[-1]}.")
        return

    summary = {}
    for eval_dir in sorted(ROOT.iterdir()):
        if not eval_dir.is_dir():
            continue
        for arm in ("with_skill", "without_skill"):
            run = eval_dir / arm
            if not (run / "outputs").exists():
                continue
            res = grade(eval_dir.name, run, args.iteration)
            passed = sum(1 for r in res if r["passed"])
            json.dump({"expectations": res, "passed": passed, "total": len(res)},
                      open(run / "grading.json", "w"), indent=2)
            summary[f"{eval_dir.name}/{arm}"] = (passed, len(res))

    print(f"{'run':62} {'score':>8}")
    print("-" * 72)
    for k, (p, t) in summary.items():
        print(f"{k:62} {p:>3}/{t:<3}")
    ws = [v for k, v in summary.items() if k.endswith("with_skill")]
    bs = [v for k, v in summary.items() if k.endswith("without_skill")]
    a = "SKILL (self-contained)" if args.iteration >= 3 else "WITH SKILL"
    b = "BASELINE"
    print("-" * 72)
    if ws:
        print(f"{a:62} {sum(p for p,_ in ws):>3}/{sum(t for _,t in ws):<3}")
    if bs:  # single-arm iterations have no comparison arm
        print(f"{b:62} {sum(p for p,_ in bs):>3}/{sum(t for _,t in bs):<3}")


if __name__ == "__main__":
    main()
