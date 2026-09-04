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
import build_model as build_model_mod  # noqa: E402
import calibrate  # noqa: E402
import environments as env_mod  # noqa: E402
import licensing  # noqa: E402
import miniyaml  # noqa: E402
import rates  # noqa: E402
import specification as spec_mod  # noqa: E402

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
            # Infrastructure and pipeline work is authored once but applied
            # per environment; everything else is authored once.
            "per_environment": bool(entry.get("per_environment", False)),
            # Evaluation cases attributable to this component. When any item
            # declares them, target credits attribute per component instead of
            # arriving as one undifferentiated pool.
            "eval_cases": int(entry.get("eval_cases", 0) or 0),
        })
    return items


def interview(prompt=input, echo=print):
    """Collect a manifest interactively. Reserve is asked and re-asked."""
    echo("")
    echo("Build Work Estimator -- estimates the BUILD, never the run.")
    echo("")
    project = prompt("Project name: ").strip() or "Unnamed build"

    import specification as _spec
    specification = _spec.interview(prompt=prompt, echo=echo)

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

    # Which model does the building. The catalogue is platform-specific:
    # Claude Code runs Anthropic models, GitHub Copilot runs its own. Offering
    # a model the platform cannot run would price a build that cannot happen.
    echo("")
    echo("=" * 68)
    echo("Q1b. Which MODEL will do the building?")
    echo("")
    echo("Model choice changes the price of every token in every turn. Blank")
    echo("means the calibration profile's own mix, which the report discloses.")
    echo("")
    catalogue = sorted(rates.models_for_platform(build_platform))
    for key in catalogue:
        echo("  %s" % key)
    build_model_choice = ""
    while True:
        build_model_choice = prompt("\n  Build model [blank = calibration mix]: ").strip().lower()
        if not build_model_choice:
            build_model_choice = None
            break
        try:
            rates.validate_model_for_platform(build_platform, build_model_choice)
            break
        except ValueError as exc:
            echo("    %s" % str(exc).splitlines()[0])

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
        "specification": specification,
        "build_platform": build_platform,
        "build_model": build_model_choice,
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


def compute(manifest, profile, env_multiplier=1.0):
    """Estimate a Claude Code build. Other platforms route through compute_plan."""
    reserve_pct = validate_reserve(manifest.get("reserve_percent"))
    items = normalise_items(manifest.get("items"))
    index = bucket_index(profile)

    # Which model builds it changes the price of every token in every turn.
    # Only the Claude Code path reprices: compute() is reused to SIZE the
    # GitHub run, where the cost fields are not the ones that ship.
    platform = str(manifest.get("build_platform") or "claude-code").strip().lower()
    model_info = None
    if platform == "claude-code":
        model_info = build_model_mod.resolve(manifest, profile, "claude-code")
        base_per_turn = model_info["cost_per_turn"]
    else:
        base_per_turn = profile["cost_per_main_turn"]
    per_turn = base_per_turn * profile.get("subagent_multiplier", 1.0)

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
        if item["per_environment"]:
            turns *= env_multiplier

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
            "per_environment": item["per_environment"],
            "eval_cases": item["eval_cases"],
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
        # Turn count is a property of the WORK, not of the tool doing it, so
        # it sizes a GitHub Copilot build too -- only the price per turn
        # differs. The report states that this comes from Claude Code
        # calibration when it is used that way.
        "total_turns": int(sum(r["turns"] for r in rows)),
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
        "build_model": model_info,
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
    try:
        specification = spec_mod.normalise(manifest.get("specification"))
        research_review = spec_mod.normalise_review(
            manifest.get("research_review"))
        breakdown_source = spec_mod.normalise_breakdown_source(
            manifest.get("breakdown_source"))
    except spec_mod.SpecificationError as exc:
        raise EstimateError(str(exc))

    try:
        envs = env_mod.normalise(manifest.get("environments"))
    except env_mod.EnvironmentError_ as exc:
        raise EstimateError(str(exc))

    target_cfg = dict(manifest.get("target") or {})
    cycles = max(1, int(target_cfg.get("eval_cycles", 1) or 1))

    # When components declare their own evaluation cases, the target volume is
    # derived from the breakdown rather than asserted as a lump sum -- which is
    # what lets credits attribute back to each component.
    declared_items = normalise_items(manifest.get("items")) \
        if manifest.get("items") else []
    item_eval_cases = sum(i["eval_cases"] for i in declared_items)
    if item_eval_cases:
        target_cfg["eval_test_cases"] = item_eval_cases

    # Azure components describe ONE environment; environments multiply them.
    components = target_cfg.get("azure_components") or []
    explicit = [e for e in envs["environments"] if e["azure_usd"]]
    if explicit:
        target_cfg["azure_components"] = [
            {"name": "%s environment" % e["name"], "usd": e["azure_usd"],
             "note": "per-environment build and test consumption"}
            for e in envs["environments"] if e["azure_usd"]]
    elif components and envs["count"] > 1:
        target_cfg["azure_components"] = [
            dict(c, usd=float(c.get("usd") or 0.0) * envs["count"],
                 note="%s x %d environments"
                      % (c.get("note", "per environment"), envs["count"]))
            for c in components]

    # --- build side -------------------------------------------------------
    if build_key == "claude-code":
        base = compute(manifest, profile, envs["work_multiplier"])
        build_detail = None
        build_currency_total = base["base"]
    else:
        import github_copilot
        gh_cfg = dict(manifest.get("github_copilot") or {})
        sized_from_items = None
        if manifest.get("items") and not gh_cfg.get("interactions"):
            # Size the GitHub Copilot build from the SAME work breakdown the
            # Claude Code path uses, so two estimates of one scenario are
            # actually estimating the same scenario.
            sizing = compute(manifest, profile, envs["work_multiplier"])
            gh_cfg["interactions"] = sizing["total_turns"]
            sized_from_items = {
                "total_turns": sizing["total_turns"],
                "items": sizing["items"],
                "thin_buckets": sizing.get("thin_buckets", []),
                "profile": sizing["profile"],
            }
        try:
            build_detail = github_copilot.compute(gh_cfg, reserve_pct)
        except github_copilot.GitHubCopilotError as exc:
            raise EstimateError(str(exc))
        if sized_from_items:
            build_detail["sized_from_items"] = sized_from_items
            # Same spread that gives the Claude Code build its range: similar
            # work varies in how many turns it actually takes.
            sizing_base = sizing["base"] or 1.0
            for label, key in (("low", "low"), ("high", "high")):
                ratio = sizing[key] / sizing_base
                variant = dict(gh_cfg)
                variant["interactions"] = max(
                    1, int(round(sizing["total_turns"] * ratio)))
                priced = github_copilot.compute(variant, reserve_pct)
                build_detail["%s_units" % label] = priced["total_units"]
                build_detail["%s_dollars" % label] = priced.get(
                    "total_dollars", 0)
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
            targets.append(target_platform.compute_range(
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
        "specification": specification,
        "research_review": research_review,
        "breakdown_source": breakdown_source,
        "environments": envs,
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
        result["build_model"] = base.get("build_model")
    else:
        result["build"] = None
        result["build_model"] = {
            "platform": "github-copilot",
            "declared": {},
            "declared_label": (build_detail or {}).get("build_model")
                              or "not declared",
            "repriced": False,
            "ratio": 1.0,
            "reason": (build_detail or {}).get(
                "model_rate_source", "not declared"),
        }
        sized = (build_detail or {}).get("sized_from_items")
        if sized:
            # The work was sized from the same calibrated turn medians. Turn
            # count is a property of the work, not the tool -- but that is an
            # assumption, and the report must state it rather than imply the
            # figure came from GitHub Copilot history.
            result["profile"] = dict(sized["profile"])
            result["profile"]["sized_from_claude_calibration"] = True
        else:
            result["profile"] = {"source": "not applicable"}

    return _record_totals(result)


def _record_totals(result):
    """Compute and RECORD every figure the report will display.

    The renderer must not compute. Anything it shows has to exist here first,
    because a number the estimator never recorded is a number nobody can
    account for -- and the provenance validator will reject it.
    """
    reserve_pct = result["reserve_percent"]
    build, detail = result.get("build"), result.get("build_detail")
    gh_rate = rates.DOLLARS_PER_GITHUB_AI_CREDIT
    cc_rate = rates.DOLLARS_PER_CREDIT

    if build:
        side = {
            "currency": "USD", "unit": "USD",
            "low": build["low"], "likely": build["base"],
            "high": build["high"], "with_reserve": build["budget_ask"],
            "usd_low": build["low"], "usd_likely": build["base"],
            "usd_high": build["high"], "usd_with_reserve": build["budget_ask"],
            "notional": (build.get("licensing") or {}).get("model") == "seat",
            "sized_from_items": False, "no_range": False,
        }
    else:
        detail = detail or {}
        units = detail.get("total_units", 0) or 0
        reserved = detail.get("budget_units", units)
        low = detail.get("low_units", units)
        high = detail.get("high_units", units)
        side = {
            "currency": "GitHub AI Credits", "unit": "credits",
            "low": low, "likely": units, "high": high,
            "with_reserve": reserved,
            "usd_low": round(low * gh_rate, 2),
            "usd_likely": round(units * gh_rate, 2),
            "usd_high": round(high * gh_rate, 2),
            "usd_with_reserve": round(reserved * gh_rate, 2),
            "notional": (result.get("licensing") or {}).get("model") == "seat",
            "sized_from_items": bool(detail.get("sized_from_items")),
            "no_range": not detail.get("sized_from_items"),
        }

    tgt = {"credits_low": 0.0, "credits_likely": 0.0, "credits_high": 0.0,
           "credits_with_reserve": 0.0, "usd_low": 0.0, "usd_likely": 0.0,
           "usd_high": 0.0, "usd_with_reserve": 0.0}
    for target in result["targets"]:
        if target["target"] == "azure":
            for key in ("low", "likely", "high"):
                tgt["usd_" + key] += target["total_dollars"]
            tgt["usd_with_reserve"] += target["budget_dollars"]
            continue
        span = target.get("range") or {}
        tgt["credits_low"] += span.get("low_credits", target["total_credits"])
        tgt["credits_likely"] += target["total_credits"]
        tgt["credits_high"] += span.get("high_credits", target["total_credits"])
        tgt["credits_with_reserve"] += target["budget_credits"]
        tgt["usd_low"] += span.get("low_dollars", target["total_dollars"])
        tgt["usd_likely"] += target["total_dollars"]
        tgt["usd_high"] += span.get("high_dollars", target["total_dollars"])
        tgt["usd_with_reserve"] += target["budget_dollars"]
    for key in list(tgt):
        tgt[key] = round(tgt[key], 2)

    combined = dict(
        (key, round(side["usd_" + key] + tgt["usd_" + key], 2))
        for key in ("low", "likely", "high", "with_reserve"))

    # Per-component attribution. Only the evaluation line attributes: the rest
    # is exercised across the solution, and splitting it would be invention.
    eval_credits = shared_credits = 0.0
    for target in result["targets"]:
        if target["target"] == "azure":
            continue
        for line in target.get("lines", []):
            if line["label"].startswith("Evaluation runs"):
                eval_credits += line["credits"]
            else:
                shared_credits += line["credits"]

    components = []
    rows = (build or {}).get("items") or []
    total_cases = sum(r.get("eval_cases", 0) for r in rows)
    for row in rows:
        cases = row.get("eval_cases", 0)
        credits = round(eval_credits * cases / total_cases, 2) \
            if total_cases and cases else 0.0
        components.append({
            "name": row["name"], "size": row["size"], "turns": row["turns"],
            "build_cost": row["cost"], "eval_cases": cases,
            "target_credits": credits,
            "combined_usd": round(row["cost"] + credits * cc_rate, 2),
            "per_environment": row.get("per_environment", False),
        })

    result["totals"] = {
        "build": side, "target": tgt, "combined": combined,
        "reserve_percent": reserve_pct,
    }
    result["component_costs"] = {
        "components": components,
        "attributable": bool(total_cases),
        "total_eval_cases": total_cases,
        "eval_credits": round(eval_credits, 2),
        "shared_credits": round(shared_credits, 2),
        "shared_dollars": round(shared_credits * cc_rate, 2),
        "build_total": round(sum(c["build_cost"] for c in components), 2),
        "turns_total": int(sum(c["turns"] for c in components)),
        "attributed_combined": round(
            sum(c["combined_usd"] for c in components), 2),
    }
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
    ap.add_argument("--report", metavar="BASENAME",
                    help="also render the report to BASENAME.md/.pdf, so one "
                         "command goes manifest -> finished deliverable")
    ap.add_argument("--format", default="md",
                    choices=["md", "pdf", "both"],
                    help="report format when --report is used (default: md)")
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
    except (EstimateError, licensing.LicensingError,
            spec_mod.SpecificationError) as exc:
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
    elif not args.report:
        print(payload)

    # Rendering in the same command matters more than it looks. Estimating and
    # reporting used to be two invocations, so "run it" was a SEQUENCE -- and
    # in real sessions the second half kept not happening while the assistant
    # narrated as though it had. One command, one deliverable.
    if args.report:
        import render_report
        written = render_report.write(result, args.report, args.format)
        for path in written:
            print("Wrote %s" % path)
        totals = result.get("totals", {}).get("combined", {})
        if totals:
            print("Likely %s | with reserve %s"
                  % (_money(totals.get("likely")),
                     _money(totals.get("with_reserve"))))
    return 0


def _money(value):
    return "n/a" if value is None else "$%s" % format(float(value), ",.2f")


if __name__ == "__main__":
    sys.exit(main())
