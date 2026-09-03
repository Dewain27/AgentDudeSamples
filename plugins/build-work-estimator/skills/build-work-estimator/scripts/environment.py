#!/usr/bin/env python3
"""What this host can actually do, and what to do when it can't.

Author: Dewain Robinson

The estimator runs in four very different places: Claude Code, Claude Cowork,
GitHub Copilot, and Microsoft Copilot Cowork. They differ in ways that change
the answer, not just the plumbing:

  * Only a machine running Claude Code has `~/.claude/projects`, so only there
    can the estimate be calibrated from measured history. Everywhere else it
    falls back to published baselines -- which is fine, and must be SAID.
  * Sandboxed hosts have no package installation and no browser, so PyYAML,
    markdown, and Playwright may all be absent. The bundled parser covers YAML;
    for PDF the host's own document creation is used instead.

    python environment.py            # human-readable capability report
    python environment.py --json

Capabilities are PROBED, not inferred from a host name. Host detection is
guesswork; asking "can I read session history?" is not.
"""

__author__ = "Dewain Robinson"

import argparse
import glob
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def has_session_history(root=None):
    """True when Claude Code transcripts are readable here."""
    root = root or os.path.expanduser("~/.claude/projects")
    if not os.path.isdir(root):
        return False
    return bool(glob.glob(os.path.join(root, "*", "*.jsonl")))


def _importable(name):
    try:
        __import__(name)
        return True
    except Exception:
        return False


def has_chromium():
    """True when Playwright can most likely render a PDF."""
    if not _importable("playwright"):
        return False
    candidates = [
        os.environ.get("CHROMIUM_PATH", ""),
        "/opt/pw-browsers/chromium",
        "/usr/bin/chromium",
        "/usr/bin/chromium-browser",
        "/usr/bin/google-chrome",
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    ]
    if any(path and os.path.exists(path) for path in candidates):
        return True
    # Playwright may still have its own managed browser; treat as maybe-yes.
    return bool(glob.glob(os.path.expanduser(
        "~/Library/Caches/ms-playwright/chromium*"))) or bool(glob.glob(
        os.path.expanduser("~/.cache/ms-playwright/chromium*")))


def probe(history_root=None):
    """Return what this environment can do."""
    yaml_available = _importable("yaml")
    return {
        "session_history": has_session_history(history_root),
        "pyyaml": yaml_available,
        "manifest_parsing": True,  # bundled parser always works
        "markdown": _importable("markdown"),
        "playwright": _importable("playwright"),
        "chromium": has_chromium(),
        "pdf_locally": _importable("markdown") and has_chromium(),
    }


def calibration_mode(caps):
    return "measured" if caps["session_history"] else "published-baseline"


def guidance(caps):
    """Plain statements about what this host will and won't do."""
    notes = []

    if caps["session_history"]:
        notes.append(
            "Session history found. The estimate will be calibrated from "
            "measured local usage, which is the accurate path.")
    else:
        notes.append(
            "No Claude Code session history on this host, so the estimate "
            "falls back to published baselines. That is expected on GitHub "
            "Copilot, Copilot Cowork, and Claude Cowork -- but a "
            "published-baseline estimate is materially less reliable than a "
            "measured one, and every report says so. To calibrate, run the "
            "estimator on a machine that runs Claude Code.")

    if not caps["pyyaml"]:
        notes.append(
            "PyYAML is not installed; the bundled manifest parser is used "
            "instead. Same result on the supported subset -- no action needed.")

    if not caps["pdf_locally"]:
        missing = []
        if not caps["markdown"]:
            missing.append("the `markdown` package")
        if not caps["chromium"]:
            missing.append("a headless browser")
        notes.append(
            "PDF cannot be rendered locally (%s unavailable). The Markdown "
            "report is still written in full. On a host that creates "
            "documents natively -- Copilot Cowork, Claude Cowork, Copilot "
            "Studio -- ask the host to produce the PDF from that Markdown "
            "rather than installing a browser."
            % " and ".join(missing))

    return notes


def render(caps):
    lines = ["Environment capabilities", ""]
    rows = [
        ("Session history (calibration)", caps["session_history"]),
        ("PyYAML", caps["pyyaml"]),
        ("Manifest parsing", caps["manifest_parsing"]),
        ("markdown package", caps["markdown"]),
        ("Playwright", caps["playwright"]),
        ("Headless browser", caps["chromium"]),
        ("Local PDF rendering", caps["pdf_locally"]),
    ]
    for label, value in rows:
        lines.append("  %-32s %s" % (label, "yes" if value else "no"))
    lines.append("")
    lines.append("Calibration mode: %s" % calibration_mode(caps))
    lines.append("")
    for note in guidance(caps):
        lines.append("- " + note)
    return "\n".join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--history-root", default=None)
    args = ap.parse_args(argv)

    caps = probe(args.history_root)
    if args.json:
        print(json.dumps({"capabilities": caps,
                          "calibration_mode": calibration_mode(caps),
                          "guidance": guidance(caps)}, indent=2))
    else:
        print(render(caps))
    return 0


if __name__ == "__main__":
    sys.exit(main())
