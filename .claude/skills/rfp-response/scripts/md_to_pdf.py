#!/usr/bin/env python3
"""Render an RFP proposal (Markdown) as a formatted PDF.

    python md_to_pdf.py proposal.md                    # -> proposal.pdf
    python md_to_pdf.py proposal.md -o out/bid.pdf
    python md_to_pdf.py rfp.md --kind request          # buyer-side styling

The document is expected to open with a title (`# ...`), an optional subtitle
(`## ...`), an optional metadata table, and then numbered sections
(`## 1. Cover letter`). Everything before the first numbered section becomes a
cover page; the rest flows as the body with running page numbers.

Dependencies: `pip install markdown playwright`. Chromium is located
automatically; set CHROMIUM_PATH to override.
"""

import argparse
import os
import re
import sys
from pathlib import Path

CHROMIUM_CANDIDATES = [
    os.environ.get("CHROMIUM_PATH", ""),
    "/opt/pw-browsers/chromium",
    "/usr/bin/chromium",
    "/usr/bin/chromium-browser",
    "/usr/bin/google-chrome",
]

ACCENTS = {
    "response": {"accent": "#0b5d51", "soft": "#eaf3f1", "label": "Proposal Response"},
    "request": {"accent": "#334e68", "soft": "#eef2f7", "label": "Request for Proposal"},
}


def _chromium_path():
    for candidate in CHROMIUM_CANDIDATES:
        if candidate and Path(candidate).exists():
            return candidate
    return None  # let Playwright fall back to its own download


def _css(kind):
    theme = ACCENTS[kind]
    accent, soft = theme["accent"], theme["soft"]
    return f"""
@page {{ size: Letter; margin: 0.85in 0.8in 0.95in 0.8in; }}
* {{ box-sizing: border-box; }}
body {{ font-family: "Charter","Bitstream Charter","Liberation Serif",Georgia,serif;
  font-size: 10.5pt; line-height: 1.55; color: #1a1a1a; margin: 0; }}

.cover {{ break-after: page; padding-top: 0.3in; }}
.cover .eyebrow {{ font-family: "Liberation Sans","DejaVu Sans",Arial,sans-serif;
  font-size: 8.5pt; font-weight: 700; letter-spacing: .16em; text-transform: uppercase;
  color: #fff; background: {accent}; display: inline-block; padding: 5px 12px;
  border-radius: 2px; margin-bottom: 26px; }}
.cover h1 {{ font-family: "Liberation Sans","DejaVu Sans",Arial,sans-serif;
  font-size: 25pt; line-height: 1.2; font-weight: 700; color: {accent};
  margin: 0 0 6px 0; border: none; padding: 0; }}
.cover h2 {{ font-family: "Liberation Sans","DejaVu Sans",Arial,sans-serif;
  font-size: 14pt; font-weight: 400; color: #4a5568; margin: 0 0 22px 0;
  border: none; padding: 0; }}
.cover .rule {{ height: 3px; background: {accent}; margin: 0 0 22px 0; }}
.cover p {{ font-size: 12pt; margin: 0 0 4px 0; }}
.cover .org {{ font-family: "Liberation Sans","DejaVu Sans",Arial,sans-serif;
  font-size: 13pt; font-weight: 700; color: #1a1a1a; margin-bottom: 26px; }}
.cover table {{ width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 10pt; }}
.cover table td {{ padding: 8px 12px; border: none; border-bottom: 1px solid #dde3ea;
  vertical-align: top; }}
.cover table td:first-child {{ width: 38%; color: #4a5568; }}
.cover table tr:first-child td {{ border-top: 1px solid #dde3ea; }}

.notice {{ border-left: 4px solid #c9a227; background: #fdf8e8; padding: 10px 14px;
  font-size: 9pt; line-height: 1.45; color: #5c4813; margin: 34px 0 0 0; }}
.notice p {{ margin: 0; font-size: 9pt; }}

h2 {{ font-family: "Liberation Sans","DejaVu Sans",Arial,sans-serif; font-size: 13pt;
  font-weight: 700; color: {accent}; margin: 22px 0 9px 0; padding-bottom: 5px;
  border-bottom: 2px solid {accent}; break-after: avoid; }}
h3 {{ font-family: "Liberation Sans","DejaVu Sans",Arial,sans-serif; font-size: 11pt;
  font-weight: 700; color: #2d3748; margin: 16px 0 6px 0; break-after: avoid; }}
p {{ margin: 0 0 9px 0; orphans: 2; widows: 2; }}
ul, ol {{ margin: 0 0 10px 0; padding-left: 20px; }}
li {{ margin-bottom: 4px; break-inside: avoid; }}
strong {{ color: #16202b; }}
hr {{ border: none; border-top: 1px solid #dde3ea; margin: 18px 0; }}
table {{ width: 100%; border-collapse: collapse; margin: 10px 0 14px 0;
  font-size: 9.5pt; break-inside: avoid; }}
th {{ font-family: "Liberation Sans","DejaVu Sans",Arial,sans-serif; background: {soft};
  color: {accent}; font-size: 9pt; font-weight: 700; text-align: left;
  padding: 7px 10px; border-bottom: 2px solid {accent}; }}
td {{ padding: 6px 10px; border-bottom: 1px solid #e6ebf1; vertical-align: top; }}
tbody tr:nth-child(even) td {{ background: #fafbfc; }}
tr {{ break-inside: avoid; }}
blockquote {{ border-left: 3px solid {accent}; background: {soft}; margin: 10px 0;
  padding: 8px 14px; font-size: 9.5pt; }}
blockquote p {{ margin: 0; }}
em {{ color: #4a5568; }}
"""


FOOTER = """
<div style="font-family:'Liberation Sans',Arial,sans-serif; font-size:7.5pt;
            color:#8a94a0; width:100%; padding:0 0.8in; display:flex;
            justify-content:space-between; align-items:center;">
  <span style="max-width:70%; overflow:hidden; white-space:nowrap;">{left}</span>
  <span>Page <span class="pageNumber"></span> of <span class="totalPages"></span></span>
</div>
"""

# Body sections are numbered (`## 1. Cover letter`). Match only those so a bare
# `## <subtitle>` line under the title stays on the cover page where it belongs.
SECTION_RE = re.compile(r"^## \d+\.?\s", re.MULTILINE)
EMPTY_THEAD_RE = re.compile(
    r"<thead>\s*<tr>\s*(?:<th[^>]*>\s*</th>\s*)+</tr>\s*</thead>", re.DOTALL
)
EMPTY_P_RE = re.compile(r"<p>\s*</p>")


def _tidy(html):
    return EMPTY_P_RE.sub("", EMPTY_THEAD_RE.sub("", html))


def build_html(md_text, kind):
    import markdown as md

    match = SECTION_RE.search(md_text)
    cover_md, body_md = (
        (md_text[: match.start()], md_text[match.start():]) if match else (md_text, "")
    )

    # nl2br on the cover only: its address-style lines must stay stacked, while
    # body paragraphs wrap freely across source lines and must not gain breaks.
    cover_html = _tidy(
        md.Markdown(extensions=["tables", "sane_lists", "nl2br"]).convert(cover_md)
    )
    body_html = _tidy(md.Markdown(extensions=["tables", "sane_lists"]).convert(body_md))

    notice = ""
    bq = re.search(r"<blockquote>.*?</blockquote>", cover_html, re.DOTALL)
    if bq:
        inner = re.sub(r"</?blockquote>", "", bq.group(0)).strip()
        notice = f'<div class="notice">{inner}</div>'
        cover_html = cover_html.replace(bq.group(0), "")

    cover_html = cover_html.replace("<table>", '<div class="rule"></div><table>', 1)
    cover_html = re.sub(
        r"<p><strong>(.*?)</strong></p>", r'<p class="org">\1</p>', cover_html, count=1
    )

    return f"""<!doctype html><html><head><meta charset="utf-8">
<style>{_css(kind)}</style></head><body>
<div class="cover"><div class="eyebrow">{ACCENTS[kind]['label']}</div>
{cover_html}{notice}</div>
{body_html}</body></html>"""


def render(md_path, out_path, kind, footer_label):
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        sys.exit(
            "error: PDF rendering needs 'markdown' and 'playwright'.\n"
            "       pip install markdown playwright"
        )

    html = build_html(Path(md_path).read_text(encoding="utf-8"), kind)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(
            executable_path=_chromium_path(), args=["--no-sandbox"]
        )
        page = browser.new_page()
        page.set_content(html, wait_until="load")
        page.pdf(
            path=str(out_path),
            format="Letter",
            print_background=True,
            display_header_footer=True,
            header_template='<div style="font-size:1px;color:transparent;">.</div>',
            footer_template=FOOTER.format(left=footer_label),
            margin={"top": "0.85in", "bottom": "0.95in",
                    "left": "0.8in", "right": "0.8in"},
        )
        browser.close()
    return out_path


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("markdown", help="Path to the Markdown document.")
    ap.add_argument("-o", "--out", help="Output PDF path (default: alongside input).")
    ap.add_argument("--kind", choices=["response", "request"], default="response",
                    help="Styling: 'response' is teal (vendor), 'request' slate (buyer).")
    ap.add_argument("--footer", default=None,
                    help="Footer text on the left of each page (default: the title).")
    args = ap.parse_args()

    md_path = Path(args.markdown)
    if not md_path.exists():
        sys.exit(f"error: no such file: {md_path}")

    out = Path(args.out) if args.out else md_path.with_suffix(".pdf")

    footer = args.footer
    if footer is None:
        first_h1 = re.search(r"^# (.+)$", md_path.read_text(encoding="utf-8"),
                             re.MULTILINE)
        footer = first_h1.group(1).strip() if first_h1 else md_path.stem

    render(md_path, out, args.kind, footer)
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
