"""Running the lessons and writing down what each cell printed.

One recording per interpreter. The recording is a small JSON file rather than an executed
notebook, because an executed notebook is mostly metadata and the diff of two of them is
unreadable, which defeats the purpose.

Cells are keyed by their notebook id rather than by their position. `nbbuild` counts the
ids out from one, so inserting a cell renumbers everything after it, and a comparison keyed
on position would then report every later cell as changed. Keying on the id means a
recording made before the insertion still lines up.
"""

from __future__ import annotations

import json
import platform
from dataclasses import dataclass
from pathlib import Path

from .normalise import outputs

#: Where the recordings go by default. Not committed: two of them are made side by side in
#: one CI run and compared immediately, and a checked in recording would be a claim about
#: an interpreter nobody is running any more.
DEFAULT_ROOT = Path("build") / "versions"


@dataclass(frozen=True)
class Recording:
    """What one interpreter printed for one notebook."""

    notebook: str
    python: str
    cells: dict[str, str]

    def as_json(self) -> str:
        body = {"notebook": self.notebook, "python": self.python, "cells": self.cells}
        return json.dumps(body, indent=1, sort_keys=True) + "\n"

    @classmethod
    def load(cls, path: Path) -> Recording:
        body = json.loads(path.read_text(encoding="utf-8"))
        return cls(notebook=body["notebook"], python=body["python"], cells=body["cells"])


def version() -> str:
    """The running interpreter, as the two numbers that matter for this comparison."""
    return ".".join(platform.python_version_tuple()[:2])


def run(path: Path, *, timeout: int = 300) -> Recording:
    """Execute a notebook and record what every code cell printed.

    Executed in the notebook's own directory, the same as `nbcheck run` and the same as
    Colab, so a relative path that works for a reader works here. Errors are recorded
    rather than raised: a lesson that raises on purpose is a lesson whose exception is one
    of the outputs being compared, and a lesson that raises by accident is `nbcheck run`'s
    problem and will have failed there first.
    """
    import nbformat
    from nbclient import NotebookClient

    book = nbformat.read(path, as_version=4)
    client = NotebookClient(
        book,
        timeout=timeout,
        kernel_name="python3",
        resources={"metadata": {"path": str(path.parent)}},
        allow_errors=True,
    )
    client.execute()
    cells = {
        cell["id"]: outputs(cell)
        for cell in book.cells
        if cell.get("cell_type") == "code" and cell.get("id")
    }
    return Recording(notebook=path.name, python=version(), cells=cells)


def write(recording: Recording, root: Path) -> Path:
    """One file per notebook, named after it, so the two directories line up by name."""
    root.mkdir(parents=True, exist_ok=True)
    path = root / f"{Path(recording.notebook).stem}.json"
    path.write_text(recording.as_json(), encoding="utf-8")
    return path


def load_all(root: Path) -> dict[str, Recording]:
    """Every recording in a directory, keyed by notebook file name."""
    found = {}
    for path in sorted(root.glob("*.json")):
        recording = Recording.load(path)
        found[recording.notebook] = recording
    return found
