"""Reading the version notes an author put on a cell.

A note lives in the cell's own metadata rather than in a list somewhere else in the
repository. A list drifts: somebody deletes the cell and the entry stays, or copies the
cell into another lesson and the entry does not follow. Metadata moves with the cell,
survives a round trip through Jupyter, and is what nbformat is for.

`nbbuild` writes the note from the `differs=` or `varies=` keyword on `Lesson.code`, and
also writes a visible markdown cell underneath saying the same thing in prose, so a reader
on Colab sees the warning without opening the metadata.

There are two keys because there are two kinds of note. `differs` is a claim about the
language: this cell prints one thing on 3.14 and another on 3.15, and the comparison can
check it. `varies` is a claim about the reader's machine: how their interpreter was
configured, how many files their standard library has, how deep the C stack goes. Two
recordings cannot check that one, because whether the two runs happen to agree depends on
which machine made them. So `varies` is reported and never fails.
"""

from __future__ import annotations

import json
from pathlib import Path

#: The namespace this project owns inside a cell's metadata. Everything else in there
#: belongs to Jupyter, Colab or an extension, and writing a bare key at the top level is
#: how you collide with one of them.
NAMESPACE = "cpython_internals"

#: A sentence about a difference between the two Python versions. Checkable.
DIFFERS = "differs"

#: A sentence about a difference between two machines or two builds. Not checkable.
VARIES = "varies"


def note(cell: dict, key: str = DIFFERS) -> str:
    """The note of one kind on one cell, or the empty string if it does not have one."""
    body = cell.get("metadata", {}).get(NAMESPACE, {})
    if not isinstance(body, dict):
        return ""
    return str(body.get(key, "")).strip()


def notes(path: Path, key: str = DIFFERS) -> dict[str, str]:
    """Every cell in one notebook carrying a note of that kind, keyed by cell id.

    Read as JSON rather than through nbformat because this is a lookup, not an execution,
    and going through nbformat here would mean the comparison depends on a validator
    accepting a notebook that the record step already ran.
    """
    book = json.loads(path.read_text(encoding="utf-8"))
    found = {}
    for cell in book.get("cells", []):
        text = note(cell, key)
        if text and cell.get("id"):
            found[cell["id"]] = text
    return found


def all_notes(paths: list[Path], key: str = DIFFERS) -> dict[str, dict[str, str]]:
    """The notes for several notebooks, keyed by file name then by cell id."""
    return {path.name: notes(path, key) for path in paths}
