"""Real gdb sessions against the debug build, recorded so a reader without gdb can read one.

Everything else in this project is something the reader runs. This is the one thing that is
not, and it is deliberate. Watching a stopped interpreter needs three things a reader in a
browser tab does not have: a debug build, a debugger, and the C source the debugger reads.
Asking for all three before lesson twelve is asking most people to stop.

So the session runs here instead. It runs in the debug image this project publishes and pins
by digest, and gdb's output is committed command by command, each with the line of
explanation that would have gone above it anyway. The lesson lays those out in order and
puts its own paragraphs between them, so the reader goes through the session at the pace a
person at the prompt would have, without needing the prompt.

The transcripts are checked twice. Offline, on every pull request, they are checked for
still belonging to the session above them and still naming the image this project pins. In
the job that has Docker they are run again and compared, with addresses and process ids
allowed to move and nothing else. That second check is the only thing that makes committing
a backtrace worth more than pasting one into the prose by hand.
"""

from .checks import problems, shown_in_lesson
from .recording import (
    ARCHES,
    RECORDINGS,
    Printed,
    Recording,
    Unreadable,
    comparable,
    differences,
    program_of,
    show,
    steps_of,
)
from .sessions import BUILDS, SESSIONS, Session, Step, find

__all__ = [
    "ARCHES",
    "BUILDS",
    "RECORDINGS",
    "SESSIONS",
    "Printed",
    "Recording",
    "Session",
    "Step",
    "Unreadable",
    "comparable",
    "differences",
    "find",
    "problems",
    "program_of",
    "show",
    "shown_in_lesson",
    "steps_of",
]
