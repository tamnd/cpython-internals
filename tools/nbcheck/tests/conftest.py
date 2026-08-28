"""Fixtures shared by the nbcheck tests. The builders live in notebook_fixtures.py."""

from __future__ import annotations

from pathlib import Path

import pytest
from notebook_fixtures import clean_cells, write


@pytest.fixture
def root(tmp_path: Path) -> Path:
    return tmp_path


@pytest.fixture
def clean(tmp_path: Path) -> Path:
    """A notebook that passes every rule, so a test can break exactly one thing."""
    return write(tmp_path / "lessons" / "t01" / "t01.ipynb", clean_cells())
