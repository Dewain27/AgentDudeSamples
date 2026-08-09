"""Render the generated Markdown RFP documents as professional PDFs.

Pipeline: Markdown -> styled HTML -> Chromium (headless) -> PDF.

The Markdown produced by `render_request` / `render_response` opens with a
sample notice, an H1 title, an optional H2 subtitle, and a metadata table,
followed by numbered `## ` sections. We split at the first numbered section:
everything before it becomes a designed cover page, and the rest flows as the
document body with running page numbers.

Optional feature — requires the extras in `requirements-pdf.txt`:
    pip install -r requirements-pdf.txt
"""

import re
from pathlib import Path

# Chromium ships with the environment; Playwright drives it for print-to-PDF.
CHROMIUM_CANDIDATES = [
    "/opt/pw-browsers/chromium",
    "/usr/bin/chromium",
    "/usr/bin/chromium-browser",
    "/usr/bin/google-chrome",
]


class MissingPdfDependencies(RuntimeError):
    """Raised when the optional PDF extras are not installed."""


def _require_deps():
    try:
        import markdown  # noqa: F401
        from playwright.sync_api import sync_playwright  # noqa: F401
    except ImportError as exc:  # pragma: no cover - depends on environment
        raise MissingPdfDependencies(
            "PDF export needs the optional extras. Install them with:\n"
            "    pip install -r requirements-pdf.txt"
        ) from exc


def _chromium_path():
    for candidate in CHROMIUM_CANDIDATES:
        if Path(candidate).exists():
            return candidate
    return None  # fall back to Playwright's bundled browser


# ---------------------------------------------------------------------------
# Styling
# ---------------------------------------------------------------------------

ACCENTS = {
    "request": {"accent": "#334e68", "soft": "#eef2f7", "label": "Request for Proposal"},
    "response": {"accent": "#0b5d51", "soft": "#eaf3f1", "label": "Proposal Response"},
}


def _css(kind: str) -> str:
    theme = ACCENTS[kind]
    accent = theme["accent"]
    soft = theme["soft"]
    return f"""
@page {{
  size: Letter;
  margin: 0.85in 0.8in 0.95in 0.8in;
}}

* {{ box-sizing: border-box; }}

body {{
  font-family: "Charter", "Bitstream Charter", "Liberation Serif", Georgia, serif;
  font-size: 10.5pt;
  line-height: 1.55;
  color: #1a1a1a;
  margin: 0;
}}

/* ---------- Cover page ---------- */

.cover {{
  break-after: page;
  padding-top: 0.3in;
}}

.cover .eyebrow {{
  font-family: "Liberation Sans", "DejaVu Sans", Arial, sans-serif;
  font-size: 8.5pt;
  font-weight: 700;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: #ffffff;
  background: {accent};
  display: inline-block;
  padding: 5px 12px;
  border-radius: 2px;
  margin-bottom: 26px;
}}

.cover h1 {{
  font-family: "Liberation Sans", "DejaVu Sans", Arial, sans-serif;
  font-size: 25pt;
  line-height: 1.2;
  font-weight: 700;
  color: {accent};
  margin: 0 0 6px 0;
  padding: 0;
  border: none;
}}

.cover h2 {{
  font-family: "Liberation Sans", "DejaVu Sans", Arial, sans-serif;
  font-size: 14pt;
  font-weight: 400;
  color: #4a5568;
  margin: 0 0 22px 0;
  padding: 0;
  border: none;
}}

.cover .rule {{
  height: 3px;
  background: {accent};
  width: 100%;
  margin: 0 0 22px 0;
}}

.cover p {{
  font-size: 12pt;
  margin: 0 0 4px 0;
}}

.cover .org {{
  font-family: "Liberation Sans", "DejaVu Sans", Arial, sans-serif;
  font-size: 13pt;
  font-weight: 700;
  color: #1a1a1a;
  margin-bottom: 26px;
}}

.cover table {{
  width: 100%;
  border-collapse: collapse;
  margin-top: 10px;
  font-size: 10pt;
}}

.cover table td {{
  padding: 8px 12px;
  border: none;
  border-bottom: 1px solid #dde3ea;
  vertical-align: top;
}}

.cover table td:first-child {{
  width: 38%;
  color: #4a5568;
}}

.cover table tr:first-child td {{ border-top: 1px solid #dde3ea; }}

/* Sample notice (from the leading blockquote) */
.notice {{
  border-left: 4px solid #c9a227;
  background: #fdf8e8;
  padding: 10px 14px;
  font-size: 9pt;
  line-height: 1.45;
  color: #5c4813;
  margin: 34px 0 0 0;
}}
.notice p {{ margin: 0; font-size: 9pt; }}

/* ---------- Body ---------- */

h2 {{
  font-family: "Liberation Sans", "DejaVu Sans", Arial, sans-serif;
  font-size: 13pt;
  font-weight: 700;
  color: {accent};
  margin: 22px 0 9px 0;
  padding-bottom: 5px;
  border-bottom: 2px solid {accent};
  break-after: avoid;
}}

h3 {{
  font-family: "Liberation Sans", "DejaVu Sans", Arial, sans-serif;
  font-size: 11pt;
  font-weight: 700;
  color: #2d3748;
  margin: 16px 0 6px 0;
  break-after: avoid;
}}

p {{ margin: 0 0 9px 0; orphans: 2; widows: 2; }}

ul, ol {{ margin: 0 0 10px 0; padding-left: 20px; }}
li {{ margin-bottom: 4px; break-inside: avoid; }}

strong {{ color: #16202b; }}

hr {{
  border: none;
  border-top: 1px solid #dde3ea;
  margin: 18px 0;
}}

table {{
  width: 100%;
  border-collapse: collapse;
  margin: 10px 0 14px 0;
  font-size: 9.5pt;
  break-inside: avoid;
}}

th {{
  font-family: "Liberation Sans", "DejaVu Sans", Arial, sans-serif;
  background: {soft};
  color: {accent};
  font-size: 9pt;
  font-weight: 700;
  text-align: left;
  padding: 7px 10px;
  border-bottom: 2px solid {accent};
}}

td {{
  padding: 6px 10px;
  border-bottom: 1px solid #e6ebf1;
  vertical-align: top;
}}

tbody tr:nth-child(even) td {{ background: #fafbfc; }}

tr {{ break-inside: avoid; }}

/* Body blockquotes (rare) */
blockquote {{
  border-left: 3px solid {accent};
  background: {soft};
  margin: 10px 0;
  padding: 8px 14px;
  font-size: 9.5pt;
}}
blockquote p {{ margin: 0; }}

em {{ color: #4a5568; }}

/* Closing italic sign-off line */
p > em:only-child {{ font-size: 9pt; }}
"""


FOOTER_TEMPLATE = """
<div style="font-family: 'Liberation Sans', Arial, sans-serif; font-size:7.5pt;
            color:#8a94a0; width:100%; padding:0 0.8in;
            display:flex; justify-content:space-between; align-items:center;">
  <span style="max-width:70%; overflow:hidden; white-space:nowrap;">{left}</span>
  <span>Page <span class="pageNumber"></span> of <span class="totalPages"></span></span>
</div>
"""

HEADER_TEMPLATE = '<div style="font-size:1px; color:transparent;">.</div>'


# ---------------------------------------------------------------------------
# Markdown -> HTML
# ---------------------------------------------------------------------------

_H1_RE = re.compile(r"^# .+$", re.MULTILINE)
_HEADING_RE = re.compile(r"^## .+$", re.MULTILINE)


def _find_body_start(md_text):
    """Return the offset where the cover ends and the body begins.

    Body sections may be numbered (`## 1. Introduction`) or lettered
    (`## Part A — Tenderer details`) when a buyer mandates their own scheme.
    An H2 sitting directly under the H1 is the document subtitle and stays on
    the cover. Returns None if there is no body heading at all.
    """
    h1 = _H1_RE.search(md_text)
    for i, heading in enumerate(_HEADING_RE.finditer(md_text)):
        if i == 0 and h1 and not md_text[h1.end():heading.start()].strip():
            continue
        return heading.start()
    return None

# The metadata tables are written as headerless Markdown (`| | |`), which the
# converter turns into a <thead> of empty cells. Left in place it prints as a
# stray accent bar, so strip it.
_EMPTY_THEAD_RE = re.compile(
    r"<thead>\s*<tr>\s*(?:<th[^>]*>\s*</th>\s*)+</tr>\s*</thead>", re.DOTALL
)
_EMPTY_P_RE = re.compile(r"<p>\s*</p>")


def _tidy(html: str) -> str:
    html = _EMPTY_THEAD_RE.sub("", html)
    return _EMPTY_P_RE.sub("", html)


def _split_cover(md_text: str):
    """Split the document into (cover_markdown, body_markdown).

    The cover is everything before the first numbered `## ` section.
    """
    split = _find_body_start(md_text)
    if split is None:
        return md_text, ""
    return md_text[:split], md_text[split:]


def _build_html(md_text: str, kind: str) -> str:
    import markdown as md

    cover_md, body_md = _split_cover(md_text)

    # nl2br on the cover only: its address-style lines ("Submitted by ...",
    # "Prepared for ...") are single newlines that must stay on separate lines.
    cover_conv = md.Markdown(extensions=["tables", "sane_lists", "nl2br"])
    cover_html = _tidy(cover_conv.convert(cover_md))

    body_conv = md.Markdown(extensions=["tables", "sane_lists"])
    body_html = _tidy(body_conv.convert(body_md))

    # The leading blockquote is the sample notice — restyle it and move it to
    # the bottom of the cover page.
    notice_html = ""
    bq = re.search(r"<blockquote>.*?</blockquote>", cover_html, re.DOTALL)
    if bq:
        inner = re.sub(r"</?blockquote>", "", bq.group(0)).strip()
        notice_html = f'<div class="notice">{inner}</div>'
        cover_html = cover_html.replace(bq.group(0), "")

    # Insert the accent rule after the title block (before the first table).
    cover_html = cover_html.replace("<table>", '<div class="rule"></div><table>', 1)

    # Bold standalone paragraphs on the cover are the organization name.
    cover_html = re.sub(
        r"<p><strong>(.*?)</strong></p>",
        r'<p class="org">\1</p>',
        cover_html,
        count=1,
    )

    label = ACCENTS[kind]["label"]

    return f"""<!doctype html>
<html><head><meta charset="utf-8"><style>{_css(kind)}</style></head>
<body>
<div class="cover">
  <div class="eyebrow">{label}</div>
  {cover_html}
  {notice_html}
</div>
{body_html}
</body></html>
"""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def markdown_to_pdf(md_text: str, out_path: Path, kind: str, footer_label: str, page=None):
    """Render one Markdown document to a PDF at `out_path`.

    Pass an existing Playwright `page` to reuse a browser across many
    documents; otherwise a browser is launched for this single render.
    """
    _require_deps()
    html = _build_html(md_text, kind)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    def _render(pg):
        pg.set_content(html, wait_until="load")
        pg.pdf(
            path=str(out_path),
            format="Letter",
            print_background=True,
            display_header_footer=True,
            header_template=HEADER_TEMPLATE,
            footer_template=FOOTER_TEMPLATE.format(left=footer_label),
            margin={"top": "0.85in", "bottom": "0.95in", "left": "0.8in", "right": "0.8in"},
        )

    if page is not None:
        _render(page)
        return out_path

    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(
            executable_path=_chromium_path(), args=["--no-sandbox"]
        )
        pg = browser.new_page()
        _render(pg)
        browser.close()
    return out_path


class PdfSession:
    """Context manager that keeps one browser open across many renders."""

    def __init__(self):
        _require_deps()
        self._pw = None
        self._browser = None
        self.page = None

    def __enter__(self):
        from playwright.sync_api import sync_playwright

        self._pw = sync_playwright().start()
        self._browser = self._pw.chromium.launch(
            executable_path=_chromium_path(), args=["--no-sandbox"]
        )
        self.page = self._browser.new_page()
        return self

    def __exit__(self, *exc):
        if self._browser:
            self._browser.close()
        if self._pw:
            self._pw.stop()
        return False

    def render(self, md_text: str, out_path: Path, kind: str, footer_label: str):
        return markdown_to_pdf(md_text, out_path, kind, footer_label, page=self.page)
