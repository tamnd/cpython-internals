"""Ask a browser Python which of the surfaces this project needs actually work.

Every Tier 0 experiment in the lessons is supposed to run in a browser tab with nothing
installed. That rests on Pyodide, which is CPython compiled to WebAssembly, and on the
introspection surfaces the lessons poke at surviving that build. This package runs the same
list of checks twice, once here and once there, and puts the two answers side by side.

The answer is not all good news, which is the point of measuring rather than assuming.
"""

from .browser import Missing
from .checks import BY_KEY, CHECKS, INFO, NICE, TIER0, Check
from .report import differences, markdown, regressions, summary, table, verdict
from .result import FATAL, OK, RAISED, SKIPPED, Outcome, Run

__all__ = [
    "BY_KEY",
    "CHECKS",
    "FATAL",
    "INFO",
    "NICE",
    "OK",
    "RAISED",
    "SKIPPED",
    "TIER0",
    "Check",
    "Missing",
    "Outcome",
    "Run",
    "differences",
    "markdown",
    "regressions",
    "summary",
    "table",
    "verdict",
]
