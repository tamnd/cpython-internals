"""The citation lockfile.

Every citation in the project has an entry recording the digest of the region it points
at plus the first cited line in plain text. The plain text is there for the human reading
the diff: a lockfile of nothing but hashes tells a reviewer that something moved but not
what, and a reviewer who cannot see what moved approves the update without reading it.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .citation import Citation
from .resolve import Resolved
from .tree import PINNED_COMMIT, PINNED_TAG

LOCK_VERSION = 1


@dataclass(frozen=True)
class Entry:
    key: str
    digest: str
    first_line: str
    lines: int

    @classmethod
    def from_resolved(cls, resolved: Resolved) -> Entry:
        return cls(
            key=resolved.citation.key,
            digest=resolved.digest,
            first_line=resolved.first_line,
            lines=resolved.citation.line_count,
        )


@dataclass
class Lock:
    tag: str = PINNED_TAG
    commit: str = PINNED_COMMIT
    entries: dict[str, Entry] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.entries is None:
            self.entries = {}

    def get(self, citation: Citation) -> Entry | None:
        return self.entries.get(citation.key)

    def put(self, resolved: Resolved) -> None:
        entry = Entry.from_resolved(resolved)
        self.entries[entry.key] = entry

    @classmethod
    def load(cls, path: Path) -> Lock:
        if not path.is_file():
            return cls()
        document = json.loads(path.read_text(encoding="utf-8"))
        entries = {
            key: Entry(
                key=key,
                digest=value["digest"],
                first_line=value["first_line"],
                lines=value["lines"],
            )
            for key, value in document.get("citations", {}).items()
        }
        return cls(
            tag=document.get("tag", PINNED_TAG),
            commit=document.get("commit", PINNED_COMMIT),
            entries=entries,
        )

    def dump(self, path: Path) -> None:
        document = {
            "version": LOCK_VERSION,
            "tag": self.tag,
            "commit": self.commit,
            "citations": {
                key: {
                    "digest": entry.digest,
                    "first_line": entry.first_line,
                    "lines": entry.lines,
                }
                for key, entry in sorted(self.entries.items())
            },
        }
        # Sorted keys and a trailing newline so that the diff of a regenerated lockfile
        # shows only what changed.
        path.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")
