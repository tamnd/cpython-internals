"""The bpcheck command.

Two exit codes, and the difference matters to CI. 1 means a blueprint is wrong, which is
the thing to branch on. 2 means the command was used wrong, which must not be mistaken for
a passing check that happened not to look at anything.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .document import DocumentError, find, load
from .rules import check, check_index

DEFAULT_ROOTS = ["blueprints"]
INDEX = "README.md"


def command_lint(args: argparse.Namespace) -> int:
    roots = [Path(path) for path in (args.paths or DEFAULT_ROOTS)]
    paths = find(roots)
    if not paths:
        print("no blueprints found", file=sys.stderr)
        return 0

    documents = []
    for path in paths:
        try:
            documents.append(load(path))
        except DocumentError as error:
            print(error, file=sys.stderr)
            return 1

    problems = []
    for document in documents:
        problems.extend(check(document))

    index = Path(roots[0]) / INDEX
    if index.is_file():
        problems.extend(check_index(index, index.read_text(encoding="utf-8"), documents))

    for problem in problems:
        print(problem, file=sys.stderr)
    print(f"{len(documents)} blueprint(s): {len(problems)} problem(s)")
    return 1 if problems else 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="bpcheck",
        description="Structural checks for the blueprint documents",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    lint = sub.add_parser("lint", help="check the structure every blueprint must have")
    lint.add_argument("paths", nargs="*", help=f"defaults to {' '.join(DEFAULT_ROOTS)}")
    lint.set_defaults(func=command_lint)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
