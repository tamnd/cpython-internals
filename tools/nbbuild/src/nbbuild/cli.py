"""The nbbuild command.

`nbbuild build` regenerates every lesson notebook from its builder. `nbbuild check` runs
the same builders and fails if a committed notebook has drifted from the code that is
supposed to produce it, which is the check CI cares about: without it, somebody edits a
cell in Jupyter, commits the notebook, and the builder quietly becomes fiction.

`nbbuild claims` collects the claim ledger out of every builder and writes it to
`lessons/CLAIMS.md`, and with `--check` fails if the committed file has drifted. A builder
whose claims no longer have runnable cells behind them fails on its own, before this gets
near it, because `Lesson.save` resolves them in both modes.

Each builder runs in its own process. They are ordinary scripts that a person is expected
to run directly while writing a lesson, and importing them here instead would mean a
builder behaves differently under the command than it does on its own.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from .claims import render

BUILDER = "build.py"
DEFAULT_ROOT = "lessons"
LEDGER = "CLAIMS.md"


def builders(root: Path) -> list[Path]:
    """Every lesson builder, in lesson order.

    Sorted by path, which for `t01`, `t02` and so on is also the order a reader meets them
    in. That keeps the output of a failing run readable rather than shuffled.
    """
    return sorted(root.glob(f"*/{BUILDER}"))


def _run(path: Path, arguments: list[str]) -> int:
    result = subprocess.run([sys.executable, str(path), *arguments], check=False)
    return result.returncode


def command_claims(args) -> int:
    """Build the ledger from every builder, and write it or check it.

    Each builder is asked for its own claims as JSON, in the same separate process the other
    commands use. Importing them here would be less code and would mean a builder behaves
    differently under this command than it does when an author runs it directly, which is the
    kind of difference that only shows up on the day it matters.
    """
    root = Path(args.root)
    found = builders(root)
    entries = []
    for path in found:
        result = subprocess.run(
            [sys.executable, str(path), "--claims"], capture_output=True, text=True, check=False
        )
        if result.returncode != 0:
            print(result.stdout + result.stderr, file=sys.stderr)
            print(f"{path} could not report its claims", file=sys.stderr)
            return 1
        entries.append(json.loads(result.stdout))

    ledger = root / LEDGER
    text = render(entries)
    counted = sum(len(one["claims"]) for one in entries)
    if args.check:
        if not ledger.exists() or ledger.read_text() != text:
            print(f"{ledger} is out of date, run `just build-claims`", file=sys.stderr)
            return 1
        print(f"{ledger} is up to date, {counted} claims")
        return 0
    ledger.write_text(text)
    print(f"wrote {ledger}, {counted} claims across {len(entries)} lessons")
    return 0


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

    ledger = sub.add_parser("claims", help="write or check the claim ledger")
    ledger.add_argument("--root", default=DEFAULT_ROOT, help="the lessons directory")
    ledger.add_argument("--check", action="store_true", help="fail rather than rewrite it")
    ledger.set_defaults(func=command_claims)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
