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
import licensing  # noqa: E402
import miniyaml  # noqa: E402
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
    """Read a manifest. Works without PyYAML -- sandboxed hosts have no pip."""
    try:
        with open(path, "r") as fh:
            text = fh.read()
    except (IOError, OSError) as exc:
        raise EstimateError("Could not read manifest %s: %s" % (path, exc))
    try:
        data = miniyaml.load(text) or {}
    except miniyaml.ManifestParseError as exc:
        raise EstimateError("Could not parse manifest %s: %s" % (path, exc))
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

    echo("")
    echo("=" * 68)
    echo("Q1. What are you BUILDING WITH?")
    echo("")
    echo("This is the coding agent that authors the work. Copilot Studio is")
    echo("NOT an option here -- it is a destination, not a build tool.")
    echo("")
    for key in sorted(rates.BUILD_PLATFORMS):
        echo("  %-16s %s" % (key, rates.BUILD_PLATFORMS[key]["currency"]))
    build_platform = ""
    while build_platform not in rates.BUILD_PLATFORMS:
        build_platform = prompt("\n  Build platform: ").strip().lower()
        if build_platform not in rates.BUILD_PLATFORMS:
            echo("    Expected one of: %s"
                 % ", ".join(sorted(rates.BUILD_PLATFORMS)))

    echo("")
    echo("=" * 68)
    echo("Q2. What are you BUILDING ON?")
    echo("")
    echo("Where the agent is deployed, previewed, evaluated and validated.")
    echo("")
    for key in sorted(rates.TARGET_PLATFORMS):
        echo("  %-16s %s" % (key, rates.TARGET_PLATFORMS[key]["currency"]))
    target_platform = ""
    while target_platform not in rates.TARGET_PLATFORMS:
        target_platform = prompt("\n  Target platform: ").strip().lower()
        if target_platform not in rates.TARGET_PLATFORMS:
            echo("    Expected one of: %s"
                 % ", ".join(sorted(rates.TARGET_PLATFORMS)))
    if target_platform == "ai-recommend":
        echo("")
        echo("  Requirements interview needed before this can be estimated.")
        echo("  Agree a concrete target with the user, then re-run with it set.")

    target = {}
    if target_platform in ("copilot-studio", "both"):
        echo("")
        echo("=" * 68)
        echo("Q3. Which TARGET HARNESS?")
        echo("")
        echo("  standard        build, preview, test and evaluation in the")
        echo("                  interface are NOT billed")
        echo("  github-copilot  billed from the moment building starts")
        echo("")
        echo("This one answer moves the target figure between near-zero and")
        echo("the largest line in the estimate, so it is not guessed.")
        harness = ""
        while harness not in rates.HARNESS_BUILD_BILLING or harness == "none":
            harness = prompt("\n  Target harness: ").strip().lower()
            if harness not in rates.HARNESS_BUILD_BILLING or harness == "none":
                echo("    Expected 'standard' or 'github-copilot'.")
        target["harness"] = harness

        echo("")
        echo("Evaluations, remediation and retesting are always planned --")
        echo("an agent build where every evaluation passes first time is not")
        echo("a plan, it is a hope.")
        target["eval_test_cases"] = int(
            prompt("  Evaluation test cases [0]: ").strip() or "0")
        target["eval_repeats"] = int(
            prompt("  Repeats per test set [3]: ").strip() or "3")
        target["eval_cycles"] = int(
            prompt("  Build -> evaluate -> fix cycles to plan [1]: ").strip()
            or "1")

        echo("")
        echo("Human validation happens in the Copilot Studio interface. The")
        echo("hours are used to size test volume -- never priced as labour.")
        target["interactive_test_hours"] = float(
            prompt("  Planned validation hours [0]: ").strip() or "0")

    if target_platform in ("azure", "both"):
        echo("")
        target["azure_build_usd"] = float(
            prompt("  Azure spend during build and test ($) [0]: ").strip()
            or "0")

    echo("")
    echo("=" * 68)
    echo("How is the BUILD PLATFORM licensed? This decides what the number MEANS.")
    echo("")
    echo("  consumption   every unit bills (API/Console, pay-as-you-go)")
    echo("  seat          draws on an allowance already paid for")
    model = ""
    while model not in (licensing.SEAT, licensing.CONSUMPTION):
        model = prompt("\n  Licensing model: ").strip().lower()
        if model not in (licensing.SEAT, licensing.CONSUMPTION):
            echo("    Expected 'seat' or 'consumption'.")

    licence = {"model": model,
               "plan": prompt("  Plan name (optional): ").strip()}
    if model == licensing.SEAT:
        echo("")
        echo("A seat is not free. To attribute a fair share of it to this")
        echo("build, its monthly cost is required.")
        licence["seat_monthly_cost"] = prompt("  Seat cost per month ($): ").strip()
        licence["seats"] = prompt("  Number of seats [1]: ").strip() or "1"
        echo("")
        echo("How much of the allowance period is already committed to other")
        echo("work? 0.0 = this build is the only thing using the seat.")
        licence["other_workload_share"] = prompt("  Other workload share (0-1): ").strip()
        conc = prompt("  Is this build compressed into a short period? [y/N]: ")
        licence["concentrated"] = conc.strip().lower().startswith("y")

    return {
        "project": project,
        "items": items,
        "reserve_percent": reserve,
        "build_platform": build_platform,
        "target_platform": target_platform,
        "target": target,
        "licensing": licence,
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


REMEDIATION_SHARE = 0.25   # each extra eval cycle costs ~25% of the build


def validate_platforms(manifest):
    """Two axes, both required, and they are not the same question.

    build_platform  = what does the AI-assisted building (Claude Code or
                      GitHub Copilot). Decides the build-side currency.
    target_platform = where the result is deployed, previewed, evaluated and
                      validated. Decides the target-side meter.

    Copilot Studio is a TARGET, never a build platform. Microsoft's own VS Code
    extension docs name GitHub Copilot and Claude Code as the harnesses used to
    author Copilot Studio agent components.
    """
    if "build_stack" in manifest and "build_platform" not in manifest:
        raise EstimateError(
            "`build_stack:` has been replaced by two separate keys, because "
            "one value was\ndoing two jobs.\n\n"
            "  build_platform:  %s\n"
            "  target_platform: %s\n\n"
            "Copilot Studio was never a build platform -- it is where the "
            "agent is deployed,\npreviewed, evaluated and validated. The "
            "building happens in a coding agent."
            % (" | ".join(sorted(rates.BUILD_PLATFORMS)),
               " | ".join(sorted(rates.TARGET_PLATFORMS))))

    raw_build = manifest.get("build_platform")
    if raw_build is None:
        raise EstimateError(
            "build_platform is required: %s\n\n"
            "This is what does the building. It is not the same as what you "
            "are building ON."
            % " | ".join(sorted(rates.BUILD_PLATFORMS)))
    raw_target = manifest.get("target_platform")
    if raw_target is None:
        raise EstimateError(
            "target_platform is required: %s\n\n"
            "This is where the agent is deployed, previewed, evaluated and "
            "validated.\nUse `ai-recommend` to have the skill interview for "
            "requirements and propose one."
            % " | ".join(sorted(rates.TARGET_PLATFORMS)))
    try:
        build = rates.build_platform_info(raw_build)
        target = rates.target_platform_info(raw_target)
    except ValueError as exc:
        raise EstimateError(str(exc))

    target_key = str(raw_target).strip().lower()
    if target_key == "ai-recommend":
        raise EstimateError(
            "target_platform is still `ai-recommend`.\n\n"
            "Run the requirements interview, agree a concrete target with the "
            "user, then set\n`target_platform:` to that value. The estimator "
            "will not silently pick one -- the\nchoice changes the "
            "architecture, not just the number."
        )
    return (build, str(raw_build).strip().lower(),
            target, target_key)


def compute(manifest, profile):
    """Estimate a Claude Code build. Other stacks route through compute_stack."""
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


def compute_plan(manifest, profile):
    """Estimate a build across both platforms.

    Build-side and target-side are ADDITIVE, not alternatives: the same
    project spends on both meters at the same time. The evaluation loop ties
    them together -- a failed evaluation on the target sends remediation work
    back to the build platform, and both are re-spent.
    """
    build_info, build_key, target_info, target_key = validate_platforms(manifest)
    reserve_pct = validate_reserve(manifest.get("reserve_percent"))
    licence = licensing.normalise(manifest.get("licensing"))

    target_cfg = dict(manifest.get("target") or {})
    cycles = max(1, int(target_cfg.get("eval_cycles", 1) or 1))

    # --- build side -------------------------------------------------------
    if build_key == "claude-code":
        base = compute(manifest, profile)
        build_detail = None
        build_currency_total = base["base"]
    else:
        import github_copilot
        try:
            build_detail = github_copilot.compute(
                manifest.get("github_copilot"), reserve_pct)
        except github_copilot.GitHubCopilotError as exc:
            raise EstimateError(str(exc))
        base = None
        build_currency_total = build_detail.get("total_units", 0)

    # Remediation: every cycle after the first sends work back to the build
    # platform. An estimate that prices only the first pass is planning for a
    # build where every evaluation passes first time, which does not happen.
    remediation_factor = 1.0 + (cycles - 1) * REMEDIATION_SHARE

    # --- target side ------------------------------------------------------
    import target_platform
    targets = []
    for key in (["copilot-studio", "azure"] if target_key == "both"
                else [target_key]):
        try:
            targets.append(target_platform.compute(
                target_cfg, reserve_pct, target=key))
        except target_platform.TargetPlatformError as exc:
            raise EstimateError(str(exc))

    result = {
        "estimate_id": new_estimate_id(),
        "generated": calibrate._now(),
        "author": manifest.get("author", "Dewain Robinson"),
        "project": manifest.get("project", "Unnamed build"),
        "build_platform": build_key,
        "build_platform_label": build_info["label"],
        "build_currency": build_info["currency"],
        "target_platform": target_key,
        "target_platform_label": target_info["label"],
        "target_currency": target_info["currency"],
        "reserve_percent": reserve_pct,
        "eval_cycles": cycles,
        "remediation_factor": round(remediation_factor, 3),
        "remediation_share": REMEDIATION_SHARE,
        "licensing": licence,
        "build_detail": build_detail,
        "targets": targets,
        "warnings": rates.staleness_warnings(),
    }

    if base is not None:
        # Scale the Claude Code build for remediation across cycles, then
        # re-attribute against the seat allowance on the scaled figure.
        for key in ("base", "low", "high"):
            base[key] = round(base[key] * remediation_factor, 2)
        for row in base["items"]:
            row["cost"] = round(row["cost"] * remediation_factor, 2)
            row["low"] = round(row["low"] * remediation_factor, 2)
            row["high"] = round(row["high"] * remediation_factor, 2)
            row["turns"] = int(round(row["turns"] * remediation_factor))
        base["reserve"] = round(base["base"] * reserve_pct / 100.0, 2)
        base["budget_ask"] = round(base["base"] + base["reserve"], 2)
        base["adequacy"] = {
            "reserve_percent": reserve_pct,
            "budget_ask": base["budget_ask"],
            "high": base["high"],
            "covers_high": base["budget_ask"] >= base["high"],
            "required_percent": round(
                (base["high"] - base["base"]) / base["base"] * 100.0, 1)
            if base["base"] else 0.0,
        }
        base["licensing"] = licensing.attribute(base["base"], licence, profile)
        result["build"] = base
        result["profile"] = base["profile"]
    else:
        result["build"] = None
        result["profile"] = {"source": "not applicable"}

    return result


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
    build = result.get("build") if result.get("targets") is not None else result
    if result.get("targets") is not None:
        targets = [{"target": tgt["target"],
                    "credits": tgt.get("total_credits", 0),
                    "dollars": tgt.get("total_dollars", 0)}
                   for tgt in result["targets"]]
    else:
        targets = []

    if build and build.get("base") is not None:
        predicted = {
            "base": build["base"], "low": build["low"],
            "high": build["high"], "budget_ask": build["budget_ask"],
            "targets": targets,
            "items": [
                {"name": r["name"], "size": r["size"], "bucket": r["bucket"],
                 "files": r["files"], "unknowns": r["unknowns"],
                 "brownfield": r["brownfield"], "turns": r["turns"],
                 "cost": r["cost"]}
                for r in build["items"]
            ],
        }
        profile_source = build.get("profile", {}).get("source", "unknown")
    else:
        detail = result.get("build_detail") or result.get("stack_detail") or {}
        predicted = {
            "unit": detail.get("unit", "unit"),
            "total_units": detail.get("total_units",
                                      detail.get("total_credits")),
            "budget_units": detail.get("budget_units",
                                       detail.get("budget_credits")),
            "targets": targets,
            "items": [],
        }
        profile_source = "not applicable"

    ledger["estimates"].append({
        "estimate_id": result["estimate_id"],
        "generated": result["generated"],
        "project": result["project"],
        "build_platform": result.get("build_platform"),
        "target_platform": result.get("target_platform"),
        "manifest": manifest,
        "predicted": predicted,
        "profile_source": profile_source,
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
    ap.add_argument("--estimate-id", default=None,
                    help="fixed estimate id (deterministic regeneration)")
    ap.add_argument("--generated", default=None,
                    help="fixed generation timestamp (deterministic "
                         "regeneration)")
    ap.add_argument("--no-ledger", action="store_true",
                    help="do not append to the ledger (regeneration/CI)")
    args = ap.parse_args(argv)

    try:
        if args.interactive or not args.manifest:
            manifest = interview()
        else:
            manifest = load_manifest(args.manifest)
        if args.reserve is not None:
            manifest["reserve_percent"] = args.reserve

        profile = calibrate.load_profile(args.profile)
        result = compute_plan(manifest, profile)
    except (EstimateError, licensing.LicensingError) as exc:
        print("ERROR  %s" % exc, file=sys.stderr)
        return 1

    # Fixed id and timestamp make the shipped examples byte-reproducible, so
    # CI can detect drift with a plain diff instead of fuzzy matching.
    if args.estimate_id:
        result["estimate_id"] = args.estimate_id
    if args.generated:
        result["generated"] = args.generated

    if not args.no_ledger:
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
