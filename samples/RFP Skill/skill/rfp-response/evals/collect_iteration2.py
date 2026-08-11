#!/usr/bin/env python3
"""Copy iteration-2 run outputs out of the isolated workspaces.

Runs happened in /tmp/eval2/<eval>/<arm>/workspace/ so the agents had no route
back to the repo (iteration 1's baselines found the catalog in
rfp-automation-kit and the comparison collapsed). This pulls just the produced
artefacts into the review workspace, leaving the isolation intact.
"""

import json
import shutil
from pathlib import Path

SRC = Path("/tmp/eval2")
DST = Path(__file__).resolve().parents[3] / "build" / "eval-runs" / "iteration-2"

NAMES = {
    "eval-0-clean-match-permitting-portal": "Clean match — permitting portal",
    "eval-1-ambiguous-match-uncovered-requirement": "Ambiguous match + uncovered requirement",
    "eval-2-prescribed-structure-under-budget": "Prescribed structure + under budget",
}
ARMS = {"with_skill": "skill + knowledge base",
        "without_skill": "skill, no knowledge base"}


def main():
    evals = json.load(open(Path(__file__).resolve().parent / "evals.json"))["evals"]
    prompts = {e["name"]: e["prompt"] for e in evals}

    for eval_dir, label in NAMES.items():
        key = eval_dir.split("-", 2)[2]
        for arm in ARMS:
            src = SRC / eval_dir / arm / "workspace" / "outputs"
            dst = DST / eval_dir / arm / "outputs"
            dst.mkdir(parents=True, exist_ok=True)
            if not src.exists():
                print(f"  MISSING {eval_dir}/{arm}")
                continue
            n = 0
            for f in src.iterdir():
                if f.is_file():
                    shutil.copy2(f, dst / f.name)
                    n += 1
            meta = dst.parent.parent / "eval_metadata.json"
            json.dump({"eval_id": list(NAMES).index(eval_dir),
                       "eval_name": key,
                       "prompt": prompts.get(key, ""),
                       "assertions": []},
                      open(meta, "w"), indent=2)
            print(f"  {n} file(s)  {eval_dir}/{arm}")


if __name__ == "__main__":
    main()
