"""The nbbuild command.

`nbbuild build` regenerates every lesson notebook from its builder. `nbbuild check` runs
the same builders and fails if a committed notebook has drifted from the code that is
supposed to produce it, which is the check CI cares about: without it, somebody edits a
cell in Jupyter, commits the notebook, and the builder quietly becomes fiction.

Each builder runs in its own process. They are ordinary scripts that a person is expected
to run directly while writing a lesson, and importing them here instead would mean a
builder behaves differently under the command than it does on its own.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

BUILDER = "build.py"
DEFAULT_ROOT = "lessons"


def builders(root: Path) -> list[Path]:
    """Every lesson builder, in lesson order.

    Sorted by path, which for `t01`, `t02` and so on is also the order a reader meets them
    in. That keeps the output of a failing run readable rather than shuffled.
    """
    return sorted(root.glob(f"*/{BUILDER}"))


def _run(path: Path, arguments: list[str]) -> int:
    result = subprocess.run([sys.executable, str(path), *arguments], check=False)
    return result.returncode


def command_build(args) -> int:
    return _each(args, [])


def command_check(args) -> int:
    return _each(args, ["--check"])


def _each(args, arguments: list[str]) -> int:
    root = Path(args.root)
    found = builders(root)
    if not found:
        print(f"no {BUILDER} under {root}", file=sys.stderr)
        return 0

    failed = [path for path in found if _run(path, arguments) != 0]
    print(f"{len(found)} lesson(s): {len(failed)} failed")
    return 1 if failed else 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="nbbuild",
        description="Build the lesson notebooks from the Python files that define them",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    build = sub.add_parser("build", help="regenerate every lesson notebook")
    build.add_argument("--root", default=DEFAULT_ROOT, help="the lessons directory")
    build.set_defaults(func=command_build)

    check = sub.add_parser("check", help="fail if a notebook no longer matches its builder")
    check.add_argument("--root", default=DEFAULT_ROOT, help="the lessons directory")
    check.set_defaults(func=command_check)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
