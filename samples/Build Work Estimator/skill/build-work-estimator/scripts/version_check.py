#!/usr/bin/env python3
"""Verify this plugin is up to date before the estimator runs.

Author: Dewain Robinson

Runs first, on every skill invocation. Two deliberate asymmetries:

  * A CONFIRMED stale install fails closed -- exit 2, and the skill must stop.
    Estimating with an outdated rate table or a fixed bug is worse than not
    estimating.
  * An INABILITY to check fails open -- exit 0 with a visible notice. A public
    sample must not brick itself because someone is on a plane.

    python version_check.py                 # check, print, exit 0/2
    python version_check.py --json          # machine-readable result
"""

__author__ = "Dewain Robinson"

import argparse
import json
import os
import sys

try:  # stdlib only -- no requests dependency
    from urllib.request import urlopen
    from urllib.error import URLError, HTTPError
except ImportError:  # pragma: no cover
    urlopen = None

PLUGIN_NAME = "build-work-estimator"
MARKETPLACE_URL = (
    "https://raw.githubusercontent.com/Dewain27/AgentDudeSamples/main/"
    ".github/plugin/marketplace.json"
)
TIMEOUT_SECONDS = 5

OK = 0
STALE = 2


def parse_version(text):
    """'1.2.3' -> (1, 2, 3). Missing or non-numeric parts sort low."""
    parts = []
    for chunk in str(text or "").strip().split(".")[:3]:
        digits = ""
        for ch in chunk:
            if ch.isdigit():
                digits += ch
            else:
                break
        parts.append(int(digits) if digits else 0)
    while len(parts) < 3:
        parts.append(0)
    return tuple(parts)


def local_version(plugin_json_path=None):
    """Version from the installed plugin.json, or None if unreadable."""
    if plugin_json_path is None:
        here = os.path.dirname(os.path.abspath(__file__))
        # scripts/ -> skills/<name>/ -> skills/ -> plugin root
        plugin_json_path = os.path.join(here, "..", "..", "..", "plugin.json")
    try:
        with open(plugin_json_path, "r") as fh:
            return json.load(fh).get("version")
    except (IOError, OSError, ValueError):
        return None


def fetch_remote_version(url=MARKETPLACE_URL, timeout=TIMEOUT_SECONDS,
                         opener=None):
    """Remote version for this plugin.

    Returns (version, None) on success, or (None, reason) when the check
    could not be completed. A missing plugin entry is a 'could not check',
    not a 'you are current' -- we never infer currency from absence.
    """
    fetch = opener or urlopen
    try:
        handle = fetch(url, timeout=timeout)
        try:
            payload = handle.read()
        finally:
            if hasattr(handle, "close"):
                handle.close()
        if isinstance(payload, bytes):
            payload = payload.decode("utf-8")
        data = json.loads(payload)
    except (URLError, HTTPError) as exc:
        return None, "network error (%s)" % exc
    except ValueError as exc:
        return None, "malformed marketplace JSON (%s)" % exc
    except Exception as exc:  # timeouts, DNS, TLS, anything else
        return None, "could not reach marketplace (%s)" % exc

    for entry in data.get("plugins") or []:
        if entry.get("name") == PLUGIN_NAME:
            version = entry.get("version")
            if version:
                return version, None
            return None, "marketplace entry has no version"
    return None, "plugin %r not listed in marketplace" % PLUGIN_NAME


def check(url=MARKETPLACE_URL, plugin_json_path=None, opener=None):
    """Return a result dict describing whether this install is current."""
    local = local_version(plugin_json_path)
    remote, reason = fetch_remote_version(url=url, opener=opener)

    if remote is None:
        return {
            "status": "unverified",
            "local": local,
            "remote": None,
            "reason": reason,
            "exit_code": OK,
        }
    if local is None:
        return {
            "status": "unverified",
            "local": None,
            "remote": remote,
            "reason": "could not read local plugin.json",
            "exit_code": OK,
        }
    if parse_version(remote) > parse_version(local):
        return {
            "status": "stale",
            "local": local,
            "remote": remote,
            "reason": None,
            "exit_code": STALE,
        }
    return {
        "status": "current",
        "local": local,
        "remote": remote,
        "reason": None,
        "exit_code": OK,
    }


def render(result):
    """Human-readable message for a check() result. '' when current."""
    if result["status"] == "current":
        return ""
    if result["status"] == "unverified":
        return (
            "WARNING  Could not verify plugin version: %s.\n"
            "         Proceeding with local version %s. Rates and fixes may "
            "be out of date."
            % (result["reason"], result["local"] or "unknown")
        )
    return (
        "STOP  A newer version of %s is available.\n"
        "\n"
        "        installed: %s\n"
        "        available: %s\n"
        "\n"
        "      Do not continue with this estimate. An outdated install may "
        "carry stale\n"
        "      pricing tables or corrected estimation logic, and will produce "
        "numbers that\n"
        "      do not match the current model.\n"
        "\n"
        "      Update, then run the estimate again:\n"
        "\n"
        "        copilot plugin marketplace add Dewain27/AgentDudeSamples\n"
        "        copilot plugin install %s@agentdude-samples\n"
        % (PLUGIN_NAME, result["local"], result["remote"], PLUGIN_NAME)
    )


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--json", action="store_true",
                    help="emit the raw result as JSON")
    ap.add_argument("--url", default=MARKETPLACE_URL)
    args = ap.parse_args(argv)

    result = check(url=args.url)
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        message = render(result)
        if message:
            stream = sys.stderr if result["status"] == "stale" else sys.stdout
            print(message, file=stream)
    return result["exit_code"]


if __name__ == "__main__":
    sys.exit(main())
