"""Structural checks and execution for the lesson notebooks.

Every lesson ships as a notebook a reader can open in Colab and run without installing
anything first. That promise has a handful of preconditions, all of them easy to break by
accident and none of them visible in a diff, so they are checked here rather than trusted.
"""

from __future__ import annotations

from .notebook import Cell, Notebook, NotebookError, find, load
from .rules import Problem, check
from .run import Failure, execute

__all__ = [
    "Cell",
    "Failure",
    "Notebook",
    "NotebookError",
    "Problem",
    "check",
    "execute",
    "find",
    "load",
]
__version__ = "0.1.0"
