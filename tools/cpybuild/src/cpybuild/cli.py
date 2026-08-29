"""The command line.

Two audiences, and they want opposite things. A person wants to see the five builds and what
each is for. A workflow wants one string on standard output with no decoration around it, so
it can put it in a shell variable. Every subcommand here that a workflow uses prints one
thing and nothing else.

    cpybuild list                       the five builds, for a person
    cpybuild matrix                     the same list as JSON, for the workflow
    cpybuild packages debug             the apt line for one build
    cpybuild flags debug                the configure line for one build
    cpybuild buildargs debug            every --build-arg the Dockerfile wants, one per line
    cpybuild proof debug                a program that fails unless the image is that build
    cpybuild check                      is the committed lockfile complete and on the pin
    cpybuild reference debug --arch amd64
    cpybuild record debug amd64 sha256:...
    cpybuild protected                  digests the tidy up is not allowed to delete
    cpybuild prune --versions v.json --protected p.txt   version ids that can be deleted
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from refcheck import PINNED_COMMIT, PINNED_TAG

from . import retention
from .configs import ARCHITECTURES, BY_KEY, CONFIGURATIONS, matrix, packages
from .images import LOCKFILE, Broken, Lock, digests, problems, protected


def _list(args: argparse.Namespace) -> int:
    for one in CONFIGURATIONS:
        print(f"{one.key:14} {one.summary}")
        if one.flags:
            print(f"{'':14} configure {' '.join(one.flags)}")
    return 0


def _matrix(args: argparse.Namespace) -> int:
    print(json.dumps(matrix()))
    return 0


def _packages(args: argparse.Namespace) -> int:
    print(" ".join(packages(BY_KEY[args.config])))
    return 0


def _flags(args: argparse.Namespace) -> int:
    print(" ".join(BY_KEY[args.config].flags))
    return 0


PROOF = """import sys, sysconfig
ok = bool({expression})
print("{key}: " + ("yes" if ok else "NO"))
sys.exit(0 if ok else 1)"""


def _proof(args: argparse.Namespace) -> int:
    """Print a program that exits non zero unless the image really is that build.

    Run inside the published image, which is the only place the question can honestly be
    asked. Everything before this point checks that a build succeeded, and a build succeeding
    is not the same as a build being the one that was asked for: a configure flag that was
    accepted and then ignored produces a perfectly working interpreter that is quietly the
    release build wearing another name. That image would still be tagged, still be written
    into the lockfile, and still be pulled by a lesson that draws a conclusion from it.

    A program rather than an expression so the message and the exit code are decided here
    instead of in a shell fragment inside a YAML string.
    """
    one = BY_KEY[args.config]
    print(PROOF.format(expression=one.proof, key=one.key))
    return 0


def _buildargs(args: argparse.Namespace) -> int:
    """Print every build argument the Dockerfile takes, one `NAME=value` per line.

    This exists so the Dockerfile's argument list is worked out in one place. The workflow
    feeds these straight to `build-push-action`, which wants exactly this format, and the
    justfile turns each line into a `--build-arg`. Before this, the workflow had a snippet of
    Python inside a YAML string working out `CC` and `DEBUGGER`, and the local recipe did not
    work them out at all, so `just build-image debug` quietly produced an image with no gdb
    in it.

    Empty values are printed rather than skipped. `CC=` reaching the Dockerfile is what the
    `if [ -n "${CC}" ]` there expects, and a missing line would leave whatever the previous
    build set.
    """
    one = BY_KEY[args.config]
    for name, value in [
        ("CPYTHON_COMMIT", PINNED_COMMIT),
        ("CPYTHON_TAG", PINNED_TAG),
        ("CONFIG", one.key),
        ("CONFIGURE_FLAGS", " ".join(one.flags)),
        ("PACKAGES", " ".join(packages(one))),
        ("CC", one.environment.get("CC", "")),
        ("LLVM", one.llvm),
        ("DEBUGGER", "yes" if one.debugger else ""),
        ("SUMMARY", one.summary),
    ]:
        print(f"{name}={value}")
    return 0


def _check(args: argparse.Namespace) -> int:
    """Read the committed lockfile and say whether it still describes this project.

    Offline and instant. It does not reach for the registry, because a check that needs the
    network is a check that fails on a train, and the thing worth catching here is a lockfile
    that has fallen behind the pin or is missing a build somebody added.
    """
    try:
        lock = Lock.load(Path(args.lockfile))
    except Broken as error:
        print(str(error), file=sys.stderr)
        return 1
    found = problems(lock)
    total = len(CONFIGURATIONS) * len(ARCHITECTURES)
    print(f"{total} images from CPython {lock.tag} at {lock.commit[:12]}")
    for one in found:
        print(f"  {one}", file=sys.stderr)
    return 1 if found else 0


def _reference(args: argparse.Namespace) -> int:
    lock = Lock.load(Path(args.lockfile))
    try:
        print(lock.reference(args.config, args.arch))
    except Broken as error:
        print(str(error), file=sys.stderr)
        return 1
    return 0


def _protected(args: argparse.Namespace) -> int:
    """Print every digest the tidy up must keep, one per line.

    The current lockfile plus the lockfile as of every release tag. Somebody who checks out
    `v0.2.0` and runs the experiments has to get the interpreter that version was written
    against, and a retention rule counted in weeks cannot know that.
    """
    found = protected()
    path = Path(args.lockfile)
    if path.is_file():
        found |= digests(Lock.load(path))
    for one in sorted(found):
        print(one)
    return 0


def _prune(args: argparse.Namespace) -> int:
    """Print the id of every package version that can be deleted, one per line.

    Reads rather than fetches, and prints rather than deletes. The workflow does both of the
    parts that touch the registry, so this can be run against a saved copy of the version list
    to see what a tidy up would do before letting it do it.
    """
    body = json.loads(Path(args.versions).read_text(encoding="utf-8"))
    versions = retention.read(body)
    safe = {
        one.strip()
        for one in Path(args.protected).read_text(encoding="utf-8").splitlines()
        if one.strip()
    }
    print(retention.why(versions, safe, args.keep), file=sys.stderr)
    for one in retention.doomed(versions, safe, args.keep):
        print(one.id)
    return 0


def _record(args: argparse.Namespace) -> int:
    path = Path(args.lockfile)
    lock = Lock.load(path) if path.is_file() else Lock()
    lock.record(args.config, args.arch, args.digest, size=args.size)
    lock.write(path)
    print(f"{path}: {args.config} on {args.arch} is {args.digest}")
    return 0


def build() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="cpybuild", description=__doc__)
    parser.add_argument("--lockfile", default=str(LOCKFILE), help="where the lockfile lives")
    subs = parser.add_subparsers(dest="command", required=True)

    named = subs.add_parser("list", help="the five builds and what each is for")
    named.set_defaults(handler=_list)

    grid = subs.add_parser("matrix", help="the build list as JSON, for the workflow")
    grid.set_defaults(handler=_matrix)

    apt = subs.add_parser("packages", help="the apt line for one build")
    apt.add_argument("config", choices=sorted(BY_KEY))
    apt.set_defaults(handler=_packages)

    flagged = subs.add_parser("flags", help="the configure line for one build")
    flagged.add_argument("config", choices=sorted(BY_KEY))
    flagged.set_defaults(handler=_flags)

    args_for = subs.add_parser("buildargs", help="every --build-arg for one build")
    args_for.add_argument("config", choices=sorted(BY_KEY))
    args_for.set_defaults(handler=_buildargs)

    shown = subs.add_parser("proof", help="a program that fails unless the image is that build")
    shown.add_argument("config", choices=sorted(BY_KEY))
    shown.set_defaults(handler=_proof)

    gate = subs.add_parser("check", help="is the lockfile complete and on the pin")
    gate.set_defaults(handler=_check)

    named_ref = subs.add_parser("reference", help="the digest reference for one image")
    named_ref.add_argument("config", choices=sorted(BY_KEY))
    named_ref.add_argument("--arch", choices=ARCHITECTURES, default="amd64")
    named_ref.set_defaults(handler=_reference)

    safe = subs.add_parser("protected", help="digests the tidy up must not delete")
    safe.set_defaults(handler=_protected)

    gone = subs.add_parser("prune", help="version ids that can be deleted")
    gone.add_argument("--versions", required=True, help="the registry's version list as JSON")
    gone.add_argument("--protected", required=True, help="digests to keep, one per line")
    gone.add_argument("--keep", type=int, default=120, help="newest versions to keep regardless")
    gone.set_defaults(handler=_prune)

    kept = subs.add_parser("record", help="put a freshly published digest in the lockfile")
    kept.add_argument("config", choices=sorted(BY_KEY))
    kept.add_argument("arch", choices=ARCHITECTURES)
    kept.add_argument("digest")
    kept.add_argument("--size", type=int, default=0, help="compressed bytes, for the table")
    kept.set_defaults(handler=_record)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build().parse_args(argv)
    return int(args.handler(args))


if __name__ == "__main__":
    raise SystemExit(main())
