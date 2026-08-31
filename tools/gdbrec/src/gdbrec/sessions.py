"""The gdb sessions this project records, and what each one is trying to show.

A reader in a browser tab has no gdb, no debug build and no C source, and telling them to
get all three before they can see what a stopped interpreter looks like is telling them to
stop reading. So the session is run for them, in the published debug image, and the whole
transcript is committed next to the lesson that shows it. They read the same thing somebody
sitting at the prompt would have read, one command at a time, with a line of explanation
above each one.

Every session declares why it needs the debug build. As in `tier1`, that field is the entry
fee rather than documentation: gdb will happily attach to a release build, and if the answer
is that a release build shows the same thing then the session is not earning the image.
"""

from __future__ import annotations

from dataclasses import dataclass

#: Which build each session wants. The debug one today. The field exists because a session
#: about the free threaded object header will want a different image and nothing else about
#: the machinery would change.
BUILDS = ("debug", "freethreaded", "jit", "tailcall", "release")

#: Where the program under test is written inside the container. One path for every session,
#: so a command in a transcript reads the same as a command a reader would type.
PROGRAM = "/tmp/program.py"

#: Commands run before anything the reader sees. These two are batch mode plumbing rather
#: than anything to learn: with pagination on, gdb stops every twenty four lines waiting for
#: a keypress that is never coming, and with confirmation on it asks whether you really meant
#: it and then answers itself. Everything worth typing is in a session's own script.
PREAMBLE = ("set pagination off", "set confirm off")


@dataclass(frozen=True)
class Step:
    """One command, and the sentence that goes above its output."""

    command: str
    #: What this command is for, in one line. Checked for being filled in.
    note: str

    def problems(self, slug: str) -> list[str]:
        found = []
        if not self.command.strip():
            found.append(f"{slug}: a step with no command")
        if "\n" in self.command:
            found.append(f"{slug}: {self.command!r} should be one command")
        if not self.note.strip():
            found.append(f"{slug}: say what {self.command!r} is for")
        if "\n" in self.note:
            found.append(f"{slug}: the note on {self.command!r} should be one line")
        return found


@dataclass(frozen=True)
class Session:
    """One program, one script of gdb commands, and the reason it needs a debugger at all."""

    slug: str
    lesson: str
    title: str
    #: The question in one sentence, which is what a reader sees above the transcript.
    asks: str
    #: Why this needs the debug build rather than any Python. Checked for being filled in,
    #: not for being true, because nothing can check that.
    needs: str
    build: str
    program: str
    script: tuple[Step, ...]

    def commands(self) -> list[str]:
        return [one.command for one in self.script]

    def problems(self) -> list[str]:
        found = []
        if not self.slug.startswith(self.lesson.lower()):
            found.append(f"{self.slug}: the slug should start with {self.lesson.lower()}")
        for field, text in (("asks", self.asks), ("needs", self.needs)):
            if not text.strip():
                found.append(f"{self.slug}: say what the {field} field should say")
            if "\n" in text:
                found.append(f"{self.slug}: the {field} field should be one line")
        if self.build not in BUILDS:
            found.append(f"{self.slug}: {self.build!r} is not one of the published builds")
        if not self.program.strip():
            found.append(f"{self.slug}: there is no program")
        if not self.script:
            found.append(f"{self.slug}: there are no commands, so there is nothing to record")
        for step in self.script:
            found.extend(step.problems(self.slug))
        return found


#: Why every session here wants the debug build, in one sentence each time it is asked for.
#: Kept in one place because it is the same reason twice and two copies of it drift.
DEBUG = (
    "a release build is compiled with optimizations, so the arguments read <optimized out> "
    "and half the frames have been inlined away, and this image is also the one that ships "
    "Tools/gdb/libpython.py, which is where py-bt comes from"
)


TWO_STACKS = Session(
    slug="b02-the-two-stacks",
    lesson="B02",
    title="Two stacks, one moment",
    asks="What does a stopped interpreter look like from C, and from Python, at the same instant?",
    needs=DEBUG,
    build="debug",
    program="""# Four Python calls deep, ending in one multiplication.
#
# The multiplication is the point. It is the last thing this program does before it has an
# answer, so a breakpoint on the C function behind * stops the interpreter at a moment we can
# describe from both sides.
#
# Four functions, one operator, one print, and no docstring. The docstring is left out on
# purpose: it would land in the module's globals, and gdb prints the globals dictionary in
# every frame that carries one.


def double(n):
    return n * 2


def middle(n):
    return double(n)


def top():
    return middle(21)


print(top())
""",
    script=(
        Step(
            "tbreak pymain_run_file",
            "The interpreter runs a lot of Python of its own before it reaches your file, so "
            "stop once at the moment it is about to start. The t means this fires only once.",
        ),
        Step(
            f"run {PROGRAM}",
            "Start the program under the debugger. It stops at the temporary breakpoint.",
        ),
        Step(
            "break PyNumber_Multiply",
            "Now that startup is out of the way, break on the C function behind the * operator.",
        ),
        Step(
            "continue",
            "Let it run until the multiplication. The two arguments printed are the operands.",
        ),
        Step(
            "bt -frame-arguments none",
            "The whole C stack, with the argument values left out, because a CPython frame "
            "carries whole dictionaries and printing them buries the shape. Count the "
            "_PyEval_EvalFrameDefault frames.",
        ),
        Step(
            "py-bt",
            "The same instant, described in Python. Count these frames and compare.",
        ),
        Step(
            "print ((PyObject *) v)->ob_type->tp_name",
            "v is the left operand. Every object starts with a pointer to its type, and this "
            "reads the name out of memory rather than asking type() for it.",
        ),
        Step(
            "print ((PyObject *) v)->ob_refcnt",
            "The other half of the object header. This number is worth staring at.",
        ),
    ),
)


A_CRASH = Session(
    slug="b02-where-a-crash-came-from",
    lesson="B02",
    title="Where a crash came from",
    asks="When the interpreter segfaults, which line of Python was responsible?",
    needs=DEBUG,
    build="debug",
    program="""# Read one byte from address zero, on purpose.
#
# There is no way to do this by accident in Python, which is the point. ctypes is the door out
# of the language, and past that door a mistake is a segfault rather than an exception.
# Extension modules live on the other side of the same door, so this is a small version of
# what a bug in one looks like from the outside.
#
# This program prints nothing. It dies three calls down, and working out which three is the
# whole exercise.

import ctypes


def read_nothing():
    return ctypes.string_at(0)


def ask():
    return read_nothing()


print(ask())
""",
    script=(
        Step(
            f"run {PROGRAM}",
            "No breakpoints this time. Run it and wait for it to fall over.",
        ),
        Step(
            "bt 4",
            "The top four C frames. The first is inside the C library and has no name, which "
            "is about as much as a C stack alone was ever going to tell you.",
        ),
        Step(
            "py-bt",
            "The same crash, in Python. This is the answer, and it took one command.",
        ),
        Step(
            "py-list",
            "The Python source around the line that did it, read out of the stopped process.",
        ),
    ),
)


SESSIONS: tuple[Session, ...] = (TWO_STACKS, A_CRASH)

BY_SLUG = {one.slug: one for one in SESSIONS}


def find(slug: str) -> Session:
    """One session by slug, with the list in the error rather than a bare KeyError."""
    if slug not in BY_SLUG:
        known = ", ".join(BY_SLUG)
        raise KeyError(f"no session called {slug!r}. There are these: {known}")
    return BY_SLUG[slug]
