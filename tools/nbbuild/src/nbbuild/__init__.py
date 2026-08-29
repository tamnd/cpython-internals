"""Lesson notebooks, written as Python and generated into JSON.

Nobody should have to edit a `.ipynb` by hand, and nobody should have to review a diff of
one either. Each lesson is defined by a `build.py` sitting next to it, and this package is
the small amount of machinery that turns one into a notebook a reader can open in Colab.
"""

from __future__ import annotations

from .lesson import BADGE_IMAGE, COLAB, Lesson, Malformed, repository_root
from .notes import BANNER, OFFSETS, SMALL_INTS, TRAILING_NONE, YOUR_INSTALL

__all__ = [
    "BADGE_IMAGE",
    "BANNER",
    "COLAB",
    "OFFSETS",
    "SMALL_INTS",
    "TRAILING_NONE",
    "YOUR_INSTALL",
    "Lesson",
    "Malformed",
    "repository_root",
]
__version__ = "0.1.0"
