#!/usr/bin/env python3
"""Generate plugins/build-work-estimator/ from this sample.

Author: Dewain Robinson

    python build/build_plugin.py

The sample is the source of truth; plugins/ is generated. Editing plugins/
directly will be overwritten on the next build.

Authorship is asserted on every generated artifact and the build FAILS if any
is missing, so attribution cannot drift as files are added.
"""

__author__ = "Dewain Robinson"

import argparse
import json
import os
import shutil
import sys

AUTHOR = "Dewain Robinson"
AUTHOR_URL = "https://github.com/Dewain27"
PLUGIN = "build-work-estimator"
VERSION = "1.0.0"
MARKETPLACE = "agentdude-samples"
REPO_URL = "https://github.com/Dewain27/AgentDudeSamples"

DESCRIPTION = (
    "Estimates the work of BUILDING something with an AI coding agent -- "
    "turns, tokens, and cost -- calibrated from your own session history, "
    "with a required contingency reserve, build-time Copilot Credits for "
    "Microsoft work, and Markdown plus PDF reports. Estimates the build, "
    "never the run."
)

HERE = os.path.dirname(os.path.abspath(__file__))
SAMPLE = os.path.abspath(os.path.join(HERE, ".."))
REPO = os.path.abspath(os.path.join(SAMPLE, "..", ".."))

#: Files that must carry the author attribution, and the marker to look for.
AUTHOR_MARKERS = {
    ".py": "__author__ = \"%s\"" % AUTHOR,
    ".md": AUTHOR,
    ".json": AUTHOR,
}


def plugin_root():
    return os.path.join(REPO, "plugins", PLUGIN)


def skill_root():
    return os.path.join(plugin_root(), "skills", PLUGIN)


def clean():
    if os.path.isdir(plugin_root()):
        shutil.rmtree(plugin_root())


def copy_skill():
    src = os.path.join(SAMPLE, "skill", PLUGIN)
    dst = skill_root()
    shutil.copytree(src, dst)
    for root, _dirs, files in os.walk(dst):
        for name in files:
            if name.endswith(".pyc") or name == ".DS_Store":
                os.remove(os.path.join(root, name))


def copy_references():
    refs = os.path.join(skill_root(), "references")
    if not os.path.isdir(refs):
        os.makedirs(refs)
    pairs = [
        ("docs/methodology.md", "methodology.md"),
        ("docs/copilot-credits.md", "rates-copilot-credits.md"),
        ("docs/CONTRIBUTING-CALIBRATION.md", "contributing-calibration.md"),
        ("docs/licensing-and-stacks.md", "licensing-and-stacks.md"),
    ]
    for src_rel, dst_name in pairs:
        src = os.path.join(SAMPLE, src_rel)
        if os.path.exists(src):
            shutil.copyfile(src, os.path.join(refs, dst_name))
    write_anthropic_reference(os.path.join(refs, "rates-anthropic.md"))


def write_anthropic_reference(path):
    sys.path.insert(0, os.path.join(SAMPLE, "skill", PLUGIN, "scripts"))
    import rates

    lines = [
        "# Anthropic rates",
        "",
        "**Author:** %s" % AUTHOR,
        "**Verified:** %s" % rates.ANTHROPIC_VERIFIED,
        "**Source:** %s" % rates.ANTHROPIC_SOURCE,
        "",
        "List price, USD per 1M tokens.",
        "",
        "| Model | Input | Output |",
        "| --- | ---: | ---: |",
    ]
    seen = set()
    for model, (rin, rout) in sorted(rates.ANTHROPIC_RATES.items(),
                                     key=lambda kv: (-kv[1][0], kv[0])):
        key = (rin, rout)
        lines.append("| `%s` | $%.2f | $%.2f |" % (model, rin, rout))
        seen.add(key)
    lines += [
        "",
        "Multipliers applied to the input rate:",
        "",
        "| Token kind | Multiplier |",
        "| --- | ---: |",
        "| Cache read | %.2fx |" % rates.CACHE_READ_MULT,
        "| Cache write, 5 minute TTL | %.2fx |" % rates.CACHE_WRITE_5M_MULT,
        "| Cache write, 1 hour TTL | %.2fx |" % rates.CACHE_WRITE_1H_MULT,
        "",
        "## Published baselines",
        "",
        "Used only when no local session history exists. Source: %s"
        % rates.PUBLISHED_BASELINE_SOURCE,
        "",
        "| Figure | Value |",
        "| --- | ---: |",
        "| Cost per developer per active day | $%.2f |"
        % rates.PUBLISHED_BASELINE["cost_per_developer_active_day"],
        "| Cost per developer per month | $%.0f - $%.0f |"
        % (rates.PUBLISHED_BASELINE["cost_per_developer_month_low"],
           rates.PUBLISHED_BASELINE["cost_per_developer_month_high"]),
        "| 90th percentile per active day | $%.2f |"
        % rates.PUBLISHED_BASELINE["p90_cost_per_active_day"],
        "",
        "> These are population averages published by Anthropic. They are a "
        "fallback, not a\n> measurement of any particular user, and an "
        "estimate built on them is materially\n> less reliable than one built "
        "on measured history.",
        "",
        "**Rates change without notice.** Re-verify against the source links "
        "above; the\nestimator warns when a table is more than 90 days past "
        "its verification date.",
        "",
    ]
    with open(path, "w") as fh:
        fh.write("\n".join(lines))


def copy_assets():
    assets = os.path.join(skill_root(), "assets")
    if not os.path.isdir(assets):
        os.makedirs(assets)
    for name in ("harbor-line-estimate.md", "harbor-line-manifest.yaml",
                 "granite-peak-estimate.md", "granite-peak-manifest.yaml"):
        src = os.path.join(SAMPLE, "examples", name)
        if os.path.exists(src):
            shutil.copyfile(src, os.path.join(assets, name))
    baseline = os.path.join(SAMPLE, "calibration", "baseline.json")
    if os.path.exists(baseline):
        shutil.copyfile(baseline, os.path.join(assets, "baseline.json"))


def write_plugin_json():
    payload = {
        "$schema": "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json",
        "name": PLUGIN,
        "description": DESCRIPTION,
        "version": VERSION,
        "author": {"name": AUTHOR, "url": AUTHOR_URL},
        "repository": REPO_URL,
        "license": "MIT",
        "keywords": ["estimation", "cost", "tokens", "budgeting",
                     "copilot-credits", "build-estimation", "agent-skills"],
    }
    path = os.path.join(plugin_root(), "plugin.json")
    with open(path, "w") as fh:
        json.dump(payload, fh, indent=2)
        fh.write("\n")


def write_plugin_readme():
    text = """# %s

**Author:** %s

Estimates the work of **building** something with an AI coding agent — turns,
tokens, and cost — calibrated from your own session history. Produces Markdown
and PDF reports with a required contingency reserve, and translates Microsoft
work into build-time Copilot Credits.

> ### This estimates the build, not the run
>
> It tells you what it costs to *build* a thing. It says nothing about what that
> thing costs to operate afterwards. For runtime agent consumption, use
> Microsoft's [agent usage estimator](https://microsoft.github.io/copilot-studio-estimator/).

## Install

```
copilot plugin marketplace add Dewain27/AgentDudeSamples
copilot plugin install %s@%s
```

## Try it

```
python scripts/version_check.py
python scripts/calibrate.py --print
python scripts/estimate.py --manifest assets/harbor-line-manifest.yaml --out e.json
python scripts/render_report.py e.json -o estimate --format both
```

A complete worked example is in `assets/harbor-line-estimate.md`.

## Note

This is a **sample**. Its worked example uses Harbor Line Logistics, a fictional
company; every figure in it is invented. It demonstrates *how* to build an
estimator — recalibrate and reprice it for your organization before using it for
real budgeting. Full documentation:
[`samples/Build Work Estimator/`](../../samples/Build%%20Work%%20Estimator/).

> Generated by `build/build_plugin.py` — edit the sample, not this folder.
""" % (PLUGIN, AUTHOR, PLUGIN, MARKETPLACE)
    with open(os.path.join(plugin_root(), "README.md"), "w") as fh:
        fh.write(text)


def update_marketplace():
    path = os.path.join(REPO, ".github", "plugin", "marketplace.json")
    with open(path, "r") as fh:
        data = json.load(fh)

    entry = {
        "name": PLUGIN,
        "source": "plugins/%s" % PLUGIN,
        "description": DESCRIPTION,
        "version": VERSION,
        "author": AUTHOR,
    }
    plugins = data.setdefault("plugins", [])
    changed = True
    for index, existing in enumerate(plugins):
        if existing.get("name") == PLUGIN:
            changed = existing != entry
            plugins[index] = entry
            break
    else:
        plugins.append(entry)

    meta = data.setdefault("metadata", {})
    # Only bump when the entry actually changed. A rebuild that produces an
    # identical manifest must be a no-op, or every build inflates the version
    # and the version gate starts telling users to update to nothing.
    if changed:
        parts = str(meta.get("version", "1.0.0")).split(".")
        while len(parts) < 3:
            parts.append("0")
        parts[1] = str(int(parts[1]) + 1)
        parts[2] = "0"
        meta["version"] = ".".join(parts)

    with open(path, "w") as fh:
        json.dump(data, fh, indent=2)
        fh.write("\n")
    return meta["version"], changed


def assert_authorship():
    """Fail the build if any generated artifact lacks attribution.

    Deliberate exception: contributed calibration records are anonymous by
    design (see docs/CONTRIBUTING-CALIBRATION.md), so nothing under
    calibration/community/ is checked.
    """
    missing = []
    for root, _dirs, files in os.walk(plugin_root()):
        if os.sep + "community" in root:
            continue
        for name in files:
            ext = os.path.splitext(name)[1]
            marker = AUTHOR_MARKERS.get(ext)
            if not marker:
                continue
            path = os.path.join(root, name)
            with open(path, "r", encoding="utf-8", errors="replace") as fh:
                if marker not in fh.read():
                    missing.append(os.path.relpath(path, REPO))
    if missing:
        raise SystemExit(
            "Authorship assertion FAILED. These generated artifacts do not "
            "carry '%s':\n  %s" % (AUTHOR, "\n  ".join(sorted(missing))))
    return True


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--no-marketplace", action="store_true")
    args = ap.parse_args(argv)

    clean()
    copy_skill()
    copy_references()
    copy_assets()
    write_plugin_json()
    write_plugin_readme()
    assert_authorship()

    print("Built plugins/%s" % PLUGIN)
    if not args.no_marketplace:
        version, changed = update_marketplace()
        print("Registered in .github/plugin/marketplace.json "
              "(marketplace version %s%s)"
              % (version, "" if changed else ", unchanged"))
    print("Authorship assertion passed: every artifact carries '%s'." % AUTHOR)
    return 0


if __name__ == "__main__":
    sys.exit(main())
