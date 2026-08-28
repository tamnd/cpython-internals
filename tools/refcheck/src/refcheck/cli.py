"""The refcheck command line."""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

from .citation import Citation, CitationError
from .lock import Lock
from .resolve import FIXABLE_BY_UPDATE, Finding, Resolved, Status, resolve
from .scan import Occurrence, scan
from .tree import PINNED_TAG, TreeNotFound, find_tree, tree_commit

DEFAULT_LOCK = Path("citations.lock.json")
DEFAULT_ROOTS = [Path("book"), Path("lessons"), Path("blueprints"), Path("README.md")]


def _check_one(occurrence: Occurrence, tree: Path, lock: Lock, update: bool) -> Finding:
    outcome = resolve(occurrence.citation, tree)
    if isinstance(outcome, Finding):
        return Finding(outcome.citation, outcome.status, outcome.detail, source=occurrence.source)

    resolved: Resolved = outcome
    if update:
        lock.put(resolved)
        return Finding(occurrence.citation, Status.OK, resolved=resolved, source=occurrence.source)

    entry = lock.get(occurrence.citation)
    if entry is None:
        return Finding(
            occurrence.citation,
            Status.NOT_IN_LOCK,
            "no lockfile entry; run `just recheck` after confirming the citation is right",
            resolved=resolved,
            source=occurrence.source,
        )
    if entry.digest != resolved.digest:
        return Finding(
            occurrence.citation,
            Status.DIGEST_MISMATCH,
            f"was {entry.first_line!r}, now {resolved.first_line!r}",
            resolved=resolved,
            source=occurrence.source,
        )
    return Finding(occurrence.citation, Status.OK, resolved=resolved, source=occurrence.source)


def _roots(args: argparse.Namespace) -> list[Path]:
    if args.roots:
        return [Path(root) for root in args.roots]
    return [root for root in DEFAULT_ROOTS if root.exists()]


def command_verify(args: argparse.Namespace) -> int:
    tree = find_tree(args.tree)
    roots = _roots(args)
    occurrences = scan(roots)
    lock = Lock.load(Path(args.lock))

    commit = tree_commit(tree)
    if commit and lock.commit and commit != lock.commit:
        print(
            f"warning: tree is at {commit[:12]} but the lockfile was written against "
            f"{lock.commit[:12]}",
            file=sys.stderr,
        )

    findings = [_check_one(o, tree, lock, update=args.update) for o in occurrences]
    failures = [f for f in findings if not f.ok]

    for finding in failures:
        print(finding.render(), file=sys.stderr)

    if args.update:
        Lock(tag=PINNED_TAG, commit=commit or lock.commit, entries=lock.entries).dump(
            Path(args.lock)
        )
        print(f"wrote {len(lock.entries)} entries to {args.lock}")

    counts = Counter(f.status.value for f in findings)
    summary = ", ".join(f"{name} {count}" for name, count in sorted(counts.items()))
    print(f"{len(findings)} citations in {len(roots)} root(s): {summary or 'none'}")

    if args.update:
        # Re-baselining clears a stale digest. It does not conjure a file that is not in
        # the tree, so those failures survive --update and still fail the run.
        unfixable = [f for f in failures if f.status not in FIXABLE_BY_UPDATE]
        return 1 if unfixable else 0
    return 1 if failures else 0


def command_scan(args: argparse.Namespace) -> int:
    for occurrence in scan(_roots(args)):
        print(f"{occurrence.source}\t{occurrence.citation}")
    return 0


def command_url(args: argparse.Namespace) -> int:
    # A malformed citation here is a usage error, so it propagates to main and exits 2.
    # Exit 1 is reserved for "the citations are real but one of them has drifted", which
    # is the case CI branches on.
    for text in args.citations:
        print(Citation.parse(text).github_url())
    return 0


def command_show(args: argparse.Namespace) -> int:
    tree = find_tree(args.tree)
    citation = Citation.parse(args.citation)
    outcome = resolve(citation, tree)
    if isinstance(outcome, Finding):
        print(outcome.render(), file=sys.stderr)
        return 1
    width = len(str(citation.end))
    for offset, line in enumerate(outcome.lines):
        print(f"{citation.start + offset:>{width}}  {line}")
    print(f"\n{citation.github_url()}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="refcheck",
        description="Verify that every source citation still points at what it claimed to.",
    )
    parser.add_argument("--tree", help="path to the pinned CPython checkout")
    subparsers = parser.add_subparsers(dest="command", required=True)

    verify = subparsers.add_parser("verify", help="resolve every citation and compare digests")
    verify.add_argument("roots", nargs="*", help="files or directories to scan")
    verify.add_argument("--lock", default=str(DEFAULT_LOCK))
    verify.add_argument(
        "--update",
        action="store_true",
        help="rewrite the lockfile instead of failing, after a human has looked at the diff",
    )
    verify.set_defaults(func=command_verify)

    scan_parser = subparsers.add_parser("scan", help="list every citation and where it is written")
    scan_parser.add_argument("roots", nargs="*")
    scan_parser.set_defaults(func=command_scan)

    url = subparsers.add_parser("url", help="print the GitHub permalink for a citation")
    url.add_argument("citations", nargs="+")
    url.set_defaults(func=command_url)

    show = subparsers.add_parser("show", help="print the cited lines from the pinned tree")
    show.add_argument("citation")
    show.set_defaults(func=command_show)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except TreeNotFound as error:
        print(str(error), file=sys.stderr)
        return 2
    except CitationError as error:
        print(str(error), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
