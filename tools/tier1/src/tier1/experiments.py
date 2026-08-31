"""The experiments that a reader's own Python cannot run, and what each one is asking.

A Tier 0 experiment runs in a browser tab. A Tier 1 experiment needs an interpreter that
was built a particular way, and asking a reader to build one is asking them to skip the
lesson. So the experiment is run in the published image instead, in CI, and what it printed
is committed next to it. The reader gets the numbers and the program that produced them, and
anybody who wants to check can run the same image.

Every experiment declares why it needs the build it needs. That field is not documentation,
it is the entry fee: if the answer is "it does not", the experiment belongs in the lesson as
a cell the reader runs, where it is worth ten times as much.
"""

from __future__ import annotations

from dataclasses import dataclass

#: Which build each of these wants. One today, and the field exists because the free
#: threaded and JIT builds are published too and the concurrency lessons will want them.
BUILDS = ("debug", "freethreaded", "jit", "tailcall", "release")

#: A line the checker does not compare. The program marks a line this way when what it
#: prints is a measurement rather than a fact, and two runs of a measurement are allowed to
#: disagree. See `recording.py` for why this exists rather than a tolerance.
MEASURED = "~ "


@dataclass(frozen=True)
class Experiment:
    """One program, the build it needs, and the reason it needs it."""

    slug: str
    lesson: str
    title: str
    #: The question in one sentence, which is what a reader sees above the output.
    asks: str
    #: Why a stock interpreter cannot answer it. Checked for being filled in, not for being
    #: true, because nothing can check that.
    needs: str
    build: str
    program: str

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
        if MEASURED.strip() not in self.program:
            found.append(
                f"{self.slug}: nothing in the program is marked as a measurement, so every "
                f"line of its output has to come out the same on two machines"
            )
        return found


COMPILING_COSTS_NOTHING_THAT_LASTS = Experiment(
    slug="t05-compiling-costs-nothing-that-lasts",
    lesson="T05",
    title="What compiling leaves behind",
    asks="Does compiling the same line over and over leave anything behind?",
    needs=(
        "sys.gettotalrefcount() only exists in a build configured with --with-pydebug, and "
        "it is the only way to see every reference in the process rather than one object's"
    ),
    build="debug",
    program='''"""Compile one line two thousand times and see what is left over.

T05 says the compiler throws away everything except the code object. This is that sentence,
measured. `sys.gettotalrefcount()` is the sum of every reference count in the process, so if
compiling kept something and forgot about it, this number would climb and keep climbing.
"""

import gc
import sys

SOURCE = "answer = 6 * 7\\n"


def total():
    """Every reference in the process, after tidying up anything the collector can free."""
    gc.collect()
    return sys.gettotalrefcount()


# The noise floor, first, because without it none of the numbers below can be read. Taking
# the measurement is itself Python: the collector runs, an f-string gets built, objects are
# made and dropped. So the same measurement twice in a row does not come back the same.
quiet = total()
noise = total() - quiet
print(f"~ how far the number moves when nothing happens: {noise}")

# The first compile is not free and is not supposed to be. The names in the source get
# interned, the filename gets interned, and the interpreter keeps all of it on purpose.
cold = total()
first = compile(SOURCE, "lesson.py", "exec")
del first
warm = total()
print(f"~ what the first compile leaves behind: {warm - cold}")

for _ in range(2000):
    code = compile(SOURCE, "lesson.py", "exec")
    del code
after = total()
drift = after - warm
print(f"~ what two thousand more compiles leave behind: {drift}")

# Fifty is generous next to a noise floor in single figures, and tiny next to the thing it
# would catch. If every compile kept one object, this would be two thousand.
assert abs(drift) < 50, f"two thousand compiles moved the total by {drift}"

# Now the other direction. One code object costs a handful of references, which is a number
# lost in the noise, so keep a thousand and the cost stops being arguable.
kept = [compile(SOURCE, "lesson.py", "exec") for _ in range(1000)]
held = total() - after
print(f"~ what a thousand code objects cost while they are alive: {held}")
assert held > 1000, f"a thousand live code objects cost {held}, which cannot be right"

del kept
left = total() - after
print(f"~ what is left after dropping all thousand: {left}")
assert abs(left) < 50, f"dropping a thousand code objects left {left} behind"

print("compiling keeps the code object and nothing else, and dropping that gets it all back")
''',
)


A_LEAK_YOU_CAN_SEE = Experiment(
    slug="b03-a-leak-you-can-see",
    lesson="B03",
    title="What the leak hunter actually catches",
    asks="What does it look like when the test suite catches a reference leak?",
    needs=(
        "the -R flag reads sys.gettotalrefcount(), which only exists in a build configured "
        "with --with-pydebug, and regrtest refuses to hunt leaks without it"
    ),
    build="debug",
    program='''"""Run two test files under the leak hunter, one written to leak and one not.

B03 says `-R` runs a test a few times over and watches the interpreter's total reference
count. This is that sentence run for real. The two test files do the same amount of work and
differ in one line: one of them appends to a list that outlives the test, and the other
appends to a list that does not.

The interesting part is the row of dots and digits. Two warmup runs, then three counted ones,
one character each, and the difference between the two files is visible at a glance.
"""

import re
import subprocess
import sys
import time
from pathlib import Path

LEAKY = \"\"\"import unittest

KEPT = []


class Leaky(unittest.TestCase):
    def test_keeps_one_object(self):
        KEPT.append(object())
        self.assertEqual(1 + 1, 2)
\"\"\"

FINE = \"\"\"import unittest


class Fine(unittest.TestCase):
    def test_keeps_nothing(self):
        kept = []
        kept.append(object())
        self.assertEqual(1 + 1, 2)
\"\"\"

#: The wall clock and the load average regrtest puts in front of its progress lines. Both are
#: different on every run on every machine and neither says anything about the leak, so the
#: prefix comes off and the rest of the line stays exactly as it was printed.
STAMP = re.compile("^[0-9]+:[0-9][0-9]:[0-9][0-9] load avg: [0-9.]+ ")

where = Path("/tmp/b03")
where.mkdir(exist_ok=True)
(where / "test_leaky.py").write_text(LEAKY)
(where / "test_fine.py").write_text(FINE)

command = [
    sys.executable,
    "-m",
    "test",
    "--testdir",
    str(where),
    "-R",
    "3:3",
    "test_fine",
    "test_leaky",
]
print("$ python -m test --testdir /tmp/b03 -R 3:3 test_fine test_leaky")
print()

# The two streams are merged rather than kept apart. regrtest writes its progress to standard
# output and the leak hunter writes to standard error, both flushed line by line, and reading
# them separately would print the verdict in one block and the run it came from in another.
started = time.monotonic()
done = subprocess.run(
    command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, cwd="/tmp"
)
took = time.monotonic() - started

for line in done.stdout.splitlines():
    if line.startswith(("Using random seed", "Total duration")):
        continue
    print(STAMP.sub("", line))

print()
print(f"~ how long the two files took together, in seconds: {took:.1f}")
print(f"regrtest exited {done.returncode}, which is the code it uses for a test that failed")

assert done.returncode == 2, done.stdout
assert "test_leaky leaked [1, 1, 1] references" in done.stdout, done.stdout
assert "test_fine leaked" not in done.stdout, done.stdout
''',
)


EXPERIMENTS: tuple[Experiment, ...] = (
    COMPILING_COSTS_NOTHING_THAT_LASTS,
    A_LEAK_YOU_CAN_SEE,
)


def find(slug: str) -> Experiment:
    for experiment in EXPERIMENTS:
        if experiment.slug == slug:
            return experiment
    known = ", ".join(one.slug for one in EXPERIMENTS)
    raise KeyError(f"no experiment called {slug!r}; there is {known}")
