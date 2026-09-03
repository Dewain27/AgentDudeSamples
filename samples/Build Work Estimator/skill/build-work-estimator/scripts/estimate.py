#!/usr/bin/env python3
"""Estimate the work of BUILDING something with an AI coding agent.

Author: Dewain Robinson

Estimates the build. Never the run. See the sample README for the boundary.

    python estimate.py --manifest estimate.yaml
    python estimate.py --interactive
    python estimate.py --manifest m.yaml --reserve 25   # override the manifest

`reserve_percent` is REQUIRED. There is no default and no skip flag: a build
estimate without a stated contingency is the failure mode this tool exists to
prevent, so it refuses to produce one.
"""

__author__ = "Dewain Robinson"

import argparse
import binascii
import datetime
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import calibrate  # noqa: E402
import rates  # noqa: E402

VALID_SIZES = tuple(calibrate.SIZE_TO_BUCKET)
BROWNFIELD_FACTOR = 1.5
UNKNOWNS_RANGE_STEP = 0.25
MAX_UNKNOWNS = 5
RESERVE_MIN, RESERVE_MAX = 0, 500
CORRECTION_SHRINKAGE_K = 3
CORRECTION_MIN_N = 2


class EstimateError(Exception):
    """Raised for input the user must fix. Message is shown verbatim."""


def ledger_path():
    return os.path.expanduser("~/.claude/build-work-estimator/ledger.json")


def new_estimate_id(now=None):
    now = now or datetime.datetime.utcnow()
    return "est_%s_%s" % (
        now.strftime("%Y%m%dT%H%M%S"),
        binascii.hexlify(os.urandom(3)).decode("ascii"),
    )


# --------------------------------------------------------------------------
# Input
# --------------------------------------------------------------------------

def validate_reserve(value, source="reserve_percent"):
    if value is None:
        raise EstimateError(
            "%s is required and has no default.\n\n"
            "Every estimate must state the contingency reserve carried on top "
            "of it.\nAdd `reserve_percent: <number>` to the manifest, or pass "
            "--reserve <number>.\nA value of 0 is allowed if you genuinely "
            "intend to carry no reserve." % source
        )
    try:
        pct = float(value)
    except (TypeError, ValueError):
        raise EstimateError("%s must be a number, got %r" % (source, value))
    if not (RESERVE_MIN <= pct <= RESERVE_MAX):
        raise EstimateError(
            "%s must be between %d and %d, got %s"
            % (source, RESERVE_MIN, RESERVE_MAX, pct)
        )
    return pct


def load_manifest(path):
    try:
        import yaml
    except ImportError:
        raise EstimateError(
            "PyYAML is required to read a manifest. Install it with "
            "`pip install pyyaml`, or use --interactive."
        )
    try:
        with open(path, "r") as fh:
            data = yaml.safe_load(fh) or {}
    except (IOError, OSError) as exc:
        raise EstimateError("Could not read manifest %s: %s" % (path, exc))
    if not isinstance(data, dict):
        raise EstimateError("Manifest must be a mapping at the top level.")
    return data


def normalise_items(raw_items):
    if not raw_items:
        raise EstimateError("Manifest has no `items:` to estimate.")
    items = []
    for index, entry in enumerate(raw_items, 1):
        if not isinstance(entry, dict):
            raise EstimateError("items[%d] must be a mapping." % index)
        size = str(entry.get("size", "")).strip().lower()
        if size not in VALID_SIZES:
            raise EstimateError(
                "items[%d] has size %r; expected one of: %s"
                % (index, entry.get("size"), ", ".join(VALID_SIZES))
            )
        unknowns = int(entry.get("unknowns", 0) or 0)
        if not (0 <= unknowns <= MAX_UNKNOWNS):
            raise EstimateError(
                "items[%d].unknowns must be 0-%d, got %d"
                % (index, MAX_UNKNOWNS, unknowns)
            )
        items.append({
            "name": entry.get("name") or ("item %d" % index),
            "size": size,
            "files": int(entry.get("files", 0) or 0),
            "unknowns": unknowns,
            "brownfield": bool(entry.get("brownfield", False)),
        })
    return items


def interview(prompt=input, echo=print):
    """Collect a manifest interactively. Reserve is asked and re-asked."""
    echo("")
    echo("Build Work Estimator -- estimates the BUILD, never the run.")
    echo("")
    project = prompt("Project name: ").strip() or "Unnamed build"

    items = []
    echo("")
    echo("Describe each unit of work. Blank name when you're done.")
    while True:
        echo("")
        name = prompt("  Item name (blank to finish): ").strip()
        if not name:
            break
        size = ""
        while size not in VALID_SIZES:
            size = prompt("  Size [%s]: " % "/".join(VALID_SIZES)).strip().lower()
            if size not in VALID_SIZES:
                echo("    Expected one of: %s" % ", ".join(VALID_SIZES))
        files = prompt("  Files touched (0 for research): ").strip() or "0"
        unknowns = prompt("  Unknowns 0-%d [0]: " % MAX_UNKNOWNS).strip() or "0"
        brown = prompt("  Existing codebase? [y/N]: ").strip().lower()
        items.append({
            "name": name, "size": size,
            "files": int(files or 0),
            "unknowns": max(0, min(MAX_UNKNOWNS, int(unknowns or 0))),
            "brownfield": brown.startswith("y"),
        })
    if not items:
        raise EstimateError("No items described; nothing to estimate.")

    echo("")
    echo("Contingency reserve -- REQUIRED. This is the percentage added on top")
    echo("of the estimate for budgeting headroom. There is no default.")
    reserve = None
    while reserve is None:
        raw = prompt("  Reserve %%: ").strip()
        try:
            reserve = validate_reserve(raw if raw else None)
        except EstimateError as exc:
            echo("    " + str(exc).splitlines()[0])
            reserve = None

    ms = prompt("\nDoes this build target Microsoft/Copilot Studio? [y/N]: ")
    return {
        "project": project,
        "items": items,
        "reserve_percent": reserve,
        "microsoft": ms.strip().lower().startswith("y"),
    }


# --------------------------------------------------------------------------
# Model
# --------------------------------------------------------------------------

def bucket_index(profile):
    return dict((row["label"], row) for row in profile.get("buckets", []))


def shrunk_ratio(median_ratio, n, k=CORRECTION_SHRINKAGE_K):
    """Pull an observed correction toward 1.0 in proportion to sample size.

    With one recorded actual, a raw ratio is a sample of size one. Applying it
    undiluted is precisely the over-confidence this estimator exists to avoid.
    """
    if not n:
        return 1.0
    return 1.0 + (median_ratio - 1.0) * (float(n) / (n + k))


def correction_for(profile, bucket):
    entry = (profile.get("corrections") or {}).get(bucket)
    if not entry:
        return 1.0, None
    n = int(entry.get("n", 0) or 0)
    ratio = shrunk_ratio(float(entry.get("median_ratio", 1.0)), n)
    applied = n >= CORRECTION_MIN_N
    info = {
        "bucket": bucket, "n": n,
        "median_ratio": entry.get("median_ratio"),
        "shrunk_ratio": round(ratio, 4),
        "applied": applied,
    }
    return (ratio if applied else 1.0), info


def compute(manifest, profile):
    reserve_pct = validate_reserve(manifest.get("reserve_percent"))
    items = normalise_items(manifest.get("items"))
    index = bucket_index(profile)
    per_turn = profile["cost_per_main_turn"] * profile.get("subagent_multiplier", 1.0)

    rows, corrections = [], []
    base = low = high = 0.0
    for item in items:
        bucket = calibrate.SIZE_TO_BUCKET[item["size"]]
        row = index.get(bucket)
        if row is None:
            raise EstimateError(
                "The calibration profile has no data for size %r. Run "
                "calibrate.py, or choose a size the profile covers: %s"
                % (item["size"], ", ".join(sorted(index)))
            )
        factor, info = correction_for(profile, bucket)
        if info and info not in corrections:
            corrections.append(info)

        turns = row["median_turns"]
        if item["brownfield"]:
            turns *= BROWNFIELD_FACTOR
        turns *= factor

        cost = turns * per_turn
        median = row["median_cost"] or cost or 1.0
        item_low = cost * (row["min_cost"] / median) if median else cost
        item_high = (cost * (row["max_cost"] / median) if median else cost) * \
            (1 + UNKNOWNS_RANGE_STEP * item["unknowns"])

        base += cost
        low += item_low
        high += item_high
        rows.append({
            "name": item["name"], "size": item["size"], "bucket": bucket,
            "files": item["files"], "unknowns": item["unknowns"],
            "brownfield": item["brownfield"], "n": row["n"],
            "turns": round(turns), "cost": round(cost, 2),
            "low": round(item_low, 2), "high": round(item_high, 2),
        })

    reserve = base * reserve_pct / 100.0
    budget = base + reserve
    adequacy = {
        "reserve_percent": reserve_pct,
        "budget_ask": round(budget, 2),
        "high": round(high, 2),
        "covers_high": budget >= high,
        "required_percent": round(((high - base) / base * 100.0), 1) if base else 0.0,
    }

    thin = sorted(set(r["bucket"] for r in rows if 0 < r["n"] < 3))
    return {
        "estimate_id": new_estimate_id(),
        "generated": calibrate._now(),
        "author": manifest.get("author", "Dewain Robinson"),
        "project": manifest.get("project", "Unnamed build"),
        "microsoft": bool(manifest.get("microsoft")),
        "items": rows,
        "base": round(base, 2),
        "low": round(low, 2),
        "high": round(high, 2),
        "reserve": round(reserve, 2),
        "reserve_percent": reserve_pct,
        "budget_ask": round(budget, 2),
        "adequacy": adequacy,
        "corrections": corrections,
        "profile": {
            "source": profile["source"],
            "sessions": profile.get("sessions", 0),
            "generated": profile.get("generated"),
            "date_range": profile.get("date_range"),
            "cost_per_main_turn": profile["cost_per_main_turn"],
        },
        "thin_buckets": thin,
        "warnings": rates.staleness_warnings(),
    }


def append_ledger(result, manifest, path=None):
    """Record the prediction so a later actual can be compared against it."""
    path = path or ledger_path()
    directory = os.path.dirname(path)
    if directory and not os.path.isdir(directory):
        os.makedirs(directory)
    try:
        with open(path, "r") as fh:
            ledger = json.load(fh)
    except (IOError, OSError, ValueError):
        ledger = {"schema": 1, "estimates": []}
    ledger["estimates"].append({
        "estimate_id": result["estimate_id"],
        "generated": result["generated"],
        "project": result["project"],
        "manifest": manifest,
        "predicted": {
            "base": result["base"], "low": result["low"], "high": result["high"],
            "budget_ask": result["budget_ask"],
            "items": [
                {"name": r["name"], "size": r["size"], "bucket": r["bucket"],
                 "files": r["files"], "unknowns": r["unknowns"],
                 "brownfield": r["brownfield"], "turns": r["turns"],
                 "cost": r["cost"]}
                for r in result["items"]
            ],
        },
        "profile_source": result["profile"]["source"],
        "actual": None,
    })
    with open(path, "w") as fh:
        json.dump(ledger, fh, indent=2)
    return path


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--manifest")
    ap.add_argument("--interactive", action="store_true")
    ap.add_argument("--reserve", type=float, default=None,
                    help="reserve %%, overrides the manifest")
    ap.add_argument("--profile", default=None)
    ap.add_argument("--out", default=None, help="write result JSON here")
    args = ap.parse_args(argv)

    try:
        if args.interactive or not args.manifest:
            manifest = interview()
        else:
            manifest = load_manifest(args.manifest)
        if args.reserve is not None:
            manifest["reserve_percent"] = args.reserve

        profile = calibrate.load_profile(args.profile)
        result = compute(manifest, profile)
    except EstimateError as exc:
        print("ERROR  %s" % exc, file=sys.stderr)
        return 1

    append_ledger(result, manifest)
    payload = json.dumps(result, indent=2)
    if args.out:
        with open(args.out, "w") as fh:
            fh.write(payload)
        print("Wrote %s" % args.out)
        print("Estimate id: %s" % result["estimate_id"])
    else:
        print(payload)
    return 0


if __name__ == "__main__":
    sys.exit(main())
