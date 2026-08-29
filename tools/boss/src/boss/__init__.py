"""The boss fights, and the machinery that keeps them honest.

Every part of this project ends with something a reader can check themselves against. Most of
that is a cell that prints a number next to the number the lesson predicted. A boss fight is
the harder version: a problem with no worked answer in the text, and a grader that says yes or
no and, when it says no, says exactly where you and CPython stopped agreeing.

The graders live with their lessons, at `lessons/<lesson>/grade.py`, because a reader should be
able to run one with a plain `python` and no install. This package is the part around them.
It knows which fights exist, checks that each one is still assembled properly, and runs every
grader against a submission that should pass and a submission that should fail. That last bit
is the one that matters over time. A grader nobody has watched fail is a grader that might be
waving everything through, and the way you find that out is by handing it something wrong on
every pull request and insisting it notices.
"""

from .checks import problems
from .fights import FIGHTS, Fight, Unknown, find
from .run import Ran, graded, verdicts

__all__ = [
    "FIGHTS",
    "Fight",
    "Ran",
    "Unknown",
    "find",
    "graded",
    "problems",
    "verdicts",
]
