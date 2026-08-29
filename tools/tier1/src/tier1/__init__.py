"""Experiments that need a debug build, run in one, and recorded so a reader does not need one.

Most of this project is Tier 0: open the notebook, run the cell, watch the thing happen on
whatever Python you already have. A few questions cannot be asked that way. Counting every
reference in the process needs an interpreter configured with `--with-pydebug`, and telling a
beginner to compile CPython before lesson five is telling them to stop reading.

So the program runs somewhere else. It runs in the image this project publishes and pins by
digest, in CI, and what it printed is committed next to it and shown in the lesson. The reader
gets the program and the numbers. Anybody who wants to check gets one `docker run` and the
same digest. And when the pinned interpreter moves, the recording stops matching and something
goes red, which is the part that keeps it honest a year from now.
"""

from .checks import problems, shown_in_lesson
from .experiments import BUILDS, EXPERIMENTS, MEASURED, Experiment, find
from .recording import RECORDINGS, Recording, Unreadable, comparable, differences, show

__all__ = [
    "BUILDS",
    "EXPERIMENTS",
    "MEASURED",
    "RECORDINGS",
    "Experiment",
    "Recording",
    "Unreadable",
    "comparable",
    "differences",
    "find",
    "problems",
    "show",
    "shown_in_lesson",
]
