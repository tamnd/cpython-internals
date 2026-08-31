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


#: The program for b04-what-a-script-wrote. Long enough that inlining it would bury the
#: three fields above it that say what the experiment is for.
PROGRAM_ONE = r'''"""Count how much of the C in a real CPython checkout was written by a script.

Z02 makes this claim and cannot check it, because checking it needs the whole source tree and
that lesson deliberately does not download one. The build image has the tree the interpreter
was compiled from sitting at /usr/src/cpython, so here the claim is a measurement.

The rule for spotting a generated file is the one from Z02 and nothing cleverer: the file says
so in its own first three lines. The part worth reading is the bottom block, where every one of
those files is asked which script wrote it, and answers.
"""

import re
import time
from collections import Counter
from pathlib import Path

TREE = Path("/usr/src/cpython")
MARKERS = ("generated", "do not edit", "autogenerated")

#: The banners are not one format. pegen writes `@generated by pegen from python.gram`, the
#: cases generator writes a path on a line of its own, asdl_c writes a sentence, and Argument
#: Clinic writes a marker with no script name in it at all. Three patterns cover every file.
WROTE_IT = re.compile(r"[A-Za-z_][\w/]*\.py|\bpegen\b|\[clinic input\]")
NAMES = {"pegen": "Parser/pegen, the parser generator", "[clinic input]": "Argument Clinic"}


def head(path):
    return path.read_text(encoding="utf-8", errors="replace").split("\n")[:3]


def looks_generated(lines):
    return any(marker in " ".join(lines).lower() for marker in MARKERS)


def who_wrote(lines):
    found = WROTE_IT.search(" ".join(lines))
    if found is None:
        return "it does not say"
    return NAMES.get(found.group(0), found.group(0))


started = time.monotonic()
files = sorted(p for p in TREE.rglob("*") if p.suffix in {".c", ".h"} and p.is_file())

lines_in_all = 0
generated = []
for path in files:
    top = head(path)
    lines = len(path.read_text(encoding="utf-8", errors="replace").splitlines())
    lines_in_all += lines
    if looks_generated(top):
        generated.append((lines, str(path.relative_to(TREE)), who_wrote(top)))
took = time.monotonic() - started

lines_generated = sum(count for count, _, _ in generated)

print(f"C and header files in the tree: {len(files):>10,}")
print(f"lines in them:                  {lines_in_all:>10,}")
print()
print(f"files a script wrote:           {len(generated):>10,}")
print(f"lines a script wrote:           {lines_generated:>10,}")
print(f"share of the C nobody typed:    {lines_generated / lines_in_all:>10.1%}")
print()
print("the eight biggest, and the script each one names in its own first three lines")
print()
for lines, where, script in sorted(generated, reverse=True)[:8]:
    print(f"  {lines:>7,}  {where:<43} {script}")

print()
print("who wrote the most files")
print()
counted = Counter(script for _, _, script in generated)
for script, many in counted.most_common(6):
    print(f"  {many:>4} files   {script}")

print()
print(f"~ how long the scan took, in seconds: {took:.1f}")

assert len(files) > 1000, len(files)
assert 0.3 < lines_generated / lines_in_all < 0.45
'''


#: The program for b04-changing-the-source-of-truth.
PROGRAM_TWO = r'''"""Run the generators behind a third of CPython's C, then change what they read.

Two halves. The first regenerates four files that are already in the tree and compares them
byte for byte with what is there, which is what turns the word `generated` from a comment into
a fact. The second adds three lines to a copy of Python/bytecodes.c and runs two of the same
generators again, so one new instruction becomes an opcode number and thirteen lines of C.

Nothing here touches the tree. Every output goes to /tmp and the build is left as it was.
"""

import subprocess
import sys
import time
from pathlib import Path

TREE = Path("/usr/src/cpython")
BYTECODES = TREE / "Python/bytecodes.c"
GENERATORS = TREE / "Tools/cases_generator"

#: Four of the twelve things `make regen-cases` runs, picked because between them they cover a
#: header of numbers, a jump table, a Python module and the body of the eval loop.
JOBS = [
    ("opcode_id_generator.py", "Include/opcode_ids.h"),
    ("target_generator.py", "Python/opcode_targets.h"),
    ("py_metadata_generator.py", "Lib/_opcode_metadata.py"),
    ("tier1_generator.py", "Python/generated_cases.c.h"),
]

#: The three lines being added, and the instruction they go after. NOP is the smallest thing in
#: the file, so copying its shape gives an instruction that takes nothing and returns nothing.
NOP = """        pure inst(NOP, (--)) {
        }
"""
ADDED = """        pure inst(SHOUT, (--)) {
            printf("this instruction was not here an hour ago\\n");
        }
"""


def run(generator, source, into):
    subprocess.run(
        [sys.executable, str(GENERATORS / generator), "-o", str(into), str(source)],
        check=True,
        capture_output=True,
    )
    return Path(into)


counted = len(BYTECODES.read_text().splitlines())
print(f"input:      Python/bytecodes.c, {counted:,} lines")
print("generators: Tools/cases_generator")
print()

started = time.monotonic()
for generator, output in JOBS:
    fresh = run(generator, BYTECODES, f"/tmp/{Path(output).name}")
    already = TREE / output
    same = fresh.read_bytes() == already.read_bytes()
    lines = len(already.read_text().splitlines())
    print(f"  {output:<32} {lines:>7,} lines   byte for byte identical: {same}")
    assert same, output
took = time.monotonic() - started

print()
print("Now the same generators, with three lines added to a copy of the input.")
print()
for line in ADDED.splitlines():
    print("   ", line.removeprefix("        "))

source = BYTECODES.read_text()
assert source.count(NOP) == 1
changed = Path("/tmp/bytecodes.c")
changed.write_text(source.replace(NOP, NOP + "\n" + ADDED))

ids = run("opcode_id_generator.py", changed, "/tmp/new_ids.h")
cases = run("tier1_generator.py", changed, "/tmp/new_cases.c.h")

print()
print("Include/opcode_ids.h comes back with a number for it:")
print()
for line in ids.read_text().splitlines():
    if "SHOUT" in line:
        print("   ", line.rstrip())

body = cases.read_text().splitlines()
at = body.index("        TARGET(SHOUT) {")
ends = body.index("        }", at)
print()
print("and Python/generated_cases.c.h comes back with the eval loop case for it:")
print()
for line in body[at : ends + 1]:
    print("   ", line.removeprefix("        "))

print()
print(f"~ how long the first four generators took, in seconds: {took:.1f}")

assert "#define SHOUT" in ids.read_text()
assert "this instruction was not here an hour ago" in cases.read_text()
'''


WHAT_A_SCRIPT_WROTE = Experiment(
    slug="b04-what-a-script-wrote",
    lesson="B04",
    title="How much of the C nobody typed",
    asks="How much of the C in CPython was written by a script rather than by a person?",
    needs=(
        "the answer is a count over every C file in the source tree, and a reader running in "
        "a browser has the standard library but not the 1,185 C and header files"
    ),
    build="debug",
    program=PROGRAM_ONE,
)


CHANGING_THE_SOURCE_OF_TRUTH = Experiment(
    slug="b04-changing-the-source-of-truth",
    lesson="B04",
    title="Adding an instruction and watching the C appear",
    asks="What happens to the generated C when you add an instruction to Python/bytecodes.c?",
    needs=(
        "the generators are scripts in Tools/cases_generator that read Python/bytecodes.c out "
        "of a source tree, and neither the scripts nor the input ship with an installed Python"
    ),
    build="debug",
    program=PROGRAM_TWO,
)


EXPERIMENTS: tuple[Experiment, ...] = (
    COMPILING_COSTS_NOTHING_THAT_LASTS,
    A_LEAK_YOU_CAN_SEE,
    WHAT_A_SCRIPT_WROTE,
    CHANGING_THE_SOURCE_OF_TRUTH,
)


def find(slug: str) -> Experiment:
    for experiment in EXPERIMENTS:
        if experiment.slug == slug:
            return experiment
    known = ", ".join(one.slug for one in EXPERIMENTS)
    raise KeyError(f"no experiment called {slug!r}; there is {known}")
