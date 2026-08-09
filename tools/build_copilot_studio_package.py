#!/usr/bin/env python3
"""Build a Copilot Studio -upload-ready package of the rfp-response skill.

Copilot Studio's GitHub Copilot harness accepts a skill as a ZIP containing a
`SKILL.md` (YAML front matter + Markdown) plus optional supporting files. The
format is the Agent Skills open standard, so our authored skill is already
compatible in substance — but two things have to change to ship it:

1. **Companion-file budget.** The authored skill keeps one reference file per
   offering (15 of them), which is great for token efficiency in a shell agent
   but puts the package at exactly 20 companion files — the documented ceiling,
   with no headroom. Here we regenerate the offering references consolidated by
   product line (6 files), which drops the package to 11 companions.

2. **PDF rendering.** The bundled `md_to_pdf.py` drives headless Chromium. The
   Copilot Studio sandbox has no browser and no package installation, but the
   harness creates PDFs natively — so the packaged instructions tell the agent
   to use that, and keep the script as the shell-environment option.

Everything else is copied verbatim. Reference content is regenerated from the
rfp-automation-kit catalog, which stays the single source of truth.

    python tools/build_copilot_studio_package.py
    python tools/build_copilot_studio_package.py --out dist --keep-tree

Limits enforced below are those Microsoft documents for Agent Skills packaging.
Copilot Studio's own docs don't publish per-package numbers; these come from the
Copilot Cowork plugin documentation for the same standard, so they're treated as
the safe ceiling rather than a guess.
"""

import argparse
import re
import shutil
import sys
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SKILL_SRC = REPO / ".claude" / "skills" / "rfp-response"
KIT = REPO / "rfp-automation-kit"

# Documented Agent Skills packaging limits.
MAX_COMPANION_FILES = 20
MAX_FILE_BYTES = 5 * 1024 * 1024
MAX_TOTAL_BYTES = 10 * 1024 * 1024
MAX_NAME_LEN = 64
MAX_DESC_LEN = 1024
SAFE_NAME = re.compile(r"[A-Za-z0-9_. !-]+")
WINDOWS_RESERVED = {
    "CON", "PRN", "AUX", "NUL",
    *(f"COM{i}" for i in range(1, 10)),
    *(f"LPT{i}" for i in range(1, 10)),
}

# --- SKILL.md transformations -------------------------------------------------
# Each is asserted to apply, so an edit to the source that breaks one fails the
# build loudly instead of shipping a package that points at files it doesn't have.

OLD_OFFERING_PATH = "`references/offerings/<id>.md`"
NEW_OFFERING_PATH = "`references/offerings-<product-line>.md`"

OLD_PDF_SECTION = """### 5. Render the PDF

```bash
python scripts/md_to_pdf.py proposal.md -o proposal.pdf
```

The script produces a cover page, styled tables, and running page numbers. It
needs `markdown` and `playwright` (`pip install markdown playwright`); if they're
missing it says so and exits, and the Markdown is still a complete deliverable.
Save both files and tell the user where they are."""

NEW_PDF_SECTION = """### 5. Produce the PDF

Return a PDF alongside the Markdown. How you make it depends on where you're
running:

- **In Copilot Studio (GitHub Copilot harness)** — the harness creates PDF files
  natively, so generate the PDF directly from the finished Markdown. Don't try to
  install packages or launch a browser; the sandbox has neither, and you don't
  need them. Keep the cover block, section numbering, and tables intact so the
  output matches the house format.
- **In a shell environment** (a local checkout, a coding agent with a terminal) —
  run the bundled renderer instead, which applies the house cover page and page
  numbering for you:

  ```bash
  python scripts/md_to_pdf.py proposal.md -o proposal.pdf
  ```

  It needs `markdown` and `playwright`; if they're missing it says so and exits,
  and the Markdown is still a complete deliverable.

Either way, save both files and tell the user where they are."""

OLD_SCRIPT_ROW = (
    "| `scripts/md_to_pdf.py` | To render the finished Markdown as a PDF |"
)
NEW_SCRIPT_ROW = (
    "| `scripts/md_to_pdf.py` | To render the PDF **when you have a shell**; "
    "in Copilot Studio use the harness's native PDF creation instead |"
)


def transform_skill_md(text: str) -> str:
    """Apply the packaging transformations, asserting each one lands."""
    subs = [
        ("offering reference path", OLD_OFFERING_PATH, NEW_OFFERING_PATH, 2),
        ("PDF section", OLD_PDF_SECTION, NEW_PDF_SECTION, 1),
        ("bundled-files script row", OLD_SCRIPT_ROW, NEW_SCRIPT_ROW, 1),
    ]
    for label, old, new, expected in subs:
        found = text.count(old)
        if found != expected:
            sys.exit(
                f"error: expected {expected} occurrence(s) of the {label} in "
                f"SKILL.md, found {found}.\n"
                f"       The source skill changed — update the transformation in "
                f"{Path(__file__).name} to match."
            )
        text = text.replace(old, new)
    return text


def build_references(dest: Path) -> None:
    """Regenerate offering references, consolidated one file per product line."""
    sys.path.insert(0, str(KIT))
    from rfpkit.catalog_data import OFFERINGS, PRODUCT_LINES  # noqa: E402

    for line_key, line in PRODUCT_LINES.items():
        out = [f"# {line['name']}\n", f"_{line['summary']}_\n"]
        out.append(
            "Full detail for every offering in this product line. Pricing ranges "
            "are indicative for a full-scope engagement; quote a fixed fee inside "
            "the range that reflects the scope the RFP actually describes.\n"
        )
        for o in [x for x in OFFERINGS if x["line"] == line_key]:
            out.append(f"\n---\n\n## {o['name']}  (`{o['id']}`)\n")
            out.append(f"_{o['tagline']}_\n")
            out.append(f"**Scope:** {o['summary']}.  ")
            out.append(f"**Best fit for:** {', '.join(o['target_industries'])}.  ")
            out.append(
                f"**Indicative pricing:** {o['pricing_model']} · "
                f"${o['price_low']:,}–${o['price_high']:,} · "
                f"{o['timeline_months']} months.\n"
            )
            out.append("**Capabilities to describe in the proposed solution**\n")
            out += [f"- {c}" for c in o["capabilities"]]
            out.append("\n**Requirements this offering answers**\n")
            out += [f"- {r}" for r in o["typical_requirements"]]
            out.append("\n**Integrations** — name the buyer's actual systems when "
                       "the RFP identifies them; these are the fallback.\n")
            out += [f"- {i}" for i in o["integrations"]]
            out.append(f"\n**Compliance:** {', '.join(o['compliance'])}.\n")
            out.append("**Differentiators**\n")
            out += [f"- {d}" for d in o["differentiators"]]
            out.append("\n**Success measures buyers care about** — mirror these in "
                       "the executive summary when the RFP states similar goals.\n")
            out += [f"- {s}" for s in o["success_metrics"]]
            out.append("\n**Approved positioning language** — the backbone of "
                       "sections 3 and 4. Adapt wording to the buyer's terms; keep "
                       "the substance.\n")
            out.append(f"_Understanding:_ {o['snippets']['understanding']}\n")
            out.append(f"_Solution:_ {o['snippets']['solution']}\n")

        (dest / f"offerings-{line_key}.md").write_text(
            "\n".join(out) + "\n", encoding="utf-8"
        )


def validate(pkg: Path) -> list:
    """Check the staged package against the documented limits."""
    problems = []

    skill_md = pkg / "SKILL.md"
    if not skill_md.exists():
        problems.append("SKILL.md is missing from the package root")
        return problems

    text = skill_md.read_text(encoding="utf-8")
    fm = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    if not fm:
        problems.append("SKILL.md has no YAML front matter")
    else:
        name = re.search(r"^name:\s*(.+)$", fm.group(1), re.M)
        desc = re.search(r"^description:\s*(.+)$", fm.group(1), re.M)
        if not name:
            problems.append("front matter is missing `name`")
        else:
            n = name.group(1).strip()
            if n != pkg.name:
                problems.append(f"name '{n}' != package folder '{pkg.name}'")
            if not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", n):
                problems.append(f"name '{n}' is not kebab-case")
            if len(n) > MAX_NAME_LEN:
                problems.append(f"name is {len(n)} chars (max {MAX_NAME_LEN})")
        if not desc:
            problems.append("front matter is missing `description`")
        elif len(desc.group(1).strip()) > MAX_DESC_LEN:
            problems.append(
                f"description is {len(desc.group(1).strip())} chars "
                f"(max {MAX_DESC_LEN})"
            )

    companions = [p for p in pkg.rglob("*") if p.is_file() and p.name != "SKILL.md"]
    if len(companions) > MAX_COMPANION_FILES:
        problems.append(
            f"{len(companions)} companion files (max {MAX_COMPANION_FILES})"
        )

    total = 0
    for p in companions:
        rel = p.relative_to(pkg)
        size = p.stat().st_size
        total += size
        if size > MAX_FILE_BYTES:
            problems.append(f"{rel} is {size/1e6:.1f} MB (max 5 MB)")
        for part in rel.parts:
            if part.startswith("."):
                problems.append(f"{rel}: hidden file/dir not allowed")
            if part == "..":
                problems.append(f"{rel}: path traversal not allowed")
            if not SAFE_NAME.fullmatch(part):
                problems.append(f"{rel}: unsafe characters in name")
            if Path(part).stem.upper() in WINDOWS_RESERVED:
                problems.append(f"{rel}: Windows reserved name")
        if "\\" in str(rel):
            problems.append(f"{rel}: backslash in path")
    if total > MAX_TOTAL_BYTES:
        problems.append(f"companions total {total/1e6:.1f} MB (max 10 MB)")

    return problems


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default="dist", help="Output directory (default: dist).")
    ap.add_argument("--keep-tree", action="store_true",
                    help="Keep the staged folder next to the ZIP for inspection.")
    args = ap.parse_args()

    out_dir = (REPO / args.out) if not Path(args.out).is_absolute() else Path(args.out)
    stage = out_dir / "rfp-response"
    if stage.exists():
        shutil.rmtree(stage)
    (stage / "references").mkdir(parents=True)
    (stage / "assets").mkdir(parents=True)
    (stage / "scripts").mkdir(parents=True)

    # SKILL.md, transformed
    (stage / "SKILL.md").write_text(
        transform_skill_md((SKILL_SRC / "SKILL.md").read_text(encoding="utf-8")),
        encoding="utf-8",
    )

    # References: catalog index + answer library verbatim, offerings consolidated
    for name in ("catalog.md", "answer-library.md"):
        shutil.copy2(SKILL_SRC / "references" / name, stage / "references" / name)
    build_references(stage / "references")

    # The index points at per-offering files in the authored skill; repoint it.
    idx = stage / "references" / "catalog.md"
    idx.write_text(
        idx.read_text(encoding="utf-8").replace(
            "`references/offerings/<id>.md`",
            "`references/offerings-<product-line>.md` (the file for that "
            "offering's product line)",
        ),
        encoding="utf-8",
    )

    for name in ("example-rfp-request.md", "example-rfp-response.md"):
        shutil.copy2(SKILL_SRC / "assets" / name, stage / "assets" / name)
    shutil.copy2(SKILL_SRC / "scripts" / "md_to_pdf.py", stage / "scripts" / "md_to_pdf.py")

    problems = validate(stage)
    companions = [p for p in stage.rglob("*") if p.is_file() and p.name != "SKILL.md"]
    total_kb = sum(p.stat().st_size for p in companions) / 1024

    print(f"staged {stage.relative_to(REPO)}")
    print(f"  companion files : {len(companions)} / {MAX_COMPANION_FILES}")
    print(f"  total size      : {total_kb:.0f} KB / {MAX_TOTAL_BYTES/1024:.0f} KB")

    if problems:
        print("\nVALIDATION FAILED:")
        for p in problems:
            print(f"  - {p}")
        return 1
    print("  validation      : all checks passed")

    zip_path = out_dir / "rfp-response.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for p in sorted(stage.rglob("*")):
            if p.is_file():
                z.write(p, p.relative_to(stage))

    print(f"\nwrote {zip_path.relative_to(REPO)}  ({zip_path.stat().st_size/1024:.0f} KB)")
    print("Upload in Copilot Studio: Build tab > Skills > Add skill > Upload a skill")

    if not args.keep_tree:
        shutil.rmtree(stage)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
