"""The command line.

    tier1 list                  every experiment, and which build each one needs
    tier1 show t05-...          the recording, as the lesson shows it
    tier1 check                 the offline checks, which is what `just tier1` runs
    tier1 record                run every experiment in its image and rewrite the recordings
    tier1 verify                run them and compare against what is committed, without writing

`record` and `verify` need Docker and a couple of hundred megabytes of image. `list`, `show`
and `check` need nothing and take milliseconds, which is why they are the ones in `just
check` and the other two are a job of their own.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .checks import problems
from .experiments import EXPERIMENTS, find
from .recording import REPOSITORY, Recording, differences, show


def _list(args: argparse.Namespace) -> int:
    for one in EXPERIMENTS:
        print(f"{one.slug}  {one.lesson}  {one.build}")
        print(f"    {one.asks}")
        print(f"    needs it because {one.needs}")
    return 0


def _show(args: argparse.Namespace) -> int:
    print(show(args.slug, Path(args.root)))
    return 0


def _check(args: argparse.Namespace) -> int:
    found = problems(Path(args.root))
    print(f"{len(EXPERIMENTS)} Tier 1 experiment(s): {len(found)} problem(s)")
    for one in found:
        print(f"  {one}", file=sys.stderr)
    return 1 if found else 0


def _chosen(args: argparse.Namespace):
    return [find(one) for one in args.slugs] if args.slugs else list(EXPERIMENTS)


def _record(args: argparse.Namespace) -> int:
    from .run import Failed, record

    root = Path(args.root)
    for one in _chosen(args):
        try:
            fresh = record(one, lockfile=root / args.lockfile, docker=args.docker)
        except Failed as error:
            print(f"{one.slug}: {error}", file=sys.stderr)
            return 1
        print(f"{fresh.write(root)}: {len(fresh.output)} line(s) from {fresh.image}")
    return 0


def _verify(args: argparse.Namespace) -> int:
    """Run every experiment again and say whether the committed recording still holds.

    This is the half that runs against a real debug build in CI. It writes nothing, so a
    difference is reported rather than absorbed, which is the whole point of committing the
    recording in the first place.
    """
    from .run import Failed, record

    root = Path(args.root)
    found: list[str] = []
    for one in _chosen(args):
        committed = Recording.load(one.slug, root)
        try:
            fresh = record(one, lockfile=root / args.lockfile, docker=args.docker)
        except Failed as error:
            found.append(f"{one.slug}: {error}")
            continue
        for said in differences(committed, fresh):
            found.append(f"{one.slug}: {said}")
        print(f"{one.slug}: ran in {fresh.image}")
    for one in found:
        print(f"  {one}", file=sys.stderr)
    return 1 if found else 0


def build() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="tier1", description=__doc__)
    parser.add_argument("--root", default=str(REPOSITORY), help="the top of the repository")
    parser.add_argument(
        "--lockfile",
        default="images/cpython.lock.json",
        help="the image lockfile, relative to the root",
    )
    parser.add_argument("--docker", default="docker", help="the container command to use")
    subs = parser.add_subparsers(dest="command", required=True)

    named = subs.add_parser("list", help="every experiment and the build it needs")
    named.set_defaults(handler=_list)

    seen = subs.add_parser("show", help="one recording, as the lesson shows it")
    seen.add_argument("slug")
    seen.set_defaults(handler=_show)

    gate = subs.add_parser("check", help="the offline checks")
    gate.set_defaults(handler=_check)

    kept = subs.add_parser("record", help="run in the image and rewrite the recordings")
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
