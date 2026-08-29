"""Notebook and recording builders for the nbversion tests.

Not conftest.py: pytest collects the whole repository in one run and imports every test
directory's conftest under the same module name, so two of them called conftest collide
and the error points at the wrong package.
"""

from __future__ import annotations

import itertools
import json
from pathlib import Path

from nbversion.declare import DIFFERS, NAMESPACE, VARIES
from nbversion.record import Recording
from nbversion.record import write as write_recording

_ids = itertools.count()


def code(
    source: str, *, differs: str = "", varies: str = "", identifier: str | None = None
) -> dict:
    metadata = {}
    if differs:
        metadata = {NAMESPACE: {DIFFERS: differs}}
    elif varies:
        metadata = {NAMESPACE: {VARIES: varies}}
    return {
        "cell_type": "code",
        "id": identifier or f"cell-{next(_ids)}",
        "metadata": metadata,
        "execution_count": None,
        "outputs": [],
        "source": source.splitlines(keepends=True),
    }


def markdown(source: str, *, identifier: str | None = None) -> dict:
    return {
        "cell_type": "markdown",
        "id": identifier or f"cell-{next(_ids)}",
        "metadata": {},
        "source": source.splitlines(keepends=True),
    }


def notebook(path: Path, cells: list[dict]) -> Path:
    body = {
        "cells": cells,
        "metadata": {"kernelspec": {"name": "python3", "display_name": "Python 3"}},
        "nbformat": 4,
        "nbformat_minor": 5,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(body, indent=1), encoding="utf-8")
    return path


def recorded(root: Path, python: str, cells: dict[str, str], name: str = "t01.ipynb") -> Path:
    """A recording on disk, without going anywhere near a kernel."""
    return write_recording(Recording(notebook=name, python=python, cells=cells), root)
