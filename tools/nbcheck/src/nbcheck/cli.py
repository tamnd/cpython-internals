"""The nbcheck command.

Two exit codes, and the difference matters to CI. 1 means a notebook is wrong, which is
the thing to branch on. 2 means the command was used wrong, which must not be mistaken
for a passing check that happened not to look at anything.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .blocks import measurements
from .blocks import problems as shape_problems
from .notebook import NotebookError, find, load
from .rules import check
from .run import execute

DEFAULT_ROOTS = ["lessons"]


def _roots(args) -> list[Path]:
    return [Path(p) for p in (args.paths or DEFAULT_ROOTS)]


def command_lint(args) -> int:
    root = Path(args.root).resolve()
    notebooks = find(_roots(args))
    if not notebooks:
        print("no notebooks found", file=sys.stderr)
        return 0

    problems = []
    for path in notebooks:
        try:
            book = load(path)
        except NotebookError as error:
            print(error, file=sys.stderr)
            return 1
        problems.extend(check(book, root))

    for problem in problems:
        print(problem, file=sys.stderr)
    print(f"{len(notebooks)} notebook(s): {len(problems)} problem(s)")
    return 1 if problems else 0


def command_blocks(args) -> int:
    """Measure every lesson against the shape and the caps in the authoring guide.

    This prints the three numbers for every lesson whether or not anything is wrong, because
    the useful thing to know while writing is how much room is left, and a check that only
    speaks up at the moment you have gone over tells you that too late.
    """
    notebooks = find(_roots(args))
    if not notebooks:
        print("no notebooks found", file=sys.stderr)
        return 0

    problems = []
    print(f"{'lesson':40} {'hook':>6} {'tour':>6} {'lesson':>7}")
    for path in notebooks:
        try:
            book = load(path)
        except NotebookError as error:
            print(error, file=sys.stderr)
            return 1
        sizes = measurements(book)
        print(f"{path.parent.name:40} {sizes['hook']:6} {sizes['tour']:6} {sizes['lesson']:7}")
        problems.extend(f"{path}: {one}" for one in shape_problems(book, path))

    for problem in problems:
        print(problem, file=sys.stderr)
    print(f"{len(notebooks)} lesson(s): {len(problems)} problem(s)")
    return 1 if problems else 0


def command_run(args) -> int:
    notebooks = find(_roots(args))
    if not notebooks:
        print("no notebooks found", file=sys.stderr)
        return 0

    failures = []
    for path in notebooks:
        print(f"running {path}", flush=True)
        failure = execute(path, timeout=args.timeout)
        if failure is not None:
            failures.append(failure)
            print(failure, file=sys.stderr)

    print(f"{len(notebooks)} notebook(s): {len(failures)} failed")
    return 1 if failures else 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="nbcheck",
        description="Structural checks and execution for the lesson notebooks",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    lint = sub.add_parser("lint", help="check the structure every lesson notebook must have")
    lint.add_argument("paths", nargs="*", help=f"defaults to {' '.join(DEFAULT_ROOTS)}")
    lint.add_argument(
        "--root",
        default=".",
        help="the repository root, used to work out what the Colab badge should point at",
    )
    lint.set_defaults(func=command_lint)

    shape = sub.add_parser("blocks", help="the nine blocks, in order, within the word caps")
    shape.add_argument("paths", nargs="*", help=f"defaults to {' '.join(DEFAULT_ROOTS)}")
    shape.set_defaults(func=command_blocks)

    run = sub.add_parser("run", help="execute every cell and fail on the first cell that raises")
    run.add_argument("paths", nargs="*", help=f"defaults to {' '.join(DEFAULT_ROOTS)}")
    run.add_argument("--timeout", type=int, default=300, help="seconds per cell")
    run.set_defaults(func=command_run)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
