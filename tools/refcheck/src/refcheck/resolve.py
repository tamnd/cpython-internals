"""Resolving citations against the pinned tree and digesting what they point at."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from .citation import Citation
from .tree import PINNED_TAG, read_lines

CONTEXT_LINES = 5
DIGEST_LENGTH = 16


class Status(StrEnum):
    OK = "ok"
    WRONG_TAG = "wrong-tag"
    MISSING_FILE = "missing-file"
    OUT_OF_RANGE = "out-of-range"
    SYMBOL_NOT_FOUND = "symbol-not-found"
    DIGEST_MISMATCH = "digest-mismatch"
    NOT_IN_LOCK = "not-in-lock"
    TOO_LONG = "too-long"


#: Quoting more than this from CPython in one citation is a sign the author is pasting a
#: function rather than pointing at one. The authoring guide caps quoted fragments at 25
#: lines and this is the mechanical half of that rule.
MAX_CITED_LINES = 40

#: Statuses that re-baselining the lockfile can legitimately clear. Everything else is a
#: citation that does not resolve at all, and no amount of updating a lockfile fixes a
#: pointer to a file that is not there. Keeping the two apart is what stops `--update`
#: from turning into a way to make failures disappear.
FIXABLE_BY_UPDATE = frozenset({Status.NOT_IN_LOCK, Status.DIGEST_MISMATCH})


@dataclass(frozen=True)
class Resolved:
    """What a citation actually points at right now."""

    citation: Citation
    lines: tuple[str, ...]
    digest: str
    first_line: str

    @property
    def text(self) -> str:
        return "\n".join(self.lines)


@dataclass(frozen=True)
class Finding:
    """One problem, or one clean result, for a single citation."""

    citation: Citation
    status: Status
    detail: str = ""
    resolved: Resolved | None = None
    source: str = ""

    @property
    def ok(self) -> bool:
        return self.status is Status.OK

    def render(self) -> str:
        where = f"{self.source}: " if self.source else ""
        if self.ok:
            return f"{where}{self.citation} ok"
        return f"{where}{self.citation} {self.status.value}: {self.detail}"


def digest_region(lines: tuple[str, ...]) -> str:
    """A stable digest of a region, insensitive to trailing whitespace only.

    Trailing whitespace is stripped because it changes for reasons that have nothing to
    do with meaning. Nothing else is normalised: an indentation change in CPython is a
    real change to the thing we are pointing at, and the author should look at it.
    """
    hasher = hashlib.sha256()
    for line in lines:
        hasher.update(line.rstrip().encode("utf-8", errors="surrogateescape"))
        hasher.update(b"\n")
    return hasher.hexdigest()[:DIGEST_LENGTH]


def resolve(citation: Citation, tree: Path) -> Resolved | Finding:
    """Read the cited region, or explain why it cannot be read."""
    if citation.tag != PINNED_TAG:
        return Finding(
            citation,
            Status.WRONG_TAG,
            f"tree is pinned at {PINNED_TAG}, citation says {citation.tag}",
        )

    if citation.line_count > MAX_CITED_LINES:
        return Finding(
            citation,
            Status.TOO_LONG,
            f"{citation.line_count} lines cited, limit is {MAX_CITED_LINES}",
        )

    try:
        all_lines = read_lines(tree, citation.path)
    except FileNotFoundError:
        return Finding(citation, Status.MISSING_FILE, f"{citation.path} is not in the tree")
    except IsADirectoryError:
        return Finding(citation, Status.MISSING_FILE, f"{citation.path} is a directory")

    if citation.end > len(all_lines):
        return Finding(
            citation,
            Status.OUT_OF_RANGE,
            f"{citation.path} has {len(all_lines)} lines, citation ends at {citation.end}",
        )

    cited = all_lines[citation.start - 1 : citation.end]

    if citation.symbol is not None and not any(citation.symbol in line for line in cited):
        nearby = _find_symbol(all_lines, citation.symbol)
        hint = f", but it appears at line {nearby}" if nearby else ", and it is not in the file"
        return Finding(
            citation,
            Status.SYMBOL_NOT_FOUND,
            f"{citation.symbol!r} is not in lines {citation.start}-{citation.end}{hint}",
        )

    low = max(0, citation.start - 1 - CONTEXT_LINES)
    high = min(len(all_lines), citation.end + CONTEXT_LINES)
    window = tuple(all_lines[low:high])

    return Resolved(
        citation=citation,
        lines=tuple(cited),
        digest=digest_region(window),
        first_line=cited[0].strip() if cited else "",
    )


def _find_symbol(lines: tuple[str, ...], symbol: str) -> int | None:
    """The first line number containing the symbol, for a useful error message."""
    for number, line in enumerate(lines, start=1):
        if symbol in line:
            return number
    return None
