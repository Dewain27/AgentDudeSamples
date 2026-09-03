#!/usr/bin/env python3
"""Contribute an ANONYMIZED actual back to the shipped baseline.

Author: Dewain Robinson

Opens a pull request adding one small record to the repo's community
calibration set, so installs with no local history get a better fallback than
published population averages.

    python contribute.py est_20260903T101500_a1b2c3

TWO DESIGN RULES, both load-bearing:

1. ALLOWLIST, NOT REDACTION. The payload is built by copying named fields into
   a fresh object. Nothing is included unless it appears in ALLOWLIST, so a
   field added to the ledger later cannot leak by someone forgetting to strip
   it. Redaction fails open; an allowlist fails closed.

2. CONSENT EVERY TIME. No default-yes, no --yes flag, no remembered consent.
   The complete payload is printed and a specific phrase must be typed. A
   merged record cannot be recalled from a public repository's history.

Deliberately NOT in the payload: project names, file paths, session ids,
prompt or response content, dollar amounts (they can expose negotiated rates),
org identifiers, usernames, exact dates -- and no author attribution, because
naming the contributor would defeat the anonymization.
"""

__author__ = "Dewain Robinson"

import argparse
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import calibrate  # noqa: E402

#: The complete set of fields a contribution may contain. Nothing else ships.
ALLOWLIST = (
    "schema",
    "contributed",
    "size",
    "files",
    "unknowns",
    "brownfield",
    "estimated_turns",
    "actual_turns",
    "ratio",
    "model_tier",
    "cache_hit_rate_band",
    "harness",
)

SCHEMA = 1
CONSENT_PHRASE = "contribute"
REPO = "Dewain27/AgentDudeSamples"
COMMUNITY_DIR = "samples/Build Work Estimator/calibration/community"

CACHE_BANDS = ((0.50, "0-50"), (0.75, "50-75"), (0.90, "75-90"),
               (0.95, "90-95"), (1.01, "95-100"))
DOMINANT_SHARE = 0.6


class ContributeError(Exception):
    """Raised for input the user must fix."""


def band_cache_hit_rate(rate):
    """Coarsen a cache hit rate into a band. Exact values are not shared."""
    try:
        value = float(rate or 0.0)
    except (TypeError, ValueError):
        value = 0.0
    for ceiling, label in CACHE_BANDS:
        if value < ceiling:
            return label
    return CACHE_BANDS[-1][1]


def model_tier(model_mix):
    """Collapse a model mix into a family name. Never a specific model id."""
    if not model_mix:
        return "unknown"
    families = {}
    for model, share in model_mix.items():
        name = str(model or "")
        if "opus" in name:
            family = "opus"
        elif "sonnet" in name:
            family = "sonnet"
        elif "haiku" in name:
            family = "haiku"
        elif "fable" in name or "mythos" in name:
            family = "opus"
        else:
            continue
        families[family] = families.get(family, 0.0) + float(share or 0.0)
    if not families:
        return "unknown"
    top, share = max(families.items(), key=lambda kv: kv[1])
    return top if share >= DOMINANT_SHARE else "mixed"


def build_record(entry, profile):
    """Construct the contribution payload by allowlist.

    Every value below is derived explicitly. There is no dict copy, no
    ``**entry``, and no iteration over the source object -- that is the point.
    """
    actual = entry.get("actual")
    if not actual or not actual.get("turn_ratio"):
        raise ContributeError(
            "This estimate has no recorded actual yet. Run record_actual.py "
            "first -- there is nothing useful to contribute without one."
        )

    predicted = entry.get("predicted") or {}
    items = predicted.get("items") or []
    if not items:
        raise ContributeError("Estimate has no items; nothing to contribute.")

    buckets = [i.get("bucket") for i in items if i.get("bucket")]
    largest = max(buckets, key=lambda b: [row[0] for row in calibrate.BUCKETS].index(b)) \
        if buckets else "unknown"

    manifest = entry.get("manifest") or {}
    harness = str(((manifest.get("copilot") or {}).get("harness")) or "none")
    if harness not in ("none", "standard", "github-copilot"):
        harness = "none"

    record = {
        "schema": SCHEMA,
        # Month precision. An exact date narrows the field of who this is.
        "contributed": str(entry.get("generated", ""))[:7],
        "size": largest,
        "files": int(sum(int(i.get("files") or 0) for i in items)),
        "unknowns": int(max([int(i.get("unknowns") or 0) for i in items] or [0])),
        "brownfield": bool(any(i.get("brownfield") for i in items)),
        "estimated_turns": int(sum(int(i.get("turns") or 0) for i in items)),
        "actual_turns": int(actual.get("actual_turns") or 0),
        "ratio": round(float(actual.get("turn_ratio") or 0.0), 4),
        "model_tier": model_tier((profile or {}).get("model_mix")),
        "cache_hit_rate_band": band_cache_hit_rate(
            (profile or {}).get("cache_hit_rate")),
        "harness": harness,
    }

    # Belt and braces: prove the shape before it can ever be written.
    extra = set(record) - set(ALLOWLIST)
    if extra:
        raise ContributeError(
            "internal error: fields outside the allowlist: %s"
            % ", ".join(sorted(extra)))
    return record


def render_record(record):
    """YAML-ish rendering of the payload. Field lines only -- no prose."""
    lines = []
    for key in ALLOWLIST:
        value = record[key]
        if isinstance(value, bool):
            value = "true" if value else "false"
        lines.append("%s: %s" % (key, value))
    return "\n".join(lines)


def consent_text(record):
    return (
        "\n"
        "This will open a PUBLIC pull request against %s.\n"
        "Once merged it cannot be recalled from that repository's history.\n"
        "\n"
        "This is the COMPLETE payload. Nothing else is sent:\n"
        "\n"
        "%s\n"
        "\n"
        "No project names, file paths, session ids, dollar amounts, or exact\n"
        "dates are included, and the record is not attributed to you.\n"
        % (REPO, "\n".join("    " + l for l in render_record(record).splitlines()))
    )


def interpret_consent(answer):
    """Only the exact phrase counts. 'y' and 'yes' are deliberately not enough."""
    return str(answer or "").strip().lower() == CONSENT_PHRASE


def _prompt_confirm(text):
    print(text)
    answer = input("Type '%s' to open the pull request, anything else to "
                   "cancel: " % CONSENT_PHRASE)
    return interpret_consent(answer)


def _run(argv):
    return subprocess.run(argv, check=True, capture_output=True, text=True)


def submit(entry, profile, confirm=None, runner=None, out_dir=None,
           branch=None):
    """Build, confirm, then write and offer the record upstream.

    Nothing is written and nothing is executed unless `confirm` returns True.
    """
    record = build_record(entry, profile)
    confirm = confirm or _prompt_confirm

    if not confirm(consent_text(record)):
        return {"status": "declined", "record": record, "path": None}

    runner = runner or _run
    filename = "%s-%s-%s.yaml" % (record["contributed"], record["size"],
                                 str(abs(hash(record["ratio"])))[:6])

    if out_dir is None:
        return {"status": "confirmed", "record": record, "path": None,
                "filename": filename}

    if not os.path.isdir(out_dir):
        os.makedirs(out_dir)
    path = os.path.join(out_dir, filename)
    with open(path, "w") as fh:
        fh.write("# Anonymized build calibration record\n")
        fh.write("# Contributed via contribute.py -- allowlist fields only\n")
        fh.write(render_record(record))
        fh.write("\n")

    result = {"status": "written", "record": record, "path": path,
              "filename": filename}

    if _have_gh():
        branch = branch or ("calibration/%s-%s" % (record["contributed"],
                                                   record["size"]))
        try:
            runner(["gh", "repo", "fork", REPO, "--remote=false", "--clone=false"])
        except Exception:
            pass  # already forked, or fork not required
        try:
            runner(["git", "checkout", "-b", branch])
            runner(["git", "add", path])
            runner(["git", "commit", "-m",
                    "Add anonymized calibration record (%s, %s)"
                    % (record["size"], record["contributed"])])
            runner(["git", "push", "-u", "origin", branch])
            runner(["gh", "pr", "create", "--repo", REPO,
                    "--title", "Calibration: %s build, ratio %.2fx"
                    % (record["size"], record["ratio"]),
                    "--body", "Anonymized build calibration record.\n\n```yaml\n%s\n```"
                    % render_record(record)])
            result["status"] = "submitted"
        except Exception as exc:
            result["status"] = "written"
            result["error"] = str(exc)
    return result


def _have_gh():
    try:
        subprocess.run(["gh", "auth", "status"], check=True,
                       capture_output=True)
        return True
    except Exception:
        return False


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("estimate_id")
    ap.add_argument("--ledger", default=None)
    ap.add_argument("--profile", default=None)
    ap.add_argument("--out-dir", default=None)
    args = ap.parse_args(argv)

    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import record_actual  # noqa: E402

    try:
        ledger = record_actual.load_ledger(args.ledger)
        entry = record_actual.find_estimate(ledger, args.estimate_id)
        profile = calibrate.load_profile(args.profile)
        out_dir = args.out_dir or COMMUNITY_DIR
        result = submit(entry, profile, out_dir=out_dir)
    except (ContributeError, record_actual.RecordError) as exc:
        print("ERROR  %s" % exc, file=sys.stderr)
        return 1

    if result["status"] == "declined":
        print("Cancelled. Nothing was written and nothing was sent.")
        return 0
    if result["status"] == "submitted":
        print("Pull request opened. Thank you -- this improves the baseline "
              "for installs with no history of their own.")
        return 0

    print("Record written to %s" % result["path"])
    if result.get("error"):
        print("Could not open the pull request automatically: %s"
              % result["error"])
    print("\nTo submit it manually:")
    print("  1. Fork https://github.com/%s" % REPO)
    print("  2. Add the file above under %s/" % COMMUNITY_DIR)
    print("  3. Open a pull request")
    return 0


if __name__ == "__main__":
    sys.exit(main())
