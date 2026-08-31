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
    cpybuild reference debug --joined   the one reference that works on either architecture
    cpybuild record debug amd64 sha256:...
    cpybuild record-index debug sha256:...
    cpybuild devcontainer --write       point the devcontainer at the lockfile's debug image
    cpybuild protected                  digests the tidy up is not allowed to delete
    cpybuild expand --versions v.json --protected p.txt  those digests and their parts
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
from .images import (
    DEVCONTAINER,
    DIGEST,
    LOCKFILE,
    REGISTRY,
    Broken,
    Lock,
    devcontainer_problems,
    digests,
    members_of,
    problems,
    protected,
    retarget,
)


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

    # The devcontainer is checked here rather than in a recipe of its own because it is the
    # same question: does what somebody pulls still match what was built. It is skipped when
    # the file is absent so this stays usable in a checkout that has not got one.
    where = Path(args.devcontainer)
    if where.is_file():
        said = devcontainer_problems(lock, where.read_text(encoding="utf-8"))
        found = found + said
        if not said:
            print(f"{where} pulls the debug build by digest")

    for one in found:
        print(f"  {one}", file=sys.stderr)
    return 1 if found else 0


def _reference(args: argparse.Namespace) -> int:
    lock = Lock.load(Path(args.lockfile))
    try:
        if args.joined:
            print(lock.reference_index(args.config))
        else:
            print(lock.reference(args.config, args.arch))
    except Broken as error:
        print(str(error), file=sys.stderr)
        return 1
    return 0


def _devcontainer(args: argparse.Namespace) -> int:
    """Print the reference the devcontainer should name, or write it into the file.

    The workflow runs this with `--write` in the same step that records the digests, so the
    pull request that moves the lockfile moves the devcontainer with it and neither can be
    left behind.
    """
    lock = Lock.load(Path(args.lockfile))
    where = Path(args.devcontainer)
    try:
        wanted = lock.reference_index(args.config)
    except Broken as error:
        print(str(error), file=sys.stderr)
        return 1
    if not args.write:
        print(wanted)
        return 0
    body = where.read_text(encoding="utf-8")
    where.write_text(retarget(body, wanted), encoding="utf-8")
    print(f"{where}: {wanted}")
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


def _expand(args: argparse.Namespace) -> int:
    """Print the protected digests and everything they are made of, one per line.

    This is the answer to #126. What we call an image is an index naming an amd64 manifest, an
    arm64 manifest and an attestation for each, and those parts are versions the registry will
    happily delete on their own. Deleting one leaves an index pointing at nothing, which is
    `manifest unknown` for everybody pulling it.

    Refuses to print anything if the walk found no parts at all. Fifteen indexes have parts, so
    zero means Docker is not there or the login did not take, and the useful thing to do with
    an answer that is probably wrong is not hand it to something that deletes images.
    """
    body = json.loads(Path(args.versions).read_text(encoding="utf-8"))
    versions = retention.read(body)
    named = {
        one.strip()
        for one in Path(args.protected).read_text(encoding="utf-8").splitlines()
        if one.strip()
    }
    roots = retention.anchors(versions, named)
    found = retention.reachable(roots, members_of(args.registry))
    parts = found - roots
    if not parts:
        print(
            f"{len(roots)} digests to keep and not one of them is made of anything, "
            "which cannot be right, so nothing is safe to delete",
            file=sys.stderr,
        )
        return 1
    print(f"{len(roots)} kept outright, and {len(parts)} more they are made of", file=sys.stderr)
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


def _refuse_a_tag(digest: str) -> bool:
    """Whether what the workflow handed us is a digest at all.

    Checked here rather than only in `check`, because the thing that goes wrong is a build
    step printing a tag or an error message into a variable, and a lockfile that took it is a
    lockfile somebody has to go and repair by hand later.
    """
    if DIGEST.match(digest):
        return False
    print(f"{digest} is not a digest, so it is not going in the lockfile", file=sys.stderr)
    return True


def _record(args: argparse.Namespace) -> int:
    if _refuse_a_tag(args.digest):
        return 1
    path = Path(args.lockfile)
    lock = Lock.load(path) if path.is_file() else Lock()
    lock.record(args.config, args.arch, args.digest, size=args.size)
    lock.write(path)
    print(f"{path}: {args.config} on {args.arch} is {args.digest}")
    return 0


def _record_index(args: argparse.Namespace) -> int:
    if _refuse_a_tag(args.digest):
        return 1
    path = Path(args.lockfile)
    lock = Lock.load(path) if path.is_file() else Lock()
    lock.record_index(args.config, args.digest, size=args.size)
    lock.write(path)
    print(f"{path}: the joined {args.config} image is {args.digest}")
    return 0


def build() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="cpybuild", description=__doc__)
    parser.add_argument("--lockfile", default=str(LOCKFILE), help="where the lockfile lives")
    parser.add_argument(
        "--devcontainer", default=str(DEVCONTAINER), help="where the devcontainer lives"
    )
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
    named_ref.add_argument(
        "--joined", action="store_true", help="the multi architecture image rather than a half"
    )
    named_ref.set_defaults(handler=_reference)

    box = subs.add_parser("devcontainer", help="the image the devcontainer should pull")
    box.add_argument("config", nargs="?", default="debug", choices=sorted(BY_KEY))
    box.add_argument("--write", action="store_true", help="put it in the file")
    box.set_defaults(handler=_devcontainer)

    safe = subs.add_parser("protected", help="digests the tidy up must not delete")
    safe.set_defaults(handler=_protected)

    wider = subs.add_parser("expand", help="protected digests plus the parts they are made of")
    wider.add_argument("--versions", required=True, help="the registry's version list as JSON")
    wider.add_argument("--protected", required=True, help="digests to keep, one per line")
    wider.add_argument("--registry", default=REGISTRY, help="where to ask what an index lists")
    wider.set_defaults(handler=_expand)

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

    joined = subs.add_parser("record-index", help="put a joined digest in the lockfile")
    joined.add_argument("config", choices=sorted(BY_KEY))
    joined.add_argument("digest")
    joined.add_argument("--size", type=int, default=0, help="compressed bytes, for the table")
    joined.set_defaults(handler=_record_index)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build().parse_args(argv)
    return int(args.handler(args))


if __name__ == "__main__":
    raise SystemExit(main())
