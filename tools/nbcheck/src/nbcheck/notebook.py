"""Reading a lesson notebook without depending on how it was written.

A notebook is JSON, and every tool that touches one has its own opinions about how the
`source` field is stored. Jupyter writes a list of lines with the newlines kept, Colab
sometimes writes a single string, and a notebook that has been through both is a mixture.
Everything downstream of this module gets plain strings.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


class NotebookError(ValueError):
    """The file is not a notebook, or not one we can check."""


@dataclass(frozen=True)
class Cell:
    """One cell, with the position it holds in the notebook.

    The number is one based and counts every cell, not every cell of this kind, because
    that is the number a person reads off the screen when you tell them which cell is
    wrong.
    """

    number: int
    kind: str
    source: str
    outputs: list
    execution_count: int | None
    identifier: str | None = None

    @property
    def is_code(self) -> bool:
        return self.kind == "code"

    @property
    def is_markdown(self) -> bool:
        return self.kind == "markdown"

    @property
    def is_empty(self) -> bool:
        return not self.source.strip()

    def first_line(self) -> str:
        for line in self.source.splitlines():
            if line.strip():
                return line.strip()
        return ""


@dataclass(frozen=True)
class Notebook:
    """A lesson notebook, loaded and normalized."""

    path: Path
    cells: list[Cell]
    metadata: dict

    @property
    def code_cells(self) -> list[Cell]:
        return [cell for cell in self.cells if cell.is_code]

    @property
    def markdown_cells(self) -> list[Cell]:
        return [cell for cell in self.cells if cell.is_markdown]

    def cell(self, number: int) -> Cell:
        return self.cells[number - 1]

    def text(self) -> str:
        """Every cell's source, for the checks that do not care about cell boundaries."""
        return "\n".join(cell.source for cell in self.cells)


def _source_of(cell: dict) -> str:
    source = cell.get("source", "")
    if isinstance(source, list):
        return "".join(source)
    return str(source)


def load(path: Path) -> Notebook:
    """Read a notebook off disk, or say clearly why it could not be read."""
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise NotebookError(f"{path} is not valid JSON: {error}") from error
    except OSError as error:
        raise NotebookError(f"{path} could not be read: {error}") from error

    if not isinstance(document, dict) or "cells" not in document:
        raise NotebookError(f"{path} has no cells, so it is not a notebook")

    cells = [
        Cell(
            number=number,
            kind=str(raw.get("cell_type", "unknown")),
            source=_source_of(raw),
            outputs=list(raw.get("outputs", [])),
            execution_count=raw.get("execution_count"),
            identifier=raw.get("id"),
        )
        for number, raw in enumerate(document["cells"], start=1)
    ]
    return Notebook(path=path, cells=cells, metadata=dict(document.get("metadata", {})))


def find(roots: list[Path]) -> list[Path]:
    """Every notebook under these paths, skipping checkpoints and virtual environments."""
    skip = {".ipynb_checkpoints", ".venv", "venv", "node_modules", "vendor", ".git"}
    found: list[Path] = []
    for root in roots:
        if root.is_file():
            found.append(root)
            continue
        for path in sorted(root.rglob("*.ipynb")):
            if any(part in skip for part in path.parts):
                continue
            found.append(path)
    return found
