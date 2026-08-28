"""Fixtures shared by the bpcheck tests. The builders live in blueprint_fixtures.py."""

from __future__ import annotations

from pathlib import Path

import pytest
from blueprint_fixtures import clean_text, write


@pytest.fixture
def clean(tmp_path: Path) -> Path:
    """A blueprint that passes every rule, so a test can break exactly one thing."""
    return write(tmp_path / "blueprints" / "BP-DEMO.md", clean_text())
