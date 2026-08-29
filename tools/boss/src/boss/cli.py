"""The command line.

    boss list                       every fight, and what it asks for
    boss check                      the checks that run nothing, which is what `just boss` runs
    boss verify                     run the grader against the known good and known bad ones
    boss grade t05 answer.py        grade a file, the way a reader does

`check` and `verify` are both fast enough for every pull request, so both are in `just boss`.
`grade` is here for convenience while writing a fight: it finds the grader for you, which is
the only thing it does that running `python lessons/.../grade.py` yourself does not.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .checks import problems
from .fights import FIGHTS, REPOSITORY, Unknown, find
from .run import graded, verdicts


def _list(args: argparse.Namespace) -> int:
    root = Path(args.root)
    for one in FIGHTS:
        print(f"{one.code}  {one.lesson}")
        print(f"    {one.asks}")
        print(f"    run it with: python {one.grader(root).relative_to(root)} answer.py")
    return 0


def _check(args: argparse.Namespace) -> int:
    found = problems(Path(args.root))
    print(f"{len(FIGHTS)} boss fight(s): {len(found)} problem(s)")
    for one in found:
        print(f"  {one}", file=sys.stderr)
    return 1 if found else 0


def _verify(args: argparse.Namespace) -> int:
    root = Path(args.root)
    chosen = [find(one) for one in args.codes] if args.codes else list(FIGHTS)
    found: list[str] = []
    for fight in chosen:
        said = verdicts(fight, root, seeds=args.seeds)
        found += said
        ran = args.seeds * 2
        over = f"{args.seeds} seed(s)"
        print(f"{fight.code}: {ran} grading run(s) over {over}, {len(said)} problem(s)")
    for one in found:
        print(f"  {one}", file=sys.stderr)
    return 1 if found else 0


def _grade(args: argparse.Namespace) -> int:
    root = Path(args.root)
    ran = graded(find(args.code), Path(args.submission), root, seed=args.seed)
    print(ran.output, end="")
    return ran.code


def build() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="boss", description=__doc__)
    parser.add_argument("--root", default=str(REPOSITORY), help="the top of the repository")
    subs = parser.add_subparsers(dest="command", required=True)

    named = subs.add_parser("list", help="every fight and how to run it")
    named.set_defaults(handler=_list)

    gate = subs.add_parser("check", help="the checks that run nothing")
    gate.set_defaults(handler=_check)

    again = subs.add_parser("verify", help="run the known good and known bad submissions")
    again.add_argument("codes", nargs="*", help="lesson codes, or all of them by default")
    again.add_argument(
        "--seeds",
        type=int,
        default=1,
        help="how many seeds to grade over, starting at zero",
    )
    again.set_defaults(handler=_verify)

    one = subs.add_parser("grade", help="grade a file against a fight")
    one.add_argument("code", help="the lesson code, such as t05")
    one.add_argument("submission", help="your file, the one with predict() in it")
    one.add_argument("--seed", type=int, default=0)
    one.set_defaults(handler=_grade)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build().parse_args(argv)
    try:
        return int(args.handler(args))
    except Unknown as problem:
        print(problem, file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
