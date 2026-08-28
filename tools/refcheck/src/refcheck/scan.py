"""Finding citations in the files an author actually writes."""

from __future__ import annotations

import json
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from pathlib import Path

from .citation import Citation, find_all

TEXT_SUFFIXES = {".md", ".py", ".txt", ".toml", ".yml", ".yaml"}
NOTEBOOK_SUFFIXES = {".ipynb"}
SKIP_DIRECTORIES = {
    ".git",
    ".venv",
    "venv",
    "node_modules",
    "__pycache__",
    "vendor",
    "site",
    ".ruff_cache",
    ".pytest_cache",
}


@dataclass(frozen=True)
class Occurrence:
    """A citation and the file and line it was written on."""

    citation: Citation
    file: Path
    line: int

    @property
    def source(self) -> str:
        return f"{self.file}:{self.line}"


def scan_text(text: str, file: Path) -> Iterator[Occurrence]:
    for number, line in enumerate(text.splitlines(), start=1):
        for citation in find_all(line):
            yield Occurrence(citation, file, number)


def scan_notebook(text: str, file: Path) -> Iterator[Occurrence]:
    """Citations inside a Jupyter notebook's source cells, ignoring outputs.

    Outputs are ignored on purpose. A citation that appears only in a stored output is a
    citation nobody wrote, and holding the author to it produces confusing failures.
    """
    try:
        document = json.loads(text)
    except json.JSONDecodeError:
        return
    for index, cell in enumerate(document.get("cells", [])):
        source = cell.get("source", "")
        if isinstance(source, list):
            source = "".join(source)
        for number, line in enumerate(source.splitlines(), start=1):
            for citation in find_all(line):
                yield Occurrence(citation, file, number)
        del index


def scan_file(file: Path) -> list[Occurrence]:
    suffix = file.suffix.lower()
    try:
        text = file.read_text(encoding="utf-8")
    except OSError, UnicodeDecodeError:
        return []
    if suffix in NOTEBOOK_SUFFIXES:
        return list(scan_notebook(text, file))
    if suffix in TEXT_SUFFIXES:
        return list(scan_text(text, file))
    return []


def walk(roots: Iterable[Path]) -> Iterator[Path]:
    for root in roots:
        if root.is_file():
            yield root
            continue
        for path in sorted(root.rglob("*")):
            if not path.is_file():
                continue
            if any(part in SKIP_DIRECTORIES for part in path.parts):
                continue
            if path.suffix.lower() in TEXT_SUFFIXES | NOTEBOOK_SUFFIXES:
                yield path


def scan(roots: Iterable[Path]) -> list[Occurrence]:
    occurrences: list[Occurrence] = []
    for file in walk(roots):
        occurrences.extend(scan_file(file))
    return occurrences
