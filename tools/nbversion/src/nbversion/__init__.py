"""Finding the lesson cells whose output depends on which Python is running.

The lessons are written against a pinned CPython 3.15, and a reader who opens one in Colab
or clicks a WASM widget is on 3.14, because that is what those runtimes ship. Most cells
do not care. A few do, and those are the dangerous ones: the cell runs, prints something
plausible, and quietly teaches the reader a fact about the wrong interpreter.

So the lessons are executed on both versions and the outputs compared. A cell that differs
has to carry a note saying so, and a note has to correspond to a cell that really differs.
Neither half is worth much without the other.
"""

from .compare import Finding, cells, notebooks, summary
from .declare import KEY, NAMESPACE, note, notes
from .normalise import outputs, text
from .record import Recording, run, version

__all__ = [
    "KEY",
    "NAMESPACE",
    "Finding",
    "Recording",
    "cells",
    "note",
    "notebooks",
    "notes",
    "outputs",
    "run",
    "summary",
    "text",
    "version",
]
__version__ = "0.1.0"
