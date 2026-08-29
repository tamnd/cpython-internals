"""Reading the version notes an author put on a cell.

A note lives in the cell's own metadata rather than in a list somewhere else in the
repository. A list drifts: somebody deletes the cell and the entry stays, or copies the
cell into another lesson and the entry does not follow. Metadata moves with the cell,
survives a round trip through Jupyter, and is what nbformat is for.

`nbbuild` writes the note from the `differs=` keyword on `Lesson.code`, and also writes a
visible markdown cell underneath saying the same thing in prose, so a reader on Colab sees
the warning without opening the metadata.
"""

from __future__ import annotations

import json
from pathlib import Path

#: The namespace this project owns inside a cell's metadata. Everything else in there
#: belongs to Jupyter, Colab or an extension, and writing a bare key at the top level is
#: how you collide with one of them.
NAMESPACE = "cpython_internals"

#: The key inside that namespace. Its value is the sentence explaining what differs.
KEY = "differs"


def note(cell: dict) -> str:
    """The version note on one cell, or the empty string if it does not have one."""
    body = cell.get("metadata", {}).get(NAMESPACE, {})
    if not isinstance(body, dict):
        return ""
    return str(body.get(KEY, "")).strip()


def notes(path: Path) -> dict[str, str]:
    """Every declared cell in one notebook, keyed by cell id.

    Read as JSON rather than through nbformat because this is a lookup, not an execution,
    and going through nbformat here would mean the comparison depends on a validator
    accepting a notebook that the record step already ran.
    """
    book = json.loads(path.read_text(encoding="utf-8"))
    found = {}
    for cell in book.get("cells", []):
        text = note(cell)
        if text and cell.get("id"):
            found[cell["id"]] = text
    return found


def all_notes(paths: list[Path]) -> dict[str, dict[str, str]]:
    """The notes for several notebooks, keyed by file name then by cell id."""
    return {path.name: notes(path) for path in paths}
