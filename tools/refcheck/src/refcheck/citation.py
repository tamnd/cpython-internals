"""Parsing, formatting and linking of source citations.

A citation names an exact region of the pinned CPython tree. It is written the same
way everywhere in this project, in prose, in notebooks and in blueprints, so that one
checker can find all of them:

    Objects/listobject.c:874@v3.15.0rc1
    Objects/listobject.c:874-892@v3.15.0rc1
    Objects/listobject.c:874-892@v3.15.0rc1#list_append

The optional trailing symbol is the part that makes a citation self checking. A line
number alone drifts silently when upstream inserts a function above it, and the reader
never finds out. A line number plus the name of the thing that is supposed to be there
fails loudly instead.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

GITHUB_REPO = "https://github.com/python/cpython"

# Path, then a line or a line range, then the tag, then an optional symbol. The path
# pattern deliberately refuses a leading slash and refuses "..", because a citation is
# always relative to the root of the pinned tree.
_PATTERN = re.compile(
    r"""
    (?P<path>[A-Za-z0-9_][A-Za-z0-9_./+-]*\.[A-Za-z0-9_+-]+)
    :
    (?P<start>\d+)
    (?:-(?P<end>\d+))?
    @
    (?P<tag>v\d+\.\d+\.\d+(?:[ab]\d+|rc\d+)?)
    (?:\#(?P<symbol>[A-Za-z_][A-Za-z0-9_]*))?
    """,
    re.VERBOSE,
)


class CitationError(ValueError):
    """Raised when a string that was meant to be a citation is not one."""


@dataclass(frozen=True, order=True)
class Citation:
    """One reference to a region of the pinned tree."""

    path: str
    start: int
    end: int
    tag: str
    symbol: str | None = None

    def __post_init__(self) -> None:
        if self.start < 1:
            raise CitationError(f"line numbers start at 1, got {self.start}")
        if self.end < self.start:
            raise CitationError(f"range ends before it starts: {self.start}-{self.end}")
        if ".." in self.path or self.path.startswith("/"):
            raise CitationError(f"path must be relative to the tree root: {self.path!r}")

    @classmethod
    def parse(cls, text: str) -> Citation:
        match = _PATTERN.fullmatch(text.strip())
        if match is None:
            raise CitationError(f"not a citation: {text!r}")
        return cls._from_match(match)

    @classmethod
    def _from_match(cls, match: re.Match[str]) -> Citation:
        start = int(match["start"])
        end = int(match["end"]) if match["end"] else start
        return cls(
            path=match["path"],
            start=start,
            end=end,
            tag=match["tag"],
            symbol=match["symbol"],
        )

    @property
    def line_count(self) -> int:
        return self.end - self.start + 1

    @property
    def key(self) -> str:
        """The lockfile key, which ignores the symbol so that adding one is not a churn."""
        return f"{self.path}:{self.start}-{self.end}@{self.tag}"

    def github_url(self) -> str:
        """A permalink that a reader can click, with the region highlighted."""
        anchor = f"#L{self.start}" if self.start == self.end else f"#L{self.start}-L{self.end}"
        return f"{GITHUB_REPO}/blob/{self.tag}/{self.path}{anchor}"

    def markdown_link(self, label: str | None = None) -> str:
        return f"[{label or self.short()}]({self.github_url()})"

    def short(self) -> str:
        """The form a reader sees in prose, without the tag noise."""
        lines = str(self.start) if self.start == self.end else f"{self.start}-{self.end}"
        return f"{self.path}:{lines}"

    def __str__(self) -> str:
        text = self.key
        if self.symbol:
            text += f"#{self.symbol}"
        return text


def find_all(text: str) -> list[Citation]:
    """Every citation in a blob of text, in the order they appear.

    Duplicates are kept. A lesson that cites the same lines twice is citing them twice,
    and the caller decides whether that matters.
    """
    found = []
    for match in _PATTERN.finditer(text):
        try:
            found.append(Citation._from_match(match))
        except CitationError:
            # A regex match that fails validation is a malformed citation rather than
            # ordinary prose, so it is worth surfacing rather than dropping. The scanner
            # reports these separately; here we skip so one bad citation does not hide
            # the good ones on the same line.
            continue
    return found
