"""Notebook builders for the tests, written as JSON rather than through nbformat.

The point of nbcheck is that it copes with whatever wrote the file, so the tests have to
be able to write files nbformat would not. Building the JSON by hand is the only way to
produce the shapes that actually cause trouble, like a source field stored as one string
instead of a list of lines.

This is not conftest.py because pytest collects the whole repository at once and imports
every test directory's conftest under the same module name. Two of them called conftest is
one collision, and the failure it produces points at the wrong package.
"""

from __future__ import annotations

import itertools
import json
from pathlib import Path

BADGE = (
    "[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)]"
    "(https://colab.research.google.com/github/tamnd/cpython-internals/blob/main/"
    "lessons/t01/t01.ipynb)"
)

INSTALL = '%pip install -q "pyxray @ git+https://github.com/tamnd/cpython-internals@main#subdirectory=pyxray"'


#: Cell ids became mandatory in nbformat 4.5. A notebook written without them still loads,
#: but nbclient warns while validating it, and this project turns warnings into errors.
_ids = itertools.count()


def markdown(source: str) -> dict:
    return {
        "cell_type": "markdown",
        "id": f"cell-{next(_ids)}",
        "metadata": {},
        "source": source.splitlines(keepends=True),
    }


def code(source: str, *, outputs: list | None = None, count: int | None = None) -> dict:
    return {
        "cell_type": "code",
        "id": f"cell-{next(_ids)}",
        "metadata": {},
        "execution_count": count,
        "outputs": outputs or [],
        "source": source.splitlines(keepends=True),
    }


def document(cells: list[dict], *, kernel: str = "python3") -> dict:
    return {
        "cells": cells,
        "metadata": {"kernelspec": {"name": kernel, "display_name": "Python 3"}},
        "nbformat": 4,
        "nbformat_minor": 5,
    }


def write(path: Path, cells: list[dict], *, kernel: str = "python3") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document(cells, kernel=kernel), indent=1), encoding="utf-8")
    return path


def clean_cells() -> list[dict]:
    """A notebook that passes every rule, for tests that break exactly one thing."""
    return [
        markdown(f"# A lesson\n\n{BADGE}\n"),
        markdown("First, install the package this lesson uses.\n"),
        code(INSTALL),
        markdown("Now print which interpreter is about to run everything below.\n"),
        code("import pyxray\n\npyxray.show()\n"),
        markdown("And here is the one line the whole lesson is about.\n"),
        code("answer = 6 * 7\nprint(answer)\n"),
    ]
