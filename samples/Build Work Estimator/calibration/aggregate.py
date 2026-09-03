#!/usr/bin/env python3
"""Rebuild baseline.json from contributed community calibration records.

Author: Dewain Robinson

    python aggregate.py                 # community/ -> baseline.json

Each file in community/ is one anonymized record contributed through
contribute.py. This rolls them into per-bucket correction ratios that ship
with the plugin, so an install with no local history starts from something
better than a published population average.

Buckets below MIN_CONFIDENT_N are published but flagged: the plugin will not
apply a community correction that thin.
"""

__author__ = "Dewain Robinson"

import argparse
import json
import os
import statistics
import sys

MIN_CONFIDENT_N = 5
HERE = os.path.dirname(os.path.abspath(__file__))


def parse_record(path):
    """Read one contributed record. Returns None if it is unusable.

    A malformed contribution must never break the build -- it is skipped and
    counted, so a bad PR degrades the dataset rather than the tool.
    """
    try:
        import yaml
        with open(path, "r") as fh:
            data = yaml.safe_load(fh)
    except Exception:
        return None
    if not isinstance(data, dict):
        return None
    try:
        ratio = float(data["ratio"])
        size = str(data["size"])
    except (KeyError, TypeError, ValueError):
        return None
    if ratio <= 0 or size in ("", "unknown"):
        return None
    return {
        "size": size,
        "ratio": ratio,
        "harness": str(data.get("harness", "none")),
        "model_tier": str(data.get("model_tier", "unknown")),
        "brownfield": bool(data.get("brownfield", False)),
    }


def quartiles(values):
    ordered = sorted(values)
    if len(ordered) < 4:
        return ordered[0], ordered[-1]
    mid = len(ordered) // 2
    lower = ordered[:mid]
    upper = ordered[mid + 1:] if len(ordered) % 2 else ordered[mid:]
    return statistics.median(lower), statistics.median(upper)


def aggregate(community_dir=None):
    community_dir = community_dir or os.path.join(HERE, "community")
    by_bucket = {}
    skipped = 0
    total = 0

    if os.path.isdir(community_dir):
        for name in sorted(os.listdir(community_dir)):
            if not name.endswith((".yaml", ".yml")):
                continue
            total += 1
            record = parse_record(os.path.join(community_dir, name))
            if record is None:
                skipped += 1
                continue
            by_bucket.setdefault(record["size"], []).append(record["ratio"])

    buckets = {}
    for size, ratios in sorted(by_bucket.items()):
        n = len(ratios)
        q1, q3 = quartiles(ratios)
        buckets[size] = {
            "n": n,
            "median_ratio": round(statistics.median(ratios), 4),
            "iqr": [round(q1, 4), round(q3, 4)],
            "confident": n >= MIN_CONFIDENT_N,
        }

    return {
        "schema": 1,
        # The dataset file is an authored artifact of this sample. The records
        # aggregated into it are anonymous by design and carry no attribution
        # -- see docs/CONTRIBUTING-CALIBRATION.md.
        "author": __author__,
        "min_confident_n": MIN_CONFIDENT_N,
        "records": total - skipped,
        "skipped": skipped,
        "buckets": buckets,
        "note": (
            "Community-contributed build calibration. Self-selected, not a "
            "representative sample of anyone's work. Useful as a fallback for "
            "installs with no local history; never better than a user's own "
            "measured profile."
        ),
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--community", default=None)
    ap.add_argument("--out", default=os.path.join(HERE, "baseline.json"))
    args = ap.parse_args(argv)

    baseline = aggregate(args.community)
    with open(args.out, "w") as fh:
        json.dump(baseline, fh, indent=2, sort_keys=True)
    print("Wrote %s (%d records, %d skipped, %d buckets)"
          % (args.out, baseline["records"], baseline["skipped"],
             len(baseline["buckets"])))
    thin = [b for b, d in baseline["buckets"].items() if not d["confident"]]
    if thin:
        print("Low-confidence buckets (n < %d), published but not applied: %s"
              % (MIN_CONFIDENT_N, ", ".join(sorted(thin))))
    return 0


if __name__ == "__main__":
    sys.exit(main())
