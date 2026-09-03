#!/usr/bin/env python3
"""Record what a build ACTUALLY cost, so future estimates get better.

Author: Dewain Robinson

Every estimate is a prediction. Without recording the outcome, the estimator
cannot improve -- and this sample would be repeating the mistake it exists to
demonstrate.

    python record_actual.py --list
    python record_actual.py est_20260903T101500_a1b2c3 --sessions ID [ID ...]
    python record_actual.py est_20260903T101500_a1b2c3        # confirm candidates

Session attribution is never guessed. Without --sessions the candidates are
listed and confirmation is required, because a wrong attribution poisons the
correction factors for every future estimate.
"""

__author__ = "Dewain Robinson"

import argparse
import json
import os
import statistics
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import calibrate  # noqa: E402
import estimate as estimate_mod  # noqa: E402


class RecordError(Exception):
    """Raised for input the user must fix."""


def load_ledger(path=None):
    path = path or estimate_mod.ledger_path()
    try:
        with open(path, "r") as fh:
            return json.load(fh)
    except (IOError, OSError, ValueError):
        return {"schema": 1, "estimates": []}


def save_ledger(ledger, path=None):
    path = path or estimate_mod.ledger_path()
    directory = os.path.dirname(path)
    if directory and not os.path.isdir(directory):
        os.makedirs(directory)
    with open(path, "w") as fh:
        json.dump(ledger, fh, indent=2)
    return path


def find_estimate(ledger, estimate_id):
    for entry in ledger.get("estimates", []):
        if entry.get("estimate_id") == estimate_id:
            return entry
    known = [e.get("estimate_id") for e in ledger.get("estimates", [])][-10:]
    raise RecordError(
        "No estimate with id %r in the ledger.\n\nRecent ids:\n  %s"
        % (estimate_id, "\n  ".join(known) if known else "(ledger is empty)")
    )


def candidate_sessions(sessions, since):
    """Sessions whose activity starts on or after the estimate was made."""
    out = []
    for sid, acc in sessions.items():
        stamps = sorted(acc.get("timestamps") or [])
        if not stamps:
            continue
        if stamps[-1] >= since:
            out.append({
                "session_id": sid,
                "start": stamps[0][:19],
                "end": stamps[-1][:19],
                "turns": acc["turns"],
                "cost": round(acc["cost"] + acc["sub_cost"], 2),
                "files": len(acc["files"]),
            })
    out.sort(key=lambda row: row["start"])
    return out


def measure(sessions, session_ids):
    """Total turns and cost across the confirmed session ids."""
    missing = [s for s in session_ids if s not in sessions]
    if missing:
        raise RecordError(
            "These session ids were not found in the history: %s"
            % ", ".join(missing)
        )
    turns = sum(sessions[s]["turns"] for s in session_ids)
    cost = sum(sessions[s]["cost"] + sessions[s]["sub_cost"] for s in session_ids)
    files = set()
    for s in session_ids:
        files |= sessions[s]["files"]
    return {
        "sessions": list(session_ids),
        "actual_turns": turns,
        "actual_cost": round(cost, 2),
        "actual_files": len(files),
    }


def apply_to_ledger(entry, actual):
    predicted = entry["predicted"]
    est_turns = sum(i["turns"] for i in predicted["items"]) or 1
    entry["actual"] = dict(actual)
    entry["actual"]["estimated_turns"] = est_turns
    entry["actual"]["estimated_cost"] = predicted["base"]
    entry["actual"]["turn_ratio"] = round(
        float(actual["actual_turns"]) / est_turns, 4)
    entry["actual"]["cost_ratio"] = round(
        actual["actual_cost"] / predicted["base"], 4) if predicted["base"] else None
    return entry


def rebuild_corrections(ledger):
    """Per-bucket median observed ratio, from every recorded actual.

    A multi-item estimate attributes its single observed ratio to each bucket
    it contains. That is coarse, and it is why shrinkage exists.
    """
    by_bucket = {}
    for entry in ledger.get("estimates", []):
        actual = entry.get("actual")
        if not actual or not actual.get("turn_ratio"):
            continue
        buckets = set(i["bucket"] for i in entry["predicted"]["items"])
        for bucket in buckets:
            by_bucket.setdefault(bucket, []).append(actual["turn_ratio"])

    corrections = {}
    for bucket, ratios in by_bucket.items():
        n = len(ratios)
        median = statistics.median(ratios)
        corrections[bucket] = {
            "n": n,
            "median_ratio": round(median, 4),
            "shrunk_ratio": round(estimate_mod.shrunk_ratio(median, n), 4),
            "applied": n >= estimate_mod.CORRECTION_MIN_N,
        }
    return corrections


def record(estimate_id, session_ids, root=None, ledger_file=None,
           profile_file=None):
    """Attach an actual to an estimate and refresh correction factors."""
    ledger = load_ledger(ledger_file)
    entry = find_estimate(ledger, estimate_id)
    sessions = calibrate.collect(root)
    actual = measure(sessions, session_ids)
    apply_to_ledger(entry, actual)

    corrections = rebuild_corrections(ledger)
    save_ledger(ledger, ledger_file)

    profile = calibrate.load_profile(profile_file)
    profile["corrections"] = corrections
    calibrate.save_profile(profile, profile_file)

    return {"entry": entry, "corrections": corrections}


def render(result):
    entry = result["entry"]
    actual = entry["actual"]
    out = []
    out.append("Recorded actual for %s (%s)"
               % (entry["estimate_id"], entry["project"]))
    out.append("")
    out.append("  estimated turns : %s" % format(actual["estimated_turns"], ","))
    out.append("  actual turns    : %s" % format(actual["actual_turns"], ","))
    out.append("  turn ratio      : %.2fx" % actual["turn_ratio"])
    out.append("  estimated cost  : $%s" % format(actual["estimated_cost"], ",.2f"))
    out.append("  actual cost     : $%s" % format(actual["actual_cost"], ",.2f"))
    if actual.get("cost_ratio"):
        out.append("  cost ratio      : %.2fx" % actual["cost_ratio"])
    out.append("")
    out.append("Correction factors now in effect:")
    out.append("")
    out.append("  %-12s %4s %12s %12s %9s"
               % ("bucket", "n", "median", "shrunk", "applied"))
    for bucket, data in sorted(result["corrections"].items()):
        out.append("  %-12s %4d %12.2f %12.2f %9s"
                   % (bucket, data["n"], data["median_ratio"],
                      data["shrunk_ratio"], "yes" if data["applied"] else "no"))
    provisional = [b for b, d in result["corrections"].items() if not d["applied"]]
    if provisional:
        out.append("")
        out.append("Provisional (n < %d), computed but not applied: %s"
                   % (estimate_mod.CORRECTION_MIN_N, ", ".join(sorted(provisional))))
        out.append("A single actual is a sample of size one; applying it raw "
                   "would be the")
        out.append("over-confidence this estimator exists to avoid.")
    out.append("")
    out.append("Consider contributing this anonymized result so the shipped "
               "baseline improves:")
    out.append("  python contribute.py %s" % entry["estimate_id"])
    return "\n".join(out)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("estimate_id", nargs="?")
    ap.add_argument("--sessions", nargs="*", default=None)
    ap.add_argument("--list", action="store_true", help="list ledger estimates")
    ap.add_argument("--root", default=None)
    ap.add_argument("--ledger", default=None)
    ap.add_argument("--profile", default=None)
    ap.add_argument("--yes", action="store_true",
                    help="accept the listed candidate sessions")
    args = ap.parse_args(argv)

    ledger = load_ledger(args.ledger)

    if args.list or not args.estimate_id:
        entries = ledger.get("estimates", [])
        if not entries:
            print("Ledger is empty. Run estimate.py first.")
            return 0
        print("%-32s %-20s %-10s %s"
              % ("estimate_id", "generated", "actual?", "project"))
        for entry in entries:
            print("%-32s %-20s %-10s %s"
                  % (entry["estimate_id"], entry["generated"][:19],
                     "yes" if entry.get("actual") else "no", entry["project"]))
        return 0

    try:
        entry = find_estimate(ledger, args.estimate_id)
        session_ids = args.sessions
        if not session_ids:
            sessions = calibrate.collect(args.root)
            candidates = candidate_sessions(sessions, entry["generated"])
            if not candidates:
                raise RecordError(
                    "No sessions found on or after %s. Pass --sessions "
                    "explicitly." % entry["generated"][:19])
            print("Candidate sessions active since the estimate was made:")
            print()
            print("  %-38s %-20s %7s %10s %6s"
                  % ("session_id", "start", "turns", "cost", "files"))
            for row in candidates:
                print("  %-38s %-20s %7d %10.2f %6d"
                      % (row["session_id"], row["start"], row["turns"],
                         row["cost"], row["files"]))
            print()
            print("Attribution is never guessed -- a wrong one poisons every "
                  "future estimate.")
            if not args.yes:
                print("Re-run with the ids that belong to this build:")
                print("  python record_actual.py %s --sessions <id> [<id> ...]"
                      % args.estimate_id)
                return 1
            session_ids = [row["session_id"] for row in candidates]

        result = record(args.estimate_id, session_ids, root=args.root,
                        ledger_file=args.ledger, profile_file=args.profile)
    except RecordError as exc:
        print("ERROR  %s" % exc, file=sys.stderr)
        return 1

    print(render(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
