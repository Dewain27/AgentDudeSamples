#!/usr/bin/env python3
"""Package the skill for every supported host.

Author: Dewain Robinson

    python build/build_host_packages.py

Four hosts, three artifacts:

  plugins/build-work-estimator/          GitHub Copilot CLI, Claude Code
                                         (built by build_plugin.py)
  packages/build-work-estimator.zip      Agent Skills standard package --
                                         Copilot Studio and Claude Cowork
  packages/...-cowork-plugin.zip         Microsoft Copilot Cowork (Teams
                                         manifest + icons + skills/)

Two things change for the packaged variants, and both are asserted so an edit
to the source that breaks one fails the build loudly:

1. **Companion-file budget.** The authored skill carries 21 companion files --
   over the documented ceiling of 20, with no headroom. References are
   consolidated and only one worked example is shipped, bringing packages to a
   comfortable size.

2. **PDF rendering.** The bundled renderer drives headless Chromium. Sandboxed
   hosts have no browser and no package installation, but they create documents
   natively -- so packaged instructions tell the agent to use that, keeping the
   script as the shell-environment option.
"""

__author__ = "Dewain Robinson"

import argparse
import json
import os
import re
import shutil
import sys
import uuid
import zipfile

SAMPLE = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
REPO = os.path.abspath(os.path.join(SAMPLE, "..", ".."))
# The plugin build is the canonical generator -- it assembles references and
# assets from docs/ and examples/. Packaging consumes its output so the three
# artifacts cannot drift from one another.
SKILL_SRC = os.path.join(REPO, "plugins", "build-work-estimator", "skills",
                         "build-work-estimator")

NAME = "build-work-estimator"
SHORT_NAME = "Build Work Estimator"
#: Imported, not duplicated. This was its own constant, so bumping the plugin
#: left the Cowork package manifest behind at the old version with nothing
#: checking the two agreed. One source, one bump.
from build_plugin import VERSION  # noqa: E402
AUTHOR = "Dewain Robinson"
ACCENT = "#1F3A5F"

# Documented Agent Skills packaging limits.
MAX_COMPANION_FILES = 20
MAX_FILE_BYTES = 5 * 1024 * 1024
MAX_TOTAL_BYTES = 10 * 1024 * 1024
MAX_NAME_LEN = 64
MAX_DESC_LEN = 1024

# Deterministic id so rebuilds do not churn the manifest.
COWORK_ID = str(uuid.uuid5(uuid.NAMESPACE_URL,
                           "https://github.com/Dewain27/AgentDudeSamples/" + NAME))

# References consolidated for packaging: 5 files -> 2.
# One consolidated reference. The skill grew four modules and hit the
# documented 20-companion ceiling with zero headroom; splitting references
# bought nothing a reader values and cost the budget that new capability needs.
REFERENCE_GROUPS = {
    "reference.md": ["methodology.md", "platforms-and-licensing.md",
                     "rates-anthropic.md", "rates-copilot-credits.md",
                     "contributing-calibration.md"],
}

# Only one worked example ships in packages; both stay in the repo sample.
# SKILL.md already carries the complete manifest shape, so shipping the
# example manifest as well is redundant against a hard file budget.
PACKAGED_ASSETS = ("harbor-line-estimate.md",)

#: The single-command form also asks for a PDF, and this host cannot make one.
#: Rewritten to Markdown for the same reason as the block below -- and asserted
#: rather than best-effort, so a reworded SKILL.md fails the build instead of
#: silently shipping an instruction the sandbox cannot follow.
OLD_ONE_COMMAND = """python scripts/estimate.py --manifest estimate.yaml \\
    --report build-estimate --format both"""

NEW_ONE_COMMAND = """python scripts/estimate.py --manifest estimate.yaml \\
    --report build-estimate --format md"""

OLD_PDF_BLOCK = """```bash
python scripts/render_report.py estimate.json -o build-estimate --format both
```

Writes `.md` and `.pdf`. If the PDF toolchain is missing, the Markdown is still
written and the run succeeds — report the remediation, do not treat it as a
failure."""

NEW_PDF_BLOCK = """```bash
python scripts/render_report.py estimate.json -o build-estimate --format md
```

Writes the Markdown report.

**This host has no browser and no package installation, so do not try to render
the PDF with the bundled script.** It creates documents natively — take the
Markdown the command above produced and generate the PDF with the host's own
document creation. The script's `--format pdf` path exists for shell
environments and will simply report that a browser is unavailable here."""

HOST_NOTE = """
## Running here

This package runs in a sandboxed host. Two differences from a developer machine,
both handled:

- **No session history.** `~/.claude/projects` does not exist here, so
  `calibrate.py` falls back to published baselines. That is expected — but a
  baseline estimate is materially less reliable than a measured one, and every
  report says which was used. For a measured profile, run the estimator on a
  machine running Claude Code.
- **No package installation.** PyYAML is not needed; manifests are read by the
  bundled parser, which is asserted to produce identical results on the
  supported subset. `markdown` and Playwright are likewise not needed — see the
  report step.

Run `python scripts/environment.py` at any time for a capability report.
"""


def _read(path):
    with open(path, "r", encoding="utf-8") as fh:
        return fh.read()


def _write(path, text):
    directory = os.path.dirname(path)
    if directory and not os.path.isdir(directory):
        os.makedirs(directory)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)


def skill_description():
    text = _read(os.path.join(SKILL_SRC, "SKILL.md"))
    match = re.search(r"^description:\s*(.+?)$", text, re.M)
    if not match:
        raise SystemExit("SKILL.md has no description in its front matter.")
    return match.group(1).strip()


def make_icons(dest):
    """192x192 colour and 32x32 outline marks."""
    from PIL import Image, ImageDraw

    colour = Image.new("RGBA", (192, 192), (31, 58, 95, 255))
    draw = ImageDraw.Draw(colour)
    # A rising bar chart: the estimate, and its uncertainty band above it.
    bars = [(46, 132, 66, 150), (78, 108, 98, 150), (110, 84, 130, 150)]
    for x0, y0, x1, y1 in bars:
        draw.rectangle([x0, y0, x1, y1], fill=(255, 255, 255, 255))
    for x0, y0, x1, _y1 in bars:
        draw.rectangle([x0, y0 - 26, x1, y0 - 6], fill=(122, 178, 220, 255))
    colour.save(os.path.join(dest, "color.png"))

    outline = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
    d2 = ImageDraw.Draw(outline)
    for x0, y0, x1, y1 in [(7, 21, 11, 25), (13, 16, 17, 25), (19, 11, 23, 25)]:
        d2.rectangle([x0, y0, x1, y1], fill=(255, 255, 255, 255))
    outline.save(os.path.join(dest, "outline.png"))


def stage_skill(dest):
    """Copy the skill, consolidating references and trimming assets."""
    scripts_dst = os.path.join(dest, "scripts")
    shutil.copytree(os.path.join(SKILL_SRC, "scripts"), scripts_dst)
    for root, _dirs, files in os.walk(scripts_dst):
        for name in files:
            if name.endswith(".pyc") or name == ".DS_Store":
                os.remove(os.path.join(root, name))

    ref_src = os.path.join(SKILL_SRC, "references")
    ref_dst = os.path.join(dest, "references")
    os.makedirs(ref_dst)
    for target, parts in REFERENCE_GROUPS.items():
        chunks = []
        for part in parts:
            path = os.path.join(ref_src, part)
            if os.path.exists(path):
                chunks.append(_read(path).strip())
        if not chunks:
            raise SystemExit("no source files found for reference %r" % target)
        _write(os.path.join(ref_dst, target),
               ("\n\n---\n\n".join(chunks)) + "\n")

    asset_src = os.path.join(SKILL_SRC, "assets")
    asset_dst = os.path.join(dest, "assets")
    os.makedirs(asset_dst)
    for name in PACKAGED_ASSETS:
        path = os.path.join(asset_src, name)
        if os.path.exists(path):
            shutil.copyfile(path, os.path.join(asset_dst, name))

    skill = _read(os.path.join(SKILL_SRC, "SKILL.md"))
    if OLD_PDF_BLOCK not in skill:
        raise SystemExit(
            "SKILL.md no longer contains the expected PDF block; the packaged "
            "PDF instructions would be wrong. Update OLD_PDF_BLOCK.")
    assert OLD_ONE_COMMAND in skill, (
        "the single-command example changed; update OLD_ONE_COMMAND or this "
        "package ships a PDF instruction the sandbox cannot follow")
    skill = skill.replace(OLD_ONE_COMMAND, NEW_ONE_COMMAND)
    skill = skill.replace(OLD_PDF_BLOCK, NEW_PDF_BLOCK)

    # Repoint the consolidated reference names.
    skill = skill.replace("`references/methodology.md`", "`references/methodology.md`")
    skill = skill.replace("references/rates-copilot-credits.md",
                          "references/rates.md")
    skill = skill.replace("references/licensing-and-stacks.md",
                          "references/methodology.md")
    # No asset rows to strip: the plugin bundles only the harbor-line example,
    # which the package carries too, so the table is already accurate here.
    skill = skill.rstrip() + "\n" + HOST_NOTE
    _write(os.path.join(dest, "SKILL.md"), skill)


def validate(root, description):
    problems = []
    companions, total = 0, 0
    for base, _dirs, files in os.walk(root):
        for name in files:
            path = os.path.join(base, name)
            size = os.path.getsize(path)
            total += size
            if os.path.relpath(path, root) != "SKILL.md":
                companions += 1
            if size > MAX_FILE_BYTES:
                problems.append("%s exceeds the %d byte per-file limit"
                                % (os.path.relpath(path, root), MAX_FILE_BYTES))
    if companions > MAX_COMPANION_FILES:
        problems.append("%d companion files exceeds the limit of %d"
                        % (companions, MAX_COMPANION_FILES))
    if total > MAX_TOTAL_BYTES:
        problems.append("package total %d exceeds %d bytes"
                        % (total, MAX_TOTAL_BYTES))
    if len(NAME) > MAX_NAME_LEN:
        problems.append("skill name exceeds %d characters" % MAX_NAME_LEN)
    if len(description) > MAX_DESC_LEN:
        problems.append("description is %d characters, limit is %d"
                        % (len(description), MAX_DESC_LEN))
    if not os.path.exists(os.path.join(root, "SKILL.md")):
        problems.append("SKILL.md missing from the skill root")
    if problems:
        raise SystemExit("Package validation FAILED:\n  " +
                         "\n  ".join(problems))
    return companions, total


def zip_tree(root, zip_path, arc_prefix=""):
    directory = os.path.dirname(zip_path)
    if directory and not os.path.isdir(directory):
        os.makedirs(directory)
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as archive:
        for base, _dirs, files in os.walk(root):
            for name in sorted(files):
                path = os.path.join(base, name)
                arc = os.path.join(arc_prefix, os.path.relpath(path, root))
                archive.write(path, arc)
    return os.path.getsize(zip_path)


def build(out_dir, keep_tree=False):
    if not os.path.isdir(SKILL_SRC):
        raise SystemExit(
            "plugins/build-work-estimator is missing. Run "
            "build/build_plugin.py first -- it is the canonical generator and "
            "packaging consumes its output.")
    description = skill_description()
    staging = os.path.join(SAMPLE, "build", "_staging")
    if os.path.isdir(staging):
        shutil.rmtree(staging)

    # --- Agent Skills standard package: Copilot Studio, Claude Cowork -------
    skill_root = os.path.join(staging, "skill")
    os.makedirs(skill_root)
    stage_skill(skill_root)
    companions, total = validate(skill_root, description)

    standard_zip = os.path.join(out_dir, "%s.zip" % NAME)
    standard_size = zip_tree(skill_root, standard_zip)

    # --- Copilot Cowork plugin: Teams manifest + icons + skills/ -----------
    cowork_root = os.path.join(staging, "cowork")
    os.makedirs(cowork_root)
    shutil.copytree(skill_root, os.path.join(cowork_root, "skills", NAME))
    make_icons(cowork_root)
    short_desc = ("Estimates the work of building with an AI coding agent, in "
                  "the currency of the stack you build with")
    manifest = {
        "$schema": "https://developer.microsoft.com/json-schemas/teams/"
                   "v1.28/MicrosoftTeams.schema.json",
        "manifestVersion": "1.28",
        "version": VERSION,
        "id": COWORK_ID,
        "developer": {
            "name": AUTHOR,
            "websiteUrl": "https://github.com/Dewain27/AgentDudeSamples",
            "privacyUrl": "https://github.com/Dewain27/AgentDudeSamples",
            "termsOfUseUrl": "https://github.com/Dewain27/AgentDudeSamples",
        },
        "name": {"short": SHORT_NAME,
                 "full": "%s for Copilot Cowork" % SHORT_NAME},
        "description": {"short": short_desc[:80], "full": description},
        "icons": {"color": "color.png", "outline": "outline.png"},
        "accentColor": ACCENT,
        "agentSkills": [{"folder": "./skills/%s" % NAME}],
    }
    _write(os.path.join(cowork_root, "manifest.json"),
           json.dumps(manifest, indent=2) + "\n")

    if not os.path.exists(os.path.join(cowork_root, "manifest.json")):
        raise SystemExit("manifest.json missing from the Cowork package root")
    if not os.path.isdir(os.path.join(cowork_root, "skills", NAME)):
        raise SystemExit("skills/%s referenced by manifest is absent" % NAME)

    cowork_zip = os.path.join(out_dir, "%s-cowork-plugin.zip" % NAME)
    cowork_size = zip_tree(cowork_root, cowork_zip)

    if not keep_tree:
        shutil.rmtree(staging)

    return {
        "companions": companions,
        "skill_bytes": total,
        "standard_zip": standard_zip,
        "standard_size": standard_size,
        "cowork_zip": cowork_zip,
        "cowork_size": cowork_size,
        "description_len": len(description),
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", default=os.path.join(SAMPLE, "packages"))
    ap.add_argument("--keep-tree", action="store_true")
    args = ap.parse_args(argv)

    result = build(args.out, args.keep_tree)
    print("Packaged %s v%s" % (NAME, VERSION))
    print("  companion files : %d / %d" % (result["companions"],
                                           MAX_COMPANION_FILES))
    print("  skill payload   : %s bytes / %s"
          % (format(result["skill_bytes"], ","), format(MAX_TOTAL_BYTES, ",")))
    print("  description     : %d / %d chars"
          % (result["description_len"], MAX_DESC_LEN))
    print()
    print("  Agent Skills standard (Copilot Studio, Claude Cowork):")
    print("    %s (%s bytes)" % (os.path.relpath(result["standard_zip"], REPO),
                                 format(result["standard_size"], ",")))
    print("  Microsoft Copilot Cowork plugin:")
    print("    %s (%s bytes)" % (os.path.relpath(result["cowork_zip"], REPO),
                                 format(result["cowork_size"], ",")))
    print()
    print("  GitHub Copilot CLI and Claude Code install from")
    print("    plugins/%s/  (built by build_plugin.py)" % NAME)
    return 0


if __name__ == "__main__":
    sys.exit(main())
