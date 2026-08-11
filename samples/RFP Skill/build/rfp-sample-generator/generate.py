#!/usr/bin/env python3
"""RFP Sample Generator — command-line entry point.

Generate fictional RFP requests and matching RFP responses for the made-up
vendor Aventra Software Group.

Examples
--------
    python generate.py pair
    python generate.py request --stdout
    python generate.py batch --count 5 --seed 42
    python generate.py response --industry government --project constituent-portal
    python generate.py --list
"""

import argparse
import random
import sys
from pathlib import Path

from rfpgen import data
from rfpgen.render_request import render as render_request
from rfpgen.render_response import render as render_response
from rfpgen.scenario import build_scenario


def _list_options() -> str:
    industries = ", ".join(sorted(data.CLIENTS))
    lines = ["Available industries:", f"  {industries}", "", "Available project types:"]
    for key, proj in sorted(data.PROJECTS.items()):
        inds = ", ".join(proj["industries"])
        lines.append(f"  {key:<20} {proj['label']}  (industries: {inds})")
    return "\n".join(lines)


def _write(out_dir: Path, name: str, content: str) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / name
    path.write_text(content, encoding="utf-8")
    return path


def _emit(args, kind: str, slug: str, content: str) -> None:
    """Print to stdout or write to a file, per args."""
    if args.stdout:
        if not getattr(_emit, "_first_done", False):
            _emit._first_done = True
        else:
            print("\n\n" + "=" * 78 + "\n")
        print(content)
    else:
        filename = f"rfp-{kind}_{slug}.md"
        path = _write(Path(args.out), filename, content)
        print(f"wrote {path}")


def cmd_request(args, rng) -> None:
    s = build_scenario(rng, industry=args.industry, project_key=args.project)
    _emit(args, "request", s.slug(), render_request(s))


def cmd_response(args, rng) -> None:
    s = build_scenario(rng, industry=args.industry, project_key=args.project)
    _emit(args, "response", s.slug(), render_response(s, rng))


def cmd_pair(args, rng) -> None:
    s = build_scenario(rng, industry=args.industry, project_key=args.project)
    _emit(args, "request", s.slug(), render_request(s))
    _emit(args, "response", s.slug(), render_response(s, rng))


def cmd_batch(args, rng) -> None:
    for _ in range(args.count):
        s = build_scenario(rng, industry=args.industry, project_key=args.project)
        _emit(args, "request", s.slug(), render_request(s))
        _emit(args, "response", s.slug(), render_response(s, rng))


COMMANDS = {
    "request": cmd_request,
    "response": cmd_response,
    "pair": cmd_pair,
    "batch": cmd_batch,
}


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Generate fictional RFP requests and responses.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument("--list", action="store_true", help="List industries and project types, then exit.")

    sub = p.add_subparsers(dest="command")

    def add_common(sp):
        sp.add_argument("--seed", type=int, default=None, help="Seed the RNG for reproducible output.")
        sp.add_argument("--out", default="output", help="Output directory (default: output).")
        sp.add_argument("--stdout", action="store_true", help="Print to the terminal instead of writing files.")
        sp.add_argument("--industry", default=None, help="Force a client industry.")
        sp.add_argument("--project", default=None, help="Force a project type.")

    for name in ("request", "response", "pair"):
        sp = sub.add_parser(name, help=f"Generate an RFP {name}.")
        add_common(sp)

    sp = sub.add_parser("batch", help="Generate multiple matched pairs.")
    add_common(sp)
    sp.add_argument("--count", type=int, default=3, help="How many pairs to generate (default: 3).")

    return p


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.list:
        print(_list_options())
        return 0

    if not args.command:
        parser.print_help()
        return 1

    rng = random.Random(args.seed)

    try:
        COMMANDS[args.command](args, rng)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
