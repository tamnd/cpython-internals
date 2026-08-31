"""The command line.

    gdbrec list                 every session, and what each one is asking
    gdbrec show b02-...         one transcript, as the lesson shows it
    gdbrec check                the offline checks, which is what `just gdb` runs
    gdbrec record               run every session in the image and rewrite the transcripts
    gdbrec verify               run them and compare against what is committed, writing nothing

`record` and `verify` need Docker, a few hundred megabytes of image, and a machine of the
architecture being recorded. `list`, `show` and `check` need nothing and take milliseconds,
which is why they are the ones in `just check` and the other two are a job of their own.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .checks import problems
from .recording import REPOSITORY, Recording, differences, show
from .sessions import SESSIONS, find


def _list(args: argparse.Namespace) -> int:
    root = Path(args.root)
    for one in SESSIONS:
        arches = Recording.recorded_arches(one.slug, root) or ["nothing yet"]
        print(f"{one.slug}  {one.lesson}  {one.build}  {', '.join(arches)}")
        print(f"    {one.asks}")
        print(f"    {len(one.script)} command(s)")
    return 0


def _show(args: argparse.Namespace) -> int:
    print(show(args.slug, args.arch or _only(args), Path(args.root)))
    return 0


def _only(args: argparse.Namespace) -> str:
    """The architecture to read when nobody said, which is the one that was recorded."""
    arches = Recording.recorded_arches(args.slug, Path(args.root))
    if not arches:
        raise SystemExit(f"{args.slug}: nothing recorded on any architecture yet")
    return arches[0]


def _check(args: argparse.Namespace) -> int:
    found = problems(Path(args.root))
    print(f"{len(SESSIONS)} gdb session(s): {len(found)} problem(s)")
    for one in found:
        print(f"  {one}", file=sys.stderr)
    return 1 if found else 0


def _chosen(args: argparse.Namespace):
    return [find(one) for one in args.slugs] if args.slugs else list(SESSIONS)


def _record(args: argparse.Namespace) -> int:
    from .run import Failed, record

    root = Path(args.root)
    for one in _chosen(args):
        try:
            fresh = record(one, args.arch, lockfile=root / args.lockfile, docker=args.docker)
        except Failed as error:
            print(f"{one.slug}: {error}", file=sys.stderr)
            return 1
        lines = sum(len(step.output) for step in fresh.steps)
        print(f"{fresh.write(root)}: {len(fresh.steps)} command(s), {lines} line(s)")
    return 0


def _verify(args: argparse.Namespace) -> int:
    """Run every session again and say whether the committed transcript still holds.

    A session recorded on another architecture is skipped rather than failed. There is one
    machine per architecture and no honest way to check an arm64 backtrace from an amd64
    runner, so the alternative to skipping is a job that is red for everybody forever, which
    is a job people turn off.
    """
    from .run import Failed, here, record

    root = Path(args.root)
    arch = args.arch or here()
    found: list[str] = []
    ran = 0
    for one in _chosen(args):
        if arch not in Recording.recorded_arches(one.slug, root):
            print(f"{one.slug}: nothing recorded on {arch}, so there is nothing to check here")
            continue
        committed = Recording.load(one.slug, arch, root)
        try:
            fresh = record(one, arch, lockfile=root / args.lockfile, docker=args.docker)
        except Failed as error:
            found.append(f"{one.slug}: {error}")
            continue
        ran += 1
        for said in differences(committed, fresh):
            found.append(f"{one.slug}: {said}")
        print(f"{one.slug}: ran in {fresh.image}")
    print(f"{ran} session(s) checked on {arch}: {len(found)} difference(s)")
    for one in found:
        print(f"  {one}", file=sys.stderr)
    return 1 if found else 0


def build() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="gdbrec", description=__doc__)
    parser.add_argument("--root", default=str(REPOSITORY), help="the top of the repository")
    parser.add_argument(
        "--lockfile",
        default="images/cpython.lock.json",
        help="the image lockfile, relative to the root",
    )
    parser.add_argument("--docker", default="docker", help="the container command to use")
    parser.add_argument("--arch", default="", help="amd64 or arm64, defaulting to this machine")
    subs = parser.add_subparsers(dest="command", required=True)

    named = subs.add_parser("list", help="every session and what it asks")
    named.set_defaults(handler=_list)

    seen = subs.add_parser("show", help="one transcript, as the lesson shows it")
    seen.add_argument("slug")
    seen.set_defaults(handler=_show)

    gate = subs.add_parser("check", help="the offline checks")
    gate.set_defaults(handler=_check)

    kept = subs.add_parser("record", help="run in the image and rewrite the transcripts")
    kept.add_argument("slugs", nargs="*")
    kept.set_defaults(handler=_record)

    again = subs.add_parser("verify", help="run in the image and compare, writing nothing")
    again.add_argument("slugs", nargs="*")
    again.set_defaults(handler=_verify)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build().parse_args(argv)
    return int(args.handler(args))


if __name__ == "__main__":
    raise SystemExit(main())
