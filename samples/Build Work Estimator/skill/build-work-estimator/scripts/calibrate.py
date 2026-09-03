#!/usr/bin/env python3
"""Derive real cost constants from this machine's own session history.

Author: Dewain Robinson

The estimator's whole premise is that measured constants beat assumed ones.
This is where the measuring happens: it reads local Claude Code transcripts,
prices every API response at list rates, and emits an aggregate profile.

    python calibrate.py                    # write ~/.claude/build-work-estimator/profile.json
    python calibrate.py --print            # also dump a readable summary
    python calibrate.py --root DIR         # scan somewhere else (tests)

PRIVACY: the profile holds aggregates only -- no file paths, project names,
prompts, or responses. It is written to the user's home directory and is never
transmitted. `contribute.py` is the only path that sends anything anywhere,
and it builds its payload from an allowlist rather than from this file.
"""

__author__ = "Dewain Robinson"

import argparse
import glob
import json
import os
import statistics
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rates  # noqa: E402

SCHEMA = 1
EDIT_TOOLS = ("Edit", "Write", "NotebookEdit")

#: (label, min_files, max_files) -- inclusive. Ordered; first match wins.
BUCKETS = (
    ("exploration", 0, 0),
    ("trivial", 1, 1),
    ("small", 2, 5),
    ("medium", 6, 15),
    ("large", 16, 50),
    ("subsystem", 51, 10 ** 9),
)

#: Manifest `size:` values map straight onto bucket labels.
SIZE_TO_BUCKET = {
    "exploration": "exploration",
    "trivial": "trivial",
    "small": "small",
    "medium": "medium",
    "large": "large",
    "subsystem": "subsystem",
}


def default_root():
    return os.path.expanduser("~/.claude/projects")


def profile_path():
    return os.path.expanduser("~/.claude/build-work-estimator/profile.json")


def bucket_for(n_files):
    for label, lo, hi in BUCKETS:
        if lo <= n_files <= hi:
            return label
    return BUCKETS[-1][0]


def _iter_records(path):
    """Yield parsed JSON objects from a JSONL transcript, skipping junk.

    Transcripts can be truncated mid-write, so an unparseable line is normal
    and is not an error worth surfacing.
    """
    try:
        handle = open(path, "r", encoding="utf-8", errors="replace")
    except (IOError, OSError):
        return
    with handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except ValueError:
                continue


def _usage_tokens(usage):
    """Normalise a usage block into (input, cache_read, write_5m, write_1h, output)."""
    inp = usage.get("input_tokens") or 0
    out = usage.get("output_tokens") or 0
    read = usage.get("cache_read_input_tokens") or 0
    creation = usage.get("cache_creation") or {}
    w5 = creation.get("ephemeral_5m_input_tokens") or 0
    w1 = creation.get("ephemeral_1h_input_tokens") or 0
    if not (w5 or w1):
        # Older transcripts carry only the flat total; treat it as 5m.
        w5 = usage.get("cache_creation_input_tokens") or 0
    return inp, read, w5, w1, out


def scan_session(paths, is_subagent):
    """Accumulate one session's worth of transcript files."""
    acc = {
        "turns": 0, "sub_turns": 0, "cost": 0.0, "sub_cost": 0.0,
        "output": 0, "cache_read": 0, "fresh": 0, "contexts": [],
        "files": set(), "models": {}, "unpriced": 0, "timestamps": [],
    }
    for path in paths:
        seen = set()
        for record in _iter_records(path):
            stamp = record.get("timestamp")
            if stamp:
                acc["timestamps"].append(stamp)
            if record.get("type") != "assistant":
                continue
            message = record.get("message") or {}
            usage = message.get("usage")
            if not usage:
                continue
            key = record.get("requestId") or record.get("uuid")
            if key in seen:
                continue
            seen.add(key)

            model = message.get("model")
            inp, read, w5, w1, out = _usage_tokens(usage)
            cost = rates.price_response(model, inp, read, w5, w1, out)
            if cost is None:
                acc["unpriced"] += 1
                continue

            acc["models"][model] = acc["models"].get(model, 0) + 1
            acc["output"] += out
            if is_subagent(path):
                acc["sub_turns"] += 1
                acc["sub_cost"] += cost
            else:
                acc["turns"] += 1
                acc["cost"] += cost
                acc["contexts"].append(inp + read + w5 + w1)
                acc["cache_read"] += read
                acc["fresh"] += inp + w5 + w1
                for block in message.get("content") or []:
                    if not isinstance(block, dict):
                        continue
                    if block.get("type") == "tool_use" and \
                            block.get("name") in EDIT_TOOLS:
                        target = (block.get("input") or {}).get("file_path")
                        if target:
                            acc["files"].add(target)
    return acc


def collect(root=None):
    """Group transcript files by session id and scan each."""
    root = root or default_root()
    sessions = {}

    for path in glob.glob(os.path.join(root, "*", "*.jsonl")):
        sid = os.path.basename(path)[:-6]
        sessions.setdefault(sid, {"main": [], "sub": []})["main"].append(path)

    # Subagent transcripts live at <project>/<session-id>/subagents/*.jsonl
    for path in glob.glob(os.path.join(root, "*", "*", "subagents", "*.jsonl")):
        sid = os.path.basename(os.path.dirname(os.path.dirname(path)))
        sessions.setdefault(sid, {"main": [], "sub": []})["sub"].append(path)

    out = {}
    for sid, group in sessions.items():
        sub_paths = set(group["sub"])
        acc = scan_session(
            group["main"] + group["sub"],
            is_subagent=lambda p, s=sub_paths: p in s,
        )
        # Keep sessions whose only records were unpriced: dropping them would
        # silently lose the unknown-model count that the report depends on to
        # disclose incomplete coverage.
        if acc["turns"] or acc["sub_turns"] or acc["unpriced"]:
            out[sid] = acc
    return out


def build_profile(sessions, generated=None):
    """Turn scanned sessions into the profile the estimator consumes."""
    live = [s for s in sessions.values() if s["turns"] > 0]
    # Counted across every scanned session, including ones with no priceable
    # turns at all -- otherwise a history full of unknown models would report
    # zero unpriced records, which is the opposite of the truth.
    unpriced_total = sum(s["unpriced"] for s in sessions.values())
    if not live:
        profile = fallback_profile(generated)
        profile["unpriced_records"] = unpriced_total
        return profile

    total_cost = sum(s["cost"] + s["sub_cost"] for s in live)
    total_turns = sum(s["turns"] for s in live)
    total_sub_turns = sum(s["sub_turns"] for s in live)
    total_output = sum(s["output"] for s in live)
    read = sum(s["cache_read"] for s in live)
    fresh = sum(s["fresh"] for s in live)
    main_cost = sum(s["cost"] for s in live)

    contexts = []
    for s in live:
        contexts.extend(s["contexts"])

    models = {}
    for s in live:
        for model, n in s["models"].items():
            models[model] = models.get(model, 0) + n
    model_turns = sum(models.values()) or 1

    buckets = {}
    for s in live:
        label = bucket_for(len(s["files"]))
        buckets.setdefault(label, []).append(
            {"turns": s["turns"], "cost": s["cost"] + s["sub_cost"]}
        )

    bucket_rows = []
    for label, _lo, _hi in BUCKETS:
        rows = buckets.get(label)
        if not rows:
            continue
        costs = sorted(r["cost"] for r in rows)
        turns = sorted(r["turns"] for r in rows)
        bucket_rows.append({
            "label": label,
            "n": len(rows),
            "median_turns": statistics.median(turns),
            "median_cost": round(statistics.median(costs), 4),
            "min_cost": round(costs[0], 4),
            "max_cost": round(costs[-1], 4),
        })

    stamps = []
    for s in live:
        stamps.extend(s["timestamps"])
    stamps.sort()

    return {
        "schema": SCHEMA,
        "generated": generated or _now(),
        "source": "measured",
        "sessions": len(live),
        "date_range": [stamps[0][:10], stamps[-1][:10]] if stamps else None,
        "cost_per_main_turn": round(total_cost / total_turns, 6),
        "median_context_tokens": int(statistics.median(contexts)) if contexts else 0,
        "mean_output_tokens_per_turn": int(
            total_output / (total_turns + total_sub_turns)
        ) if (total_turns + total_sub_turns) else 0,
        "cache_hit_rate": round(read / (read + fresh), 4) if (read + fresh) else 0.0,
        "subagent_multiplier": round(total_cost / main_cost, 4) if main_cost else 1.0,
        "model_mix": dict(
            (m, round(n / model_turns, 4)) for m, n in sorted(
                models.items(), key=lambda kv: -kv[1])
        ),
        "unpriced_records": unpriced_total,
        "buckets": bucket_rows,
        "corrections": {},
    }


def fallback_profile(generated=None):
    """Published-baseline profile, used when there is no local history.

    Materially less reliable than a measured profile. Every report built on
    this must say so -- that is why `source` is mandatory in the schema.
    """
    base = rates.PUBLISHED_BASELINE
    # A developer-day is treated as roughly one medium unit of work. This is a
    # published population average, not a measurement of anyone in particular.
    day = base["cost_per_developer_active_day"]
    high = base["p90_cost_per_active_day"]
    scale = {
        "exploration": 0.25, "trivial": 1.0, "small": 3.0,
        "medium": 10.0, "large": 32.0, "subsystem": 90.0,
    }
    bucket_rows = []
    for label, _lo, _hi in BUCKETS:
        turns = scale[label]
        bucket_rows.append({
            "label": label,
            "n": 0,
            "median_turns": round(turns * 8),
            "median_cost": round(day * turns / 10.0, 4),
            "min_cost": round(day * turns / 10.0 * 0.3, 4),
            "max_cost": round(high * turns / 10.0 * 1.6, 4),
        })
    return {
        "schema": SCHEMA,
        "generated": generated or _now(),
        "source": "published-baseline",
        "sessions": 0,
        "date_range": None,
        "cost_per_main_turn": round(day / 33.0, 6),
        "median_context_tokens": 0,
        "mean_output_tokens_per_turn": 0,
        "cache_hit_rate": 0.0,
        "subagent_multiplier": 1.0,
        "model_mix": {},
        "unpriced_records": 0,
        "buckets": bucket_rows,
        "corrections": {},
        "baseline_source": rates.PUBLISHED_BASELINE_SOURCE,
    }


def _now():
    import datetime
    return datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def load_profile(path=None):
    """Read the saved profile, or build a fallback if none exists."""
    path = path or profile_path()
    try:
        with open(path, "r") as fh:
            return json.load(fh)
    except (IOError, OSError, ValueError):
        return fallback_profile()


def save_profile(profile, path=None):
    path = path or profile_path()
    directory = os.path.dirname(path)
    if directory and not os.path.isdir(directory):
        os.makedirs(directory)
    # Preserve corrections learned from recorded actuals across recalibration.
    existing = None
    try:
        with open(path, "r") as fh:
            existing = json.load(fh)
    except (IOError, OSError, ValueError):
        pass
    if existing and existing.get("corrections") and not profile.get("corrections"):
        profile["corrections"] = existing["corrections"]
    with open(path, "w") as fh:
        json.dump(profile, fh, indent=2, sort_keys=True)
    return path


def summarise(profile):
    lines = []
    lines.append("Calibration source : %s" % profile["source"])
    if profile["source"] == "measured":
        lines.append("Sessions           : %d" % profile["sessions"])
        if profile.get("date_range"):
            lines.append("Date range         : %s .. %s" % tuple(profile["date_range"]))
        lines.append("Cost per turn      : $%.3f" % profile["cost_per_main_turn"])
        lines.append("Median context     : %sk tokens"
                     % format(profile["median_context_tokens"] // 1000, ","))
        lines.append("Cache hit rate     : %.1f%%" % (profile["cache_hit_rate"] * 100))
        lines.append("Subagent multiplier: %.2fx" % profile["subagent_multiplier"])
        if profile.get("unpriced_records"):
            lines.append("Unpriced records   : %d (unknown model ids, skipped)"
                         % profile["unpriced_records"])
    else:
        lines.append("No local session history found. Using published baselines,")
        lines.append("which are materially less reliable than a measured profile.")
    lines.append("")
    lines.append("%-13s %4s %11s %11s %11s %11s"
                 % ("bucket", "n", "med turns", "med cost", "min", "max"))
    for row in profile["buckets"]:
        lines.append("%-13s %4d %11.0f %11.2f %11.2f %11.2f"
                     % (row["label"], row["n"], row["median_turns"],
                        row["median_cost"], row["min_cost"], row["max_cost"]))
    weak = [r["label"] for r in profile["buckets"] if 0 < r["n"] < 3]
    if weak:
        lines.append("")
        lines.append("Thin buckets (n<3), medians are weak: %s" % ", ".join(weak))
    return "\n".join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--root", default=None, help="session history root")
    ap.add_argument("--out", default=None, help="profile output path")
    ap.add_argument("--print", dest="show", action="store_true")
    args = ap.parse_args(argv)

    sessions = collect(args.root)
    profile = build_profile(sessions)
    path = save_profile(profile, args.out)

    print("Wrote %s (%s, %d sessions)"
          % (path, profile["source"], profile["sessions"]))
    for warning in rates.staleness_warnings():
        print("WARNING  " + warning)
    if args.show:
        print()
        print(summarise(profile))
    return 0


if __name__ == "__main__":
    sys.exit(main())
