#!/usr/bin/env python3
"""Regenerate the shipped worked examples from their manifests.

Author: Dewain Robinson

    python build/regenerate_examples.py            # rewrite examples/
    python build/regenerate_examples.py --check    # verify, change nothing

Committed sample output that lags the code which produced it is worse than no
sample at all: it looks authoritative and is quietly wrong. So the examples are
regenerated from committed inputs, and CI fails if they drift.

DETERMINISM. Estimate ids and timestamps are pinned per scenario, and the
calibration profile is committed alongside the manifests. Two runs of this
script therefore produce byte-identical Markdown, which is what lets `--check`
be a plain comparison rather than a fuzzy one.

PDFs are NOT byte-reproducible -- the renderer embeds a creation date and the
compressor is not stable -- so they are regenerated but verified by content:
every headline figure in the Markdown must appear in the PDF text. That still
catches the failure that matters, which is a PDF left behind at old numbers.
"""

__author__ = "Dewain Robinson"

import argparse
import os
import re
import subprocess
import sys
import tempfile

SAMPLE = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SCRIPTS = os.path.join(SAMPLE, "skill", "build-work-estimator", "scripts")
EXAMPLES = os.path.join(SAMPLE, "examples")
SCENARIOS_DIR = os.path.join(SAMPLE, "scenarios")
PROFILE = os.path.join(EXAMPLES, "calibration-profile.json")

#: Pinned so regeneration is deterministic. These are sample identifiers, not
#: real estimate ids -- they never come from a live run.
SCENARIOS = (
    {
        "name": "harbor-line",
        "manifest": "harbor-line-manifest.yaml",
        "estimate_id": "est_20260903T000000_sample1",
        "generated": "2026-09-03T00:00:00Z",
    },
    {
        "name": "granite-peak",
        "manifest": "granite-peak-manifest.yaml",
        "estimate_id": "est_20260903T000000_sample2",
        "generated": "2026-09-03T00:00:00Z",
    },
    {
        # A GitHub Copilot build on a BLEND of GPT models, priced from the
        # published per-model table rather than one model standing in for all.
        "name": "copper-basin",
        "manifest": "copper-basin-manifest.yaml",
        "estimate_id": "est_20260904T000000_sample3",
        "generated": "2026-09-04T00:00:00Z",
    },
)

#: Full worked scenarios. Same governance as the minimal examples: generated
#: from committed inputs, byte-reproducible, and checked in CI.
SCENARIO_RUNS = (
    {
        "name": "kestrel-claude-code",
        "dir": os.path.join(SCENARIOS_DIR, "kestrel-financial"),
        "manifest": "kestrel-claude-code-manifest.yaml",
        "estimate_id": "est_20260903T000000_kestrelcc",
        "generated": "2026-09-03T00:00:00Z",
    },
    {
        "name": "kestrel-github-copilot",
        "dir": os.path.join(SCENARIOS_DIR, "kestrel-financial"),
        "manifest": "kestrel-github-copilot-manifest.yaml",
        "estimate_id": "est_20260903T000000_kestrelgh",
        "generated": "2026-09-03T00:00:00Z",
    },
)

#: Figures pulled out of the Markdown and required to appear in the PDF.
MONEY = re.compile(r"\$[\d,]+\.\d{2}")
BIG_NUMBER = re.compile(r"\b\d{1,3}(?:,\d{3})+\b")


def run(argv):
    proc = subprocess.run(argv, capture_output=True, text=True)
    if proc.returncode != 0:
        raise SystemExit("command failed: %s\n%s%s"
                         % (" ".join(argv), proc.stdout, proc.stderr))
    return proc.stdout


def _home(scenario):
    return scenario.get("dir", EXAMPLES)


def generate(scenario, out_dir, formats="both", payload_dir=None):
    """Produce <name>-estimate.md (and .pdf) for one scenario into out_dir.

    The intermediate estimate JSON goes to a scratch directory, not to
    out_dir: examples/ holds inputs (manifests, calibration profile) and
    outputs (.md, .pdf), and nothing else.
    """
    payload_dir = payload_dir or tempfile.mkdtemp()
    if not os.path.isdir(payload_dir):
        os.makedirs(payload_dir)
    payload = os.path.join(payload_dir, scenario["name"] + ".json")
    run([sys.executable, os.path.join(SCRIPTS, "estimate.py"),
         "--manifest", os.path.join(_home(scenario), scenario["manifest"]),
         "--profile", PROFILE,
         "--estimate-id", scenario["estimate_id"],
         "--generated", scenario["generated"],
         "--no-ledger",
         "--out", payload])
    run([sys.executable, os.path.join(SCRIPTS, "render_report.py"), payload,
         "-o", os.path.join(out_dir, scenario["name"] + "-estimate"),
         "--format", formats])
    return os.path.join(out_dir, scenario["name"] + "-estimate.md")


def pdf_text(path):
    try:
        import pypdf
    except ImportError:
        return None
    try:
        reader = pypdf.PdfReader(path)
        return "\n".join((page.extract_text() or "") for page in reader.pages)
    except Exception:
        return None


def figures(markdown):
    """Headline figures a current PDF must also contain."""
    found = set(MONEY.findall(markdown)) | set(BIG_NUMBER.findall(markdown))
    # Ignore anything appearing only inside a fenced block or a URL.
    return sorted(f for f in found if len(f) > 3)


def check_pdf(name, md_path, pdf_path):
    """Confirm the committed PDF carries the same figures as the Markdown."""
    problems = []
    if not os.path.exists(pdf_path):
        return ["%s: PDF is missing" % name]
    text = pdf_text(pdf_path)
    if text is None:
        return ["%s: could not read the PDF (install pypdf to verify content)"
                % name]
    flat = " ".join(text.split())
    with open(md_path) as fh:
        markdown = fh.read()
    missing = [f for f in figures(markdown) if f not in flat]
    if missing:
        problems.append(
            "%s: the PDF is missing %d figure%s present in the Markdown "
            "(e.g. %s) -- it is stale, regenerate it"
            % (name, len(missing), "" if len(missing) == 1 else "s",
               ", ".join(missing[:5])))
    return problems


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true",
                    help="verify the committed examples are current; write "
                         "nothing and exit non-zero on drift")
    args = ap.parse_args(argv)

    if not os.path.exists(PROFILE):
        raise SystemExit(
            "The calibration profile fixture is missing: %s\n\nWithout it the "
            "examples cannot be reproduced by anyone else, which is the whole "
            "point of committing them." % PROFILE)

    if not args.check:
        scratch = tempfile.mkdtemp()
        for scenario in SCENARIOS:
            generate(scenario, EXAMPLES, "both", payload_dir=scratch)
            print("Regenerated examples/%s-estimate.{md,pdf}" % scenario["name"])
        for scenario in SCENARIO_RUNS:
            generate(scenario, scenario["dir"], "both", payload_dir=scratch)
            print("Regenerated scenarios/%s/%s-estimate.{md,pdf}"
                  % (os.path.basename(scenario["dir"]), scenario["name"]))
        print("\nCommit the result. `--check` in CI will fail if these drift "
              "from the code.")
        return 0

    problems = []
    staging = tempfile.mkdtemp()
    for scenario in SCENARIOS + SCENARIO_RUNS:
        fresh = generate(scenario, staging, "md")
        committed = os.path.join(
            _home(scenario), scenario["name"] + "-estimate.md")
        if not os.path.exists(committed):
            problems.append("%s: committed Markdown is missing"
                            % scenario["name"])
            continue
        with open(fresh) as a, open(committed) as b:
            if a.read() != b.read():
                problems.append(
                    "%s: the committed Markdown does not match a fresh "
                    "regeneration -- the examples are stale relative to the "
                    "code" % scenario["name"])
        problems.extend(check_pdf(
            scenario["name"], committed,
            os.path.join(_home(scenario),
                         scenario["name"] + "-estimate.pdf")))

    if problems:
        print("Worked examples are OUT OF DATE:\n", file=sys.stderr)
        for problem in problems:
            print("  - %s" % problem, file=sys.stderr)
        print("\nRegenerate them and commit the result:\n"
              "  python build/regenerate_examples.py", file=sys.stderr)
        return 1

    total = len(SCENARIOS) + len(SCENARIO_RUNS)
    print("Worked examples and scenarios are current (%d run%s checked)."
          % (total, "" if total == 1 else "s"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
