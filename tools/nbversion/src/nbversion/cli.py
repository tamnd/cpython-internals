"""The nbversion command.

Two subcommands because the two halves run on different interpreters. `record` runs on one
Python and writes down what it saw. `compare` runs on either and reads two of those
recordings. Trying to do both in one process would mean one of the two interpreters is a
subprocess, and then a failure to start it looks the same as a lesson that behaves
identically on both versions.

Exit codes follow the rest of the tools here. 1 means a lesson is wrong, 2 means the
command was used wrong, and 2 must never be mistaken for a check that passed because it
found nothing to look at.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from nbcheck.notebook import find

from .compare import notebooks, summary
from .declare import all_notes
from .record import DEFAULT_ROOT, load_all, run, version, write

DEFAULT_ROOTS = ["lessons"]


def _roots(args) -> list[Path]:
    return [Path(one) for one in (args.paths or DEFAULT_ROOTS)]


def command_record(args) -> int:
    found = find(_roots(args))
    if not found:
        print("no notebooks found", file=sys.stderr)
        return 2

    root = Path(args.into) / version()
    print(f"recording {len(found)} notebook(s) on Python {version()} into {root}")
    for path in found:
        print(f"running {path}", flush=True)
        write(run(path, timeout=args.timeout), root)
    print(f"wrote {len(found)} recording(s)")
    return 0


def command_compare(args) -> int:
    first, second = Path(args.first), Path(args.second)
    for one in (first, second):
        if not one.is_dir():
            print(f"{one} is not a directory of recordings", file=sys.stderr)
            return 2

    left, right = load_all(first), load_all(second)
    if not left and not right:
        print("there are no recordings to compare", file=sys.stderr)
        return 2

    declared = all_notes(find(_roots(args)))
    findings = notebooks(left, right, declared)
    for one in findings:
        stream = sys.stderr if one.failed else sys.stdout
        print(one.line(), file=stream)

    failures = [one for one in findings if one.failed]
    print(f"{len(left)} notebook(s) compared: {summary(findings)}")
    if failures:
        print(
            "a cell whose output depends on the version needs a `differs=` note on it, "
            "and a note whose cell no longer differs needs removing",
            file=sys.stderr,
        )
    return 1 if failures else 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="nbversion",
        description="Find the lesson cells whose output depends on which Python is running",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    record = sub.add_parser("record", help="execute the lessons and write down what they printed")
    record.add_argument("paths", nargs="*", help=f"defaults to {' '.join(DEFAULT_ROOTS)}")
    record.add_argument(
        "--into",
        default=str(DEFAULT_ROOT),
        help="where the recording goes, under a directory named after the version",
    )
    record.add_argument("--timeout", type=int, default=300, help="seconds per cell")
    record.set_defaults(func=command_record)

    compare = sub.add_parser("compare", help="diff two recordings and check the notes match")
    compare.add_argument("first", help="a directory written by `nbversion record`")
    compare.add_argument("second", help="the other one")
    compare.add_argument(
        "--paths",
        nargs="*",
        help=f"where the notebooks themselves are, defaults to {' '.join(DEFAULT_ROOTS)}",
    )
    compare.set_defaults(func=command_compare)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
