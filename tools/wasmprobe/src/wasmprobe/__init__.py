"""Ask a browser Python which of the surfaces this project needs actually work.

Every Tier 0 experiment in the lessons is supposed to run in a browser tab with nothing
installed. That rests on Pyodide, which is CPython compiled to WebAssembly, and on the
introspection surfaces the lessons poke at surviving that build. This package runs the same
list of checks twice, once here and once there, and puts the two answers side by side.

The answer is not all good news, which is the point of measuring rather than assuming.

There is a second half in `lessons.py`, which runs the notebooks themselves rather than a
list of surfaces. It has its own `markdown`, `summary` and `regressions`, doing the same job
one level up, so the module is exported rather than its functions and you reach them as
`lessons.markdown(ran)`. Two functions of the same name in one namespace would be a coin flip
over which one a reader thinks they are calling.
"""

from . import lessons
from .browser import Missing
from .checks import BY_KEY, CHECKS, INFO, NICE, TIER0, Check
from .lessons import ACCEPTED, Cell, Lesson, Ran
from .report import differences, markdown, regressions, summary, table, verdict
from .result import FATAL, OK, RAISED, SKIPPED, Outcome, Run

__all__ = [
    "ACCEPTED",
    "BY_KEY",
    "CHECKS",
    "FATAL",
    "INFO",
    "NICE",
    "OK",
    "RAISED",
    "SKIPPED",
    "TIER0",
    "Cell",
    "Check",
    "Lesson",
    "Missing",
    "Outcome",
    "Ran",
    "Run",
    "differences",
    "lessons",
    "markdown",
    "regressions",
    "summary",
    "table",
    "verdict",
]
